#dominio 
#Define como sera el usuario exactamente 
from dataclasses import dataclass
from enum import Enum

class RolUsuario(Enum):
    ADMIN="ADMIN"
    OPERADOR ="OPERADOR"

@dataclass
class Usuario:
    id:str
    nombre:str
    email:str
    password_hash: str
    rol:RolUsuario
    estado: bool = True
