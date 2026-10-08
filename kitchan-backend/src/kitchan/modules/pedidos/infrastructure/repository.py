import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.kitchan.modules.pedidos.domain.entities import EstadoPedido, Pedido
from src.kitchan.modules.pedidos.domain.ports import PedidoRepositoryPort
from src.kitchan.modules.pedidos.infrastructure.models import PedidoModel

ESTADOS_TERMINALES = [EstadoPedido.ENTREGADA.value, EstadoPedido.CANCELADA.value]


class PostgresPedidoRepository(PedidoRepositoryPort):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def guardar(self, pedido: Pedido) -> Pedido:
        modelo = PedidoModel.from_domain(pedido)
        self.session.add(modelo)
        await self.session.commit()
        await self.session.refresh(modelo)
        return modelo.to_domain()

    async def actualizar_estado(self, pedido_id: str, nuevo_estado: str) -> bool:
        modelo = await self._buscar_modelo_por_id(pedido_id)
        if modelo is None:
            return False
        modelo.estado = nuevo_estado
        await self.session.commit()
        return True

    async def actualizar_estado_entrega(
        self, pedido_id: str, estado_entrega: str
    ) -> bool:
        modelo = await self._buscar_modelo_por_id(pedido_id)
        if modelo is None:
            return False
        modelo.estado_entrega = estado_entrega
        await self.session.commit()
        return True

    async def buscar_por_id_externo(
        self, origen: str, id_externo: str
    ) -> Optional[Pedido]:
        stmt = select(PedidoModel).where(
            PedidoModel.origen == origen, PedidoModel.id_externo == id_externo
        )
        resultado = await self.session.execute(stmt)
        modelo = resultado.scalar_one_or_none()
        return modelo.to_domain() if modelo else None

    async def buscar_por_id(self, pedido_id: str) -> Optional[Pedido]:
        modelo = await self._buscar_modelo_por_id(pedido_id)
        return modelo.to_domain() if modelo else None

    async def listar_estancados(self, minutos: int) -> list[Pedido]:
        limite = datetime.now(timezone.utc) - timedelta(minutes=minutos)
        stmt = select(PedidoModel).where(
            PedidoModel.estado.notin_(ESTADOS_TERMINALES),
            PedidoModel.fecha_actualizacion < limite,
        )
        resultado = await self.session.execute(stmt)
        modelos = resultado.scalars().all()
        return [m.to_domain() for m in modelos]

    async def listar_por_restaurante(
        self,
        restaurante_id: str,
        estados: Optional[list[str]] = None,
        canal: Optional[str] = None,
        search: Optional[str] = None,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> tuple[list[Pedido], int]:
        condiciones = [PedidoModel.restaurante_id == uuid.UUID(str(restaurante_id))]
        if estados:
            condiciones.append(PedidoModel.estado.in_(estados))
        if canal:
            condiciones.append(PedidoModel.origen == canal)
        if search:
            patron = f"%{search}%"
            condiciones.append(
                or_(
                    PedidoModel.cliente.ilike(patron),
                    PedidoModel.id_externo.ilike(patron),
                )
            )

        stmt_total = select(func.count()).select_from(PedidoModel).where(*condiciones)
        total = (await self.session.execute(stmt_total)).scalar_one()

        stmt = (
            select(PedidoModel)
            .where(*condiciones)
            .order_by(PedidoModel.fecha_creacion.desc())
        )
        if page and page_size:
            stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        resultado = await self.session.execute(stmt)
        modelos = resultado.scalars().all()
        return [m.to_domain() for m in modelos], total

    async def _buscar_modelo_por_id(self, pedido_id: str) -> Optional[PedidoModel]:
        stmt = select(PedidoModel).where(PedidoModel.id == uuid.UUID(str(pedido_id)))
        resultado = await self.session.execute(stmt)
        return resultado.scalar_one_or_none()
