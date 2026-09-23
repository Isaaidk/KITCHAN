"""Dominio de la integración Uber Eats: payload del webhook de Uber
(específico de esta plataforma) más el DTO neutral compartido, re-exportado
aquí para no romper los imports existentes de esta integración.
"""
from pydantic import BaseModel
from typing import Optional

# Re-exportado: KitchanOrderDTO/KitchanOrderItem ahora viven en
# integraciones.core.domain.entities (son neutrales, no específicos de
# Uber). Se mantiene este import para que el resto del código de esta
# integración (application/*, controllers/*) siga funcionando sin cambios.
from src.kitchan.modules.integraciones.core.domain.entities import (  # noqa: F401
    KitchanOrderDTO,
    KitchanOrderItem,
)


class UberWebhookMeta(BaseModel):
    """Metadatos del evento de Uber"""
    resource_id: Optional[str] = None

    status: Optional[str] = None

    user_id: Optional[str] = None

    order_id: Optional[str] = None

    courier_trip_id: Optional[str] = None

    external_order_id: Optional[str] = None

    store_id: Optional[str] = None

class UberWebhookPayload(BaseModel):
    """Estructura esperada del Webhook de Uber Eats"""
    event_id: str
    event_type: str
    meta: UberWebhookMeta

