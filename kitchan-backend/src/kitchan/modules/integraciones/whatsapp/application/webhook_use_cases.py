"""Caso de uso de la integración WhatsApp: procesa el pedido que envía el bot.
Equivalente arquitectónico a RappiWebhookUseCase: el body trae el pedido
completo, se traduce al DTO neutral y se despacha al módulo de Pedidos.
"""

import logging

from src.kitchan.modules.integraciones.core.domain.entities import (
    KitchanOrderDTO,
    KitchanOrderItem,
)
from src.kitchan.modules.integraciones.core.domain.metodos_pago import (
    normalizar_metodo_pago,
)
from src.kitchan.modules.integraciones.core.domain.inter_module_ports import (
    OrderDispatcherPort,
)
from src.kitchan.modules.integraciones.whatsapp.domain.models import (
    WhatsAppOrderPayload,
)
from src.kitchan.modules.integraciones.whatsapp.domain.ports import (
    WhatsAppStoreMappingPort,
)

logger = logging.getLogger(__name__)

PLATAFORMA = "WHATSAPP"


class WhatsAppWebhookUseCase:
    def __init__(
        self,
        store_mapping: WhatsAppStoreMappingPort,
        order_dispatcher: OrderDispatcherPort,
    ):
        self.store_mapping = store_mapping
        self.order_dispatcher = order_dispatcher

    def map_whatsapp_to_kitchan(
        self, payload: WhatsAppOrderPayload, restaurante_id: str
    ) -> KitchanOrderDTO:
        """Capa Anticorrupción: del contrato del bot al modelo neutral."""
        return KitchanOrderDTO(
            id_externo=payload.order_id,
            plataforma=PLATAFORMA,
            restaurante_id=restaurante_id,
            nombre_cliente=payload.customer_name.strip() or "Cliente WhatsApp",
            items=[
                KitchanOrderItem(
                    nombre=item.name,
                    cantidad=item.quantity,
                    precio_unitario=item.unit_price,
                    notas_especiales=item.notes,
                )
                for item in payload.items
            ],
            total=payload.total,
            estado="NUEVA",
            metodo_pago=normalizar_metodo_pago(payload.payment_method),
            telefono_cliente=payload.customer_phone,
            tipo_entrega=payload.delivery_type,
            # Un retiro en local no tiene dirección aunque el bot la enviara.
            direccion_entrega=(
                payload.delivery_address
                if payload.delivery_type == "DOMICILIO"
                else None
            ),
            nota_cliente=payload.order_notes,
        )

    async def procesar_nuevo_pedido(self, payload: WhatsAppOrderPayload) -> bool:
        """True si el pedido quedó registrado (o ya lo estaba); False si la
        tienda no pertenece a ningún restaurante."""
        restaurante_id = await self.store_mapping.get_restaurante_id(payload.store_id)
        if not restaurante_id:
            logger.error(
                "La tienda WhatsApp %s no pertenece a ningún restaurante de KITCHAN.",
                payload.store_id,
            )
            return False

        # Idempotencia: el bot reintenta si no recibe 200, no duplicamos.
        if await self.order_dispatcher.order_already_exists(
            PLATAFORMA, payload.order_id
        ):
            logger.info(
                "Pedido WhatsApp %s ya procesado; se ignora el reenvío.",
                payload.order_id,
            )
            return True

        kitchan_dto = self.map_whatsapp_to_kitchan(payload, restaurante_id)
        id_interno = await self.order_dispatcher.dispatch_new_order(kitchan_dto)
        logger.info(
            "Pedido WhatsApp %s guardado en KITCHAN con ID %s",
            payload.order_id,
            id_interno,
        )
        return True
