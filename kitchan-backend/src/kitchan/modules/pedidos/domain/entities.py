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
    restaurante_id: str
    origen: str  # Ej: "UBER_EATS", "RAPPI", "LOCAL"
    id_externo: Optional[str] = None  # El ID largo que nos manda Uber
    cliente: str
    nota_cliente: Optional[str] = None
    # Datos de contacto y entrega que informa el canal; None cuando no los da.
    telefono_cliente: Optional[str] = None
    tipo_entrega: Optional[str] = None  # DOMICILIO | RETIRO
    direccion_entrega: Optional[str] = None
    items: List[PedidoItem]
    total: float
    estado: EstadoPedido = EstadoPedido.NUEVA
    estado_entrega: Optional[str] = None
    fecha_creacion: datetime = Field(default_factory=datetime.utcnow)
    # Último cambio de estado (lo asigna la base de datos); None si el pedido
    # todavía no se guardó.
    fecha_actualizacion: Optional[datetime] = None
    # Cómo se pagó (EFECTIVO, TARJETA, ...). None cuando el canal no lo informa:
    # nunca se inventa un valor.
    metodo_pago: Optional[str] = None
    # Momentos exactos en que la cocina empezó (aceptó) y terminó el pedido.
    # Con ellos el tiempo de preparación no depende del "último cambio de estado".
    fecha_aceptacion: Optional[datetime] = None
    fecha_lista: Optional[datetime] = None
    # Usuario de KITCHAN que aceptó el pedido (None si lo aceptó el sistema o es anterior).
    aceptado_por_id: Optional[str] = None
