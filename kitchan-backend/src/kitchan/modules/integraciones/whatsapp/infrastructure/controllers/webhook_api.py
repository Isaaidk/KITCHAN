"""Infraestructura de WhatsApp: endpoint que recibe los pedidos del bot.

- NEW_ORDER -> POST /api/v1/integraciones/whatsapp/webhook/new-order

El bot es un servicio independiente: firma cada request con
WHATSAPP_BOT_SECRET (ver security/signature_validator.py). El pedido queda en
estado NUEVA y el restaurante lo acepta o rechaza desde el KDS.
"""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException

from src.kitchan.modules.integraciones.core.domain.inter_module_ports import (
    OrderDispatcherPort,
)
from src.kitchan.modules.integraciones.whatsapp.application.webhook_use_cases import (
    WhatsAppWebhookUseCase,
)
from src.kitchan.modules.integraciones.whatsapp.domain.models import (
    WhatsAppOrderPayload,
)
from src.kitchan.modules.integraciones.whatsapp.domain.ports import (
    WhatsAppStoreMappingPort,
)
from src.kitchan.modules.integraciones.whatsapp.infrastructure.adapters.env_store_mapping_adapter import (
    EnvWhatsAppStoreMappingAdapter,
)
from src.kitchan.modules.integraciones.whatsapp.infrastructure.security.signature_validator import (
    validar_firma_whatsapp,
)
from src.kitchan.modules.pedidos.infrastructure.dependencias import get_order_dispatcher

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/integraciones/whatsapp/webhook",
    tags=["Integraciones - WhatsApp Webhook"],
)


def get_store_mapping() -> WhatsAppStoreMappingPort:
    return EnvWhatsAppStoreMappingAdapter()


def get_webhook_use_case(
    order_dispatcher: OrderDispatcherPort = Depends(get_order_dispatcher),
    store_mapping: WhatsAppStoreMappingPort = Depends(get_store_mapping),
) -> WhatsAppWebhookUseCase:
    return WhatsAppWebhookUseCase(
        store_mapping=store_mapping, order_dispatcher=order_dispatcher
    )


@router.post("/new-order")
async def whatsapp_new_order(
    valid_body: bytes = Depends(validar_firma_whatsapp),
    use_case: WhatsAppWebhookUseCase = Depends(get_webhook_use_case),
):
    try:
        payload = WhatsAppOrderPayload(**json.loads(valid_body))
    except Exception as error:
        logger.warning("Payload incompatible con WhatsAppOrderPayload: %s", error)
        raise HTTPException(
            status_code=422,
            detail={
                "error": "INVALID_WHATSAPP_PAYLOAD",
                "mensaje": "El payload no coincide con WhatsAppOrderPayload",
            },
        )

    try:
        registrado = await use_case.procesar_nuevo_pedido(payload)
    except Exception:
        logger.exception("Error inesperado procesando pedido WhatsApp %s", payload.order_id)
        raise HTTPException(status_code=500, detail={"error": "INTERNAL_SERVICE_ERROR"})

    if not registrado:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "STORE_NOT_FOUND",
                "mensaje": (
                    f"La tienda WhatsApp '{payload.store_id}' "
                    "no está dada de alta en KITCHAN."
                ),
            },
        )

    return {"status": "success"}
