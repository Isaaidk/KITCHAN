"""Infraestructura de WhatsApp: cliente HTTP hacia el bot (servicio
independiente). Le avisa la decisión del restaurante para que escriba al
cliente por WhatsApp.
"""

import json
import logging
import os
from typing import Optional

import httpx

from src.kitchan.modules.integraciones.whatsapp.domain.ports import WhatsAppBotPort
from src.kitchan.modules.integraciones.whatsapp.infrastructure.security.signature_validator import (
    HEADER,
    firmar,
)

logger = logging.getLogger(__name__)


class WhatsAppBotHttpAdapter(WhatsAppBotPort):
    def __init__(self, base_url: Optional[str] = None, secret: Optional[str] = None):
        self.base_url = (
            base_url or os.getenv("WHATSAPP_BOT_URL", "http://127.0.0.1:8001")
        ).rstrip("/")
        self.secret = secret or os.getenv("WHATSAPP_BOT_SECRET", "")

    async def notify_order_status(
        self, order_id: str, status: str, reason: Optional[str] = None
    ) -> bool:
        if not self.secret:
            logger.error("Falta WHATSAPP_BOT_SECRET: no se puede avisar al bot.")
            return False

        body = json.dumps({"status": status, "reason": reason}).encode("utf-8")
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    f"{self.base_url}/api/kitchan/orders/{order_id}/status",
                    content=body,
                    headers={
                        "Content-Type": "application/json",
                        HEADER: firmar(self.secret, body),
                    },
                )
        except httpx.HTTPError as error:
            logger.warning("El bot de WhatsApp no respondió: %s", error)
            return False

        if response.is_error:
            logger.warning(
                "El bot de WhatsApp rechazó el aviso (%s): %s",
                response.status_code,
                response.text[:300],
            )
            return False
        return True
