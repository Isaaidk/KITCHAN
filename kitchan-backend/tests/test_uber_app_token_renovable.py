"""Tests del App Token de Uber que se renueva solo cuando falta en Redis.
Redis y Uber se reemplazan por dobles: ningún test sale a la red.
"""

import asyncio

import httpx
import pytest

from src.kitchan.modules.integraciones.uber.infrastructure.adapters import (
    uber_app_token_renovable as modulo,
)
from src.kitchan.modules.integraciones.uber.infrastructure.adapters.redis_token_adapter import (
    RedisUberTokenAdapter,
)
from src.kitchan.modules.integraciones.uber.infrastructure.adapters.uber_app_token_renovable import (
    RedisUberTokenAdapterRenovable,
    solicitar_app_token,
)

RESTAURANTE = "11111111-1111-1111-1111-111111111111"


@pytest.fixture
def almacen(monkeypatch):
    """Sustituye la lectura y escritura en Redis por un diccionario."""
    datos: dict[str, str] = {}

    async def get_app_token(self, restaurante_id):
        return datos.get(restaurante_id)

    async def save_app_token(self, restaurante_id, token, expires_in):
        datos[restaurante_id] = token

    monkeypatch.setattr(RedisUberTokenAdapter, "get_app_token", get_app_token)
    monkeypatch.setattr(RedisUberTokenAdapter, "save_app_token", save_app_token)
    return datos


class SolicitudFalsa:
    def __init__(self, resultado=("token-nuevo", 2592000), error=None, demora=0):
        self.llamadas = 0
        self.resultado = resultado
        self.error = error
        self.demora = demora

    async def __call__(self):
        self.llamadas += 1
        if self.demora:
            await asyncio.sleep(self.demora)
        if self.error:
            raise self.error
        return self.resultado


def _adaptador(solicitud) -> RedisUberTokenAdapterRenovable:
    return RedisUberTokenAdapterRenovable(
        redis_url="redis://localhost:6390/0", solicitar_token=solicitud
    )


@pytest.mark.asyncio
async def test_si_el_token_existe_no_se_pide_a_uber(almacen):
    almacen[RESTAURANTE] = "token-guardado"
    solicitud = SolicitudFalsa()

    token = await _adaptador(solicitud).get_app_token(RESTAURANTE)

    assert token == "token-guardado"
    assert solicitud.llamadas == 0


@pytest.mark.asyncio
async def test_si_falta_el_token_se_pide_y_se_guarda(almacen):
    solicitud = SolicitudFalsa(resultado=("token-nuevo", 2592000))
    adaptador = _adaptador(solicitud)

    token = await adaptador.get_app_token(RESTAURANTE)

    assert token == "token-nuevo"
    assert almacen[RESTAURANTE] == "token-nuevo"
    # La siguiente lectura ya lo encuentra guardado.
    assert await adaptador.get_app_token(RESTAURANTE) == "token-nuevo"
    assert solicitud.llamadas == 1


@pytest.mark.asyncio
async def test_si_uber_falla_devuelve_none_sin_romper(almacen):
    solicitud = SolicitudFalsa(error=RuntimeError("Uber rechazó la solicitud"))

    token = await _adaptador(solicitud).get_app_token(RESTAURANTE)

    assert token is None
    assert RESTAURANTE not in almacen


@pytest.mark.asyncio
async def test_webhooks_simultaneos_piden_el_token_una_sola_vez(almacen):
    solicitud = SolicitudFalsa(demora=0.05)
    adaptador = _adaptador(solicitud)

    tokens = await asyncio.gather(
        *(adaptador.get_app_token(RESTAURANTE) for _ in range(5))
    )

    assert tokens == ["token-nuevo"] * 5
    assert solicitud.llamadas == 1


# --------------------------------------------------------------------------
# Solicitud real a Uber (con httpx reemplazado)
# --------------------------------------------------------------------------


@pytest.fixture
def credenciales(monkeypatch):
    monkeypatch.setenv("UBER_CLIENT_ID", ' "id-de-prueba" ')
    monkeypatch.setenv("UBER_CLIENT_SECRET", "secreto-de-prueba")


def _responder(monkeypatch, respuesta: httpx.Response, capturado: dict):
    async def post(self, url, **kwargs):
        capturado["url"] = url
        capturado["data"] = kwargs.get("data")
        return respuesta

    monkeypatch.setattr(httpx.AsyncClient, "post", post)


@pytest.mark.asyncio
async def test_solicitar_token_usa_client_credentials(monkeypatch, credenciales):
    capturado: dict = {}
    _responder(
        monkeypatch,
        httpx.Response(200, json={"access_token": "abc", "expires_in": 2592000}),
        capturado,
    )

    token, expira = await solicitar_app_token()

    assert (token, expira) == ("abc", 2592000)
    assert capturado["url"] == modulo.UBER_TOKEN_URL
    assert capturado["data"]["grant_type"] == "client_credentials"
    assert capturado["data"]["scope"] == "eats.store eats.order"
    # Las comillas y espacios del .env se limpian.
    assert capturado["data"]["client_id"] == "id-de-prueba"


@pytest.mark.asyncio
async def test_solicitar_token_falla_si_uber_rechaza(monkeypatch, credenciales):
    _responder(monkeypatch, httpx.Response(401, json={}), {})

    with pytest.raises(RuntimeError, match="rechazó"):
        await solicitar_app_token()


@pytest.mark.asyncio
async def test_solicitar_token_falla_sin_access_token(monkeypatch, credenciales):
    _responder(monkeypatch, httpx.Response(200, json={}), {})

    with pytest.raises(RuntimeError, match="access_token"):
        await solicitar_app_token()


@pytest.mark.asyncio
async def test_solicitar_token_falla_sin_credenciales(monkeypatch):
    monkeypatch.delenv("UBER_CLIENT_ID", raising=False)
    monkeypatch.delenv("UBER_CLIENT_SECRET", raising=False)

    with pytest.raises(RuntimeError, match="UBER_CLIENT_ID"):
        await solicitar_app_token()
