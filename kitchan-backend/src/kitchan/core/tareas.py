"""Utilidades para las tareas periódicas en segundo plano (auto-cancelación,
conciliación con Odoo, etc.)."""

import asyncio


def propagar_si_cancelada() -> None:
    """Llamar dentro de un `except Exception` de un bucle periódico.

    Si la tarea ya recibió `cancel()` (al apagar la app), una excepción
    derivada —por ejemplo la que SQLAlchemy lanza al cerrar la sesión en medio
    de la cancelación— no debe tragarse: de lo contrario el bucle sigue vivo,
    se duerme otra vez y el apagado queda esperando a que despierte.
    """
    tarea = asyncio.current_task()
    if tarea is not None and tarea.cancelling():
        raise asyncio.CancelledError
