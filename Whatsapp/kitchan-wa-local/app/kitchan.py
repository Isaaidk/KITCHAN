"""Cliente del backend de KITCHAN (servicio independiente).

El bot solo EMITE el evento de pedido al webhook de KITCHAN y RECIBE de vuelta
la decisión del restaurante (aceptado/rechazado/listo). Toda la comunicación va
firmada con HMAC-SHA256 sobre "<t>.<body>" (header X-Kitchan-Signature), el
mismo esquema en ambos sentidos.
"""

import hashlib
import hmac
import json
import logging
import os
import time
from typing import Optional

import httpx

log = logging.getLogger("kitchan_whatsapp.kitchan")

HEADER = "X-Kitchan-Signature"
TOLERANCIA_SEGUNDOS = 300

KITCHAN_API_URL = os.getenv("KITCHAN_API_URL", "http://127.0.0.1:8000").strip().rstrip("/")
BOT_SECRET = os.getenv("KITCHAN_BOT_SECRET", "").strip()
STORE_ID = os.getenv("KITCHAN_STORE_ID", "default").strip() or "default"
NEW_ORDER_URL = f"{KITCHAN_API_URL}/api/v1/integraciones/whatsapp/webhook/new-order"


def configured() -> bool:
    return bool(BOT_SECRET and KITCHAN_API_URL)


def sign(raw_body: bytes, timestamp: Optional[int] = None) -> str:
    t = str(int(time.time()) if timestamp is None else timestamp)
    digest = hmac.new(BOT_SECRET.encode(), t.encode() + b"." + raw_body, hashlib.sha256).hexdigest()
    return f"t={t},sign={digest}"


def verify(raw_body: bytes, header: str, now: Optional[float] = None) -> bool:
    if not BOT_SECRET or not header:
        return False
    parts = dict(p.strip().partition("=")[::2] for p in header.split(","))
    try:
        t = int(parts.get("t", ""))
    except ValueError:
        return False
    if abs((time.time() if now is None else now) - t) > TOLERANCIA_SEGUNDOS:
        return False
    expected = sign(raw_body, t).partition("sign=")[2]
    return hmac.compare_digest(expected, parts.get("sign", ""))


def build_payload(order: dict) -> dict:
    """Pedido local (fila de `orders` ya con items decodificados) -> contrato del webhook."""
    return {
        "order_id": order["kitchan_order_id"],
        "store_id": STORE_ID,
        "customer_name": order.get("customer_name") or f"WhatsApp ***{order['customer_phone'][-4:]}",
        "items": [{"name": i["title"], "quantity": i["quantity"], "unit_price": i["unit_price"],
                   "notes": i.get("notes") or None} for i in order["items"]],
        "total": order["total"],
        "currency": order.get("currency") or None,
        "payment_method": order.get("payment_method") or None,
        "customer_phone": order.get("customer_phone") or None,
        "delivery_type": order.get("delivery_type") or None,
        "delivery_address": order.get("delivery_address") or None,
        "order_notes": order.get("order_notes") or None,
    }


async def send_order(order: dict) -> tuple[bool, str]:
    """Envía el pedido a KITCHAN. (True, "") si KITCHAN lo registró (200, también
    si ya lo tenía: es idempotente). Un 4xx de validación no se reintenta."""
    if not configured():
        return False, "Falta KITCHAN_BOT_SECRET en .env"
    body = json.dumps(build_payload(order), ensure_ascii=False).encode()
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(NEW_ORDER_URL, content=body,
                                         headers={"Content-Type": "application/json", HEADER: sign(body)})
    except httpx.HTTPError as e:
        return False, f"KITCHAN no responde: {e.__class__.__name__}"
    if response.is_success:
        return True, ""
    return False, f"HTTP {response.status_code}: {response.text[:200]}"
