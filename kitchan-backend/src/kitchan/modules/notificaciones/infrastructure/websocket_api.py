from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from src.kitchan.core.security import decodificar_access_token
from src.kitchan.core.websockets_manager import connection_manager

router = APIRouter(prefix="/api/v1/pedidos", tags=["Pedidos - WebSocket"])


@router.websocket("/ws/pedidos")
async def websocket_pedidos(websocket: WebSocket, token: str = Query(...)):
    # El WebSocket nativo del browser no soporta headers custom, así que el
    # JWT viaja por query param. El restaurante_id SIEMPRE sale del claim del
    # token (multi-tenant), nunca de un parámetro de la URL.
    try:
        claims = decodificar_access_token(token)
    except ValueError:
        await websocket.close(code=1008)
        return

    restaurante_id = claims.get("restaurante_id")
    if not restaurante_id:
        await websocket.close(code=1008)
        return

    await connection_manager.conectar(restaurante_id, websocket)
    try:
        while True:
            # Canal solo server->client; se ignora cualquier mensaje entrante
            # (se usa receive() para detectar la desconexión vía ping/pong).
            await websocket.receive_text()
    except WebSocketDisconnect:
        connection_manager.desconectar(restaurante_id, websocket)
