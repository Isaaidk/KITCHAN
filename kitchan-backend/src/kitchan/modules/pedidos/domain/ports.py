from abc import ABC, abstractmethod
from src.kitchan.modules.pedidos.domain.entities import Pedido

class PedidoRepositoryPort(ABC):
    @abstractmethod
    async def guardar(self, pedido: Pedido) -> Pedido:
        """
        Guarda un pedido en la base de datos y retorna la entidad guardada.
        """
        pass

    @abstractmethod
    async def actualizar_estado(self, pedido_id: str, nuevo_estado: str) -> bool:
        """
        Actualiza el estado de un pedido en la base de datos.
        Retorna True si fue exitoso, False si el pedido no existe.
        """
        pass
    