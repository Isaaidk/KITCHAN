"""Tests del health check de Rappi (PING, STORE_CONNECTIVITY, ORDER_OTHER_EVENT)
y de la elección del login: con audiencia se usa el Auth0 del sandbox y sin
ella el login clásico (el del simulador local). Ninguno sale a la red.
"""

import hashlib
import hmac
import json

import httpx
import pytest

from src.kitchan.modules.integraciones.rappi.infrastructure.adapters import (
    http_order_adapter as modulo,
)
from src.kitchan.modules.integraciones.rappi.infrastructure.adapters.http_order_adapter import (
    AUTH0_DEV_URL,
    RappiHttpAdapter,
)

SECRETO = "secreto-webhook-de-test"
BASE = "/api/v1/integraciones/rappi/webhook"


@pytest.fixture(autouse=True)
def _secreto(monkeypatch):
    monkeypatch.setenv("RAPPI_WEBHOOK_SECRET", SECRETO)


def _firmado(cuerpo: dict) -> tuple[bytes, dict]:
    body = json.dumps(cuerpo).encode("utf-8")
    t = "1700000000"
    firma = hmac.new(
        SECRETO.encode(), t.encode() + b"." + body, hashlib.sha256
    ).hexdigest()
    return body, {
        "Content-Type": "application/json",
        "Rappi-Signature": f"t={t},sign={firma}",
    }


# --------------------------------------------------------------------------
# Health check y eventos informativos
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ping_responde_ok(client):
    respuesta = await client.post(f"{BASE}/ping", json={"store_id": 900175767})

    assert respuesta.status_code == 200
    assert respuesta.json() == {"status": "OK"}


@pytest.mark.asyncio
async def test_ping_sin_cuerpo_tambien_responde_ok(client):
    respuesta = await client.post(f"{BASE}/ping")

    assert respuesta.status_code == 200
    assert respuesta.json() == {"status": "OK"}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "ruta,cuerpo",
    [
        (
            "store-connectivity",
            {"external_store_id": "900175767", "enabled": False, "message": "x"},
        ),
        ("other-event", {"order_id": "123", "event": "arrive"}),
    ],
)
async def test_eventos_informativos_firmados_se_reconocen(client, ruta, cuerpo):
    body, headers = _firmado(cuerpo)

    respuesta = await client.post(f"{BASE}/{ruta}", content=body, headers=headers)

    assert respuesta.status_code == 200
    assert respuesta.json() == {"status": "success"}


@pytest.mark.asyncio
@pytest.mark.parametrize("ruta", ["store-connectivity", "other-event"])
async def test_eventos_informativos_con_firma_falsa_se_rechazan(client, ruta):
    respuesta = await client.post(
        f"{BASE}/{ruta}",
        content=b"{}",
        headers={
            "Content-Type": "application/json",
            "Rappi-Signature": "t=1,sign=falsa",
        },
    )

    assert respuesta.status_code == 403


# --------------------------------------------------------------------------
# Elección del login
# --------------------------------------------------------------------------


class TokenCacheFalso:
    async def get_app_token(self):
        return None

    async def save_app_token(self, token, expires_in):
        self.guardado = (token, expires_in)


def _adaptador(monkeypatch, **entorno) -> RappiHttpAdapter:
    for clave in ("RAPPI_AUDIENCE", "RAPPI_AUTH_URL"):
        monkeypatch.delenv(clave, raising=False)
    for clave, valor in entorno.items():
        monkeypatch.setenv(clave, valor)
    monkeypatch.setenv("RAPPI_CLIENT_ID", "id-de-prueba")
    monkeypatch.setenv("RAPPI_CLIENT_SECRET", "secreto-de-prueba")
    monkeypatch.setenv("RAPPI_AUTH_BASE", "http://127.0.0.1:8010")
    return RappiHttpAdapter(token_cache=TokenCacheFalso())


def test_con_audience_el_login_es_auth0(monkeypatch):
    adaptador = _adaptador(monkeypatch, RAPPI_AUDIENCE="https://int-public-api-v2/api")

    assert adaptador._url_login() == AUTH0_DEV_URL


def test_sin_audience_el_login_es_el_clasico(monkeypatch):
    adaptador = _adaptador(monkeypatch)

    assert adaptador._url_login() == ("http://127.0.0.1:8010" + modulo.TOKEN_PATH)


def test_rappi_auth_url_manda_sobre_lo_demas(monkeypatch):
    adaptador = _adaptador(
        monkeypatch,
        RAPPI_AUDIENCE="https://int-public-api-v2/api",
        RAPPI_AUTH_URL="https://login.ejemplo.test/oauth/token",
    )

    assert adaptador._url_login() == "https://login.ejemplo.test/oauth/token"


@pytest.mark.asyncio
async def test_el_login_envia_la_audience_y_guarda_el_token(monkeypatch):
    capturado: dict = {}

    async def post(self, url, **kwargs):
        capturado["url"] = url
        capturado["json"] = kwargs.get("json")
        return httpx.Response(
            200, json={"access_token": "token-sandbox", "expires_in": 604800}
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", post)
    adaptador = _adaptador(monkeypatch, RAPPI_AUDIENCE="https://int-public-api-v2/api")

    token = await adaptador._obtener_token()

    assert token == "token-sandbox"
    assert capturado["url"] == AUTH0_DEV_URL
    assert capturado["json"]["audience"] == "https://int-public-api-v2/api"
    assert capturado["json"]["grant_type"] == "client_credentials"
    assert adaptador.token_cache.guardado == ("token-sandbox", 604800)
