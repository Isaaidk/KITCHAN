"""Caso de uso de la integración Rappi: procesa los webhooks que Rappi envía
(NEW_ORDER y ORDER_EVENT_CANCEL). Es el equivalente arquitectónico a
UberWebhookUseCase / PedidosYaOrderDispatchUseCase.

Diferencias de transporte con las otras integraciones:
- Con Uber, el webhook solo avisa y hay que descargar el pedido; Rappi
  entrega el pedido completo en el body de NEW_ORDER (como PedidosYa).
- Rappi configura una URL por evento, así que cada evento tiene su propio
  método en vez de un único dispatcher por `event_type`.
"""

from src.kitchan.modules.integraciones.core.domain.entities import (
    KitchanOrderDTO,
    KitchanOrderItem,
)
from src.kitchan.modules.integraciones.core.domain.inter_module_ports import (
    OrderDispatcherPort,
)
from src.kitchan.modules.integraciones.rappi.domain.models import (
    RappiCancelEventPayload,
    RappiOrderPayload,
)
from src.kitchan.modules.integraciones.rappi.domain.ports import RappiStoreMappingPort

PLATAFORMA = "RAPPI"


class RappiWebhookUseCase:
    def __init__(
        self,
        store_mapping: RappiStoreMappingPort,
        order_dispatcher: OrderDispatcherPort,
    ):
        self.store_mapping = store_mapping
        self.order_dispatcher = order_dispatcher

    def map_rappi_to_kitchan(
        self, payload: RappiOrderPayload, restaurante_id: str
    ) -> KitchanOrderDTO:
        """Capa Anticorrupción: traduce el payload de Rappi a nuestro modelo
        neutral. Ver los TODO en domain/models.py sobre unidades de precio."""
        items_kitchan = [
            KitchanOrderItem(
                nombre=item.name,
                cantidad=item.quantity,
                precio_unitario=item.price,
                notas_especiales=item.comments,
            )
            for item in payload.order_detail.items
        ]

        nombre_cliente = (
            f"{payload.customer.first_name} {payload.customer.last_name}".strip()
        )

        return KitchanOrderDTO(
            id_externo=payload.order_detail.order_id,
            plataforma=PLATAFORMA,
            restaurante_id=restaurante_id,
            nombre_cliente=nombre_cliente,
            items=items_kitchan,
            total=payload.order_detail.totals.total_order,
            estado="NUEVA",
        )

    async def procesar_nuevo_pedido(self, payload: RappiOrderPayload) -> bool:
        """
        Retorna True si el pedido quedó registrado en KITCHAN (o ya lo
        estaba) y False si la tienda no pertenece a ningún restaurante.
        """
        order_id = payload.order_detail.order_id
        store_id = payload.store.internal_id

        restaurante_id = await self.store_mapping.get_restaurante_id(store_id)
        if not restaurante_id:
            print(
                f"🚨 ERROR MULTI-TENANT: La tienda Rappi {store_id} no pertenece "
                "a ningún restaurante de KITCHAN."
            )
            return False

        # Idempotencia: si Rappi reintenta el webhook, no duplicamos el pedido.
        ya_existe = await self.order_dispatcher.order_already_exists(
            PLATAFORMA, order_id
        )
        if ya_existe:
            print(
                f"ℹ️ [RAPPI] Pedido {order_id} ya había sido procesado; "
                "se ignora el reenvío duplicado."
            )
            return True

        kitchan_dto = self.map_rappi_to_kitchan(payload, restaurante_id)

        print(f"🚀 [RAPPI] Enviando orden {order_id} al módulo central de pedidos...")
        id_interno = await self.order_dispatcher.dispatch_new_order(kitchan_dto)
        print(f"✅ [RAPPI] Orden guardada en DB principal con ID: {id_interno}")
        return True

    async def procesar_cancelacion(self, payload: RappiCancelEventPayload) -> bool:
        """Rappi (o el cliente) canceló el pedido. Retorna True si el pedido
        existía en KITCHAN. Si ya estaba en LISTA/ENTREGADA,
        ActualizarEstadoPedidoUseCase ignora la cancelación."""
        print(
            f"🛑 [RAPPI CANCEL] Orden cancelada en Rappi: {payload.order_id} "
            f"({payload.event})"
        )
        actualizado = await self.order_dispatcher.dispatch_order_status_update(
            origen=PLATAFORMA, id_externo=payload.order_id, nuevo_estado="CANCELADA"
        )
        if not actualizado:
            print(
                f"⚠️ [RAPPI CANCEL] No se encontró en KITCHAN el pedido {payload.order_id}."
            )
        return actualizado
