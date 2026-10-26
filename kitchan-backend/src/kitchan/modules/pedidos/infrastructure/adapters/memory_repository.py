from datetime import datetime, timedelta
from typing import Optional

from src.kitchan.modules.pedidos.domain.ports import PedidoRepositoryPort
from src.kitchan.modules.pedidos.domain.entities import EstadoPedido, Pedido
from src.kitchan.modules.pedidos.domain.exceptions import PedidoDuplicadoError

ESTADOS_TERMINALES = {EstadoPedido.ENTREGADA, EstadoPedido.CANCELADA}


class MemoryPedidoRepository(PedidoRepositoryPort):
    """
    Repositorio en memoria (diccionario). Solo para tests unitarios rápidos
    que no necesitan una base de datos real; la app usa PostgresPedidoRepository.
    """

    def __init__(self):
        self.db: dict[str, Pedido] = {}

    async def guardar(self, pedido: Pedido) -> Pedido:
        if pedido.id_externo is not None and await self.buscar_por_id_externo(
            pedido.origen, pedido.id_externo
        ):
            raise PedidoDuplicadoError(f"{pedido.origen} {pedido.id_externo}")
        self.db[pedido.id] = pedido
        return pedido

    async def actualizar_estado(
        self,
        pedido_id: str,
        nuevo_estado: str,
        estado_esperado: Optional[str] = None,
    ) -> bool:
        pedido = self.db.get(pedido_id)
        if pedido is None:
            return False
        if estado_esperado is not None and pedido.estado != estado_esperado:
            return False
        pedido.estado = nuevo_estado
        return True

    async def actualizar_estado_entrega(
        self, pedido_id: str, estado_entrega: str
    ) -> bool:
        if pedido_id in self.db:
            self.db[pedido_id].estado_entrega = estado_entrega
            return True
        return False

    async def buscar_por_id_externo(
        self, origen: str, id_externo: str
    ) -> Optional[Pedido]:
        for pedido in self.db.values():
            if pedido.origen == origen and pedido.id_externo == id_externo:
                return pedido
        return None

    async def buscar_por_id(self, pedido_id: str) -> Optional[Pedido]:
        return self.db.get(pedido_id)

    async def listar_estancados(self, minutos: int) -> list[Pedido]:
        # No hay fecha_actualizacion en el dominio; se aproxima con
        # fecha_creacion (suficiente para el repo de tests en memoria).
        limite = datetime.utcnow() - timedelta(minutes=minutos)
        return [
            p
            for p in self.db.values()
            if p.estado not in ESTADOS_TERMINALES and p.fecha_creacion < limite
        ]

    async def listar_por_restaurante_desde(
        self, restaurante_id: str, desde: datetime
    ) -> list[Pedido]:
        return [
            p
            for p in self.db.values()
            if p.restaurante_id == restaurante_id and p.fecha_creacion >= desde
        ]

    async def listar_por_restaurante(
        self,
        restaurante_id: str,
        estados: Optional[list[str]] = None,
        canal: Optional[str] = None,
        search: Optional[str] = None,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> tuple[list[Pedido], int]:
        pedidos = [p for p in self.db.values() if p.restaurante_id == restaurante_id]
        if estados:
            pedidos = [p for p in pedidos if p.estado in estados]
        if canal:
            pedidos = [p for p in pedidos if p.origen == canal]
        if search:
            s = search.lower()
            pedidos = [
                p
                for p in pedidos
                if s in p.cliente.lower()
                or (p.id_externo and s in p.id_externo.lower())
            ]
        total = len(pedidos)
        if page and page_size:
            inicio = (page - 1) * page_size
            pedidos = pedidos[inicio : inicio + page_size]
        return pedidos, total
