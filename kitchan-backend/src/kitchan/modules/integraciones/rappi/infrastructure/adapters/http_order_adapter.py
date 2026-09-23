"""Infraestructura de Rappi: adaptador que implementa RappiApiPort contra la
Restaurants Integrations Public API de Rappi (equivalente a UberHttpAdapter /
PedidosYaHttpAdapter).

Autenticación: OAuth client-credentials. Se pide un token a
POST {RAPPI_AUTH_BASE}/restaurants/auth/v1/token/login/integrations y se
envía en el header `x-authorization: Bearer <token>` (no `Authorization`).
"""

import os
from typing import Optional

import httpx
from fastapi import HTTPException

from src.kitchan.modules.integraciones.rappi.domain.ports import (
    RappiApiPort,
    RappiTokenCachePort,
)

# Dominios de desarrollo documentados por Rappi. En producción se reemplazan
# por los del país (Ecuador: https://api.rappi.com.ec para auth; el dominio
# productivo de la API de pedidos lo confirma Rappi durante el alta).
RAPPI_AUTH_BASE_DEFAULT = "https://api.dev.rappi.com"
RAPPI_API_BASE_DEFAULT = "https://microservices.dev.rappi.com"

ORDERS_PATH = "/api/v2/restaurants-integrations-public-api/orders"
TOKEN_PATH = "/restaurants/auth/v1/token/login/integrations"


class RappiHttpAdapter(RappiApiPort):
    def __init__(self, token_cache: RappiTokenCachePort):
        self.token_cache = token_cache
        self.auth_base = os.getenv("RAPPI_AUTH_BASE", RAPPI_AUTH_BASE_DEFAULT)
        self.api_base = os.getenv("RAPPI_API_BASE", RAPPI_API_BASE_DEFAULT)
        self.client_id = os.getenv("RAPPI_CLIENT_ID")
        self.client_secret = os.getenv("RAPPI_CLIENT_SECRET")
        self.audience = os.getenv("RAPPI_AUDIENCE")

    async def _obtener_token(self) -> str:
        token = await self.token_cache.get_app_token()
        if token:
            return token

        if not self.client_id or not self.client_secret:
            raise HTTPException(
                status_code=401,
                detail="Credenciales de Rappi (client_id/client_secret) no configuradas.",
            )

        # TODO: la doc pública solo muestra el endpoint; los nombres del body
        # (client_id, client_secret, audience, grant_type) y de la respuesta
        # (access_token, expires_in) son el estándar client-credentials y
        # deben confirmarse con las credenciales reales que entregue Rappi.
        body = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials",
        }
        if self.audience:
            body["audience"] = self.audience

        async with httpx.AsyncClient() as client:
            respuesta = await client.post(
                f"{self.auth_base}{TOKEN_PATH}", json=body, timeout=15
            )

        if respuesta.status_code != 200:
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "No se pudo obtener el token de Rappi",
                    "respuesta": respuesta.text,
                },
            )

        datos = respuesta.json()
        token = datos.get("access_token")
        if not token:
            raise HTTPException(
                status_code=401, detail="Rappi no devolvió access_token."
            )

        await self.token_cache.save_app_token(token, int(datos.get("expires_in", 3600)))
        return token

    async def _llamar(
        self, metodo: str, path: str, accion: str, json: Optional[dict] = None
    ) -> bool:
        token = await self._obtener_token()
        headers = {"x-authorization": f"Bearer {token}"}

        async with httpx.AsyncClient() as client:
            respuesta = await client.request(
                metodo,
                f"{self.api_base}{path}",
                json=json,
                headers=headers,
                timeout=15,
            )

        print(f"📡 [RAPPI {accion}] {metodo} {path} -> {respuesta.status_code}")

        if respuesta.status_code not in (200, 204):
            raise HTTPException(
                status_code=respuesta.status_code,
                detail={
                    "error": f"No se pudo ejecutar '{accion}' en Rappi",
                    "respuesta": respuesta.text,
                },
            )
        return True

    async def take_order(
        self, order_id: str, cooking_time: Optional[int] = None
    ) -> bool:
        # Sin cooking_time, Rappi usa el tiempo de cocción por defecto de la tienda.
        path = f"{ORDERS_PATH}/{order_id}/take"
        if cooking_time is not None:
            path = f"{path}/{cooking_time}"
        return await self._llamar("PUT", path, "TAKE")

    async def reject_order(self, order_id: str, reason: str, cancel_type: str) -> bool:
        return await self._llamar(
            "PUT",
            f"{ORDERS_PATH}/{order_id}/reject",
            "REJECT",
            json={"reason": reason, "cancel_type": cancel_type},
        )

    async def mark_ready_for_pickup(self, order_id: str) -> bool:
        return await self._llamar(
            "POST", f"{ORDERS_PATH}/{order_id}/ready-for-pickup", "READY"
        )
