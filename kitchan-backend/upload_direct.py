import httpx
import asyncio

async def probar_flujo_oficial():
    # 1. Credenciales de tu KITCHAN V1
    CLIENT_ID = "oJS2l9uRbwnZBwZiEbyJQ7MXoLV1E4lF"
    CLIENT_SECRET = "WOMOg2snzChXvb0cMSM7r8wsfmU41tsuScILC_CG"
    
    print("=== PASO 1: Generar Token (Client Credentials) ===")
    
    # Nota: Usamos sandbox-login porque tu tienda es de prueba, 
    # pero el formato es idéntico al auth.uber.com de la documentación.
    token_url = "https://sandbox-login.uber.com/oauth/v2/token"
    
    # Según la doc, se envían como form-data (-F en curl)
    payload = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "client_credentials",
        "scope": "eats.store eats.order"
    }
    
    async with httpx.AsyncClient() as client:
        # httpx usa 'data' para enviar como application/x-www-form-urlencoded
        token_res = await client.post(token_url, data=payload)
        
    if token_res.status_code != 200:
        print(f"❌ Error al generar token: {token_res.text}")
        return
        
    respuesta_json = token_res.json()
    token = respuesta_json.get("access_token")
    
    print("✅ ¡Token generado exitosamente!")
    print(f"Tipo: {respuesta_json.get('token_type')}")
    print(f"Expira en: {respuesta_json.get('expires_in')} segundos")
    print(f"Scopes autorizados: {respuesta_json.get('scope')}")
    
    print("\n=== PASO 2: Usar el token de portador (Bearer) ===")
    print("Consultando el punto final de tiendas según la documentación...")
    
    # Endpoint de la documentación para listar tiendas
    stores_url = "https://api.uber.com/v1/eats/stores"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    async with httpx.AsyncClient() as client:
        stores_res = await client.get(stores_url, headers=headers)
        
    print(f"Código HTTP de respuesta: {stores_res.status_code}")
    
    if stores_res.status_code == 200:
        print("✅ Tiendas detectadas:")
        print(stores_res.text)
    else:
        print(f"⚠️ Respuesta de Uber: {stores_res.text}")

if __name__ == "__main__":
    asyncio.run(probar_flujo_oficial())