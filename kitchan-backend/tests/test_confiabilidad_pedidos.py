"""Tests de confiabilidad de pedidos: pedidos duplicados (webhooks repetidos o
simultáneos), estados finales que no se reabren, cambios simultáneos de dos
operadores y cancelación automática configurable.
"""

import uuid

import pytest

from src.kitchan.modules.pedidos.application.actualizar_estado_pedido_service import (
    ActualizarEstadoPedidoUseCase,
)
from src.kitchan.modules.pedidos.application.crear_pedido_service import (
    CrearPedidoUseCase,
)
from src.kitchan.modules.pedidos.application.ports import NotificadorEventosPort
from src.kitchan.modules.pedidos.domain.entities import EstadoPedido, Pedido, PedidoItem
from src.kitchan.modules.pedidos.domain.exceptions import PedidoDuplicadoError
from src.kitchan.modules.pedidos.infrastructure.adapters.memory_repository import (
    MemoryPedidoRepository,
)
from src.kitchan.modules.pedidos.infrastructure.repository import (
    PostgresPedidoRepository,
)
from src.kitchan.modules.pedidos.infrastructure.tareas.auto_cancelar import (
    MINUTOS_LIMITE_POR_DEFECTO,
    minutos_limite,
)
from src.kitchan.modules.usuarios.infrastructure.security import JWTTokenGenerator

RESTAURANTE = str(uuid.uuid4())


class NotificadorContador(NotificadorEventosPort):
    def __init__(self):
        self.creados = 0
        self.actualizados = 0

    async def notificar_pedido_creado(self, pedido: Pedido) -> None:
        self.creados += 1

    async def notificar_pedido_actualizado(self, pedido: Pedido) -> None:
        self.actualizados += 1


def _pedido(origen="RAPPI", id_externo="R-1", estado=EstadoPedido.NUEVA) -> Pedido:
    return Pedido(
        restaurante_id=RESTAURANTE,
        origen=origen,
        id_externo=id_externo,
        cliente="Cliente Test",
        items=[PedidoItem(nombre="Papas", cantidad=1, precio_unitario=5.0)],
        total=5.0,
        estado=estado,
    )


# --------------------------------------------------------------------------
# Pedidos duplicados
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pedido_repetido_devuelve_el_mismo_y_no_avisa_dos_veces():
    repo = MemoryPedidoRepository()
    notificador = NotificadorContador()
    caso = CrearPedidoUseCase(repository=repo, notificador=notificador)

    primero = await caso.ejecutar(_pedido())
    segundo = await caso.ejecutar(_pedido())

    assert primero == segundo
    assert len(repo.db) == 1
    assert notificador.creados == 1


@pytest.mark.asyncio
async def test_mismo_id_en_otra_plataforma_no_es_duplicado():
    repo = MemoryPedidoRepository()
    caso = CrearPedidoUseCase(repository=repo)

    await caso.ejecutar(_pedido(origen="RAPPI", id_externo="X-1"))
    await caso.ejecutar(_pedido(origen="PEDIDOS_YA", id_externo="X-1"))

    assert len(repo.db) == 2


@pytest.mark.asyncio
async def test_pedidos_sin_id_externo_no_se_consideran_duplicados():
    repo = MemoryPedidoRepository()
    caso = CrearPedidoUseCase(repository=repo)

    await caso.ejecutar(_pedido(origen="LOCAL", id_externo=None))
    await caso.ejecutar(_pedido(origen="LOCAL", id_externo=None))

    assert len(repo.db) == 2


class RepoQuePierdeLaCarrera(MemoryPedidoRepository):
    """Simula dos webhooks iguales a la vez: al consultar todavía no existe,
    pero cuando se intenta guardar el otro ya lo guardó."""

    def __init__(self, existente: Pedido):
        super().__init__()
        self.existente = existente
        self.consultas = 0

    async def buscar_por_id_externo(self, origen, id_externo):
        self.consultas += 1
        return None if self.consultas == 1 else self.existente

    async def guardar(self, pedido):
        raise PedidoDuplicadoError(f"{pedido.origen} {pedido.id_externo}")


@pytest.mark.asyncio
async def test_carrera_de_webhooks_simultaneos_devuelve_el_pedido_ganador():
    existente = _pedido()
    notificador = NotificadorContador()
    caso = CrearPedidoUseCase(
        repository=RepoQuePierdeLaCarrera(existente), notificador=notificador
    )

    resultado = await caso.ejecutar(_pedido())

    assert resultado == existente.id
    assert notificador.creados == 0


@pytest.mark.asyncio
async def test_la_base_rechaza_el_duplicado_por_plataforma(db_session):
    repo = PostgresPedidoRepository(session=db_session)
    await repo.guardar(_pedido(origen="RAPPI", id_externo="D-1"))

    with pytest.raises(PedidoDuplicadoError):
        await repo.guardar(_pedido(origen="RAPPI", id_externo="D-1"))

    # La sesión sigue usable tras el rechazo y solo hay un pedido.
    existente = await repo.buscar_por_id_externo("RAPPI", "D-1")
    assert existente is not None
    pedidos, total = await repo.listar_por_restaurante(RESTAURANTE)
    assert total == 1


@pytest.mark.asyncio
async def test_la_base_permite_mismo_id_en_otra_plataforma_y_sin_id(db_session):
    repo = PostgresPedidoRepository(session=db_session)

    await repo.guardar(_pedido(origen="RAPPI", id_externo="D-2"))
    await repo.guardar(_pedido(origen="UBER_EATS", id_externo="D-2"))
    await repo.guardar(_pedido(origen="LOCAL", id_externo=None))
    await repo.guardar(_pedido(origen="LOCAL", id_externo=None))

    _, total = await repo.listar_por_restaurante(RESTAURANTE)
    assert total == 4


@pytest.mark.asyncio
async def test_crear_pedido_repetido_con_la_base_real_deja_uno_solo(db_session):
    repo = PostgresPedidoRepository(session=db_session)
    caso = CrearPedidoUseCase(repository=repo)

    primero = await caso.ejecutar(_pedido(id_externo="D-3"))
    segundo = await caso.ejecutar(_pedido(id_externo="D-3"))

    assert primero == segundo
    _, total = await repo.listar_por_restaurante(RESTAURANTE)
    assert total == 1


# --------------------------------------------------------------------------
# Estados finales y cambios simultáneos
# --------------------------------------------------------------------------


async def _con_estado(repo: MemoryPedidoRepository, estado: EstadoPedido) -> Pedido:
    pedido = _pedido(estado=estado)
    await repo.guardar(pedido)
    return pedido


@pytest.mark.asyncio
@pytest.mark.parametrize("final", [EstadoPedido.ENTREGADA, EstadoPedido.CANCELADA])
@pytest.mark.parametrize("nuevo", [EstadoPedido.NUEVA, EstadoPedido.EN_PREPARACION])
async def test_un_pedido_finalizado_no_se_reabre(final, nuevo):
    repo = MemoryPedidoRepository()
    notificador = NotificadorContador()
    pedido = await _con_estado(repo, final)
    caso = ActualizarEstadoPedidoUseCase(repository=repo, notificador=notificador)

    resultado = await caso.ejecutar_por_id(pedido.id, nuevo)

    assert resultado.estado == final
    assert repo.db[pedido.id].estado == final
    assert notificador.actualizados == 0


@pytest.mark.asyncio
async def test_repetir_el_mismo_estado_no_avisa_otra_vez():
    repo = MemoryPedidoRepository()
    notificador = NotificadorContador()
    pedido = await _con_estado(repo, EstadoPedido.EN_PREPARACION)
    caso = ActualizarEstadoPedidoUseCase(repository=repo, notificador=notificador)

    resultado = await caso.ejecutar_por_id(pedido.id, EstadoPedido.EN_PREPARACION)

    assert resultado.estado == EstadoPedido.EN_PREPARACION
    assert notificador.actualizados == 0


class RepoConCambioSimultaneo(MemoryPedidoRepository):
    """Otro operador mueve el pedido justo entre la lectura y la escritura."""

    async def actualizar_estado(self, pedido_id, nuevo_estado, estado_esperado=None):
        if estado_esperado is not None:
            self.db[pedido_id].estado = EstadoPedido.EN_PREPARACION
        return await super().actualizar_estado(pedido_id, nuevo_estado, estado_esperado)


@pytest.mark.asyncio
async def test_cambio_simultaneo_no_pisa_el_del_otro_operador():
    repo = RepoConCambioSimultaneo()
    notificador = NotificadorContador()
    pedido = await _con_estado(repo, EstadoPedido.NUEVA)
    caso = ActualizarEstadoPedidoUseCase(repository=repo, notificador=notificador)

    resultado = await caso.ejecutar_por_id(pedido.id, EstadoPedido.CANCELADA)

    # Gana el cambio del otro operador; el nuestro no se aplica ni se avisa.
    assert resultado.estado == EstadoPedido.EN_PREPARACION
    assert repo.db[pedido.id].estado == EstadoPedido.EN_PREPARACION
    assert notificador.actualizados == 0


@pytest.mark.asyncio
async def test_la_base_solo_cambia_si_el_estado_sigue_igual(db_session):
    repo = PostgresPedidoRepository(session=db_session)
    pedido = await repo.guardar(_pedido(id_externo="E-1"))

    assert await repo.actualizar_estado(
        pedido.id, "EN_PREPARACION", estado_esperado="NUEVA"
    )
    # El segundo intento parte de un estado que ya no es el real.
    assert not await repo.actualizar_estado(
        pedido.id, "CANCELADA", estado_esperado="NUEVA"
    )
    actual = await repo.buscar_por_id(pedido.id)
    assert actual.estado == EstadoPedido.EN_PREPARACION


def _headers() -> dict:
    token = JWTTokenGenerator().generar_token(
        {
            "sub": "operador@test.com",
            "id": str(uuid.uuid4()),
            "rol": "OPERADOR",
            "restaurante_id": RESTAURANTE,
        }
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_completar_un_pedido_cancelado_responde_409(client, db_session):
    repo = PostgresPedidoRepository(session=db_session)
    pedido = await repo.guardar(
        _pedido(id_externo="E-2", estado=EstadoPedido.CANCELADA)
    )

    respuesta = await client.post(
        f"/api/v1/pedidos/{pedido.id}/completar", headers=_headers()
    )

    assert respuesta.status_code == 409
    assert "CANCELADA" in respuesta.json()["detail"]


@pytest.mark.asyncio
async def test_completar_un_pedido_listo_responde_200(client, db_session, monkeypatch):
    # El endpoint crea su notificador (Redis) directamente; en test no hay Redis.
    monkeypatch.setattr(
        "src.kitchan.modules.pedidos.infrastructure.rest_api.construir_notificador",
        lambda: NotificadorContador(),
    )
    repo = PostgresPedidoRepository(session=db_session)
    pedido = await repo.guardar(_pedido(id_externo="E-3", estado=EstadoPedido.LISTA))

    respuesta = await client.post(
        f"/api/v1/pedidos/{pedido.id}/completar", headers=_headers()
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "ENTREGADA"


# --------------------------------------------------------------------------
# Cancelación automática configurable
# --------------------------------------------------------------------------


def test_minutos_de_auto_cancelacion_por_defecto(monkeypatch):
    monkeypatch.delenv("AUTO_CANCELAR_MINUTOS", raising=False)
    assert minutos_limite() == MINUTOS_LIMITE_POR_DEFECTO == 20


def test_minutos_de_auto_cancelacion_configurados(monkeypatch):
    monkeypatch.setenv("AUTO_CANCELAR_MINUTOS", "35")
    assert minutos_limite() == 35


@pytest.mark.parametrize("valor", ["", "abc", "0", "-5", "1.5"])
def test_minutos_invalidos_usan_el_valor_por_defecto(monkeypatch, valor):
    monkeypatch.setenv("AUTO_CANCELAR_MINUTOS", valor)
    assert minutos_limite() == MINUTOS_LIMITE_POR_DEFECTO
