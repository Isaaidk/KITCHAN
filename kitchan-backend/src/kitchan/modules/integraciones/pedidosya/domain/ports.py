"""Dominio de la integración PedidosYa: puertos de salida hacia el
Integration Middleware API de PedidosYa (la API que YA existe y que
nosotros consumimos) y hacia el mapeo de vendors dado de alta manualmente.
"""

from abc import ABC, abstractmethod
from typing import Optional


class PedidosYaApiPort(ABC):
    """
    Puerto exclusivo para la comunicación HTTP con el Integration Middleware
    API de PedidosYa. Es el equivalente a UberApiPort, pero acotado a las
    dos operaciones que tienen paridad directa con las acciones del KDS de
    Uber (accept/deny/cancel -> update_order_status, ready -> mark_order_prepared).
    """

    @abstractmethod
    async def update_order_status(
        self, remote_order_id: str, status: str, reason: str | None = None
    ) -> bool:
        """Actualiza el estado de un pedido (aceptar/rechazar/cancelar)."""
        pass

    @abstractmethod
    async def mark_order_prepared(self, remote_order_id: str) -> bool:
        """Marca un pedido como listo para recoger."""
        pass


class PedidosYaVendorMappingPort(ABC):
    """
    Puerto para resolver el `remoteId` que PedidosYa manda en la URL del POST
    de dispatch hacia el `restaurante_id` interno de KITCHAN.

    A diferencia de Uber (que descubre las tiendas dinámicamente vía OAuth
    después de que el merchant autoriza la conexión desde la UI), en
    PedidosYa el remoteId lo elegimos nosotros mismos durante el alta manual
    (NDA + formulario con el contacto de cuenta) — por eso este mapeo es
    estático/configurado de antemano, no un flujo de autodescubrimiento en
    tiempo de ejecución.
    """

    @abstractmethod
    async def get_restaurante_id(self, remote_id: str) -> Optional[str]:
        pass
