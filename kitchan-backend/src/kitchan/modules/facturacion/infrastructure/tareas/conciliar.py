"""Barrido periódico de conciliación con Odoo: respaldo del webhook por si
Odoo no pudo avisar (KITCHAN caído, sin URL pública, etc.)."""

import asyncio
import logging

from src.kitchan.core.database import AsyncSessionLocal
from src.kitchan.core.tareas import propagar_si_cancelada
from src.kitchan.modules.facturacion.infrastructure.dependencias import (
    construir_conciliar_use_case,
)
from src.kitchan.modules.facturacion.infrastructure.odoo_json2_adapter import (
    OdooJson2Adapter,
)

logger = logging.getLogger(__name__)

INTERVALO_SEGUNDOS = 300


async def _bucle_conciliar() -> None:
    while True:
        await asyncio.sleep(INTERVALO_SEGUNDOS)
        try:
            async with AsyncSessionLocal() as session:
                caso_uso = construir_conciliar_use_case(session, OdooJson2Adapter())
                actualizadas = await caso_uso.ejecutar()
            if actualizadas:
                logger.info("🧾 %s facturas actualizadas desde Odoo.", actualizadas)
        except Exception:
            propagar_si_cancelada()
            logger.exception("Error en la conciliación de facturas con Odoo.")


def iniciar_conciliador_facturas() -> asyncio.Task:
    return asyncio.create_task(_bucle_conciliar())
