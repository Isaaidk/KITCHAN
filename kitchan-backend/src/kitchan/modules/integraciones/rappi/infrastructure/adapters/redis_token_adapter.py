"""Infraestructura de Rappi: caché de los tokens en Redis.

- Token de aplicación (integrador, client-credentials): una sola clave global.
- Token del comercio (OAuth): también global, porque hoy KITCHAN opera un solo
  comercio ante Rappi; es el `id_token` que devuelve el flujo de autorización.
- Estado del OAuth: `state` -> `code_verifier` de PKCE, de un solo uso.
"""

from typing import Optional

import redis.asyncio as redis

from src.kitchan.modules.integraciones.rappi.domain.ports import (
    RappiMerchantTokenCachePort,
    RappiOAuthStatePort,
    RappiTokenCachePort,
)

CLAVE_TOKEN = "rappi_app_token"
CLAVE_TOKEN_COMERCIO = "rappi_merchant_token"
PREFIJO_ESTADO = "rappi_oauth_state:"


def _ttl_seguro(expires_in: int) -> int:
    return expires_in - 60 if expires_in > 60 else expires_in


class RedisRappiTokenAdapter(
    RappiTokenCachePort, RappiMerchantTokenCachePort, RappiOAuthStatePort
):
    def __init__(self, redis_url: str):
        self.redis_client = redis.from_url(redis_url, decode_responses=True)

    async def save_app_token(self, token: str, expires_in: int) -> None:
        await self.redis_client.setex(CLAVE_TOKEN, _ttl_seguro(expires_in), token)

    async def get_app_token(self) -> Optional[str]:
        return await self.redis_client.get(CLAVE_TOKEN)

    async def save_merchant_token(self, token: str, expires_in: int) -> None:
        await self.redis_client.setex(
            CLAVE_TOKEN_COMERCIO, _ttl_seguro(expires_in), token
        )

    async def get_merchant_token(self) -> Optional[str]:
        return await self.redis_client.get(CLAVE_TOKEN_COMERCIO)

    async def save_state(
        self, state: str, code_verifier: str, expires_in: int = 600
    ) -> None:
        await self.redis_client.setex(PREFIJO_ESTADO + state, expires_in, code_verifier)

    async def pop_code_verifier(self, state: str) -> Optional[str]:
        # GETDEL: lee y borra en un solo paso, así un state no se puede reusar.
        return await self.redis_client.getdel(PREFIJO_ESTADO + state)
