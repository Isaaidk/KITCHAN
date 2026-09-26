"""Integration Middleware de PedidosYa falso: recibe las llamadas que hace
PedidosYaHttpAdapter (integraciones/pedidosya/infrastructure/adapters/
http_order_adapter.py) al aceptar / rechazar / cancelar / marcar listo,
responde OK y muestra en consola lo recibido (Basic Auth, URL y body).

Uso (desde kitchan-backend/):
    uvicorn scripts.simulador_pedidosya.api_pedidosya_falsa:app --port 8011

y en el .env del backend:
    PEDIDOSYA_API_BASE=http://127.0.0.1:8011
"""

import base64
import os
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Request

load_dotenv(".env")

app = FastAPI(title="Integration Middleware de PedidosYa falso (simulador KITCHAN)")


def _verificar_basic(authorization: Optional[str], accion: str, order_id: str) -> None:
    esperado_user = os.getenv("PEDIDOSYA_PLUGIN_USERNAME", "")
    esperado_pass = os.getenv("PEDIDOSYA_PLUGIN_PASSWORD", "")
    try:
        user, _, password = base64.b64decode(authorization.split(" ", 1)[1]).decode().partition(":")
    except Exception:
        user = password = None
    if not authorization or not authorization.startswith("Basic ") or (user, password) != (esperado_user, esperado_pass):
        print(f"🚨 [PYA FALSA] {accion} {order_id}: Basic Auth inválido")
        raise HTTPException(status_code=401, detail="Basic Auth inválido")
    print(f"✅ [PYA FALSA] {accion} del pedido {order_id} (Basic Auth OK, usuario {user!r})")


@app.post("/order/{order_id}/status")
async def status(order_id: str, request: Request, authorization: Optional[str] = Header(default=None)):
    _verificar_basic(authorization, "STATUS", order_id)
    print(f"   body: {await request.json()}")
    return {"status": "OK"}


@app.post("/order/{order_id}/prepared")
async def prepared(order_id: str, authorization: Optional[str] = Header(default=None)):
    _verificar_basic(authorization, "PREPARED", order_id)
    return {"status": "OK"}
