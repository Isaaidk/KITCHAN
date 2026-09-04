from abc import ABC, abstractmethod


class OdooSyncPort(ABC):
    """
    Puerto de salida para la futura integración con Odoo (verificación de
    facturas). La instancia de Odoo ya existe y está configurada fuera de
    KITCHAN; esta tarea solo deja la estructura hexagonal lista — sin
    implementación real ni endpoint expuesto en main.py.
    """

    @abstractmethod
    async def sincronizar_factura(self, pedido_id: str) -> bool:
        """Verifica/sincroniza la factura de un pedido contra Odoo."""
        pass
