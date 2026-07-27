# Tests de integración de la protección de rutas por rol: confirman que los
# endpoints de administración devuelven 401 sin token y 403 con un token de
# rol no autorizado, y que un token de ADMIN sí puede operar con normalidad.
import pytest


async def registrar_restaurante_helper(client):
    payload = {
        "restaurante": {
            "nombre_comercial": "Restaurante Proteccion",
            "razon_social": "Proteccion S.A.",
            "identificacion_fiscal": "1799999999001",
            "direccion": "Av Proteccion",
            "telefono": "0977777777",
            "email_corporativo": "proteccion@restaurante.com",
        },
        "admin": {
            "nombre": "Admin Proteccion",
            "email": "admin.proteccion@restaurante.com",
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


async def crear_operador_helper(client, restaurante_id, headers_admin):
    payload = {
        "nombre": "Operador Proteccion",
        "email": "operador.proteccion@restaurante.com",
        "password": "PasswordOperador123*",
        "rol": "OPERADOR",
    }
    await client.post(
        f"/api/v1/usuarios/restaurante/{restaurante_id}",
        json=payload,
        headers=headers_admin,
    )
    return await login_helper(
        client, "operador.proteccion@restaurante.com", "PasswordOperador123*"
    )


@pytest.mark.asyncio
async def test_sin_token_no_accede_a_endpoint_admin(client):
    restaurante_id, _ = await registrar_restaurante_helper(client)

    response = await client.get(f"/api/v1/usuarios/restaurante/{restaurante_id}")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_token_invalido_no_accede_a_endpoint_admin(client):
    restaurante_id, _ = await registrar_restaurante_helper(client)

    response = await client.get(
        f"/api/v1/usuarios/restaurante/{restaurante_id}",
        headers={"Authorization": "Bearer token-falso-no-valido"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_operador_no_puede_crear_usuarios(client):
    restaurante_id, admin_email = await registrar_restaurante_helper(client)
    headers_admin = await login_helper(client, admin_email)
    headers_operador = await crear_operador_helper(
        client, restaurante_id, headers_admin
    )

    payload_usuario = {
        "nombre": "Otro Usuario",
        "email": "otro.usuario@restaurante.com",
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
async def test_operador_no_puede_eliminar_usuarios(client):
    restaurante_id, admin_email = await registrar_restaurante_helper(client)
    headers_admin = await login_helper(client, admin_email)
    headers_operador = await crear_operador_helper(
        client, restaurante_id, headers_admin
    )

    response = await client.delete(
        "/api/v1/usuarios/00000000-0000-0000-0000-000000000000",
        headers=headers_operador,
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_operador_no_puede_listar_usuarios_por_restaurante(client):
    restaurante_id, admin_email = await registrar_restaurante_helper(client)
    headers_admin = await login_helper(client, admin_email)
    headers_operador = await crear_operador_helper(
        client, restaurante_id, headers_admin
    )

    response = await client.get(
        f"/api/v1/usuarios/restaurante/{restaurante_id}",
        headers=headers_operador,
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_operador_no_puede_listar_todos_los_usuarios(client):
    restaurante_id, admin_email = await registrar_restaurante_helper(client)
    headers_admin = await login_helper(client, admin_email)
    headers_operador = await crear_operador_helper(
        client, restaurante_id, headers_admin
    )

    response = await client.get("/api/v1/usuarios/", headers=headers_operador)

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_si_puede_listar_usuarios_de_su_restaurante(client):
    restaurante_id, admin_email = await registrar_restaurante_helper(client)
    headers_admin = await login_helper(client, admin_email)

    response = await client.get(
        f"/api/v1/usuarios/restaurante/{restaurante_id}",
        headers=headers_admin,
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_usuario_puede_editar_su_propia_contrasena(client):
    restaurante_id, admin_email = await registrar_restaurante_helper(client)
    headers_admin = await login_helper(client, admin_email)
    headers_operador = await crear_operador_helper(
        client, restaurante_id, headers_admin
    )

    response = await client.patch(
        "/api/v1/usuarios/operador.proteccion@restaurante.com",
        json={"password_hash": "NuevaPasswordSegura123*"},
        headers=headers_operador,
    )

    assert response.status_code == 204


@pytest.mark.asyncio
async def test_usuario_no_puede_editar_contrasena_de_otro(client):
    restaurante_id, admin_email = await registrar_restaurante_helper(client)
    headers_admin = await login_helper(client, admin_email)
    headers_operador = await crear_operador_helper(
        client, restaurante_id, headers_admin
    )

    # El operador intenta cambiar la contraseña del admin
    response = await client.patch(
        f"/api/v1/usuarios/{admin_email}",
        json={"password_hash": "PasswordHackeada123*"},
        headers=headers_operador,
    )

    assert response.status_code == 403
