import uuid
from datetime import datetime

from sqlalchemy import UUID, DateTime, Integer, Numeric, String, Text, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column

from src.kitchan.core.database import Base
from src.kitchan.modules.facturacion.domain.entities import (
    EstadoFactura,
    FacturaPedido,
)


class FacturaPedidoModel(Base):
    """Factura electrónica de un pedido. Una por pedido: el pedido_id es la
    clave primaria. Sin llave foránea a `pedidos` para no acoplar los módulos
    en la base de datos."""

    __tablename__ = "facturas_pedidos"

    pedido_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    restaurante_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    odoo_move_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    numero: Mapped[str | None] = mapped_column(String(64), nullable=True)
    estado: Mapped[EstadoFactura] = mapped_column(
        SQLEnum(EstadoFactura, name="estado_factura_enum"), nullable=False, index=True
    )
    total: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    numero_autorizacion: Mapped[str | None] = mapped_column(String(64), nullable=True)
    fecha_autorizacion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    mensaje_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    fecha_actualizacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def to_domain(self) -> FacturaPedido:
        return FacturaPedido(
            pedido_id=str(self.pedido_id),
            restaurante_id=str(self.restaurante_id),
            odoo_move_id=self.odoo_move_id,
            numero=self.numero,
            estado=EstadoFactura(self.estado),
            total=float(self.total or 0),
            numero_autorizacion=self.numero_autorizacion,
            fecha_autorizacion=self.fecha_autorizacion,
            mensaje_error=self.mensaje_error,
            fecha_actualizacion=self.fecha_actualizacion,
        )
