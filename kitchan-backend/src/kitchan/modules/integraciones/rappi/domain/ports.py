"""Dominio de la integración Rappi: puertos de salida hacia la API pública
de Rappi (Restaurants Integrations Public API), hacia el caché del token de
aplicación y hacia el mapeo de tiendas dado de alta manualmente.
"""

from abc import ABC, abstractmethod
from typing import Optional


class RappiApiPort(ABC):
    """
    Puerto exclusivo para la comunicación HTTP con la API de Rappi. Es el
    equivalente a UberApiPort / PedidosYaApiPort, acotado a las operaciones
    que tienen paridad con las acciones del KDS (accept -> take,
    deny -> reject, ready -> ready-for-pickup).

    Nota: la API pública de Rappi no documenta un endpoint para cancelar un
    pedido YA TOMADO (el equivalente a /cancel de Uber), por eso no existe
    ese método aquí.
    """

    @abstractmethod
    async def take_order(
        self, order_id: str, cooking_time: Optional[int] = None
    ) -> bool:
        """Toma (acepta) un pedido. Solo válido mientras está en SENT."""
        pass

    @abstractmethod
    async def reject_order(self, order_id: str, reason: str, cancel_type: str) -> bool:
        """Rechaza un pedido. Solo válido mientras está en SENT."""
        pass

    @abstractmethod
    async def mark_ready_for_pickup(self, order_id: str) -> bool:
        """Marca un pedido como listo para recoger (Rappi limita a 3 llamadas por pedido)."""
        pass


class RappiTokenCachePort(ABC):
    """
    Caché del access token de Rappi. A diferencia de Uber (un token por
    restaurante, obtenido vía OAuth del merchant), Rappi usa
    client-credentials: un único token para toda la aplicación.
    """

    @abstractmethod
    async def save_app_token(self, token: str, expires_in: int) -> None:
        pass

    @abstractmethod
    async def get_app_token(self) -> Optional[str]:
        pass


class RappiMerchantTokenCachePort(ABC):
    """
    Caché del token del COMERCIO (el `id_token` que entrega el OAuth de
    Rappi). La API v2 exige dos tokens en cada llamada: el del integrador
    (client-credentials, ver RappiTokenCachePort) y este, que identifica al
    comercio que autorizó a KITCHAN.
    """

    @abstractmethod
    async def save_merchant_token(self, token: str, expires_in: int) -> None:
        pass

    @abstractmethod
    async def get_merchant_token(self) -> Optional[str]:
        pass


class RappiOAuthStatePort(ABC):
    """Guarda, mientras el comercio autoriza en Rappi, el `code_verifier` de
    PKCE asociado al `state` de esa autorización."""

    @abstractmethod
    async def save_state(
        self, state: str, code_verifier: str, expires_in: int = 600
    ) -> None:
        pass

    @abstractmethod
    async def pop_code_verifier(self, state: str) -> Optional[str]:
        """Devuelve y elimina el code_verifier (el state solo sirve una vez)."""
        pass


class RappiOAuthPort(ABC):
    """Cliente del endpoint de tokens del OAuth de Rappi."""

    @abstractmethod
    async def exchange_code(
        self, code: str, code_verifier: str, redirect_uri: str
    ) -> tuple[str, int]:
        """Cambia el `code` por el token del comercio. Devuelve
        (id_token, segundos de vigencia). Lanza RappiOAuthError si falla."""
        pass


class RappiStoreMappingPort(ABC):
    """
    Puerto para resolver el id de tienda de Rappi (store.internal_id /
    store_id) hacia el `restaurante_id` interno de KITCHAN.

    Igual que en PedidosYa (y a diferencia de Uber), el alta de tiendas en
    Rappi es manual, por eso este mapeo es estático/configurado de antemano.
    """

    @abstractmethod
    async def get_restaurante_id(self, store_id: str) -> Optional[str]:
        pass
