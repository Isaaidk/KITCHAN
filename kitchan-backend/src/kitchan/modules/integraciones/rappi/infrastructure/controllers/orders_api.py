"""Infraestructura de Rappi: rutas HTTP consumidas por el frontend/KDS para
disparar acciones manuales sobre un pedido de Rappi (aceptar/rechazar/marcar
listo), equivalentes a las de las integraciones de Uber y PedidosYa.

Diferencias con esas rutas:
- No hay /cancel: la API pública de Rappi no documenta cómo cancelar un
  pedido ya tomado; /deny (reject) solo vale mientras está en SENT.
- Se exige un usuario de KITCHAN autenticado (Bearer JWT), igual que en
  pedidos/rest_api.py.
"""

import logging
import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.kitchan.core.database import get_db
from src.kitchan.modules.integraciones.rappi.application.order_use_cases import (
    RappiOrderUseCase,
)
from src.kitchan.modules.integraciones.rappi.infrastructure.adapters.http_order_adapter import (
    RappiHttpAdapter,
)
from src.kitchan.modules.integraciones.rappi.infrastructure.adapters.redis_token_adapter import (
    RedisRappiTokenAdapter,
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
from src.kitchan.modules.usuarios.infrastructure.auth_dependencies import (
    obtener_usuario_actual,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/integraciones/rappi/orders",
    tags=["Integraciones - Acciones de Pedidos Rappi"],
)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


class AcceptOrderRequest(BaseModel):
    # Minutos de preparación; si es None, Rappi usa el de la tienda.
    cooking_time: Optional[int] = None


class DenyOrderRequest(BaseModel):
    # Valores válidos según Rappi: ITEM_WRONG_PRICE, ITEM_NOT_FOUND,
    # ITEM_OUT_OF_STOCK, ORDER_MISSING_INFORMATION,
    # ORDER_MISSING_ADDRESS_INFORMATION, ORDER_TOTAL_INCORRECT.
    cancel_type: str = "ITEM_OUT_OF_STOCK"
    reason: str = "No podemos preparar el pedido en este momento."


def get_order_use_case(db: AsyncSession = Depends(get_db)) -> RappiOrderUseCase:
    token_adapter = RedisRappiTokenAdapter(redis_url=REDIS_URL)
    api_adapter = RappiHttpAdapter(token_cache=token_adapter)

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

    return RappiOrderUseCase(rappi_api=api_adapter, order_dispatcher=dispatcher)


@router.post("/{order_id}/accept")
async def accept_rappi_order(
    order_id: str,
    payload: Optional[AcceptOrderRequest] = None,
    _usuario: dict = Depends(obtener_usuario_actual),
    use_case: RappiOrderUseCase = Depends(get_order_use_case),
):
    cooking_time = payload.cooking_time if payload else None
    try:
        await use_case.accept_order_in_rappi(order_id, cooking_time)
        return {
            "status": "success",
            "message": f"Pedido {order_id} aceptado en Rappi.",
        }
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error inesperado aceptando el pedido %s", order_id)
        raise HTTPException(
            status_code=500, detail="Error interno al aceptar el pedido."
        )


@router.post("/{order_id}/deny")
async def deny_rappi_order(
    order_id: str,
    payload: DenyOrderRequest,
    _usuario: dict = Depends(obtener_usuario_actual),
    use_case: RappiOrderUseCase = Depends(get_order_use_case),
):
    try:
        await use_case.deny_order_in_rappi(
            order_id, reason=payload.reason, cancel_type=payload.cancel_type
        )
        return {
            "status": "success",
            "message": f"Pedido {order_id} rechazado en Rappi.",
        }
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error inesperado rechazando el pedido %s", order_id)
        raise HTTPException(
            status_code=500, detail="Error interno al rechazar el pedido."
        )


@router.post("/{order_id}/ready")
async def ready_rappi_order(
    order_id: str,
    _usuario: dict = Depends(obtener_usuario_actual),
    use_case: RappiOrderUseCase = Depends(get_order_use_case),
):
    try:
        await use_case.mark_order_ready_in_rappi(order_id)
        return {
            "status": "success",
            "message": f"Pedido {order_id} marcado como listo en Rappi.",
        }
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error inesperado marcando pedido %s como listo", order_id)
        raise HTTPException(
            status_code=500, detail="Error interno al marcar el pedido como listo."
        )
