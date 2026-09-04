from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


# --- Esquemas de Entrada (Request) ---
class RestauranteCreateRequest(BaseModel):
    nombre_comercial: str
    razon_social: str
    identificacion_fiscal: str
    direccion: str
    telefono: str
    email_corporativo: EmailStr


class AdminCreateRequest(BaseModel):
    nombre: str
    email: EmailStr
    password: str


class OnboardingRequest(BaseModel):
    restaurante: RestauranteCreateRequest
    admin: AdminCreateRequest


# --- Esquemas de Salida (Response) ---
class RestauranteResponse(BaseModel):
    id: str
    nombre_comercial: str
    email_corporativo: EmailStr
    estado: bool
    fecha_registro: Optional[datetime] = None

    class Config:
        from_attributes = True


# Reutilizamos el esquema de salida de Usuario, pero lo definimos aquí si lo necesitas
class UsuarioSaaSResponse(BaseModel):
    id: str
    restaurante_id: str
    nombre: str
    email: str
    rol: str
    estado: bool

    class Config:
        from_attributes = True


class OnboardingResponse(BaseModel):
    restaurante: RestauranteResponse
    admin: UsuarioSaaSResponse
