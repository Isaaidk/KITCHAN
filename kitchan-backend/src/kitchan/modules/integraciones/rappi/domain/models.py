"""Dominio de la integración Rappi: payloads que Rappi envía a nuestros
webhooks (NEW_ORDER y ORDER_EVENT_CANCEL).

Fuente: Rappi Developer Portal (https://dev-portal.rappi.com), secciones
"Orders" y "Webhook events". El webhook NEW_ORDER entrega "la misma
información que el endpoint getOrders" — a diferencia de Uber, NO hace falta
descargar el pedido después de recibir la notificación.

⚠️ Campos "best-effort": la documentación pública muestra la forma general
del pedido (order_detail / customer / store) pero no aclara todos los
detalles (ej. si `price` y `total_order` vienen en centavos o en unidades).
Los TODO puntuales marcan lo que DEBE verificarse contra un payload real de
staging antes de ir a producción.
"""

from pydantic import BaseModel, ConfigDict, Field
from typing import Optional


class RappiOrderItemPayload(BaseModel):
    # La API puede agregar campos nuevos; los ignoramos en vez de fallar.
    model_config = ConfigDict(extra="ignore")

    name: str
    quantity: int = 1
    # TODO: la doc declara `price` como integer; confirmar si viene en
    # centavos (habría que dividir por 100) o en unidades de moneda.
    price: float = 0.0
    comments: Optional[str] = None


class RappiOrderTotalsPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    # TODO: confirmar unidad (centavos vs unidades), igual que `price`.
    total_order: float = 0.0


class RappiOrderDetailPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    order_id: str
    cooking_time: Optional[int] = None
    items: list[RappiOrderItemPayload] = Field(default_factory=list)
    totals: RappiOrderTotalsPayload = Field(default_factory=RappiOrderTotalsPayload)


class RappiCustomerPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    first_name: str = "Cliente"
    last_name: str = "Rappi"


class RappiStorePayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    # internal_id = id de la tienda en Rappi (el mismo que llega como
    # `store_id` en ORDER_EVENT_CANCEL); external_id = id que nosotros
    # informamos durante el alta.
    internal_id: str
    external_id: Optional[str] = None
    name: Optional[str] = None


class RappiOrderPayload(BaseModel):
    """Body del webhook NEW_ORDER (misma forma que GET .../orders)."""

    model_config = ConfigDict(extra="ignore")

    order_detail: RappiOrderDetailPayload
    customer: RappiCustomerPayload = Field(default_factory=RappiCustomerPayload)
    store: RappiStorePayload


class RappiCancelEventPayload(BaseModel):
    """Body del webhook ORDER_EVENT_CANCEL."""

    model_config = ConfigDict(extra="ignore")

    event: Optional[str] = None  # ej. "canceled_with_charge"
    order_id: str
    store_id: Optional[str] = None
