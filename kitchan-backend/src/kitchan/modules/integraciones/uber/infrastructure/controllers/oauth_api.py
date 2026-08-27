import os
import secrets
from urllib.parse import urlencode

import httpx
from dotenv import load_dotenv
from src.kitchan.modules.integraciones.uber.domain.schemas import UberProvisionRequest
from fastapi import APIRouter, HTTPException, Query, Depends,Request
from fastapi.responses import RedirectResponse, Response 

from src.kitchan.modules.integraciones.uber.domain.ports import (
    UberTokenCachePort,
    UberOAuthStatePort
)

from src.kitchan.modules.integraciones.uber.infrastructure.adapters.redis_token_adapter import (
    RedisUberTokenAdapter
)


# ============================================================
# CONFIGURACIÓN
# ============================================================

load_dotenv()


router = APIRouter(
    prefix="/api/v1/integraciones/uber/auth",
    tags=["Integraciones - Uber Eats Auth"]
)


UBER_CLIENT_ID = os.getenv("UBER_CLIENT_ID")
UBER_CLIENT_SECRET = os.getenv("UBER_CLIENT_SECRET")

REDIS_URL = os.getenv(
    "REDIS_URL",
    "redis://localhost:6379/0"
)


# ============================================================
# URLS DE UBER
# ============================================================

# Authorization Code
# Se utiliza para que el merchant autorice KITCHAN.
UBER_AUTHORIZE_URL = (
    "https://sandbox-login.uber.com/oauth/v2/authorize"
)


# Intercambio authorization_code -> access_token
UBER_TOKEN_URL = (
    "https://sandbox-login.uber.com/oauth/v2/token"
)


# API de pruebas de Uber Eats
UBER_API_BASE = "https://test-api.uber.com"


# ============================================================
# REDIRECT URI
# ============================================================

UBER_REDIRECT_URI = (
    "https://automatic-funicular-ww9xx7p66jxhvvwr-8000.app.github.dev"
    "/api/v1/integraciones/uber/auth/callback"
)


# ============================================================
# SCOPES
# ============================================================

# Scope utilizado para autorización/provisionamiento
# de tiendas de Uber Eats.
UBER_SCOPE = "eats.pos_provisioning"


# ============================================================
# DEPENDENCIES
# ============================================================

def get_token_adapter() -> UberTokenCachePort:
    """
    Devuelve el adaptador encargado de almacenar
    y recuperar los access tokens desde Redis.
    """

    return RedisUberTokenAdapter(
        redis_url=REDIS_URL
    )


def get_oauth_state_adapter() -> UberOAuthStatePort:
    """
    Devuelve el adaptador encargado de almacenar
    temporalmente los estados OAuth.
    """

    return RedisUberTokenAdapter(
        redis_url=REDIS_URL
    )


# ============================================================
# AUTHORIZATION CODE FLOW
# ============================================================

@router.get("/login")
async def uber_login(
    restaurante_id: str = Query(
        ...,
        description="ID del restaurante en Kitchan"
    ),
    state_adapter: UberOAuthStatePort = Depends(
        get_oauth_state_adapter
    )
):
    """
    Inicia el flujo OAuth Authorization Code de Uber.

    El restaurante es enviado a Uber para iniciar sesión
    y autorizar a Kitchan.

    Flujo:

        Kitchan
            ↓
        /login
            ↓
        Uber Authorization
            ↓
        Usuario acepta
            ↓
        /callback
    """

    # --------------------------------------------------------
    # Validar Client ID
    # --------------------------------------------------------

    if not UBER_CLIENT_ID:

        raise HTTPException(
            status_code=500,
            detail="UBER_CLIENT_ID no está configurado"
        )


    # --------------------------------------------------------
    # Limpiar Client ID
    # --------------------------------------------------------

    client_id_limpio = (
        UBER_CLIENT_ID
        .strip()
        .replace('"', '')
        .replace("'", "")
    )


    if not client_id_limpio:

        raise HTTPException(
            status_code=500,
            detail="UBER_CLIENT_ID está vacío"
        )


    # --------------------------------------------------------
    # Generar STATE
    # --------------------------------------------------------

    state = secrets.token_urlsafe(32)


    # --------------------------------------------------------
    # Guardar STATE en Redis
    #
    # state -> restaurante_id
    #
    # Ejemplo:
    #
    # uber_oauth_state:ABC123
    #          ↓
    #       TEST-001
    #
    # TTL = 10 minutos
    # --------------------------------------------------------

    await state_adapter.save_state(
        state=state,
        restaurante_id=restaurante_id,
        expires_in=600
    )


    # --------------------------------------------------------
    # Parámetros OAuth
    # --------------------------------------------------------

    params = {
        "client_id": client_id_limpio,
        "response_type": "code",
        "redirect_uri": UBER_REDIRECT_URI,
        "scope": UBER_SCOPE,
        "state": state,
        "prompt": "consent"
    }


    # --------------------------------------------------------
    # Construir URL de autorización
    # --------------------------------------------------------

    authorization_url = (
        f"{UBER_AUTHORIZE_URL}?{urlencode(params)}"
    )


    # --------------------------------------------------------
    # Redireccionar al usuario hacia Uber
    # --------------------------------------------------------

    return RedirectResponse(
        url=authorization_url,
        status_code=302
    )


# ============================================================
# OAUTH CALLBACK
# ============================================================


@router.get("/callback")
@router.post("/callback")
async def uber_callback(
    code: str = Query(..., description="Authorization code entregado por Uber"),
    state: str = Query(..., description="State generado por Kitchan"),
    token_adapter: UberTokenCachePort = Depends(get_token_adapter),
    state_adapter: UberOAuthStatePort = Depends(get_oauth_state_adapter)
):
    """
    Callback multi-tenant: Intercambia el token, descubre las tiendas autorizadas
    y crea el mapeo en Redis para que los webhooks sepan a quién pertenece cada pedido.
    """
    # 1. Recuperar el Tenant desde el State
    restaurante_id = await state_adapter.get_restaurante_id(state)
    if not restaurante_id:
        raise HTTPException(status_code=400, detail="State inválido o expirado.")
    await state_adapter.delete_state(state)

    # Limpiar credenciales
    client_id_limpio = UBER_CLIENT_ID.strip().replace('"', '').replace("'", "")
    client_secret_limpio = UBER_CLIENT_SECRET.strip().replace('"', '').replace("'", "")

    # 2. Solicitar ACCESS TOKEN
    payload = {
        "client_id": client_id_limpio,
        "client_secret": client_secret_limpio,
        "grant_type": "authorization_code",
        "redirect_uri": UBER_REDIRECT_URI,
        "code": code
    }

    async with httpx.AsyncClient() as client:
        respuesta = await client.post(
            UBER_TOKEN_URL,
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30
        )

    if respuesta.status_code != 200:
        raise HTTPException(status_code=400, detail="Uber rechazó el authorization code")

    tokens = respuesta.json()
    access_token = tokens.get("access_token")
    expires_in = tokens.get("expires_in", 2592000)

    # 3. Guardar el ACCESS TOKEN
    await token_adapter.save_provisioning_token(
        restaurante_id=restaurante_id,
        token=access_token,
        expires_in=expires_in
    )

    # ==========================================================
    # 4. LA MAGIA MULTI-TENANT: OBTENER Y MAPEAR TIENDAS
    # ==========================================================
    stores_url = f"{UBER_API_BASE}/v1/eats/stores"
    headers_store = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient() as client:
        respuesta_stores = await client.get(stores_url, headers=headers_store, timeout=30)
        
    tiendas_mapeadas = 0
    if respuesta_stores.status_code == 200:
        stores_data = respuesta_stores.json()
        
        # Uber devuelve una lista de tiendas en el campo "stores" o directamente en un array
        # Depende un poco de la API, usualmente es un dict que contiene un array
        lista_tiendas = stores_data if isinstance(stores_data, list) else stores_data.get("stores", [])
        
        for store in lista_tiendas:
            store_id = store.get("store_id")
            if store_id:
                # CREAMOS EL PUENTE: store_id -> restaurante_id
                await token_adapter.save_store_mapping(store_id, restaurante_id)
                tiendas_mapeadas += 1

    return {
        "mensaje": "Restaurante autorizado y mapeado correctamente",
        "restaurante_id": restaurante_id,
        "tiendas_vinculadas": tiendas_mapeadas,
        "expires_in": expires_in
    }

# ============================================================
# CLIENT CREDENTIALS
# ============================================================

@router.post("/app-token")
async def generate_app_token(
    restaurante_id: str = Query(
        ...,
        description="ID del restaurante en Kitchan"
    ),
    token_adapter: UberTokenCachePort = Depends(
        get_token_adapter
    )
):
    """
    Obtiene un token mediante Client Credentials.

    IMPORTANTE:

    Este endpoint NO autoriza una tienda.

    Sirve para obtener un token de aplicación para
    operaciones que utilizan Client Credentials.
    """

    # --------------------------------------------------------
    # Validar credenciales
    # --------------------------------------------------------

    if not UBER_CLIENT_ID or not UBER_CLIENT_SECRET:

        raise HTTPException(
            status_code=500,
            detail=(
                "Credenciales de Uber incompletas "
                "en el .env"
            )
        )


    # --------------------------------------------------------
    # Limpiar credenciales
    # --------------------------------------------------------

    client_id_limpio = (
        UBER_CLIENT_ID
        .strip()
        .replace('"', '')
        .replace("'", "")
    )

    client_secret_limpio = (
        UBER_CLIENT_SECRET
        .strip()
        .replace('"', '')
        .replace("'", "")
    )


    # --------------------------------------------------------
    # Client Credentials
    # --------------------------------------------------------

    payload = {
        "client_id": client_id_limpio,
        "client_secret": client_secret_limpio,
        "grant_type": "client_credentials",
        "scope": "eats.store eats.order"
    }


    headers = {
        "Content-Type": (
            "application/x-www-form-urlencoded"
        )
    }


    # --------------------------------------------------------
    # Solicitar token
    # --------------------------------------------------------

    async with httpx.AsyncClient() as client:

        try:

            respuesta = await client.post(
                "https://sandbox-login.uber.com/oauth/v2/token",
                data=payload,
                headers=headers,
                timeout=30
            )

        except httpx.RequestError as error:

            raise HTTPException(
                status_code=502,
                detail=(
                    f"No se pudo comunicar con Uber: {error}"
                )
            )


    # --------------------------------------------------------
    # Validar respuesta
    # --------------------------------------------------------

    if respuesta.status_code != 200:

        raise HTTPException(
            status_code=400,
            detail={
                "mensaje": "Fallo en Uber Auth",
                "uber_status": respuesta.status_code,
                "uber_response": respuesta.text
            }
        )


    tokens = respuesta.json()

    access_token = tokens.get("access_token")
    expires_in = tokens.get("expires_in")


    if not access_token:

        raise HTTPException(
            status_code=502,
            detail=(
                "Uber no devolvió access_token"
            )
        )


    # --------------------------------------------------------
    # Guardar token
    # --------------------------------------------------------

    await token_adapter.save_app_token(
        restaurante_id=restaurante_id,
        token=access_token,
        expires_in=expires_in
    )


    return {
        "mensaje": (
            "Access Token de aplicación generado "
            "y almacenado en Redis"
        ),
        "restaurante_id": restaurante_id,
        "expira_en_segundos": expires_in
    }


# ============================================================
# DIAGNÓSTICO DE TIENDA
# ============================================================

@router.get("/diagnostico")
async def diagnosticar_tienda_uber(
    restaurante_id: str = Query(
        ...,
        description="ID del restaurante en Kitchan"
    ),
    token_adapter: UberTokenCachePort = Depends(
        get_token_adapter
    )
):
    """
    Consulta una tienda utilizando el token almacenado.
    """

    # --------------------------------------------------------
    # Obtener token desde Redis
    # --------------------------------------------------------

    token = await token_adapter.get_token(
        restaurante_id
    )


    if not token:

        raise HTTPException(
            status_code=404,
            detail=(
                "No hay token en Redis para este restaurante."
            )
        )


    # --------------------------------------------------------
    # Store UUID de prueba
    # --------------------------------------------------------

    STORE_UUID = (
        "13e7c732-7b58-44c1-b313-957557d6b482"
    )


    # --------------------------------------------------------
    # URL de la tienda
    # --------------------------------------------------------

    store_url = (
        f"{UBER_API_BASE}"
        f"/v1/eats/stores/{STORE_UUID}"
    )


    # --------------------------------------------------------
    # Headers
    # --------------------------------------------------------

    headers = {
        "Authorization": f"Bearer {token}"
    }


    # --------------------------------------------------------
    # Request
    # --------------------------------------------------------

    async with httpx.AsyncClient() as client:

        try:

            respuesta = await client.get(
                store_url,
                headers=headers,
                timeout=30
            )

        except httpx.RequestError as error:

            raise HTTPException(
                status_code=502,
                detail=(
                    f"No se pudo comunicar con Uber: {error}"
                )
            )


    # --------------------------------------------------------
    # Éxito
    # --------------------------------------------------------

    if respuesta.status_code == 200:

        return {
            "mensaje": (
                "La tienda respondió correctamente "
                "en el entorno Sandbox"
            ),
            "datos_uber": respuesta.json()
        }


    # --------------------------------------------------------
    # Error
    # --------------------------------------------------------

    raise HTTPException(
        status_code=respuesta.status_code,
        detail={
            "mensaje": "Fallo al consultar tienda",
            "uber_status": respuesta.status_code,
            "uber_response": respuesta.text
        }
    )

@router.get("/stores")
async def obtener_tiendas_uber(
    restaurante_id: str = Query(
        ...,
        description="ID del restaurante en Kitchan"
    ),
    token_adapter: UberTokenCachePort = Depends(
        get_token_adapter
    )
):
    """
    Obtiene las tiendas autorizadas por el merchant
    utilizando el access token generado mediante OAuth.
    """

    token = await token_adapter.get_token(
        restaurante_id
    )

    if not token:
        raise HTTPException(
            status_code=404,
            detail=(
                "No existe un access token para este restaurante. "
                "Ejecuta primero /login."
            )
        )

    stores_url = (
        f"{UBER_API_BASE}/v1/eats/stores"
    )

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient() as client:

        respuesta = await client.get(
            stores_url,
            headers=headers,
            timeout=30
        )

    if respuesta.status_code != 200:

        raise HTTPException(
            status_code=respuesta.status_code,
            detail={
                "mensaje": "Uber rechazó la consulta de tiendas",
                "uber_status": respuesta.status_code,
                "uber_response": respuesta.text
            }
        )

    return {
        "mensaje": "Tiendas obtenidas correctamente",
        "restaurante_id": restaurante_id,
        "stores": respuesta.json()
    }

@router.post("/provision")
async def provisionar_tienda_uber(
    data: UberProvisionRequest,
    token_adapter: UberTokenCachePort = Depends(get_token_adapter)
):
    """
    Provisiona KITCHAN como integración POS para una tienda de Uber Eats.
    Requiere que el token en Redis sea el obtenido vía OAuth (Authorization Code).
    """
    # 1. Recuperar el token OAuth (Provisioning Token)
    token = await token_adapter.get_provisioning_token(data.restaurante_id)

    if not token:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "UBER_TOKEN_NOT_FOUND",
                "mensaje": "No existe un access token de Uber para este restaurante. Ejecuta /login primero."
            }
        )

    # 2. URL de Provisioning en el entorno Sandbox
    url = f"{UBER_API_BASE}/v1/eats/stores/{data.store_id}/pos_data"

    # 3. Payload oficial para enlazar KITCHAN
    payload = {
        "integrator_store_id": data.restaurante_id,
        "integrator_brand_id": "KITCHAN",
        "store_configuration_data": f'{{"kitchan_restaurante_id": "{data.restaurante_id}"}}'
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    # 4. Ejecutar petición a Uber
    async with httpx.AsyncClient() as client:
        respuesta = await client.post(url, json=payload, headers=headers, timeout=30)

    # 5. Uber debe devolver 204 No Content en caso de éxito
    if respuesta.status_code not in (200, 201, 204):
        raise HTTPException(
            status_code=respuesta.status_code,
            detail={
                "error": "UBER_PROVISION_FAILED",
                "mensaje": "Uber rechazó el provisioning de la tienda.",
                "uber_status": respuesta.status_code,
                "uber_response": respuesta.text,
            }
        )

    return {
        "mensaje": "Tienda provisionada correctamente en Uber Eats.",
        "restaurante_id": data.restaurante_id,
        "store_id": data.store_id,
        "status": respuesta.status_code,
    }

@router.get("/provision/{store_id}/status")
async def verificar_estado_provisioning(
    store_id: str,
    restaurante_id: str = Query(..., description="ID del restaurante en Kitchan (Ej: TEST-001)"),
    token_adapter: UberTokenCachePort = Depends(get_token_adapter)
):
    """
    Verifica el estado del provisioning en Uber usando CLIENT CREDENTIALS.
    """
    # ATENCIÓN AQUÍ: Debemos leer el APP TOKEN (Client Credentials), no el de OAuth.
    # Ajusta el nombre del método (get_app_token o get_token) según cómo lo llamaste en tu adaptador
    token = await token_adapter.get_app_token(restaurante_id)

    if not token:
        raise HTTPException(
            status_code=404,
            detail="No existe el APP TOKEN (Client Credentials) para este restaurante. Ejecuta /app-token primero."
        )

    # URL de consulta en Sandbox
    url = f"{UBER_API_BASE}/v1/eats/stores/{store_id}/pos_data"

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }

    async with httpx.AsyncClient() as client:
        respuesta = await client.get(url, headers=headers, timeout=30)

    if respuesta.status_code != 200:
        raise HTTPException(
            status_code=respuesta.status_code,
            detail={
                "error": "UBER_STATUS_CHECK_FAILED",
                "mensaje": "Fallo al leer con Client Credentials.",
                "uber_response": respuesta.text
            }
        )
        
    datos_uber = respuesta.json()

    return {
        "mensaje": "¡KITCHAN es oficialmente el POS de esta tienda!",
        "integration_enabled": datos_uber.get("integration_enabled", False),
        "datos_completos": datos_uber
    }

@router.put("/menu/upload/{store_id}")
async def subir_menu_uber(
    store_id: str,
    restaurante_id: str = Query(..., description="ID del restaurante en Kitchan (Ej: TEST-001)"),
    token_adapter: UberTokenCachePort = Depends(get_token_adapter)
):
    """
    Sube un menú de prueba a la tienda autorizada usando Client Credentials.
    """
    # 1. Recuperamos el App Token (Client Credentials)
    token = await token_adapter.get_app_token(restaurante_id)
    if not token:
        raise HTTPException(status_code=404, detail="App Token no encontrado. Ejecuta /app-token.")

    # 2. URL para subir el menú en Sandbox
    # Nota: Uber usa POST v1/delivery/stores/.../menus o PUT v2/eats/stores/.../menus
    url = f"{UBER_API_BASE}/v2/eats/stores/{store_id}/menus"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    # 3. Payload de Menú Básico (Una Hamburguesa)
    dias_semana = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    disponibilidad = [
        {
            "day_of_week": dia,
            "time_periods": [{"start_time": "00:00", "end_time": "23:59"}]
        }
        for dia in dias_semana
    ]
    menu_payload = {
        "items": [
            {
                "id": "item-hamburguesa-1",
                "title": {"translations": {"es": "Hamburguesa Kitchan"}},
                "price_info": {"price": 1000, "overrides": []}, # 10.00 en la moneda local
                "tax_info": {"tax_rate": 0}
            }
        ],
        "categories": [
            {
                "id": "cat-principales",
                "title": {"translations": {"es": "Platos Principales"}},
                "entities": [{"id": "item-hamburguesa-1", "type": "ITEM"}]
            }
        ],
        "menus": [
            {
                "id": "menu-principal",
                "title": {"translations": {"es": "Menú Principal"}},
                "category_ids": ["cat-principales"],
                "service_availability": disponibilidad
            }
        ],
        "modifier_groups": []
    }

    async with httpx.AsyncClient() as client:
        respuesta = await client.put(url, json=menu_payload, headers=headers, timeout=30)

    if respuesta.status_code not in (200, 204):
        raise HTTPException(
            status_code=respuesta.status_code,
            detail={"error": "Fallo al subir menú", "uber_response": respuesta.text}
        )

    return {"mensaje": "¡Menú inyectado con éxito!", "status": respuesta.status_code}


@router.get("/order/{order_id}")
async def obtener_detalles_pedido(
    order_id: str,
    restaurante_id: str = Query(..., description="ID del restaurante en Kitchan (Ej: TEST-001)"),
    token_adapter: UberTokenCachePort = Depends(get_token_adapter)
):
    """
    Descarga los detalles completos de un pedido usando su ID.
    Este método debe ejecutarse justo después de recibir el webhook.
    """
    token = await token_adapter.get_app_token(restaurante_id)
    if not token:
        raise HTTPException(status_code=404, detail="App Token no encontrado.")

    # Endpoint de Uber para obtener detalles del pedido (v2)
    url = f"{UBER_API_BASE}/v2/eats/order/{order_id}"

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }

    async with httpx.AsyncClient() as client:
        respuesta = await client.get(url, headers=headers, timeout=30)

    if respuesta.status_code != 200:
        raise HTTPException(
            status_code=respuesta.status_code,
            detail={"error": "Fallo al obtener pedido", "uber_response": respuesta.text}
        )

    return respuesta.json()