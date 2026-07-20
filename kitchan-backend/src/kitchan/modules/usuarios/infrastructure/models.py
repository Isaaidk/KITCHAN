import uuid
from sqlalchemy import String, Boolean, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
import enum

from src.kitchan.core.database import Base
#Adapatador de salida
#Mapea las los datos 
class RolUsuario(str, enum.Enum):
    ADMIN = "ADMIN"
    OPERADOR = "OPERADOR"

class UsuarioModel(Base):
    __tablename__ = "usuarios"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,
        index=True
    )
    
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    
    email: Mapped[str] = mapped_column(String(150), unique=True, index=True, nullable=False)
    
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    
    rol: Mapped[RolUsuario] = mapped_column(
        SQLEnum(RolUsuario, name="rol_usuario_enum", create_type=False), 
        nullable=False
    )
    
    estado: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def to_domain(self):
        from src.kitchan.modules.usuarios.domain.entities import Usuario
        return Usuario(
            id=str(self.id),
            nombre=self.nombre,
            email=self.email,
            password_hash=self.password_hash,
            rol=RolUsuario(self.rol),
            estado=self.estado
        )