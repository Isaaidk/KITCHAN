"""Infraestructura de WhatsApp: mapeo store_id del bot -> restaurante_id,
cargado desde WHATSAPP_STORE_ID_MAP (JSON), igual que Rappi/PedidosYa.
Ej: {"default": "11111111-1111-1111-1111-111111111111"}
"""

import json
import logging
import os
from typing import Optional

from src.kitchan.modules.integraciones.whatsapp.domain.ports import (
    WhatsAppStoreMappingPort,
)

logger = logging.getLogger(__name__)


class EnvWhatsAppStoreMappingAdapter(WhatsAppStoreMappingPort):
    def __init__(self):
        raw = os.getenv("WHATSAPP_STORE_ID_MAP", "{}")
        try:
            self._mapa: dict[str, str] = json.loads(raw)
        except json.JSONDecodeError:
            logger.error("WHATSAPP_STORE_ID_MAP no es JSON válido: %r", raw)
            self._mapa = {}

    async def get_restaurante_id(self, store_id: str) -> Optional[str]:
        return self._mapa.get(store_id)
