import asyncio
import logging
import os

from src.kitchan.core.database import AsyncSessionLocal
from src.kitchan.core.tareas import propagar_si_cancelada
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

MINUTOS_LIMITE_POR_DEFECTO = 20
INTERVALO_BARRIDO_SEGUNDOS = 60


def minutos_limite() -> int:
    """Minutos sin cambios tras los que un pedido se cancela solo. Se configura
    con AUTO_CANCELAR_MINUTOS; un valor vacío, inválido o <= 0 usa el de por
    defecto para no cancelar todo por error."""
    valor = os.getenv("AUTO_CANCELAR_MINUTOS", "").strip()
    try:
        minutos = int(valor)
    except ValueError:
        return MINUTOS_LIMITE_POR_DEFECTO
    return minutos if minutos > 0 else MINUTOS_LIMITE_POR_DEFECTO


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

        limite = minutos_limite()
        estancados = await repo.listar_estancados(limite)
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
                limite,
            )


async def _bucle_auto_cancelar(redis_url: str) -> None:
    while True:
        try:
            await _barrer_una_vez(redis_url)
        except Exception:
            propagar_si_cancelada()
            logger.exception("Error en el barrido de auto-cancelación de pedidos.")
        await asyncio.sleep(INTERVALO_BARRIDO_SEGUNDOS)


def iniciar_auto_cancelador(redis_url: str) -> asyncio.Task:
    return asyncio.create_task(_bucle_auto_cancelar(redis_url))
