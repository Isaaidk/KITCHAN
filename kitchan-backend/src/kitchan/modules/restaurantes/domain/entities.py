from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Restaurante:
    id: str
    nombre_comercial: str
    razon_social: str
    identificacion_fiscal: str
    direccion: str
    telefono: str
    email_corporativo: str
    estado: bool
    fecha_registro: Optional[datetime] = None


ROL_ADMIN = "ADMIN"


@dataclass
class AdministradorInicial:
    """Cuenta administradora que nace junto con el restaurante (onboarding).

    Es la visión propia de este módulo: Restaurantes no importa las entidades de
    Usuarios; solo sabe que debe crear una cuenta ADMIN junto al restaurante.
    """

    id: str
    restaurante_id: str
    nombre: str
    email: str
    password_hash: str
    rol: str = ROL_ADMIN
    estado: bool = True
