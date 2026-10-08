"""Caso de uso de Facturación: sincronizar la factura de un pedido con Odoo.

Depende solo del puerto OdooSyncPort. Hoy el adaptador real
(infrastructure/odoo_client.py) responde False mientras no existan las
credenciales de Odoo; cuando estén, se completa el adaptador y este caso de
uso no cambia.
"""

import logging

from src.kitchan.modules.facturacion.domain.ports import OdooSyncPort

logger = logging.getLogger(__name__)


class SincronizarFacturaPedidoUseCase:
    def __init__(self, odoo: OdooSyncPort):
        self.odoo = odoo

    async def ejecutar(self, pedido_id: str) -> bool:
        """Retorna True si Odoo confirmó la factura del pedido."""
        if not pedido_id:
            raise ValueError(
                "Se necesita el id del pedido para sincronizar su factura."
            )

        sincronizado = await self.odoo.sincronizar_factura(pedido_id)
        if not sincronizado:
            logger.info(
                "La factura del pedido %s no se sincronizó con Odoo.", pedido_id
            )
        return sincronizado
