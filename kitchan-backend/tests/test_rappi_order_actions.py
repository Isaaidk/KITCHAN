"""Tests unitarios de las acciones de Rappi (accept/deny/ready y error de
autenticación con el proveedor), con fakes en memoria — mismo estilo que
test_pedidosya_order_actions.py. Incluye un test HTTP que verifica que las
rutas del KDS exigen un usuario autenticado.
"""

import pytest

from src.kitchan.modules.integraciones.rappi.application.order_use_cases import (
    RappiOrderUseCase,
)
from src.kitchan.modules.integraciones.rappi.domain.ports import RappiApiPort
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


class FakeRappiApi(RappiApiPort):
    """Reemplaza a RappiHttpAdapter en tests: nunca llama a la red."""

    def __init__(self, fallar_auth: bool = False):
        self.fallar_auth = fallar_auth
        self.llamadas: list[tuple] = []

    def _verificar_auth(self):
        if self.fallar_auth:
            raise ValueError(
                "Credenciales de Rappi (client_id/client_secret) no configuradas."
            )

    async def take_order(self, order_id, cooking_time=None):
        self._verificar_auth()
        self.llamadas.append(("take", order_id, cooking_time))
        return True

    async def reject_order(self, order_id, reason, cancel_type):
        self._verificar_auth()
        self.llamadas.append(("reject", order_id, reason, cancel_type))
        return True

    async def mark_ready_for_pickup(self, order_id):
        self._verificar_auth()
        self.llamadas.append(("ready", order_id))
        return True


def _armar_caso_de_uso(
    api: RappiApiPort,
) -> tuple[RappiOrderUseCase, MemoryPedidoRepository]:
    repo = MemoryPedidoRepository()
    crear_pedido_uc = CrearPedidoUseCase(repository=repo)
    actualizar_estado_uc = ActualizarEstadoPedidoUseCase(repository=repo)
    dispatcher = PedidosIntegracionesAdapter(
        use_case=crear_pedido_uc, actualizar_estado_use_case=actualizar_estado_uc
    )
    return RappiOrderUseCase(rappi_api=api, order_dispatcher=dispatcher), repo


async def _crear_pedido_previo(repo: MemoryPedidoRepository, order_id: str) -> None:
    await repo.guardar(
        Pedido(
            restaurante_id="rest-1",
            origen="RAPPI",
            id_externo=order_id,
            cliente="Cliente Test",
            items=[PedidoItem(nombre="Pizza", cantidad=1, precio_unitario=10.0)],
            total=10.0,
            estado=EstadoPedido.NUEVA,
        )
    )


@pytest.mark.asyncio
async def test_accept_order_actualiza_estado_a_en_preparacion():
    api = FakeRappiApi()
    use_case, repo = _armar_caso_de_uso(api)
    await _crear_pedido_previo(repo, "R-1")

    resultado = await use_case.accept_order_in_rappi("R-1", cooking_time=20)

    assert resultado is True
    assert ("take", "R-1", 20) in api.llamadas
    pedido = await repo.buscar_por_id_externo("RAPPI", "R-1")
    assert pedido.estado == EstadoPedido.EN_PREPARACION


@pytest.mark.asyncio
async def test_deny_order_actualiza_estado_a_cancelada():
    api = FakeRappiApi()
    use_case, repo = _armar_caso_de_uso(api)
    await _crear_pedido_previo(repo, "R-2")

    await use_case.deny_order_in_rappi(
        "R-2", reason="Sin stock", cancel_type="ITEM_OUT_OF_STOCK"
    )

    assert ("reject", "R-2", "Sin stock", "ITEM_OUT_OF_STOCK") in api.llamadas
    pedido = await repo.buscar_por_id_externo("RAPPI", "R-2")
    assert pedido.estado == EstadoPedido.CANCELADA


@pytest.mark.asyncio
async def test_mark_ready_actualiza_estado_a_lista():
    api = FakeRappiApi()
    use_case, repo = _armar_caso_de_uso(api)
    await _crear_pedido_previo(repo, "R-3")

    await use_case.mark_order_ready_in_rappi("R-3")

    pedido = await repo.buscar_por_id_externo("RAPPI", "R-3")
    assert pedido.estado == EstadoPedido.LISTA


@pytest.mark.asyncio
async def test_accept_order_sin_credenciales_de_rappi_propaga_error():
    """Si las credenciales de Rappi no están configuradas, el caso de uso no
    debe tragarse el error ni tocar el estado del pedido."""
    api = FakeRappiApi(fallar_auth=True)
    use_case, repo = _armar_caso_de_uso(api)
    await _crear_pedido_previo(repo, "R-4")

    with pytest.raises(ValueError):
        await use_case.accept_order_in_rappi("R-4")

    pedido = await repo.buscar_por_id_externo("RAPPI", "R-4")
    assert pedido.estado == EstadoPedido.NUEVA


@pytest.mark.asyncio
async def test_acciones_kds_sin_usuario_autenticado_retornan_401(client):
    for accion in ("accept", "ready"):
        respuesta = await client.post(
            f"/api/v1/integraciones/rappi/orders/R-5/{accion}"
        )
        assert respuesta.status_code == 401
