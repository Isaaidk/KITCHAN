import os
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
import logging

# Importamos nuestro Caso de Uso y los Adaptadores
from src.kitchan.modules.integraciones.uber.application.order_use_cases import UberOrderUseCase
from src.kitchan.modules.integraciones.uber.infrastructure.adapters.redis_token_adapter import RedisUberTokenAdapter
from src.kitchan.modules.integraciones.uber.infrastructure.adapters.http_order_adapter import UberHttpAdapter
from src.kitchan.modules.pedidos.application.crear_pedido_service import CrearPedidoUseCase
from src.kitchan.modules.pedidos.infrastructure.adapters.integraciones_dispatcher import PedidosIntegracionesAdapter

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/integraciones/uber/orders",
    tags=["Integraciones - Acciones de Pedidos Uber"]
)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Modelo de Pydantic para el body del endpoint de rechazo
class DenyOrderRequest(BaseModel):
    reason_code: str = "OTHER"  # Opciones comunes: ITEM_OUT_OF_STOCK, KITCHEN_CLOSED, OTHER
    explanation: str = "No podemos preparar el pedido en este momento."

# Inyección de Dependencias
def get_order_use_case() -> UberOrderUseCase:
    token_adapter = RedisUberTokenAdapter(redis_url=REDIS_URL)
    api_adapter = UberHttpAdapter()
    crear_pedido_uc = CrearPedidoUseCase(...)
    dispatcher = PedidosIntegracionesAdapter(use_case=crear_pedido_uc)



    return UberOrderUseCase(
        token_cache=token_adapter, 
        uber_api=api_adapter,
        order_dispatcher=dispatcher # <--- ESTO ES LO QUE FALTABA
    )

@router.post("/{order_id}/accept")
async def accept_uber_order(
    order_id: str,
    restaurante_id: str = Query(..., description="ID del restaurante en Kitchan"),
    use_case: UberOrderUseCase = Depends(get_order_use_case)
):
    """
    Endpoint consumido por el frontend para ACEPTAR un pedido en Uber Eats.
    """
    try:
        await use_case.accept_order_in_uber(order_id, restaurante_id)
        return {"status": "success", "message": f"Pedido {order_id} aceptado en Uber Eats."}
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error interno al aceptar el pedido.")

@router.post("/{order_id}/deny")
async def deny_uber_order(
    order_id: str,
    payload: DenyOrderRequest,
    restaurante_id: str = Query(..., description="ID del restaurante en Kitchan"),
    use_case: UberOrderUseCase = Depends(get_order_use_case)
):
    """
    Endpoint consumido por el frontend para RECHAZAR un pedido en Uber Eats.
    """
    try:
        await use_case.deny_order_in_uber(
            order_id=order_id, 
            restaurante_id=restaurante_id, 
            reason=payload.reason_code, 
            explanation=payload.explanation
        )
        return {"status": "success", "message": f"Pedido {order_id} rechazado en Uber Eats."}
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error interno al rechazar el pedido.")

@router.post("/{order_id}/ready")
async def ready_uber_order(
    order_id: str,
    restaurante_id: str = Query(
        ...,
        description="ID del restaurante en Kitchan"
    ),
    use_case: UberOrderUseCase = Depends(
        get_order_use_case
    )
):
    try:
        await use_case.mark_order_ready_in_uber(
            order_id=order_id,
            restaurante_id=restaurante_id
        )

        return {
            "status": "success",
            "message": (
                f"Pedido {order_id} "
                "marcado como listo para pickup en Uber Eats."
            )
        }

    except ValueError as e:
        raise HTTPException(
            status_code=401,
            detail=str(e)
        )

    except Exception as error:
        logger.exception(
            "❌ Error marcando pedido Uber %s como READY",
            order_id
        )

        raise HTTPException(
            status_code=500,
            detail="Error interno al marcar el pedido como listo."
        )

@router.get("/{order_id}/delivery-status")
async def get_delivery_order_status(
    order_id: str,
    restaurante_id: str = Query(
        ...,
        description="ID del restaurante en Kitchan"
    ),
    use_case: UberOrderUseCase = Depends(
        get_order_use_case
    )
):
    try:
        return await use_case.get_delivery_order_status(
            order_id=order_id,
            restaurante_id=restaurante_id
        )

    except ValueError as e:
        raise HTTPException(
            status_code=401,
            detail=str(e)
        )

    except Exception:
        logger.exception(
            "❌ Error obteniendo estado delivery de Uber %s",
            order_id
        )

        raise HTTPException(
            status_code=500,
            detail="Error obteniendo estado del pedido en Uber."
        )