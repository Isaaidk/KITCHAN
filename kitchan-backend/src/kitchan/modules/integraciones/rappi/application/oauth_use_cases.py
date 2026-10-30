"""Casos de uso del OAuth de Rappi (Authorization Code + PKCE).

Rappi pide dos tokens en cada llamada de la API v2: el del integrador y el
del comercio. El del comercio se obtiene con este flujo, parecido al de Uber:

    iniciar() -> URL de Rappi -> el comercio autoriza -> completar(code, state)

PKCE (RFC 7636): se genera un `code_verifier` aleatorio, se envía a Rappi solo
su hash (`code_challenge`, SHA-256 en base64url) y el `code_verifier` se
entrega al canjear el código, así que no hace falta un client_secret.
"""

import base64
import hashlib
import secrets
from dataclasses import dataclass
from urllib.parse import urlencode

from src.kitchan.modules.integraciones.rappi.domain.exceptions import (
    RappiOAuthEstadoInvalidoError,
)
from src.kitchan.modules.integraciones.rappi.domain.ports import (
    RappiMerchantTokenCachePort,
    RappiOAuthPort,
    RappiOAuthStatePort,
)


def generar_code_verifier() -> str:
    """43 a 128 caracteres seguros para URL (aquí, 43)."""
    return secrets.token_urlsafe(32)


def calcular_code_challenge(code_verifier: str) -> str:
    """BASE64URL(SHA256(code_verifier)), sin relleno `=`."""
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


@dataclass(frozen=True)
class RappiOAuthConfig:
    client_id: str
    redirect_uri: str
    authorize_url: str
    scope: str = "openid profile email"


class RappiOAuthUseCase:
    def __init__(
        self,
        config: RappiOAuthConfig,
        state_store: RappiOAuthStatePort,
        oauth_client: RappiOAuthPort,
        token_cache: RappiMerchantTokenCachePort,
    ):
        self.config = config
        self.state_store = state_store
        self.oauth_client = oauth_client
        self.token_cache = token_cache

    async def iniciar(self) -> str:
        """URL de autorización de Rappi a la que se envía al comercio."""
        code_verifier = generar_code_verifier()
        state = secrets.token_urlsafe(32)
        await self.state_store.save_state(state, code_verifier, expires_in=600)

        parametros = {
            "client_id": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "response_type": "code",
            "scope": self.config.scope,
            "code_challenge": calcular_code_challenge(code_verifier),
            "code_challenge_method": "S256",
            "state": state,
        }
        return f"{self.config.authorize_url}?{urlencode(parametros)}"

    async def completar(self, code: str, state: str) -> None:
        """Valida el `state`, canjea el código y guarda el token del comercio."""
        code_verifier = await self.state_store.pop_code_verifier(state)
        if code_verifier is None:
            raise RappiOAuthEstadoInvalidoError(
                "El state no existe, expiró o ya se usó."
            )

        id_token, expires_in = await self.oauth_client.exchange_code(
            code, code_verifier, self.config.redirect_uri
        )
        await self.token_cache.save_merchant_token(id_token, expires_in)
