import enum
import uuid

from datetime import datetime, timezone

from sqlalchemy import UUID, Boolean, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.kitchan.core.database import Base
from src.kitchan.modules.usuarios.domain.entities import RolUsuario, Usuario

# Adaptador de salida
# Mapea los datos


class UsuarioModel(Base):
    __tablename__ = "usuarios"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )

    # Clave foránea hacia el restaurante. Se referencia la tabla por nombre
    # (sin importar el modelo de restaurantes) para que los dos módulos no
    # dependan uno del otro.
    restaurante_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("restaurantes.id"), nullable=False
    )

    nombre: Mapped[str] = mapped_column(String(100), nullable=False)

    email: Mapped[str] = mapped_column(
        String(150), unique=True, index=True, nullable=False
    )

    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    rol: Mapped[RolUsuario] = mapped_column(
        SQLEnum(RolUsuario, name="rol_usuario_enum", create_type=False), nullable=False
    )

    estado: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )
    ultimo_acceso: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

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
            creado_en=self.creado_en,
            ultimo_acceso=self.ultimo_acceso,
        )


class CodigoRecuperacionModel(Base):
    """Código de un solo uso (guardado como hash) para restablecer la contraseña."""

    __tablename__ = "codigos_recuperacion"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    codigo_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expira_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    intentos: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    usado: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def to_domain(self):
        from src.kitchan.modules.usuarios.domain.entities import CodigoRecuperacion

        return CodigoRecuperacion(
            id=str(self.id),
            usuario_id=str(self.usuario_id),
            codigo_hash=self.codigo_hash,
            expira_en=self.expira_en,
            intentos=self.intentos,
            usado=self.usado,
            creado_en=self.creado_en,
        )
