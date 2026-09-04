from abc import ABC, abstractmethod
from src.kitchan.modules.integraciones.uber.domain.models import KitchanOrderDTO

class OrderDispatcherPort(ABC):
    """
    Puerto de salida. Integraciones usará esto para enviar pedidos limpios
    a cualquier otro módulo del sistema, sin acoplarse a su base de datos.
    """
    @abstractmethod
    async def dispatch_new_order(self, order: KitchanOrderDTO) -> str:
        """Debe enviar la orden y retornar el ID interno generado en Kitchan"""
        pass