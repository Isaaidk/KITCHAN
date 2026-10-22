import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.kitchan.modules.facturacion.domain.entities import (
    EstadoFactura,
    FacturaPedido,
)
from src.kitchan.modules.facturacion.domain.ports import FacturaRepositoryPort
from src.kitchan.modules.facturacion.infrastructure.models import FacturaPedidoModel


class PostgresFacturaRepository(FacturaRepositoryPort):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def guardar(self, factura: FacturaPedido) -> FacturaPedido:
        modelo = await self.session.get(
            FacturaPedidoModel, uuid.UUID(factura.pedido_id)
        )
        if modelo is None:
            modelo = FacturaPedidoModel(
                pedido_id=uuid.UUID(factura.pedido_id),
                restaurante_id=uuid.UUID(factura.restaurante_id),
            )
            self.session.add(modelo)
        modelo.odoo_move_id = factura.odoo_move_id
        modelo.numero = factura.numero
        modelo.estado = factura.estado
        modelo.total = factura.total
        modelo.numero_autorizacion = factura.numero_autorizacion
        modelo.fecha_autorizacion = factura.fecha_autorizacion
        modelo.mensaje_error = factura.mensaje_error
        await self.session.commit()
        await self.session.refresh(modelo)
        return modelo.to_domain()

    async def buscar_por_pedido(self, pedido_id: str) -> Optional[FacturaPedido]:
        try:
            clave = uuid.UUID(pedido_id)
        except ValueError:
            return None
        modelo = await self.session.get(FacturaPedidoModel, clave)
        return modelo.to_domain() if modelo else None

    async def buscar_por_odoo_move(self, odoo_move_id: int) -> Optional[FacturaPedido]:
        resultado = await self.session.execute(
            select(FacturaPedidoModel).where(
                FacturaPedidoModel.odoo_move_id == odoo_move_id
            )
        )
        modelo = resultado.scalar_one_or_none()
        return modelo.to_domain() if modelo else None

    async def listar_por_restaurante(self, restaurante_id: str) -> list[FacturaPedido]:
        try:
            clave = uuid.UUID(str(restaurante_id))
        except ValueError:
            return []
        resultado = await self.session.execute(
            select(FacturaPedidoModel).where(FacturaPedidoModel.restaurante_id == clave)
        )
        return [modelo.to_domain() for modelo in resultado.scalars()]

    async def listar_pendientes(self) -> list[FacturaPedido]:
        resultado = await self.session.execute(
            select(FacturaPedidoModel).where(
                FacturaPedidoModel.estado == EstadoFactura.PENDIENTE_SRI
            )
        )
        return [modelo.to_domain() for modelo in resultado.scalars()]
