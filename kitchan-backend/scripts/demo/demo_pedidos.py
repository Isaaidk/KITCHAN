"""Menú interactivo para la demo de KITCHAN.

Envía pedidos de Rappi y PedidosYa a KITCHAN con clientes y productos
realistas, usando la misma firma (Rappi-Signature) y el mismo JWT
(Integration Middleware) que usan las plataformas reales. Reutiliza la lógica
de los simuladores de scripts/simulador_rappi y scripts/simulador_pedidosya.

Uso (desde kitchan-backend/):
    python scripts/demo/demo_pedidos.py
"""

import json
import os
import sys
import uuid
from pathlib import Path

import httpx
from dotenv import load_dotenv

SCRIPTS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS / "simulador_rappi"))
sys.path.insert(0, str(SCRIPTS / "simulador_pedidosya"))

import simular_pedidosya  # noqa: E402
import simular_rappi  # noqa: E402

KITCHAN_URL = "http://127.0.0.1:8000"

PEDIDOS_RAPPI = [
    (
        ("María", "Torres"),
        [
            ("Combo hamburguesa clásica", 1, 8.50, "Sin cebolla"),
            ("Papas fritas medianas", 1, 2.75, None),
            ("Coca-Cola 500 ml", 1, 1.50, None),
        ],
    ),
    (
        ("Andrés", "Vega"),
        [("Hot dog especial", 2, 4.25, "Extra salsa"), ("Limonada", 2, 2.00, None)],
    ),
    (
        ("Lucía", "Paredes"),
        [("Nuggets x10", 1, 5.90, None), ("Papas fritas grandes", 1, 3.25, None)],
    ),
]

PEDIDOS_PEDIDOSYA = [
    (
        "Camila Ruiz",
        [("Alitas BBQ x8", 1, 7.90, "Bien cocidas"), ("Limonada", 1, 2.00, None)],
    ),
    (
        "Diego Mora",
        [
            ("Combo hamburguesa doble", 2, 10.50, None),
            ("Coca-Cola 500 ml", 2, 1.50, None),
        ],
    ),
    ("Sofía Andrade", [("Hamburguesa clásica", 1, 6.50, "Sin tomate")]),
]

estado = {
    "rappi": 0,
    "pedidosya": 0,
    "ultimo_rappi": None,
    # Último pedido enviado (cuerpo exacto), para poder reenviarlo igual.
    "ultimo_rappi_body": None,
    "ultimo_pedidosya": None,
}


def _post(url: str, body: bytes, headers: dict) -> httpx.Response | None:
    try:
        return httpx.post(url, content=body, headers=headers, timeout=15)
    except httpx.ConnectError:
        print("  ❌ KITCHAN no responde. ¿Está corriendo iniciar_demo.cmd?")
        return None


def _resultado(respuesta: httpx.Response | None, esperado: int) -> None:
    if respuesta is None:
        return
    icono = "✅" if respuesta.status_code == esperado else "⚠️"
    print(f"  {icono} KITCHAN respondió {respuesta.status_code} {respuesta.text}")


def pedido_rappi() -> None:
    (nombre, apellido), items = PEDIDOS_RAPPI[estado["rappi"] % len(PEDIDOS_RAPPI)]
    estado["rappi"] += 1
    order_id = f"RAPPI-{uuid.uuid4().hex[:6].upper()}"
    store_id = simular_rappi._store_id_por_defecto()
    total = round(sum(c * p for _, c, p, _ in items), 2)
    payload = {
        "order_detail": {
            "order_id": order_id,
            "cooking_time": 15,
            "items": [
                {"name": n, "quantity": c, "price": p, "comments": nota}
                for n, c, p, nota in items
            ],
            "totals": {"total_order": total},
        },
        "customer": {"first_name": nombre, "last_name": apellido},
        "store": {"internal_id": store_id},
    }
    body = json.dumps(payload).encode("utf-8")
    estado["ultimo_rappi_body"] = body
    firma = simular_rappi._firmar(os.environ["RAPPI_WEBHOOK_SECRET"], body)
    print(f"\n🛵 Rappi: pedido de {nombre} {apellido} por ${total:.2f} ({order_id})")
    respuesta = _post(
        f"{KITCHAN_URL}/api/v1/integraciones/rappi/webhook/new-order",
        body,
        {"Content-Type": "application/json", "Rappi-Signature": firma},
    )
    _resultado(respuesta, 200)
    if respuesta is not None and respuesta.status_code == 200:
        estado["ultimo_rappi"] = order_id


def pedido_pedidosya() -> None:
    cliente, items = PEDIDOS_PEDIDOSYA[estado["pedidosya"] % len(PEDIDOS_PEDIDOSYA)]
    estado["pedidosya"] += 1
    order_id = f"PYA-{uuid.uuid4().hex[:6].upper()}"
    total = round(sum(c * p for _, c, p, _ in items), 2)
    payload = {
        "orderId": order_id,
        "customerName": cliente,
        "totalPrice": total,
        "items": [
            {"name": n, "quantity": c, "price": p, "notes": nota}
            for n, c, p, nota in items
        ],
    }
    remote_id = simular_pedidosya._remote_id_por_defecto()
    cuerpo = json.dumps(payload).encode("utf-8")
    estado["ultimo_pedidosya"] = (remote_id, cuerpo, order_id)
    token = simular_pedidosya._jwt(os.environ["PEDIDOSYA_JWT_SECRET"])
    print(f"\n🛵 PedidosYa: pedido de {cliente} por ${total:.2f} ({order_id})")
    respuesta = _post(
        f"{KITCHAN_URL}/api/v1/integraciones/pedidosya/order/{remote_id}",
        cuerpo,
        {"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
    )
    _resultado(respuesta, 200)


def intentos_falsos() -> None:
    print("\n🕵️ Intento 1: pedido de Rappi con firma falsa")
    body = json.dumps(
        {
            "order_detail": {"order_id": "FALSO-1", "items": [], "totals": {}},
            "store": {"internal_id": simular_rappi._store_id_por_defecto()},
        }
    ).encode("utf-8")
    _resultado(
        _post(
            f"{KITCHAN_URL}/api/v1/integraciones/rappi/webhook/new-order",
            body,
            {
                "Content-Type": "application/json",
                "Rappi-Signature": simular_rappi._firmar("secreto-falso", body),
            },
        ),
        403,
    )
    print("🕵️ Intento 2: pedido de PedidosYa con JWT falso")
    _resultado(
        _post(
            f"{KITCHAN_URL}/api/v1/integraciones/pedidosya/order/"
            f"{simular_pedidosya._remote_id_por_defecto()}",
            json.dumps({"orderId": "FALSO-2", "items": []}).encode("utf-8"),
            {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {simular_pedidosya._jwt('secreto-falso')}",
            },
        ),
        401,
    )
    print("  → Ninguno de los dos aparece en el KDS.")


def rappi_cancela() -> None:
    if not estado["ultimo_rappi"]:
        pedido_rappi()
    order_id = estado["ultimo_rappi"]
    if not order_id:
        return  # el envío falló y ya se mostró el error
    body = json.dumps(
        {
            "event": "canceled_by_user",
            "order_id": order_id,
            "store_id": simular_rappi._store_id_por_defecto(),
        }
    ).encode("utf-8")
    print(f"\n🛑 El cliente cancela en la app de Rappi el pedido {order_id}")
    _resultado(
        _post(
            f"{KITCHAN_URL}/api/v1/integraciones/rappi/webhook/order-cancel",
            body,
            {
                "Content-Type": "application/json",
                "Rappi-Signature": simular_rappi._firmar(
                    os.environ["RAPPI_WEBHOOK_SECRET"], body
                ),
            },
        ),
        200,
    )
    estado["ultimo_rappi"] = None


def reenviar_rappi() -> None:
    if not estado["ultimo_rappi_body"]:
        pedido_rappi()
    body = estado["ultimo_rappi_body"]
    if not body:
        return
    order_id = json.loads(body)["order_detail"]["order_id"]
    print(f"\n🔁 Rappi reenvía el MISMO pedido {order_id} (como ante un timeout)")
    _resultado(
        _post(
            f"{KITCHAN_URL}/api/v1/integraciones/rappi/webhook/new-order",
            body,
            {
                "Content-Type": "application/json",
                "Rappi-Signature": simular_rappi._firmar(
                    os.environ["RAPPI_WEBHOOK_SECRET"], body
                ),
            },
        ),
        200,
    )
    print("  → KITCHAN responde OK pero NO crea otra tarjeta en el KDS.")


def reenviar_pedidosya() -> None:
    if not estado["ultimo_pedidosya"]:
        pedido_pedidosya()
    ultimo = estado["ultimo_pedidosya"]
    if not ultimo:
        return
    remote_id, cuerpo, order_id = ultimo
    token = simular_pedidosya._jwt(os.environ["PEDIDOSYA_JWT_SECRET"])
    print(f"\n🔁 PedidosYa reenvía el MISMO pedido {order_id} (entrega duplicada)")
    _resultado(
        _post(
            f"{KITCHAN_URL}/api/v1/integraciones/pedidosya/order/{remote_id}",
            cuerpo,
            {"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
        ),
        200,
    )
    print("  → KITCHAN responde OK pero NO crea otra tarjeta en el KDS.")


OPCIONES = {
    "1": ("Llega un pedido de Rappi", pedido_rappi),
    "2": ("Llega un pedido de PedidosYa", pedido_pedidosya),
    "3": ("Intentos falsos (firma y JWT inválidos)", intentos_falsos),
    "4": ("El cliente cancela el último pedido de Rappi", rappi_cancela),
    "5": ("Rappi reenvía el MISMO pedido (no se duplica)", reenviar_rappi),
    "6": ("PedidosYa reenvía el MISMO pedido (no se duplica)", reenviar_pedidosya),
}


def main() -> None:
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
    faltan = [
        v for v in ("RAPPI_WEBHOOK_SECRET", "PEDIDOSYA_JWT_SECRET") if not os.getenv(v)
    ]
    if faltan:
        print(f"❌ Faltan en el .env: {', '.join(faltan)}")
        sys.exit(1)

    while True:
        print("\n========== DEMO KITCHAN ==========")
        for clave, (texto, _) in OPCIONES.items():
            print(f"  {clave}. {texto}")
        print("  0. Salir")
        opcion = input("Elige una opción: ").strip()
        if opcion == "0":
            break
        accion = OPCIONES.get(opcion)
        if accion:
            accion[1]()
        else:
            print("  Opción no válida.")


if __name__ == "__main__":
    main()
