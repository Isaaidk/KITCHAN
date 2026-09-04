import asyncio
import logging

from src.kitchan.core.database import AsyncSessionLocal
from src.kitchan.modules.pedidos.domain.entities import EstadoPedido
from src.kitchan.modules.pedidos.infrastructure.eventos.redis_publisher import (
    RedisPublisherAdapter,
)
from src.kitchan.modules.pedidos.infrastructure.repository import PostgresPedidoRepository

logger = logging.getLogger(__name__)

MINUTOS_LIMITE = 20
INTERVALO_BARRIDO_SEGUNDOS = 60


async def _barrer_una_vez(redis_url: str) -> None:
    async with AsyncSessionLocal() as session:
        repo = PostgresPedidoRepository(session=session)
        notificador = RedisPublisherAdapter(redis_url=redis_url)

        estancados = await repo.listar_estancados(MINUTOS_LIMITE)
        for pedido in estancados:
            actualizado = await repo.actualizar_estado(pedido.id, EstadoPedido.CANCELADA.value)
            if not actualizado:
                continue
            pedido.estado = EstadoPedido.CANCELADA
            await notificador.notificar_pedido_actualizado(pedido)
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
