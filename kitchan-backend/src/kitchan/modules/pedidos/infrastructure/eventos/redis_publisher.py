import json

import redis.asyncio as redis

from src.kitchan.modules.pedidos.application.ports import NotificadorEventosPort
from src.kitchan.modules.pedidos.domain.entities import Pedido

CANAL_PREFIX = "pedidos"


class RedisPublisherAdapter(NotificadorEventosPort):
    """
    Publica los eventos de pedidos al canal Redis `pedidos:{restaurante_id}`.
    El subscriber (pedidos/infrastructure/websocket/redis_subscriber.py) escucha
    con psubscribe("pedidos:*") y reenvía al ConnectionManager de WebSockets.
    Se envía el pedido completo para que el frontend no necesite un round-trip
    REST adicional al recibir el evento.
    """

    def __init__(self, redis_url: str):
        self.redis_client = redis.from_url(redis_url, decode_responses=True)

    async def notificar_pedido_creado(self, pedido: Pedido) -> None:
        await self._publicar("PEDIDO_CREADO", pedido)

    async def notificar_pedido_actualizado(self, pedido: Pedido) -> None:
        await self._publicar("PEDIDO_ACTUALIZADO", pedido)

    async def _publicar(self, tipo: str, pedido: Pedido) -> None:
        canal = f"{CANAL_PREFIX}:{pedido.restaurante_id}"
        mensaje = {
            "tipo": tipo,
            "restaurante_id": pedido.restaurante_id,
            "pedido": json.loads(pedido.model_dump_json()),
        }
        await self.redis_client.publish(canal, json.dumps(mensaje))
