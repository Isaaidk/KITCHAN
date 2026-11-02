"""Respuestas con Gemini. Devuelve JSON estructurado para que el código ejecute las acciones."""
import asyncio
import json
import logging
import os

import httpx

log = logging.getLogger("kitchan_whatsapp.ai")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash").strip()
GEMINI_FALLBACK_MODEL = os.getenv("GEMINI_FALLBACK_MODEL", "gemini-3.5-flash-lite").strip()
BUSINESS_NAME = os.getenv("BUSINESS_NAME", "Vangalia by Sweet Center").strip()

SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "reply": {"type": "STRING"},
        "action": {"type": "STRING", "enum": ["none", "show_menu", "show_products", "start_checkout"]},
        "product_ids": {"type": "ARRAY", "items": {"type": "STRING"}},
        "items": {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {
            "product_id": {"type": "STRING"}, "quantity": {"type": "INTEGER"}, "notes": {"type": "STRING"}},
            "required": ["product_id", "quantity"]}},
    },
    "required": ["reply", "action"],
}


def configured() -> bool:
    return bool(GEMINI_API_KEY)


def _system_prompt(products: list[dict], cart: list[tuple] | None = None) -> str:
    in_cart = ""
    if cart:
        in_cart = ("\n\nCARRITO ACTUAL DEL CLIENTE (ya registrado): "
                   + "; ".join(f"{q} x {p['title']}" + (f" ({n})" if n else "") for p, q, n in cart)
                   + ".\nEn items devuelve SOLO los productos que el cliente agrega ahora; NUNCA repitas los del carrito.")
    lines = []
    for p in products:
        stock = "disponible" if p["stock"] is None and p["available"] else (f"{p['stock']} en stock" if p["available"] else "AGOTADO")
        lines.append(f"- {p['id']} | {p['title']} | {p['description']} | {p['price']:.2f} {p['currency']} | {stock}")
    return (
        f"Eres el asistente de WhatsApp de {BUSINESS_NAME}, una cafetería. Responde en español, amable, breve y con algún emoji.\n"
        "Solo puedes ofrecer productos del MENÚ de abajo, con sus precios y disponibilidad exactos. Nunca inventes productos, precios ni stock.\n"
        "Acciones: show_menu = enviar la lista completa del menú; show_products = enviar ficha con foto de los product_ids indicados; "
        "start_checkout = cuando el cliente ya dijo qué productos y cuántas unidades quiere pedir; indica en items los product_id y cantidades. "
        "Si el cliente pide algo especial para un producto (ej. 'leche deslactosada', 'sin azúcar', 'con crema extra', 'sin hielo'), "
        "ponlo textual y breve en el campo notes de ESE producto dentro de items; si no hay especificación deja notes vacío. "
        "No inventes especificaciones. Si pide el mismo producto con distintas especificaciones, crea una línea por cada una. "
        "Si pregunta si puede personalizar o cambiar algo (leche, azúcar, extras), dile que sí y que lo anotarás en el pedido; "
        "no prometas cambios de precio. "
        "NUNCA agregues productos que el cliente no pidió con claridad (no asumas croissants, postres ni extras). "
        "El sistema preguntará después, con botones, si desea algo más y qué especificación quiere en cada producto (tipo de leche, azúcar, extras), "
        "y luego pedirá nombre, apellido, tipo de entrega (domicilio o retiro), dirección, método de pago y la confirmación final, "
        "así que NO pidas confirmación ni esos datos tú: "
        "tu reply debe ser corto (resume lo pedido y avisa que enseguida le preguntarás si desea algo más). En cualquier otro caso usa none.\n"
        "No ofrezcas ni aceptes productos AGOTADOS; sugiere alternativas. Si preguntan algo fuera de tema, redirige al menú.\n\n"
        "MENÚ:\n" + "\n".join(lines) + in_cart
    )


async def reply(history: list[dict], products: list[dict], cart: list[tuple] | None = None) -> dict | None:
    """history: [{'role': 'user'|'model', 'text': str}] en orden cronológico. None si falla.
    cart: líneas (producto, cantidad, especificación) que el cliente ya tiene registradas."""
    if not GEMINI_API_KEY:
        return None
    body = {
        "systemInstruction": {"parts": [{"text": _system_prompt(products, cart or [])}]},
        "contents": [{"role": m["role"], "parts": [{"text": m["text"]}]} for m in history],
        "generationConfig": {"responseMimeType": "application/json", "responseSchema": SCHEMA, "temperature": 0.4},
    }
    for attempt, model in enumerate([GEMINI_MODEL, GEMINI_MODEL, GEMINI_FALLBACK_MODEL]):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.post(url, headers={"x-goog-api-key": GEMINI_API_KEY}, json=body)
            if r.status_code in (429, 500, 502, 503, 504):
                log.warning("Gemini %s respondió %s (intento %s)", model, r.status_code, attempt + 1)
                await asyncio.sleep(1.5)
                continue
            r.raise_for_status()
            data = json.loads(r.json()["candidates"][0]["content"]["parts"][0]["text"])
            data.setdefault("action", "none")
            return data
        except Exception:
            log.exception("Gemini falló con %s", model)
            return None
    return None
