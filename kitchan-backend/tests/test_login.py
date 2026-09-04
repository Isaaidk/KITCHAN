import pytest


@pytest.mark.asyncio
async def test_login_exitoso(client):
    # 1. Registramos un restaurante para tener un usuario admin válido en la BD
    payload_onboarding = {
        "restaurante": {
            "nombre_comercial": "Kitchan Login",
            "razon_social": "Login S.A.",
            "identificacion_fiscal": "1755555555001",
            "direccion": "Av Central",
            "telefono": "0955555555",
            "email_corporativo": "login@kitchan.com",
        },
        "admin": {
            "nombre": "Admin Login",
            "email": "admin.login@kitchan.com",
            "password": "PasswordSeguro123*",
        },
    }
    await client.post("/api/v1/onboarding/", json=payload_onboarding)

    # 2. Intentamos hacer login con las credenciales correctas
    payload_login = {
        "email": "admin.login@kitchan.com",
        "password": "PasswordSeguro123*",
    }
    response = await client.post("/api/v1/usuarios/login", json=payload_login)

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["usuario"]["email"] == "admin.login@kitchan.com"
    assert data["usuario"]["rol"] == "ADMIN"


@pytest.mark.asyncio
async def test_login_password_incorrecta(client):
    payload_onboarding = {
        "restaurante": {
            "nombre_comercial": "Kitchan Pass",
            "razon_social": "Pass S.A.",
            "identificacion_fiscal": "1766666666001",
            "direccion": "Av Sur",
            "telefono": "0944444444",
            "email_corporativo": "pass@kitchan.com",
        },
        "admin": {
            "nombre": "Admin Pass",
            "email": "admin.pass@kitchan.com",
            "password": "PasswordCorrecta123*",
        },
    }
    await client.post("/api/v1/onboarding/", json=payload_onboarding)

    # Login con contraseña errónea
    payload_login = {"email": "admin.pass@kitchan.com", "password": "PasswordFalsaXYZ"}
    response = await client.post("/api/v1/usuarios/login", json=payload_login)

    # Por seguridad, el sistema debe retornar 401 Unauthorized y un mensaje genérico ("Credenciales inválidas")
    assert response.status_code == 401
    assert "credenciales" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_email_no_registrado(client):
    payload_login = {
        "email": "noexisto@kitchan.com",
        "password": "CualquierPassword123*",
    }
    response = await client.post("/api/v1/usuarios/login", json=payload_login)

    # Debe retornar 401 para no filtrar qué correos existen en la base de datos
    assert response.status_code == 401
    assert "credenciales" in response.json()["detail"].lower()
