from abc import ABC, abstractmethod
from datetime import datetime

from src.kitchan.modules.reportes.domain.entities import PedidoResumen


class PedidosLecturaPort(ABC):
    """Puerto de salida: de dónde obtiene Reportes los pedidos a analizar."""

    @abstractmethod
    async def listar_desde(
        self, restaurante_id: str, desde: datetime
    ) -> list[PedidoResumen]:
        """Pedidos del restaurante creados desde `desde`, en cualquier estado."""
        pass
