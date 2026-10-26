"""Recuperación de contraseña por código de verificación enviado al correo."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import update

from src.kitchan.modules.usuarios.application.ports import IEnviadorCorreo
from src.kitchan.modules.usuarios.infrastructure import rest_api
from src.kitchan.modules.usuarios.infrastructure.models import CodigoRecuperacionModel

EMAIL = "cocina@vangalia.com"
PASSWORD = "ClaveActual123*"


class CorreoFalso(IEnviadorCorreo):
    def __init__(self):
        self.enviados = []

    async def enviar_codigo_recuperacion(
        self, destinatario, nombre, codigo, minutos_validez
    ):
        self.enviados.append({"para": destinatario, "codigo": codigo})


@pytest.fixture
def correo(monkeypatch):
    falso = CorreoFalso()
    monkeypatch.setattr(rest_api, "construir_enviador_correo", lambda: falso)
    return falso


async def _crear_cuenta(client, email=EMAIL):
    payload = {
        "restaurante": {
            "nombre_comercial": "Vangalia",
            "razon_social": "Vangalia S.A.",
            "identificacion_fiscal": "1790000000001",
            "direccion": "Av Principal",
            "telefono": "0999999999",
            "email_corporativo": "info@vangalia.com",
        },
        "admin": {"nombre": "Cocina", "email": email, "password": PASSWORD},
    }
    res = await client.post("/api/v1/onboarding/", json=payload)
    assert res.status_code == 201


async def _login(client, password):
    return await client.post(
        "/api/v1/usuarios/login", json={"email": EMAIL, "password": password}
    )


async def _solicitar(client):
    return await client.post(
        "/api/v1/usuarios/recuperar/solicitar", json={"email": EMAIL}
    )


async def _verificar(client, codigo):
    return await client.post(
        "/api/v1/usuarios/recuperar/verificar", json={"email": EMAIL, "codigo": codigo}
    )


async def _restablecer(client, token, password="NuevaClave456*"):
    return await client.post(
        "/api/v1/usuarios/recuperar/restablecer",
        json={"token_restablecimiento": token, "nueva_password": password},
    )


@pytest.mark.asyncio
async def test_flujo_completo_cambia_la_contrasena(client, correo):
    await _crear_cuenta(client)

    res = await _solicitar(client)
    assert res.status_code == 200
    assert len(correo.enviados) == 1
    assert correo.enviados[0]["para"] == EMAIL
    codigo = correo.enviados[0]["codigo"]
    assert len(codigo) == 6 and codigo.isdigit()

    res = await _verificar(client, codigo)
    assert res.status_code == 200
    token = res.json()["token_restablecimiento"]

    assert (await _restablecer(client, token)).status_code == 204

    assert (await _login(client, "NuevaClave456*")).status_code == 200
    assert (await _login(client, PASSWORD)).status_code == 401


@pytest.mark.asyncio
async def test_un_correo_inexistente_responde_igual_y_no_envia_nada(client, correo):
    await _crear_cuenta(client)

    res = await client.post(
        "/api/v1/usuarios/recuperar/solicitar", json={"email": "nadie@vangalia.com"}
    )

    assert res.status_code == 200
    assert res.json() == (await _solicitar(client)).json()
    # Solo salió el correo de la cuenta que sí existe.
    assert [c["para"] for c in correo.enviados] == [EMAIL]


@pytest.mark.asyncio
async def test_un_codigo_incorrecto_se_rechaza(client, correo):
    await _crear_cuenta(client)
    await _solicitar(client)
    incorrecto = "000000" if correo.enviados[0]["codigo"] != "000000" else "111111"

    res = await _verificar(client, incorrecto)

    assert res.status_code == 400


@pytest.mark.asyncio
async def test_tras_cinco_intentos_fallidos_ni_el_codigo_correcto_sirve(client, correo):
    await _crear_cuenta(client)
    await _solicitar(client)
    codigo = correo.enviados[0]["codigo"]
    incorrecto = "000000" if codigo != "000000" else "111111"

    for _ in range(5):
        assert (await _verificar(client, incorrecto)).status_code == 400

    assert (await _verificar(client, codigo)).status_code == 400


@pytest.mark.asyncio
async def test_un_codigo_vencido_no_sirve(client, correo, db_session):
    await _crear_cuenta(client)
    await _solicitar(client)
    await db_session.execute(
        update(CodigoRecuperacionModel).values(
            expira_en=datetime.now(timezone.utc) - timedelta(minutes=1)
        )
    )
    await db_session.commit()

    res = await _verificar(client, correo.enviados[0]["codigo"])

    assert res.status_code == 400


@pytest.mark.asyncio
async def test_el_token_de_restablecimiento_solo_se_usa_una_vez(client, correo):
    await _crear_cuenta(client)
    await _solicitar(client)
    token = (await _verificar(client, correo.enviados[0]["codigo"])).json()[
        "token_restablecimiento"
    ]

    assert (await _restablecer(client, token)).status_code == 204
    assert (await _restablecer(client, token, "OtraClave789*")).status_code == 400
    assert (await _login(client, "NuevaClave456*")).status_code == 200


@pytest.mark.asyncio
async def test_una_solicitud_nueva_invalida_el_codigo_anterior(
    client, correo, db_session
):
    await _crear_cuenta(client)
    await _solicitar(client)
    primero = correo.enviados[0]["codigo"]
    # Se adelanta la hora de creación para saltar la espera entre solicitudes.
    await db_session.execute(
        update(CodigoRecuperacionModel).values(
            creado_en=datetime.now(timezone.utc) - timedelta(minutes=5)
        )
    )
    await db_session.commit()

    await _solicitar(client)
    segundo = correo.enviados[1]["codigo"]

    if primero != segundo:
        assert (await _verificar(client, primero)).status_code == 400
    assert (await _verificar(client, segundo)).status_code == 200


@pytest.mark.asyncio
async def test_pedir_el_codigo_varias_veces_seguidas_envia_un_solo_correo(
    client, correo
):
    await _crear_cuenta(client)

    for _ in range(3):
        assert (await _solicitar(client)).status_code == 200

    assert len(correo.enviados) == 1


@pytest.mark.asyncio
async def test_la_contrasena_nueva_debe_tener_al_menos_ocho_caracteres(client, correo):
    await _crear_cuenta(client)
    await _solicitar(client)
    token = (await _verificar(client, correo.enviados[0]["codigo"])).json()[
        "token_restablecimiento"
    ]

    res = await _restablecer(client, token, "corta")

    assert res.status_code == 422


@pytest.mark.asyncio
async def test_los_tokens_de_sesion_y_de_restablecimiento_no_son_intercambiables(
    client, correo
):
    await _crear_cuenta(client)
    sesion = (await _login(client, PASSWORD)).json()["access_token"]
    await _solicitar(client)
    restablecimiento = (await _verificar(client, correo.enviados[0]["codigo"])).json()[
        "token_restablecimiento"
    ]

    # Un token de sesión no restablece contraseñas...
    assert (await _restablecer(client, sesion, "OtraClave789*")).status_code == 400
    # ...y uno de restablecimiento no abre una sesión.
    res = await client.get(
        "/api/v1/usuarios/", headers={"Authorization": f"Bearer {restablecimiento}"}
    )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_un_usuario_desactivado_no_recibe_codigo(client, correo, db_session):
    await _crear_cuenta(client)
    token = (await _login(client, PASSWORD)).json()
    usuario_id = token["usuario"]["id"]
    res = await client.patch(
        f"/api/v1/usuarios/{usuario_id}/estado",
        json={"estado": False},
        headers={"Authorization": f"Bearer {token['access_token']}"},
    )
    assert res.status_code == 200

    await _solicitar(client)

    assert correo.enviados == []
