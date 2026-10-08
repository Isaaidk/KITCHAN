import asyncio
import httpx


async def cazar_tienda_especifica():
    token_url = "https://sandbox-login.uber.com/oauth/v2/token"
    payload = {
        "client_id": "oJS2l9uRbwnZBwZiEbyJQ7MXoLV1E4lF",
        "client_secret": "WOMOg2snzChXvb0cMSM7r8wsfmU41tsuScILC_CG",
        "grant_type": "client_credentials",
        "scope": "eats.store eats.order",
    }

    async with httpx.AsyncClient() as client:
        token_res = await client.post(token_url, data=payload)
    token = token_res.json().get("access_token")

    # 2. Consultamos directamente tu UUID de Organización a ver si también es el de la Tienda
    store_uuid = "f7127b4e-0021-407d-baf5-40524c4e96f9"
    stores_url = f"https://api.uber.com/v1/eats/stores/{store_uuid}"
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient() as client:
        respuesta = await client.get(stores_url, headers=headers)

    if respuesta.status_code == 200:
        print(f"✅ ¡BINGO! Tu Developer UUID es tu Store UUID. ID: {store_uuid}")
    else:
        print(
            f"❌ No es el mismo ID (Error {respuesta.status_code}). Hay que buscarlo en el panel."
        )


if __name__ == "__main__":
    asyncio.run(cazar_tienda_especifica())
