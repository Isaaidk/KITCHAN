"""Bot de WhatsApp falso: se hace pasar por el bot real (servicio independiente)
para que las acciones de KITCHAN (aceptar / rechazar / listo) se puedan probar
en la demo sin el bot ni un número de WhatsApp.

Implementa la ruta que llama WhatsAppBotHttpAdapter
(integraciones/whatsapp/infrastructure/adapters/http_bot_adapter.py): valida la
firma `X-Kitchan-Signature` con WHATSAPP_BOT_SECRET y muestra en consola el
mensaje que el bot le escribiría al cliente.

Uso (desde kitchan-backend/):
    uvicorn scripts.simulador_whatsapp.bot_whatsapp_falso:app --port 8001

y en el .env del backend:
    WHATSAPP_BOT_URL=http://127.0.0.1:8001
"""

import hashlib
import hmac
import json
import os
import time
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Request

load_dotenv(".env")

app = FastAPI(title="Bot de WhatsApp falso (simulador KITCHAN)")

TOLERANCIA_SEGUNDOS = 300

# Lo que el bot real le escribiría al cliente según la decisión del restaurante.
MENSAJES = {
    "ACCEPTED": "✅ ¡Tu pedido fue aceptado y ya lo estamos preparando!",
    "REJECTED": "❌ Lo sentimos, no podemos atender tu pedido",
    "READY": "🛎️ ¡Tu pedido está listo!",
    "CANCELLED": "❌ Tu pedido fue cancelado",
}


def _firma_valida(secret: str, body: bytes, header: Optional[str]) -> bool:
    if not secret or not header:
        return False
    partes = dict(p.strip().partition("=")[::2] for p in header.split(","))
    try:
        t = int(partes.get("t", ""))
    except ValueError:
        return False
    if abs(time.time() - t) > TOLERANCIA_SEGUNDOS:
        return False
    esperada = hmac.new(
        secret.encode("utf-8"), str(t).encode() + b"." + body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(esperada, partes.get("sign", ""))


@app.post("/api/kitchan/orders/{order_id}/status")
async def estado_del_pedido(
    order_id: str,
    request: Request,
    x_kitchan_signature: Optional[str] = Header(default=None),
):
    body = await request.body()
    if not _firma_valida(
        os.getenv("WHATSAPP_BOT_SECRET", ""), body, x_kitchan_signature
    ):
        print(f"🚨 [BOT WHATSAPP FALSO] Aviso del pedido {order_id} con firma inválida")
        raise HTTPException(status_code=401, detail="Firma inválida")

    datos = json.loads(body or b"{}")
    estado = str(datos.get("status", "")).upper()
    motivo = datos.get("reason")
    mensaje = MENSAJES.get(estado, f"Estado del pedido: {estado}")
    if motivo:
        mensaje += f" ({motivo})"
    print(f"💬 [BOT WHATSAPP FALSO] Pedido {order_id} -> al cliente: {mensaje}")
    return {"status": "ok"}


@app.get("/")
async def raiz():
    return {"servicio": "Bot de WhatsApp falso", "puerto": 8001}
