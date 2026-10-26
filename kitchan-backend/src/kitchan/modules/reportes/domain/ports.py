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


class ExportadorAnaliticasPort(ABC):
    """Puerto de salida: serializa las analíticas calculadas a un archivo."""

    media_type: str
    extension: str

    @abstractmethod
    def exportar(self, dashboard: dict) -> bytes:
        """Devuelve el contenido del archivo con el dashboard del periodo."""
        pass
