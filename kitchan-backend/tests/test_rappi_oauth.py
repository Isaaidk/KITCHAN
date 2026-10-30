"""Tests del OAuth de Rappi (Authorization Code + PKCE): generación del reto,
URL de autorización, canje del código, controlador y el doble encabezado de
las llamadas a la API v2. Rappi y Redis se reemplazan por dobles.
"""

import uuid
from typing import Optional
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from src.kitchan.main import app
from src.kitchan.modules.integraciones.rappi.application.oauth_use_cases import (
    RappiOAuthConfig,
    RappiOAuthUseCase,
    calcular_code_challenge,
    generar_code_verifier,
)
from src.kitchan.modules.integraciones.rappi.domain.exceptions import (
    RappiOAuthError,
    RappiOAuthEstadoInvalidoError,
)
from src.kitchan.modules.integraciones.rappi.domain.ports import (
    RappiMerchantTokenCachePort,
    RappiOAuthPort,
    RappiOAuthStatePort,
    RappiTokenCachePort,
)
from src.kitchan.modules.integraciones.rappi.infrastructure.adapters.http_oauth_adapter import (
    RappiOAuthHttpAdapter,
)
from src.kitchan.modules.integraciones.rappi.infrastructure.adapters.http_order_adapter import (
    RappiHttpAdapter,
)
from src.kitchan.modules.integraciones.rappi.infrastructure.controllers.oauth_api import (
    get_oauth_use_case,
)
from src.kitchan.modules.usuarios.infrastructure.security import JWTTokenGenerator

AUTORIZACION = "https://login.partners.dev.rappi.com/authorize"
REDIRECT = "https://ejemplo.test/api/v1/integraciones/rappi/auth/callback"


# --------------------------------------------------------------------------
# Dobles
# --------------------------------------------------------------------------


class EstadoEnMemoria(RappiOAuthStatePort):
    def __init__(self):
        self.estados: dict[str, str] = {}

    async def save_state(self, state, code_verifier, expires_in=600):
        self.estados[state] = code_verifier

    async def pop_code_verifier(self, state) -> Optional[str]:
        return self.estados.pop(state, None)


class TokenComercioEnMemoria(RappiMerchantTokenCachePort):
    def __init__(self):
        self.token: Optional[str] = None
        self.expires_in: Optional[int] = None

    async def save_merchant_token(self, token, expires_in):
        self.token, self.expires_in = token, expires_in

    async def get_merchant_token(self):
        return self.token


class ClienteOAuthFalso(RappiOAuthPort):
    def __init__(self, error: Optional[Exception] = None):
        self.error = error
        self.llamadas: list[tuple] = []

    async def exchange_code(self, code, code_verifier, redirect_uri):
        self.llamadas.append((code, code_verifier, redirect_uri))
        if self.error:
            raise self.error
        return "id-token-del-comercio", 7200


def _caso_de_uso(cliente=None):
    estado, tokens = EstadoEnMemoria(), TokenComercioEnMemoria()
    cliente = cliente or ClienteOAuthFalso()
    caso = RappiOAuthUseCase(
        config=RappiOAuthConfig(
            client_id="client-id-de-prueba",
            redirect_uri=REDIRECT,
            authorize_url=AUTORIZACION,
        ),
        state_store=estado,
        oauth_client=cliente,
        token_cache=tokens,
    )
    return caso, estado, tokens, cliente


# --------------------------------------------------------------------------
# PKCE
# --------------------------------------------------------------------------


def test_el_reto_pkce_coincide_con_el_vector_del_rfc_7636():
    verificador = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"

    assert calcular_code_challenge(verificador) == (
        "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"
    )


def test_el_code_verifier_es_largo_unico_y_seguro_para_url():
    uno, otro = generar_code_verifier(), generar_code_verifier()

    assert 43 <= len(uno) <= 128
    assert uno != otro
    assert set(uno) <= set(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
    )


# --------------------------------------------------------------------------
# Casos de uso
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_iniciar_arma_la_url_de_autorizacion_con_pkce():
    caso, estado, _, _ = _caso_de_uso()

    url = await caso.iniciar()

    partes = urlparse(url)
    consulta = {k: v[0] for k, v in parse_qs(partes.query).items()}
    assert f"{partes.scheme}://{partes.netloc}{partes.path}" == AUTORIZACION
    assert consulta["client_id"] == "client-id-de-prueba"
    assert consulta["redirect_uri"] == REDIRECT
    assert consulta["response_type"] == "code"
    assert consulta["scope"] == "openid profile email"
    assert consulta["code_challenge_method"] == "S256"
    # El state quedó guardado con el verifier cuyo hash viaja en la URL.
    verificador = estado.estados[consulta["state"]]
    assert consulta["code_challenge"] == calcular_code_challenge(verificador)


@pytest.mark.asyncio
async def test_completar_canjea_el_codigo_y_guarda_el_token_del_comercio():
    caso, estado, tokens, cliente = _caso_de_uso()
    url = await caso.iniciar()
    state = parse_qs(urlparse(url).query)["state"][0]
    verificador = estado.estados[state]

    await caso.completar("codigo-de-rappi", state)

    assert cliente.llamadas == [("codigo-de-rappi", verificador, REDIRECT)]
    assert (tokens.token, tokens.expires_in) == ("id-token-del-comercio", 7200)


@pytest.mark.asyncio
async def test_un_state_desconocido_se_rechaza_sin_canjear():
    caso, _, tokens, cliente = _caso_de_uso()

    with pytest.raises(RappiOAuthEstadoInvalidoError):
        await caso.completar("codigo", "state-que-no-existe")

    assert cliente.llamadas == []
    assert tokens.token is None


@pytest.mark.asyncio
async def test_el_state_solo_sirve_una_vez():
    caso, _, _, _ = _caso_de_uso()
    state = parse_qs(urlparse(await caso.iniciar()).query)["state"][0]
    await caso.completar("codigo", state)

    with pytest.raises(RappiOAuthEstadoInvalidoError):
        await caso.completar("codigo", state)


@pytest.mark.asyncio
async def test_si_rappi_rechaza_el_canje_no_se_guarda_ningun_token():
    caso, _, tokens, _ = _caso_de_uso(ClienteOAuthFalso(error=RappiOAuthError("no")))
    state = parse_qs(urlparse(await caso.iniciar()).query)["state"][0]

    with pytest.raises(RappiOAuthError):
        await caso.completar("codigo", state)

    assert tokens.token is None


# --------------------------------------------------------------------------
# Cliente HTTP del endpoint de tokens
# --------------------------------------------------------------------------


def _responder(monkeypatch, respuesta: httpx.Response, capturado: dict):
    async def post(self, url, **kwargs):
        capturado["url"] = url
        capturado["data"] = kwargs.get("data")
        return respuesta

    monkeypatch.setattr(httpx.AsyncClient, "post", post)


@pytest.mark.asyncio
async def test_el_canje_usa_el_id_token_y_no_el_access_token(monkeypatch):
    capturado: dict = {}
    _responder(
        monkeypatch,
        httpx.Response(
            200,
            json={
                "access_token": "jwe-opaco-que-no-sirve",
                "id_token": "a.b.c",
                "expires_in": 86400,
            },
        ),
        capturado,
    )

    token, vigencia = await RappiOAuthHttpAdapter(
        token_url="https://rappi.test/oauth/token", client_id="cid"
    ).exchange_code("codigo", "verificador", REDIRECT)

    assert (token, vigencia) == ("a.b.c", 86400)
    assert capturado["url"] == "https://rappi.test/oauth/token"
    assert capturado["data"] == {
        "grant_type": "authorization_code",
        "code": "codigo",
        "client_id": "cid",
        "code_verifier": "verificador",
        "redirect_uri": REDIRECT,
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "respuesta",
    [
        httpx.Response(400, json={"error": "invalid_grant"}),
        httpx.Response(200, json={"access_token": "solo-access"}),
    ],
)
async def test_un_canje_fallido_o_sin_id_token_lanza_error(monkeypatch, respuesta):
    _responder(monkeypatch, respuesta, {})

    with pytest.raises(RappiOAuthError):
        await RappiOAuthHttpAdapter(
            token_url="https://x.test", client_id="cid"
        ).exchange_code("c", "v", REDIRECT)


@pytest.mark.asyncio
async def test_sin_client_id_no_se_intenta_el_canje():
    with pytest.raises(RappiOAuthError, match="RAPPI_OAUTH_CLIENT_ID"):
        await RappiOAuthHttpAdapter(
            token_url="https://x.test", client_id=""
        ).exchange_code("c", "v", REDIRECT)


# --------------------------------------------------------------------------
# Controlador
# --------------------------------------------------------------------------


def _headers(rol: str) -> dict:
    token = JWTTokenGenerator().generar_token(
        {
            "sub": "u@test.com",
            "id": str(uuid.uuid4()),
            "rol": rol,
            "restaurante_id": str(uuid.uuid4()),
        }
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def caso_falso():
    caso, estado, tokens, cliente = _caso_de_uso()
    app.dependency_overrides[get_oauth_use_case] = lambda: caso
    yield caso, estado, tokens, cliente
    app.dependency_overrides.pop(get_oauth_use_case, None)


@pytest.mark.asyncio
async def test_login_exige_sesion(client, caso_falso):
    respuesta = await client.post("/api/v1/integraciones/rappi/auth/login")

    assert respuesta.status_code == 401


@pytest.mark.asyncio
async def test_login_solo_para_administradores(client, caso_falso):
    respuesta = await client.post(
        "/api/v1/integraciones/rappi/auth/login", headers=_headers("OPERADOR")
    )

    assert respuesta.status_code == 403


@pytest.mark.asyncio
async def test_login_devuelve_la_url_de_rappi(client, caso_falso):
    respuesta = await client.post(
        "/api/v1/integraciones/rappi/auth/login", headers=_headers("ADMIN")
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["authorization_url"].startswith(AUTORIZACION + "?")


@pytest.mark.asyncio
async def test_callback_exitoso_vuelve_al_frontend_conectado(client, caso_falso):
    caso, _, tokens, _ = caso_falso
    state = parse_qs(urlparse(await caso.iniciar()).query)["state"][0]

    respuesta = await client.get(
        "/api/v1/integraciones/rappi/auth/callback",
        params={"code": "abc", "state": state},
        follow_redirects=False,
    )

    assert respuesta.status_code == 302
    assert respuesta.headers["location"].endswith("/integraciones?rappi=conectado")
    assert tokens.token == "id-token-del-comercio"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "parametros,resultado",
    [
        ({"code": "abc", "state": "desconocido"}, "estado_invalido"),
        ({"error": "access_denied"}, "error"),
        ({"code": "abc"}, "error"),
    ],
)
async def test_callback_con_problemas_vuelve_con_el_error(
    client, caso_falso, parametros, resultado
):
    respuesta = await client.get(
        "/api/v1/integraciones/rappi/auth/callback",
        params=parametros,
        follow_redirects=False,
    )

    assert respuesta.status_code == 302
    assert respuesta.headers["location"].endswith(f"/integraciones?rappi={resultado}")


# --------------------------------------------------------------------------
# Doble encabezado en las llamadas a la API v2
# --------------------------------------------------------------------------


class CacheCompleto(RappiTokenCachePort, RappiMerchantTokenCachePort):
    def __init__(self, comercio: Optional[str]):
        self.comercio = comercio

    async def save_app_token(self, token, expires_in):
        pass

    async def get_app_token(self):
        return "token-del-integrador"

    async def save_merchant_token(self, token, expires_in):
        self.comercio = token

    async def get_merchant_token(self):
        return self.comercio


class CacheSoloIntegrador(RappiTokenCachePort):
    async def save_app_token(self, token, expires_in):
        pass

    async def get_app_token(self):
        return "token-del-integrador"


async def _headers_enviados(monkeypatch, cache) -> dict:
    capturado: dict = {}

    async def request(self, metodo, url, **kwargs):
        capturado["headers"] = kwargs.get("headers", {})
        return httpx.Response(200, json={})

    monkeypatch.setattr(httpx.AsyncClient, "request", request)
    await RappiHttpAdapter(token_cache=cache).mark_ready_for_pickup("123")
    return capturado["headers"]


@pytest.mark.asyncio
async def test_con_token_del_comercio_se_envian_los_dos_encabezados(monkeypatch):
    headers = await _headers_enviados(monkeypatch, CacheCompleto("id-token-comercio"))

    assert headers["x-authorization"] == "Bearer token-del-integrador"
    assert headers["Authorization-Partners"] == "Bearer id-token-comercio"


@pytest.mark.asyncio
@pytest.mark.parametrize("cache", [CacheCompleto(None), CacheSoloIntegrador()])
async def test_sin_token_del_comercio_solo_va_el_del_integrador(monkeypatch, cache):
    headers = await _headers_enviados(monkeypatch, cache)

    assert headers["x-authorization"] == "Bearer token-del-integrador"
    assert "Authorization-Partners" not in headers
