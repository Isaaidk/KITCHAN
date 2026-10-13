from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class EstadoFactura(str, Enum):
    """Estado de la factura electrónica de un pedido ante el SRI.

    KITCHAN no firma ni envía nada al SRI: lo hace Odoo. Este estado es el
    reflejo, en KITCHAN, de lo que Odoo informa.
    """

    PENDIENTE_SRI = "PENDIENTE_SRI"  # Emitida en Odoo, esperando al SRI
    AUTORIZADA = "AUTORIZADA"
    CON_ERROR = "CON_ERROR"  # El SRI u Odoo la rechazaron; se puede reintentar
    ANULADA = "ANULADA"


class LineaFactura(BaseModel):
    descripcion: str
    cantidad: int
    # Precio unitario con IVA incluido, tal como lo cobra la plataforma.
    precio_con_iva: float


class DatosFactura(BaseModel):
    """Lo que Odoo necesita para emitir la factura de un pedido."""

    referencia: str  # Única por pedido: evita facturar dos veces
    origen: str  # Texto legible para el contador, p. ej. "RAPPI 123"
    lineas: list[LineaFactura]


class ResultadoOdoo(BaseModel):
    """Estado de una factura según Odoo."""

    odoo_move_id: int
    numero: Optional[str] = None
    estado: EstadoFactura
    total: float = 0.0
    numero_autorizacion: Optional[str] = None
    fecha_autorizacion: Optional[datetime] = None
    mensaje_error: Optional[str] = None


class PedidoAFacturar(BaseModel):
    """Lo que Facturación necesita saber de un pedido (sin depender del
    módulo de pedidos)."""

    id: str
    restaurante_id: str
    origen: str
    id_externo: Optional[str] = None
    estado: str
    items: list[LineaFactura]


class FacturaPedido(BaseModel):
    pedido_id: str
    restaurante_id: str
    odoo_move_id: int
    numero: Optional[str] = None
    estado: EstadoFactura
    total: float = 0.0
    numero_autorizacion: Optional[str] = None
    fecha_autorizacion: Optional[datetime] = None
    mensaje_error: Optional[str] = None
    fecha_actualizacion: Optional[datetime] = None

    def aplicar(self, resultado: ResultadoOdoo) -> "FacturaPedido":
        return self.model_copy(update=resultado.model_dump())
