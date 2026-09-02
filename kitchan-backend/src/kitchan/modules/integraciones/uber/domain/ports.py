from abc import ABC, abstractmethod
from typing import Optional

class UberTokenCachePort(ABC):
    """
    Puerto para gestionar el almacenamiento de los tokens de Uber.
    Se separan los tokens de Provisioning (OAuth) y de Aplicación (Client Credentials).
    """

    @abstractmethod
    async def save_provisioning_token(self, restaurante_id: str, token: str, expires_in: int) -> None:
        pass

    @abstractmethod
    async def get_provisioning_token(self, restaurante_id: str) -> Optional[str]:
        pass

    @abstractmethod
    async def save_app_token(self, restaurante_id: str, token: str, expires_in: int) -> None:
        pass

    @abstractmethod
    async def get_app_token(self, restaurante_id: str) -> Optional[str]:
        pass

    @abstractmethod
    async def save_store_mapping(self, store_id: str, restaurante_id: str) -> None:
        """Guarda la relación store_id (Uber) -> restaurante_id (Kitchan)"""
        pass

    @abstractmethod
    async def get_restaurante_id_by_store(self, store_id: str) -> str | None:
        """Obtiene el restaurante_id a partir del store_id de Uber"""
        pass


class UberOAuthStatePort(ABC):
    """
    Puerto para almacenar temporalmente el state generado
    durante el flujo OAuth.
    """

    @abstractmethod
    async def save_state(self, state: str, restaurante_id: str, expires_in: int = 600) -> None:
        pass

    @abstractmethod
    async def get_restaurante_id(self, state: str) -> Optional[str]:
        pass

    @abstractmethod
    async def delete_state(self, state: str) -> None:
        pass


class UberApiPort(ABC):
    """
    Puerto exclusivo para la comunicación HTTP con la API de Uber.
    """

    @abstractmethod
    async def get_order_details(self, order_id: str, access_token: str) -> dict:
        pass

    @abstractmethod
    async def accept_order(self, order_id: str, access_token: str, reason: str = "Accepted") -> bool:
        pass

    @abstractmethod
    async def deny_order(self, order_id: str, access_token: str, reason: str, explanation: str) -> bool:
        pass

    @abstractmethod
    async def mark_order_ready(
        self,
        order_id: str,
        access_token: str
    ) -> bool:
        pass