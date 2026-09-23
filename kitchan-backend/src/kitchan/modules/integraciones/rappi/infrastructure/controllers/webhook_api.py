"""Infraestructura de Rappi: endpoints que reciben los webhooks de Rappi.
Es el equivalente arquitectónico al webhook_api.py de Uber y al
order_dispatch_api.py de PedidosYa: valida la firma entrante, parsea y valida
el payload, y delega en el caso de uso.

Rappi configura una URL por evento (POST webhook con {event, url, stores}),
por eso hay un endpoint por evento en vez de uno solo que distingue por
`event_type` como en Uber:
- NEW_ORDER           -> POST /api/v1/integraciones/rappi/webhook/new-order
- ORDER_EVENT_CANCEL  -> POST /api/v1/integraciones/rappi/webhook/order-cancel
"""

import json
import logging
import os

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.kitchan.core.database import get_db
from src.kitchan.modules.integraciones.rappi.application.webhook_use_cases import (
    RappiWebhookUseCase,
)
from src.kitchan.modules.integraciones.rappi.domain.models import (
    RappiCancelEventPayload,
    RappiOrderPayload,
)
from src.kitchan.modules.integraciones.rappi.domain.ports import RappiStoreMappingPort
from src.kitchan.modules.integraciones.rappi.infrastructure.adapters.env_store_mapping_adapter import (
    EnvRappiStoreMappingAdapter,
)
from src.kitchan.modules.integraciones.rappi.infrastructure.security.signature_validator import (
    validar_firma_rappi,
)
from src.kitchan.modules.pedidos.application.actualizar_estado_pedido_service import (
    ActualizarEstadoPedidoUseCase,
)
from src.kitchan.modules.pedidos.application.crear_pedido_service import (
    CrearPedidoUseCase,
)
from src.kitchan.modules.pedidos.infrastructure.adapters.integraciones_dispatcher import (
    PedidosIntegracionesAdapter,
)
from src.kitchan.modules.pedidos.infrastructure.eventos.redis_publisher import (
    RedisPublisherAdapter,
)
from src.kitchan.modules.pedidos.infrastructure.repository import (
    PostgresPedidoRepository,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/integraciones/rappi/webhook",
    tags=["Integraciones - Rappi Webhook"],
)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


# ============================================================
# DEPENDENCY INJECTION
# ============================================================
def get_store_mapping() -> RappiStoreMappingPort:
    return EnvRappiStoreMappingAdapter()


def get_webhook_use_case(
    db: AsyncSession = Depends(get_db),
    store_mapping: RappiStoreMappingPort = Depends(get_store_mapping),
) -> RappiWebhookUseCase:
    repo_pedidos = PostgresPedidoRepository(session=db)
    notificador = RedisPublisherAdapter(redis_url=REDIS_URL)

    crear_pedido_uc = CrearPedidoUseCase(
        repository=repo_pedidos, notificador=notificador
    )
    actualizar_estado_uc = ActualizarEstadoPedidoUseCase(
        repository=repo_pedidos, notificador=notificador
    )

    dispatcher_adapter = PedidosIntegracionesAdapter(
        use_case=crear_pedido_uc, actualizar_estado_use_case=actualizar_estado_uc
    )

    return RappiWebhookUseCase(
        store_mapping=store_mapping, order_dispatcher=dispatcher_adapter
    )


def _parsear_json(valid_body: bytes) -> dict:
    try:
        return json.loads(valid_body)
    except json.JSONDecodeError as error:
        logger.warning("Payload de Rappi no es JSON válido: %s", error)
        raise HTTPException(
            status_code=422, detail="El payload recibido no es JSON válido"
        )


# ============================================================
# NEW_ORDER
# ============================================================
@router.post("/new-order")
async def rappi_new_order(
    valid_body: bytes = Depends(validar_firma_rappi),
    use_case: RappiWebhookUseCase = Depends(get_webhook_use_case),
):
    payload_dict = _parsear_json(valid_body)

    try:
        payload_model = RappiOrderPayload(**payload_dict)
    except Exception as error:
        logger.warning("Payload incompatible con RappiOrderPayload: %s", error)
        raise HTTPException(
            status_code=422,
            detail={
                "error": "INVALID_RAPPI_PAYLOAD",
                "mensaje": "El payload recibido de Rappi no coincide con RappiOrderPayload",
            },
        )

    try:
        registrado = await use_case.procesar_nuevo_pedido(payload_model)
    except HTTPException:
        raise
    except Exception:
        logger.exception(
            "Error inesperado procesando NEW_ORDER de Rappi %s",
            payload_model.order_detail.order_id,
        )
        raise HTTPException(status_code=500, detail={"error": "INTERNAL_SERVICE_ERROR"})

    if not registrado:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "STORE_NOT_FOUND",
                "mensaje": (
                    f"La tienda Rappi '{payload_model.store.internal_id}' "
                    "no está dada de alta en KITCHAN."
                ),
            },
        )

    return {"status": "success"}


# ============================================================
# ORDER_EVENT_CANCEL
# ============================================================
@router.post("/order-cancel")
async def rappi_order_cancel(
    valid_body: bytes = Depends(validar_firma_rappi),
    use_case: RappiWebhookUseCase = Depends(get_webhook_use_case),
):
    payload_dict = _parsear_json(valid_body)

    try:
        payload_model = RappiCancelEventPayload(**payload_dict)
    except Exception as error:
        logger.warning("Payload incompatible con RappiCancelEventPayload: %s", error)
        raise HTTPException(
            status_code=422,
            detail={
                "error": "INVALID_RAPPI_PAYLOAD",
                "mensaje": "El payload recibido de Rappi no coincide con RappiCancelEventPayload",
            },
        )

    try:
        await use_case.procesar_cancelacion(payload_model)
    except Exception:
        logger.exception(
            "Error inesperado procesando ORDER_EVENT_CANCEL de Rappi %s",
            payload_model.order_id,
        )
        raise HTTPException(status_code=500, detail={"error": "INTERNAL_SERVICE_ERROR"})

    # Aunque el pedido no exista en KITCHAN, respondemos 200 para que Rappi
    # no reintente indefinidamente un evento que no podemos aplicar.
    return {"status": "success"}
