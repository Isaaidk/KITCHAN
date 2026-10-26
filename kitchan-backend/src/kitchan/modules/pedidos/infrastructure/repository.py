import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.kitchan.core.contexto_usuario import usuario_actual_id
from src.kitchan.modules.pedidos.domain.entities import EstadoPedido, Pedido
from src.kitchan.modules.pedidos.domain.exceptions import PedidoDuplicadoError
from src.kitchan.modules.pedidos.domain.ports import PedidoRepositoryPort
from src.kitchan.modules.pedidos.infrastructure.models import PedidoModel

ESTADOS_TERMINALES = [EstadoPedido.ENTREGADA.value, EstadoPedido.CANCELADA.value]


class PostgresPedidoRepository(PedidoRepositoryPort):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def guardar(self, pedido: Pedido) -> Pedido:
        modelo = PedidoModel.from_domain(pedido)
        self.session.add(modelo)
        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            # Si la causa es el índice único (dos webhooks iguales a la vez),
            # se informa como duplicado; cualquier otro error se propaga.
            if pedido.id_externo is not None and await self.buscar_por_id_externo(
                pedido.origen, pedido.id_externo
            ):
                raise PedidoDuplicadoError(
                    f"{pedido.origen} {pedido.id_externo}"
                ) from None
            raise
        await self.session.refresh(modelo)
        return modelo.to_domain()

    async def actualizar_estado(
        self,
        pedido_id: str,
        nuevo_estado: str,
        estado_esperado: Optional[str] = None,
    ) -> bool:
        condiciones = [PedidoModel.id == uuid.UUID(str(pedido_id))]
        if estado_esperado is not None:
            condiciones.append(PedidoModel.estado == estado_esperado)
        resultado = await self.session.execute(
            update(PedidoModel)
            .where(*condiciones)
            .values(**self._valores_de_actualizacion(nuevo_estado))
        )
        await self.session.commit()
        return resultado.rowcount > 0

    @staticmethod
    def _valores_de_actualizacion(nuevo_estado) -> dict:
        """Valores del UPDATE: el nuevo estado y, solo la primera vez, cuándo
        (y quién) aceptó y terminó el pedido en cocina."""
        estado = getattr(nuevo_estado, "value", nuevo_estado)
        ahora = datetime.now(timezone.utc)
        valores: dict = {"estado": estado}
        if estado == EstadoPedido.EN_PREPARACION.value:
            # coalesce: si ya tenía valor (primera aceptación) se conserva.
            valores["fecha_aceptacion"] = func.coalesce(
                PedidoModel.fecha_aceptacion, ahora
            )
            valores["aceptado_por_id"] = func.coalesce(
                PedidoModel.aceptado_por_id, usuario_actual_id()
            )
        if estado == EstadoPedido.LISTA.value:
            valores["fecha_lista"] = func.coalesce(PedidoModel.fecha_lista, ahora)
        return valores

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

    async def listar_por_restaurante_desde(
        self, restaurante_id: str, desde: datetime
    ) -> list[Pedido]:
        stmt = select(PedidoModel).where(
            PedidoModel.restaurante_id == uuid.UUID(str(restaurante_id)),
            PedidoModel.fecha_creacion >= desde,
        )
        resultado = await self.session.execute(stmt)
        return [m.to_domain() for m in resultado.scalars().all()]

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
