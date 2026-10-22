"""Resumen de la facturación de un restaurante: cuántas facturas hay en cada
estado ante el SRI y cuándo hubo la última novedad."""

from src.kitchan.modules.facturacion.domain.entities import EstadoFactura
from src.kitchan.modules.facturacion.domain.ports import FacturaRepositoryPort


class ObtenerResumenFacturacionUseCase:
    def __init__(self, facturas: FacturaRepositoryPort):
        self.facturas = facturas

    async def ejecutar(self, restaurante_id: str) -> dict:
        facturas = await self.facturas.listar_por_restaurante(restaurante_id)

        def cuantas(estado: EstadoFactura) -> int:
            return len([f for f in facturas if f.estado == estado])

        autorizadas = [f for f in facturas if f.estado == EstadoFactura.AUTORIZADA]
        con_novedad = [f.fecha_actualizacion for f in facturas if f.fecha_actualizacion]
        con_autorizacion = [f.fecha_autorizacion for f in autorizadas if f.fecha_autorizacion]
        return {
            "total": len(facturas),
            "pendientes_sri": cuantas(EstadoFactura.PENDIENTE_SRI),
            "autorizadas": len(autorizadas),
            "con_error": cuantas(EstadoFactura.CON_ERROR),
            "anuladas": cuantas(EstadoFactura.ANULADA),
            "monto_autorizado": round(sum(f.total for f in autorizadas), 2),
            "ultima_novedad": max(con_novedad).isoformat() if con_novedad else None,
            "ultima_autorizacion": max(con_autorizacion).isoformat() if con_autorizacion else None,
        }
