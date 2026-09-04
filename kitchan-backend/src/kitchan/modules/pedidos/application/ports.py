from abc import ABC, abstractmethod

from src.kitchan.modules.pedidos.domain.entities import Pedido


class NotificadorEventosPort(ABC):
    """
    Puerto de salida: pedidos lo usa para avisar en tiempo real (WebSocket vía
    Redis pub/sub) cuando un pedido se crea o cambia de estado. Ninguna
    integración conoce este puerto directamente — solo los casos de uso de
    pedidos, que son quienes "orquestan" la emisión de eventos.
    """

    @abstractmethod
    async def notificar_pedido_creado(self, pedido: Pedido) -> None:
        pass

    @abstractmethod
    async def notificar_pedido_actualizado(self, pedido: Pedido) -> None:
        pass
