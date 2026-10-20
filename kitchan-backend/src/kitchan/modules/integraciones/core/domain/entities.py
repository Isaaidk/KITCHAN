"""Dominio compartido de integraciones: DTOs neutrales (agnósticos de
plataforma) que cualquier integración (Uber, PedidosYa, ...) usa para hablar
con el módulo de Pedidos a través de OrderDispatcherPort.
"""

from pydantic import BaseModel
from typing import Optional


class KitchanOrderItem(BaseModel):
    """Modelo interno para los productos de una orden"""

    nombre: str
    cantidad: int
    precio_unitario: float
    notas_especiales: Optional[str] = None


class KitchanOrderDTO(BaseModel):
    """Modelo interno estandarizado para KITCHAN (Capa Anticorrupción).

    Antes vivía en integraciones.uber.domain.models pese a no tener nada
    específico de Uber (de ahí que OrderDispatcherPort ya lo usaba como si
    fuera neutral). Se movió aquí al agregar la segunda integración real
    (PedidosYa) para que el puerto compartido no dependa del paquete de Uber.
    """

    id_externo: str
    plataforma: str = "UBER_EATS"
    restaurante_id: str
    nombre_cliente: str
    items: list[KitchanOrderItem]
    total: float
    estado: str = "NUEVA"
