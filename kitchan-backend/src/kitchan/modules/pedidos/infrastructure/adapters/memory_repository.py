from src.kitchan.modules.pedidos.domain.ports import PedidoRepositoryPort
from src.kitchan.modules.pedidos.domain.entities import Pedido

class MemoryPedidoRepository(PedidoRepositoryPort):
    """
    Base de datos temporal en memoria (un diccionario).
    Nos permite probar la arquitectura antes de instalar SQLAlchemy.
    """
    def __init__(self):
        self.db = {}

    async def guardar(self, pedido: Pedido) -> Pedido:
        self.db[pedido.id] = pedido
        print(f"🗄️ [DB LOCAL] Pedido guardado en memoria. ID interno: {pedido.id} | Total: ${pedido.total}")
        return pedido
        
    async def actualizar_estado(self, pedido_id: str, nuevo_estado: str) -> bool:
        if pedido_id in self.db:
            self.db[pedido_id].estado = nuevo_estado
            return True
        return False