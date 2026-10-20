"""Casos de uso de Facturación.

KITCHAN no firma ni envía comprobantes al SRI: le pide a Odoo que emita la
factura del pedido (Odoo firma con el certificado de la empresa y la envía
al SRI) y guarda el resultado. Después, el estado se actualiza cuando Odoo
avisa por webhook o en el barrido periódico de conciliación.
"""

import logging
from typing import Optional

from src.kitchan.modules.facturacion.domain.entities import (
    DatosFactura,
    EstadoFactura,
    FacturaPedido,
)
from src.kitchan.modules.facturacion.domain.exceptions import (
    OdooError,
    OdooNoConfiguradoError,
    PedidoNoEncontradoError,
    PedidoNoFacturableError,
)
from src.kitchan.modules.facturacion.domain.ports import (
    FacturaRepositoryPort,
    OdooFacturacionPort,
    PedidosFacturablesPort,
)

logger = logging.getLogger(__name__)

# Se factura lo que la cocina ya preparó: un pedido nuevo todavía se puede
# rechazar y uno cancelado no es una venta.
ESTADOS_FACTURABLES = {"LISTA", "ENTREGADA"}


def referencia_de(pedido_id: str) -> str:
    return f"KITCHAN-{pedido_id}"


class FacturarPedidoUseCase:
    def __init__(
        self,
        odoo: OdooFacturacionPort,
        facturas: FacturaRepositoryPort,
        pedidos: PedidosFacturablesPort,
    ):
        self.odoo = odoo
        self.facturas = facturas
        self.pedidos = pedidos

    async def ejecutar(self, pedido_id: str, restaurante_id: str) -> FacturaPedido:
        pedido = await self.pedidos.obtener(pedido_id)
        if pedido is None or pedido.restaurante_id != restaurante_id:
            raise PedidoNoEncontradoError("Pedido no encontrado.")
        if not self.odoo.configurado():
            raise OdooNoConfiguradoError("Odoo no está configurado en KITCHAN.")

        existente = await self.facturas.buscar_por_pedido(pedido_id)
        if existente is not None:
            # Idempotente: un segundo clic no crea otra factura. Si quedó con
            # error, se reintenta el envío al SRI de la misma factura.
            if existente.estado != EstadoFactura.CON_ERROR:
                return existente
            resultado = await self.odoo.reenviar_al_sri(existente.odoo_move_id)
            return await self.facturas.guardar(existente.aplicar(resultado))

        if pedido.estado not in ESTADOS_FACTURABLES:
            raise PedidoNoFacturableError(
                "Solo se facturan pedidos listos o entregados."
            )
        lineas = [linea for linea in pedido.items if linea.cantidad > 0]
        if not lineas:
            raise PedidoNoFacturableError("El pedido no tiene productos para facturar.")

        origen = f"{pedido.origen} {pedido.id_externo or pedido.id}"
        resultado = await self.odoo.emitir_factura(
            DatosFactura(
                referencia=referencia_de(pedido.id), origen=origen, lineas=lineas
            )
        )
        logger.info(
            "Factura %s del pedido %s emitida en Odoo (%s).",
            resultado.numero,
            pedido.id,
            resultado.estado.value,
        )
        return await self.facturas.guardar(
            FacturaPedido(
                pedido_id=pedido.id,
                restaurante_id=pedido.restaurante_id,
                **resultado.model_dump(),
            )
        )


class ConsultarFacturaPedidoUseCase:
    def __init__(self, facturas: FacturaRepositoryPort):
        self.facturas = facturas

    async def ejecutar(
        self, pedido_id: str, restaurante_id: str
    ) -> Optional[FacturaPedido]:
        factura = await self.facturas.buscar_por_pedido(pedido_id)
        if factura is None or factura.restaurante_id != restaurante_id:
            return None
        return factura


class ActualizarFacturaDesdeOdooUseCase:
    """Lo usa el webhook de Odoo. No confía en el cuerpo del webhook: vuelve
    a leer la factura en Odoo con la API."""

    def __init__(self, odoo: OdooFacturacionPort, facturas: FacturaRepositoryPort):
        self.odoo = odoo
        self.facturas = facturas

    async def ejecutar(self, odoo_move_id: int) -> Optional[FacturaPedido]:
        factura = await self.facturas.buscar_por_odoo_move(odoo_move_id)
        if factura is None:
            # Factura de Odoo que no salió de KITCHAN (p. ej. del punto de venta).
            return None
        resultado = await self.odoo.consultar_factura(odoo_move_id)
        return await self.facturas.guardar(factura.aplicar(resultado))


class ConciliarFacturasPendientesUseCase:
    """Respaldo del webhook: revisa en Odoo las facturas que siguen
    esperando al SRI y pide procesar el envío otra vez."""

    def __init__(self, odoo: OdooFacturacionPort, facturas: FacturaRepositoryPort):
        self.odoo = odoo
        self.facturas = facturas

    async def ejecutar(self) -> int:
        if not self.odoo.configurado():
            return 0
        actualizadas = 0
        for factura in await self.facturas.listar_pendientes():
            try:
                resultado = await self.odoo.reenviar_al_sri(factura.odoo_move_id)
            except OdooError as error:
                # Una factura que falla no detiene la revisión de las demás.
                logger.warning(
                    "No se pudo conciliar la factura %s: %s", factura.numero, error
                )
                continue
            if resultado.estado != factura.estado:
                actualizadas += 1
            await self.facturas.guardar(factura.aplicar(resultado))
        return actualizadas
