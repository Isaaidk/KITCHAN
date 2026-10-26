from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

from src.kitchan.modules.reportes.domain.ports import ExportadorAnaliticasPort

_CABECERA = PatternFill("solid", fgColor="1F2937")
_TEXTO_CABECERA = Font(bold=True, color="FFFFFF")


def _cabecera(hoja, fila: int, titulos: list[str]) -> None:
    for col, titulo in enumerate(titulos, start=1):
        celda = hoja.cell(row=fila, column=col, value=titulo)
        celda.fill = _CABECERA
        celda.font = _TEXTO_CABECERA
        celda.alignment = Alignment(horizontal="center")


class ExportadorExcel(ExportadorAnaliticasPort):
    media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    extension = "xlsx"

    def exportar(self, analiticas: dict, fecha: str) -> bytes:
        libro = Workbook()

        resumen = libro.active
        resumen.title = "Resumen"
        resumen["A1"] = "Analíticas KITCHAN"
        resumen["A1"].font = Font(bold=True, size=14)
        resumen["A2"] = f"Fecha: {fecha}"
        _cabecera(resumen, 4, ["Métrica", "Valor"])
        metricas = [
            ("Pedidos totales hoy", analiticas["pedidos_totales_hoy"]),
            ("Ticket promedio ($)", analiticas["ticket_promedio"]),
            (
                "Tiempo promedio de preparación (min)",
                analiticas["tiempo_promedio_preparacion_minutos"],
            ),
            ("Pedidos cancelados hoy", analiticas["pedidos_cancelados_hoy"]),
        ]
        for i, (nombre, valor) in enumerate(metricas, start=5):
            resumen.cell(row=i, column=1, value=nombre)
            resumen.cell(row=i, column=2, value=valor)
        resumen["B6"].number_format = "$#,##0.00"
        resumen.column_dimensions["A"].width = 42
        resumen.column_dimensions["B"].width = 16

        canales = libro.create_sheet("Por canal")
        _cabecera(canales, 1, ["Canal", "Pedidos hoy"])
        for i, (canal, cantidad) in enumerate(analiticas["por_canal"].items(), start=2):
            canales.cell(row=i, column=1, value=canal)
            canales.cell(row=i, column=2, value=cantidad)
        canales.column_dimensions["A"].width = 24
        canales.column_dimensions["B"].width = 14

        horas = libro.create_sheet("Hoy vs ayer")
        _cabecera(horas, 1, ["Hora", "Hoy", "Ayer"])
        for i, punto in enumerate(analiticas["comparacion_hoy_vs_ayer"], start=2):
            horas.cell(row=i, column=1, value=f"{punto['hora']:02d}:00")
            horas.cell(row=i, column=2, value=punto["hoy"])
            horas.cell(row=i, column=3, value=punto["ayer"])
        for letra in "ABC":
            horas.column_dimensions[letra].width = 12

        salida = BytesIO()
        libro.save(salida)
        return salida.getvalue()
