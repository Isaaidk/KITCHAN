"""Dominio de la integración WhatsApp: puertos de salida hacia el bot de
WhatsApp (servicio independiente) y hacia el mapeo tienda -> restaurante.
"""

from abc import ABC, abstractmethod
from typing import Optional


class WhatsAppBotPort(ABC):
    """
    Puerto para avisarle al bot el resultado de la decisión del restaurante,
    para que él (que es quien tiene el chat con el cliente) le escriba por
    WhatsApp. KITCHAN no habla con Meta directamente.
    """

    @abstractmethod
    async def notify_order_status(
        self, order_id: str, status: str, reason: Optional[str] = None
    ) -> bool:
        """Retorna True si el bot confirmó la recepción. Estados:
        ACCEPTED, READY, REJECTED, CANCELLED."""
        pass


class WhatsAppStoreMappingPort(ABC):
    @abstractmethod
    async def get_restaurante_id(self, store_id: str) -> Optional[str]:
        pass
