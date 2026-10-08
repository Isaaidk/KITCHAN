from typing import Optional

from src.kitchan.modules.pedidos.application.ports import NotificadorEventosPort
from src.kitchan.modules.pedidos.domain.entities import Pedido
from src.kitchan.modules.pedidos.domain.ports import PedidoRepositoryPort


class CrearPedidoUseCase:
    """
    Orquesta la creación de un nuevo pedido en el restaurante y notifica
    automáticamente (WS) a quien esté escuchando ese restaurante.
    """

    def __init__(
        self,
        repository: PedidoRepositoryPort,
        notificador: Optional[NotificadorEventosPort] = None,
    ):
        self.repository = repository
        self.notificador = notificador

    async def ejecutar(self, pedido: Pedido) -> str:
        # Aquí validamos reglas de negocio internas
        if pedido.total <= 0:
            raise ValueError("Un pedido no puede tener un total de $0 o negativo.")

        if not pedido.items:
            raise ValueError("Un pedido debe tener al menos un producto.")

        # Guardamos en la base de datos a través del puerto
        pedido_guardado = await self.repository.guardar(pedido)

        if self.notificador is not None:
            await self.notificador.notificar_pedido_creado(pedido_guardado)

        print(f"🍳 [COCINA] Pedido interno {pedido_guardado.id} creado exitosamente.")
        return pedido_guardado.id
