"""Composición pública del módulo Pedidos.

Es el único punto donde se arman las piezas internas de `pedidos`
(repositorio de Postgres, notificador de eventos y casos de uso). El resto
de los módulos —las integraciones con Uber, PedidosYa y Rappi— dependen solo
de `get_order_dispatcher`, que les entrega el puerto `OrderDispatcherPort`,
sin conocer cómo está construido el núcleo de pedidos por dentro.
"""

import os

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.kitchan.core.database import get_db
from src.kitchan.modules.integraciones.core.domain.inter_module_ports import (
    OrderDispatcherPort,
)
from src.kitchan.modules.notificaciones.infrastructure.redis_publisher import (
    RedisPublisherAdapter,
)
from src.kitchan.modules.pedidos.application.actualizar_estado_pedido_service import (
    ActualizarEstadoPedidoUseCase,
)
from src.kitchan.modules.pedidos.application.crear_pedido_service import (
    CrearPedidoUseCase,
)
from src.kitchan.modules.pedidos.application.ports import NotificadorEventosPort
from src.kitchan.modules.pedidos.infrastructure.adapters.integraciones_dispatcher import (
    PedidosIntegracionesAdapter,
)
from src.kitchan.modules.pedidos.infrastructure.repository import (
    PostgresPedidoRepository,
)


def _redis_url() -> str:
    return os.getenv("REDIS_URL", "redis://localhost:6379/0")


def construir_notificador() -> NotificadorEventosPort:
    return RedisPublisherAdapter(redis_url=_redis_url())


def construir_actualizar_estado_use_case(
    session: AsyncSession,
) -> ActualizarEstadoPedidoUseCase:
    return ActualizarEstadoPedidoUseCase(
        repository=PostgresPedidoRepository(session=session),
        notificador=construir_notificador(),
    )


def construir_order_dispatcher(session: AsyncSession) -> OrderDispatcherPort:
    repositorio = PostgresPedidoRepository(session=session)
    notificador = construir_notificador()
    return PedidosIntegracionesAdapter(
        use_case=CrearPedidoUseCase(repository=repositorio, notificador=notificador),
        actualizar_estado_use_case=ActualizarEstadoPedidoUseCase(
            repository=repositorio, notificador=notificador
        ),
    )


def get_order_dispatcher(db: AsyncSession = Depends(get_db)) -> OrderDispatcherPort:
    """Dependencia de FastAPI para las integraciones."""
    return construir_order_dispatcher(db)
