from abc import ABC, abstractmethod
from src.kitchan.modules.integraciones.uber.domain.models import KitchanOrderDTO

class OrderDispatcherPort(ABC):
    """
    Puerto de salida. Integraciones usará esto para enviar pedidos limpios
    a cualquier otro módulo del sistema, sin acoplarse a su base de datos.

    NOTA (deuda técnica preexistente): este puerto compartido depende de
    KitchanOrderDTO definido en integraciones.uber.domain.models en vez de un
    DTO neutral en este mismo paquete (integraciones.core). No se corrige en
    este cambio para minimizar el diff; queda documentado para una futura
    limpieza cuando se agregue una segunda integración real (Rappi/PedidosYa).
    """
    @abstractmethod
    async def dispatch_new_order(self, order: KitchanOrderDTO) -> str:
        """Debe enviar la orden y retornar el ID interno generado en Kitchan"""
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