"""Caso de uso de Reportes: exporta las analíticas del día a un archivo."""

from datetime import date
from typing import Callable

from src.kitchan.modules.reportes.application.analiticas_pedidos import (
    ObtenerAnaliticasPedidosUseCase,
)
from src.kitchan.modules.reportes.domain.ports import ExportadorAnaliticasPort


class FormatoExportacionNoSoportado(ValueError):
    pass


class ExportarAnaliticasPedidosUseCase:
    def __init__(
        self,
        analiticas: ObtenerAnaliticasPedidosUseCase,
        exportadores: dict[str, ExportadorAnaliticasPort],
        hoy: Callable[[], date] = date.today,
    ):
        self.analiticas = analiticas
        self.exportadores = exportadores
        self.hoy = hoy

    async def ejecutar(
        self, restaurante_id: str, formato: str
    ) -> tuple[bytes, ExportadorAnaliticasPort, str]:
        """Devuelve (contenido, exportador, nombre_de_archivo)."""
        exportador = self.exportadores.get(formato)
        if exportador is None:
            raise FormatoExportacionNoSoportado(formato)
        datos = await self.analiticas.ejecutar(restaurante_id)
        fecha = self.hoy().isoformat()
        contenido = exportador.exportar(datos, fecha)
        return contenido, exportador, f"kitchan-analiticas-{fecha}.{exportador.extension}"
