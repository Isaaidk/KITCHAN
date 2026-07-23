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
    return res.json()["restaurante"]["id"]


@pytest.mark.asyncio
async def test_crear_operador_por_admin_exitoso(client):
    restaurante_id = await registrar_restaurante_helper(client)

    payload_usuario = {
        "nombre": "Mesero Juan",
        "email": "juan.mesero@restaurante.com",
        "password": "PasswordOperador123*",
        "rol": "OPERADOR",
        "admin_rol_ejecutor": "ADMIN",  # El admin ejecuta la acción con éxito
    }

    response = await client.post(
        f"/api/v1/usuarios/restaurante/{restaurante_id}", json=payload_usuario
    )
    assert response.status_code == 201
    data = response.json()
    assert data["nombre"] == "Mesero Juan"
    assert data["rol"] == "OPERADOR"
    assert data["restaurante_id"] == restaurante_id


@pytest.mark.asyncio
async def test_bloquear_creacion_usuario_si_es_operador(client):
    restaurante_id = await registrar_restaurante_helper(client)

    payload_usuario = {
        "nombre": "Intruso",
        "email": "intruso@restaurante.com",
        "password": "Password123*",
        "rol": "OPERADOR",
        "admin_rol_ejecutor": "OPERADOR",  # Un operador intenta crear usuario -> Debe fallar
    }

    response = await client.post(
        f"/api/v1/usuarios/restaurante/{restaurante_id}", json=payload_usuario
    )
    assert response.status_code == 400
    assert "operadores no tienen permisos" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_crear_usuario_email_duplicado(client):
    restaurante_id = await registrar_restaurante_helper(client)

    payload_usuario = {
        "nombre": "Mesero Juan",
        "email": "juan.mesero@restaurante.com",
        "password": "PasswordOperador123*",
        "rol": "OPERADOR",
        "admin_rol_ejecutor": "ADMIN",
    }

    # Primer registro exitoso
    await client.post(
        f"/api/v1/usuarios/restaurante/{restaurante_id}", json=payload_usuario
    )

    # Intentar registrar otro usuario con el mismo email exacto
    response = await client.post(
        f"/api/v1/usuarios/restaurante/{restaurante_id}", json=payload_usuario
    )
    assert response.status_code == 400
    assert "registrado" in response.json()["detail"].lower()
