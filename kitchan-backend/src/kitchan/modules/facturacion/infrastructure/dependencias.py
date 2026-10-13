"""Composición del módulo Facturación: arma los casos de uso con sus
adaptadores (Odoo por JSON-2, Postgres y el repositorio de pedidos)."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.kitchan.core.database import get_db
from src.kitchan.modules.facturacion.application.facturar_pedido import (
    ActualizarFacturaDesdeOdooUseCase,
    ConciliarFacturasPendientesUseCase,
    ConsultarFacturaPedidoUseCase,
    FacturarPedidoUseCase,
)
from src.kitchan.modules.facturacion.domain.ports import OdooFacturacionPort
from src.kitchan.modules.facturacion.infrastructure.odoo_json2_adapter import (
    OdooJson2Adapter,
)
from src.kitchan.modules.facturacion.infrastructure.pedidos_adapter import (
    PedidosFacturablesAdapter,
)
from src.kitchan.modules.facturacion.infrastructure.repository import (
    PostgresFacturaRepository,
)
from src.kitchan.modules.pedidos.infrastructure.dependencias import (
    construir_repositorio_pedidos,
)


def get_odoo() -> OdooFacturacionPort:
    return OdooJson2Adapter()


def get_facturar_use_case(
    db: AsyncSession = Depends(get_db), odoo: OdooFacturacionPort = Depends(get_odoo)
) -> FacturarPedidoUseCase:
    return FacturarPedidoUseCase(
        odoo=odoo,
        facturas=PostgresFacturaRepository(db),
        pedidos=PedidosFacturablesAdapter(construir_repositorio_pedidos(db)),
    )


def get_consultar_use_case(
    db: AsyncSession = Depends(get_db),
) -> ConsultarFacturaPedidoUseCase:
    return ConsultarFacturaPedidoUseCase(facturas=PostgresFacturaRepository(db))


def get_actualizar_use_case(
    db: AsyncSession = Depends(get_db), odoo: OdooFacturacionPort = Depends(get_odoo)
) -> ActualizarFacturaDesdeOdooUseCase:
    return ActualizarFacturaDesdeOdooUseCase(
        odoo=odoo, facturas=PostgresFacturaRepository(db)
    )


def construir_conciliar_use_case(
    db: AsyncSession, odoo: OdooFacturacionPort
) -> ConciliarFacturasPendientesUseCase:
    return ConciliarFacturasPendientesUseCase(
        odoo=odoo, facturas=PostgresFacturaRepository(db)
    )


def get_conciliar_use_case(
    db: AsyncSession = Depends(get_db), odoo: OdooFacturacionPort = Depends(get_odoo)
) -> ConciliarFacturasPendientesUseCase:
    return construir_conciliar_use_case(db, odoo)
