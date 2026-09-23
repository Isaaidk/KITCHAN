"""Caso de uso de la integración PedidosYa: procesa el POST de "Dispatch
Order" que Delivery Hero hace contra nuestro endpoint. Es el equivalente
arquitectónico al webhook de Uber (UberWebhookUseCase) — la diferencia es de
transporte (POST directo con remoteId en la URL, en vez de un evento de
webhook con metadata), no de capa.
"""

from src.kitchan.modules.integraciones.core.domain.entities import (
    KitchanOrderDTO,
    KitchanOrderItem,
)
from src.kitchan.modules.integraciones.core.domain.inter_module_ports import (
    OrderDispatcherPort,
)
from src.kitchan.modules.integraciones.pedidosya.domain.models import (
    OrderDispatchAcknowledgedResponse,
    PedidosYaOrderPayload,
)

PLATAFORMA = "PEDIDOS_YA"


class PedidosYaOrderDispatchUseCase:
    def __init__(self, order_dispatcher: OrderDispatcherPort):
        self.order_dispatcher = order_dispatcher

    def map_pedidosya_to_kitchan(
        self, payload: PedidosYaOrderPayload, restaurante_id: str
    ) -> KitchanOrderDTO:
        """Capa Anticorrupción: traduce el payload de PedidosYa a nuestro
        modelo neutral. Ver los TODO en domain/models.py sobre los campos
        pendientes de confirmar contra el YAML real de pluginApi."""
        items_kitchan = [
            KitchanOrderItem(
                nombre=item.name,
                cantidad=item.quantity,
                precio_unitario=item.price,
                notas_especiales=item.notes,
            )
            for item in payload.items
        ]

        return KitchanOrderDTO(
            id_externo=payload.order_id,
            plataforma=PLATAFORMA,
            restaurante_id=restaurante_id,
            nombre_cliente=payload.customer_name,
            items=items_kitchan,
            total=payload.total_price,
            estado="NUEVA",
        )

    async def procesar_dispatch(
        self, restaurante_id: str, payload: PedidosYaOrderPayload
    ) -> OrderDispatchAcknowledgedResponse:
        """
        Idempotencia: la documentación de PedidosYa advierte explícitamente
        que la misma notificación de pedido puede reenviarse más de una vez
        — a diferencia de Uber, donde esto nunca se validó. Por eso
        chequeamos antes de despachar.
        """
        ya_existe = await self.order_dispatcher.order_already_exists(
            PLATAFORMA, payload.order_id
        )
        if ya_existe:
            print(
                f"ℹ️ [PEDIDOSYA] Pedido {payload.order_id} ya había sido procesado; "
                "se ignora el reenvío duplicado."
            )
            return OrderDispatchAcknowledgedResponse()

        kitchan_dto = self.map_pedidosya_to_kitchan(payload, restaurante_id)

        print(
            f"🚀 [PEDIDOSYA] Enviando orden {kitchan_dto.id_externo} al módulo central de pedidos..."
        )
        id_interno = await self.order_dispatcher.dispatch_new_order(kitchan_dto)
        print(f"✅ [PEDIDOSYA] Orden guardada en DB principal con ID: {id_interno}")

        return OrderDispatchAcknowledgedResponse()
