from src.kitchan.modules.integraciones.uber.domain.ports import UberTokenCachePort, UberApiPort
from src.kitchan.modules.integraciones.uber.domain.models import KitchanOrderDTO, KitchanOrderItem
from src.kitchan.modules.integraciones.core.domain.inter_module_ports import OrderDispatcherPort
from src.kitchan.modules.integraciones.uber.domain.ports import UberTokenCachePort, UberApiPort
from src.kitchan.modules.integraciones.uber.domain.models import UberWebhookPayload, KitchanOrderDTO, KitchanOrderItem
class UberOrderUseCase:
    def __init__(self, token_cache: UberTokenCachePort, uber_api: UberApiPort, order_dispatcher: OrderDispatcherPort):
        self.token_cache = token_cache
        self.uber_api = uber_api
        self.order_dispatcher = order_dispatcher
        

    def map_uber_to_kitchan(self, uber_json: dict, restaurante_id: str) -> KitchanOrderDTO:
        """Capa Anticorrupción: Traduce el JSON caótico de Uber a nuestro modelo limpio."""
        
        # Extraemos al cliente (Uber lo anida bajo 'eater')
        cliente = uber_json.get("eater", {}).get("first_name", "Cliente Desconocido")
        
        # Extraemos el total (Uber lo anida bajo 'payment' -> 'charges' -> 'total' y viene como objeto)
        # Nota: Ajustar esto según el payload exacto de tu país, usualmente viene en formato string o entero centavos.
        total_price = float(uber_json.get("payment", {}).get("charges", {}).get("total", {}).get("amount", 0.0))
        
        items_kitchan = []
        for item in uber_json.get("cart", {}).get("items", []):
            items_kitchan.append(KitchanOrderItem(
                nombre=item.get("title", "Item Desconocido"),
                cantidad=item.get("quantity", 1),
                precio_unitario=float(item.get("price", {}).get("unit_price", {}).get("amount", 0.0)),
                notas_especiales=item.get("special_instructions", "")
            ))

        return KitchanOrderDTO(
            id_externo=uber_json.get("id"),
            restaurante_id=restaurante_id,
            nombre_cliente=cliente,
            items=items_kitchan,
            total=total_price,
            estado="PENDING"
        )

    async def accept_order_in_uber(self, order_id: str, restaurante_id: str) -> bool:
        """Flujo cuando el usuario presiona 'Aceptar' en el frontend de Kitchan."""
        # 1. Recuperamos el token de Redis
        token = await self.token_cache.get_token(restaurante_id)
        if not token:
            raise ValueError("Token de Uber no encontrado o expirado. Vuelva a conectar la tienda.")

        # 2. Llamamos a Uber para aceptar la orden
        await self.uber_api.accept_order(order_id, token)
        
        print(f"✅ [NEGOCIO] Orden {order_id} aceptada exitosamente en Uber.")
        
        # TODO: Aquí llamarías al caso de uso interno de `pedidos` para cambiar 
        # el estado de la orden en nuestra base de datos SQL a "EN_PREPARACION".
        return True

    async def process_notification(self, payload: UberWebhookPayload, restaurante_id: str) -> None:
        if payload.event_type == "orders.notification":
            # ... (Aquí hacías la descarga con get_order_details) ...
            order_details = await self.uber_api.get_order_details(order_id, token)
            
            # 1. Traducimos la orden caótica a nuestro modelo limpio
            kitchan_dto = self.map_uber_to_kitchan(order_details, restaurante_id)
            
            # 2. Despachamos la orden al módulo central
            print(f"🚀 [NEGOCIO] Enviando orden {kitchan_dto.id_externo} al módulo central de pedidos...")
            id_interno = await self.order_dispatcher.dispatch_new_order(kitchan_dto)
            
            print(f"✅ [NEGOCIO] Orden guardada en DB principal con ID: {id_interno}")

    async def deny_order_in_uber(self, order_id: str, restaurante_id: str, reason: str, explanation: str) -> bool:
        # 1. Recuperamos el token
        token = await self.token_cache.get_token(restaurante_id)
        if not token:
            raise ValueError("Token de Uber expirado o no encontrado.")

        # 2. Ejecutamos el rechazo
        await self.uber_api.deny_order(order_id, token, reason, explanation)
        
        print(f"❌ [NEGOCIO] Orden {order_id} rechazada en Uber. Razón: {explanation}")
        
        # (Futuro: Aquí actualizarás el estado interno a CANCELADA)
        return True