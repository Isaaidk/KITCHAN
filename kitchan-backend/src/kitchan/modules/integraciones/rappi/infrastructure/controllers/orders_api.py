"""Infraestructura de Rappi: rutas HTTP consumidas por el frontend/KDS para
disparar acciones manuales sobre un pedido de Rappi (aceptar/rechazar/marcar
listo), equivalentes a las de las integraciones de Uber y PedidosYa.

Diferencias con esas rutas:
- No hay /cancel: la API pública de Rappi no documenta cómo cancelar un
  pedido ya tomado; /deny (reject) solo vale mientras está en SENT.
- Se exige un usuario de KITCHAN autenticado (Bearer JWT) y dueño del pedido.
"""

import logging
import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.kitchan.modules.integraciones.rappi.application.order_use_cases import (
    RappiOrderUseCase,
)
from src.kitchan.modules.integraciones.rappi.infrastructure.adapters.http_order_adapter import (
    RappiHttpAdapter,
)
from src.kitchan.modules.integraciones.rappi.infrastructure.adapters.redis_token_adapter import (
    RedisRappiTokenAdapter,
)
from src.kitchan.modules.integraciones.core.domain.inter_module_ports import (
    OrderDispatcherPort,
)
from src.kitchan.modules.pedidos.infrastructure.dependencias import get_order_dispatcher
from src.kitchan.modules.integraciones.core.infrastructure.seguridad import (
    usuario_duenio_del_pedido,
)
from src.kitchan.modules.integraciones.core.infrastructure.errores import (
    error_de_plataforma,
)

logger = logging.getLogger(__name__)

# Solo usuarios de KITCHAN dueños del pedido (ver core/infrastructure/seguridad.py).
requiere_duenio = usuario_duenio_del_pedido("RAPPI")

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


def get_order_use_case(
    order_dispatcher: OrderDispatcherPort = Depends(get_order_dispatcher),
) -> RappiOrderUseCase:
    token_adapter = RedisRappiTokenAdapter(redis_url=REDIS_URL)
    api_adapter = RappiHttpAdapter(token_cache=token_adapter)

    return RappiOrderUseCase(rappi_api=api_adapter, order_dispatcher=order_dispatcher)


@router.post("/{order_id}/accept")
async def accept_rappi_order(
    order_id: str,
    payload: Optional[AcceptOrderRequest] = None,
    _usuario: dict = Depends(requiere_duenio),
    use_case: RappiOrderUseCase = Depends(get_order_use_case),
):
    cooking_time = payload.cooking_time if payload else None
    try:
        await use_case.accept_order_in_rappi(order_id, cooking_time)
        return {
            "status": "success",
            "message": f"Pedido {order_id} aceptado en Rappi.",
        }
    except HTTPException as e:
        raise error_de_plataforma(e, "Rappi")
    except Exception:
        logger.exception("Error inesperado aceptando el pedido %s", order_id)
        raise HTTPException(
            status_code=500, detail="Error interno al aceptar el pedido."
        )


@router.post("/{order_id}/deny")
async def deny_rappi_order(
    order_id: str,
    payload: DenyOrderRequest,
    _usuario: dict = Depends(requiere_duenio),
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
    except HTTPException as e:
        raise error_de_plataforma(e, "Rappi")
    except Exception:
        logger.exception("Error inesperado rechazando el pedido %s", order_id)
        raise HTTPException(
            status_code=500, detail="Error interno al rechazar el pedido."
        )


@router.post("/{order_id}/ready")
async def ready_rappi_order(
    order_id: str,
    _usuario: dict = Depends(requiere_duenio),
    use_case: RappiOrderUseCase = Depends(get_order_use_case),
):
    try:
        await use_case.mark_order_ready_in_rappi(order_id)
        return {
            "status": "success",
            "message": f"Pedido {order_id} marcado como listo en Rappi.",
        }
    except HTTPException as e:
        raise error_de_plataforma(e, "Rappi")
    except Exception:
        logger.exception("Error inesperado marcando pedido %s como listo", order_id)
        raise HTTPException(
            status_code=500, detail="Error interno al marcar el pedido como listo."
        )
