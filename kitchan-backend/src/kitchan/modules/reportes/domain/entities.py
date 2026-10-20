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
class PedidoResumen:
    origen: str
    total: float
    estado: str
    fecha_creacion: datetime
    fecha_actualizacion: Optional[datetime] = None
