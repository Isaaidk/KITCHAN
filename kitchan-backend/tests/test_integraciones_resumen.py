"""Datos de la pantalla de Integraciones: actividad de cada canal y resumen de facturación."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from src.kitchan.modules.facturacion.application.resumen_facturacion import (
    ObtenerResumenFacturacionUseCase,
)
from src.kitchan.modules.facturacion.domain.entities import EstadoFactura, FacturaPedido
from src.kitchan.modules.facturacion.domain.ports import FacturaRepositoryPort
from src.kitchan.modules.facturacion.infrastructure.models import FacturaPedidoModel
from src.kitchan.modules.reportes.application.actividad_canales import (
    ObtenerActividadCanalesUseCase,
)
from src.kitchan.modules.reportes.domain.entities import PedidoResumen
from src.kitchan.modules.reportes.domain.ports import PedidosLecturaPort

UTC = timezone.utc
QUITO = timezone(timedelta(hours=-5))
# 08/10/2026 15:00 hora de Guayaquil
AHORA = datetime(2026, 10, 8, 20, 0, tzinfo=UTC)


class PedidosFalsos(PedidosLecturaPort):
    def __init__(self, pedidos):
        self.pedidos = pedidos

    async def listar_desde(self, restaurante_id, desde):
        return [p for p in self.pedidos if p.fecha_creacion >= desde]


def _pedido(origen, creado):
    return PedidoResumen(
        origen=origen, total=10.0, estado="ENTREGADA", fecha_creacion=creado
    )


@pytest.mark.asyncio
async def test_actividad_de_canales_cuenta_hoy_y_recuerda_el_ultimo_pedido():
    use_case = ObtenerActividadCanalesUseCase(
        PedidosFalsos(
            [
                _pedido("RAPPI", datetime(2026, 10, 8, 18, 0, tzinfo=UTC)),
                _pedido("RAPPI", datetime(2026, 10, 8, 19, 30, tzinfo=UTC)),
                _pedido("RAPPI", datetime(2026, 10, 5, 12, 0, tzinfo=UTC)),
                _pedido("PEDIDOSYA", datetime(2026, 10, 3, 12, 0, tzinfo=UTC)),
                # Antes de las 00:00 de hoy en Guayaquil (05:00 UTC): cuenta como ayer.
                _pedido("UBER_EATS", datetime(2026, 10, 8, 4, 30, tzinfo=UTC)),
                # Fuera de los 30 días.
                _pedido("LOCAL", datetime(2026, 8, 1, 12, 0, tzinfo=UTC)),
            ]
        ),
        zona=QUITO,
        ahora=lambda: AHORA,
    )

    canales = {c["canal"]: c for c in await use_case.ejecutar("rest-1")}

    assert canales["RAPPI"]["pedidos_hoy"] == 2
    assert canales["RAPPI"]["pedidos_30d"] == 3
    assert canales["RAPPI"]["ultimo_pedido"].startswith("2026-10-08T19:30")
    # PedidosYa se acepta con las dos grafías y queda con una sola.
    assert canales["PEDIDOS_YA"]["pedidos_hoy"] == 0
    assert canales["PEDIDOS_YA"]["pedidos_30d"] == 1
    assert canales["UBER_EATS"]["pedidos_hoy"] == 0
    assert "LOCAL" not in canales


class FacturasFalsas(FacturaRepositoryPort):
    def __init__(self, facturas):
        self.facturas = facturas

    async def guardar(self, factura):
        raise NotImplementedError

    async def buscar_por_pedido(self, pedido_id):
        return None

    async def buscar_por_odoo_move(self, odoo_move_id):
        return None

    async def listar_pendientes(self):
        return []

    async def listar_por_restaurante(self, restaurante_id):
        return self.facturas


def _factura(estado, total=10.0, autorizada_en=None, actualizada_en=None):
    return FacturaPedido(
        pedido_id=str(uuid.uuid4()),
        restaurante_id="r",
        odoo_move_id=1,
        estado=estado,
        total=total,
        fecha_autorizacion=autorizada_en,
        fecha_actualizacion=actualizada_en,
    )


@pytest.mark.asyncio
async def test_resumen_de_facturacion_cuenta_por_estado():
    t1 = datetime(2026, 10, 7, 10, 0, tzinfo=UTC)
    t2 = datetime(2026, 10, 8, 10, 0, tzinfo=UTC)
    use_case = ObtenerResumenFacturacionUseCase(
        FacturasFalsas(
            [
                _factura(
                    EstadoFactura.AUTORIZADA, 12.5, autorizada_en=t1, actualizada_en=t1
                ),
                _factura(
                    EstadoFactura.AUTORIZADA, 7.5, autorizada_en=t2, actualizada_en=t2
                ),
                _factura(EstadoFactura.PENDIENTE_SRI),
                _factura(EstadoFactura.CON_ERROR),
                _factura(EstadoFactura.ANULADA),
            ]
        )
    )

    resumen = await use_case.ejecutar("r")

    assert resumen["total"] == 5
    assert resumen["autorizadas"] == 2
    assert resumen["pendientes_sri"] == 1
    assert resumen["con_error"] == 1
    assert resumen["anuladas"] == 1
    assert resumen["monto_autorizado"] == 20.0
    assert resumen["ultima_autorizacion"].startswith("2026-10-08T10:00")


@pytest.mark.asyncio
async def test_resumen_sin_facturas_devuelve_ceros():
    resumen = await ObtenerResumenFacturacionUseCase(FacturasFalsas([])).ejecutar("r")

    assert resumen["total"] == 0
    assert resumen["ultima_autorizacion"] is None
    assert resumen["ultima_novedad"] is None


# ---------- API ----------


async def _admin(client, sufijo="A", ruc="1790000000031"):
    payload = {
        "restaurante": {
            "nombre_comercial": f"Local {sufijo}",
            "razon_social": f"Local {sufijo} S.A.",
            "identificacion_fiscal": ruc,
            "direccion": "Av Principal",
            "telefono": "0999999999",
            "email_corporativo": f"info{sufijo}@local.com",
        },
        "admin": {
            "nombre": "Admin",
            "email": f"admin{sufijo}@local.com",
            "password": "Password123*",
        },
    }
    assert (await client.post("/api/v1/onboarding/", json=payload)).status_code == 201
    login = await client.post(
        "/api/v1/usuarios/login",
        json={"email": payload["admin"]["email"], "password": "Password123*"},
    )
    datos = login.json()
    return datos["usuario"], {"Authorization": f"Bearer {datos['access_token']}"}


@pytest.mark.asyncio
async def test_endpoints_de_integraciones_responden_para_el_administrador(
    client, db_session
):
    admin, headers = await _admin(client)
    db_session.add(
        FacturaPedidoModel(
            pedido_id=uuid.uuid4(),
            restaurante_id=uuid.UUID(admin["restaurante_id"]),
            odoo_move_id=77,
            estado=EstadoFactura.AUTORIZADA,
            total=15.0,
            fecha_autorizacion=datetime.now(UTC),
        )
    )
    await db_session.commit()

    facturacion = await client.get("/api/v1/facturacion/resumen", headers=headers)
    canales = await client.get("/api/v1/reportes/canales/actividad", headers=headers)

    assert facturacion.status_code == 200
    assert facturacion.json()["autorizadas"] == 1
    assert facturacion.json()["monto_autorizado"] == 15.0
    assert canales.status_code == 200
    assert canales.json() == []


@pytest.mark.asyncio
async def test_endpoints_de_integraciones_exigen_administrador(client):
    sin_sesion = await client.get("/api/v1/facturacion/resumen")
    sin_sesion_canales = await client.get("/api/v1/reportes/canales/actividad")

    assert sin_sesion.status_code == 401
    assert sin_sesion_canales.status_code == 401
