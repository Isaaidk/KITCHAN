import pytest


async def registrar_restaurante_helper(client):
    payload = {
        "restaurante": {
            "nombre_comercial": "Restaurante Test",
            "razon_social": "Test S.A.",
            "identificacion_fiscal": "1744444444001",
            "direccion": "Av Test",
            "telefono": "0966666666",
            "email_corporativo": "test@restaurante.com",
        },
        "admin": {
            "nombre": "Super Admin",
            "email": "superadmin@restaurante.com",
            "password": "Password123*",
        },
    }
    res = await client.post("/api/v1/onboarding/", json=payload)
    return res.json()["restaurante"]["id"], payload["admin"]["email"]


async def login_helper(client, email, password="Password123*"):
    res = await client.post(
        "/api/v1/usuarios/login", json={"email": email, "password": password}
    )
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_crear_operador_por_admin_exitoso(client):
    restaurante_id, admin_email = await registrar_restaurante_helper(client)
    headers_admin = await login_helper(client, admin_email)

    payload_usuario = {
        "nombre": "Mesero Juan",
        "email": "juan.mesero@restaurante.com",
        "password": "PasswordOperador123*",
        "rol": "OPERADOR",
    }

    response = await client.post(
        f"/api/v1/usuarios/restaurante/{restaurante_id}",
        json=payload_usuario,
        headers=headers_admin,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["nombre"] == "Mesero Juan"
    assert data["rol"] == "OPERADOR"
    assert data["restaurante_id"] == restaurante_id


@pytest.mark.asyncio
async def test_bloquear_creacion_usuario_si_es_operador(client):
    restaurante_id, admin_email = await registrar_restaurante_helper(client)
    headers_admin = await login_helper(client, admin_email)

    # Un admin crea primero un operador legítimo
    payload_operador = {
        "nombre": "Operador Legitimo",
        "email": "operador.legitimo@restaurante.com",
        "password": "PasswordOperador123*",
        "rol": "OPERADOR",
    }
    await client.post(
        f"/api/v1/usuarios/restaurante/{restaurante_id}",
        json=payload_operador,
        headers=headers_admin,
    )
    headers_operador = await login_helper(
        client, "operador.legitimo@restaurante.com", "PasswordOperador123*"
    )

    # El operador intenta crear un usuario -> Debe ser rechazado por rol
    payload_usuario = {
        "nombre": "Intruso",
        "email": "intruso@restaurante.com",
        "password": "Password123*",
        "rol": "OPERADOR",
    }

    response = await client.post(
        f"/api/v1/usuarios/restaurante/{restaurante_id}",
        json=payload_usuario,
        headers=headers_operador,
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_crear_usuario_email_duplicado(client):
    restaurante_id, admin_email = await registrar_restaurante_helper(client)
    headers_admin = await login_helper(client, admin_email)

    payload_usuario = {
        "nombre": "Mesero Juan",
        "email": "juan.mesero.dup@restaurante.com",
        "password": "PasswordOperador123*",
        "rol": "OPERADOR",
    }

    # Primer registro exitoso
    await client.post(
        f"/api/v1/usuarios/restaurante/{restaurante_id}",
        json=payload_usuario,
        headers=headers_admin,
    )

    # Intentar registrar otro usuario con el mismo email exacto
    response = await client.post(
        f"/api/v1/usuarios/restaurante/{restaurante_id}",
        json=payload_usuario,
        headers=headers_admin,
    )
    assert response.status_code == 400
    assert "registrado" in response.json()["detail"].lower()
