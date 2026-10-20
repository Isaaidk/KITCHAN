"""Tests HTTP del endpoint de dispatch de PedidosYa (equivalente,
arquitectónicamente, al webhook de Uber): recepción de pedido válido,
idempotencia ante reenvíos duplicados, JWT ausente/inválido y payload
malformado/incompleto. No se llama a la API real de PedidosYa: el mapeo de
vendor se mockea vía dependency override y las acciones salientes ni
siquiera se ejercitan en este endpoint (solo recibe pedidos).
"""

import json

import pytest
from fastapi import Depends
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from src.kitchan.core.database import get_db
from src.kitchan.main import app
from src.kitchan.modules.integraciones.pedidosya.application.order_dispatch_use_case import (
    PedidosYaOrderDispatchUseCase,
)
from src.kitchan.modules.integraciones.pedidosya.domain.ports import (
    PedidosYaVendorMappingPort,
)
from src.kitchan.modules.integraciones.pedidosya.infrastructure.controllers.order_dispatch_api import (
    get_order_dispatch_use_case,
    get_vendor_mapping,
)
from src.kitchan.modules.pedidos.application.actualizar_estado_pedido_service import (
    ActualizarEstadoPedidoUseCase,
)
from src.kitchan.modules.pedidos.application.crear_pedido_service import (
    CrearPedidoUseCase,
)
from src.kitchan.modules.pedidos.application.ports import NotificadorEventosPort
from src.kitchan.modules.pedidos.domain.entities import Pedido
from src.kitchan.modules.pedidos.infrastructure.adapters.integraciones_dispatcher import (
    PedidosIntegracionesAdapter,
)
from src.kitchan.modules.pedidos.infrastructure.repository import (
    PostgresPedidoRepository,
)

JWT_SECRET_TEST = "secreto-de-test"
RESTAURANTE_ID_TEST = "11111111-1111-1111-1111-111111111111"
REMOTE_ID_TEST = "POS_RESTAURANT_0001"


class FakeVendorMapping(PedidosYaVendorMappingPort):
    """Reemplaza a EnvPedidosYaVendorMappingAdapter en tests."""

    async def get_restaurante_id(self, remote_id: str):
        return RESTAURANTE_ID_TEST if remote_id == REMOTE_ID_TEST else None


class NotificadorFake(NotificadorEventosPort):
    """Reemplaza a RedisPublisherAdapter en tests: no hay Redis real
    disponible ni en este entorno ni en el pipeline de CI (mismo criterio
    que NotificadorFake en test_pedidos_websocket.py)."""

    async def notificar_pedido_creado(self, pedido: Pedido) -> None:
        pass

    async def notificar_pedido_actualizado(self, pedido: Pedido) -> None:
        pass


def _override_get_order_dispatch_use_case(
    db: AsyncSession = Depends(get_db),
) -> PedidosYaOrderDispatchUseCase:
    repo = PostgresPedidoRepository(session=db)
    notificador = NotificadorFake()
    crear_pedido_uc = CrearPedidoUseCase(repository=repo, notificador=notificador)
    actualizar_estado_uc = ActualizarEstadoPedidoUseCase(
        repository=repo, notificador=notificador
    )
    dispatcher = PedidosIntegracionesAdapter(
        use_case=crear_pedido_uc, actualizar_estado_use_case=actualizar_estado_uc
    )
    return PedidosYaOrderDispatchUseCase(order_dispatcher=dispatcher)


@pytest.fixture(autouse=True)
def _pedidosya_jwt_secret(monkeypatch):
    monkeypatch.setenv("PEDIDOSYA_JWT_SECRET", JWT_SECRET_TEST)


@pytest.fixture(autouse=True)
def _override_vendor_mapping():
    app.dependency_overrides[get_vendor_mapping] = lambda: FakeVendorMapping()
    app.dependency_overrides[get_order_dispatch_use_case] = (
        _override_get_order_dispatch_use_case
    )
    yield
    app.dependency_overrides.pop(get_vendor_mapping, None)
    app.dependency_overrides.pop(get_order_dispatch_use_case, None)


def _bearer_token(secret: str = JWT_SECRET_TEST, claims: dict | None = None) -> str:
    payload = claims if claims is not None else {"service": "middleware"}
    return jwt.encode(payload, secret, algorithm="HS512")


def _headers(token: str | None = None) -> dict:
    headers = {"Content-Type": "application/json"}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _payload_valido(order_id: str = "PY-ORDER-1") -> dict:
    return {
        "orderId": order_id,
        "customerName": "Juan Test",
        "totalPrice": 15.5,
        "items": [{"name": "Pizza", "quantity": 1, "price": 15.5}],
        # La API puede agregar campos nuevos con el tiempo; este no debe
        # romper el parseo.
        "un_campo_futuro_desconocido": "no debería romper nada",
    }


@pytest.mark.asyncio
async def test_dispatch_pedido_valido_lo_persiste(client):
    respuesta = await client.post(
        f"/api/v1/integraciones/pedidosya/order/{REMOTE_ID_TEST}",
        content=json.dumps(_payload_valido()).encode(),
        headers=_headers(_bearer_token()),
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["status"] == "ACKNOWLEDGED"


@pytest.mark.asyncio
async def test_dispatch_pedido_duplicado_no_se_duplica(client, db_session):
    body = json.dumps(_payload_valido(order_id="PY-ORDER-DUP")).encode()
    headers = _headers(_bearer_token())

    r1 = await client.post(
        f"/api/v1/integraciones/pedidosya/order/{REMOTE_ID_TEST}",
        content=body,
        headers=headers,
    )
    r2 = await client.post(
        f"/api/v1/integraciones/pedidosya/order/{REMOTE_ID_TEST}",
        content=body,
        headers=headers,
    )

    assert r1.status_code == 200
    assert r2.status_code == 200

    repo = PostgresPedidoRepository(session=db_session)
    pedidos, _total = await repo.listar_por_restaurante(RESTAURANTE_ID_TEST)
    coincidencias = [p for p in pedidos if p.id_externo == "PY-ORDER-DUP"]
    assert len(coincidencias) == 1


@pytest.mark.asyncio
async def test_dispatch_sin_jwt_retorna_401(client):
    respuesta = await client.post(
        f"/api/v1/integraciones/pedidosya/order/{REMOTE_ID_TEST}",
        content=json.dumps(_payload_valido()).encode(),
        headers=_headers(),
    )
    assert respuesta.status_code == 401


@pytest.mark.asyncio
async def test_dispatch_jwt_firmado_con_secreto_incorrecto_retorna_401(client):
    token_malo = _bearer_token(secret="secreto-incorrecto")
    respuesta = await client.post(
        f"/api/v1/integraciones/pedidosya/order/{REMOTE_ID_TEST}",
        content=json.dumps(_payload_valido()).encode(),
        headers=_headers(token_malo),
    )
    assert respuesta.status_code == 401


@pytest.mark.asyncio
async def test_dispatch_jwt_sin_claim_service_middleware_retorna_401(client):
    token_sin_claim = _bearer_token(claims={"service": "otra-cosa"})
    respuesta = await client.post(
        f"/api/v1/integraciones/pedidosya/order/{REMOTE_ID_TEST}",
        content=json.dumps(_payload_valido()).encode(),
        headers=_headers(token_sin_claim),
    )
    assert respuesta.status_code == 401


@pytest.mark.asyncio
async def test_dispatch_json_malformado_retorna_422(client):
    respuesta = await client.post(
        f"/api/v1/integraciones/pedidosya/order/{REMOTE_ID_TEST}",
        content=b"{ esto no es json valido",
        headers=_headers(_bearer_token()),
    )
    assert respuesta.status_code == 422


@pytest.mark.asyncio
async def test_dispatch_payload_sin_order_id_retorna_422(client):
    payload_incompleto = {"customerName": "Juan"}
    respuesta = await client.post(
        f"/api/v1/integraciones/pedidosya/order/{REMOTE_ID_TEST}",
        content=json.dumps(payload_incompleto).encode(),
        headers=_headers(_bearer_token()),
    )
    assert respuesta.status_code == 422


@pytest.mark.asyncio
async def test_dispatch_remote_id_no_mapeado_retorna_404(client):
    respuesta = await client.post(
        "/api/v1/integraciones/pedidosya/order/REMOTE-NO-DADO-DE-ALTA",
        content=json.dumps(_payload_valido()).encode(),
        headers=_headers(_bearer_token()),
    )
    assert respuesta.status_code == 404
