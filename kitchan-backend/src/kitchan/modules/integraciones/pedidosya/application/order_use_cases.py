"""Caso de uso de la integración PedidosYa: acciones manuales que dispara el
KDS de KITCHAN (aceptar/rechazar/cancelar/marcar listo), equivalentes a las
que UberOrderUseCase expone para Uber.

Nota de diseño: a diferencia de Uber (que necesita `restaurante_id` para
resolver el token OAuth del tenant en Redis), las llamadas salientes de
PedidosYa usan credenciales estáticas de aplicación (ver
infrastructure/adapters/http_order_adapter.py) — por eso estos métodos no
reciben `restaurante_id`.
"""

from src.kitchan.modules.integraciones.core.domain.inter_module_ports import (
    OrderDispatcherPort,
)
from src.kitchan.modules.integraciones.pedidosya.domain.ports import PedidosYaApiPort

PLATAFORMA = "PEDIDOS_YA"


class PedidosYaOrderUseCase:
    def __init__(
        self, pedidosya_api: PedidosYaApiPort, order_dispatcher: OrderDispatcherPort
    ):
        self.pedidosya_api = pedidosya_api
        self.order_dispatcher = order_dispatcher

    async def accept_order_in_pedidosya(self, order_id: str) -> bool:
        """Flujo cuando el usuario presiona 'Aceptar' en el frontend de Kitchan."""
        await self.pedidosya_api.update_order_status(order_id, status="CONFIRMED")

        print(f"✅ [NEGOCIO] Orden {order_id} aceptada exitosamente en PedidosYa.")

        await self.order_dispatcher.dispatch_order_status_update(
            origen=PLATAFORMA, id_externo=order_id, nuevo_estado="EN_PREPARACION"
        )
        return True

    async def deny_order_in_pedidosya(self, order_id: str, reason: str) -> bool:
        await self.pedidosya_api.update_order_status(
            order_id, status="REJECTED", reason=reason
        )

        print(f"❌ [NEGOCIO] Orden {order_id} rechazada en PedidosYa. Razón: {reason}")

        await self.order_dispatcher.dispatch_order_status_update(
            origen=PLATAFORMA, id_externo=order_id, nuevo_estado="CANCELADA"
        )
        return True

    async def cancel_order_in_pedidosya(self, order_id: str, reason: str) -> bool:
        """Cancela un pedido YA ACEPTADO (igual distinción que en Uber: deny
        es previo a la aceptación, cancel es posterior)."""
        await self.pedidosya_api.update_order_status(
            order_id, status="CANCELLED", reason=reason
        )

        print(f"❌ [NEGOCIO] Orden {order_id} cancelada en PedidosYa. Razón: {reason}")

        await self.order_dispatcher.dispatch_order_status_update(
            origen=PLATAFORMA, id_externo=order_id, nuevo_estado="CANCELADA"
        )
        return True

    async def mark_order_ready_in_pedidosya(self, order_id: str) -> bool:
        await self.pedidosya_api.mark_order_prepared(order_id)

        print(f"✅ [NEGOCIO] Orden {order_id} marcada como READY en PedidosYa.")

        await self.order_dispatcher.dispatch_order_status_update(
            origen=PLATAFORMA, id_externo=order_id, nuevo_estado="LISTA"
        )
        return True
