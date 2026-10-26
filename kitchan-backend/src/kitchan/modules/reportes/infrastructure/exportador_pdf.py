from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from src.kitchan.modules.reportes.domain.ports import ExportadorAnaliticasPort


def _tabla(filas: list[list], anchos: list[float]) -> Table:
    tabla = Table(filas, colWidths=anchos, repeatRows=1)
    tabla.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F2937")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D1D5DB")),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.white, colors.HexColor("#F3F4F6")],
                ),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ]
        )
    )
    return tabla


class ExportadorPdf(ExportadorAnaliticasPort):
    media_type = "application/pdf"
    extension = "pdf"

    def exportar(self, analiticas: dict, fecha: str) -> bytes:
        estilos = getSampleStyleSheet()
        salida = BytesIO()
        doc = SimpleDocTemplate(
            salida, pagesize=A4, title=f"Analíticas KITCHAN {fecha}", topMargin=2 * cm
        )

        resumen = [
            ["Métrica", "Valor"],
            ["Pedidos totales hoy", analiticas["pedidos_totales_hoy"]],
            ["Ticket promedio", f"${analiticas['ticket_promedio']:.2f}"],
            [
                "Tiempo promedio de preparación",
                f"{analiticas['tiempo_promedio_preparacion_minutos']} min",
            ],
            ["Pedidos cancelados hoy", analiticas["pedidos_cancelados_hoy"]],
        ]
        canales = [["Canal", "Pedidos hoy"]] + [
            [canal, cantidad] for canal, cantidad in analiticas["por_canal"].items()
        ]
        if len(canales) == 1:
            canales.append(["Sin pedidos hoy", 0])
        # Solo las horas con actividad: 24 filas casi vacías no aportan.
        horas = [["Hora", "Hoy", "Ayer"]] + [
            [f"{p['hora']:02d}:00", p["hoy"], p["ayer"]]
            for p in analiticas["comparacion_hoy_vs_ayer"]
            if p["hoy"] or p["ayer"]
        ]
        if len(horas) == 1:
            horas.append(["Sin actividad", 0, 0])

        doc.build(
            [
                Paragraph("Analíticas KITCHAN", estilos["Title"]),
                Paragraph(f"Fecha: {fecha}", estilos["Normal"]),
                Spacer(1, 0.6 * cm),
                Paragraph("Resumen del día", estilos["Heading2"]),
                _tabla(resumen, [9 * cm, 5 * cm]),
                Spacer(1, 0.6 * cm),
                Paragraph("Pedidos por canal", estilos["Heading2"]),
                _tabla(canales, [9 * cm, 5 * cm]),
                Spacer(1, 0.6 * cm),
                Paragraph("Hoy vs ayer por hora", estilos["Heading2"]),
                _tabla(horas, [5 * cm, 4.5 * cm, 4.5 * cm]),
            ]
        )
        return salida.getvalue()
