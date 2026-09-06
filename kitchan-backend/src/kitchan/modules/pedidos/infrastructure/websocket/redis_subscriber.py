import asyncio
import json

import redis.asyncio as redis

from src.kitchan.core.websockets_manager import ConnectionManager
from src.kitchan.modules.pedidos.infrastructure.eventos.redis_publisher import (
    CANAL_PREFIX,
)


async def escuchar_eventos(redis_url: str, manager: ConnectionManager) -> None:
    """
    Se suscribe a pedidos:* en Redis y reenvía cada evento al ConnectionManager
    para hacer broadcast a los clientes WS conectados. Necesario para que el
    broadcast funcione entre múltiples workers de uvicorn (cada worker tiene
    su propio ConnectionManager en memoria, pero todos escuchan el mismo Redis).
    """
    cliente = redis.from_url(redis_url, decode_responses=True)
    pubsub = cliente.pubsub()
    await pubsub.psubscribe(f"{CANAL_PREFIX}:*")

    try:
        async for mensaje in pubsub.listen():
            if mensaje["type"] != "pmessage":
                continue
            try:
                payload = json.loads(mensaje["data"])
            except (TypeError, json.JSONDecodeError):
                continue
            restaurante_id = payload.get("restaurante_id")
            if restaurante_id:
                await manager.broadcast(restaurante_id, payload)
    finally:
        await pubsub.punsubscribe(f"{CANAL_PREFIX}:*")
        await pubsub.aclose()
        await cliente.aclose()


def iniciar_subscriber(redis_url: str, manager: ConnectionManager) -> asyncio.Task:
    return asyncio.create_task(escuchar_eventos(redis_url, manager))
