"""Caso de uso de Reportes: métricas del día para la pantalla de Analíticas."""

from datetime import date, datetime, time, timedelta
from typing import Callable

from src.kitchan.modules.reportes.domain.entities import (
    ESTADO_CANCELADA,
    ESTADO_ENTREGADA,
    ESTADO_LISTA,
    PedidoResumen,
)
from src.kitchan.modules.reportes.domain.ports import PedidosLecturaPort


class ObtenerAnaliticasPedidosUseCase:
    def __init__(
        self,
        pedidos: PedidosLecturaPort,
        hoy: Callable[[], date] = date.today,
    ):
        self.pedidos = pedidos
        # Inyectable para poder probar el cálculo con una fecha fija.
        self.hoy = hoy

    async def ejecutar(self, restaurante_id: str) -> dict:
        hoy = self.hoy()
        ayer = hoy - timedelta(days=1)
        resumenes = await self.pedidos.listar_desde(
            restaurante_id, datetime.combine(ayer, time.min)
        )

        pedidos_hoy = [p for p in resumenes if p.fecha_creacion.date() == hoy]
        pedidos_ayer = [p for p in resumenes if p.fecha_creacion.date() == ayer]

        return {
            "pedidos_totales_hoy": len(pedidos_hoy),
            "ticket_promedio": round(_ticket_promedio(pedidos_hoy), 2),
            "tiempo_promedio_preparacion_minutos": round(
                _tiempo_promedio_preparacion(pedidos_hoy), 1
            ),
            "pedidos_cancelados_hoy": len(
                [p for p in pedidos_hoy if p.estado == ESTADO_CANCELADA]
            ),
            "por_canal": _por_canal(pedidos_hoy),
            "comparacion_hoy_vs_ayer": _comparacion_por_hora(pedidos_hoy, pedidos_ayer),
        }


def _ticket_promedio(pedidos: list[PedidoResumen]) -> float:
    return sum(p.total for p in pedidos) / len(pedidos) if pedidos else 0.0


def _tiempo_promedio_preparacion(pedidos: list[PedidoResumen]) -> float:
    preparados = [
        p
        for p in pedidos
        if p.estado in (ESTADO_LISTA, ESTADO_ENTREGADA) and p.fecha_actualizacion
    ]
    if not preparados:
        return 0.0
    minutos = [
        (p.fecha_actualizacion - p.fecha_creacion).total_seconds() / 60
        for p in preparados
    ]
    return sum(minutos) / len(minutos)


def _por_canal(pedidos: list[PedidoResumen]) -> dict[str, int]:
    por_canal: dict[str, int] = {}
    for p in pedidos:
        por_canal[p.origen] = por_canal.get(p.origen, 0) + 1
    return por_canal


def _comparacion_por_hora(
    pedidos_hoy: list[PedidoResumen], pedidos_ayer: list[PedidoResumen]
) -> list[dict]:
    por_hora_hoy = [0] * 24
    por_hora_ayer = [0] * 24
    for p in pedidos_hoy:
        por_hora_hoy[p.fecha_creacion.hour] += 1
    for p in pedidos_ayer:
        por_hora_ayer[p.fecha_creacion.hour] += 1
    return [
        {"hora": h, "hoy": por_hora_hoy[h], "ayer": por_hora_ayer[h]} for h in range(24)
    ]
