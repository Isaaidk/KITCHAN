"""Dominio de la integración WhatsApp: payload que el bot de WhatsApp (servicio
independiente) envía al webhook de KITCHAN cuando un cliente confirma un pedido.

A diferencia de Uber/Rappi/PedidosYa, el emisor no es una plataforma de
terceros sino un servicio propio, así que el contrato es nuestro y estable.
Los montos vienen en unidades de moneda (no centavos).
"""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class WhatsAppOrderItemPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    quantity: int = Field(default=1, ge=1)
    unit_price: float = Field(default=0.0, ge=0)
    notes: Optional[str] = None


class WhatsAppOrderPayload(BaseModel):
    """Body del webhook POST .../whatsapp/webhook/new-order."""

    model_config = ConfigDict(extra="ignore")

    order_id: str = Field(min_length=1, max_length=64)
    # Identificador de la tienda/bot; se resuelve a un restaurante_id con
    # WHATSAPP_STORE_ID_MAP (igual que Rappi con RAPPI_STORE_ID_MAP).
    store_id: str = Field(min_length=1, max_length=64)
    customer_name: str = "Cliente WhatsApp"
    items: list[WhatsAppOrderItemPayload] = Field(min_length=1)
    total: float = Field(gt=0)
    currency: Optional[str] = None
    payment_method: Optional[str] = None
