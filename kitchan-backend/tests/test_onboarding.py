import pytest


@pytest.mark.asyncio
async def test_registrar_restaurante_happy_path(client):
    payload = {
        "restaurante": {
            "nombre_comercial": "KITCHAN Centro",
            "razon_social": "Kitchan S.A.",
            "identificacion_fiscal": "1791234567001",
            "direccion": "Av. Amazonas y Naciones Unidas",
            "telefono": "0987654321",
            "email_corporativo": "empresa@kitchan.com",
        },
        "admin": {
            "nombre": "Isaac Puga",
            "email": "isaac.admin@kitchan.com",
            "password": "Password123*",
        },
    }
    response = await client.post("/api/v1/onboarding/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "restaurante" in data
    assert "admin" in data
    assert data["restaurante"]["email_corporativo"] == "empresa@kitchan.com"


@pytest.mark.asyncio
async def test_registrar_restaurante_ruc_duplicado(client):
    payload = {
        "restaurante": {
            "nombre_comercial": "Local 1",
            "razon_social": "S.A. 1",
            "identificacion_fiscal": "1799999999001",
            "direccion": "Calle A",
            "telefono": "0999999999",
            "email_corporativo": "correo1@test.com",
        },
        "admin": {
            "nombre": "Admin 1",
            "email": "admin1@test.com",
            "password": "Password123*",
        },
    }
    # Primer registro exitoso
    res1 = await client.post("/api/v1/onboarding/", json=payload)
    assert res1.status_code == 201

    # Segundo registro con el mismo RUC (identificacion_fiscal)
    payload["admin"][
        "email"
    ] = "admin2@test.com"  # Cambiamos email para probar solo el RUC
    res2 = await client.post("/api/v1/onboarding/", json=payload)
    assert res2.status_code == 400
    assert "identificación fiscal" in res2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_registrar_restaurante_email_empresa_duplicado(client):
    payload = {
        "restaurante": {
            "nombre_comercial": "Local A",
            "razon_social": "Sociedad A",
            "identificacion_fiscal": "1711111111001",
            "direccion": "Calle 1",
            "telefono": "0988888888",
            "email_corporativo": "duplicado@empresa.com",
        },
        "admin": {
            "nombre": "Admin A",
            "email": "a@test.com",
            "password": "Password123*",
        },
    }
    await client.post("/api/v1/onboarding/", json=payload)

    # Intentar registrar otro restaurante con el mismo email corporativo
    payload["restaurante"]["identificacion_fiscal"] = "1722222222001"
    payload["admin"]["email"] = "b@test.com"
    res = await client.post("/api/v1/onboarding/", json=payload)
    assert res.status_code == 400
    assert "email corporativo" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_registrar_restaurante_mismo_correo_empresa_y_admin(client):
    payload = {
        "restaurante": {
            "nombre_comercial": "Local Mismo Correo",
            "razon_social": "S.A.",
            "identificacion_fiscal": "1733333333001",
            "direccion": "Calle X",
            "telefono": "0977777777",
            "email_corporativo": "mismo@correo.com",
        },
        "admin": {
            "nombre": "Admin",
            "email": "mismo@correo.com",  # <- Mismo correo que la empresa
            "password": "Password123*",
        },
    }
    res = await client.post("/api/v1/onboarding/", json=payload)
    assert res.status_code == 400
    assert (
        "igual" in res.json()["detail"].lower()
        or "diferente" in res.json()["detail"].lower()
    )
