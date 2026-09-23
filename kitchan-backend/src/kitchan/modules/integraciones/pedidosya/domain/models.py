"""Dominio de la integración PedidosYa: payload que Delivery Hero envía en
el POST de "Dispatch Order" contra nuestro endpoint, y el modelo de
confirmación que les debemos devolver.

⚠️ Campos "best-effort": el resumen de documentación disponible
(https://integration-middleware.stg.restaurant-partners.com/apidocs/pluginApi.yaml)
confirma la existencia de un identificador de orden en el path (remoteId) y
la nota de que la API puede agregar campos nuevos con el tiempo, pero no
incluye el schema completo del body (cliente/items/precio). Los campos de
abajo son una aproximación razonable (misma forma que ya maneja Uber) y
DEBEN verificarse contra el YAML real antes de ir a producción — de ahí los
TODO puntuales.
"""

from pydantic import BaseModel, ConfigDict, Field
from typing import Optional


class PedidosYaOrderItemPayload(BaseModel):
    """TODO: confirmar nombres de campos reales contra pluginApi.yaml."""

    # La API puede evolucionar agregando campos nuevos; los ignoramos en vez
    # de fallar (requisito explícito de la doc de PedidosYa).
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    name: str = Field(alias="name")
    quantity: int = Field(alias="quantity")
    price: float = Field(alias="price")
    notes: Optional[str] = Field(default=None, alias="notes")


class PedidosYaOrderPayload(BaseModel):
    """Body del POST /order/{remoteId}. TODO: confirmar contra el YAML real
    los nombres exactos de campo (se asume camelCase, estilo Delivery Hero)."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    order_id: str = Field(alias="orderId")
    customer_name: str = Field(default="Cliente PedidosYa", alias="customerName")
    total_price: float = Field(default=0.0, alias="totalPrice")
    items: list[PedidosYaOrderItemPayload] = Field(default_factory=list, alias="items")
    notes: Optional[str] = Field(default=None, alias="notes")


class OrderDispatchAcknowledgedResponse(BaseModel):
    """Respuesta de confirmación esperada por Delivery Hero tras el POST de
    dispatch. TODO: confirmar el shape exacto del schema
    OrderDispatchAcknowledgedResponse contra el YAML real."""

    status: str = "ACKNOWLEDGED"
