# dominio
# Define como sera el usuario exactamente
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class RolUsuario(Enum):
    ADMIN = "ADMIN"
    OPERADOR = "OPERADOR"


@dataclass
class Usuario:
    id: str
    restaurante_id: str
    nombre: str
    email: str
    password_hash: str
    rol: RolUsuario
    estado: bool = True
    creado_en: Optional[datetime] = None
    # Último inicio de sesión; None si todavía no ha entrado.
    ultimo_acceso: Optional[datetime] = None


@dataclass
class CodigoRecuperacion:
    """Código de 6 dígitos enviado por correo; solo se conserva su hash."""

    id: str
    usuario_id: str
    codigo_hash: str
    expira_en: datetime
    creado_en: datetime
    intentos: int = 0
    usado: bool = False
