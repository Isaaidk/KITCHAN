import redis.asyncio as redis
from typing import Optional

from src.kitchan.modules.integraciones.uber.domain.ports import (
    UberTokenCachePort,
    UberOAuthStatePort
)


class RedisUberTokenAdapter(
    UberTokenCachePort,
    UberOAuthStatePort
):

    def __init__(self, redis_url: str):
        self.redis_client = redis.from_url(
            redis_url,
            decode_responses=True
        )

    # =========================================================
    # ACCESS TOKEN
    # =========================================================

    async def save_token(
        self,
        restaurante_id: str,
        token: str,
        expires_in: int
    ) -> None:

        key = f"uber_token:{restaurante_id}"

        ttl_seguro = (
            expires_in - 60
            if expires_in > 60
            else expires_in
        )

        await self.redis_client.setex(
            key,
            ttl_seguro,
            token
        )

    async def get_token(
        self,
        restaurante_id: str
    ) -> Optional[str]:

        key = f"uber_token:{restaurante_id}"

        return await self.redis_client.get(key)

    # =========================================================
    # OAUTH STATE
    # =========================================================

    async def save_state(
        self,
        state: str,
        restaurante_id: str,
        expires_in: int = 600
    ) -> None:

        key = f"uber_oauth_state:{state}"

        await self.redis_client.setex(
            key,
            expires_in,
            restaurante_id
        )
        valor = await self.redis_client.get(key)

        print("========== OAUTH STATE GUARDADO ==========")
        print("REDIS URL:", self.redis_client.connection_pool.connection_kwargs)
        print("KEY:", key)
        print("RESTAURANTE:", restaurante_id)
        print("VALOR GUARDADO:", valor)
        print("===========================================")



    async def get_restaurante_id(
        self,
        state: str
    ) -> Optional[str]:

        key = f"uber_oauth_state:{state}"
        valor = await self.redis_client.get(key)
        print("========== OAUTH STATE BUSCADO ==========")
        print("REDIS URL:", self.redis_client.connection_pool.connection_kwargs)
        print("KEY:", key)
        print("VALOR ENCONTRADO:", valor)
        print("==========================================")
        return valor


        return await self.redis_client.get(key)




    async def delete_state(
        self,
        state: str
    ) -> None:

        key = f"uber_oauth_state:{state}"

        await self.redis_client.delete(key)

    async def close(self):
        await self.redis_client.aclose()



    async def save_provisioning_token(self, restaurante_id: str, token: str, expires_in: int) -> None:
            key = f"uber_provisioning_token:{restaurante_id}"
            ttl_seguro = expires_in - 60 if expires_in > 60 else expires_in
            await self.redis_client.setex(key, ttl_seguro, token)

    async def get_provisioning_token(self, restaurante_id: str) -> Optional[str]:
        key = f"uber_provisioning_token:{restaurante_id}"
        return await self.redis_client.get(key)

    async def save_app_token(self, restaurante_id: str, token: str, expires_in: int) -> None:
        key = f"uber_app_token:{restaurante_id}"
        ttl_seguro = expires_in - 60 if expires_in > 60 else expires_in
        await self.redis_client.setex(key, ttl_seguro, token)

    async def get_app_token(self, restaurante_id: str) -> Optional[str]:
        key = f"uber_app_token:{restaurante_id}"
        return await self.redis_client.get(key)

    async def save_store_mapping(self, store_id: str, restaurante_id: str) -> None:
        """
        Crea el puente Multi-Tenant:
        Guarda la relación uber_store_mapping:{store_id} -> {restaurante_id}
        """
        key = f"uber_store_mapping:{store_id}"
        # No le ponemos expiración, este mapeo es permanente mientras dure la integración
        await self.redis_client.set(key, restaurante_id)
        print(f"🔗 [MULTI-TENANT] Mapeo creado en Redis: {store_id} pertenece a {restaurante_id}")

    async def get_restaurante_id_by_store(self, store_id: str) -> str | None:
        """
        Dado un ID de tienda de Uber, devuelve el ID del tenant de KITCHAN.
        """
        key = f"uber_store_mapping:{store_id}"
        restaurante_id = await self.redis_client.get(key)
        
        if restaurante_id:
            print(f"🔍 [MULTI-TENANT] Encontrado: Tienda {store_id} -> Tenant {restaurante_id}")
        else:
            print(f"⚠️ [MULTI-TENANT] No se encontró mapeo para la tienda {store_id}")
            
        return restaurante_id