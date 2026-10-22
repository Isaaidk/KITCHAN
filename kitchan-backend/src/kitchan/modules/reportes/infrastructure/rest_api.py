import os
from typing import Literal, Optional

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.kitchan.core.database import get_db
from src.kitchan.modules.pedidos.infrastructure.dependencias import (
    construir_repositorio_pedidos,
)
from src.kitchan.modules.reportes.application.analiticas_pedidos import (
    ObtenerAnaliticasPedidosUseCase,
)
from src.kitchan.modules.reportes.application.actividad_usuarios import (
    ObtenerActividadUsuariosUseCase,
)
from src.kitchan.modules.reportes.application.dashboard_pedidos import (
    ZONA_POR_DEFECTO,
    ObtenerDashboardPedidosUseCase,
    RangoInvalidoError,
    zona_horaria,
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


# ---------- Dashboard y analíticas por rango de fechas ----------


class ResumenPeriodo(BaseModel):
    unidades_por_pedido: float = 0.0
    pedidos_totales: int
    pedidos_cancelados: int
    tasa_cancelacion: float
    ventas_totales: float
    ticket_promedio: float
    tiempo_promedio_preparacion_minutos: float


class PuntoHora(BaseModel):
    hora: int
    pedidos: int
    pedidos_anterior: int


class HoraPico(BaseModel):
    hora: int
    pedidos: int


class PuntoDia(BaseModel):
    fecha: str
    pedidos: int
    ventas: float


class PuntoDiaSemana(BaseModel):
    dia: int
    pedidos: int
    ventas: float


class CanalResumen(BaseModel):
    canal: str
    pedidos: int
    cancelados: int
    ventas: float
    ticket_promedio: float
    tiempo_promedio_minutos: float
    tasa_demora: float
    porcentaje_pedidos: float
    porcentaje_ventas: float


class ProductoVendido(BaseModel):
    nombre: str
    cantidad: int
    ventas: float


class DistribucionClientes(BaseModel):
    etiqueta: str
    clientes: int


class ClienteFrecuente(BaseModel):
    cliente: str
    pedidos: int
    ventas: float


class ClientesResumen(BaseModel):
    identificacion: str
    clientes_unicos: int
    clientes_recurrentes: int
    tasa_recurrencia: float
    pedidos_por_cliente: float
    distribucion: list[DistribucionClientes]
    mas_frecuentes: list[ClienteFrecuente]
    pedidos_analizados: int


class MetodoPagoItem(BaseModel):
    metodo: str
    pedidos: int
    ventas: float
    porcentaje_pedidos: float
    porcentaje_ventas: float


class MetodosPago(BaseModel):
    disponible: bool
    sin_dato: int
    cobertura: float
    items: list[MetodoPagoItem]


class DashboardPedidosResponse(BaseModel):
    rango: str
    canal: Optional[str] = None
    desde: str
    hasta: str
    resumen: ResumenPeriodo
    periodo_anterior: ResumenPeriodo
    por_hora: list[PuntoHora]
    hora_pico: Optional[HoraPico]
    por_dia: list[PuntoDia]
    por_dia_semana: list[PuntoDiaSemana]
    por_canal: list[CanalResumen]
    umbral_demora_minutos: int
    productos_mas_vendidos: list[ProductoVendido]
    productos_menos_vendidos: list[ProductoVendido]
    productos_mayor_ingreso: list[ProductoVendido]
    combos_mas_vendidos: list[ProductoVendido]
    productos_distintos: int
    clientes: ClientesResumen
    metodos_pago: MetodosPago


class ResumenActividad(BaseModel):
    pedidos_atendidos: int
    pedidos_cancelados: int
    ventas: float
    tiempo_promedio_minutos: float
    tasa_demora: float
    ultima_actividad: Optional[str] = None


class ActividadUsuario(ResumenActividad):
    usuario_id: str


class CanalActividad(BaseModel):
    canal: str
    pedidos: int


class PedidoReciente(BaseModel):
    canal: str
    cliente: str
    total: float
    estado: str
    fecha: str
    minutos_preparacion: Optional[float] = None


class DetalleActividadUsuario(ActividadUsuario):
    por_canal: list[CanalActividad]
    recientes: list[PedidoReciente]


class ActividadUsuariosResponse(BaseModel):
    rango: str
    desde: str
    hasta: str
    sin_atribuir: int
    usuarios: list[ActividadUsuario]
    detalle: Optional[DetalleActividadUsuario] = None


def get_actividad_use_case(
    db: AsyncSession = Depends(get_db),
) -> ObtenerActividadUsuariosUseCase:
    zona = zona_horaria(os.getenv("KITCHAN_ZONA_HORARIA", ZONA_POR_DEFECTO))
    return ObtenerActividadUsuariosUseCase(
        pedidos=PedidosLecturaAdapter(construir_repositorio_pedidos(db)), zona=zona
    )


def get_analiticas_use_case(
    db: AsyncSession = Depends(get_db),
) -> ObtenerAnaliticasPedidosUseCase:
    return ObtenerAnaliticasPedidosUseCase(
        pedidos=PedidosLecturaAdapter(construir_repositorio_pedidos(db))
    )


def get_dashboard_use_case(
    db: AsyncSession = Depends(get_db),
) -> ObtenerDashboardPedidosUseCase:
    # La zona horaria del restaurante sale del entorno (por defecto, Ecuador).
    zona = zona_horaria(os.getenv("KITCHAN_ZONA_HORARIA", ZONA_POR_DEFECTO))
    return ObtenerDashboardPedidosUseCase(
        pedidos=PedidosLecturaAdapter(construir_repositorio_pedidos(db)), zona=zona
    )


@router.get("/pedidos/analiticas", response_model=AnaliticasPedidosResponse)
async def analiticas_pedidos(
    usuario_actual: dict = Depends(requiere_rol(RolUsuario.ADMIN.value)),
    use_case: ObtenerAnaliticasPedidosUseCase = Depends(get_analiticas_use_case),
):
    datos = await use_case.ejecutar(usuario_actual["restaurante_id"])
    return AnaliticasPedidosResponse(**datos)


@router.get("/pedidos/dashboard", response_model=DashboardPedidosResponse)
async def dashboard_pedidos(
    rango: Literal["hoy", "7d", "30d"] = Query(
        "hoy", description="Periodo a analizar: hoy, últimos 7 días o últimos 30 días"
    ),
    canal: Optional[str] = Query(
        None,
        max_length=30,
        description="Limita el reporte a un canal (UBER_EATS, RAPPI, PEDIDOS_YA, WHATSAPP, LOCAL)",
    ),
    usuario_actual: dict = Depends(requiere_rol(RolUsuario.ADMIN.value)),
    use_case: ObtenerDashboardPedidosUseCase = Depends(get_dashboard_use_case),
):
    try:
        datos = await use_case.ejecutar(usuario_actual["restaurante_id"], rango, canal)
    except RangoInvalidoError as error:
        raise HTTPException(status_code=422, detail=str(error))
    return DashboardPedidosResponse(**datos)


@router.get("/usuarios/actividad", response_model=ActividadUsuariosResponse)
async def actividad_de_usuarios(
    rango: Literal["hoy", "7d", "30d"] = Query("7d"),
    usuario_actual: dict = Depends(requiere_rol(RolUsuario.ADMIN.value)),
    use_case: ObtenerActividadUsuariosUseCase = Depends(get_actividad_use_case),
):
    """Pedidos aceptados por cada usuario del restaurante en el rango."""
    datos = await use_case.ejecutar(usuario_actual["restaurante_id"], rango)
    return ActividadUsuariosResponse(**datos)


@router.get(
    "/usuarios/{usuario_id}/actividad", response_model=ActividadUsuariosResponse
)
async def actividad_de_un_usuario(
    usuario_id: str,
    rango: Literal["hoy", "7d", "30d"] = Query("7d"),
    usuario_actual: dict = Depends(requiere_rol(RolUsuario.ADMIN.value)),
    use_case: ObtenerActividadUsuariosUseCase = Depends(get_actividad_use_case),
):
    """Lo mismo que /usuarios/actividad, con el detalle de un usuario (canales y últimos pedidos)."""
    datos = await use_case.ejecutar(
        usuario_actual["restaurante_id"], rango, usuario_id=usuario_id
    )
    return ActividadUsuariosResponse(**datos)
