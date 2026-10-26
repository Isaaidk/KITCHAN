from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

from src.kitchan.modules.reportes.domain.ports import ExportadorAnaliticasPort

_CABECERA = PatternFill("solid", fgColor="1F2937")
_TEXTO_CABECERA = Font(bold=True, color="FFFFFF")
_DIA_SEMANA = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


def _tabla(hoja, titulos: list[str], filas: list[list], anchos: list[int]) -> None:
    for col, titulo in enumerate(titulos, start=1):
        celda = hoja.cell(row=1, column=col, value=titulo)
        celda.fill = _CABECERA
        celda.font = _TEXTO_CABECERA
        celda.alignment = Alignment(horizontal="center")
    for fila in filas:
        hoja.append(fila)
    for letra, ancho in zip("ABCDEFGHI", anchos):
        hoja.column_dimensions[letra].width = ancho
    hoja.freeze_panes = "A2"


class ExportadorExcel(ExportadorAnaliticasPort):
    media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    extension = "xlsx"

    def exportar(self, dashboard: dict) -> bytes:
        libro = Workbook()
        actual, previo = dashboard["resumen"], dashboard["periodo_anterior"]

        hoja = libro.active
        hoja.title = "Resumen"
        metricas = [
            ("Pedidos totales", "pedidos_totales"),
            ("Pedidos cancelados", "pedidos_cancelados"),
            ("Tasa de cancelación (%)", "tasa_cancelacion"),
            ("Ventas totales ($)", "ventas_totales"),
            ("Ticket promedio ($)", "ticket_promedio"),
            ("Tiempo promedio de preparación (min)", "tiempo_promedio_preparacion_minutos"),
            ("Unidades por pedido", "unidades_por_pedido"),
        ]
        _tabla(
            hoja,
            ["Métrica", "Periodo", "Periodo anterior"],
            [[nombre, actual[k], previo[k]] for nombre, k in metricas],
            [42, 16, 18],
        )
        pico = dashboard["hora_pico"]
        for nombre, valor in (
            ("Hora pico", f"{pico['hora']:02d}:00 ({pico['pedidos']} pedidos)" if pico else "Sin pedidos"),
            ("Productos distintos vendidos", dashboard["productos_distintos"]),
            ("Umbral de demora (min)", dashboard["umbral_demora_minutos"]),
        ):
            hoja.append([nombre, valor])
        hoja["E1"] = "Periodo"
        hoja["F1"] = f"{dashboard['desde']} al {dashboard['hasta']} ({dashboard['rango']})"
        hoja["E2"] = "Canal"
        hoja["F2"] = dashboard["canal"] or "Todos"
        hoja.column_dimensions["E"].width = 10
        hoja.column_dimensions["F"].width = 30

        _tabla(
            libro.create_sheet("Por canal"),
            [
                "Canal",
                "Pedidos",
                "Cancelados",
                "Ventas ($)",
                "Ticket promedio ($)",
                "Tiempo prom. (min)",
                "Demorados (%)",
                "% pedidos",
                "% ventas",
            ],
            [
                [
                    c["canal"],
                    c["pedidos"],
                    c["cancelados"],
                    c["ventas"],
                    c["ticket_promedio"],
                    c["tiempo_promedio_minutos"],
                    c["tasa_demora"],
                    c["porcentaje_pedidos"],
                    c["porcentaje_ventas"],
                ]
                for c in dashboard["por_canal"]
            ],
            [18, 10, 12, 12, 20, 18, 14, 11, 11],
        )
        _tabla(
            libro.create_sheet("Por día"),
            ["Fecha", "Pedidos", "Ventas ($)"],
            [[d["fecha"], d["pedidos"], d["ventas"]] for d in dashboard["por_dia"]],
            [14, 10, 12],
        )
        _tabla(
            libro.create_sheet("Por hora"),
            ["Hora", "Pedidos", "Periodo anterior"],
            [
                [f"{h['hora']:02d}:00", h["pedidos"], h["pedidos_anterior"]]
                for h in dashboard["por_hora"]
            ],
            [10, 10, 18],
        )
        _tabla(
            libro.create_sheet("Día de la semana"),
            ["Día", "Pedidos", "Ventas ($)"],
            [
                [_DIA_SEMANA[d["dia"] % 7], d["pedidos"], d["ventas"]]
                for d in dashboard["por_dia_semana"]
            ],
            [14, 10, 12],
        )
        productos = [
            [seccion, p["nombre"], p["cantidad"], p["ventas"]]
            for seccion, clave in (
                ("Más vendidos", "productos_mas_vendidos"),
                ("Mayor ingreso", "productos_mayor_ingreso"),
                ("Menos vendidos", "productos_menos_vendidos"),
                ("Combos", "combos_mas_vendidos"),
            )
            for p in dashboard[clave]
        ]
        _tabla(
            libro.create_sheet("Productos"),
            ["Ranking", "Producto", "Cantidad", "Ventas ($)"],
            productos,
            [18, 40, 10, 12],
        )

        pagos = dashboard["metodos_pago"]
        hoja_pagos = libro.create_sheet("Métodos de pago")
        _tabla(
            hoja_pagos,
            ["Método", "Pedidos", "Ventas ($)", "% pedidos", "% ventas"],
            [
                [m["metodo"], m["pedidos"], m["ventas"], m["porcentaje_pedidos"], m["porcentaje_ventas"]]
                for m in pagos["items"]
            ],
            [20, 10, 12, 11, 11],
        )
        hoja_pagos.append([])
        hoja_pagos.append(["Pedidos sin método informado", pagos["sin_dato"]])
        hoja_pagos.append(["Cobertura del dato (%)", pagos["cobertura"]])

        clientes = dashboard["clientes"]
        hoja_clientes = libro.create_sheet("Clientes")
        _tabla(
            hoja_clientes,
            ["Indicador", "Valor"],
            [
                ["Identificación de clientes por", clientes["identificacion"]],
                ["Clientes únicos", clientes["clientes_unicos"]],
                ["Clientes recurrentes", clientes["clientes_recurrentes"]],
                ["Tasa de recurrencia (%)", clientes["tasa_recurrencia"]],
                ["Pedidos por cliente", clientes["pedidos_por_cliente"]],
                ["Pedidos analizados", clientes["pedidos_analizados"]],
            ],
            [34, 18, 12],
        )
        hoja_clientes.append([])
        hoja_clientes.append(["Pedidos por cliente (distribución)", "Clientes"])
        for d in clientes["distribucion"]:
            hoja_clientes.append([d["etiqueta"], d["clientes"]])
        hoja_clientes.append([])
        hoja_clientes.append(["Clientes más frecuentes", "Pedidos", "Ventas ($)"])
        for c in clientes["mas_frecuentes"]:
            hoja_clientes.append([c["cliente"], c["pedidos"], c["ventas"]])

        salida = BytesIO()
        libro.save(salida)
        return salida.getvalue()
