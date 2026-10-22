"""Caso de uso de Reportes: qué tan activo está cada canal de venta.

Para la pantalla de Integraciones: cuántos pedidos recibió cada canal hoy y
cuándo fue el último (mirando los últimos 30 días).
"""

from datetime import datetime, time, timedelta, timezone, tzinfo
from typing import Callable, Optional

from src.kitchan.modules.reportes.application.dashboard_pedidos import zona_horaria
from src.kitchan.modules.reportes.domain.ports import PedidosLecturaPort

DIAS_HISTORIAL = 30


def _ahora_utc() -> datetime:
    return datetime.now(timezone.utc)


class ObtenerActividadCanalesUseCase:
    def __init__(
        self,
        pedidos: PedidosLecturaPort,
        zona: Optional[tzinfo] = None,
        ahora: Callable[[], datetime] = _ahora_utc,
    ):
        self.pedidos = pedidos
        self.zona = zona or zona_horaria()
        self.ahora = ahora

    async def ejecutar(self, restaurante_id: str) -> list[dict]:
        hoy = self.ahora().astimezone(self.zona).date()
        inicio_hoy = datetime.combine(hoy, time.min, tzinfo=self.zona)
        desde = datetime.combine(
            hoy - timedelta(days=DIAS_HISTORIAL - 1), time.min, tzinfo=self.zona
        )

        canales: dict[str, dict] = {}
        for p in await self.pedidos.listar_desde(restaurante_id, desde):
            origen = "PEDIDOS_YA" if p.origen.upper() == "PEDIDOSYA" else p.origen.upper()
            fila = canales.setdefault(
                origen,
                {"canal": origen, "pedidos_hoy": 0, "pedidos_30d": 0, "ultimo_pedido": None},
            )
            creado = (
                p.fecha_creacion
                if p.fecha_creacion.tzinfo
                else p.fecha_creacion.replace(tzinfo=timezone.utc)
            )
            fila["pedidos_30d"] += 1
            if creado.astimezone(self.zona) >= inicio_hoy:
                fila["pedidos_hoy"] += 1
            if fila["ultimo_pedido"] is None or creado > fila["ultimo_pedido"]:
                fila["ultimo_pedido"] = creado

        return [
            {**f, "ultimo_pedido": f["ultimo_pedido"].isoformat()}
            for f in sorted(canales.values(), key=lambda f: f["canal"])
        ]
