"""Infraestructura de PedidosYa: rutas HTTP consumidas por el frontend/KDS
para disparar acciones manuales sobre un pedido de PedidosYa
(aceptar/rechazar/cancelar/marcar listo), equivalentes a las de
integraciones/uber/infrastructure/controllers/orders_api.py.

Nota de diseño: a diferencia de las rutas de Uber, estas no reciben
`restaurante_id` como query param — las llamadas salientes de PedidosYa usan
credenciales estáticas de aplicación (no un token OAuth por tenant), así que
no hace falta resolver el tenant para autenticar la llamada saliente.
"""

import logging
import os

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.kitchan.core.database import get_db
from src.kitchan.modules.integraciones.pedidosya.application.order_use_cases import (
    PedidosYaOrderUseCase,
)
from src.kitchan.modules.integraciones.pedidosya.infrastructure.adapters.http_order_adapter import (
    PedidosYaHttpAdapter,
)
from src.kitchan.modules.pedidos.application.actualizar_estado_pedido_service import (
    ActualizarEstadoPedidoUseCase,
)
from src.kitchan.modules.pedidos.application.crear_pedido_service import (
    CrearPedidoUseCase,
)
from src.kitchan.modules.pedidos.infrastructure.adapters.integraciones_dispatcher import (
    PedidosIntegracionesAdapter,
)
from src.kitchan.modules.pedidos.infrastructure.eventos.redis_publisher import (
    RedisPublisherAdapter,
)
from src.kitchan.modules.pedidos.infrastructure.repository import (
    PostgresPedidoRepository,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/integraciones/pedidosya/orders",
    tags=["Integraciones - Acciones de Pedidos PedidosYa"],
)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


class DenyOrderRequest(BaseModel):
    reason: str = "No podemos preparar el pedido en este momento."


class CancelOrderRequest(BaseModel):
    reason: str = "OTHER"


def get_order_use_case(db: AsyncSession = Depends(get_db)) -> PedidosYaOrderUseCase:
    api_adapter = PedidosYaHttpAdapter()

    repo_pedidos = PostgresPedidoRepository(session=db)
    notificador = RedisPublisherAdapter(redis_url=REDIS_URL)
    crear_pedido_uc = CrearPedidoUseCase(
        repository=repo_pedidos, notificador=notificador
    )
    actualizar_estado_uc = ActualizarEstadoPedidoUseCase(
        repository=repo_pedidos, notificador=notificador
    )
    dispatcher = PedidosIntegracionesAdapter(
        use_case=crear_pedido_uc, actualizar_estado_use_case=actualizar_estado_uc
    )

    return PedidosYaOrderUseCase(pedidosya_api=api_adapter, order_dispatcher=dispatcher)


@router.post("/{order_id}/accept")
async def accept_pedidosya_order(
    order_id: str, use_case: PedidosYaOrderUseCase = Depends(get_order_use_case)
):
    try:
        await use_case.accept_order_in_pedidosya(order_id)
        return {
            "status": "success",
            "message": f"Pedido {order_id} aceptado en PedidosYa.",
        }
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error inesperado aceptando el pedido %s", order_id)
        raise HTTPException(
            status_code=500, detail="Error interno al aceptar el pedido."
        )


@router.post("/{order_id}/deny")
async def deny_pedidosya_order(
    order_id: str,
    payload: DenyOrderRequest,
    use_case: PedidosYaOrderUseCase = Depends(get_order_use_case),
):
    try:
        await use_case.deny_order_in_pedidosya(order_id, payload.reason)
        return {
            "status": "success",
            "message": f"Pedido {order_id} rechazado en PedidosYa.",
        }
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error inesperado rechazando el pedido %s", order_id)
        raise HTTPException(
            status_code=500, detail="Error interno al rechazar el pedido."
        )


@router.post("/{order_id}/cancel")
async def cancel_pedidosya_order(
    order_id: str,
    payload: CancelOrderRequest,
    use_case: PedidosYaOrderUseCase = Depends(get_order_use_case),
):
    try:
        await use_case.cancel_order_in_pedidosya(order_id, payload.reason)
        return {
            "status": "success",
            "message": f"Pedido {order_id} cancelado en PedidosYa.",
        }
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error inesperado cancelando el pedido %s", order_id)
        raise HTTPException(
            status_code=500, detail="Error interno al cancelar el pedido."
        )


@router.post("/{order_id}/ready")
async def ready_pedidosya_order(
    order_id: str, use_case: PedidosYaOrderUseCase = Depends(get_order_use_case)
):
    try:
        await use_case.mark_order_ready_in_pedidosya(order_id)
        return {
            "status": "success",
            "message": f"Pedido {order_id} marcado como listo en PedidosYa.",
        }
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error inesperado marcando pedido %s como listo", order_id)
        raise HTTPException(
            status_code=500, detail="Error interno al marcar el pedido como listo."
        )
