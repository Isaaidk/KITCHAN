import httpx
import hmac
import hashlib
import json
import os
import asyncio
from dotenv import load_dotenv


async def disparar_webhook_simulado():
    # 1. Cargamos tu clave secreta
    load_dotenv()
    secret = os.getenv("UBER_WEBHOOK_SECRET", "")

    if not secret:
        print("❌ Error: No se encontró UBER_WEBHOOK_SECRET en el .env")
        return

    # 2. Creamos el JSON exacto que Uber enviaría
    payload = {
        "event_type": "orders.notification",
        "event_id": "evento-simulado-123",
        "meta": {
            "resource_id": "MOCK-ORDER-12345",  # Este es el ID de la orden
            "status": "pending",
            "user_id": "cliente-test",
        },
    }

    # 3. Convertimos a bytes sin espacios (vital para la criptografía)
    cuerpo_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")

    # 4. Generamos la firma HMAC exactamente como lo hace Uber
    firma = hmac.new(secret.encode("utf-8"), cuerpo_bytes, hashlib.sha256).hexdigest()

    # Apuntamos a tu servidor local en el puerto 8000
    url = "http://127.0.0.1:8000/api/v1/integraciones/uber/webhook?restaurante_id=TEST-123"
    headers = {"Content-Type": "application/json", "X-Uber-Signature": firma}

    print("🚀 Disparando webhook simulado a KITCHAN...")

    async with httpx.AsyncClient() as client:
        respuesta = await client.post(url, content=cuerpo_bytes, headers=headers)

    print(f"Respuesta de KITCHAN: {respuesta.status_code} -> {respuesta.text}")


# Ejecutamos el script
if __name__ == "__main__":
    asyncio.run(disparar_webhook_simulado())
