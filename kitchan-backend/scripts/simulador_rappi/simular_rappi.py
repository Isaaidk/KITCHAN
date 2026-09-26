"""Simulador de Rappi (emisor de webhooks) para probar KITCHAN sin acceso DEV.

Hace lo mismo que Rappi: arma el JSON del evento, lo firma con
`Rappi-Signature: t=<timestamp>,sign=<hmac>` (HMAC-SHA256 sobre
"<t>.<body>", igual que valida signature_validator.py) y lo envía a los
webhooks de KITCHAN.

Uso (desde kitchan-backend/):
    python scripts/simulador_rappi/simular_rappi.py nuevo-pedido
    python scripts/simulador_rappi/simular_rappi.py nuevo-pedido --order-id RAPPI-TEST-1
    python scripts/simulador_rappi/simular_rappi.py cancelar --order-id RAPPI-TEST-1
    python scripts/simulador_rappi/simular_rappi.py firma-invalida

Lee del .env: RAPPI_WEBHOOK_SECRET y RAPPI_STORE_ID_MAP (usa la primera
tienda del mapa si no se pasa --store-id). KITCHAN_URL es opcional
(por defecto http://127.0.0.1:8000).
"""

import argparse
import hashlib
import hmac
import json
import os
import sys
import time
import uuid

import httpx
from dotenv import load_dotenv

WEBHOOK_BASE = "/api/v1/integraciones/rappi/webhook"

# Menú de prueba (precios en unidades de moneda, ver TODO de domain/models.py
# sobre centavos vs unidades: hay que confirmarlo con un payload real).
MENU_PRUEBA = [
    {"id": "1001", "sku": "HAMB-CLASICA", "name": "Hamburguesa clásica", "price": 6.5},
    {"id": "1002", "sku": "PAPAS-M", "name": "Papas fritas medianas", "price": 2.75},
    {"id": "1003", "sku": "COCA-500", "name": "Coca-Cola 500 ml", "price": 1.5},
]


def _firmar(secret: str, body: bytes) -> str:
    timestamp = str(int(time.time() * 1000))
    mensaje = timestamp.encode("utf-8") + b"." + body
    firma = hmac.new(secret.encode("utf-8"), mensaje, hashlib.sha256).hexdigest()
    return f"t={timestamp},sign={firma}"


def _store_id_por_defecto() -> str | None:
    try:
        mapa = json.loads(os.getenv("RAPPI_STORE_ID_MAP", "{}"))
    except json.JSONDecodeError:
        return None
    return next(iter(mapa), None)


def _payload_nuevo_pedido(order_id: str, store_id: str) -> dict:
    items = [
        {**MENU_PRUEBA[0], "quantity": 2, "comments": "Sin cebolla"},
        {**MENU_PRUEBA[1], "quantity": 1, "comments": None},
        {**MENU_PRUEBA[2], "quantity": 2, "comments": None},
    ]
    total = round(sum(i["price"] * i["quantity"] for i in items), 2)
    return {
        "order_detail": {
            "order_id": order_id,
            "cooking_time": 15,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "delivery_method": "delivery",
            "payment_method": "cc",
            "items": items,
            "totals": {"total_order": total},
        },
        "customer": {"first_name": "Cliente", "last_name": "Simulado"},
        "store": {"internal_id": store_id, "external_id": "KITCHAN", "name": "Tienda simulada"},
    }


def _enviar(url: str, body: bytes, firma: str) -> None:
    # Se envía exactamente el mismo body que se firmó.
    headers = {"Content-Type": "application/json", "Rappi-Signature": firma}
    try:
        respuesta = httpx.post(url, content=body, headers=headers, timeout=15)
    except httpx.ConnectError:
        print(f"❌ No se pudo conectar a {url}. ¿Está corriendo el backend?")
        sys.exit(1)
    print(f"📨 POST {url}")
    print(f"   -> {respuesta.status_code} {respuesta.text}")


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(description="Simulador de webhooks de Rappi")
    parser.add_argument("evento", choices=["nuevo-pedido", "cancelar", "firma-invalida"])
    parser.add_argument("--order-id", help="ID del pedido (por defecto uno aleatorio)")
    parser.add_argument("--store-id", help="ID de tienda Rappi (por defecto la 1ª de RAPPI_STORE_ID_MAP)")
    args = parser.parse_args()

    secret = os.getenv("RAPPI_WEBHOOK_SECRET")
    if not secret:
        print("❌ Falta RAPPI_WEBHOOK_SECRET en el .env (debe ser el mismo que usa el backend).")
        sys.exit(1)

    store_id = args.store_id or _store_id_por_defecto()
    if not store_id:
        print("❌ Falta --store-id o una tienda en RAPPI_STORE_ID_MAP del .env.")
        sys.exit(1)

    base = os.getenv("KITCHAN_URL", "http://127.0.0.1:8000").rstrip("/")
    order_id = args.order_id or f"RAPPI-SIM-{uuid.uuid4().hex[:8].upper()}"

    if args.evento == "nuevo-pedido":
        payload = _payload_nuevo_pedido(order_id, store_id)
        body = json.dumps(payload).encode("utf-8")
        print(f"🛵 Nuevo pedido Rappi {order_id} para la tienda {store_id} "
              f"(total {payload['order_detail']['totals']['total_order']})")
        _enviar(f"{base}{WEBHOOK_BASE}/new-order", body, _firmar(secret, body))

    elif args.evento == "cancelar":
        if not args.order_id:
            print("❌ Para cancelar hay que indicar --order-id.")
            sys.exit(1)
        payload = {"event": "canceled_with_charge", "order_id": order_id, "store_id": store_id}
        body = json.dumps(payload).encode("utf-8")
        print(f"🛑 Cancelación Rappi del pedido {order_id}")
        _enviar(f"{base}{WEBHOOK_BASE}/order-cancel", body, _firmar(secret, body))

    else:  # firma-invalida: KITCHAN debe responder 403 y no crear el pedido
        payload = _payload_nuevo_pedido(order_id, store_id)
        body = json.dumps(payload).encode("utf-8")
        print("🕵️ Enviando pedido con firma falsa (se espera 403)")
        _enviar(f"{base}{WEBHOOK_BASE}/new-order", body, _firmar("secreto-incorrecto", body))


if __name__ == "__main__":
    main()
