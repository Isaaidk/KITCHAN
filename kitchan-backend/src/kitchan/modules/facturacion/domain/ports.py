from abc import ABC, abstractmethod
from typing import Optional

from src.kitchan.modules.facturacion.domain.entities import (
    DatosFactura,
    FacturaPedido,
    PedidoAFacturar,
    ResultadoOdoo,
)


class OdooFacturacionPort(ABC):
    """Puerto de salida hacia el ERP que emite la factura electrónica (Odoo).
    Odoo es quien firma el comprobante y lo envía al SRI."""

    @abstractmethod
    def configurado(self) -> bool:
        """True si hay credenciales para hablar con Odoo."""

    @abstractmethod
    async def emitir_factura(self, datos: DatosFactura) -> ResultadoOdoo:
        """Crea (o reutiliza, si ya existe con la misma referencia), publica
        y envía al SRI la factura. Debe ser idempotente por `referencia`."""

    @abstractmethod
    async def consultar_factura(self, odoo_move_id: int) -> ResultadoOdoo:
        """Lee el estado actual de la factura en Odoo, sin modificarla."""

    @abstractmethod
    async def reenviar_al_sri(self, odoo_move_id: int) -> ResultadoOdoo:
        """Pide a Odoo procesar de nuevo el envío al SRI y devuelve el estado."""


class FacturaRepositoryPort(ABC):
    @abstractmethod
    async def guardar(self, factura: FacturaPedido) -> FacturaPedido:
        """Inserta o actualiza la factura del pedido."""

    @abstractmethod
    async def buscar_por_pedido(self, pedido_id: str) -> Optional[FacturaPedido]:
        pass

    @abstractmethod
    async def buscar_por_odoo_move(self, odoo_move_id: int) -> Optional[FacturaPedido]:
        pass

    @abstractmethod
    async def listar_pendientes(self) -> list[FacturaPedido]:
        """Facturas que esperan respuesta del SRI."""


class PedidosFacturablesPort(ABC):
    """De dónde obtiene Facturación los datos del pedido."""

    @abstractmethod
    async def obtener(self, pedido_id: str) -> Optional[PedidoAFacturar]:
        pass
