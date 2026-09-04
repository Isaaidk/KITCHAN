from src.kitchan.modules.integraciones.core.domain.inter_module_ports import OrderDispatcherPort
from src.kitchan.modules.integraciones.uber.domain.models import KitchanOrderDTO

from src.kitchan.modules.pedidos.domain.entities import Pedido, PedidoItem, EstadoPedido
from src.kitchan.modules.pedidos.application.crear_pedido_service import CrearPedidoUseCase

class PedidosIntegracionesAdapter(OrderDispatcherPort):
    """
    Puente de comunicación: Recibe un DTO de integraciones, 
    lo traduce al Dominio Core, y ejecuta el caso de uso.
    """
    def __init__(self, use_case: CrearPedidoUseCase):
        self.use_case = use_case

    async def dispatch_new_order(self, order_dto: KitchanOrderDTO) -> str:
        # 1. Traducción (Mapeo)
        items_core = [
            PedidoItem(
                nombre=item.nombre,
                cantidad=item.cantidad,
                precio_unitario=item.precio_unitario,
                notas=item.notas_especiales
            )
            for item in order_dto.items
        ]

        pedido_core = Pedido(
            origen=order_dto.plataforma,
            id_externo=order_dto.id_externo,
            cliente=order_dto.nombre_cliente,
            items=items_core,
            total=order_dto.total,
            estado=EstadoPedido.NUEVA
        )

        print(f"🌉 [PUENTE] Traducción completada. Enviando a Cocina Central...")
        
        # 2. Ejecución de la lógica de negocio
        pedido_id = await self.use_case.ejecutar(pedido_core)
        
        return pedido_id