"""Actividad del personal: último acceso, quién aceptó cada pedido y código de
recuperación enviado por un administrador."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from src.kitchan.core.contexto_usuario import fijar_usuario_actual, usuario_actual_id
from src.kitchan.modules.reportes.application.actividad_usuarios import (
    ObtenerActividadUsuariosUseCase,
)
from src.kitchan.modules.reportes.domain.entities import ItemResumen, PedidoResumen
from src.kitchan.modules.reportes.domain.ports import PedidosLecturaPort
from src.kitchan.modules.usuarios.application.ports import IEnviadorCorreo
from src.kitchan.modules.usuarios.infrastructure import rest_api as usuarios_api

UTC = timezone.utc
QUITO = timezone(timedelta(hours=-5))
AHORA = datetime(2026, 10, 8, 20, 0, tzinfo=UTC)


class PedidosFalsos(PedidosLecturaPort):
    def __init__(self, pedidos):
        self.pedidos = pedidos

    async def listar_desde(self, restaurante_id, desde):
        return [p for p in self.pedidos if p.fecha_creacion >= desde]


def _pedido(por, origen="RAPPI", minutos=6, estado="ENTREGADA", hora=17, total=10.0):
    creado = datetime(2026, 10, 8, hora, 0, tzinfo=UTC)
    return PedidoResumen(
        origen=origen,
        total=total,
        estado=estado,
        fecha_creacion=creado,
        fecha_aceptacion=creado,
        fecha_lista=creado + timedelta(minutes=minutos),
        cliente="Ana",
        items=(ItemResumen("Brownie", 1, total),),
        aceptado_por_id=por,
    )


def _use_case(pedidos):
    return ObtenerActividadUsuariosUseCase(
        PedidosFalsos(pedidos), zona=QUITO, ahora=lambda: AHORA
    )


@pytest.mark.asyncio
async def test_reparte_los_pedidos_entre_quienes_los_aceptaron():
    use_case = _use_case(
        [
            _pedido("ana", minutos=4),
            _pedido("ana", minutos=8),
            _pedido("ana", estado="CANCELADA"),
            _pedido("luis", minutos=15, total=20.0),
            _pedido(None),  # lo aceptó el sistema o es anterior al registro
        ]
    )

    datos = await use_case.ejecutar("rest-1", "hoy")

    por_usuario = {u["usuario_id"]: u for u in datos["usuarios"]}
    assert [u["usuario_id"] for u in datos["usuarios"]] == ["ana", "luis"]
    assert por_usuario["ana"]["pedidos_atendidos"] == 3
    assert por_usuario["ana"]["pedidos_cancelados"] == 1
    assert por_usuario["ana"]["tiempo_promedio_minutos"] == 6.0
    assert por_usuario["ana"]["ventas"] == 20.0
    assert por_usuario["luis"]["tasa_demora"] == 100.0  # 15 min > 10
    assert datos["sin_atribuir"] == 1
    assert "detalle" not in datos


@pytest.mark.asyncio
async def test_el_detalle_de_un_usuario_trae_canales_y_ultimos_pedidos():
    use_case = _use_case(
        [
            _pedido("ana", origen="RAPPI", hora=15),
            _pedido("ana", origen="RAPPI", hora=16),
            _pedido("ana", origen="UBER_EATS", hora=17),
            _pedido("luis", origen="PEDIDOS_YA"),
        ]
    )

    datos = await use_case.ejecutar("rest-1", "hoy", usuario_id="ana")

    detalle = datos["detalle"]
    assert detalle["pedidos_atendidos"] == 3
    assert detalle["por_canal"] == [
        {"canal": "RAPPI", "pedidos": 2},
        {"canal": "UBER_EATS", "pedidos": 1},
    ]
    # El más reciente primero.
    assert [r["canal"] for r in detalle["recientes"]] == ["UBER_EATS", "RAPPI", "RAPPI"]
    assert detalle["recientes"][0]["minutos_preparacion"] == 6.0


@pytest.mark.asyncio
async def test_un_usuario_sin_actividad_devuelve_ceros():
    datos = await _use_case([_pedido("luis")]).ejecutar("rest-1", "hoy", usuario_id="ana")

    assert datos["detalle"]["pedidos_atendidos"] == 0
    assert datos["detalle"]["recientes"] == []
    assert datos["detalle"]["ultima_actividad"] is None


# ---------- API ----------


class CorreoFalso(IEnviadorCorreo):
    def __init__(self):
        self.enviados = []

    async def enviar_codigo_recuperacion(self, destinatario, nombre, codigo, minutos_validez):
        self.enviados.append(destinatario)


@pytest.fixture
def correo(monkeypatch):
    falso = CorreoFalso()
    monkeypatch.setattr(usuarios_api, "construir_enviador_correo", lambda: falso)
    return falso


async def _restaurante(client, sufijo, ruc):
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
            "nombre": f"Admin {sufijo}",
            "email": f"admin{sufijo}@local.com",
            "password": "Password123*",
        },
    }
    res = await client.post("/api/v1/onboarding/", json=payload)
    assert res.status_code == 201
    login = await client.post(
        "/api/v1/usuarios/login",
        json={"email": payload["admin"]["email"], "password": "Password123*"},
    )
    datos = login.json()
    return datos["usuario"], {"Authorization": f"Bearer {datos['access_token']}"}


async def _operador(client, restaurante_id, headers, email="op@local.com"):
    res = await client.post(
        f"/api/v1/usuarios/restaurante/{restaurante_id}",
        json={"nombre": "Operador", "email": email, "password": "Password123*", "rol": "OPERADOR"},
        headers=headers,
    )
    assert res.status_code == 201
    return res.json()


@pytest.mark.asyncio
async def test_el_login_guarda_el_ultimo_acceso(client):
    admin, headers = await _restaurante(client, "A", "1790000000011")
    operador = await _operador(client, admin["restaurante_id"], headers)
    assert operador["ultimo_acceso"] is None
    assert operador["creado_en"] is not None

    await client.post(
        "/api/v1/usuarios/login", json={"email": "op@local.com", "password": "Password123*"}
    )
    lista = await client.get(
        f"/api/v1/usuarios/restaurante/{admin['restaurante_id']}", headers=headers
    )

    por_email = {u["email"]: u for u in lista.json()}
    assert por_email["op@local.com"]["ultimo_acceso"] is not None
    assert por_email["adminA@local.com"]["ultimo_acceso"] is not None


@pytest.mark.asyncio
async def test_la_autenticacion_deja_el_usuario_disponible_para_los_adaptadores(client):
    admin, headers = await _restaurante(client, "B", "1790000000012")
    fijar_usuario_actual(None)

    await client.get("/api/v1/usuarios/", headers=headers)

    assert usuario_actual_id() == admin["id"]


@pytest.mark.asyncio
async def test_el_repositorio_guarda_quien_acepto_el_pedido(client, db_session):
    from src.kitchan.modules.pedidos.domain.entities import EstadoPedido, Pedido
    from src.kitchan.modules.pedidos.infrastructure.repository import (
        PostgresPedidoRepository,
    )

    admin, _ = await _restaurante(client, "C", "1790000000013")
    repo = PostgresPedidoRepository(db_session)
    pedido = await repo.guardar(
        Pedido(
            restaurante_id=admin["restaurante_id"],
            origen="RAPPI",
            id_externo="R-1",
            cliente="Ana",
            items=[],
            total=5.0,
            id=str(uuid.uuid4()),
        )
    )

    fijar_usuario_actual(admin["id"])
    await repo.actualizar_estado(pedido.id, EstadoPedido.EN_PREPARACION)
    # Si otra persona lo marca listo después, el que aceptó no cambia.
    fijar_usuario_actual("otro")
    await repo.actualizar_estado(pedido.id, EstadoPedido.LISTA)

    guardado = await repo.buscar_por_id(pedido.id)
    assert guardado.aceptado_por_id == admin["id"]
    fijar_usuario_actual(None)


@pytest.mark.asyncio
async def test_endpoint_de_actividad_solo_para_administradores(client):
    admin, headers = await _restaurante(client, "D", "1790000000014")
    await _operador(client, admin["restaurante_id"], headers)
    login = await client.post(
        "/api/v1/usuarios/login", json={"email": "op@local.com", "password": "Password123*"}
    )
    headers_op = {"Authorization": f"Bearer {login.json()['access_token']}"}

    ok = await client.get("/api/v1/reportes/usuarios/actividad?rango=7d", headers=headers)
    prohibido = await client.get("/api/v1/reportes/usuarios/actividad", headers=headers_op)
    detalle = await client.get(
        f"/api/v1/reportes/usuarios/{admin['id']}/actividad", headers=headers
    )

    assert ok.status_code == 200 and ok.json()["usuarios"] == []
    assert prohibido.status_code == 403
    assert detalle.status_code == 200
    assert detalle.json()["detalle"]["pedidos_atendidos"] == 0


@pytest.mark.asyncio
async def test_un_admin_envia_el_codigo_a_un_usuario_de_su_restaurante(client, correo):
    admin, headers = await _restaurante(client, "E", "1790000000015")
    operador = await _operador(client, admin["restaurante_id"], headers)

    res = await client.post(
        f"/api/v1/usuarios/{operador['id']}/codigo-recuperacion", headers=headers
    )

    assert res.status_code == 200
    assert correo.enviados == ["op@local.com"]
    # Una segunda orden inmediata no reenvía: queda la espera de un minuto.
    otra = await client.post(
        f"/api/v1/usuarios/{operador['id']}/codigo-recuperacion", headers=headers
    )
    assert otra.status_code == 429
    assert len(correo.enviados) == 1


@pytest.mark.asyncio
async def test_no_se_envia_codigo_a_usuarios_de_otro_restaurante_ni_desactivados(
    client, correo
):
    admin_a, headers_a = await _restaurante(client, "F", "1790000000016")
    admin_b, headers_b = await _restaurante(client, "G", "1790000000017")
    operador_b = await _operador(client, admin_b["restaurante_id"], headers_b, "opb@local.com")

    ajeno = await client.post(
        f"/api/v1/usuarios/{operador_b['id']}/codigo-recuperacion", headers=headers_a
    )
    assert ajeno.status_code == 404

    operador_a = await _operador(client, admin_a["restaurante_id"], headers_a, "opa@local.com")
    await client.patch(
        f"/api/v1/usuarios/{operador_a['id']}/estado", json={"estado": False}, headers=headers_a
    )
    inactivo = await client.post(
        f"/api/v1/usuarios/{operador_a['id']}/codigo-recuperacion", headers=headers_a
    )
    assert inactivo.status_code == 400
    assert correo.enviados == []
