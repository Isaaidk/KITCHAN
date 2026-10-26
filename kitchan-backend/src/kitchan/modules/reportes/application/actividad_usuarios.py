"""Caso de uso de Reportes: actividad del personal (qué pedidos aceptó cada usuario).

Solo cuenta los pedidos cuyo usuario quedó registrado al aceptarlos; los
aceptados antes de que se guardara ese dato, o por el sistema, aparecen en
`sin_atribuir` y no se reparten entre usuarios.
"""

from collections import defaultdict
from datetime import datetime, time, timedelta, timezone, tzinfo
from typing import Callable, Optional

from src.kitchan.modules.reportes.application.dashboard_pedidos import (
    RANGOS_DIAS,
    UMBRAL_DEMORA_MINUTOS,
    RangoInvalidoError,
    _pct,
    _promedio,
    minutos_preparacion,
    zona_horaria,
)
from src.kitchan.modules.reportes.domain.entities import (
    ESTADO_CANCELADA,
    PedidoResumen,
)
from src.kitchan.modules.reportes.domain.ports import PedidosLecturaPort

RECIENTES = 8


def _ahora_utc() -> datetime:
    return datetime.now(timezone.utc)


class ObtenerActividadUsuariosUseCase:
    def __init__(
        self,
        pedidos: PedidosLecturaPort,
        zona: Optional[tzinfo] = None,
        ahora: Callable[[], datetime] = _ahora_utc,
    ):
        self.pedidos = pedidos
        self.zona = zona or zona_horaria()
        self.ahora = ahora

    async def ejecutar(
        self, restaurante_id: str, rango: str = "7d", usuario_id: Optional[str] = None
    ) -> dict:
        dias = RANGOS_DIAS.get(rango)
        if dias is None:
            raise RangoInvalidoError(f"Rango no válido: {rango}")

        hoy = self.ahora().astimezone(self.zona).date()
        primer_dia = hoy - timedelta(days=dias - 1)
        inicio = datetime.combine(primer_dia, time.min, tzinfo=self.zona)

        periodo = [
            p
            for p in await self.pedidos.listar_desde(restaurante_id, inicio)
            if self._local(p.fecha_creacion) >= inicio
        ]
        aceptados = [p for p in periodo if p.fecha_aceptacion is not None]
        grupos: dict[str, list[PedidoResumen]] = defaultdict(list)
        for p in aceptados:
            if p.aceptado_por_id:
                grupos[p.aceptado_por_id].append(p)

        resultado = {
            "rango": rango,
            "desde": primer_dia.isoformat(),
            "hasta": hoy.isoformat(),
            "sin_atribuir": len([p for p in aceptados if not p.aceptado_por_id]),
            "usuarios": [
                {"usuario_id": uid, **self._resumen(pedidos)}
                for uid, pedidos in sorted(
                    grupos.items(), key=lambda kv: (-len(kv[1]), kv[0])
                )
            ],
        }
        if usuario_id is not None:
            propios = grupos.get(usuario_id, [])
            resultado["detalle"] = {
                "usuario_id": usuario_id,
                **self._resumen(propios),
                "por_canal": self._por_canal(propios),
                "recientes": self._recientes(propios),
            }
        return resultado

    def _local(self, fecha: datetime) -> datetime:
        if fecha.tzinfo is None:
            fecha = fecha.replace(tzinfo=timezone.utc)
        return fecha.astimezone(self.zona)

    def _resumen(self, pedidos: list[PedidoResumen]) -> dict:
        validos = [p for p in pedidos if p.estado != ESTADO_CANCELADA]
        tiempos = [
            m for m in (minutos_preparacion(p) for p in validos) if m is not None
        ]
        demorados = len([t for t in tiempos if t > UMBRAL_DEMORA_MINUTOS])
        ultimo = max(
            (p.fecha_aceptacion for p in pedidos if p.fecha_aceptacion), default=None
        )
        return {
            "pedidos_atendidos": len(pedidos),
            "pedidos_cancelados": len(pedidos) - len(validos),
            "ventas": round(sum(p.total for p in validos), 2),
            "tiempo_promedio_minutos": _promedio(tiempos, 1),
            "tasa_demora": _pct(demorados, len(tiempos)),
            "ultima_actividad": ultimo.isoformat() if ultimo else None,
        }

    @staticmethod
    def _por_canal(pedidos: list[PedidoResumen]) -> list[dict]:
        cuentas: dict[str, int] = defaultdict(int)
        for p in pedidos:
            cuentas[p.origen] += 1
        return [
            {"canal": canal, "pedidos": n}
            for canal, n in sorted(cuentas.items(), key=lambda kv: (-kv[1], kv[0]))
        ]

    @staticmethod
    def _recientes(pedidos: list[PedidoResumen]) -> list[dict]:
        ordenados = sorted(
            pedidos, key=lambda p: p.fecha_aceptacion or p.fecha_creacion, reverse=True
        )
        filas = []
        for p in ordenados[:RECIENTES]:
            minutos = minutos_preparacion(p)
            filas.append(
                {
                    "canal": p.origen,
                    "cliente": p.cliente,
                    "total": round(p.total, 2),
                    "estado": p.estado,
                    "fecha": (p.fecha_aceptacion or p.fecha_creacion).isoformat(),
                    "minutos_preparacion": (
                        None if minutos is None else round(minutos, 1)
                    ),
                }
            )
        return filas
