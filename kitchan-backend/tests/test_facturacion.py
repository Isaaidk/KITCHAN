"""Tests de Facturación: casos de uso con puertos falsos, el adaptador de
Odoo (JSON-2) con un transporte HTTP simulado y el webhook de Odoo."""

import json
from datetime import datetime, timezone

import httpx
import pytest

from src.kitchan.main import app
from src.kitchan.modules.facturacion.application.facturar_pedido import (
    ActualizarFacturaDesdeOdooUseCase,
    ConciliarFacturasPendientesUseCase,
    FacturarPedidoUseCase,
)
from src.kitchan.modules.facturacion.domain.entities import (
    DatosFactura,
    EstadoFactura,
    FacturaPedido,
    LineaFactura,
    PedidoAFacturar,
    ResultadoOdoo,
)
from src.kitchan.modules.facturacion.domain.exceptions import (
    OdooError,
    OdooNoConfiguradoError,
    PedidoNoEncontradoError,
    PedidoNoFacturableError,
)
from src.kitchan.modules.facturacion.domain.ports import (
    FacturaRepositoryPort,
    OdooFacturacionPort,
    PedidosFacturablesPort,
)
from src.kitchan.modules.facturacion.infrastructure.dependencias import (
    get_actualizar_use_case,
)
from src.kitchan.modules.facturacion.infrastructure.odoo_json2_adapter import (
    OdooJson2Adapter,
    a_resultado,
)

RESTAURANTE = "11111111-1111-1111-1111-111111111111"


def _pedido(estado="ENTREGADA", restaurante_id=RESTAURANTE) -> PedidoAFacturar:
    return PedidoAFacturar(
        id="pedido-1",
        restaurante_id=restaurante_id,
        origen="RAPPI",
        id_externo="RAPPI-ABC",
        estado=estado,
        items=[
            LineaFactura(descripcion="Hamburguesa", cantidad=2, precio_con_iva=4.25),
            LineaFactura(descripcion="Regalo", cantidad=0, precio_con_iva=0),
        ],
    )


class OdooFalso(OdooFacturacionPort):
    def __init__(self, estado=EstadoFactura.PENDIENTE_SRI, configurado=True):
        self.estado = estado
        self._configurado = configurado
        self.emitidas: list[DatosFactura] = []
        self.reenvios: list[int] = []
        self.fallar_en: set[int] = set()

    def configurado(self) -> bool:
        return self._configurado

    def _resultado(self, move_id: int) -> ResultadoOdoo:
        return ResultadoOdoo(
            odoo_move_id=move_id, numero=f"Fact {move_id}", estado=self.estado
        )

    async def emitir_factura(self, datos):
        self.emitidas.append(datos)
        return self._resultado(10)

    async def consultar_factura(self, odoo_move_id):
        return self._resultado(odoo_move_id)

    async def reenviar_al_sri(self, odoo_move_id):
        if odoo_move_id in self.fallar_en:
            raise OdooError("Odoo no respondió.")
        self.reenvios.append(odoo_move_id)
        return self._resultado(odoo_move_id)


class FacturasEnMemoria(FacturaRepositoryPort):
    def __init__(self, *facturas: FacturaPedido):
        self.facturas = {f.pedido_id: f for f in facturas}

    async def guardar(self, factura):
        self.facturas[factura.pedido_id] = factura
        return factura

    async def buscar_por_pedido(self, pedido_id):
        return self.facturas.get(pedido_id)

    async def buscar_por_odoo_move(self, odoo_move_id):
        return next(
            (f for f in self.facturas.values() if f.odoo_move_id == odoo_move_id),
            None,
        )

    async def listar_pendientes(self):
        return [
            f for f in self.facturas.values() if f.estado == EstadoFactura.PENDIENTE_SRI
        ]


class PedidosFalsos(PedidosFacturablesPort):
    def __init__(self, pedido):
        self.pedido = pedido

    async def obtener(self, pedido_id):
        return self.pedido if self.pedido and self.pedido.id == pedido_id else None


def _factura(pedido_id="pedido-1", move_id=10, estado=EstadoFactura.PENDIENTE_SRI):
    return FacturaPedido(
        pedido_id=pedido_id,
        restaurante_id=RESTAURANTE,
        odoo_move_id=move_id,
        estado=estado,
    )


# ---------------------------------------------------------------- casos de uso


@pytest.mark.asyncio
async def test_factura_el_pedido_en_odoo_y_la_guarda():
    odoo, facturas = OdooFalso(), FacturasEnMemoria()
    caso = FacturarPedidoUseCase(odoo, facturas, PedidosFalsos(_pedido()))

    factura = await caso.ejecutar("pedido-1", RESTAURANTE)

    assert factura.odoo_move_id == 10
    assert factura.estado == EstadoFactura.PENDIENTE_SRI
    datos = odoo.emitidas[0]
    assert datos.referencia == "KITCHAN-pedido-1"
    assert datos.origen == "RAPPI RAPPI-ABC"
    # Las líneas sin cantidad no se facturan.
    assert [linea.descripcion for linea in datos.lineas] == ["Hamburguesa"]
    assert await facturas.buscar_por_pedido("pedido-1") == factura


@pytest.mark.asyncio
async def test_un_segundo_clic_no_crea_otra_factura():
    odoo = OdooFalso()
    facturas = FacturasEnMemoria(_factura())
    caso = FacturarPedidoUseCase(odoo, facturas, PedidosFalsos(_pedido()))

    await caso.ejecutar("pedido-1", RESTAURANTE)

    assert odoo.emitidas == []
    assert odoo.reenvios == []


@pytest.mark.asyncio
async def test_factura_con_error_reintenta_el_envio_al_sri():
    odoo = OdooFalso(estado=EstadoFactura.AUTORIZADA)
    facturas = FacturasEnMemoria(_factura(estado=EstadoFactura.CON_ERROR))
    caso = FacturarPedidoUseCase(odoo, facturas, PedidosFalsos(_pedido()))

    factura = await caso.ejecutar("pedido-1", RESTAURANTE)

    assert odoo.reenvios == [10]
    assert odoo.emitidas == []
    assert factura.estado == EstadoFactura.AUTORIZADA


@pytest.mark.asyncio
async def test_no_factura_pedidos_de_otro_restaurante():
    odoo = OdooFalso()
    caso = FacturarPedidoUseCase(
        odoo,
        FacturasEnMemoria(),
        PedidosFalsos(_pedido(restaurante_id="otro-restaurante")),
    )

    with pytest.raises(PedidoNoEncontradoError):
        await caso.ejecutar("pedido-1", RESTAURANTE)
    assert odoo.emitidas == []


@pytest.mark.asyncio
@pytest.mark.parametrize("estado", ["NUEVA", "EN_PREPARACION", "LISTA", "CANCELADA"])
async def test_solo_factura_pedidos_entregados(estado):
    odoo = OdooFalso()
    caso = FacturarPedidoUseCase(
        odoo, FacturasEnMemoria(), PedidosFalsos(_pedido(estado=estado))
    )

    with pytest.raises(PedidoNoFacturableError):
        await caso.ejecutar("pedido-1", RESTAURANTE)
    assert odoo.emitidas == []


@pytest.mark.asyncio
async def test_sin_odoo_configurado_no_factura():
    caso = FacturarPedidoUseCase(
        OdooFalso(configurado=False), FacturasEnMemoria(), PedidosFalsos(_pedido())
    )

    with pytest.raises(OdooNoConfiguradoError):
        await caso.ejecutar("pedido-1", RESTAURANTE)


@pytest.mark.asyncio
async def test_webhook_actualiza_la_factura_releyendo_odoo():
    facturas = FacturasEnMemoria(_factura())
    caso = ActualizarFacturaDesdeOdooUseCase(
        OdooFalso(estado=EstadoFactura.AUTORIZADA), facturas
    )

    factura = await caso.ejecutar(10)

    assert factura.estado == EstadoFactura.AUTORIZADA
    # Una factura de Odoo que no salió de KITCHAN se ignora.
    assert await caso.ejecutar(999) is None


@pytest.mark.asyncio
async def test_conciliacion_sigue_aunque_una_factura_falle():
    odoo = OdooFalso(estado=EstadoFactura.AUTORIZADA)
    odoo.fallar_en = {10}
    facturas = FacturasEnMemoria(
        _factura("pedido-1", 10),
        _factura("pedido-2", 20),
        _factura("pedido-3", 30, estado=EstadoFactura.AUTORIZADA),
    )

    actualizadas = await ConciliarFacturasPendientesUseCase(odoo, facturas).ejecutar()

    assert actualizadas == 1
    assert odoo.reenvios == [20]
    assert facturas.facturas["pedido-1"].estado == EstadoFactura.PENDIENTE_SRI


# ------------------------------------------------------------ adaptador JSON-2


@pytest.fixture
def odoo_env(monkeypatch):
    valores = {
        "ODOO_URL": "https://odoo.test/",
        "ODOO_DB": "base-prueba",
        "ODOO_API_KEY": "clave-de-prueba",
        "ODOO_DIARIO_ID": "8",
        "ODOO_CLIENTE_ID": "7",
        "ODOO_PRODUCTO_ID": "1367",
        "ODOO_IMPUESTO_ID": "3",
        "ODOO_PAGO_SRI_ID": "7",
    }
    for variable, valor in valores.items():
        monkeypatch.setenv(variable, valor)


FACTURA_PUBLICADA = {
    "id": 4600,
    "name": "Fact 001-020-000001517",
    "state": "posted",
    "amount_total": 8.51,
    "edi_state": "to_send",
    "edi_error_message": False,
    "edi_blocking_level": False,
    "l10n_ec_authorization_number": False,
    "l10n_ec_authorization_date": False,
}


def _odoo_simulado(existentes: list, falla_envio: bool = False):
    llamadas: list[tuple[str, dict]] = []

    def responder(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "bearer clave-de-prueba"
        assert request.headers["X-Odoo-Database"] == "base-prueba"
        ruta = request.url.path.removeprefix("/json/2/")
        cuerpo = json.loads(request.content)
        llamadas.append((ruta, cuerpo))
        respuestas = {
            "account.move/search_read": existentes,
            "account.tax/read": [{"id": 3, "amount": 15.0}],
            "account.move/create": [4600],
            "account.move/action_post": False,
            "account.move/action_process_edi_web_services": None,
            "account.move/read": [FACTURA_PUBLICADA],
        }
        if falla_envio and ruta == "account.move/action_process_edi_web_services":
            return httpx.Response(
                500,
                json={
                    "message": "Password was given but private key is not encrypted."
                },
            )
        return httpx.Response(200, json=respuestas[ruta])

    return httpx.AsyncClient(transport=httpx.MockTransport(responder)), llamadas


DATOS = DatosFactura(
    referencia="KITCHAN-pedido-1",
    origen="RAPPI RAPPI-ABC",
    lineas=[LineaFactura(descripcion="Hamburguesa", cantidad=2, precio_con_iva=4.25)],
)


@pytest.mark.asyncio
async def test_adaptador_crea_publica_y_envia_la_factura(odoo_env):
    cliente, llamadas = _odoo_simulado(existentes=[])

    resultado = await OdooJson2Adapter(http_client=cliente).emitir_factura(DATOS)

    assert [ruta for ruta, _ in llamadas] == [
        "account.move/search_read",
        "account.tax/read",
        "account.move/create",
        "account.move/action_post",
        "account.move/action_process_edi_web_services",
        "account.move/read",
    ]
    factura = llamadas[2][1]["vals_list"][0]
    assert factura["journal_id"] == 8
    assert factura["partner_id"] == 7
    assert factura["l10n_ec_sri_payment_id"] == 7
    assert factura["ref"] == "KITCHAN-pedido-1"
    linea = factura["invoice_line_ids"][0][2]
    # 4.25 con IVA 15 % incluido -> 3.70 sin IVA.
    assert linea["price_unit"] == 3.70
    assert linea["quantity"] == 2
    assert linea["tax_ids"] == [[6, 0, [3]]]
    assert resultado.odoo_move_id == 4600
    assert resultado.numero == "Fact 001-020-000001517"
    assert resultado.estado == EstadoFactura.PENDIENTE_SRI


@pytest.mark.asyncio
async def test_adaptador_no_duplica_una_factura_que_ya_existe(odoo_env):
    cliente, llamadas = _odoo_simulado(existentes=[{"id": 4600, "state": "posted"}])

    await OdooJson2Adapter(http_client=cliente).emitir_factura(DATOS)

    rutas = [ruta for ruta, _ in llamadas]
    assert "account.move/create" not in rutas
    assert "account.move/action_post" not in rutas


@pytest.mark.asyncio
async def test_adaptador_marca_error_si_odoo_no_puede_enviar_al_sri(odoo_env):
    cliente, _ = _odoo_simulado(
        existentes=[{"id": 4600, "state": "posted"}], falla_envio=True
    )

    resultado = await OdooJson2Adapter(http_client=cliente).emitir_factura(DATOS)

    assert resultado.estado == EstadoFactura.CON_ERROR
    assert "private key is not encrypted" in resultado.mensaje_error


@pytest.mark.asyncio
async def test_adaptador_avisa_si_odoo_rechaza_la_api_key(odoo_env):
    cliente = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(401, json={"message": "Invalid apikey"})
        )
    )

    with pytest.raises(OdooError, match="API key"):
        await OdooJson2Adapter(http_client=cliente).consultar_factura(4600)


def test_adaptador_sin_variables_no_esta_configurado(monkeypatch):
    for variable in ("ODOO_URL", "ODOO_API_KEY", "ODOO_DIARIO_ID"):
        monkeypatch.delenv(variable, raising=False)

    assert OdooJson2Adapter().configurado() is False


def test_traduce_los_estados_de_odoo():
    autorizada = a_resultado(
        FACTURA_PUBLICADA
        | {
            "edi_state": "sent",
            "l10n_ec_authorization_number": "2709202601179320399600120010200000015003121521413",
            "l10n_ec_authorization_date": "2026-09-28 22:07:50",
        }
    )
    assert autorizada.estado == EstadoFactura.AUTORIZADA
    assert autorizada.fecha_autorizacion == datetime(
        2026, 9, 28, 22, 7, 50, tzinfo=timezone.utc
    )

    rechazada = a_resultado(
        FACTURA_PUBLICADA
        | {
            "edi_blocking_level": "error",
            "edi_error_message": "<p>35 - ARCHIVO NO CUMPLE ESTRUCTURA XML</p>",
        }
    )
    assert rechazada.estado == EstadoFactura.CON_ERROR
    assert rechazada.mensaje_error == "35 - ARCHIVO NO CUMPLE ESTRUCTURA XML"

    assert a_resultado(FACTURA_PUBLICADA | {"state": "draft"}).estado == (
        EstadoFactura.CON_ERROR
    )
    assert a_resultado(FACTURA_PUBLICADA | {"state": "cancel"}).estado == (
        EstadoFactura.ANULADA
    )


# --------------------------------------------------------------------- API


class ActualizarFalso:
    def __init__(self):
        self.ids: list[int] = []

    async def ejecutar(self, odoo_move_id):
        self.ids.append(odoo_move_id)


@pytest.mark.asyncio
async def test_webhook_de_odoo_rechaza_un_token_invalido(client, monkeypatch):
    monkeypatch.setenv("ODOO_WEBHOOK_TOKEN", "token-secreto")
    falso = ActualizarFalso()
    app.dependency_overrides[get_actualizar_use_case] = lambda: falso

    respuesta = await client.post(
        "/api/v1/facturacion/odoo/webhook/otro-token",
        json={"_model": "account.move", "_id": 4600},
    )

    assert respuesta.status_code == 404
    assert falso.ids == []


@pytest.mark.asyncio
async def test_webhook_de_odoo_sin_token_configurado_se_rechaza(client, monkeypatch):
    monkeypatch.delenv("ODOO_WEBHOOK_TOKEN", raising=False)
    falso = ActualizarFalso()
    app.dependency_overrides[get_actualizar_use_case] = lambda: falso

    respuesta = await client.post(
        "/api/v1/facturacion/odoo/webhook/", json={"_model": "account.move"}
    )

    assert respuesta.status_code == 404
    assert falso.ids == []


@pytest.mark.asyncio
async def test_webhook_de_odoo_actualiza_la_factura(client, monkeypatch):
    monkeypatch.setenv("ODOO_WEBHOOK_TOKEN", "token-secreto")
    falso = ActualizarFalso()
    app.dependency_overrides[get_actualizar_use_case] = lambda: falso

    respuesta = await client.post(
        "/api/v1/facturacion/odoo/webhook/token-secreto",
        json={"_model": "account.move", "_id": 4600, "edi_state": "sent"},
    )

    assert respuesta.status_code == 200
    assert falso.ids == [4600]


@pytest.mark.asyncio
async def test_facturar_requiere_sesion(client):
    respuesta = await client.post("/api/v1/facturacion/pedidos/pedido-1")

    assert respuesta.status_code in (401, 403)
