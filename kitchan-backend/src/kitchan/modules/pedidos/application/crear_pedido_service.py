from src.kitchan.modules.pedidos.domain.entities import Pedido
from src.kitchan.modules.pedidos.domain.ports import PedidoRepositoryPort
#/workspaces/KITCHAN/kitchan-backend/src/kitchan/modules/pedidos/domain/ports/ports.py

class CrearPedidoUseCase:
    """
    Orquesta la creación de un nuevo pedido en el restaurante.
    """
    def __init__(self, repository: PedidoRepositoryPort):
        self.repository = repository

    async def ejecutar(self, pedido: Pedido) -> str:
        # Aquí validamos reglas de negocio internas
        if pedido.total <= 0:
            raise ValueError("Un pedido no puede tener un total de $0 o negativo.")
            
        if not pedido.items:
            raise ValueError("Un pedido debe tener al menos un producto.")

        # Guardamos en la base de datos a través del puerto
        pedido_guardado = await self.repository.guardar(pedido)
        
        print(f"🍳 [COCINA] Pedido interno {pedido_guardado.id} creado exitosamente.")
        return pedido_guardado.id