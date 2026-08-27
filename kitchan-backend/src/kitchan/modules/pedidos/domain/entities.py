from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum
from datetime import datetime
import uuid

class EstadoPedido(str, Enum):
    """El ciclo de vida oficial de un pedido en KITCHAN"""
    NUEVA = "NUEVA"
    EN_PREPARACION = "EN_PREPARACION"
    LISTA = "LISTA"
    ENTREGADA = "ENTREGADA"
    CANCELADA = "CANCELADA"

class PedidoItem(BaseModel):
    nombre: str
    cantidad: int
    precio_unitario: float
    notas: Optional[str] = None

class Pedido(BaseModel):
    """La entidad core. Todo en el sistema gira en torno a esto."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    origen: str  # Ej: "UBER_EATS", "RAPPI", "LOCAL"
    id_externo: Optional[str] = None  # El ID largo que nos manda Uber
    cliente: str
    items: List[PedidoItem]
    total: float
    estado: EstadoPedido = EstadoPedido.NUEVA
    fecha_creacion: datetime = Field(default_factory=datetime.utcnow)