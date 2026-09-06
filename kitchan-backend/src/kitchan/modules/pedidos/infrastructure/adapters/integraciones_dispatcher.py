from src.kitchan.modules.integraciones.core.domain.inter_module_ports import (
    OrderDispatcherPort,
)
from src.kitchan.modules.integraciones.uber.domain.models import KitchanOrderDTO

from src.kitchan.modules.pedidos.domain.entities import Pedido, PedidoItem, EstadoPedido
from src.kitchan.modules.pedidos.application.crear_pedido_service import (
    CrearPedidoUseCase,
)
from src.kitchan.modules.pedidos.application.actualizar_estado_pedido_service import (
    ActualizarEstadoPedidoUseCase,
)


class PedidosIntegracionesAdapter(OrderDispatcherPort):
    """
    Puente de comunicación: Recibe un DTO de integraciones,
    lo traduce al Dominio Core, y ejecuta el caso de uso.
    """

    def __init__(
        self,
        use_case: CrearPedidoUseCase,
        actualizar_estado_use_case: ActualizarEstadoPedidoUseCase,
    ):
        self.use_case = use_case
        self.actualizar_estado_use_case = actualizar_estado_use_case

    async def dispatch_new_order(self, order_dto: KitchanOrderDTO) -> str:
        # 1. Traducción (Mapeo)
        items_core = [
            PedidoItem(
                nombre=item.nombre,
                cantidad=item.cantidad,
                precio_unitario=item.precio_unitario,
                notas=item.notas_especiales,
            )
            for item in order_dto.items
        ]

        pedido_core = Pedido(
            restaurante_id=order_dto.restaurante_id,
            origen=order_dto.plataforma,
            id_externo=order_dto.id_externo,
            cliente=order_dto.nombre_cliente,
            items=items_core,
            total=order_dto.total,
            estado=EstadoPedido.NUEVA,
        )

        print(f"🌉 [PUENTE] Traducción completada. Enviando a Cocina Central...")

        # 2. Ejecución de la lógica de negocio
        pedido_id = await self.use_case.ejecutar(pedido_core)

        return pedido_id

    async def dispatch_order_status_update(
        self, origen: str, id_externo: str, nuevo_estado: str
    ) -> bool:
        pedido = await self.actualizar_estado_use_case.ejecutar_por_id_externo(
            origen, id_externo, EstadoPedido(nuevo_estado)
        )
        return pedido is not None

    async def dispatch_delivery_status_update(
        self, origen: str, id_externo: str, estado_entrega: str
    ) -> bool:
        pedido = await self.actualizar_estado_use_case.actualizar_estado_entrega(
            origen, id_externo, estado_entrega
        )
        return pedido is not None
