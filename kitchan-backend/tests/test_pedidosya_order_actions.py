"""Tests unitarios de las acciones de PedidosYa (accept/ready y error de
autenticación con el proveedor), con fakes en memoria — mismo estilo que
test_pedidos_websocket.py (fakes, sin mocks de librerías externas).
"""

import pytest

from src.kitchan.modules.integraciones.core.domain.entities import (
    KitchanOrderDTO,
    KitchanOrderItem,
)
from src.kitchan.modules.integraciones.pedidosya.application.order_use_cases import (
    PedidosYaOrderUseCase,
)
from src.kitchan.modules.integraciones.pedidosya.domain.ports import PedidosYaApiPort
from src.kitchan.modules.pedidos.application.actualizar_estado_pedido_service import (
    ActualizarEstadoPedidoUseCase,
)
from src.kitchan.modules.pedidos.application.crear_pedido_service import (
    CrearPedidoUseCase,
)
from src.kitchan.modules.pedidos.domain.entities import EstadoPedido, Pedido, PedidoItem
from src.kitchan.modules.pedidos.infrastructure.adapters.integraciones_dispatcher import (
    PedidosIntegracionesAdapter,
)
from src.kitchan.modules.pedidos.infrastructure.adapters.memory_repository import (
    MemoryPedidoRepository,
)


class FakePedidosYaApi(PedidosYaApiPort):
    """Reemplaza a PedidosYaHttpAdapter en tests: nunca llama a la red."""

    def __init__(self, fallar_auth: bool = False):
        self.fallar_auth = fallar_auth
        self.llamadas: list[tuple] = []

    async def update_order_status(self, remote_order_id, status, reason=None):
        if self.fallar_auth:
            raise ValueError(
                "Credenciales de PedidosYa (plugin username/password) no configuradas."
            )
        self.llamadas.append(("status", remote_order_id, status, reason))
        return True

    async def mark_order_prepared(self, remote_order_id):
        if self.fallar_auth:
            raise ValueError(
                "Credenciales de PedidosYa (plugin username/password) no configuradas."
            )
        self.llamadas.append(("prepared", remote_order_id))
        return True


def _armar_caso_de_uso(
    api: PedidosYaApiPort,
) -> tuple[PedidosYaOrderUseCase, MemoryPedidoRepository]:
    repo = MemoryPedidoRepository()
    crear_pedido_uc = CrearPedidoUseCase(repository=repo)
    actualizar_estado_uc = ActualizarEstadoPedidoUseCase(repository=repo)
    dispatcher = PedidosIntegracionesAdapter(
        use_case=crear_pedido_uc, actualizar_estado_use_case=actualizar_estado_uc
    )
    return PedidosYaOrderUseCase(pedidosya_api=api, order_dispatcher=dispatcher), repo


async def _crear_pedido_previo(repo: MemoryPedidoRepository, order_id: str) -> None:
    dto = KitchanOrderDTO(
        id_externo=order_id,
        plataforma="PEDIDOS_YA",
        restaurante_id="rest-1",
        nombre_cliente="Cliente Test",
        items=[KitchanOrderItem(nombre="Pizza", cantidad=1, precio_unitario=10.0)],
        total=10.0,
    )
    pedido = Pedido(
        restaurante_id=dto.restaurante_id,
        origen=dto.plataforma,
        id_externo=dto.id_externo,
        cliente=dto.nombre_cliente,
        items=[
            PedidoItem(
                nombre=item.nombre,
                cantidad=item.cantidad,
                precio_unitario=item.precio_unitario,
            )
            for item in dto.items
        ],
        total=dto.total,
        estado=EstadoPedido.NUEVA,
    )
    await repo.guardar(pedido)


@pytest.mark.asyncio
async def test_accept_order_actualiza_estado_a_en_preparacion():
    api = FakePedidosYaApi()
    use_case, repo = _armar_caso_de_uso(api)
    await _crear_pedido_previo(repo, "PY-1")

    resultado = await use_case.accept_order_in_pedidosya("PY-1")

    assert resultado is True
    assert ("status", "PY-1", "CONFIRMED", None) in api.llamadas
    pedido = await repo.buscar_por_id_externo("PEDIDOS_YA", "PY-1")
    assert pedido.estado == EstadoPedido.EN_PREPARACION


@pytest.mark.asyncio
async def test_mark_ready_actualiza_estado_a_lista():
    api = FakePedidosYaApi()
    use_case, repo = _armar_caso_de_uso(api)
    await _crear_pedido_previo(repo, "PY-2")

    await use_case.mark_order_ready_in_pedidosya("PY-2")

    pedido = await repo.buscar_por_id_externo("PEDIDOS_YA", "PY-2")
    assert pedido.estado == EstadoPedido.LISTA


@pytest.mark.asyncio
async def test_accept_order_sin_credenciales_de_pedidosya_propaga_error():
    """Error de autenticación con el proveedor: si las credenciales de
    PedidosYa no están configuradas, el caso de uso no debe tragarse el
    error ni tocar el estado del pedido (mismo criterio que UberOrderUseCase
    cuando no hay token de Uber disponible)."""
    api = FakePedidosYaApi(fallar_auth=True)
    use_case, repo = _armar_caso_de_uso(api)
    await _crear_pedido_previo(repo, "PY-3")

    with pytest.raises(ValueError):
        await use_case.accept_order_in_pedidosya("PY-3")

    pedido = await repo.buscar_por_id_externo("PEDIDOS_YA", "PY-3")
    assert pedido.estado == EstadoPedido.NUEVA
