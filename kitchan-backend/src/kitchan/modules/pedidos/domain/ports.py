from abc import ABC, abstractmethod
from typing import Optional
from src.kitchan.modules.pedidos.domain.entities import Pedido


class PedidoRepositoryPort(ABC):
    @abstractmethod
    async def guardar(self, pedido: Pedido) -> Pedido:
        """
        Guarda un pedido en la base de datos y retorna la entidad guardada.
        """
        pass

    @abstractmethod
    async def actualizar_estado(self, pedido_id: str, nuevo_estado: str) -> bool:
        """
        Actualiza el estado de un pedido en la base de datos.
        Retorna True si fue exitoso, False si el pedido no existe.
        """
        pass

    @abstractmethod
    async def actualizar_estado_entrega(
        self, pedido_id: str, estado_entrega: str
    ) -> bool:
        """
        Actualiza el estado de entrega/delivery (courier) de un pedido.
        Retorna True si fue exitoso, False si el pedido no existe.
        """
        pass

    @abstractmethod
    async def buscar_por_id_externo(
        self, origen: str, id_externo: str
    ) -> Optional[Pedido]:
        """
        Busca un pedido por el id que le asignó la plataforma externa (Uber, etc.),
        necesario porque los webhooks/acciones de integraciones solo conocen ese id.
        """
        pass

    @abstractmethod
    async def buscar_por_id(self, pedido_id: str) -> Optional[Pedido]:
        """Busca un pedido por su id interno."""
        pass

    @abstractmethod
    async def listar_estancados(self, minutos: int) -> list[Pedido]:
        """
        Pedidos no terminales (ni ENTREGADA ni CANCELADA) de CUALQUIER
        restaurante cuyo último cambio de estado tiene más de `minutos`
        minutos — usado por el barrido de auto-cancelación.
        """
        pass

    @abstractmethod
    async def listar_por_restaurante(
        self,
        restaurante_id: str,
        estados: Optional[list[str]] = None,
        canal: Optional[str] = None,
        search: Optional[str] = None,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> tuple[list[Pedido], int]:
        """
        Lista pedidos de un restaurante. Sin `page`/`page_size` retorna todos los
        que matcheen los filtros (uso: tablero KDS). Con paginación, retorna
        (pedidos_de_la_pagina, total_de_registros) (uso: pantalla Historial).
        """
        pass
