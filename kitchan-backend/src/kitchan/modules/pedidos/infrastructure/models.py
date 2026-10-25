import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    UUID,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    func,
    text,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.kitchan.core.database import Base
from src.kitchan.modules.pedidos.domain.entities import EstadoPedido, Pedido, PedidoItem


class PedidoModel(Base):
    __tablename__ = "pedidos"
    __table_args__ = (
        # Un mismo pedido de una plataforma no puede guardarse dos veces. Los
        # pedidos sin id externo (p. ej. LOCAL) quedan fuera del índice.
        Index(
            "uq_pedidos_origen_id_externo",
            "origen",
            "id_externo",
            unique=True,
            postgresql_where=text("id_externo IS NOT NULL"),
            sqlite_where=text("id_externo IS NOT NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    restaurante_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("restaurantes.id"), nullable=False, index=True
    )
    origen: Mapped[str] = mapped_column(String(30), nullable=False)
    id_externo: Mapped[str | None] = mapped_column(
        String(100), nullable=True, index=True
    )
    cliente: Mapped[str] = mapped_column(String(150), nullable=False)
    nota_cliente: Mapped[str | None] = mapped_column(String(500), nullable=True)
    items: Mapped[list] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=False
    )
    total: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    estado: Mapped[EstadoPedido] = mapped_column(
        SQLEnum(EstadoPedido, name="estado_pedido_enum"), nullable=False
    )
    estado_entrega: Mapped[str | None] = mapped_column(String(50), nullable=True)
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    fecha_actualizacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    metodo_pago: Mapped[str | None] = mapped_column(String(30), nullable=True)
    fecha_aceptacion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    fecha_lista: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    aceptado_por_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True, index=True
    )

    def to_domain(self) -> Pedido:
        return Pedido(
            id=str(self.id),
            restaurante_id=str(self.restaurante_id),
            origen=self.origen,
            id_externo=self.id_externo,
            cliente=self.cliente,
            nota_cliente=self.nota_cliente,
            items=[PedidoItem(**item) for item in self.items],
            total=float(self.total),
            estado=EstadoPedido(self.estado),
            estado_entrega=self.estado_entrega,
            fecha_creacion=self.fecha_creacion,
            fecha_actualizacion=self.fecha_actualizacion,
            metodo_pago=self.metodo_pago,
            fecha_aceptacion=self.fecha_aceptacion,
            fecha_lista=self.fecha_lista,
            aceptado_por_id=self.aceptado_por_id,
        )

    @staticmethod
    def from_domain(pedido: Pedido) -> "PedidoModel":
        return PedidoModel(
            id=uuid.UUID(str(pedido.id)),
            restaurante_id=uuid.UUID(str(pedido.restaurante_id)),
            origen=pedido.origen,
            id_externo=pedido.id_externo,
            cliente=pedido.cliente,
            nota_cliente=pedido.nota_cliente,
            items=[item.model_dump() for item in pedido.items],
            total=pedido.total,
            estado=pedido.estado,
            estado_entrega=pedido.estado_entrega,
            metodo_pago=pedido.metodo_pago,
        )
