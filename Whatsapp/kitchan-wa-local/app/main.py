import asyncio
import hashlib
import hmac
import json
import logging
import os
import re
import sqlite3
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

from app import ai, kitchan, sheets  # noqa: E402  (leen variables de entorno al importar)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("kitchan_whatsapp")

ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN", "").strip()
PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "").strip()
API_VERSION = os.getenv("WHATSAPP_API_VERSION", "").strip()
VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "").strip()
APP_SECRET = os.getenv("WHATSAPP_APP_SECRET", "").strip()
ORDER_NOTIFICATION_PHONE = os.getenv("ORDER_NOTIFICATION_PHONE", "").strip().replace("+", "").replace(" ", "").replace("-", "")
AUTO_REPLY_ENABLED = os.getenv("AUTO_REPLY_ENABLED", "true").lower() in {"1", "true", "yes", "si", "sí"}
AUTO_REPLY_TEXT = os.getenv(
    "AUTO_REPLY_TEXT",
    "¡Hola! Gracias por escribir a KITCHAN. Recibimos tu mensaje y pronto te atenderemos.",
)
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", "./data/whatsapp.db"))
if not DATABASE_PATH.is_absolute():
    DATABASE_PATH = BASE_DIR / DATABASE_PATH
DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

KITCHAN_RETRY_SECONDS = 30
KITCHAN_MAX_ATTEMPTS = 20


@asynccontextmanager
async def lifespan(_: FastAPI):
    retry_task = asyncio.create_task(kitchan_retry_loop())
    yield
    retry_task.cancel()


app = FastAPI(title="KITCHAN WhatsApp Local", version="1.1.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "app" / "static")), name="static")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DATABASE_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with db() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wa_message_id TEXT UNIQUE,
            phone TEXT NOT NULL,
            direction TEXT NOT NULL CHECK(direction IN ('incoming','outgoing','status')),
            message_type TEXT NOT NULL DEFAULT 'text',
            text TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'received',
            timestamp TEXT NOT NULL,
            raw_json TEXT NOT NULL DEFAULT '{}'
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )""")
        conn.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('auto_reply_enabled',?)", ('true' if AUTO_REPLY_ENABLED else 'false',))
        conn.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('auto_reply_text',?)", (AUTO_REPLY_TEXT,))
        conn.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('order_notification_phone',?)", (ORDER_NOTIFICATION_PHONE,))
        conn.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('ai_enabled','true')")
        conn.execute("""CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wa_order_id TEXT UNIQUE,
            customer_phone TEXT NOT NULL,
            customer_name TEXT NOT NULL DEFAULT '',
            catalog_id TEXT NOT NULL DEFAULT '',
            items_json TEXT NOT NULL DEFAULT '[]',
            total REAL NOT NULL DEFAULT 0,
            currency TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'nuevo',
            raw_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS checkouts (
            phone TEXT PRIMARY KEY,
            step TEXT NOT NULL,
            cart_json TEXT NOT NULL DEFAULT '[]',
            first_name TEXT NOT NULL DEFAULT '',
            last_name TEXT NOT NULL DEFAULT '',
            payment TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL
        )""")
        # Migraciones aditivas (la tabla puede venir de versiones anteriores).
        for column in ("payment_method TEXT NOT NULL DEFAULT ''",
                       "kitchan_order_id TEXT NOT NULL DEFAULT ''",   # id externo enviado a KITCHAN
                       "kitchan_synced INTEGER NOT NULL DEFAULT 0",   # 1 = KITCHAN confirmó con 200
                       "kitchan_attempts INTEGER NOT NULL DEFAULT 0",
                       "kitchan_error TEXT NOT NULL DEFAULT ''"):
            try:
                conn.execute(f"ALTER TABLE orders ADD COLUMN {column}")
            except sqlite3.OperationalError:
                pass
        conn.commit()


init_db()


def setting(key: str, default: str = "") -> str:
    with db() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


def save_message(wa_message_id: str | None, phone: str, direction: str,
                 message_type: str, text: str, status: str, raw: Any) -> bool:
    try:
        with db() as conn:
            conn.execute(
                "INSERT INTO messages(wa_message_id,phone,direction,message_type,text,status,timestamp,raw_json) VALUES(?,?,?,?,?,?,?,?)",
                (wa_message_id, phone, direction, message_type, text, status, now_iso(), json.dumps(raw, ensure_ascii=False)),
            )
            conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False


async def send_whatsapp_text(to: str, text: str) -> dict:
    if not ACCESS_TOKEN or not PHONE_NUMBER_ID or not API_VERSION or "XX" in API_VERSION:
        raise HTTPException(status_code=503, detail="Configura WHATSAPP_ACCESS_TOKEN, WHATSAPP_PHONE_NUMBER_ID y una WHATSAPP_API_VERSION válida en .env")
    url = f"https://graph.facebook.com/{API_VERSION}/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    payload = {"messaging_product": "whatsapp", "recipient_type": "individual", "to": to, "type": "text", "text": {"preview_url": False, "body": text}}
    async with httpx.AsyncClient(timeout=25) as client:
        response = await client.post(url, headers=headers, json=payload)
    try:
        result = response.json()
    except ValueError:
        result = {"raw": response.text[:1000]}
    if response.is_error:
        log.error("WhatsApp send failed HTTP %s: %s", response.status_code, json.dumps(result)[:1000])
        raise HTTPException(status_code=502, detail={"message": "Meta rechazó el envío", "meta_response": result})
    messages = result.get("messages", [])
    wa_id = messages[0].get("id") if messages else None
    save_message(wa_id, to, "outgoing", "text", text, "sent_to_meta", result)
    return result


async def send_catalog(to: str) -> dict:
    """Abre el catálogo vinculado al número de WhatsApp en Meta."""
    if not ACCESS_TOKEN or not PHONE_NUMBER_ID or not API_VERSION or "XX" in API_VERSION:
        raise HTTPException(status_code=503, detail="Configura las credenciales de WhatsApp en .env")
    url = f"https://graph.facebook.com/{API_VERSION}/{PHONE_NUMBER_ID}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "catalog_message",
            "body": {"text": "🍽️ *Menú KITCHAN*\nExplora nuestro catálogo, elige tus productos y envíanos tu carrito para confirmar el pedido."},
            "action": {"name": "catalog_message"}
        }
    }
    async with httpx.AsyncClient(timeout=25) as client:
        response = await client.post(url, headers={"Authorization": f"Bearer {ACCESS_TOKEN}"}, json=payload)
    try:
        result = response.json()
    except ValueError:
        result = {"raw": response.text[:1000]}
    if response.is_error:
        log.error("WhatsApp catalog send failed HTTP %s: %s", response.status_code, json.dumps(result, ensure_ascii=False)[:1000])
        raise HTTPException(status_code=502, detail={"message": "Meta rechazó el envío del catálogo. Comprueba que el catálogo esté vinculado al número de WhatsApp en Commerce Manager/WhatsApp Manager.", "meta_response": result})
    messages = result.get("messages", [])
    wa_id = messages[0].get("id") if messages else None
    save_message(wa_id, to, "outgoing", "interactive_catalog", "Menú KITCHAN enviado", "sent_to_meta", result)
    return result


async def _post_message(payload: dict, saved_type: str, saved_text: str) -> dict:
    if not ACCESS_TOKEN or not PHONE_NUMBER_ID or not API_VERSION or "XX" in API_VERSION:
        raise HTTPException(status_code=503, detail="Configura las credenciales de WhatsApp en .env")
    url = f"https://graph.facebook.com/{API_VERSION}/{PHONE_NUMBER_ID}/messages"
    async with httpx.AsyncClient(timeout=25) as client:
        response = await client.post(url, headers={"Authorization": f"Bearer {ACCESS_TOKEN}"},
                                     json={"messaging_product": "whatsapp", "recipient_type": "individual", **payload})
    try:
        result = response.json()
    except ValueError:
        result = {"raw": response.text[:1000]}
    if response.is_error:
        log.error("WhatsApp send failed HTTP %s: %s", response.status_code, json.dumps(result, ensure_ascii=False)[:1000])
        raise HTTPException(status_code=502, detail={"message": "Meta rechazó el envío", "meta_response": result})
    messages = result.get("messages", [])
    save_message(messages[0].get("id") if messages else None, payload["to"], "outgoing", saved_type, saved_text, "sent_to_meta", result)
    return result


def _money(p: dict) -> str:
    return f"{p['price']:.2f} {p['currency']}".strip()


async def send_whatsapp_image(to: str, link: str, caption: str) -> dict:
    return await _post_message({"to": to, "type": "image", "image": {"link": link, "caption": caption[:1024]}},
                               "image", caption)


async def send_menu_list(to: str, products: list[dict]) -> dict:
    available = [p for p in products if p["available"]][:10]
    rows = [{"id": p["id"], "title": p["title"][:24], "description": f"{_money(p)} · {p['description']}"[:72]} for p in available]
    return await _post_message({"to": to, "type": "interactive", "interactive": {
        "type": "list",
        "body": {"text": f"☕ *Menú {ai.BUSINESS_NAME}*\nElige un producto para ver detalles o dime qué quieres pedir."},
        "action": {"button": "Ver menú", "sections": [{"title": "Productos", "rows": rows}]},
    }}, "interactive_menu", "Menú enviado")


async def send_product_card(to: str, product: dict) -> None:
    stock = "" if product["stock"] is None else f"\nQuedan {product['stock']}"
    caption = f"*{product['title']}* — {_money(product)}\n{product['description']}{stock}"
    if product["image_link"]:
        try:
            await send_whatsapp_image(to, product["image_link"], caption)
            return
        except HTTPException:
            log.warning("No se pudo enviar la imagen de %s; se envía solo texto", product["id"])
    await send_whatsapp_text(to, caption)


def create_ai_order(phone: str, first_name: str, last_name: str, payment: str, lines: list[tuple[dict, int]]) -> dict:
    items, total = [], 0.0
    for p, qty in lines:
        line_total = p["price"] * qty
        total += line_total
        items.append({"product_retailer_id": p["id"], "title": p["title"], "quantity": qty,
                      "unit_price": p["price"], "line_total": line_total, "currency": p["currency"]})
    currency = lines[0][0]["currency"] if lines else ""
    name = f"{first_name} {last_name}".strip()
    wa_order_id = f"ai:{phone}:{uuid.uuid4().hex[:8]}"
    kitchan_order_id = new_kitchan_order_id()
    with db() as conn:
        cur = conn.execute("""INSERT INTO orders(wa_order_id,customer_phone,customer_name,catalog_id,items_json,total,currency,status,raw_json,created_at,payment_method,kitchan_order_id)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""", (wa_order_id, phone, name, "sheet", json.dumps(items, ensure_ascii=False),
                                                  total, currency, "nuevo", "{}", now_iso(), payment, kitchan_order_id))
        conn.commit()
        number = cur.lastrowid
    return {"id": wa_order_id, "number": number, "customer_phone": phone, "customer_name": name, "first_name": first_name,
            "last_name": last_name, "payment_method": payment, "items": items, "total": total, "currency": currency,
            "kitchan_order_id": kitchan_order_id}


def new_kitchan_order_id() -> str:
    """Id externo del pedido en KITCHAN: opaco (sin teléfono) porque viaja en URLs y logs."""
    return f"WA-{uuid.uuid4().hex[:12].upper()}"


def _order_for_kitchan(row: sqlite3.Row) -> dict:
    order = dict(row)
    order["items"] = json.loads(order.pop("items_json") or "[]")
    return order


async def sync_order_to_kitchan(local_id: int) -> bool:
    """Envía el pedido al webhook de KITCHAN y registra el resultado. Idempotente
    (KITCHAN ignora reenvíos del mismo order_id), así que se puede reintentar."""
    with db() as conn:
        row = conn.execute("SELECT * FROM orders WHERE id=? AND kitchan_order_id<>''", (local_id,)).fetchone()
    if not row or row["kitchan_synced"]:
        return bool(row)
    order = _order_for_kitchan(row)
    if not order["items"] or order["total"] <= 0:
        ok, error = False, "Pedido sin artículos o sin total; KITCHAN lo rechazaría"
    else:
        ok, error = await kitchan.send_order(order)
    with db() as conn:
        conn.execute("UPDATE orders SET kitchan_synced=?, kitchan_attempts=kitchan_attempts+1, kitchan_error=? WHERE id=?",
                     (1 if ok else 0, error, local_id))
        conn.commit()
    if ok:
        log.info("Pedido %s enviado a KITCHAN (%s)", local_id, order["kitchan_order_id"])
    else:
        log.warning("Pedido %s no llegó a KITCHAN (se reintentará): %s", local_id, error)
    return ok


async def kitchan_retry_loop() -> None:
    """Reenvía los pedidos que KITCHAN no confirmó (caído, red, secreto mal puesto)."""
    while True:
        try:
            with db() as conn:
                pending = conn.execute(
                    "SELECT id FROM orders WHERE kitchan_synced=0 AND kitchan_order_id<>'' AND status<>'cancelado' AND kitchan_attempts<?",
                    (KITCHAN_MAX_ATTEMPTS,)).fetchall()
            for r in pending:
                await sync_order_to_kitchan(r["id"])
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("Fallo en el reintento de pedidos hacia KITCHAN")
        await asyncio.sleep(KITCHAN_RETRY_SECONDS)


def chat_history(phone: str, limit: int = 12) -> list[dict]:
    with db() as conn:
        rows = conn.execute("SELECT direction,text FROM messages WHERE phone=? AND direction IN ('incoming','outgoing') AND text<>'' ORDER BY id DESC LIMIT ?",
                            (phone, limit)).fetchall()
    history = []
    for r in reversed(rows):
        role = "user" if r["direction"] == "incoming" else "model"
        if history and history[-1]["role"] == role:
            history[-1]["text"] += "\n" + r["text"]
        else:
            history.append({"role": role, "text": r["text"]})
    while history and history[0]["role"] != "user":
        history.pop(0)
    return history


async def handle_ai_text(to: str, products: list[dict]) -> bool:
    """Responde con Gemini. False si no se pudo (el llamador usa el respaldo)."""
    result = await ai.reply(chat_history(to), products)
    if not result:
        return False
    action = result.get("action", "none")
    by_id = {p["id"].lower(): p for p in products}
    if action == "start_checkout":
        lines = [(by_id[str(i["product_id"]).lower()], max(1, int(i["quantity"])))
                 for i in result.get("items", []) if str(i.get("product_id", "")).lower() in by_id]
        if not lines:
            await send_whatsapp_text(to, result["reply"])
            return True
        problems = [f"{p['title']} está agotado" if not p["available"] else f"De {p['title']} solo quedan {p['stock']}"
                    for p, q in lines if not p["available"] or (p["stock"] is not None and p["stock"] < q)]
        if problems:
            await send_whatsapp_text(to, "Lo siento, no puedo tomar ese pedido: " + "; ".join(problems) + ". ¿Quieres ajustarlo?")
            return True
        await send_whatsapp_text(to, result["reply"])
        await start_checkout(to, [{"product_id": p["id"], "quantity": q} for p, q in lines])
        return True
    if result.get("reply"):
        await send_whatsapp_text(to, result["reply"])
    if action == "show_menu":
        await send_menu_list(to, products)
    elif action == "show_products":
        for pid in result.get("product_ids", [])[:4]:
            if pid.lower() in by_id and by_id[pid.lower()]["available"]:
                await send_product_card(to, by_id[pid.lower()])
    return True


PAYMENT_METHODS = {"pay:efectivo": "Efectivo", "pay:transferencia": "Transferencia", "pay:tarjeta": "Tarjeta"}
PAYMENT_BUTTONS = list(PAYMENT_METHODS.items())
CONFIRM_BUTTONS = [("co:confirm", "✅ Confirmar"), ("co:cancel", "❌ Cancelar")]


async def send_buttons(to: str, body: str, buttons: list[tuple[str, str]]) -> dict:
    return await _post_message({"to": to, "type": "interactive", "interactive": {
        "type": "button", "body": {"text": body[:1024]},
        "action": {"buttons": [{"type": "reply", "reply": {"id": i, "title": t[:20]}} for i, t in buttons]},
    }}, "interactive_buttons", body)


def get_checkout(phone: str) -> dict | None:
    with db() as conn:
        row = conn.execute("SELECT * FROM checkouts WHERE phone=?", (phone,)).fetchone()
    return dict(row) if row else None


def save_checkout(phone: str, **fields: Any) -> None:
    fields["updated_at"] = now_iso()
    cols = ",".join(fields)
    marks = ",".join("?" * len(fields))
    updates = ",".join(f"{k}=excluded.{k}" for k in fields)
    with db() as conn:
        conn.execute(f"INSERT INTO checkouts(phone,{cols}) VALUES(?,{marks}) ON CONFLICT(phone) DO UPDATE SET {updates}",
                     (phone, *fields.values()))
        conn.commit()


def clear_checkout(phone: str, only_step: str | None = None) -> bool:
    """Borra el checkout; True si esta llamada fue la que lo borró (evita doble confirmación)."""
    with db() as conn:
        if only_step:
            cur = conn.execute("DELETE FROM checkouts WHERE phone=? AND step=?", (phone, only_step))
        else:
            cur = conn.execute("DELETE FROM checkouts WHERE phone=?", (phone,))
        conn.commit()
    return cur.rowcount > 0


async def start_checkout(to: str, cart: list[dict]) -> None:
    save_checkout(to, step="first_name", cart_json=json.dumps(cart), first_name="", last_name="", payment="")
    await send_whatsapp_text(to, "📝 Para registrar tu pedido necesito unos datos.\n\n¿Cuál es tu *nombre*? (puedes escribir *cancelar* en cualquier momento)")


def _cart_lines(cart: list[dict], products: list[dict]) -> list[tuple[dict, int]]:
    by_id = {p["id"].lower(): p for p in products}
    return [(by_id[c["product_id"].lower()], int(c["quantity"])) for c in cart if c["product_id"].lower() in by_id]


def _summary(co: dict, lines: list[tuple[dict, int]]) -> str:
    total = sum(p["price"] * q for p, q in lines)
    currency = lines[0][0]["currency"] if lines else ""
    items = "\n".join(f"• {q} × {p['title']} — {p['price'] * q:.2f} {p['currency']}" for p, q in lines)
    return (f"🧾 *Resumen de tu pedido*\n{items}\n\n*Total:* {total:.2f} {currency}\n"
            f"*Nombre:* {co['first_name']} {co['last_name']}\n*Pago:* {co['payment']}\n\n¿Confirmas tu pedido?")


async def handle_checkout(to: str, text: str, reply_id: str, co: dict) -> None:
    t = text.strip()
    if reply_id == "co:cancel" or t.lower() in {"cancelar", "cancel", "salir"}:
        clear_checkout(to)
        await send_whatsapp_text(to, "Pedido cancelado. No se descontó nada. Escribe *menú* cuando quieras pedir de nuevo. ☕")
        return
    step = co["step"]
    if step in ("first_name", "last_name"):
        label = "nombre" if step == "first_name" else "apellido"
        if reply_id or not (2 <= len(t) <= 40) or re.search(r"\d", t):
            await send_whatsapp_text(to, f"Por favor escribe tu *{label}* con letras (2 a 40 caracteres).")
            return
        t = " ".join(w.capitalize() for w in t.split())
        if step == "first_name":
            save_checkout(to, step="last_name", first_name=t)
            await send_whatsapp_text(to, f"Gracias, {t}. ¿Cuál es tu *apellido*?")
        else:
            save_checkout(to, step="payment", last_name=t)
            await send_buttons(to, "💳 ¿Cómo vas a pagar?", PAYMENT_BUTTONS)
        return
    if step == "payment":
        if reply_id not in PAYMENT_METHODS:
            await send_buttons(to, "Elige una opción de pago:", PAYMENT_BUTTONS)
            return
        save_checkout(to, step="confirm", payment=PAYMENT_METHODS[reply_id])
        co = get_checkout(to)
        lines = _cart_lines(json.loads(co["cart_json"]), await sheets.get_products())
        await send_buttons(to, _summary(co, lines), CONFIRM_BUTTONS)
        return
    if step == "confirm":
        if reply_id != "co:confirm":
            lines = _cart_lines(json.loads(co["cart_json"]), await sheets.get_products())
            await send_buttons(to, _summary(co, lines), CONFIRM_BUTTONS)
            return
        await finalize_checkout(to, co)


async def finalize_checkout(to: str, co: dict) -> None:
    if not clear_checkout(to, only_step="confirm"):  # otra confirmación ya lo procesó
        return
    products = await sheets.get_products(force=True)
    lines = _cart_lines(json.loads(co["cart_json"]), products)
    problems = await sheets.change_stock([{"product_id": p["id"], "quantity": q} for p, q in lines], -1) if lines else ["El pedido está vacío"]
    if problems:
        await send_whatsapp_text(to, "Lo siento, no pude completar el pedido: " + "; ".join(problems) + ". Escribe *menú* para elegir de nuevo.")
        return
    order = create_ai_order(to, co["first_name"], co["last_name"], co["payment"], lines)
    await send_whatsapp_text(to, f"✅ ¡Pedido #{order['number']} recibido, {co['first_name']}! Total: {order['total']:.2f} {order['currency']} ({co['payment']}). Estamos esperando la confirmación del restaurante y te avisaremos por aquí. ☕")
    await notify_order(order)
    await sync_order_to_kitchan(order["number"])
    try:
        await sheets.append_order([
            now_iso(), order["number"], order["first_name"], order["last_name"], to,
            "; ".join(f"{i['quantity']}x {i['title']}" for i in order["items"]),
            f"{order['total']:.2f}", order["currency"], order["payment_method"], "nuevo"])
    except Exception:
        log.exception("No se pudo registrar el pedido %s en la hoja", order["number"])


def parse_order_message(message: dict, customer_phone: str, customer_name: str) -> dict | None:
    """Persist an order message generated when a customer submits their WhatsApp catalog cart."""
    if message.get("type") != "order":
        return None
    order = message.get("order", {})
    products = order.get("product_items", []) or []
    items = []
    total = 0.0
    currency = ""
    for product in products:
        try:
            qty = int(product.get("quantity", 1))
            price = float(product.get("item_price", 0))
        except (TypeError, ValueError):
            qty, price = 1, 0.0
        currency = product.get("currency", currency)
        line_total = qty * price
        total += line_total
        items.append({
            "product_retailer_id": product.get("product_retailer_id", ""),
            "title": product.get("product_retailer_id", "Producto del catálogo"),
            "quantity": qty,
            "unit_price": price,
            "line_total": line_total,
            "currency": product.get("currency", currency),
        })
    order_id = message.get("id") or f"order:{customer_phone}:{message.get('timestamp','')}"
    with db() as conn:
        cur = conn.execute("""INSERT OR IGNORE INTO orders(wa_order_id,customer_phone,customer_name,catalog_id,items_json,total,currency,status,raw_json,created_at,kitchan_order_id)
            VALUES(?,?,?,?,?,?,?,?,?,?,?)""", (
            order_id, customer_phone, customer_name, order.get("catalog_id", ""),
            json.dumps(items, ensure_ascii=False), total, currency, "nuevo",
            json.dumps(message, ensure_ascii=False), now_iso(), new_kitchan_order_id()))
        conn.commit()
        local_id = cur.lastrowid if cur.rowcount else None  # None: ya existía
    return {"id": order_id, "local_id": local_id, "customer_phone": customer_phone, "customer_name": customer_name,
            "items": items, "total": total, "currency": currency, "catalog_id": order.get("catalog_id", "")}


async def notify_order(order: dict) -> None:
    recipient = setting("order_notification_phone", ORDER_NOTIFICATION_PHONE).strip()
    if not recipient:
        log.info("Pedido guardado en el panel; no hay número de notificación configurado.")
        return
    items_text = "\n".join(f"• {i['title']} (ID {i['product_retailer_id']}) × {i['quantity']} — {i['line_total']:.2f} {i['currency']}" for i in order["items"])
    currency = order.get("currency", "")
    body = (f"🛎️ *Nuevo pedido KITCHAN*\nCliente: {order['customer_name'] or 'Sin nombre'}\nWhatsApp: {order['customer_phone']}\n\n{items_text or 'El carrito no incluye artículos legibles.'}\n\nTotal estimado: {order['total']:.2f} {currency}\nPago: {order.get('payment_method') or 'no indicado'}\nPedido: {order['id']}\nRevisa el panel para gestionar el estado.")
    try:
        await send_whatsapp_text(recipient, body)
    except Exception:
        log.exception("No se pudo enviar notificación de pedido %s", order.get("id"))


async def handle_customer_text(to: str, text: str, reply_id: str = "") -> None:
    normalized = text.strip().lower()
    co = get_checkout(to)
    if co:
        await handle_checkout(to, text, reply_id, co)
        return
    if reply_id.startswith(("co:", "pay:")):  # botón de un pedido ya procesado o cancelado
        await send_whatsapp_text(to, "Ese pedido ya fue procesado. Escribe *menú* si quieres hacer uno nuevo. ☕")
        return
    if setting("ai_enabled", "true").lower() == "true" and ai.configured():
        products = await sheets.get_products()
        if products:
            try:
                if await handle_ai_text(to, products):
                    return
            except Exception:
                log.exception("Fallo en la respuesta con IA; se usa el respaldo")
    menu_words ={"hola", "buenas", "buenos días", "buenas tardes", "buenas noches", "menu", "menú", "ver menu", "ver menú", "carta", "catalogo", "catálogo", "pedir", "hacer pedido", "inicio"}
    if normalized in menu_words or any(word in normalized for word in ("ver menu", "ver menú", "mostrar menú", "mostrar menu")):
        try:
            products = await sheets.get_products()
            if products:
                await send_menu_list(to, products)
            else:
                await send_catalog(to)
        except Exception:
            # Fallback that explains the next step without falsely claiming catalog delivery.
            await send_whatsapp_text(to, "¡Hola! 🍽️ Para ver el menú, abre el catálogo de KITCHAN desde el perfil de WhatsApp Business. Si no aparece, estamos revisando la conexión del catálogo. También puedes escribir MENÚ para intentarlo de nuevo.")
        return
    if normalized in {"ayuda", "help", "opciones"}:
        await send_whatsapp_text(to, "¡Hola! Soy el asistente de KITCHAN. Escribe *MENÚ* para ver los productos del catálogo de WhatsApp. Añade productos al carrito y envía el pedido desde WhatsApp; cuando lo recibamos, te confirmaremos la recepción.")
        return
    if setting("auto_reply_enabled", "false").lower() == "true":
        await send_whatsapp_text(to, "¡Gracias por escribir a KITCHAN! 🍽️ Escribe *MENÚ* para ver los productos y elegir lo que deseas pedir.")


async def auto_reply(to: str) -> None:
    if setting("auto_reply_enabled", "false").lower() != "true":
        return
    reply = setting("auto_reply_text", AUTO_REPLY_TEXT).strip()
    if not reply:
        return
    try:
        await send_whatsapp_text(to, reply)
    except Exception:
        log.exception("Auto reply failed for phone ending %s", to[-4:])


def verify_signature(raw_body: bytes, signature: str) -> bool:
    # En modo Cloud API real, se exige siempre el secreto de la aplicación.
    if not APP_SECRET or not signature.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(APP_SECRET.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


@app.get("/", include_in_schema=False)
async def dashboard() -> FileResponse:
    return FileResponse(BASE_DIR / "app" / "static" / "index.html")


@app.get("/health")
async def health() -> dict:
    return {"ok": True, "service": "kitchan-whatsapp-local", "timestamp": now_iso()}


@app.get("/webhook", response_class=PlainTextResponse)
async def verify_webhook(request: Request):
    q = request.query_params
    if q.get("hub.mode") == "subscribe" and VERIFY_TOKEN and hmac.compare_digest(q.get("hub.verify_token", ""), VERIFY_TOKEN):
        return PlainTextResponse(q.get("hub.challenge", ""), status_code=200)
    raise HTTPException(status_code=403, detail="Webhook verification failed. Revisa WHATSAPP_VERIFY_TOKEN.")


@app.post("/webhook")
async def receive_webhook(request: Request, background_tasks: BackgroundTasks):
    raw_body = await request.body()
    if not verify_signature(raw_body, request.headers.get("x-hub-signature-256", "")):
        raise HTTPException(status_code=401, detail="Firma de Meta inválida. Revisa WHATSAPP_APP_SECRET y la cabecera X-Hub-Signature-256.")
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="JSON inválido")

    # Confirmar recepción rápido; los eventos se guardan antes de devolver 200.
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            if change.get("field") != "messages":
                continue
            value = change.get("value", {})
            contacts = {c.get("wa_id"): c.get("profile", {}).get("name", "") for c in value.get("contacts", [])}
            for message in value.get("messages", []) or []:
                phone = message.get("from", "")
                msg_type = message.get("type", "unknown")
                text = ""
                reply_id = ""
                if msg_type == "text":
                    text = message.get("text", {}).get("body", "")
                elif msg_type == "button":
                    text = message.get("button", {}).get("text", "")
                elif msg_type == "interactive":
                    interactive = message.get("interactive", {})
                    reply = interactive.get("button_reply") or interactive.get("list_reply") or {}
                    reply_id = reply.get("id", "")
                    text = reply.get("title", "")
                    if interactive.get("list_reply"):
                        text = f"Me interesa {text} (código {reply.get('id', '')}). Muéstramelo con su foto y precio."
                elif msg_type == "image":
                    text = "[Imagen recibida] " + message.get("image", {}).get("caption", "")
                elif msg_type == "audio":
                    text = "[Audio recibido]"
                elif msg_type == "document":
                    text = "[Documento recibido] " + message.get("document", {}).get("filename", "")
                elif msg_type == "video":
                    text = "[Video recibido] " + message.get("video", {}).get("caption", "")
                elif msg_type == "sticker":
                    text = "[Sticker recibido]"
                else:
                    text = f"[{msg_type} recibido]"
                customer_name = contacts.get(phone, "")
                inserted = save_message(message.get("id"), phone, "incoming", msg_type, text, "received", {"message": message, "contact_name": customer_name})
                if inserted:
                    log.info("Mensaje entrante: tipo=%s, teléfono=***%s, id=%s", msg_type, phone[-4:], message.get("id", ""))
                    if phone and msg_type in ("text", "interactive", "button") and text:
                        background_tasks.add_task(handle_customer_text, phone, text, reply_id)
                    elif phone and msg_type == "order":
                        order = parse_order_message(message, phone, customer_name)
                        if order:
                            log.info("Pedido nuevo recibido: teléfono=***%s, artículos=%s", phone[-4:], len(order["items"]))
                            background_tasks.add_task(notify_order, order)
                            if order["local_id"]:
                                background_tasks.add_task(sync_order_to_kitchan, order["local_id"])
                            background_tasks.add_task(send_whatsapp_text, phone, "✅ ¡Recibimos tu pedido! El equipo de KITCHAN revisará los productos y te confirmará los detalles en breve.")

            for status in value.get("statuses", []) or []:
                recipient = status.get("recipient_id", "")
                status_text = status.get("status", "unknown")
                status_id = status.get("id", "")
                save_message(f"status:{status_id}:{status_text}:{status.get('timestamp','')}", recipient, "status", "status", f"Mensaje {status_text}", status_text, status)
    return {"ok": True}


class SendRequest(BaseModel):
    to: str = Field(min_length=8, max_length=20, description="Teléfono del cliente con código de país, solo dígitos")
    text: str = Field(min_length=1, max_length=4096)


class SettingsRequest(BaseModel):
    auto_reply_enabled: bool
    auto_reply_text: str = Field(min_length=1, max_length=1000)
    order_notification_phone: str = Field(default="", max_length=20)


@app.get("/api/messages")
async def list_messages(limit: int = 200, phone: str | None = None) -> dict:
    limit = max(1, min(limit, 500))
    with db() as conn:
        if phone:
            rows = conn.execute("SELECT * FROM messages WHERE phone=? ORDER BY id DESC LIMIT ?", (phone, limit)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM messages ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    result = []
    for row in reversed(rows):
        item = dict(row)
        try:
            item["raw"] = json.loads(item.pop("raw_json"))
        except Exception:
            item["raw"] = {}
            item.pop("raw_json", None)
        result.append(item)
    return {"messages": result}


@app.post("/api/send")
async def send_message(body: SendRequest) -> dict:
    to = body.to.replace("+", "").replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if not to.isdigit():
        raise HTTPException(status_code=422, detail="Usa el número con código de país, solo dígitos; por ejemplo 5939XXXXXXXX")
    result = await send_whatsapp_text(to, body.text.strip())
    return {"ok": True, "meta": result}


@app.get("/api/settings")
async def get_settings() -> dict:
    return {
        "auto_reply_enabled": setting("auto_reply_enabled", "false").lower() == "true",
        "auto_reply_text": setting("auto_reply_text", AUTO_REPLY_TEXT),
        "order_notification_phone": setting("order_notification_phone", ORDER_NOTIFICATION_PHONE),
    }


@app.put("/api/settings")
async def update_settings(body: SettingsRequest) -> dict:
    with db() as conn:
        conn.execute("INSERT INTO settings(key,value) VALUES('auto_reply_enabled',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", ("true" if body.auto_reply_enabled else "false",))
        conn.execute("INSERT INTO settings(key,value) VALUES('auto_reply_text',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (body.auto_reply_text.strip(),))
        phone = body.order_notification_phone.replace("+", "").replace(" ", "").replace("-", "").replace("(", "").replace(")", "").strip()
        if phone and not phone.isdigit():
            raise HTTPException(status_code=422, detail="El teléfono de notificación debe llevar solo dígitos con código de país, por ejemplo 5939XXXXXXXX")
        conn.execute("INSERT INTO settings(key,value) VALUES('order_notification_phone',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (phone,))
        conn.commit()
    return await get_settings()


class OrderStatusRequest(BaseModel):
    status: str = Field(pattern="^(nuevo|confirmado|preparando|listo|entregado|cancelado)$")


@app.get("/api/orders")
async def list_orders(limit: int = 100, status: str | None = None) -> dict:
    limit = max(1, min(limit, 300))
    with db() as conn:
        if status:
            rows = conn.execute("SELECT * FROM orders WHERE status=? ORDER BY id DESC LIMIT ?", (status, limit)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM orders ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    orders = []
    for row in rows:
        item = dict(row)
        item["items"] = json.loads(item.pop("items_json") or "[]")
        item.pop("raw_json", None)
        orders.append(item)
    return {"orders": orders}


@app.patch("/api/orders/{order_id}/status")
async def update_order_status(order_id: int, body: OrderStatusRequest) -> dict:
    with db() as conn:
        prev = conn.execute("SELECT status,wa_order_id,items_json FROM orders WHERE id=?", (order_id,)).fetchone()
        if not prev:
            raise HTTPException(status_code=404, detail="Pedido no encontrado")
        conn.execute("UPDATE orders SET status=? WHERE id=?", (body.status, order_id))
        conn.commit()
        row = conn.execute("SELECT id,status FROM orders WHERE id=?", (order_id,)).fetchone()
    if body.status == "cancelado" and prev["status"] != "cancelado":
        await restock_if_bot_order(prev)
    return {"ok": True, "order": dict(row)}


async def restock_if_bot_order(order: sqlite3.Row) -> None:
    """Solo los pedidos creados por el bot descontaron stock de la hoja."""
    if (order["wa_order_id"] or "").startswith("ai:"):
        items = [{"product_id": i["product_retailer_id"], "quantity": i["quantity"]} for i in json.loads(order["items_json"] or "[]")]
        await sheets.change_stock(items, +1)


# Decisión del restaurante en KITCHAN -> (estado local, mensaje al cliente)
KITCHAN_STATUS = {
    "ACCEPTED": ("preparando", "✅ ¡Tu pedido #{n} fue aceptado! Ya lo estamos preparando. ☕"),
    "READY": ("listo", "🎉 ¡Tu pedido #{n} está listo!"),
    "REJECTED": ("cancelado", "😔 Lo sentimos, el restaurante no pudo aceptar tu pedido #{n}.{reason}"),
    "CANCELLED": ("cancelado", "😔 Tu pedido #{n} fue cancelado por el restaurante.{reason}"),
}


class KitchanStatusRequest(BaseModel):
    status: str = Field(pattern="^(ACCEPTED|READY|REJECTED|CANCELLED)$")
    reason: str | None = Field(default=None, max_length=500)


@app.post("/api/kitchan/orders/{kitchan_order_id}/status")
async def kitchan_order_status(kitchan_order_id: str, request: Request) -> dict:
    """KITCHAN avisa lo que decidió el restaurante; el bot se lo cuenta al cliente por WhatsApp."""
    raw_body = await request.body()
    if not kitchan.verify(raw_body, request.headers.get(kitchan.HEADER, "")):
        raise HTTPException(status_code=401, detail="Firma de KITCHAN inválida. Revisa KITCHAN_BOT_SECRET.")
    try:
        body = KitchanStatusRequest(**json.loads(raw_body))
    except Exception:
        raise HTTPException(status_code=422, detail="Cuerpo inválido")
    with db() as conn:
        order = conn.execute("SELECT * FROM orders WHERE kitchan_order_id=?", (kitchan_order_id,)).fetchone()
    if not order:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    new_status, template = KITCHAN_STATUS[body.status]
    if order["status"] == new_status or order["status"] == "cancelado":
        return {"ok": True, "duplicate": True}  # reenvío o pedido ya cancelado: no repetir el mensaje
    with db() as conn:
        conn.execute("UPDATE orders SET status=? WHERE id=?", (new_status, order["id"]))
        conn.commit()
    if new_status == "cancelado":
        await restock_if_bot_order(order)
    reason = f" Motivo: {body.reason.strip()}" if body.reason and body.reason.strip() else ""
    await send_whatsapp_text(order["customer_phone"], template.format(n=order["id"], reason=reason))
    return {"ok": True}


class StockRequest(BaseModel):
    stock: int = Field(ge=0, le=100000)


@app.get("/api/products")
async def api_products(refresh: bool = False) -> dict:
    return {"products": await sheets.get_products(force=refresh), "stock_writable": sheets.writable()}


@app.patch("/api/products/{product_id}/stock")
async def api_set_stock(product_id: str, body: StockRequest) -> dict:
    try:
        return {"ok": True, "product": await sheets.set_stock(product_id, body.stock)}
    except KeyError:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))


@app.post("/api/products/init-stock")
async def api_init_stock(default: int = 20) -> dict:
    try:
        await sheets.init_stock_column(max(0, default))
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return {"ok": True, "products": await sheets.get_products()}


@app.put("/api/ai")
async def api_toggle_ai(enabled: bool) -> dict:
    with db() as conn:
        conn.execute("INSERT INTO settings(key,value) VALUES('ai_enabled',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", ("true" if enabled else "false",))
        conn.commit()
    return {"ai_enabled": enabled}


@app.post("/api/catalog/send")
async def api_send_catalog(body: SendRequest) -> dict:
    to = body.to.replace("+", "").replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if not to.isdigit():
        raise HTTPException(status_code=422, detail="Usa el teléfono con código de país, solo dígitos")
    result = await send_catalog(to)
    return {"ok": True, "meta": result}


@app.get("/api/status")
async def status() -> dict:
    return {
        "configured": bool(ACCESS_TOKEN and PHONE_NUMBER_ID and API_VERSION and "XX" not in API_VERSION and VERIFY_TOKEN and APP_SECRET),
        "phone_number_id_present": bool(PHONE_NUMBER_ID),
        "token_present": bool(ACCESS_TOKEN),
        "app_secret_present": bool(APP_SECRET),
        "api_version": API_VERSION or "no configurada",
        "auto_reply_enabled": setting("auto_reply_enabled", "false").lower() == "true",
        "ai_enabled": setting("ai_enabled", "true").lower() == "true",
        "gemini_key_present": ai.configured(),
        "sheet_stock_writable": sheets.writable(),
        "order_notification_phone_configured": bool(setting("order_notification_phone", ORDER_NOTIFICATION_PHONE)),
        "kitchan_configured": kitchan.configured(),
        "kitchan_url": kitchan.KITCHAN_API_URL,
        "orders_pending_kitchan": pending_kitchan_count(),
        "database": str(DATABASE_PATH),
    }


def pending_kitchan_count() -> int:
    with db() as conn:
        return conn.execute("SELECT COUNT(*) FROM orders WHERE kitchan_synced=0 AND kitchan_order_id<>'' AND status<>'cancelado'").fetchone()[0]
