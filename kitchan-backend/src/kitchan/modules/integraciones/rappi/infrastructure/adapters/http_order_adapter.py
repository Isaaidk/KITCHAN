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
    RappiMerchantTokenCachePort,
    RappiTokenCachePort,
)

# Dominios de desarrollo documentados por Rappi. En producción se reemplazan
# por los del país (Ecuador: https://api.rappi.com.ec para auth; el dominio
# productivo de la API de pedidos lo confirma Rappi durante el alta).
RAPPI_AUTH_BASE_DEFAULT = "https://api.dev.rappi.com"
RAPPI_API_BASE_DEFAULT = "https://microservices.dev.rappi.com"

ORDERS_PATH = "/api/v2/restaurants-integrations-public-api/orders"
MENU_PATH = "/api/v2/restaurants-integrations-public-api/menu"
TOKEN_PATH = "/restaurants/auth/v1/token/login/integrations"

# El login de Auth0 (`rests-integrations-dev.auth0.com`) entrega un token que la
# API rechaza con 401 "v1_disabled" aunque el login responda 200. El token que
# sirve (menú, tiendas, webhooks y pedidos, verificado con el sandbox: 200) es el
# del login propio de Rappi, `{RAPPI_AUTH_BASE}/restaurants/auth/v1/token/login/
# integrations`, que responde 307 hacia la misma ruta con "/" final.


class RappiHttpAdapter(RappiApiPort):
    def __init__(self, token_cache: RappiTokenCachePort):
        self.token_cache = token_cache
        self.auth_base = os.getenv("RAPPI_AUTH_BASE", RAPPI_AUTH_BASE_DEFAULT)
        self.api_base = os.getenv("RAPPI_API_BASE", RAPPI_API_BASE_DEFAULT)
        self.client_id = os.getenv("RAPPI_CLIENT_ID")
        self.client_secret = os.getenv("RAPPI_CLIENT_SECRET")
        self.audience = os.getenv("RAPPI_AUDIENCE")

    def _url_login(self) -> str:
        """URL del login: la de RAPPI_AUTH_URL si está definida; si no, el login
        de Rappi (y el del simulador local) bajo RAPPI_AUTH_BASE."""
        url = (os.getenv("RAPPI_AUTH_URL") or "").strip()
        if url:
            return url
        return f"{self.auth_base}{TOKEN_PATH}"

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
            # Rappi responde 307 hacia la ruta con "/" final; el 307 conserva el
            # método y el cuerpo, así que basta con seguirlo.
            respuesta = await client.post(
                self._url_login(), json=body, timeout=15, follow_redirects=True
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

    async def _token_comercio(self) -> Optional[str]:
        if isinstance(self.token_cache, RappiMerchantTokenCachePort):
            return await self.token_cache.get_merchant_token()
        return None

    async def _llamar(
        self, metodo: str, path: str, accion: str, json: Optional[dict] = None
    ) -> bool:
        token = await self._obtener_token()
        headers = {"x-authorization": f"Bearer {token}"}
        token_comercio = await self._token_comercio()
        if token_comercio:
            # Token del comercio (OAuth): Rappi lo pide para actuar en nombre de
            # una tienda; las rutas de tiendas propias responden igual sin el.
            headers["Authorization-Partners"] = f"Bearer {token_comercio}"

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

    async def upload_menu(self, menu: dict) -> bool:
        """Envía el menú a la tienda PADRE (`menu["storeId"]`); la hija lo
        hereda. Con mapeo automático cada producto debe llevar su sku."""
        return await self._llamar("POST", MENU_PATH, "MENU", json=menu)

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
