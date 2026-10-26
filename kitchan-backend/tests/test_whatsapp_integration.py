"""Tests de la integración WhatsApp: webhook firmado que recibe el pedido del
bot (válido, idempotente, firma ausente/inválida/vencida, tienda no mapeada) y
acciones del KDS (aceptar/rechazar/listo) con un bot falso en memoria.
"""

import json
import time

import pytest
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.kitchan.core.database import get_db
from src.kitchan.main import app
from src.kitchan.modules.integraciones.whatsapp.application.order_use_cases import (
    WhatsAppOrderUseCase,
)
from src.kitchan.modules.integraciones.whatsapp.application.webhook_use_cases import (
    WhatsAppWebhookUseCase,
)
from src.kitchan.modules.integraciones.whatsapp.domain.ports import (
    WhatsAppBotPort,
    WhatsAppStoreMappingPort,
)
from src.kitchan.modules.integraciones.whatsapp.infrastructure.controllers.webhook_api import (
    get_webhook_use_case,
)
from src.kitchan.modules.integraciones.whatsapp.infrastructure.security.signature_validator import (
    HEADER,
    firmar,
    verificar,
)
from src.kitchan.modules.pedidos.application.actualizar_estado_pedido_service import (
    ActualizarEstadoPedidoUseCase,
)
from src.kitchan.modules.pedidos.application.crear_pedido_service import (
    CrearPedidoUseCase,
)
from src.kitchan.modules.pedidos.domain.entities import EstadoPedido, Pedido, PedidoItem
from src.kitchan.modules.pedidos.infrastructure.adapters.integraciones_dispatcher import (
    PedidosIntegracionesAdapter,
)
from src.kitchan.modules.pedidos.infrastructure.adapters.memory_repository import (
    MemoryPedidoRepository,
)
from src.kitchan.modules.pedidos.infrastructure.repository import (
    PostgresPedidoRepository,
)

SECRETO = "secreto-bot-de-test"
RESTAURANTE_ID_TEST = "11111111-1111-1111-1111-111111111111"
STORE_ID_TEST = "default"
URL = "/api/v1/integraciones/whatsapp/webhook/new-order"


class FakeStoreMapping(WhatsAppStoreMappingPort):
    async def get_restaurante_id(self, store_id: str):
        return RESTAURANTE_ID_TEST if store_id == STORE_ID_TEST else None


class FakeBot(WhatsAppBotPort):
    def __init__(self, responde: bool = True):
        self.responde = responde
        self.avisos: list[tuple] = []

    async def notify_order_status(self, order_id, status, reason=None):
        self.avisos.append((order_id, status, reason))
        if not self.responde:
            raise ConnectionError("bot caído")
        return True


def _override_use_case(db: AsyncSession = Depends(get_db)) -> WhatsAppWebhookUseCase:
    repo = PostgresPedidoRepository(session=db)
    dispatcher = PedidosIntegracionesAdapter(
        use_case=CrearPedidoUseCase(repository=repo),
        actualizar_estado_use_case=ActualizarEstadoPedidoUseCase(repository=repo),
    )
    return WhatsAppWebhookUseCase(
        store_mapping=FakeStoreMapping(), order_dispatcher=dispatcher
    )


@pytest.fixture(autouse=True)
def _config(monkeypatch):
    monkeypatch.setenv("WHATSAPP_BOT_SECRET", SECRETO)
    app.dependency_overrides[get_webhook_use_case] = _override_use_case
    yield
    app.dependency_overrides.pop(get_webhook_use_case, None)


def _payload(order_id: str = "WA-1", store_id: str = STORE_ID_TEST) -> dict:
    return {
        "order_id": order_id,
        "store_id": store_id,
        "customer_name": "Ana Test",
        "items": [{"name": "Café", "quantity": 2, "unit_price": 2.5}],
        "total": 5.0,
        "currency": "USD",
        "payment_method": "Efectivo",
        "campo_futuro": "se ignora",
    }


async def _post(client, payload, firma="auto"):
    body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
    headers = {"Content-Type": "application/json"}
    if firma == "auto":
        headers[HEADER] = firmar(SECRETO, body)
    elif firma is not None:
        headers[HEADER] = firma
    return await client.post(URL, content=body, headers=headers)


# ---------------- firma ----------------
def test_firma_valida_y_body_alterado():
    body = b'{"a": 1}'
    firma = firmar(SECRETO, body)
    assert verificar(SECRETO, body, firma) is True
    assert verificar(SECRETO, b'{"a": 2}', firma) is False
    assert verificar("otro", body, firma) is False
    assert verificar(SECRETO, body, "basura") is False


def test_firma_vencida_es_invalida():
    body = b"{}"
    firma = firmar(SECRETO, body, timestamp=int(time.time()) - 3600)
    assert verificar(SECRETO, body, firma) is False


# ---------------- webhook ----------------
@pytest.mark.asyncio
async def test_pedido_valido_se_persiste_como_nueva(client, db_session):
    respuesta = await _post(client, _payload())

    assert respuesta.status_code == 200
    repo = PostgresPedidoRepository(session=db_session)
    pedido = await repo.buscar_por_id_externo("WHATSAPP", "WA-1")
    assert pedido is not None
    assert pedido.cliente == "Ana Test"
    assert pedido.total == 5.0
    assert pedido.items[0].nombre == "Café"
    assert pedido.estado == EstadoPedido.NUEVA
    assert pedido.restaurante_id == RESTAURANTE_ID_TEST


@pytest.mark.asyncio
async def test_pedido_duplicado_no_se_duplica(client, db_session):
    r1 = await _post(client, _payload("WA-DUP"))
    r2 = await _post(client, _payload("WA-DUP"))

    assert r1.status_code == r2.status_code == 200
    repo = PostgresPedidoRepository(session=db_session)
    pedidos, _ = await repo.listar_por_restaurante(RESTAURANTE_ID_TEST)
    assert len([p for p in pedidos if p.id_externo == "WA-DUP"]) == 1


@pytest.mark.asyncio
async def test_sin_firma_401(client):
    assert (await _post(client, _payload(), firma=None)).status_code == 401


@pytest.mark.asyncio
async def test_firma_invalida_403(client):
    body = json.dumps(_payload()).encode()
    mala = firmar("otro-secreto", body)
    assert (await _post(client, body, firma=mala)).status_code == 403


@pytest.mark.asyncio
async def test_payload_incompleto_422(client):
    r = await _post(client, {"order_id": "WA-X", "store_id": STORE_ID_TEST})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_json_invalido_422(client):
    assert (await _post(client, b"no es json")).status_code == 422


@pytest.mark.asyncio
async def test_tienda_no_mapeada_404(client):
    r = await _post(client, _payload(store_id="desconocida"))
    assert r.status_code == 404
    assert r.json()["detail"]["error"] == "STORE_NOT_FOUND"


# ---------------- acciones KDS ----------------
def _armar(bot: WhatsAppBotPort):
    repo = MemoryPedidoRepository()
    dispatcher = PedidosIntegracionesAdapter(
        use_case=CrearPedidoUseCase(repository=repo),
        actualizar_estado_use_case=ActualizarEstadoPedidoUseCase(repository=repo),
    )
    return WhatsAppOrderUseCase(bot=bot, order_dispatcher=dispatcher), repo


async def _crear(repo, order_id):
    await repo.guardar(
        Pedido(
            restaurante_id="rest-1",
            origen="WHATSAPP",
            id_externo=order_id,
            cliente="Cliente",
            items=[PedidoItem(nombre="Café", cantidad=1, precio_unitario=2.5)],
            total=2.5,
        )
    )


@pytest.mark.asyncio
async def test_aceptar_cambia_estado_y_avisa_al_bot():
    bot = FakeBot()
    uc, repo = _armar(bot)
    await _crear(repo, "WA-A")

    assert await uc.accept_order("WA-A") is True

    assert (await repo.buscar_por_id_externo("WHATSAPP", "WA-A")).estado == (
        EstadoPedido.EN_PREPARACION
    )
    assert bot.avisos == [("WA-A", "ACCEPTED", None)]


@pytest.mark.asyncio
async def test_rechazar_cancela_y_envia_motivo():
    bot = FakeBot()
    uc, repo = _armar(bot)
    await _crear(repo, "WA-R")

    await uc.deny_order("WA-R", "Producto agotado")

    assert (await repo.buscar_por_id_externo("WHATSAPP", "WA-R")).estado == (
        EstadoPedido.CANCELADA
    )
    assert bot.avisos == [("WA-R", "REJECTED", "Producto agotado")]


@pytest.mark.asyncio
async def test_listo_cambia_a_lista():
    bot = FakeBot()
    uc, repo = _armar(bot)
    await _crear(repo, "WA-L")

    await uc.mark_order_ready("WA-L")

    assert (await repo.buscar_por_id_externo("WHATSAPP", "WA-L")).estado == (
        EstadoPedido.LISTA
    )
    assert bot.avisos[-1][1] == "READY"


@pytest.mark.asyncio
async def test_bot_caido_no_revierte_la_decision_del_restaurante():
    uc, repo = _armar(FakeBot(responde=False))
    await _crear(repo, "WA-D")

    notificado = await uc.accept_order("WA-D")

    assert notificado is False
    assert (await repo.buscar_por_id_externo("WHATSAPP", "WA-D")).estado == (
        EstadoPedido.EN_PREPARACION
    )


@pytest.mark.asyncio
async def test_acciones_kds_sin_usuario_401(client):
    for accion in ("accept", "ready"):
        r = await client.post(f"/api/v1/integraciones/whatsapp/orders/WA-Z/{accion}")
        assert r.status_code == 401
