"""Tests del caso de uso de Facturación con un puerto de Odoo falso."""

import pytest

from src.kitchan.modules.facturacion.application.sincronizar_factura import (
    SincronizarFacturaPedidoUseCase,
)
from src.kitchan.modules.facturacion.domain.ports import OdooSyncPort
from src.kitchan.modules.facturacion.infrastructure.odoo_client import (
    OdooXmlRpcAdapter,
)


class OdooFalso(OdooSyncPort):
    def __init__(self, respuesta: bool):
        self.respuesta = respuesta
        self.pedidos: list[str] = []

    async def sincronizar_factura(self, pedido_id: str) -> bool:
        self.pedidos.append(pedido_id)
        return self.respuesta


@pytest.mark.asyncio
async def test_sincroniza_la_factura_del_pedido():
    odoo = OdooFalso(respuesta=True)

    assert await SincronizarFacturaPedidoUseCase(odoo).ejecutar("pedido-1") is True
    assert odoo.pedidos == ["pedido-1"]


@pytest.mark.asyncio
async def test_sin_id_de_pedido_no_llama_a_odoo():
    odoo = OdooFalso(respuesta=True)

    with pytest.raises(ValueError):
        await SincronizarFacturaPedidoUseCase(odoo).ejecutar("")
    assert odoo.pedidos == []


@pytest.mark.asyncio
async def test_sin_credenciales_de_odoo_no_sincroniza(monkeypatch):
    for variable in ("ODOO_URL", "ODOO_DB", "ODOO_USERNAME", "ODOO_API_KEY"):
        monkeypatch.delenv(variable, raising=False)

    caso_de_uso = SincronizarFacturaPedidoUseCase(OdooXmlRpcAdapter())

    assert await caso_de_uso.ejecutar("pedido-2") is False
