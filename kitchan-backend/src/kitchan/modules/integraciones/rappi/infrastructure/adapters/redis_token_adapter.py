"""Infraestructura de Rappi: caché del access token de aplicación en Redis
(equivalente a RedisUberTokenAdapter, pero con una sola clave global porque
Rappi usa client-credentials y no un token por restaurante).
"""

from typing import Optional

import redis.asyncio as redis

from src.kitchan.modules.integraciones.rappi.domain.ports import RappiTokenCachePort

CLAVE_TOKEN = "rappi_app_token"


class RedisRappiTokenAdapter(RappiTokenCachePort):
    def __init__(self, redis_url: str):
        self.redis_client = redis.from_url(redis_url, decode_responses=True)

    async def save_app_token(self, token: str, expires_in: int) -> None:
        ttl_seguro = expires_in - 60 if expires_in > 60 else expires_in
        await self.redis_client.setex(CLAVE_TOKEN, ttl_seguro, token)

    async def get_app_token(self) -> Optional[str]:
        return await self.redis_client.get(CLAVE_TOKEN)
