"""Infraestructura de Rappi: cliente del endpoint de tokens del OAuth
(`/oauth/token`, formulario `application/x-www-form-urlencoded`).

Rappi entrega un `access_token` opaco (JWE) que la API rechaza con
"Invalid merchant token signature"; el token que sirve es el **`id_token`**
(JWT RS256 de tres partes).
"""

import logging
import os
from typing import Optional

import httpx

from src.kitchan.modules.integraciones.rappi.domain.exceptions import RappiOAuthError
from src.kitchan.modules.integraciones.rappi.domain.ports import RappiOAuthPort

logger = logging.getLogger(__name__)

AUTHORIZE_URL_DEV = "https://login.partners.dev.rappi.com/authorize"
TOKEN_URL_DEV = "https://login.partners.dev.rappi.com/oauth/token"

# Si la respuesta no trae `expires_in`, se asume una hora (conservador).
VIGENCIA_POR_DEFECTO = 3600


class RappiOAuthHttpAdapter(RappiOAuthPort):
    def __init__(
        self, token_url: Optional[str] = None, client_id: Optional[str] = None
    ):
        self.token_url = token_url or os.getenv("RAPPI_OAUTH_TOKEN_URL", TOKEN_URL_DEV)
        self.client_id = client_id or os.getenv("RAPPI_OAUTH_CLIENT_ID", "")

    async def exchange_code(
        self, code: str, code_verifier: str, redirect_uri: str
    ) -> tuple[str, int]:
        if not self.client_id:
            raise RappiOAuthError("Falta RAPPI_OAUTH_CLIENT_ID.")

        formulario = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": self.client_id,
            "code_verifier": code_verifier,
            "redirect_uri": redirect_uri,
        }
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                respuesta = await client.post(self.token_url, data=formulario)
        except httpx.HTTPError as error:
            raise RappiOAuthError(f"No se pudo contactar a Rappi: {error}") from error

        if respuesta.status_code != 200:
            # No se registra el cuerpo completo: puede incluir datos del intento.
            logger.warning(
                "Rappi rechazó el canje del código (%s)", respuesta.status_code
            )
            raise RappiOAuthError(
                f"Rappi rechazó el canje del código ({respuesta.status_code})."
            )

        datos = respuesta.json()
        id_token = datos.get("id_token")
        if not id_token:
            raise RappiOAuthError(
                "Rappi no devolvió id_token (el access_token no sirve para la API)."
            )
        return id_token, int(datos.get("expires_in") or VIGENCIA_POR_DEFECTO)
