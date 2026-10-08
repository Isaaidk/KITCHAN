import asyncio
import logging

from src.kitchan.core.database import AsyncSessionLocal
from src.kitchan.modules.pedidos.application.actualizar_estado_pedido_service import (
    ESTADOS_QUE_YA_NO_SE_CANCELAN,
    ActualizarEstadoPedidoUseCase,
)
from src.kitchan.modules.pedidos.domain.entities import EstadoPedido
from src.kitchan.modules.notificaciones.infrastructure.redis_publisher import (
    RedisPublisherAdapter,
)
from src.kitchan.modules.pedidos.infrastructure.repository import (
    PostgresPedidoRepository,
)

logger = logging.getLogger(__name__)

MINUTOS_LIMITE = 20
INTERVALO_BARRIDO_SEGUNDOS = 60


async def _barrer_una_vez(redis_url: str) -> None:
    async with AsyncSessionLocal() as session:
        repo = PostgresPedidoRepository(session=session)
        notificador = RedisPublisherAdapter(redis_url=redis_url)
        # La cancelación pasa por el caso de uso (y no directo por el
        # repositorio) para respetar las reglas de negocio de pedidos: un
        # pedido LISTA ya no se cancela aunque lleve tiempo sin moverse.
        caso_uso = ActualizarEstadoPedidoUseCase(
            repository=repo, notificador=notificador
        )

        estancados = await repo.listar_estancados(MINUTOS_LIMITE)
        for pedido in estancados:
            # Se filtran antes para no reintentar (y loguear) en cada barrido
            # una cancelación que el caso de uso siempre va a ignorar.
            if pedido.estado in ESTADOS_QUE_YA_NO_SE_CANCELAN:
                continue
            actualizado = await caso_uso.ejecutar_por_id(
                pedido.id, EstadoPedido.CANCELADA
            )
            if actualizado is None or actualizado.estado != EstadoPedido.CANCELADA:
                continue
            logger.info(
                "⏱️ Pedido %s auto-cancelado: sin cambios en más de %s minutos.",
                pedido.id,
                MINUTOS_LIMITE,
            )


async def _bucle_auto_cancelar(redis_url: str) -> None:
    while True:
        try:
            await _barrer_una_vez(redis_url)
        except Exception:
            logger.exception("Error en el barrido de auto-cancelación de pedidos.")
        await asyncio.sleep(INTERVALO_BARRIDO_SEGUNDOS)


def iniciar_auto_cancelador(redis_url: str) -> asyncio.Task:
    return asyncio.create_task(_bucle_auto_cancelar(redis_url))
