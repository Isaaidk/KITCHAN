from pydantic import BaseModel
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.kitchan.core.database import get_db
from src.kitchan.modules.pedidos.infrastructure.dependencias import (
    construir_repositorio_pedidos,
)
from src.kitchan.modules.reportes.application.analiticas_pedidos import (
    ObtenerAnaliticasPedidosUseCase,
)
from src.kitchan.modules.reportes.infrastructure.pedidos_lectura_adapter import (
    PedidosLecturaAdapter,
)
from src.kitchan.modules.usuarios.domain.entities import RolUsuario
from src.kitchan.modules.usuarios.infrastructure.auth_dependencies import requiere_rol

router = APIRouter(prefix="/api/v1/reportes", tags=["Reportes"])


class PuntoComparacionHora(BaseModel):
    hora: int
    hoy: int
    ayer: int


class AnaliticasPedidosResponse(BaseModel):
    pedidos_totales_hoy: int
    ticket_promedio: float
    tiempo_promedio_preparacion_minutos: float
    pedidos_cancelados_hoy: int
    por_canal: dict[str, int]
    comparacion_hoy_vs_ayer: list[PuntoComparacionHora]


def get_analiticas_use_case(
    db: AsyncSession = Depends(get_db),
) -> ObtenerAnaliticasPedidosUseCase:
    return ObtenerAnaliticasPedidosUseCase(
        pedidos=PedidosLecturaAdapter(construir_repositorio_pedidos(db))
    )


@router.get("/pedidos/analiticas", response_model=AnaliticasPedidosResponse)
async def analiticas_pedidos(
    usuario_actual: dict = Depends(requiere_rol(RolUsuario.ADMIN.value)),
    use_case: ObtenerAnaliticasPedidosUseCase = Depends(get_analiticas_use_case),
):
    datos = await use_case.ejecutar(usuario_actual["restaurante_id"])
    return AnaliticasPedidosResponse(**datos)
