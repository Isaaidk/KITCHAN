"""Los errores de una plataforma externa no deben responderse como 401: el
frontend interpreta 401 como "sesión de KITCHAN vencida" y cierra la sesión
del usuario. Se prueba con casos de uso falsos que imitan cada falla."""

import uuid

import pytest
from fastapi import HTTPException

from src.kitchan.main import app
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

RESTAURANTE = str(uuid.uuid4())


class CasoDeUsoQueFalla:
    def __init__(self, error: Exception):
        self.error = error

    def __getattr__(self, nombre):
        async def accion(*args, **kwargs):
            raise self.error

        return accion


@pytest.fixture
def headers():
    token = JWTTokenGenerator().generar_token(
        {
            "sub": "op@test.com",
            "id": "1",
            "rol": "OPERADOR",
            "restaurante_id": RESTAURANTE,
        }
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def _limpiar_overrides():
    yield
    for modulo in (uber_orders_api, rappi_orders_api):
        app.dependency_overrides.pop(modulo.get_order_use_case, None)


async def _crear_pedido(db_session, origen, id_externo):
    await PostgresPedidoRepository(session=db_session).guardar(
        Pedido(
            restaurante_id=RESTAURANTE,
            origen=origen,
            id_externo=id_externo,
            cliente="Cliente",
            items=[PedidoItem(nombre="Papas", cantidad=1, precio_unitario=5.0)],
            total=5.0,
            estado=EstadoPedido.NUEVA,
        )
    )


@pytest.mark.asyncio
async def test_uber_sin_token_responde_409_y_no_401(client, db_session, headers):
    await _crear_pedido(db_session, "UBER_EATS", "U-ERR-1")
    app.dependency_overrides[uber_orders_api.get_order_use_case] = (
        lambda: CasoDeUsoQueFalla(ValueError("Token de Uber expirado o no encontrado."))
    )

    respuesta = await client.post(
        f"/api/v1/integraciones/uber/orders/U-ERR-1/accept?restaurante_id={RESTAURANTE}",
        headers=headers,
    )

    assert respuesta.status_code == 409
    assert "Integraciones" in respuesta.json()["detail"]


@pytest.mark.asyncio
async def test_uber_rechaza_credenciales_responde_502(client, db_session, headers):
    await _crear_pedido(db_session, "UBER_EATS", "U-ERR-2")
    app.dependency_overrides[uber_orders_api.get_order_use_case] = (
        lambda: CasoDeUsoQueFalla(
            HTTPException(
                status_code=401, detail="User not allowed to access the store"
            )
        )
    )

    respuesta = await client.post(
        f"/api/v1/integraciones/uber/orders/U-ERR-2/ready?restaurante_id={RESTAURANTE}",
        headers=headers,
    )

    assert respuesta.status_code == 502
    assert (
        respuesta.json()["detail"]["respuesta"]
        == "User not allowed to access the store"
    )


@pytest.mark.asyncio
async def test_rappi_sin_credenciales_responde_502(client, db_session, headers):
    await _crear_pedido(db_session, "RAPPI", "R-ERR-1")
    app.dependency_overrides[rappi_orders_api.get_order_use_case] = (
        lambda: CasoDeUsoQueFalla(
            HTTPException(
                status_code=401, detail="Credenciales de Rappi no configuradas."
            )
        )
    )

    respuesta = await client.post(
        "/api/v1/integraciones/rappi/orders/R-ERR-1/accept", headers=headers
    )

    assert respuesta.status_code == 502


@pytest.mark.asyncio
async def test_otros_errores_de_la_plataforma_se_mantienen(client, db_session, headers):
    """Un 404 de Uber (orden inexistente en Uber) no se transforma."""
    await _crear_pedido(db_session, "UBER_EATS", "U-ERR-3")
    app.dependency_overrides[uber_orders_api.get_order_use_case] = (
        lambda: CasoDeUsoQueFalla(
            HTTPException(status_code=404, detail="Order not found")
        )
    )

    respuesta = await client.post(
        f"/api/v1/integraciones/uber/orders/U-ERR-3/accept?restaurante_id={RESTAURANTE}",
        headers=headers,
    )

    assert respuesta.status_code == 404
