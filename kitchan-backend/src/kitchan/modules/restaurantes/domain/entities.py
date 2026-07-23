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
