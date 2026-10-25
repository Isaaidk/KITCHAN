"""Token de aplicación de Uber que se renueva solo.

El App Token (Client Credentials) vive en Redis. Si Redis se reinicia o el
token caduca, los webhooks de pedidos fallaban con 500 ("Token no disponible
para descargar la orden") hasta que alguien regeneraba el token a mano. Este
adaptador, cuando no encuentra el token, lo pide a Uber, lo guarda y sigue.
"""

import asyncio
import logging
import os
from typing import Awaitable, Callable, Optional

import httpx

from src.kitchan.modules.integraciones.uber.infrastructure.adapters.redis_token_adapter import (
    RedisUberTokenAdapter,
)

logger = logging.getLogger(__name__)

# El resto del módulo de Uber usa el login de sandbox; se cambia por el de
# producción cuando Uber apruebe la integración.
UBER_TOKEN_URL = "https://sandbox-login.uber.com/oauth/v2/token"
UBER_APP_SCOPE = "eats.store eats.order"

# Evita que varios webhooks simultáneos pidan el mismo token a la vez.
_RENOVACION = asyncio.Lock()


def _limpio(valor: Optional[str]) -> str:
    return (valor or "").strip().replace('"', "").replace("'", "")


async def solicitar_app_token() -> tuple[str, int]:
    """Pide un token por Client Credentials. Devuelve (token, expires_in)."""
    client_id = _limpio(os.getenv("UBER_CLIENT_ID"))
    client_secret = _limpio(os.getenv("UBER_CLIENT_SECRET"))
    if not client_id or not client_secret:
        raise RuntimeError("Faltan UBER_CLIENT_ID o UBER_CLIENT_SECRET en el .env")

    async with httpx.AsyncClient() as client:
        respuesta = await client.post(
            UBER_TOKEN_URL,
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "grant_type": "client_credentials",
                "scope": UBER_APP_SCOPE,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30,
        )

    if respuesta.status_code != 200:
        raise RuntimeError(
            f"Uber rechazó la solicitud del token ({respuesta.status_code})"
        )

    datos = respuesta.json()
    token = datos.get("access_token")
    if not token:
        raise RuntimeError("Uber no devolvió access_token")
    return token, int(datos.get("expires_in") or 3600)


class RedisUberTokenAdapterRenovable(RedisUberTokenAdapter):
    """RedisUberTokenAdapter que renueva el App Token cuando falta."""

    def __init__(
        self,
        redis_url: str,
        solicitar_token: Callable[[], Awaitable[tuple[str, int]]] = solicitar_app_token,
    ):
        super().__init__(redis_url=redis_url)
        self._solicitar_token = solicitar_token

    async def get_app_token(self, restaurante_id: str) -> Optional[str]:
        token = await super().get_app_token(restaurante_id)
        if token:
            return token

        async with _RENOVACION:
            # Otro webhook pudo renovarlo mientras esperábamos el candado.
            token = await super().get_app_token(restaurante_id)
            if token:
                return token

            logger.warning(
                "No hay App Token de Uber para el restaurante %s; se solicita uno nuevo.",
                restaurante_id,
            )
            try:
                nuevo, expira_en = await self._solicitar_token()
            except Exception as error:
                # Se devuelve None: el caso de uso informa el error de siempre.
                logger.error("No se pudo renovar el App Token de Uber: %s", error)
                return None

            await self.save_app_token(restaurante_id, nuevo, expira_en)
            return nuevo
