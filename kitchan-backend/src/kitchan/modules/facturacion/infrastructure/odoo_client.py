import logging
import os

from src.kitchan.modules.facturacion.domain.ports import OdooSyncPort

logger = logging.getLogger(__name__)


class OdooXmlRpcAdapter(OdooSyncPort):
    """
    Adaptador stub: deja lista la forma del futuro cliente XML-RPC de Odoo
    (protocolo confirmado con negocio) sin implementar la llamada real, ya
    que hoy no hay credenciales de una instancia Odoo para probar contra
    ella. Cuando existan (ODOO_URL/ODOO_DB/ODOO_USERNAME/ODOO_API_KEY), este
    adaptador se completa con xmlrpc.client sin tocar el puerto ni quien lo
    consume.
    """

    def __init__(self):
        self.url = os.getenv("ODOO_URL")
        self.db = os.getenv("ODOO_DB")
        self.username = os.getenv("ODOO_USERNAME")
        self.api_key = os.getenv("ODOO_API_KEY")

    async def sincronizar_factura(self, pedido_id: str) -> bool:
        if not all([self.url, self.db, self.username, self.api_key]):
            logger.info(
                "Odoo no configurado (faltan ODOO_URL/ODOO_DB/ODOO_USERNAME/"
                "ODOO_API_KEY) — sincronización de factura omitida para el "
                "pedido %s.",
                pedido_id,
            )
            return False

        raise NotImplementedError(
            "Integración real con Odoo (XML-RPC) pendiente de implementar."
        )
