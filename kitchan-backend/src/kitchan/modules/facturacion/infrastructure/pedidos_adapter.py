"""Adaptador de salida de Facturación: obtiene el pedido a través del puerto
del repositorio de `pedidos` (PedidoRepositoryPort), sin tocar su tabla ni su
modelo de SQLAlchemy."""

from typing import Optional

from src.kitchan.modules.facturacion.domain.entities import (
    LineaFactura,
    PedidoAFacturar,
)
from src.kitchan.modules.facturacion.domain.ports import PedidosFacturablesPort
from src.kitchan.modules.pedidos.domain.ports import PedidoRepositoryPort


class PedidosFacturablesAdapter(PedidosFacturablesPort):
    def __init__(self, repositorio_pedidos: PedidoRepositoryPort):
        self.repositorio_pedidos = repositorio_pedidos

    async def obtener(self, pedido_id: str) -> Optional[PedidoAFacturar]:
        try:
            pedido = await self.repositorio_pedidos.buscar_por_id(pedido_id)
        except ValueError:
            # Un id que no es UUID no corresponde a ningún pedido.
            return None
        if pedido is None:
            return None
        return PedidoAFacturar(
            id=pedido.id,
            restaurante_id=pedido.restaurante_id,
            origen=pedido.origen,
            id_externo=pedido.id_externo,
            estado=pedido.estado.value,
            items=[
                LineaFactura(
                    descripcion=item.nombre,
                    cantidad=item.cantidad,
                    precio_con_iva=item.precio_unitario,
                )
                for item in pedido.items
            ],
        )
