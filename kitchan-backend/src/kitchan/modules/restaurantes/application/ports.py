from abc import ABC, abstractmethod

from src.kitchan.modules.restaurantes.domain.entities import Restaurante
from src.kitchan.modules.usuarios.domain.entities import Usuario


class IRestauranteRepository(ABC):
    @abstractmethod
    async def crear_con_admin(
        self, restaurante: Restaurante, admin: Usuario
    ) -> tuple[Restaurante, Usuario]:
        """
        Guarda un Restaurante y su Usuario Administrador en una única transacción ACID.
        Si algo falla, no se guarda ninguno de los dos.
        """
        pass
