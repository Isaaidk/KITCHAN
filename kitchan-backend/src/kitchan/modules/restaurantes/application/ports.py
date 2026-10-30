from abc import ABC, abstractmethod
from typing import Protocol

from src.kitchan.modules.restaurantes.domain.entities import (
    AdministradorInicial,
    Restaurante,
)


class IPasswordHasher(Protocol):
    """Puerto propio: cifrar la contraseña del administrador inicial.

    Es un Protocol (tipado estructural) para que cualquier adaptador con un
    método `hashear` lo cumpla sin que este módulo importe a Usuarios.
    """

    def hashear(self, password: str) -> str: ...


class IRestauranteRepository(ABC):
    @abstractmethod
    async def crear_con_admin(
        self, restaurante: Restaurante, admin: AdministradorInicial
    ) -> tuple[Restaurante, AdministradorInicial]:
        """
        Guarda un Restaurante y su Usuario Administrador en una única transacción ACID.
        Si algo falla, no se guarda ninguno de los dos.
        """
        pass
