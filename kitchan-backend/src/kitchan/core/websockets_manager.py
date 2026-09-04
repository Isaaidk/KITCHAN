from fastapi import WebSocket


class ConnectionManager:
    """
    Registro de conexiones WebSocket activas del KDS, agrupadas por
    restaurante_id (multi-tenant: cada restaurante solo recibe sus eventos).
    Instancia única (singleton a nivel de módulo, ver `connection_manager`
    abajo) compartida entre el endpoint WS (agrega/quita conexiones) y el
    subscriber de Redis (hace el broadcast al recibir un evento).
    """

    def __init__(self):
        self._conexiones: dict[str, set[WebSocket]] = {}

    async def conectar(self, restaurante_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._conexiones.setdefault(restaurante_id, set()).add(websocket)

    def desconectar(self, restaurante_id: str, websocket: WebSocket) -> None:
        conexiones = self._conexiones.get(restaurante_id)
        if not conexiones:
            return
        conexiones.discard(websocket)
        if not conexiones:
            del self._conexiones[restaurante_id]

    async def broadcast(self, restaurante_id: str, mensaje: dict) -> None:
        conexiones = self._conexiones.get(restaurante_id)
        if not conexiones:
            return
        muertas = set()
        for websocket in conexiones:
            try:
                await websocket.send_json(mensaje)
            except Exception:
                muertas.add(websocket)
        for websocket in muertas:
            self.desconectar(restaurante_id, websocket)


connection_manager = ConnectionManager()
