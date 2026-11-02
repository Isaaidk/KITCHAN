"""Infraestructura de WhatsApp: rutas consumidas por el KDS para aceptar,
rechazar, cancelar o marcar listo un pedido de WhatsApp. Exige un usuario de
KITCHAN autenticado y dueño del pedido (ver core/infrastructure/seguridad.py).

Respuesta: `cliente_notificado` indica si el bot pudo avisar al cliente por
WhatsApp; el estado del pedido en KITCHAN se actualiza de todos modos.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.kitchan.modules.integraciones.core.domain.inter_module_ports import (
    OrderDispatcherPort,
)
from src.kitchan.modules.integraciones.core.infrastructure.seguridad import (
    usuario_duenio_del_pedido,
)
from src.kitchan.modules.integraciones.whatsapp.application.order_use_cases import (
    WhatsAppOrderUseCase,
)
from src.kitchan.modules.integraciones.whatsapp.infrastructure.adapters.http_bot_adapter import (
    WhatsAppBotHttpAdapter,
)
from src.kitchan.modules.pedidos.infrastructure.dependencias import get_order_dispatcher

logger = logging.getLogger(__name__)

requiere_duenio = usuario_duenio_del_pedido("WHATSAPP")

router = APIRouter(
    prefix="/api/v1/integraciones/whatsapp/orders",
    tags=["Integraciones - Acciones de Pedidos WhatsApp"],
)


class MotivoRequest(BaseModel):
    reason: str = "No podemos preparar el pedido en este momento."


def get_order_use_case(
    order_dispatcher: OrderDispatcherPort = Depends(get_order_dispatcher),
) -> WhatsAppOrderUseCase:
    return WhatsAppOrderUseCase(
        bot=WhatsAppBotHttpAdapter(), order_dispatcher=order_dispatcher
    )


def _respuesta(order_id: str, mensaje: str, cliente_notificado: bool) -> dict:
    return {
        "status": "success",
        "message": f"Pedido {order_id} {mensaje}.",
        "cliente_notificado": cliente_notificado,
    }


async def _ejecutar(order_id: str, accion, mensaje: str, error_log: str) -> dict:
    try:
        return _respuesta(order_id, mensaje, await accion())
    except HTTPException:
        raise
    except Exception:
        logger.exception("%s %s", error_log, order_id)
        raise HTTPException(status_code=500, detail=f"{error_log}.")


@router.post("/{order_id}/accept")
async def accept_whatsapp_order(
    order_id: str,
    _usuario: dict = Depends(requiere_duenio),
    use_case: WhatsAppOrderUseCase = Depends(get_order_use_case),
):
    return await _ejecutar(
        order_id,
        lambda: use_case.accept_order(order_id),
        "aceptado",
        "Error interno al aceptar el pedido",
    )


@router.post("/{order_id}/deny")
async def deny_whatsapp_order(
    order_id: str,
    payload: MotivoRequest,
    _usuario: dict = Depends(requiere_duenio),
    use_case: WhatsAppOrderUseCase = Depends(get_order_use_case),
):
    return await _ejecutar(
        order_id,
        lambda: use_case.deny_order(order_id, payload.reason),
        "rechazado",
        "Error interno al rechazar el pedido",
    )


@router.post("/{order_id}/cancel")
async def cancel_whatsapp_order(
    order_id: str,
    payload: MotivoRequest,
    _usuario: dict = Depends(requiere_duenio),
    use_case: WhatsAppOrderUseCase = Depends(get_order_use_case),
):
    return await _ejecutar(
        order_id,
        lambda: use_case.cancel_order(order_id, payload.reason),
        "cancelado",
        "Error interno al cancelar el pedido",
    )


@router.post("/{order_id}/ready")
async def ready_whatsapp_order(
    order_id: str,
    _usuario: dict = Depends(requiere_duenio),
    use_case: WhatsAppOrderUseCase = Depends(get_order_use_case),
):
    return await _ejecutar(
        order_id,
        lambda: use_case.mark_order_ready(order_id),
        "marcado como listo",
        "Error interno al marcar el pedido como listo",
    )
