"""Método de pago y momentos de cocina de los pedidos: normalización, captura
desde Rappi y marcas de tiempo al cambiar de estado."""

import uuid

import pytest

from src.kitchan.modules.integraciones.core.domain.metodos_pago import (
    normalizar_metodo_pago,
)
from src.kitchan.modules.pedidos.domain.entities import (
    EstadoPedido,
    Pedido,
    PedidoItem,
)
from src.kitchan.modules.pedidos.infrastructure.repository import (
    PostgresPedidoRepository,
)


@pytest.mark.parametrize(
    "crudo, esperado",
    [
        ("cc", "TARJETA"),
        ("CC", "TARJETA"),
        ("credit-card", "TARJETA"),
        ("cash", "EFECTIVO"),
        (" Efectivo ", "EFECTIVO"),
        ("rappi_pay", "BILLETERA"),
        ("online", "ONLINE"),
        ("bank transfer", "TRANSFERENCIA"),
        # Un código desconocido se conserva (sin inventar su significado).
        ("cheque", "CHEQUE"),
    ],
)
def test_normaliza_los_codigos_de_pago_de_los_canales(crudo, esperado):
    assert normalizar_metodo_pago(crudo) == esperado


@pytest.mark.parametrize("vacio", [None, "", "   "])
def test_sin_dato_de_pago_devuelve_none(vacio):
    assert normalizar_metodo_pago(vacio) is None


async def _guardar(db_session, **extra):
    repo = PostgresPedidoRepository(session=db_session)
    pedido = await repo.guardar(
        Pedido(
            restaurante_id=str(uuid.uuid4()),
            origen="RAPPI",
            cliente="Cliente",
            items=[PedidoItem(nombre="Papas", cantidad=1, precio_unitario=5.0)],
            total=5.0,
            **extra,
        )
    )
    return repo, pedido


@pytest.mark.asyncio
async def test_el_pedido_guarda_su_metodo_de_pago(db_session):
    repo, pedido = await _guardar(db_session, metodo_pago="TARJETA")

    guardado = await repo.buscar_por_id(pedido.id)

    assert guardado.metodo_pago == "TARJETA"
    assert guardado.fecha_aceptacion is None and guardado.fecha_lista is None


@pytest.mark.asyncio
async def test_sin_metodo_de_pago_queda_vacio(db_session):
    repo, pedido = await _guardar(db_session)

    assert (await repo.buscar_por_id(pedido.id)).metodo_pago is None


@pytest.mark.asyncio
async def test_marca_cuando_la_cocina_acepta_y_termina_solo_la_primera_vez(db_session):
    repo, pedido = await _guardar(db_session)

    await repo.actualizar_estado(pedido.id, EstadoPedido.EN_PREPARACION.value)
    en_preparacion = await repo.buscar_por_id(pedido.id)
    assert en_preparacion.fecha_aceptacion is not None
    assert en_preparacion.fecha_lista is None

    await repo.actualizar_estado(pedido.id, EstadoPedido.LISTA.value)
    lista = await repo.buscar_por_id(pedido.id)
    assert lista.fecha_lista is not None
    assert lista.fecha_aceptacion == en_preparacion.fecha_aceptacion

    # Repetir un estado no pisa el momento ya guardado.
    primera_lista = lista.fecha_lista
    await repo.actualizar_estado(pedido.id, EstadoPedido.LISTA.value)
    assert (await repo.buscar_por_id(pedido.id)).fecha_lista == primera_lista
