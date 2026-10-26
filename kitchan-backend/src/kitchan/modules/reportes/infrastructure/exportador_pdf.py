from io import BytesIO
from xml.sax.saxutils import escape

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
                ("FONTSIZE", (0, 0), (-1, -1), 9),
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


def _con_datos(filas: list[list], vacio: list) -> list[list]:
    return filas if len(filas) > 1 else filas + [vacio]


def _usd(valor: float) -> str:
    return f"${valor:.2f}"


class ExportadorPdf(ExportadorAnaliticasPort):
    media_type = "application/pdf"
    extension = "pdf"

    def exportar(self, dashboard: dict) -> bytes:
        estilos = getSampleStyleSheet()
        salida = BytesIO()
        doc = SimpleDocTemplate(
            salida,
            pagesize=A4,
            title=f"Analíticas KITCHAN {dashboard['hasta']}",
            topMargin=2 * cm,
        )
        actual, previo = dashboard["resumen"], dashboard["periodo_anterior"]

        resumen = [
            ["Métrica", "Periodo", "Anterior"],
            ["Pedidos totales", actual["pedidos_totales"], previo["pedidos_totales"]],
            ["Pedidos cancelados", actual["pedidos_cancelados"], previo["pedidos_cancelados"]],
            [
                "Tasa de cancelación",
                f"{actual['tasa_cancelacion']}%",
                f"{previo['tasa_cancelacion']}%",
            ],
            ["Ventas totales", _usd(actual["ventas_totales"]), _usd(previo["ventas_totales"])],
            ["Ticket promedio", _usd(actual["ticket_promedio"]), _usd(previo["ticket_promedio"])],
            [
                "Tiempo prom. preparación",
                f"{actual['tiempo_promedio_preparacion_minutos']} min",
                f"{previo['tiempo_promedio_preparacion_minutos']} min",
            ],
        ]
        canales = _con_datos(
            [["Canal", "Pedidos", "Cancel.", "Ventas", "Ticket", "Min. prom."]]
            + [
                [
                    c["canal"],
                    c["pedidos"],
                    c["cancelados"],
                    _usd(c["ventas"]),
                    _usd(c["ticket_promedio"]),
                    c["tiempo_promedio_minutos"],
                ]
                for c in dashboard["por_canal"]
            ],
            ["Sin pedidos", 0, 0, _usd(0), _usd(0), 0],
        )
        # Solo las horas con actividad: 24 filas casi vacías no aportan.
        horas = _con_datos(
            [["Hora", "Pedidos", "Anterior"]]
            + [
                [f"{h['hora']:02d}:00", h["pedidos"], h["pedidos_anterior"]]
                for h in dashboard["por_hora"]
                if h["pedidos"] or h["pedidos_anterior"]
            ],
            ["Sin actividad", 0, 0],
        )
        productos = _con_datos(
            [["Producto", "Cantidad", "Ventas"]]
            + [
                [p["nombre"][:45], p["cantidad"], _usd(p["ventas"])]
                for p in dashboard["productos_mas_vendidos"]
            ],
            ["Sin ventas", 0, _usd(0)],
        )

        canal = dashboard["canal"] or "todos los canales"
        subtitulo = f"{dashboard['desde']} al {dashboard['hasta']} · {dashboard['rango']} · {canal}"
        doc.build(
            [
                Paragraph("Analíticas KITCHAN", estilos["Title"]),
                Paragraph(escape(subtitulo), estilos["Normal"]),
                Spacer(1, 0.5 * cm),
                Paragraph("Resumen", estilos["Heading2"]),
                _tabla(resumen, [8 * cm, 4 * cm, 4 * cm]),
                Spacer(1, 0.5 * cm),
                Paragraph("Por canal", estilos["Heading2"]),
                _tabla(canales, [4 * cm, 2.2 * cm, 2.2 * cm, 2.8 * cm, 2.8 * cm, 2.4 * cm]),
                Spacer(1, 0.5 * cm),
                Paragraph("Pedidos por hora", estilos["Heading2"]),
                _tabla(horas, [5 * cm, 4 * cm, 4 * cm]),
                Spacer(1, 0.5 * cm),
                Paragraph("Productos más vendidos", estilos["Heading2"]),
                _tabla(productos, [9 * cm, 3 * cm, 3.5 * cm]),
            ]
        )
        return salida.getvalue()
