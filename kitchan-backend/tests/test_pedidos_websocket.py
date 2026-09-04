import pytest

from src.kitchan.core.security import crear_access_token
from src.kitchan.modules.pedidos.application.actualizar_estado_pedido_service import (
    ActualizarEstadoPedidoUseCase,
)
from src.kitchan.modules.pedidos.application.crear_pedido_service import CrearPedidoUseCase
from src.kitchan.modules.pedidos.application.ports import NotificadorEventosPort
from src.kitchan.modules.pedidos.domain.entities import EstadoPedido, Pedido, PedidoItem
from src.kitchan.modules.pedidos.infrastructure.adapters.memory_repository import (
    MemoryPedidoRepository,
)


class NotificadorFake(NotificadorEventosPort):
    """Reemplaza a RedisPublisherAdapter en tests: solo registra las llamadas."""

    def __init__(self):
        self.eventos: list[tuple[str, Pedido]] = []

    async def notificar_pedido_creado(self, pedido: Pedido) -> None:
        self.eventos.append(("PEDIDO_CREADO", pedido))

    async def notificar_pedido_actualizado(self, pedido: Pedido) -> None:
        self.eventos.append(("PEDIDO_ACTUALIZADO", pedido))


def _pedido_de_prueba() -> Pedido:
    return Pedido(
        restaurante_id="rest-1",
        origen="UBER_EATS",
        id_externo="uber-order-1",
        cliente="Cliente Prueba",
        items=[PedidoItem(nombre="Hamburguesa", cantidad=1, precio_unitario=10.0)],
        total=10.0,
    )


@pytest.mark.asyncio
async def test_crear_pedido_notifica_al_orquestador():
    """El caso de uso que crea un pedido debe notificar automáticamente
    (requisito: 'el orquestador de pedidos debe emitir eventos WS
    automáticamente cuando ingrese un pedido')."""
    repo = MemoryPedidoRepository()
    notificador = NotificadorFake()
    caso_uso = CrearPedidoUseCase(repository=repo, notificador=notificador)

    await caso_uso.ejecutar(_pedido_de_prueba())

    assert len(notificador.eventos) == 1
    tipo, pedido = notificador.eventos[0]
    assert tipo == "PEDIDO_CREADO"
    assert pedido.restaurante_id == "rest-1"


@pytest.mark.asyncio
async def test_crear_pedido_sin_notificador_no_falla():
    """El notificador es opcional: sin él, la creación debe seguir funcionando."""
    repo = MemoryPedidoRepository()
    caso_uso = CrearPedidoUseCase(repository=repo)

    pedido_id = await caso_uso.ejecutar(_pedido_de_prueba())

    assert pedido_id is not None


@pytest.mark.asyncio
async def test_actualizar_estado_por_id_externo_notifica():
    """Requisito: '...o cambie de estado un pedido de Uber' también debe notificar."""
    repo = MemoryPedidoRepository()
    notificador = NotificadorFake()
    await CrearPedidoUseCase(repository=repo).ejecutar(_pedido_de_prueba())

    caso_uso = ActualizarEstadoPedidoUseCase(repository=repo, notificador=notificador)
    pedido = await caso_uso.ejecutar_por_id_externo(
        "UBER_EATS", "uber-order-1", EstadoPedido.EN_PREPARACION
    )

    assert pedido is not None
    assert pedido.estado == EstadoPedido.EN_PREPARACION
    assert notificador.eventos[-1][0] == "PEDIDO_ACTUALIZADO"


@pytest.mark.asyncio
async def test_cancelar_pedido_listo_no_lo_degrada():
    """Regla de negocio: si el pedido ya llegó a LISTA, un intento de
    cancelación posterior (ej. courier nunca llegó, Uber cancela la
    entrega) NO debe revertirlo a CANCELADA — la cocina ya cumplió."""
    repo = MemoryPedidoRepository()
    notificador = NotificadorFake()
    await CrearPedidoUseCase(repository=repo).ejecutar(_pedido_de_prueba())
    caso_uso = ActualizarEstadoPedidoUseCase(repository=repo, notificador=notificador)
    await caso_uso.ejecutar_por_id_externo("UBER_EATS", "uber-order-1", EstadoPedido.LISTA)

    pedido = await caso_uso.ejecutar_por_id_externo(
        "UBER_EATS", "uber-order-1", EstadoPedido.CANCELADA
    )

    assert pedido is not None
    assert pedido.estado == EstadoPedido.LISTA
    assert notificador.eventos[-1][0] == "PEDIDO_ACTUALIZADO"  # el de LISTA, no uno nuevo


@pytest.mark.asyncio
async def test_cancelar_pedido_en_preparacion_si_se_cancela():
    """En cambio, antes de LISTA sí debe cancelarse con normalidad."""
    repo = MemoryPedidoRepository()
    notificador = NotificadorFake()
    await CrearPedidoUseCase(repository=repo).ejecutar(_pedido_de_prueba())
    caso_uso = ActualizarEstadoPedidoUseCase(repository=repo, notificador=notificador)
    await caso_uso.ejecutar_por_id_externo("UBER_EATS", "uber-order-1", EstadoPedido.EN_PREPARACION)

    pedido = await caso_uso.ejecutar_por_id_externo(
        "UBER_EATS", "uber-order-1", EstadoPedido.CANCELADA
    )

    assert pedido is not None
    assert pedido.estado == EstadoPedido.CANCELADA


@pytest.mark.asyncio
async def test_actualizar_estado_pedido_inexistente_no_notifica():
    repo = MemoryPedidoRepository()
    notificador = NotificadorFake()
    caso_uso = ActualizarEstadoPedidoUseCase(repository=repo, notificador=notificador)

    resultado = await caso_uso.ejecutar_por_id_externo(
        "UBER_EATS", "no-existe", EstadoPedido.LISTA
    )

    assert resultado is None
    assert notificador.eventos == []


def test_ws_pedidos_rechaza_token_invalido(ws_client):
    with pytest.raises(Exception):
        with ws_client.websocket_connect("/api/v1/pedidos/ws/pedidos?token=invalido"):
            pass


def test_ws_pedidos_acepta_token_valido(ws_client):
    token = crear_access_token(
        {"sub": "kds@test.com", "id": "1", "rol": "OPERADOR", "restaurante_id": "rest-1"}
    )
    with ws_client.websocket_connect(f"/api/v1/pedidos/ws/pedidos?token={token}") as ws:
        # La conexión se acepta (no se cierra inmediatamente); no hay
        # mensajes pendientes porque nada publicó en el canal de Redis.
        assert ws is not None
