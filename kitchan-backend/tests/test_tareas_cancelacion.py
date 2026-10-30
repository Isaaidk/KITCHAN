"""Regresión del cuelgue al apagar la app: un bucle periódico que traga la
cancelación (porque una excepción derivada la sustituye, como la de SQLAlchemy
al cerrar la sesión) seguía vivo y dormía otros 60 s, y el apagado esperaba.
"""

import asyncio

import pytest

from src.kitchan.core.tareas import propagar_si_cancelada


@pytest.mark.asyncio
async def test_sin_cancelacion_no_hace_nada():
    propagar_si_cancelada()


async def _bucle(usar_ayuda: bool, listo: asyncio.Event):
    """Bucle como los de auto-cancelación y conciliación: una excepción derivada
    de la cancelación entra en su `except Exception`."""
    while True:
        try:
            listo.set()
            try:
                await asyncio.sleep(30)
            except asyncio.CancelledError:
                raise RuntimeError("excepción derivada de la cancelación")
        except Exception:
            if usar_ayuda:
                propagar_si_cancelada()
        await asyncio.sleep(30)


@pytest.mark.asyncio
async def test_el_bucle_termina_al_cancelarlo_aunque_la_cancelacion_se_convierta():
    listo = asyncio.Event()
    tarea = asyncio.create_task(_bucle(True, listo))
    await listo.wait()

    tarea.cancel()
    await asyncio.wait({tarea}, timeout=2)

    assert tarea.done()
    assert tarea.cancelled()


@pytest.mark.asyncio
async def test_sin_la_ayuda_el_bucle_seguiria_vivo():
    """Documenta el fallo original: sin `propagar_si_cancelada` la tarea sigue
    viva tras cancelarla."""
    listo = asyncio.Event()
    tarea = asyncio.create_task(_bucle(False, listo))
    await listo.wait()

    tarea.cancel()
    await asyncio.wait({tarea}, timeout=0.5)

    assert not tarea.done()
    tarea.cancel()  # limpieza: la segunda cancelación sí la mata
    await asyncio.wait({tarea}, timeout=2)
