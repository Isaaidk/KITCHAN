"""Adaptador de salida de Reportes: obtiene los pedidos a través del puerto
del repositorio de `pedidos` (PedidoRepositoryPort), sin tocar su tabla ni su
modelo de SQLAlchemy. Si cambia la persistencia de pedidos, reportes no se
entera.
"""

from datetime import datetime

from src.kitchan.modules.pedidos.domain.ports import PedidoRepositoryPort
from src.kitchan.modules.reportes.domain.entities import ItemResumen, PedidoResumen
from src.kitchan.modules.reportes.domain.ports import PedidosLecturaPort


class PedidosLecturaAdapter(PedidosLecturaPort):
    def __init__(self, repositorio_pedidos: PedidoRepositoryPort):
        self.repositorio_pedidos = repositorio_pedidos

    async def listar_desde(
        self, restaurante_id: str, desde: datetime
    ) -> list[PedidoResumen]:
        pedidos = await self.repositorio_pedidos.listar_por_restaurante_desde(
            restaurante_id, desde
        )
        return [
            PedidoResumen(
                origen=p.origen,
                total=float(p.total),
                estado=p.estado.value,
                fecha_creacion=p.fecha_creacion,
                fecha_actualizacion=p.fecha_actualizacion,
                cliente=p.cliente or "",
                items=tuple(
                    ItemResumen(
                        nombre=i.nombre,
                        cantidad=i.cantidad,
                        precio_unitario=float(i.precio_unitario),
                    )
                    for i in p.items
                ),
                metodo_pago=p.metodo_pago,
                fecha_aceptacion=p.fecha_aceptacion,
                fecha_lista=p.fecha_lista,
                aceptado_por_id=p.aceptado_por_id,
            )
            for p in pedidos
        ]
