import logging
from fastapi import HTTPException

# Importamos los modelos y puertos de la capa de dominio de Uber
from src.kitchan.modules.integraciones.uber.domain.models import UberWebhookPayload
from src.kitchan.modules.integraciones.uber.domain.ports import UberTokenCachePort
from src.kitchan.modules.integraciones.uber.domain.models import (
    KitchanOrderDTO,
    KitchanOrderItem,
)
from src.kitchan.modules.integraciones.uber.domain.models import KitchanOrderDTO

# El adaptador HTTP para ir a buscar el pedido
from src.kitchan.modules.integraciones.uber.infrastructure.adapters.http_order_adapter import (
    UberHttpAdapter,
)

# El puerto compartido para comunicarnos con el módulo de Pedidos (Anti-Corruption Layer)
from src.kitchan.modules.integraciones.core.domain.inter_module_ports import (
    OrderDispatcherPort,
)

logger = logging.getLogger(__name__)


class UberWebhookUseCase:
    """
    Caso de uso encargado de procesar los webhooks entrantes de Uber Eats.
    """

    def __init__(
        self,
        token_cache: UberTokenCachePort,
        uber_api: UberHttpAdapter,  # O su interfaz/puerto si tienes uno (ej. UberApiPort)
        order_dispatcher: OrderDispatcherPort,
    ):
        self.token_cache = token_cache
        self.uber_api = uber_api
        self.order_dispatcher = order_dispatcher

    async def process_notification(self, payload: UberWebhookPayload) -> None:
        """
        Procesa el payload validado del webhook de Uber.
        """
        # 1. Ignorar eventos que no nos interesan por ahora
        # 1. Procesar estados del delivery/courier

        if payload.event_type == "delivery.state_changed":
            order_id = payload.meta.order_id
            courier_trip_id = payload.meta.courier_trip_id
            status = payload.meta.status

            print(
                f"🚚 [UBER DELIVERY] "
                f"Orden: {order_id} | "
                f"Courier Trip: {courier_trip_id} | "
                f"Estado: {status}"
            )

            if not order_id or not status:
                print("⚠️ [UBER DELIVERY] " "El webhook no contiene order_id o status.")
                return

            actualizado = await self.order_dispatcher.dispatch_delivery_status_update(
                origen="UBER_EATS", id_externo=order_id, estado_entrega=status
            )
            if not actualizado:
                print(
                    f"⚠️ [UBER DELIVERY] No se encontró en KITCHAN el pedido {order_id}."
                )
            return

        if payload.event_type == "orders.cancel":
            order_id = payload.meta.resource_id
            print(f"🛑 [UBER CANCEL] Orden cancelada en Uber: {order_id}")

            if not order_id:
                print("⚠️ [UBER CANCEL] El webhook no contiene resource_id.")
                return

            actualizado = await self.order_dispatcher.dispatch_order_status_update(
                origen="UBER_EATS", id_externo=order_id, nuevo_estado="CANCELADA"
            )
            if not actualizado:
                print(
                    f"⚠️ [UBER CANCEL] No se encontró en KITCHAN el pedido {order_id}."
                )
            return

        # Ignorar otros eventos que todavía no procesamos
        if payload.event_type != "orders.notification":
            print(f"ℹ️ Ignorando evento de tipo: {payload.event_type}")
            return

        print(
            f"🛎️ [NEGOCIO] ¡Nueva orden detectada! ID Uber: {payload.meta.resource_id}"
        )

        # 2. Extraer los IDs clave del payload
        store_id_uber = payload.meta.user_id  # El ID de la tienda en Uber
        order_id_uber = payload.meta.resource_id  # El ID del pedido en Uber

        # ========================================================
        # 3. LA TRADUCCIÓN MULTI-TENANT (EL PUENTE)
        # ========================================================
        restaurante_id = await self.token_cache.get_restaurante_id_by_store(
            store_id_uber
        )

        if not restaurante_id:
            mensaje = f"🚨 ERROR MULTI-TENANT: El store_id {store_id_uber} no pertenece a ningún restaurante de KITCHAN."
            print(mensaje)
            return

        print(
            f"✅ Mapeo exitoso: Tienda Uber {store_id_uber} pertenece al tenant {restaurante_id}"
        )

        # ========================================================
        # 4. OBTENER EL TOKEN Y DESCARGAR EL PEDIDO
        # ========================================================
        token = await self.token_cache.get_app_token(restaurante_id)

        if not token:
            print(
                f"🚨 ERROR: No se encontró App Token para el restaurante {restaurante_id}"
            )
            raise HTTPException(
                status_code=500, detail="Token no disponible para descargar la orden"
            )

        print(f"📥 Descargando detalles de la orden {order_id_uber}...")

        orden_uber_detalles = await self.uber_api.get_order_details(
            order_id_uber, token
        )

        if not orden_uber_detalles:
            print(f"🚨 ERROR: No se pudo descargar la orden {order_id_uber} desde Uber")
            raise HTTPException(
                status_code=502, detail="Error descargando detalles de la orden"
            )

        # ========================================================
        # 5. TRANSFORMAR A DTO Y ENVIAR AL MÓDULO DE PEDIDOS
        #    (ANTI-CORRUPTION LAYER)
        # ========================================================
        print(f"🚀 Transformando JSON de Uber a KitchanOrderDTO...")

        # A. Extraer Cliente
        cliente_info = orden_uber_detalles.get("eater", {})
        nombre = cliente_info.get("first_name", "Cliente")
        apellido = cliente_info.get("last_name", "Uber")
        nombre_cliente = f"{nombre} {apellido}".strip()

        # B. Extraer Total
        try:
            total_orden = float(
                orden_uber_detalles.get("payment", {})
                .get("charges", {})
                .get("total", {})
                .get("amount", 0.0)
            )
        except (ValueError, TypeError):
            total_orden = 0.0

        # C. Extraer y mapear los Items
        items_dto = []
        cart_items = orden_uber_detalles.get("cart", {}).get("items", [])

        for item in cart_items:
            precio_info = item.get("price", {})

            # 1. Obtenemos el unit_price (Uber lo manda como diccionario: {"amount": 1500, "currency_code": "USD"})
            unit_price_data = precio_info.get("unit_price", {})

            # 2. Validamos si es un diccionario para extraer el "amount" correctamente
            if isinstance(unit_price_data, dict):
                precio_unitario = float(unit_price_data.get("amount", 0.0))
            else:
                precio_unitario = float(unit_price_data) if unit_price_data else 0.0

            items_dto.append(
                KitchanOrderItem(
                    nombre=item.get("title", "Producto Desconocido"),
                    cantidad=item.get("quantity", 1),
                    precio_unitario=precio_unitario,
                    notas_especiales=item.get("special_instructions"),
                )
            )

        # D. Ensamblar el DTO Final
        orden_dto = KitchanOrderDTO(
            id_externo=order_id_uber,
            plataforma="UBER_EATS",
            restaurante_id=restaurante_id,
            nombre_cliente=nombre_cliente,
            items=items_dto,
            total=total_orden,
            estado="NUEVA",
        )

        print(
            f"📦 DTO Construido: {orden_dto.nombre_cliente} - ${orden_dto.total} ({len(orden_dto.items)} items)"
        )
        print(f"🚀 Despachando orden al módulo Core de Pedidos...")

        # E. Enviar al Core de Pedidos de Kitchan
        await self.order_dispatcher.dispatch_new_order(orden_dto)
        print(f"🎉 ¡ÉXITO! Pedido {order_id_uber} procesado e inyectado a KITCHAN.")
