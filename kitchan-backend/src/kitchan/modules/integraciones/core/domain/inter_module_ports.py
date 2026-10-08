"""Dominio compartido de integraciones: puerto de salida que cualquier
integración (Uber, PedidosYa, ...) usa para enviar pedidos al módulo de
Pedidos, sin conocer su base de datos ni su modelo de persistencia.
"""
from abc import ABC, abstractmethod
from src.kitchan.modules.integraciones.core.domain.entities import KitchanOrderDTO


class OrderDispatcherPort(ABC):
    """
    Puerto de salida. Integraciones usará esto para enviar pedidos limpios
    a cualquier otro módulo del sistema, sin acoplarse a su base de datos.
    """

    @abstractmethod
    async def dispatch_new_order(self, order: KitchanOrderDTO) -> str:
        """Debe enviar la orden y retornar el ID interno generado en Kitchan"""
        pass

    @abstractmethod
    async def order_already_exists(self, origen: str, id_externo: str) -> bool:
        """
        Permite a una integración comprobar, antes de despachar, si un pedido
        con ese id externo ya fue creado — necesario para integraciones cuyo
        proveedor puede reenviar la misma notificación más de una vez (ej.
        PedidosYa documenta explícitamente entregas duplicadas), sin que la
        integración tenga que acoplarse al repositorio de Pedidos.
        """
        pass

    @abstractmethod
    async def dispatch_order_status_update(
        self, origen: str, id_externo: str, nuevo_estado: str
    ) -> bool:
        """
        Actualiza el estado (cocina) de un pedido ya existente, identificado
        por el id que le dio la plataforma externa. Retorna True si se
        encontró y actualizó el pedido.
        """
        pass

    @abstractmethod
    async def dispatch_delivery_status_update(
        self, origen: str, id_externo: str, estado_entrega: str
    ) -> bool:
        """
        Actualiza el estado de entrega/delivery (courier) de un pedido ya
        existente. Retorna True si se encontró y actualizó el pedido.
        """
        pass
