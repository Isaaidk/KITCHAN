import enum
import uuid

from sqlalchemy import UUID, Boolean
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.kitchan.core.database import Base
from src.kitchan.modules.usuarios.domain.entities import RolUsuario, Usuario

# Adaptador de salida
# Mapea los datos


class UsuarioModel(Base):
    __tablename__ = "usuarios"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )

    # 1. Clave foránea hacia el restaurante (Usando sintaxis SQLAlchemy 2.0)
    restaurante_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("restaurantes.id"), nullable=False
    )

    # 2. Relación bidireccional (El string "RestauranteModel" evita errores de importación circular)
    restaurante: Mapped["RestauranteModel"] = relationship(back_populates="usuarios")

    nombre: Mapped[str] = mapped_column(String(100), nullable=False)

    email: Mapped[str] = mapped_column(
        String(150), unique=True, index=True, nullable=False
    )

    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    rol: Mapped[RolUsuario] = mapped_column(
        SQLEnum(RolUsuario, name="rol_usuario_enum", create_type=False), nullable=False
    )

    estado: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def to_domain(self):
        from src.kitchan.modules.usuarios.domain.entities import Usuario

        return Usuario(
            id=str(self.id),
            restaurante_id=str(
                self.restaurante_id
            ),  # <- Añadimos el nuevo campo al dominio
            nombre=self.nombre,
            email=self.email,
            password_hash=self.password_hash,
            rol=RolUsuario(self.rol),
            estado=self.estado,
        )
