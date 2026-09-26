"""Simulador de PedidosYa (Delivery Hero Integration Middleware) para probar
KITCHAN sin la tienda de prueba real.

Hace lo mismo que el Middleware: arma el body de "Dispatch Order", firma un
JWT HS512 con el claim `service: middleware` usando PEDIDOSYA_JWT_SECRET
(lo que valida jwt_validator.py) y hace POST /order/{remoteId} a KITCHAN.

Uso (desde kitchan-backend/):
    python scripts/simulador_pedidosya/simular_pedidosya.py nuevo-pedido
    python scripts/simulador_pedidosya/simular_pedidosya.py nuevo-pedido --order-id PYA-TEST-1
    python scripts/simulador_pedidosya/simular_pedidosya.py jwt-invalido

Lee del .env: PEDIDOSYA_JWT_SECRET y PEDIDOSYA_REMOTE_ID_MAP (usa el primer
remoteId del mapa si no se pasa --remote-id). KITCHAN_URL es opcional
(por defecto http://127.0.0.1:8000).
"""

import argparse
import json
import os
import sys
import time
import uuid

import httpx
from dotenv import load_dotenv
from jose import jwt

DISPATCH_BASE = "/api/v1/integraciones/pedidosya/order"

# Mismos productos de prueba que el simulador de Rappi.
MENU_PRUEBA = [
    {"name": "Hamburguesa clásica", "price": 6.5},
    {"name": "Papas fritas medianas", "price": 2.75},
    {"name": "Coca-Cola 500 ml", "price": 1.5},
]


def _jwt(secret: str, service: str = "middleware") -> str:
    ahora = int(time.time())
    return jwt.encode(
        {"service": service, "iat": ahora, "exp": ahora + 300},
        secret,
        algorithm="HS512",
    )


def _remote_id_por_defecto() -> str | None:
    try:
        mapa = json.loads(os.getenv("PEDIDOSYA_REMOTE_ID_MAP", "{}"))
    except json.JSONDecodeError:
        return None
    return next(iter(mapa), None)


def _payload_pedido(order_id: str) -> dict:
    items = [
        {**MENU_PRUEBA[0], "quantity": 2, "notes": "Sin cebolla"},
        {**MENU_PRUEBA[1], "quantity": 1},
        {**MENU_PRUEBA[2], "quantity": 2},
    ]
    return {
        "orderId": order_id,
        "customerName": "Cliente Simulado PYA",
        "totalPrice": round(sum(i["price"] * i["quantity"] for i in items), 2),
        "items": items,
        "notes": "Pedido generado por el simulador local",
    }


def main() -> None:
    load_dotenv(".env")

    parser = argparse.ArgumentParser(description="Simulador de PedidosYa")
    parser.add_argument("evento", choices=["nuevo-pedido", "jwt-invalido"])
    parser.add_argument("--order-id", help="ID del pedido (por defecto uno aleatorio)")
    parser.add_argument("--remote-id", help="remoteId del vendor (por defecto el 1º de PEDIDOSYA_REMOTE_ID_MAP)")
    args = parser.parse_args()

    secret = os.getenv("PEDIDOSYA_JWT_SECRET")
    if not secret:
        print("❌ Falta PEDIDOSYA_JWT_SECRET en el .env (debe ser el mismo que usa el backend).")
        sys.exit(1)

    remote_id = args.remote_id or _remote_id_por_defecto()
    if not remote_id:
        print("❌ Falta --remote-id o un vendor en PEDIDOSYA_REMOTE_ID_MAP del .env.")
        sys.exit(1)

    base = os.getenv("KITCHAN_URL", "http://127.0.0.1:8000").rstrip("/")
    order_id = args.order_id or f"PYA-SIM-{uuid.uuid4().hex[:8].upper()}"
    payload = _payload_pedido(order_id)

    if args.evento == "nuevo-pedido":
        token = _jwt(secret)
        print(f"🛵 Nuevo pedido PedidosYa {order_id} para remoteId {remote_id} (total {payload['totalPrice']})")
    else:  # jwt-invalido: KITCHAN debe responder 401 y no crear el pedido
        token = _jwt("secreto-incorrecto")
        print("🕵️ Enviando pedido con JWT falso (se espera 401)")

    url = f"{base}{DISPATCH_BASE}/{remote_id}"
    try:
        respuesta = httpx.post(url, json=payload, headers={"Authorization": f"Bearer {token}"}, timeout=15)
    except httpx.ConnectError:
        print(f"❌ No se pudo conectar a {url}. ¿Está corriendo el backend?")
        sys.exit(1)
    print(f"📨 POST {url}")
    print(f"   -> {respuesta.status_code} {respuesta.text}")


if __name__ == "__main__":
    main()
