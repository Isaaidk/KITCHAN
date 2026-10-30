"""Caso de uso de la integración WhatsApp: acciones del KDS (aceptar, rechazar,
marcar listo, cancelar). Equivalente a RappiOrderUseCase.

El estado del pedido en KITCHAN es la fuente de verdad: primero se actualiza,
después se avisa al bot. Si el bot no responde, la acción del restaurante NO
se revierte (se registra el aviso fallido y se devuelve `cliente_notificado`
en False para que el KDS lo muestre).
"""

import logging
from typing import Optional

from src.kitchan.modules.integraciones.core.domain.inter_module_ports import (
    OrderDispatcherPort,
)
from src.kitchan.modules.integraciones.whatsapp.domain.ports import WhatsAppBotPort

logger = logging.getLogger(__name__)

PLATAFORMA = "WHATSAPP"


class WhatsAppOrderUseCase:
    def __init__(self, bot: WhatsAppBotPort, order_dispatcher: OrderDispatcherPort):
        self.bot = bot
        self.order_dispatcher = order_dispatcher

    async def _cambiar_estado(
        self,
        order_id: str,
        nuevo_estado: str,
        aviso: str,
        motivo: Optional[str] = None,
    ) -> bool:
        await self.order_dispatcher.dispatch_order_status_update(
            origen=PLATAFORMA, id_externo=order_id, nuevo_estado=nuevo_estado
        )
        try:
            notificado = await self.bot.notify_order_status(order_id, aviso, motivo)
        except Exception:
            logger.exception("No se pudo avisar al bot del pedido %s", order_id)
            notificado = False
        if not notificado:
            logger.warning(
                "El cliente del pedido WhatsApp %s no fue notificado (%s).",
                order_id,
                aviso,
            )
        return notificado

    async def accept_order(self, order_id: str) -> bool:
        return await self._cambiar_estado(order_id, "EN_PREPARACION", "ACCEPTED")

    async def deny_order(self, order_id: str, reason: str) -> bool:
        return await self._cambiar_estado(order_id, "CANCELADA", "REJECTED", reason)

    async def cancel_order(self, order_id: str, reason: str) -> bool:
        return await self._cambiar_estado(order_id, "CANCELADA", "CANCELLED", reason)

    async def mark_order_ready(self, order_id: str) -> bool:
        return await self._cambiar_estado(order_id, "LISTA", "READY")
