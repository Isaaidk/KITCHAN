import uuid

from sqlalchemy import UUID, Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.kitchan.core.database import Base
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.kitchan.modules.usuarios.infrastructure.models import UsuarioModel


class RestauranteModel(Base):
    __tablename__ = "restaurantes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    nombre_comercial: Mapped[str] = mapped_column(String(150), nullable=False)
    razon_social: Mapped[str] = mapped_column(String(150), nullable=False)
    identificacion_fiscal: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False
    )
    direccion: Mapped[str] = mapped_column(String(255), nullable=False)
    telefono: Mapped[str] = mapped_column(String(20), nullable=False)
    email_corporativo: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False
    )
    estado: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relación inversa hacia usuarios
    usuarios: Mapped[list["UsuarioModel"]] = relationship(
        back_populates="restaurante", cascade="all, delete-orphan"
    )
