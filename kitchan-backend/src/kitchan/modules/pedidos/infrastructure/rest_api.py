from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.kitchan.core.database import get_db
from src.kitchan.modules.pedidos.application.actualizar_estado_pedido_service import (
    ActualizarEstadoPedidoUseCase,
)
from src.kitchan.modules.pedidos.domain.entities import EstadoPedido, Pedido, PedidoItem
from src.kitchan.modules.pedidos.infrastructure.eventos.redis_publisher import (
    RedisPublisherAdapter,
)
from src.kitchan.modules.pedidos.infrastructure.repository import (
    PostgresPedidoRepository,
)
from src.kitchan.modules.usuarios.infrastructure.auth_dependencies import (
    obtener_usuario_actual,
)

import os

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

router = APIRouter(prefix="/api/v1/pedidos", tags=["Pedidos"])

ESTADOS_ACTIVOS = [
    EstadoPedido.NUEVA.value,
    EstadoPedido.EN_PREPARACION.value,
    EstadoPedido.LISTA.value,
]


class PedidoItemResponse(BaseModel):
    nombre: str
    cantidad: int
    precio_unitario: float
    notas: Optional[str] = None


class PedidoResponse(BaseModel):
    id: str
    restaurante_id: str
    origen: str
    id_externo: Optional[str] = None
    cliente: str
    nota_cliente: Optional[str] = None
    items: list[PedidoItemResponse]
    total: float
    estado: str
    estado_entrega: Optional[str] = None
    fecha_creacion: str

    @staticmethod
    def from_domain(pedido: Pedido) -> "PedidoResponse":
        return PedidoResponse(
            id=pedido.id,
            restaurante_id=pedido.restaurante_id,
            origen=pedido.origen,
            id_externo=pedido.id_externo,
            cliente=pedido.cliente,
            nota_cliente=pedido.nota_cliente,
            items=[PedidoItemResponse(**item.model_dump()) for item in pedido.items],
            total=pedido.total,
            estado=pedido.estado.value,
            estado_entrega=pedido.estado_entrega,
            fecha_creacion=pedido.fecha_creacion.isoformat(),
        )


class PedidosPaginadosResponse(BaseModel):
    resultados: list[PedidoResponse]
    total: int


@router.get("", response_model=PedidosPaginadosResponse)
async def listar_pedidos(
    estado: Optional[str] = Query(
        None, description="Filtra por un único estado (CSV soportado con `estados`)"
    ),
    estados: Optional[str] = Query(
        None, description="Lista de estados separados por coma"
    ),
    canal: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: Optional[int] = Query(None, ge=1),
    page_size: Optional[int] = Query(None, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    usuario_actual: dict = Depends(obtener_usuario_actual),
):
    """
    Sin `page`/`page_size`: hidrata el tablero KDS (por defecto, estados
    activos NUEVA/EN_PREPARACION/LISTA). Con `page`/`page_size`: modo
    paginado para la pantalla Historial (incluye todos los estados salvo que
    se filtre explícitamente).
    """
    repo = PostgresPedidoRepository(session=db)

    lista_estados: Optional[list[str]]
    if estados:
        lista_estados = [e.strip() for e in estados.split(",") if e.strip()]
    elif estado:
        lista_estados = [estado]
    elif page is None and page_size is None:
        lista_estados = ESTADOS_ACTIVOS
    else:
        lista_estados = None

    pedidos, total = await repo.listar_por_restaurante(
        restaurante_id=usuario_actual["restaurante_id"],
        estados=lista_estados,
        canal=canal,
        search=search,
        page=page,
        page_size=page_size,
    )

    return PedidosPaginadosResponse(
        resultados=[PedidoResponse.from_domain(p) for p in pedidos], total=total
    )


@router.post("/{pedido_id}/completar", response_model=PedidoResponse)
async def completar_pedido(
    pedido_id: str,
    db: AsyncSession = Depends(get_db),
    usuario_actual: dict = Depends(obtener_usuario_actual),
):
    """
    Marca un pedido LISTO como ENTREGADA manualmente desde el KDS. No llama
    a ninguna integración: la entrega/courier es responsabilidad de la
    plataforma (Uber, etc.), no algo que KITCHAN pueda confirmar por API —
    esto solo saca el pedido del tablero activo una vez que el negocio (no
    el software) sabe que ya se completó.
    """
    repo = PostgresPedidoRepository(session=db)
    pedido = await repo.buscar_por_id(pedido_id)
    if pedido is None or pedido.restaurante_id != usuario_actual["restaurante_id"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pedido no encontrado"
        )

    notificador = RedisPublisherAdapter(redis_url=REDIS_URL)
    caso_uso = ActualizarEstadoPedidoUseCase(repository=repo, notificador=notificador)
    actualizado = await caso_uso.ejecutar_por_id(pedido_id, EstadoPedido.ENTREGADA)

    return PedidoResponse.from_domain(actualizado)


@router.post("/{pedido_id}/cancelar-interno", response_model=PedidoResponse)
async def cancelar_pedido_interno(
    pedido_id: str,
    db: AsyncSession = Depends(get_db),
    usuario_actual: dict = Depends(obtener_usuario_actual),
):
    """
    Cancela un pedido a nivel KITCHAN sin avisarle a la integración externa.
    Para pedidos de Uber, usar en su lugar el endpoint /deny del módulo de
    integración correspondiente (sí le avisa a Uber); este solo aplica a
    pedidos de canales sin integración de cancelación propia (ej. LOCAL).
    """
    repo = PostgresPedidoRepository(session=db)
    pedido = await repo.buscar_por_id(pedido_id)
    if pedido is None or pedido.restaurante_id != usuario_actual["restaurante_id"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pedido no encontrado"
        )

    notificador = RedisPublisherAdapter(redis_url=REDIS_URL)
    caso_uso = ActualizarEstadoPedidoUseCase(repository=repo, notificador=notificador)
    actualizado = await caso_uso.ejecutar_por_id(pedido_id, EstadoPedido.CANCELADA)

    return PedidoResponse.from_domain(actualizado)
