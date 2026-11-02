"""Menú y stock desde Google Sheets.

Lectura: API de Sheets con cuenta de servicio; si no hay cuenta de servicio, exportación CSV
(solo lectura, el stock no se controla). Escritura de stock: solo con cuenta de servicio.
"""
import asyncio
import base64
import csv
import io
import json
import logging
import os
import re
import time
from pathlib import Path

import httpx

log = logging.getLogger("kitchan_whatsapp.sheets")

BASE_DIR = Path(__file__).resolve().parent.parent
SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "1lF3k8HNyf5nhSKbZaeZqFihyGHHegpj5Pqs7AOUPlqw").strip()
SA_PATH = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
CACHE_TTL = int(os.getenv("SHEET_CACHE_SECONDS", "60"))
SCOPE = "https://www.googleapis.com/auth/spreadsheets"

_lock = asyncio.Lock()
_cache: dict = {"at": 0.0, "products": [], "grid": None}
_token: dict = {"value": "", "exp": 0.0}


def _sa() -> dict | None:
    if not SA_PATH:
        return None
    path = Path(SA_PATH)
    if not path.is_absolute():
        path = BASE_DIR / path
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def writable() -> bool:
    return _sa() is not None


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


async def _access_token() -> str:
    if _token["value"] and time.time() < _token["exp"] - 60:
        return _token["value"]
    sa = _sa()
    if not sa:
        raise RuntimeError("Falta GOOGLE_SERVICE_ACCOUNT_JSON")
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding

    now = int(time.time())
    header = _b64(json.dumps({"alg": "RS256", "typ": "JWT"}).encode())
    claims = _b64(json.dumps({"iss": sa["client_email"], "scope": SCOPE, "aud": sa["token_uri"], "iat": now, "exp": now + 3600}).encode())
    key = serialization.load_pem_private_key(sa["private_key"].encode(), password=None)
    signature = key.sign(f"{header}.{claims}".encode(), padding.PKCS1v15(), hashes.SHA256())
    assertion = f"{header}.{claims}.{_b64(signature)}"
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(sa["token_uri"], data={"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": assertion})
    r.raise_for_status()
    data = r.json()
    _token.update(value=data["access_token"], exp=now + int(data.get("expires_in", 3600)))
    return _token["value"]


async def _api(method: str, path: str, **kwargs) -> dict:
    token = await _access_token()
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.request(method, f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}{path}",
                                 headers={"Authorization": f"Bearer {token}"}, **kwargs)
    if r.is_error:
        raise RuntimeError(f"Sheets API {r.status_code}: {r.text[:300]}")
    return r.json()


async def _tab_title() -> str:
    meta = await _api("GET", "?fields=sheets.properties.title")
    return meta["sheets"][0]["properties"]["title"]


def _col(n: int) -> str:
    s = ""
    n += 1
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


async def _read_grid() -> tuple[list[list[str]], str | None]:
    if writable():
        tab = await _tab_title()
        data = await _api("GET", f"/values/'{tab}'!A1:Z500")
        return data.get("values", []), tab
    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        r = await client.get(f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv")
    r.raise_for_status()
    return list(csv.reader(io.StringIO(r.text))), None


def _parse_price(raw: str) -> tuple[float, str]:
    m = re.search(r"([\d.,]+)\s*([A-Za-z]{3})?", raw or "")
    if not m:
        return 0.0, ""
    return float(m.group(1).replace(",", ".")), (m.group(2) or "USD").upper()


def _build(grid: list[list[str]]) -> list[dict]:
    if not grid:
        return []
    header = [h.strip().lower() for h in grid[0]]
    products = []
    for n, row in enumerate(grid[1:], start=2):
        rec = {h: (row[i].strip() if i < len(row) else "") for i, h in enumerate(header)}
        if not rec.get("id"):
            continue
        price, currency = _parse_price(rec.get("price", ""))
        stock_raw = rec.get("stock", "")
        stock = int(float(stock_raw)) if re.fullmatch(r"\d+(\.0+)?", stock_raw or "") else None
        in_stock = (stock > 0) if stock is not None else rec.get("availability", "in stock").lower() == "in stock"
        products.append({
            "id": rec["id"], "title": rec.get("title", ""), "description": rec.get("description", ""),
            "price": price, "currency": currency, "image_link": rec.get("image_link", ""),
            "stock": stock, "available": in_stock, "row": n,
        })
    return products


async def get_products(force: bool = False) -> list[dict]:
    if not force and _cache["products"] and time.time() - _cache["at"] < CACHE_TTL:
        return _cache["products"]
    try:
        grid, tab = await _read_grid()
    except Exception:
        log.exception("No se pudo leer la hoja")
        return _cache["products"]
    _cache.update(at=time.time(), products=_build(grid), grid=(grid, tab))
    return _cache["products"]


async def find(product_id: str) -> dict | None:
    return next((p for p in await get_products() if p["id"].lower() == product_id.lower()), None)


async def _write_stock(product: dict, stock: int, header: list[str], tab: str) -> None:
    lower = [h.strip().lower() for h in header]
    updates = [{"range": f"'{tab}'!{_col(lower.index('stock'))}{product['row']}", "values": [[stock]]}]
    if "availability" in lower:
        updates.append({"range": f"'{tab}'!{_col(lower.index('availability'))}{product['row']}",
                        "values": [["in stock" if stock > 0 else "out of stock"]]})
    await _api("POST", "/values:batchUpdate", json={"valueInputOption": "USER_ENTERED", "data": updates})


async def init_stock_column(default: int) -> None:
    """Crea la columna 'stock' con un valor inicial para todos los productos."""
    async with _lock:
        grid, tab = await _read_grid()
        if not tab:
            raise RuntimeError("Se necesita la cuenta de servicio para escribir en la hoja")
        header = [h.strip().lower() for h in grid[0]]
        if "stock" in header:
            return
        col = _col(len(header))
        rows = [["stock"]] + [[default] for r in grid[1:] if r and r[0].strip()]
        await _api("PUT", f"/values/'{tab}'!{col}1:{col}{len(rows)}?valueInputOption=USER_ENTERED", json={"values": rows})
        await get_products(force=True)


async def set_stock(product_id: str, stock: int) -> dict:
    async with _lock:
        await get_products(force=True)
        grid, tab = _cache["grid"]
        product = next((p for p in _cache["products"] if p["id"].lower() == product_id.lower()), None)
        if not product:
            raise KeyError(product_id)
        if not tab or "stock" not in [h.strip().lower() for h in grid[0]]:
            raise RuntimeError("La hoja no tiene columna 'stock' o falta la cuenta de servicio")
        await _write_stock(product, max(0, stock), grid[0], tab)
        await get_products(force=True)
        return await find(product_id)


async def change_stock(items: list[dict], sign: int) -> list[str]:
    """Descuenta (sign=-1) o repone (sign=+1) stock. Devuelve los problemas; no cambia nada si hay alguno al descontar."""
    async with _lock:
        await get_products(force=True)
        grid, tab = _cache["grid"]
        by_id = {p["id"].lower(): p for p in _cache["products"]}
        controlled = tab is not None and "stock" in [h.strip().lower() for h in grid[0]]
        problems, plan = [], []
        for it in items:
            p = by_id.get(str(it["product_id"]).lower())
            if not p:
                problems.append(f"Producto {it['product_id']} no existe")
                continue
            if sign < 0 and not p["available"]:
                problems.append(f"{p['title']} está agotado")
            elif p["stock"] is not None and sign < 0 and p["stock"] < it["quantity"]:
                problems.append(f"De {p['title']} solo quedan {p['stock']}")
            elif p["stock"] is not None:
                plan.append((p, p["stock"] + sign * it["quantity"]))
        if problems and sign < 0:
            return problems
        if controlled:
            for p, new in plan:
                await _write_stock(p, max(0, new), grid[0], tab)
            await get_products(force=True)
        return problems


ORDERS_TAB = os.getenv("SHEET_ORDERS_TAB", "Pedidos")
ORDERS_HEADER = ["Fecha", "Pedido", "Nombre", "Apellido", "Teléfono", "Productos", "Total", "Moneda", "Método de pago", "Estado"]


async def append_order(row: list) -> bool:
    """Añade un pedido a la hoja 'Pedidos' (la crea con encabezados si no existe)."""
    if not writable():
        return False
    async with _lock:
        meta = await _api("GET", "?fields=sheets.properties.title")
        if ORDERS_TAB not in [x["properties"]["title"] for x in meta["sheets"]]:
            await _api("POST", ":batchUpdate", json={"requests": [{"addSheet": {"properties": {"title": ORDERS_TAB}}}]})
            await _api("PUT", f"/values/'{ORDERS_TAB}'!A1?valueInputOption=RAW", json={"values": [ORDERS_HEADER]})
        await _api("POST", f"/values/'{ORDERS_TAB}'!A1:append?valueInputOption=RAW&insertDataOption=INSERT_ROWS",
                   json={"values": [[str(v) for v in row]]})
    return True
