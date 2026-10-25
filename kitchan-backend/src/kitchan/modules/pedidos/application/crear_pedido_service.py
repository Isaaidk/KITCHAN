import logging
from typing import Optional

from src.kitchan.modules.pedidos.application.ports import NotificadorEventosPort
from src.kitchan.modules.pedidos.domain.entities import Pedido
from src.kitchan.modules.pedidos.domain.exceptions import PedidoDuplicadoError
from src.kitchan.modules.pedidos.domain.ports import PedidoRepositoryPort

logger = logging.getLogger(__name__)


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

        # Idempotencia: las plataformas reenvían webhooks (reintentos, timeouts).
        # Si el pedido ya existe se devuelve el mismo, sin crearlo ni avisar de
        # nuevo a cocina.
        if pedido.id_externo is not None:
            existente = await self.repository.buscar_por_id_externo(
                pedido.origen, pedido.id_externo
            )
            if existente is not None:
                return self._ya_existia(existente)

        # Guardamos en la base de datos a través del puerto
        try:
            pedido_guardado = await self.repository.guardar(pedido)
        except PedidoDuplicadoError:
            # Dos webhooks iguales llegaron a la vez y el otro ganó la carrera.
            existente = await self.repository.buscar_por_id_externo(
                pedido.origen, pedido.id_externo
            )
            if existente is None:
                raise
            return self._ya_existia(existente)

        if self.notificador is not None:
            await self.notificador.notificar_pedido_creado(pedido_guardado)

        print(f"🍳 [COCINA] Pedido interno {pedido_guardado.id} creado exitosamente.")
        return pedido_guardado.id

    @staticmethod
    def _ya_existia(existente: Pedido) -> str:
        logger.info(
            "Pedido duplicado ignorado: %s %s ya existe como %s.",
            existente.origen,
            existente.id_externo,
            existente.id,
        )
        return existente.id
