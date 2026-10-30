"""Infraestructura de Rappi: rutas del OAuth que conecta a KITCHAN con la cuenta
de Rappi del comercio (Authorization Code + PKCE).

- POST /api/v1/integraciones/rappi/auth/login     -> URL de autorización
  (solo ADMIN: la llama el frontend con sesión y luego redirige al navegador).
- GET  /api/v1/integraciones/rappi/auth/callback  -> retorno de Rappi (pública:
  la abre el navegador sin sesión; se protege con el `state` de un solo uso).
- GET  /api/v1/integraciones/rappi/auth/status    -> si hay token del comercio.

La `redirect_uri` debe registrarse tal cual en el módulo Self Onboarding del
Integrations Portal de Rappi (https, sin comodines, igual carácter por carácter).
"""

import logging
import os
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse

from src.kitchan.modules.integraciones.rappi.application.oauth_use_cases import (
    RappiOAuthConfig,
    RappiOAuthUseCase,
)
from src.kitchan.modules.integraciones.rappi.domain.exceptions import (
    RappiOAuthError,
    RappiOAuthEstadoInvalidoError,
)
from src.kitchan.modules.integraciones.rappi.infrastructure.adapters.http_oauth_adapter import (
    AUTHORIZE_URL_DEV,
    RappiOAuthHttpAdapter,
)
from src.kitchan.modules.integraciones.rappi.infrastructure.adapters.redis_token_adapter import (
    RedisRappiTokenAdapter,
)
from src.kitchan.modules.usuarios.domain.entities import RolUsuario
from src.kitchan.modules.usuarios.infrastructure.auth_dependencies import requiere_rol

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/integraciones/rappi/auth",
    tags=["Integraciones - Rappi OAuth"],
)


def _redis_url() -> str:
    return os.getenv("REDIS_URL", "redis://localhost:6379/0")


def get_oauth_use_case() -> RappiOAuthUseCase:
    client_id = (os.getenv("RAPPI_OAUTH_CLIENT_ID") or "").strip()
    redirect_uri = (os.getenv("RAPPI_OAUTH_REDIRECT_URI") or "").strip()
    if not client_id or not redirect_uri:
        raise HTTPException(
            status_code=500,
            detail="Faltan RAPPI_OAUTH_CLIENT_ID o RAPPI_OAUTH_REDIRECT_URI.",
        )
    redis_rappi = RedisRappiTokenAdapter(_redis_url())
    return RappiOAuthUseCase(
        config=RappiOAuthConfig(
            client_id=client_id,
            redirect_uri=redirect_uri,
            authorize_url=os.getenv("RAPPI_OAUTH_AUTHORIZE_URL", AUTHORIZE_URL_DEV),
        ),
        state_store=redis_rappi,
        oauth_client=RappiOAuthHttpAdapter(client_id=client_id),
        token_cache=redis_rappi,
    )


def _volver_al_frontend(resultado: str) -> RedirectResponse:
    frontend = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")
    return RedirectResponse(
        url=f"{frontend}/integraciones?{urlencode({'rappi': resultado})}",
        status_code=302,
    )


@router.post("/login")
async def rappi_login(
    _usuario: dict = Depends(requiere_rol(RolUsuario.ADMIN.value)),
    use_case: RappiOAuthUseCase = Depends(get_oauth_use_case),
):
    """Devuelve la URL de Rappi a la que hay que enviar al comercio."""
    return {"authorization_url": await use_case.iniciar()}


@router.get("/callback")
async def rappi_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    use_case: RappiOAuthUseCase = Depends(get_oauth_use_case),
):
    """Retorno de Rappi tras la autorización del comercio."""
    if error or not code or not state:
        logger.warning("Rappi devolvió un OAuth incompleto (error=%s)", error)
        return _volver_al_frontend("error")

    try:
        await use_case.completar(code, state)
    except RappiOAuthEstadoInvalidoError:
        return _volver_al_frontend("estado_invalido")
    except RappiOAuthError as exc:
        logger.warning("No se pudo completar el OAuth de Rappi: %s", exc)
        return _volver_al_frontend("error")
    return _volver_al_frontend("conectado")


@router.get("/status")
async def rappi_status(
    _usuario: dict = Depends(requiere_rol(RolUsuario.ADMIN.value)),
):
    """Indica si KITCHAN ya tiene el token del comercio de Rappi."""
    token = await RedisRappiTokenAdapter(_redis_url()).get_merchant_token()
    return {"conectado": token is not None}
