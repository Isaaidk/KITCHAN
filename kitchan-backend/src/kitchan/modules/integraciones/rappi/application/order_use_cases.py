"""Caso de uso de la integración Rappi: acciones manuales que dispara el KDS
de KITCHAN (aceptar/rechazar/marcar listo), equivalentes a las que
UberOrderUseCase y PedidosYaOrderUseCase exponen para sus plataformas.

Nota de diseño: igual que PedidosYa (y a diferencia de Uber), las llamadas
salientes usan credenciales de aplicación (client-credentials), no un token
por restaurante — por eso estos métodos no reciben `restaurante_id`.

No hay método de "cancelar pedido ya aceptado": la API pública de Rappi solo
documenta `reject`, que es válido mientras el pedido está en SENT.
"""

from typing import Optional

from src.kitchan.modules.integraciones.core.domain.inter_module_ports import (
    OrderDispatcherPort,
)
from src.kitchan.modules.integraciones.rappi.domain.ports import RappiApiPort

PLATAFORMA = "RAPPI"


class RappiOrderUseCase:
    def __init__(self, rappi_api: RappiApiPort, order_dispatcher: OrderDispatcherPort):
        self.rappi_api = rappi_api
        self.order_dispatcher = order_dispatcher

    async def accept_order_in_rappi(
        self, order_id: str, cooking_time: Optional[int] = None
    ) -> bool:
        """Flujo cuando el usuario presiona 'Aceptar' en el frontend de Kitchan."""
        await self.rappi_api.take_order(order_id, cooking_time)

        print(f"✅ [NEGOCIO] Orden {order_id} tomada exitosamente en Rappi.")

        await self.order_dispatcher.dispatch_order_status_update(
            origen=PLATAFORMA, id_externo=order_id, nuevo_estado="EN_PREPARACION"
        )
        return True

    async def deny_order_in_rappi(
        self, order_id: str, reason: str, cancel_type: str
    ) -> bool:
        await self.rappi_api.reject_order(order_id, reason, cancel_type)

        print(
            f"❌ [NEGOCIO] Orden {order_id} rechazada en Rappi. "
            f"Tipo: {cancel_type} | Razón: {reason}"
        )

        await self.order_dispatcher.dispatch_order_status_update(
            origen=PLATAFORMA, id_externo=order_id, nuevo_estado="CANCELADA"
        )
        return True

    async def mark_order_ready_in_rappi(self, order_id: str) -> bool:
        await self.rappi_api.mark_ready_for_pickup(order_id)

        print(f"✅ [NEGOCIO] Orden {order_id} marcada como READY en Rappi.")

        await self.order_dispatcher.dispatch_order_status_update(
            origen=PLATAFORMA, id_externo=order_id, nuevo_estado="LISTA"
        )
        return True
