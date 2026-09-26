"""API de Rappi falsa: se hace pasar por api.dev.rappi.com para que las
acciones de KITCHAN (aceptar / rechazar / listo) se puedan probar sin
credenciales reales.

Implementa las mismas rutas que llama RappiHttpAdapter
(integraciones/rappi/infrastructure/adapters/http_order_adapter.py),
responde OK y muestra en consola lo que recibió, para verificar que el
header `x-authorization`, la URL y el body son los correctos.

Uso (desde kitchan-backend/):
    uvicorn scripts.simulador_rappi.api_rappi_falsa:app --port 8010

y en el .env del backend:
    RAPPI_AUTH_BASE=http://127.0.0.1:8010
    RAPPI_API_BASE=http://127.0.0.1:8010
"""

from typing import Optional

from fastapi import FastAPI, Header, HTTPException, Request

app = FastAPI(title="API de Rappi falsa (simulador KITCHAN)")

TOKEN_FALSO = "token-simulado-rappi"
ORDERS_PATH = "/api/v2/restaurants-integrations-public-api/orders"


def _verificar_token(x_authorization: Optional[str], accion: str, order_id: str) -> None:
    if x_authorization != f"Bearer {TOKEN_FALSO}":
        print(f"🚨 [RAPPI FALSA] {accion} {order_id}: x-authorization inválido -> {x_authorization!r}")
        raise HTTPException(status_code=401, detail="x-authorization inválido")
    print(f"✅ [RAPPI FALSA] {accion} del pedido {order_id} (x-authorization OK)")


@app.post("/restaurants/auth/v1/token/login/integrations")
async def login(request: Request):
    body = await request.json()
    print(f"🔑 [RAPPI FALSA] Login con client_id={body.get('client_id')!r} "
          f"grant_type={body.get('grant_type')!r}")
    if not body.get("client_id") or not body.get("client_secret"):
        raise HTTPException(status_code=401, detail="Faltan client_id/client_secret")
    return {"access_token": TOKEN_FALSO, "token_type": "Bearer", "expires_in": 3600}


@app.put(f"{ORDERS_PATH}/{{order_id}}/take")
@app.put(f"{ORDERS_PATH}/{{order_id}}/take/{{cooking_time}}")
async def take(order_id: str, cooking_time: Optional[int] = None,
               x_authorization: Optional[str] = Header(default=None)):
    _verificar_token(x_authorization, "TAKE", order_id)
    if cooking_time is not None:
        print(f"   tiempo de cocción: {cooking_time} min")
    return {"status": "TAKEN"}


@app.put(f"{ORDERS_PATH}/{{order_id}}/reject")
async def reject(order_id: str, request: Request,
                 x_authorization: Optional[str] = Header(default=None)):
    _verificar_token(x_authorization, "REJECT", order_id)
    print(f"   body: {await request.json()}")
    return {"status": "REJECTED"}


@app.post(f"{ORDERS_PATH}/{{order_id}}/ready-for-pickup")
async def ready(order_id: str, x_authorization: Optional[str] = Header(default=None)):
    _verificar_token(x_authorization, "READY_FOR_PICKUP", order_id)
    return {"status": "READY_FOR_PICKUP"}
