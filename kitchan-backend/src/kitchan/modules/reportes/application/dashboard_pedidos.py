"""Caso de uso de Reportes: dashboard y analíticas por rango de fechas.

Todo se calcula en la zona horaria del restaurante (los pedidos se guardan en
UTC): así las horas pico y los "días" coinciden con lo que ve el local.
"""

from collections import defaultdict
from datetime import datetime, time, timedelta, timezone, tzinfo
from typing import Callable, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from src.kitchan.modules.reportes.domain.entities import (
    ESTADO_CANCELADA,
    ESTADO_LISTA,
    PedidoResumen,
)
from src.kitchan.modules.reportes.domain.ports import PedidosLecturaPort

# Rangos que acepta el dashboard y cuántos días cubre cada uno (incluido hoy).
RANGOS_DIAS = {"hoy": 1, "7d": 7, "30d": 30}
# Un pedido tarda "demasiado" si pasa de estos minutos hasta quedar listo
# (mismo límite con el que la cola marca un pedido como demorado).
UMBRAL_DEMORA_MINUTOS = 10
TOP = 5
ZONA_POR_DEFECTO = "America/Guayaquil"


class RangoInvalidoError(ValueError):
    pass


def zona_horaria(nombre: str = ZONA_POR_DEFECTO) -> tzinfo:
    """Zona horaria del restaurante por nombre (p. ej. "America/Guayaquil").

    En Windows y en imágenes mínimas la base de zonas horarias viene en el paquete
    `tzdata`. Si falta y la zona es la de Ecuador (UTC-5, sin horario de verano) se
    usa ese desfase fijo; con cualquier otra zona el error es explícito.
    """
    try:
        return ZoneInfo(nombre)
    except ZoneInfoNotFoundError:
        if nombre == ZONA_POR_DEFECTO:
            return timezone(timedelta(hours=-5), "America/Guayaquil")
        raise


def _ahora_utc() -> datetime:
    return datetime.now(timezone.utc)


class ObtenerDashboardPedidosUseCase:
    def __init__(
        self,
        pedidos: PedidosLecturaPort,
        zona: Optional[tzinfo] = None,
        ahora: Callable[[], datetime] = _ahora_utc,
    ):
        self.pedidos = pedidos
        self.zona = zona or zona_horaria()
        # Inyectable para probar el cálculo con una fecha fija.
        self.ahora = ahora

    async def ejecutar(self, restaurante_id: str, rango: str = "hoy") -> dict:
        dias = RANGOS_DIAS.get(rango)
        if dias is None:
            raise RangoInvalidoError(f"Rango no válido: {rango}")

        hoy = self.ahora().astimezone(self.zona).date()
        primer_dia = hoy - timedelta(days=dias - 1)
        inicio = datetime.combine(primer_dia, time.min, tzinfo=self.zona)
        inicio_anterior = datetime.combine(
            primer_dia - timedelta(days=dias), time.min, tzinfo=self.zona
        )

        todos = await self.pedidos.listar_desde(restaurante_id, inicio_anterior)
        periodo = [p for p in todos if self._local(p.fecha_creacion) >= inicio]
        anterior = [
            p
            for p in todos
            if inicio_anterior <= self._local(p.fecha_creacion) < inicio
        ]

        resumen = self._resumen(periodo)
        return {
            "rango": rango,
            "desde": primer_dia.isoformat(),
            "hasta": hoy.isoformat(),
            "resumen": resumen,
            "periodo_anterior": self._resumen(anterior),
            "por_hora": self._por_hora(periodo, anterior),
            "hora_pico": self._hora_pico(periodo),
            "por_dia": self._por_dia(periodo, primer_dia, dias),
            "por_canal": self._por_canal(periodo, resumen["ventas_totales"]),
            "umbral_demora_minutos": UMBRAL_DEMORA_MINUTOS,
            **self._productos(periodo),
            "clientes": self._clientes(periodo),
            "metodos_pago": self._metodos_pago(periodo),
        }

    # ---------- utilidades ----------

    def _local(self, fecha: datetime) -> datetime:
        if fecha.tzinfo is None:
            fecha = fecha.replace(tzinfo=timezone.utc)
        return fecha.astimezone(self.zona)

    @staticmethod
    def _validos(pedidos: list[PedidoResumen]) -> list[PedidoResumen]:
        return [p for p in pedidos if p.estado != ESTADO_CANCELADA]

    @staticmethod
    def _minutos_preparacion(p: PedidoResumen) -> Optional[float]:
        """Minutos que tardó la cocina en dejar el pedido listo.

        Con los momentos de cocina guardados (aceptación y "listo") el cálculo es
        exacto: de que la cocina lo aceptó a que lo terminó (si nunca pasó por
        "en preparación", desde que llegó). Los pedidos anteriores a que se
        guardaran esos momentos solo se pueden medir si siguen en "lista",
        porque su último cambio de estado es justo ese; los ya entregados se
        omiten para no inflar el promedio con el tiempo de entrega.
        """
        if p.fecha_lista:
            inicio, fin = p.fecha_aceptacion or p.fecha_creacion, p.fecha_lista
        elif p.estado == ESTADO_LISTA and p.fecha_actualizacion:
            inicio, fin = p.fecha_creacion, p.fecha_actualizacion
        else:
            return None
        if (fin.tzinfo is None) != (inicio.tzinfo is None):
            fin = fin.replace(tzinfo=None)
            inicio = inicio.replace(tzinfo=None)
        return max((fin - inicio).total_seconds() / 60, 0.0)

    # ---------- bloques del reporte ----------

    def _resumen(self, pedidos: list[PedidoResumen]) -> dict:
        validos = self._validos(pedidos)
        ventas = sum(p.total for p in validos)
        tiempos = [
            m for m in (self._minutos_preparacion(p) for p in validos) if m is not None
        ]
        cancelados = len(pedidos) - len(validos)
        return {
            "pedidos_totales": len(pedidos),
            "pedidos_cancelados": cancelados,
            "tasa_cancelacion": _pct(cancelados, len(pedidos)),
            "ventas_totales": round(ventas, 2),
            "ticket_promedio": round(ventas / len(validos), 2) if validos else 0.0,
            "tiempo_promedio_preparacion_minutos": _promedio(tiempos, 1),
        }

    def _por_hora(
        self, periodo: list[PedidoResumen], anterior: list[PedidoResumen]
    ) -> list[dict]:
        actual = [0] * 24
        previo = [0] * 24
        for p in self._validos(periodo):
            actual[self._local(p.fecha_creacion).hour] += 1
        for p in self._validos(anterior):
            previo[self._local(p.fecha_creacion).hour] += 1
        return [
            {"hora": h, "pedidos": actual[h], "pedidos_anterior": previo[h]}
            for h in range(24)
        ]

    def _hora_pico(self, periodo: list[PedidoResumen]) -> Optional[dict]:
        cuentas = [0] * 24
        for p in self._validos(periodo):
            cuentas[self._local(p.fecha_creacion).hour] += 1
        maximo = max(cuentas)
        if maximo == 0:
            return None
        return {"hora": cuentas.index(maximo), "pedidos": maximo}

    def _por_dia(self, periodo: list[PedidoResumen], primer_dia, dias: int) -> list[dict]:
        pedidos_dia: dict = defaultdict(int)
        ventas_dia: dict = defaultdict(float)
        for p in self._validos(periodo):
            dia = self._local(p.fecha_creacion).date()
            pedidos_dia[dia] += 1
            ventas_dia[dia] += p.total
        resultado = []
        for i in range(dias):
            dia = primer_dia + timedelta(days=i)
            resultado.append(
                {
                    "fecha": dia.isoformat(),
                    "pedidos": pedidos_dia[dia],
                    "ventas": round(ventas_dia[dia], 2),
                }
            )
        return resultado

    def _por_canal(self, periodo: list[PedidoResumen], ventas_totales: float) -> list[dict]:
        grupos: dict[str, list[PedidoResumen]] = defaultdict(list)
        for p in periodo:
            grupos[p.origen].append(p)

        canales = []
        for canal, pedidos in grupos.items():
            validos = self._validos(pedidos)
            ventas = sum(p.total for p in validos)
            tiempos = [
                m
                for m in (self._minutos_preparacion(p) for p in validos)
                if m is not None
            ]
            demorados = len([t for t in tiempos if t > UMBRAL_DEMORA_MINUTOS])
            canales.append(
                {
                    "canal": canal,
                    "pedidos": len(pedidos),
                    "cancelados": len(pedidos) - len(validos),
                    "ventas": round(ventas, 2),
                    "ticket_promedio": round(ventas / len(validos), 2) if validos else 0.0,
                    "tiempo_promedio_minutos": _promedio(tiempos, 1),
                    "tasa_demora": _pct(demorados, len(tiempos)),
                    "porcentaje_pedidos": _pct(len(pedidos), len(periodo)),
                    "porcentaje_ventas": _pct(ventas, ventas_totales),
                }
            )
        return sorted(canales, key=lambda c: (-c["pedidos"], c["canal"]))

    def _productos(self, periodo: list[PedidoResumen]) -> dict:
        """Platos y combos vendidos. Un combo es un ítem cuyo nombre contiene
        "combo"; mientras el menú no los tenga, la lista de combos va vacía."""
        platos: dict[str, dict] = {}
        combos: dict[str, dict] = {}
        for p in self._validos(periodo):
            for item in p.items:
                nombre = item.nombre.strip()
                if not nombre or item.cantidad <= 0:
                    continue
                clave = nombre.casefold()
                destino = combos if "combo" in clave else platos
                fila = destino.setdefault(
                    clave, {"nombre": nombre, "cantidad": 0, "ventas": 0.0}
                )
                fila["cantidad"] += item.cantidad
                fila["ventas"] += item.cantidad * item.precio_unitario

        def formatear(filas: list[dict]) -> list[dict]:
            return [
                {
                    "nombre": f["nombre"],
                    "cantidad": f["cantidad"],
                    "ventas": round(f["ventas"], 2),
                }
                for f in filas
            ]

        ranking = sorted(
            platos.values(), key=lambda f: (-f["cantidad"], -f["ventas"], f["nombre"])
        )
        resto = ranking[TOP:]
        menos = sorted(
            resto, key=lambda f: (f["cantidad"], f["ventas"], f["nombre"])
        )[:TOP]
        ranking_combos = sorted(
            combos.values(), key=lambda f: (-f["cantidad"], -f["ventas"], f["nombre"])
        )[:TOP]
        return {
            "productos_mas_vendidos": formatear(ranking[:TOP]),
            "productos_menos_vendidos": formatear(menos),
            "combos_mas_vendidos": formatear(ranking_combos),
            "productos_distintos": len(platos),
        }

    def _clientes(self, periodo: list[PedidoResumen]) -> dict:
        """Frecuencia de compra. Los canales solo informan el nombre del cliente
        (no hay un ID), por eso se agrupa por nombre y el dato es aproximado."""
        por_cliente: dict[str, dict] = {}
        for p in self._validos(periodo):
            nombre = p.cliente.strip()
            if not nombre:
                continue
            fila = por_cliente.setdefault(
                nombre.casefold(), {"cliente": nombre, "pedidos": 0, "ventas": 0.0}
            )
            fila["pedidos"] += 1
            fila["ventas"] += p.total

        filas = list(por_cliente.values())
        total_pedidos = sum(f["pedidos"] for f in filas)
        recurrentes = [f for f in filas if f["pedidos"] >= 2]
        return {
            "identificacion": "nombre",
            "clientes_unicos": len(filas),
            "clientes_recurrentes": len(recurrentes),
            "tasa_recurrencia": _pct(len(recurrentes), len(filas)),
            "pedidos_por_cliente": _promedio([f["pedidos"] for f in filas], 2),
            "distribucion": [
                {
                    "etiqueta": "1 pedido",
                    "clientes": len([f for f in filas if f["pedidos"] == 1]),
                },
                {
                    "etiqueta": "2 pedidos",
                    "clientes": len([f for f in filas if f["pedidos"] == 2]),
                },
                {
                    "etiqueta": "3 o más",
                    "clientes": len([f for f in filas if f["pedidos"] >= 3]),
                },
            ],
            "mas_frecuentes": [
                {
                    "cliente": f["cliente"],
                    "pedidos": f["pedidos"],
                    "ventas": round(f["ventas"], 2),
                }
                for f in sorted(
                    recurrentes, key=lambda f: (-f["pedidos"], -f["ventas"], f["cliente"])
                )[:TOP]
            ],
            "pedidos_analizados": total_pedidos,
        }

    def _metodos_pago(self, periodo: list[PedidoResumen]) -> dict:
        """Cuánto vende cada método de pago. Solo cuenta los pedidos cuyo canal
        informó el método; el resto queda en `sin_dato` y nunca se inventa."""
        validos = self._validos(periodo)
        grupos: dict[str, dict] = {}
        for p in validos:
            if not p.metodo_pago or not p.metodo_pago.strip():
                continue
            metodo = p.metodo_pago.strip().upper()
            fila = grupos.setdefault(metodo, {"metodo": metodo, "pedidos": 0, "ventas": 0.0})
            fila["pedidos"] += 1
            fila["ventas"] += p.total

        con_dato = sum(f["pedidos"] for f in grupos.values())
        ventas_con_dato = sum(f["ventas"] for f in grupos.values())
        filas = sorted(grupos.values(), key=lambda f: (-f["ventas"], f["metodo"]))
        return {
            "disponible": con_dato > 0,
            "sin_dato": len(validos) - con_dato,
            "cobertura": _pct(con_dato, len(validos)),
            "items": [
                {
                    "metodo": f["metodo"],
                    "pedidos": f["pedidos"],
                    "ventas": round(f["ventas"], 2),
                    "porcentaje_pedidos": _pct(f["pedidos"], con_dato),
                    "porcentaje_ventas": _pct(f["ventas"], ventas_con_dato),
                }
                for f in filas
            ],
        }


def _promedio(valores: list[float], decimales: int) -> float:
    return round(sum(valores) / len(valores), decimales) if valores else 0.0


def _pct(parte: float, total: float) -> float:
    return round(parte / total * 100, 1) if total else 0.0
