"""Dominio de Reportes: el modelo de lectura propio del módulo.

Reportes no usa la entidad `Pedido` ni la tabla de `pedidos`: trabaja con un
resumen que solo tiene los campos que necesitan las métricas.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

# Estados con los que se calculan las métricas (mismos valores que pedidos).
ESTADO_LISTA = "LISTA"
ESTADO_ENTREGADA = "ENTREGADA"
ESTADO_CANCELADA = "CANCELADA"


@dataclass(frozen=True)
class ItemResumen:
    nombre: str
    cantidad: int
    precio_unitario: float


@dataclass(frozen=True)
class PedidoResumen:
    origen: str
    total: float
    estado: str
    fecha_creacion: datetime
    fecha_actualizacion: Optional[datetime] = None
    # Campos para el dashboard de analíticas (productos, clientes y pagos).
    cliente: str = ""
    items: tuple[ItemResumen, ...] = ()
    # None cuando el canal no informó cómo se pagó el pedido.
    metodo_pago: Optional[str] = None
    # Momentos exactos de cocina (None en pedidos anteriores a que se guardaran).
    fecha_aceptacion: Optional[datetime] = None
    fecha_lista: Optional[datetime] = None
    # Usuario de KITCHAN que aceptó el pedido (None si no se sabe).
    aceptado_por_id: Optional[str] = None
