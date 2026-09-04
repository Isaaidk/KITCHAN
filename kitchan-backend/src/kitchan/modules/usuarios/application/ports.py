# Puerto de salida
# Es el que define comunicacion entre el nucleo y el adaptador de salida

from abc import ABC, abstractmethod
from typing import Optional

from src.kitchan.modules.usuarios.domain.entities import RolUsuario, Usuario


class IUsuarioRepository(ABC):
    """
    Puerto de Salida: Define cómo el núcleo se comunica con la persistencia.
    """

    @abstractmethod
    async def crear(self, usuario: Usuario) -> Usuario:
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
    async def actualizar_datos(
        self, usuario_id: str, nombre: str, rol: RolUsuario
    ) -> Optional[Usuario]:
        """Edita nombre/rol de un usuario existente (usado por el CRUD de Admin)."""
        pass

    @abstractmethod
    async def cambiar_estado(self, usuario_id: str, estado: bool) -> Optional[Usuario]:
        """Activa/desactiva un usuario sin eliminarlo."""
        pass

    @abstractmethod
    async def listar_por_restaurante(self, restaurante_id: str) -> list[Usuario]:
        """Lista únicamente los usuarios que pertenecen a un restaurante específico (Multi-tenant)."""
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


# Puerto de salida: define cómo el núcleo pide la generación de un token de acceso,
# sin conocer la librería/algoritmo concreto usado para firmarlo (JWT, etc.)
class ITokenGenerator(ABC):
    @abstractmethod
    def generar_token(self, data: dict) -> str:
        pass

    @abstractmethod
    def decodificar_token(self, token: str) -> dict:
        """Valida la firma/expiración del token y retorna sus claims.

        Debe lanzar ValueError si el token es inválido o expiró.
        """
        pass
