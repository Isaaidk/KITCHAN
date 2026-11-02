"""Caso de uso de Reportes: exporta el dashboard de analíticas a un archivo."""

from typing import Optional

from src.kitchan.modules.reportes.application.dashboard_pedidos import (
    ObtenerDashboardPedidosUseCase,
)
from src.kitchan.modules.reportes.domain.ports import ExportadorAnaliticasPort


class FormatoExportacionNoSoportado(ValueError):
    pass


class ExportarAnaliticasPedidosUseCase:
    def __init__(
        self,
        dashboard: ObtenerDashboardPedidosUseCase,
        exportadores: dict[str, ExportadorAnaliticasPort],
    ):
        self.dashboard = dashboard
        self.exportadores = exportadores

    async def ejecutar(
        self,
        restaurante_id: str,
        formato: str,
        rango: str = "hoy",
        canal: Optional[str] = None,
    ) -> tuple[bytes, ExportadorAnaliticasPort, str]:
        """Devuelve (contenido, exportador, nombre_de_archivo)."""
        exportador = self.exportadores.get(formato)
        if exportador is None:
            raise FormatoExportacionNoSoportado(formato)
        datos = await self.dashboard.ejecutar(restaurante_id, rango, canal)
        sufijo = f"-{canal.lower()}" if canal else ""
        nombre = f"kitchan-analiticas-{rango}{sufijo}-{datos['hasta']}.{exportador.extension}"
        return exportador.exportar(datos), exportador, nombre
