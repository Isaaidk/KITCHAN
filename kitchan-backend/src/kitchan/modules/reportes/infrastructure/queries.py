import uuid
from datetime import date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.kitchan.modules.pedidos.domain.entities import EstadoPedido
from src.kitchan.modules.pedidos.infrastructure.models import PedidoModel

# Consultas de solo lectura para la pantalla de Analíticas (reportes). Viven
# aparte de PedidoRepositoryPort (que es para CRUD de pedidos) porque son un
# modelo de lectura propio del módulo `reportes`, no una operación de dominio
# de `pedidos`.


async def obtener_analiticas_pedidos(
    session: AsyncSession, restaurante_id: str
) -> dict:
    rid = uuid.UUID(str(restaurante_id))
    hoy = date.today()
    ayer = hoy - timedelta(days=1)
    inicio_ayer = datetime.combine(ayer, time.min)

    stmt = select(PedidoModel).where(
        PedidoModel.restaurante_id == rid,
        PedidoModel.fecha_creacion >= inicio_ayer,
    )
    modelos = (await session.execute(stmt)).scalars().all()

    pedidos_hoy = [m for m in modelos if m.fecha_creacion.date() == hoy]
    pedidos_ayer = [m for m in modelos if m.fecha_creacion.date() == ayer]

    total_hoy = len(pedidos_hoy)
    ticket_promedio = (
        sum(float(m.total) for m in pedidos_hoy) / total_hoy if total_hoy else 0.0
    )

    preparados_hoy = [
        m
        for m in pedidos_hoy
        if m.estado in (EstadoPedido.LISTA, EstadoPedido.ENTREGADA)
        and m.fecha_actualizacion
    ]
    tiempo_promedio_preparacion = (
        sum(
            (m.fecha_actualizacion - m.fecha_creacion).total_seconds() / 60
            for m in preparados_hoy
        )
        / len(preparados_hoy)
        if preparados_hoy
        else 0.0
    )

    cancelados_hoy = len([m for m in pedidos_hoy if m.estado == EstadoPedido.CANCELADA])

    por_canal: dict[str, int] = {}
    for m in pedidos_hoy:
        por_canal[m.origen] = por_canal.get(m.origen, 0) + 1

    por_hora_hoy = [0] * 24
    por_hora_ayer = [0] * 24
    for m in pedidos_hoy:
        por_hora_hoy[m.fecha_creacion.hour] += 1
    for m in pedidos_ayer:
        por_hora_ayer[m.fecha_creacion.hour] += 1

    return {
        "pedidos_totales_hoy": total_hoy,
        "ticket_promedio": round(ticket_promedio, 2),
        "tiempo_promedio_preparacion_minutos": round(tiempo_promedio_preparacion, 1),
        "pedidos_cancelados_hoy": cancelados_hoy,
        "por_canal": por_canal,
        "comparacion_hoy_vs_ayer": [
            {"hora": h, "hoy": por_hora_hoy[h], "ayer": por_hora_ayer[h]}
            for h in range(24)
        ],
    }
