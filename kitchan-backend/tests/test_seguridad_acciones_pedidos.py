"""Tests de seguridad de las acciones del KDS sobre pedidos de integraciones
(Uber, PedidosYa y Rappi): exigen sesión y que el pedido sea del restaurante
del usuario. Las llamadas a las plataformas se reemplazan por casos de uso
falsos, así que ningún test sale a la red.
"""

import uuid

import pytest

from src.kitchan.main import app
from src.kitchan.modules.integraciones.pedidosya.infrastructure.controllers import (
    orders_api as pedidosya_orders_api,
)
from src.kitchan.modules.integraciones.rappi.infrastructure.controllers import (
    orders_api as rappi_orders_api,
)
from src.kitchan.modules.integraciones.uber.infrastructure.controllers import (
    orders_api as uber_orders_api,
)
from src.kitchan.modules.pedidos.domain.entities import EstadoPedido, Pedido, PedidoItem
from src.kitchan.modules.pedidos.infrastructure.repository import (
    PostgresPedidoRepository,
)
from src.kitchan.modules.usuarios.infrastructure.security import JWTTokenGenerator

RESTAURANTE_A = str(uuid.uuid4())
RESTAURANTE_B = str(uuid.uuid4())


class CasoDeUsoFalso:
    """Acepta cualquier acción sin llamar a la plataforma externa."""

    def __getattr__(self, nombre):
        async def accion(*args, **kwargs):
            return True

        return accion


@pytest.fixture(autouse=True)
def _casos_de_uso_falsos():
    for modulo in (uber_orders_api, pedidosya_orders_api, rappi_orders_api):
        app.dependency_overrides[modulo.get_order_use_case] = lambda: CasoDeUsoFalso()
    yield
    for modulo in (uber_orders_api, pedidosya_orders_api, rappi_orders_api):
        app.dependency_overrides.pop(modulo.get_order_use_case, None)


def _headers(restaurante_id: str) -> dict:
    token = JWTTokenGenerator().generar_token(
        {
            "sub": "operador@test.com",
            "id": str(uuid.uuid4()),
            "rol": "OPERADOR",
            "restaurante_id": restaurante_id,
        }
    )
    return {"Authorization": f"Bearer {token}"}


async def _crear_pedido(db_session, origen: str, id_externo: str, restaurante_id: str):
    await PostgresPedidoRepository(session=db_session).guardar(
        Pedido(
            restaurante_id=restaurante_id,
            origen=origen,
            id_externo=id_externo,
            cliente="Cliente Test",
            items=[PedidoItem(nombre="Papas", cantidad=1, precio_unitario=5.0)],
            total=5.0,
            estado=EstadoPedido.NUEVA,
        )
    )


# ============================================================
# PedidosYa
# ============================================================
@pytest.mark.asyncio
async def test_pedidosya_sin_sesion_retorna_401(client):
    for accion in ("accept", "ready"):
        respuesta = await client.post(
            f"/api/v1/integraciones/pedidosya/orders/PY-1/{accion}"
        )
        assert respuesta.status_code == 401


@pytest.mark.asyncio
async def test_pedidosya_pedido_de_otro_restaurante_retorna_404(client, db_session):
    await _crear_pedido(db_session, "PEDIDOS_YA", "PY-2", RESTAURANTE_A)

    respuesta = await client.post(
        "/api/v1/integraciones/pedidosya/orders/PY-2/accept",
        headers=_headers(RESTAURANTE_B),
    )

    assert respuesta.status_code == 404


@pytest.mark.asyncio
async def test_pedidosya_duenio_del_pedido_puede_operarlo(client, db_session):
    await _crear_pedido(db_session, "PEDIDOS_YA", "PY-3", RESTAURANTE_A)

    respuesta = await client.post(
        "/api/v1/integraciones/pedidosya/orders/PY-3/accept",
        headers=_headers(RESTAURANTE_A),
    )

    assert respuesta.status_code == 200


# ============================================================
# Rappi
# ============================================================
@pytest.mark.asyncio
async def test_rappi_pedido_de_otro_restaurante_retorna_404(client, db_session):
    await _crear_pedido(db_session, "RAPPI", "R-10", RESTAURANTE_A)

    respuesta = await client.post(
        "/api/v1/integraciones/rappi/orders/R-10/deny",
        json={"cancel_type": "ITEM_OUT_OF_STOCK", "reason": "Sin stock"},
        headers=_headers(RESTAURANTE_B),
    )

    assert respuesta.status_code == 404


# ============================================================
# Uber
# ============================================================
@pytest.mark.asyncio
async def test_uber_sin_sesion_retorna_401(client):
    respuesta = await client.post(
        f"/api/v1/integraciones/uber/orders/U-1/accept?restaurante_id={RESTAURANTE_A}"
    )
    assert respuesta.status_code == 401


@pytest.mark.asyncio
async def test_uber_pedido_de_otro_restaurante_retorna_404(client, db_session):
    await _crear_pedido(db_session, "UBER_EATS", "U-2", RESTAURANTE_A)

    respuesta = await client.post(
        f"/api/v1/integraciones/uber/orders/U-2/accept?restaurante_id={RESTAURANTE_B}",
        headers=_headers(RESTAURANTE_B),
    )

    assert respuesta.status_code == 404


@pytest.mark.asyncio
async def test_uber_restaurante_id_ajeno_retorna_403(client, db_session):
    """El pedido es del usuario, pero pide operar con el token de Uber de
    otro restaurante pasando un restaurante_id ajeno en la URL."""
    await _crear_pedido(db_session, "UBER_EATS", "U-3", RESTAURANTE_A)

    respuesta = await client.post(
        f"/api/v1/integraciones/uber/orders/U-3/accept?restaurante_id={RESTAURANTE_B}",
        headers=_headers(RESTAURANTE_A),
    )

    assert respuesta.status_code == 403


@pytest.mark.asyncio
async def test_uber_duenio_del_pedido_puede_operarlo(client, db_session):
    await _crear_pedido(db_session, "UBER_EATS", "U-4", RESTAURANTE_A)

    respuesta = await client.post(
        f"/api/v1/integraciones/uber/orders/U-4/ready?restaurante_id={RESTAURANTE_A}",
        headers=_headers(RESTAURANTE_A),
    )

    assert respuesta.status_code == 200
