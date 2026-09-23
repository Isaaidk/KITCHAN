"""Tests HTTP de los webhooks de Rappi (NEW_ORDER y ORDER_EVENT_CANCEL):
recepción de pedido válido, idempotencia ante reenvíos, firma
ausente/inválida, payload malformado/incompleto, tienda no mapeada y
cancelación. No se llama a la API real de Rappi: el mapeo de tiendas y el
notificador se reemplazan vía dependency override (mismo criterio que
test_pedidosya_order_dispatch.py).
"""

import hashlib
import hmac
import json

import pytest
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.kitchan.core.database import get_db
from src.kitchan.main import app
from src.kitchan.modules.integraciones.rappi.application.webhook_use_cases import (
    RappiWebhookUseCase,
)
from src.kitchan.modules.integraciones.rappi.domain.ports import RappiStoreMappingPort
from src.kitchan.modules.integraciones.rappi.infrastructure.controllers.webhook_api import (
    get_webhook_use_case,
)
from src.kitchan.modules.integraciones.rappi.infrastructure.security.signature_validator import (
    verify_rappi_signature,
)
from src.kitchan.modules.pedidos.application.actualizar_estado_pedido_service import (
    ActualizarEstadoPedidoUseCase,
)
from src.kitchan.modules.pedidos.application.crear_pedido_service import (
    CrearPedidoUseCase,
)
from src.kitchan.modules.pedidos.application.ports import NotificadorEventosPort
from src.kitchan.modules.pedidos.domain.entities import EstadoPedido, Pedido
from src.kitchan.modules.pedidos.infrastructure.adapters.integraciones_dispatcher import (
    PedidosIntegracionesAdapter,
)
from src.kitchan.modules.pedidos.infrastructure.repository import (
    PostgresPedidoRepository,
)

WEBHOOK_SECRET_TEST = "secreto-webhook-de-test"
RESTAURANTE_ID_TEST = "11111111-1111-1111-1111-111111111111"
STORE_ID_TEST = "900123456"

URL_NEW_ORDER = "/api/v1/integraciones/rappi/webhook/new-order"
URL_CANCEL = "/api/v1/integraciones/rappi/webhook/order-cancel"


class FakeStoreMapping(RappiStoreMappingPort):
    """Reemplaza a EnvRappiStoreMappingAdapter en tests."""

    async def get_restaurante_id(self, store_id: str):
        return RESTAURANTE_ID_TEST if store_id == STORE_ID_TEST else None


class NotificadorFake(NotificadorEventosPort):
    """Reemplaza a RedisPublisherAdapter en tests: no hay Redis real
    disponible ni en este entorno ni en el pipeline de CI."""

    async def notificar_pedido_creado(self, pedido: Pedido) -> None:
        pass

    async def notificar_pedido_actualizado(self, pedido: Pedido) -> None:
        pass


def _override_get_webhook_use_case(
    db: AsyncSession = Depends(get_db),
) -> RappiWebhookUseCase:
    repo = PostgresPedidoRepository(session=db)
    notificador = NotificadorFake()
    crear_pedido_uc = CrearPedidoUseCase(repository=repo, notificador=notificador)
    actualizar_estado_uc = ActualizarEstadoPedidoUseCase(
        repository=repo, notificador=notificador
    )
    dispatcher = PedidosIntegracionesAdapter(
        use_case=crear_pedido_uc, actualizar_estado_use_case=actualizar_estado_uc
    )
    return RappiWebhookUseCase(
        store_mapping=FakeStoreMapping(), order_dispatcher=dispatcher
    )


@pytest.fixture(autouse=True)
def _rappi_webhook_secret(monkeypatch):
    monkeypatch.setenv("RAPPI_WEBHOOK_SECRET", WEBHOOK_SECRET_TEST)


@pytest.fixture(autouse=True)
def _override_use_case():
    app.dependency_overrides[get_webhook_use_case] = _override_get_webhook_use_case
    yield
    app.dependency_overrides.pop(get_webhook_use_case, None)


def _firmar(
    body: bytes, secret: str = WEBHOOK_SECRET_TEST, t: str = "1700000000"
) -> str:
    firma = hmac.new(
        secret.encode(), t.encode() + b"." + body, hashlib.sha256
    ).hexdigest()
    return f"t={t},sign={firma}"


def _headers(body: bytes, firma: str | None = "auto") -> dict:
    headers = {"Content-Type": "application/json"}
    if firma == "auto":
        headers["Rappi-Signature"] = _firmar(body)
    elif firma is not None:
        headers["Rappi-Signature"] = firma
    return headers


def _payload_valido(
    order_id: str = "RAPPI-ORDER-1", store_id: str = STORE_ID_TEST
) -> dict:
    return {
        "order_detail": {
            "order_id": order_id,
            "cooking_time": 15,
            "items": [
                {"id": "1", "name": "Pizza", "quantity": 2, "price": 7.5},
            ],
            "totals": {"total_order": 15.0},
            # Campo desconocido: no debe romper el parseo.
            "un_campo_futuro": "no debería romper nada",
        },
        "customer": {"first_name": "Ana", "last_name": "Test"},
        "store": {"internal_id": store_id, "external_id": "KITCHAN-1"},
    }


async def _post(client, url: str, payload, firma: str | None = "auto"):
    body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
    return await client.post(url, content=body, headers=_headers(body, firma))


# ============================================================
# Firma (unitarios)
# ============================================================
def test_verify_signature_valida():
    body = b'{"a": 1}'
    assert verify_rappi_signature(WEBHOOK_SECRET_TEST, body, _firmar(body)) is True


def test_verify_signature_body_alterado_es_invalida():
    firma = _firmar(b'{"a": 1}')
    assert verify_rappi_signature(WEBHOOK_SECRET_TEST, b'{"a": 2}', firma) is False


def test_verify_signature_header_malformado_es_invalida():
    assert verify_rappi_signature(WEBHOOK_SECRET_TEST, b"{}", "basura") is False


# ============================================================
# NEW_ORDER
# ============================================================
@pytest.mark.asyncio
async def test_new_order_valido_lo_persiste(client, db_session):
    respuesta = await _post(client, URL_NEW_ORDER, _payload_valido())

    assert respuesta.status_code == 200
    repo = PostgresPedidoRepository(session=db_session)
    pedido = await repo.buscar_por_id_externo("RAPPI", "RAPPI-ORDER-1")
    assert pedido is not None
    assert pedido.cliente == "Ana Test"
    assert pedido.total == 15.0
    assert pedido.items[0].nombre == "Pizza"
    assert pedido.estado == EstadoPedido.NUEVA


@pytest.mark.asyncio
async def test_new_order_duplicado_no_se_duplica(client, db_session):
    payload = _payload_valido(order_id="RAPPI-DUP")
    r1 = await _post(client, URL_NEW_ORDER, payload)
    r2 = await _post(client, URL_NEW_ORDER, payload)

    assert r1.status_code == 200
    assert r2.status_code == 200

    repo = PostgresPedidoRepository(session=db_session)
    pedidos, _total = await repo.listar_por_restaurante(RESTAURANTE_ID_TEST)
    assert len([p for p in pedidos if p.id_externo == "RAPPI-DUP"]) == 1


@pytest.mark.asyncio
async def test_new_order_sin_firma_retorna_401(client):
    respuesta = await _post(client, URL_NEW_ORDER, _payload_valido(), firma=None)
    assert respuesta.status_code == 401


@pytest.mark.asyncio
async def test_new_order_firma_invalida_retorna_403(client):
    body = json.dumps(_payload_valido()).encode()
    firma_mala = _firmar(body, secret="otro-secreto")
    respuesta = await _post(client, URL_NEW_ORDER, body, firma=firma_mala)
    assert respuesta.status_code == 403


@pytest.mark.asyncio
async def test_new_order_json_malformado_retorna_422(client):
    respuesta = await _post(client, URL_NEW_ORDER, b"{ esto no es json")
    assert respuesta.status_code == 422


@pytest.mark.asyncio
async def test_new_order_sin_order_id_retorna_422(client):
    payload = _payload_valido()
    del payload["order_detail"]["order_id"]
    respuesta = await _post(client, URL_NEW_ORDER, payload)
    assert respuesta.status_code == 422


@pytest.mark.asyncio
async def test_new_order_tienda_no_mapeada_retorna_404(client):
    payload = _payload_valido(store_id="TIENDA-NO-DADA-DE-ALTA")
    respuesta = await _post(client, URL_NEW_ORDER, payload)
    assert respuesta.status_code == 404


# ============================================================
# ORDER_EVENT_CANCEL
# ============================================================
@pytest.mark.asyncio
async def test_cancel_marca_pedido_como_cancelada(client, db_session):
    await _post(client, URL_NEW_ORDER, _payload_valido(order_id="RAPPI-CANCEL"))

    respuesta = await _post(
        client,
        URL_CANCEL,
        {
            "event": "canceled_with_charge",
            "order_id": "RAPPI-CANCEL",
            "store_id": STORE_ID_TEST,
        },
    )

    assert respuesta.status_code == 200
    repo = PostgresPedidoRepository(session=db_session)
    pedido = await repo.buscar_por_id_externo("RAPPI", "RAPPI-CANCEL")
    assert pedido.estado == EstadoPedido.CANCELADA


@pytest.mark.asyncio
async def test_cancel_de_pedido_inexistente_responde_200(client):
    respuesta = await _post(
        client, URL_CANCEL, {"event": "canceled", "order_id": "NO-EXISTE"}
    )
    assert respuesta.status_code == 200


@pytest.mark.asyncio
async def test_cancel_sin_firma_retorna_401(client):
    respuesta = await _post(client, URL_CANCEL, {"order_id": "RAPPI-X"}, firma=None)
    assert respuesta.status_code == 401
