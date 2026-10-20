"""Infraestructura de PedidosYa: rutas HTTP consumidas por el frontend/KDS
para disparar acciones manuales sobre un pedido de PedidosYa
(aceptar/rechazar/cancelar/marcar listo), equivalentes a las de
integraciones/uber/infrastructure/controllers/orders_api.py.

Nota de diseño: a diferencia de las rutas de Uber, estas no reciben
`restaurante_id` como query param — las llamadas salientes de PedidosYa usan
credenciales estáticas de aplicación (no un token OAuth por tenant), así que
no hace falta resolver el tenant para autenticar la llamada saliente. Por lo
mismo, cada ruta exige un usuario de KITCHAN autenticado y dueño del pedido.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.kitchan.modules.integraciones.pedidosya.application.order_use_cases import (
    PedidosYaOrderUseCase,
)
from src.kitchan.modules.integraciones.pedidosya.infrastructure.adapters.http_order_adapter import (
    PedidosYaHttpAdapter,
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
requiere_duenio = usuario_duenio_del_pedido("PEDIDOS_YA")

router = APIRouter(
    prefix="/api/v1/integraciones/pedidosya/orders",
    tags=["Integraciones - Acciones de Pedidos PedidosYa"],
)


class DenyOrderRequest(BaseModel):
    reason: str = "No podemos preparar el pedido en este momento."


class CancelOrderRequest(BaseModel):
    reason: str = "OTHER"


def get_order_use_case(
    order_dispatcher: OrderDispatcherPort = Depends(get_order_dispatcher),
) -> PedidosYaOrderUseCase:
    api_adapter = PedidosYaHttpAdapter()

    return PedidosYaOrderUseCase(
        pedidosya_api=api_adapter, order_dispatcher=order_dispatcher
    )


@router.post("/{order_id}/accept")
async def accept_pedidosya_order(
    order_id: str,
    _usuario: dict = Depends(requiere_duenio),
    use_case: PedidosYaOrderUseCase = Depends(get_order_use_case),
):
    try:
        await use_case.accept_order_in_pedidosya(order_id)
        return {
            "status": "success",
            "message": f"Pedido {order_id} aceptado en PedidosYa.",
        }
    except HTTPException as e:
        raise error_de_plataforma(e, "PedidosYa")
    except Exception:
        logger.exception("Error inesperado aceptando el pedido %s", order_id)
        raise HTTPException(
            status_code=500, detail="Error interno al aceptar el pedido."
        )


@router.post("/{order_id}/deny")
async def deny_pedidosya_order(
    order_id: str,
    payload: DenyOrderRequest,
    _usuario: dict = Depends(requiere_duenio),
    use_case: PedidosYaOrderUseCase = Depends(get_order_use_case),
):
    try:
        await use_case.deny_order_in_pedidosya(order_id, payload.reason)
        return {
            "status": "success",
            "message": f"Pedido {order_id} rechazado en PedidosYa.",
        }
    except HTTPException as e:
        raise error_de_plataforma(e, "PedidosYa")
    except Exception:
        logger.exception("Error inesperado rechazando el pedido %s", order_id)
        raise HTTPException(
            status_code=500, detail="Error interno al rechazar el pedido."
        )


@router.post("/{order_id}/cancel")
async def cancel_pedidosya_order(
    order_id: str,
    payload: CancelOrderRequest,
    _usuario: dict = Depends(requiere_duenio),
    use_case: PedidosYaOrderUseCase = Depends(get_order_use_case),
):
    try:
        await use_case.cancel_order_in_pedidosya(order_id, payload.reason)
        return {
            "status": "success",
            "message": f"Pedido {order_id} cancelado en PedidosYa.",
        }
    except HTTPException as e:
        raise error_de_plataforma(e, "PedidosYa")
    except Exception:
        logger.exception("Error inesperado cancelando el pedido %s", order_id)
        raise HTTPException(
            status_code=500, detail="Error interno al cancelar el pedido."
        )


@router.post("/{order_id}/ready")
async def ready_pedidosya_order(
    order_id: str,
    _usuario: dict = Depends(requiere_duenio),
    use_case: PedidosYaOrderUseCase = Depends(get_order_use_case),
):
    try:
        await use_case.mark_order_ready_in_pedidosya(order_id)
        return {
            "status": "success",
            "message": f"Pedido {order_id} marcado como listo en PedidosYa.",
        }
    except HTTPException as e:
        raise error_de_plataforma(e, "PedidosYa")
    except Exception:
        logger.exception("Error inesperado marcando pedido %s como listo", order_id)
        raise HTTPException(
            status_code=500, detail="Error interno al marcar el pedido como listo."
        )
