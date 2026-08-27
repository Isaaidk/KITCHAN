from pydantic import BaseModel
from typing import Optional

class UberWebhookMeta(BaseModel):
    """Metadatos del evento de Uber"""
    resource_id: str
    status: Optional[str] = None
    user_id: Optional[str] = None

class UberWebhookPayload(BaseModel):
    """Estructura esperada del Webhook de Uber Eats"""
    event_id: str
    event_type: str
    meta: UberWebhookMeta

class KitchanOrderItem(BaseModel):
    """Modelo interno para los productos de una orden"""
    nombre: str
    cantidad: int
    precio_unitario: float
    notas_especiales: Optional[str] = None

class KitchanOrderDTO(BaseModel):
    """Modelo interno estandarizado para KITCHAN (Capa Anticorrupción)"""
    id_externo: str
    plataforma: str = "UBER_EATS"
    restaurante_id: str
    nombre_cliente: str
    items: list[KitchanOrderItem]
    total: float
    estado: str = "NUEVA"