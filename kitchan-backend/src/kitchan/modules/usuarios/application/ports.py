# Puerto de salida
# Es el que define comunicacion entre el nucleo y el adaptador de salida

from abc import ABC, abstractmethod
from typing import Optional
from src.kitchan.modules.usuarios.domain.entities import Usuario


class IUsuarioRepository(ABC):
    """
    Puerto de Salida: Define cómo el núcleo se comunica con la persistencia.
    """

    @abstractmethod
    async def guardar(self, usuario: Usuario) -> Usuario:
        pass

    @abstractmethod
    async def buscar_por_email(self, email: str) -> Optional[Usuario]:
        pass

    @abstractmethod
    async def buscar_por_id(self, id: str) -> Optional[Usuario]:
        pass

    @abstractmethod
    async def eliminar(self, id: str) -> None:
        pass

    @abstractmethod
    async def editar_contraseña(self, email: str, password_hash: str) -> None:
        pass

    @abstractmethod
    async def listar(self) -> list[Usuario]:
        pass


# Clase que implementa el HASHEO de las contraseñas
class IPasswordHasher(ABC):
    @abstractmethod
    def hashear(self, password: str) -> str:
        pass

    @abstractmethod
    def verificar(self, plain_password: str, hashed_password: str) -> bool:
        pass
