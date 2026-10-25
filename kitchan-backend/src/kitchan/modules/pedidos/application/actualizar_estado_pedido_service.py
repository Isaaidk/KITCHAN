import logging
from typing import Optional

from src.kitchan.modules.pedidos.application.ports import NotificadorEventosPort
from src.kitchan.modules.pedidos.domain.entities import EstadoPedido, Pedido
from src.kitchan.modules.pedidos.domain.ports import PedidoRepositoryPort

logger = logging.getLogger(__name__)

# Una vez que la cocina terminó (LISTA) o el pedido se dio por completo
# (ENTREGADA), ya no se puede "descancelar" hacia atrás: el trabajo de
# cocina ya se hizo y KITCHAN cobra por eso independientemente de que Uber
# no consiga motorizado después. Solo lo que pasa ANTES de LISTA (courier
# nunca llegó a asignarse) puede terminar en CANCELADA.
ESTADOS_QUE_YA_NO_SE_CANCELAN = {EstadoPedido.LISTA, EstadoPedido.ENTREGADA}

# Estados terminales: ya no cambian por ningún evento (ni atrasado ni manual).
ESTADOS_FINALES = {EstadoPedido.ENTREGADA, EstadoPedido.CANCELADA}


class ActualizarEstadoPedidoUseCase:
    """
    Orquesta el cambio de estado (cocina o entrega) de un pedido existente,
    sin importar qué integración lo disparó, y notifica automáticamente (WS).
    """

    def __init__(
        self,
        repository: PedidoRepositoryPort,
        notificador: Optional[NotificadorEventosPort] = None,
    ):
        self.repository = repository
        self.notificador = notificador

    async def ejecutar_por_id_externo(
        self, origen: str, id_externo: str, nuevo_estado: EstadoPedido
    ) -> Optional[Pedido]:
        pedido = await self.repository.buscar_por_id_externo(origen, id_externo)
        if pedido is None:
            return None
        return await self._transicionar(pedido, nuevo_estado)

    async def ejecutar_por_id(
        self, pedido_id: str, nuevo_estado: EstadoPedido
    ) -> Optional[Pedido]:
        """Transición de estado puramente interna a KITCHAN (no requiere
        origen/id_externo), usada por acciones que no vienen de una
        integración — ej. marcar "Entregado" manualmente desde el KDS."""
        pedido = await self.repository.buscar_por_id(pedido_id)
        if pedido is None:
            return None
        return await self._transicionar(pedido, nuevo_estado)

    async def _transicionar(self, pedido: Pedido, nuevo_estado: EstadoPedido) -> Pedido:
        if (
            nuevo_estado == EstadoPedido.CANCELADA
            and pedido.estado in ESTADOS_QUE_YA_NO_SE_CANCELAN
        ):
            logger.info(
                "Se ignora intento de cancelar el pedido %s: ya está en %s "
                "(la cocina ya completó su parte, no se revierte).",
                pedido.id,
                pedido.estado.value,
            )
            return pedido

        if pedido.estado == nuevo_estado:
            # Mismo estado (evento repetido o dos clics): no hay nada que hacer.
            return pedido

        if pedido.estado in ESTADOS_FINALES:
            # Un evento atrasado no reabre un pedido que ya terminó.
            logger.info(
                "Se ignora el cambio de %s a %s del pedido %s: ya está finalizado.",
                pedido.estado.value,
                nuevo_estado.value,
                pedido.id,
            )
            return pedido

        # El cambio solo se aplica si el pedido sigue en el estado que leímos;
        # así, si otro operador lo movió mientras tanto, no se pisa su cambio.
        actualizado = await self.repository.actualizar_estado(
            pedido.id, nuevo_estado.value, estado_esperado=pedido.estado.value
        )
        if not actualizado:
            vigente = await self.repository.buscar_por_id(pedido.id)
            logger.info(
                "Conflicto al cambiar el pedido %s a %s: ya no estaba en %s.",
                pedido.id,
                nuevo_estado.value,
                pedido.estado.value,
            )
            return vigente or pedido

        pedido.estado = nuevo_estado
        if self.notificador is not None:
            await self.notificador.notificar_pedido_actualizado(pedido)
        return pedido

    async def actualizar_estado_entrega(
        self, origen: str, id_externo: str, estado_entrega: str
    ) -> Optional[Pedido]:
        pedido = await self.repository.buscar_por_id_externo(origen, id_externo)
        if pedido is None:
            return None

        actualizado = await self.repository.actualizar_estado_entrega(
            pedido.id, estado_entrega
        )
        if not actualizado:
            return None

        pedido.estado_entrega = estado_entrega
        if self.notificador is not None:
            await self.notificador.notificar_pedido_actualizado(pedido)
        return pedido
