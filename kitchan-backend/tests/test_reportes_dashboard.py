"""Tests del dashboard de analíticas (módulo reportes) con un puerto de lectura
falso: el cálculo por rangos no depende de la base de datos."""

from datetime import datetime, timedelta, timezone

import pytest

from src.kitchan.modules.reportes.application.dashboard_pedidos import (
    ObtenerDashboardPedidosUseCase,
    RangoInvalidoError,
    zona_horaria,
)
from src.kitchan.modules.reportes.domain.entities import ItemResumen, PedidoResumen
from src.kitchan.modules.reportes.domain.ports import PedidosLecturaPort

UTC = timezone.utc
QUITO = timezone(timedelta(hours=-5))  # Guayaquil: UTC-5, sin horario de verano
# 08/10/2026 15:00 hora de Guayaquil
AHORA = datetime(2026, 10, 8, 20, 0, tzinfo=UTC)


class PedidosFalsos(PedidosLecturaPort):
    def __init__(self, pedidos: list[PedidoResumen]):
        self.pedidos = pedidos
        self.consulta = None

    async def listar_desde(self, restaurante_id, desde):
        self.consulta = (restaurante_id, desde)
        return [p for p in self.pedidos if p.fecha_creacion >= desde]


def _utc(dia, hora, minuto=0):
    return datetime(2026, 10, dia, hora, minuto, tzinfo=UTC)


def _pedido(
    origen="LOCAL",
    total=10.0,
    estado="ENTREGADA",
    creado=None,
    minutos=None,
    cliente="",
    items=(),
    metodo_pago=None,
):
    creado = creado or _utc(8, 17)
    # `minutos` = lo que tardó la cocina: aceptó al llegar y terminó pasado ese tiempo.
    lista = creado + timedelta(minutes=minutos) if minutos is not None else None
    return PedidoResumen(
        origen=origen,
        total=total,
        estado=estado,
        fecha_creacion=creado,
        fecha_actualizacion=lista,
        fecha_aceptacion=creado if lista else None,
        fecha_lista=lista,
        cliente=cliente,
        items=tuple(ItemResumen(*i) for i in items),
        metodo_pago=metodo_pago,
    )


def _use_case(pedidos):
    fuente = PedidosFalsos(pedidos)
    return fuente, ObtenerDashboardPedidosUseCase(
        pedidos=fuente, zona=QUITO, ahora=lambda: AHORA
    )


@pytest.mark.asyncio
async def test_resumen_del_dia_excluye_cancelados_de_las_ventas():
    fuente, use_case = _use_case(
        [
            _pedido(total=10.0, minutos=8),
            _pedido(total=20.0, minutos=12, creado=_utc(8, 18)),
            _pedido(total=30.0, estado="CANCELADA"),
            # Ayer: solo cuenta en el periodo anterior.
            _pedido(total=99.0, creado=_utc(7, 17), minutos=5),
        ]
    )

    datos = await use_case.ejecutar("rest-1", "hoy")

    # Consulta desde el inicio del día anterior en hora local (00:00 -05:00).
    assert fuente.consulta == ("rest-1", datetime(2026, 10, 7, 5, 0, tzinfo=UTC))
    r = datos["resumen"]
    assert r["pedidos_totales"] == 3
    assert r["pedidos_cancelados"] == 1
    assert r["tasa_cancelacion"] == 33.3
    assert r["ventas_totales"] == 30.0
    assert r["ticket_promedio"] == 15.0
    assert r["tiempo_promedio_preparacion_minutos"] == 10.0
    assert datos["periodo_anterior"]["pedidos_totales"] == 1
    assert datos["periodo_anterior"]["ventas_totales"] == 99.0
    assert datos["desde"] == datos["hasta"] == "2026-10-08"


@pytest.mark.asyncio
async def test_las_horas_y_los_dias_usan_la_zona_horaria_del_restaurante():
    _, use_case = _use_case(
        [
            # 17:00 UTC = 12:00 en Guayaquil.
            _pedido(creado=_utc(8, 17)),
            _pedido(creado=_utc(8, 17, 30)),
            # 02:00 UTC del 9 = 21:00 del 8 en Guayaquil: sigue siendo "hoy".
            _pedido(creado=_utc(9, 2)),
            # 03:00 UTC del 8 = 22:00 del 7 en Guayaquil: pertenece a "ayer".
            _pedido(creado=_utc(8, 3)),
        ]
    )

    datos = await use_case.ejecutar("rest-1", "hoy")

    por_hora = datos["por_hora"]
    assert por_hora[12] == {"hora": 12, "pedidos": 2, "pedidos_anterior": 0}
    assert por_hora[21]["pedidos"] == 1
    assert por_hora[22] == {"hora": 22, "pedidos": 0, "pedidos_anterior": 1}
    assert datos["hora_pico"] == {"hora": 12, "pedidos": 2}
    assert datos["resumen"]["pedidos_totales"] == 3


@pytest.mark.asyncio
async def test_rango_de_siete_dias_agrupa_por_dia_y_compara_con_la_semana_anterior():
    _, use_case = _use_case(
        [
            _pedido(total=10.0, creado=_utc(8, 17)),
            _pedido(total=20.0, creado=_utc(5, 17)),
            _pedido(total=5.0, creado=_utc(5, 18)),
            # Semana anterior (del 25/09 al 01/10).
            _pedido(total=50.0, creado=datetime(2026, 9, 30, 17, tzinfo=UTC)),
        ]
    )

    datos = await use_case.ejecutar("rest-1", "7d")

    assert datos["desde"] == "2026-10-02"
    assert datos["hasta"] == "2026-10-08"
    assert len(datos["por_dia"]) == 7
    dia_5 = next(d for d in datos["por_dia"] if d["fecha"] == "2026-10-05")
    assert dia_5 == {"fecha": "2026-10-05", "pedidos": 2, "ventas": 25.0}
    assert datos["resumen"]["ventas_totales"] == 35.0
    assert datos["periodo_anterior"]["ventas_totales"] == 50.0


@pytest.mark.asyncio
async def test_compara_canales_en_pedidos_ventas_y_demoras():
    _, use_case = _use_case(
        [
            _pedido("LOCAL", 10.0, minutos=4),
            _pedido("LOCAL", 14.0, minutos=6, creado=_utc(8, 18)),
            _pedido("UBER_EATS", 30.0, minutos=20),
            _pedido("UBER_EATS", 10.0, minutos=8, creado=_utc(8, 19)),
            _pedido("RAPPI", 12.0, estado="CANCELADA"),
        ]
    )

    datos = await use_case.ejecutar("rest-1", "hoy")

    canales = {c["canal"]: c for c in datos["por_canal"]}
    assert [c["canal"] for c in datos["por_canal"]][:2] == ["LOCAL", "UBER_EATS"]
    assert canales["LOCAL"]["pedidos"] == 2
    assert canales["LOCAL"]["ventas"] == 24.0
    assert canales["LOCAL"]["tiempo_promedio_minutos"] == 5.0
    assert canales["LOCAL"]["tasa_demora"] == 0.0
    assert canales["UBER_EATS"]["tiempo_promedio_minutos"] == 14.0
    # 1 de 2 pedidos de Uber pasó del umbral de 10 minutos.
    assert canales["UBER_EATS"]["tasa_demora"] == 50.0
    assert canales["RAPPI"]["cancelados"] == 1
    assert canales["RAPPI"]["ventas"] == 0.0
    assert canales["LOCAL"]["porcentaje_ventas"] == 37.5  # 24 de 64


@pytest.mark.asyncio
async def test_productos_mas_y_menos_vendidos_y_combos():
    _, use_case = _use_case(
        [
            _pedido(items=[("Club sandwich", 3, 6.0), ("Café americano", 2, 2.0)]),
            _pedido(items=[("club sandwich ", 1, 6.0), ("Brownie", 1, 3.5)]),
            _pedido(items=[("Bolón de verde", 4, 3.0), ("Muffin", 1, 2.5)]),
            _pedido(items=[("Limonada", 2, 2.0), ("Té", 1, 1.5)]),
            _pedido(items=[("Panini Caprese", 2, 6.5), ("Combo desayuno", 5, 7.0)]),
            _pedido(items=[("Cheesecake", 1, 4.0), ("Wrap vegetariano", 1, 5.5)]),
            _pedido(items=[("Café americano", 1, 2.0)], estado="CANCELADA"),
        ]
    )

    datos = await use_case.ejecutar("rest-1", "hoy")

    mas = datos["productos_mas_vendidos"]
    # Empatan en 4 unidades: el desempate es el que más vendió en dinero.
    assert [p["nombre"] for p in mas][:2] == ["Club sandwich", "Bolón de verde"]
    # El mismo plato con otra mayúscula o espacio se suma una sola vez.
    assert mas[0] == {"nombre": "Club sandwich", "cantidad": 4, "ventas": 24.0}
    # El pedido cancelado no suma ventas del plato.
    assert next(p for p in mas if p["nombre"] == "Café americano")["cantidad"] == 2
    # Los de menos ventas salen del resto (fuera del top 5), del más flojo al más fuerte.
    menos = datos["productos_menos_vendidos"]
    assert menos and menos[0]["cantidad"] == 1
    assert all(m["nombre"] not in [p["nombre"] for p in mas] for m in menos)
    assert datos["combos_mas_vendidos"] == [
        {"nombre": "Combo desayuno", "cantidad": 5, "ventas": 35.0}
    ]
    assert "Combo desayuno" not in [p["nombre"] for p in mas]


@pytest.mark.asyncio
async def test_frecuencia_de_compra_por_cliente():
    _, use_case = _use_case(
        [
            _pedido(cliente="Marcela Quispe", total=10.0),
            _pedido(cliente="marcela quispe ", total=12.0),
            _pedido(cliente="Marcela Quispe", total=8.0),
            _pedido(cliente="Diego Salas", total=9.0),
            _pedido(cliente="Diego Salas", total=11.0),
            _pedido(cliente="Lucía Fernández", total=7.0),
            _pedido(cliente="", total=5.0),
            _pedido(cliente="Camila Ortiz", total=99.0, estado="CANCELADA"),
        ]
    )

    c = (await use_case.ejecutar("rest-1", "hoy"))["clientes"]

    assert c["identificacion"] == "nombre"
    assert c["clientes_unicos"] == 3
    assert c["clientes_recurrentes"] == 2
    assert c["tasa_recurrencia"] == 66.7
    assert c["pedidos_por_cliente"] == 2.0
    assert [d["clientes"] for d in c["distribucion"]] == [1, 1, 1]
    assert c["mas_frecuentes"][0] == {
        "cliente": "Marcela Quispe",
        "pedidos": 3,
        "ventas": 30.0,
    }


@pytest.mark.asyncio
async def test_metodos_de_pago_solo_con_datos_reales():
    _, use_case = _use_case(
        [
            _pedido(total=10.0, metodo_pago="efectivo"),
            _pedido(total=30.0, metodo_pago="TARJETA"),
            _pedido(total=20.0, metodo_pago="tarjeta"),
            _pedido(total=40.0),
            _pedido(total=50.0, metodo_pago="EFECTIVO", estado="CANCELADA"),
        ]
    )

    pagos = (await use_case.ejecutar("rest-1", "hoy"))["metodos_pago"]

    assert pagos["disponible"] is True
    assert pagos["sin_dato"] == 1
    assert pagos["cobertura"] == 75.0
    assert pagos["items"][0] == {
        "metodo": "TARJETA",
        "pedidos": 2,
        "ventas": 50.0,
        "porcentaje_pedidos": 66.7,
        "porcentaje_ventas": 83.3,
    }
    assert pagos["items"][1]["metodo"] == "EFECTIVO"


@pytest.mark.asyncio
async def test_sin_metodos_de_pago_no_inventa_datos():
    _, use_case = _use_case([_pedido(total=10.0), _pedido(total=20.0)])

    pagos = (await use_case.ejecutar("rest-1", "hoy"))["metodos_pago"]

    assert pagos == {"disponible": False, "sin_dato": 2, "cobertura": 0.0, "items": []}


@pytest.mark.asyncio
async def test_sin_pedidos_retorna_ceros_y_listas_vacias():
    _, use_case = _use_case([])

    datos = await use_case.ejecutar("rest-1", "30d")

    assert datos["resumen"]["pedidos_totales"] == 0
    assert datos["resumen"]["ventas_totales"] == 0.0
    assert datos["resumen"]["ticket_promedio"] == 0.0
    assert datos["hora_pico"] is None
    assert len(datos["por_dia"]) == 30
    assert datos["por_canal"] == []
    assert datos["productos_mas_vendidos"] == []
    assert datos["clientes"]["clientes_unicos"] == 0


@pytest.mark.asyncio
async def test_el_tiempo_de_preparacion_va_de_la_aceptacion_a_listo():
    llego = _utc(8, 17, 0)
    _, use_case = _use_case(
        [
            PedidoResumen(
                origen="LOCAL",
                total=10.0,
                estado="ENTREGADA",
                fecha_creacion=llego,
                # Esperó 5 min antes de que la cocina lo aceptara y se entregó mucho después:
                # solo cuentan los 10 min de aceptación a "listo".
                fecha_aceptacion=_utc(8, 17, 5),
                fecha_lista=_utc(8, 17, 15),
                fecha_actualizacion=_utc(8, 18, 30),
            )
        ]
    )

    datos = await use_case.ejecutar("rest-1", "hoy")

    assert datos["resumen"]["tiempo_promedio_preparacion_minutos"] == 10.0


@pytest.mark.asyncio
async def test_pedidos_anteriores_sin_momentos_solo_cuentan_si_siguen_en_lista():
    _, use_case = _use_case(
        [
            # Sin fecha_lista, en LISTA: el último cambio de estado es justo ese momento.
            PedidoResumen(
                origen="LOCAL",
                total=10.0,
                estado="LISTA",
                fecha_creacion=_utc(8, 17, 0),
                fecha_actualizacion=_utc(8, 17, 8),
            ),
            # Sin fecha_lista y ya ENTREGADO: su último cambio incluye la entrega, se omite.
            PedidoResumen(
                origen="LOCAL",
                total=10.0,
                estado="ENTREGADA",
                fecha_creacion=_utc(8, 17, 0),
                fecha_actualizacion=_utc(8, 18, 40),
            ),
        ]
    )

    datos = await use_case.ejecutar("rest-1", "hoy")

    assert datos["resumen"]["tiempo_promedio_preparacion_minutos"] == 8.0


def test_la_zona_por_defecto_es_utc_menos_5_aunque_falte_tzdata():
    zona = zona_horaria()

    assert datetime(2026, 10, 8, 12, 0, tzinfo=UTC).astimezone(zona).hour == 7


@pytest.mark.asyncio
async def test_rango_invalido_se_rechaza():
    _, use_case = _use_case([])

    with pytest.raises(RangoInvalidoError):
        await use_case.ejecutar("rest-1", "1y")


async def _guardar_pedido_y_token(db_session):
    import uuid

    from src.kitchan.modules.pedidos.domain.entities import Pedido, PedidoItem
    from src.kitchan.modules.pedidos.infrastructure.repository import (
        PostgresPedidoRepository,
    )
    from src.kitchan.modules.usuarios.infrastructure.security import JWTTokenGenerator

    restaurante_id = str(uuid.uuid4())
    await PostgresPedidoRepository(session=db_session).guardar(
        Pedido(
            restaurante_id=restaurante_id,
            origen="RAPPI",
            cliente="Marcela Quispe",
            items=[PedidoItem(nombre="Club sandwich", cantidad=2, precio_unitario=6.5)],
            total=13.0,
        )
    )
    token = JWTTokenGenerator().generar_token(
        {"sub": "a@a.com", "id": "1", "rol": "ADMIN", "restaurante_id": restaurante_id}
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_endpoint_dashboard_responde_con_datos_reales(client, db_session):
    """Cadena completa: ruta -> caso de uso -> adaptador -> repositorio de pedidos."""
    cabeceras = await _guardar_pedido_y_token(db_session)

    respuesta = await client.get(
        "/api/v1/reportes/pedidos/dashboard?rango=7d", headers=cabeceras
    )

    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["rango"] == "7d"
    assert datos["resumen"]["pedidos_totales"] == 1
    assert datos["resumen"]["ventas_totales"] == 13.0
    assert datos["productos_mas_vendidos"] == [
        {"nombre": "Club sandwich", "cantidad": 2, "ventas": 13.0}
    ]
    assert datos["por_canal"][0]["canal"] == "RAPPI"
    assert datos["clientes"]["clientes_unicos"] == 1
    assert datos["metodos_pago"]["disponible"] is False
    assert len(datos["por_hora"]) == 24 and len(datos["por_dia"]) == 7


@pytest.mark.asyncio
async def test_endpoint_dashboard_rechaza_un_rango_invalido(client, db_session):
    cabeceras = await _guardar_pedido_y_token(db_session)

    respuesta = await client.get(
        "/api/v1/reportes/pedidos/dashboard?rango=1y", headers=cabeceras
    )

    assert respuesta.status_code == 422


@pytest.mark.asyncio
async def test_endpoint_dashboard_exige_rol_admin(client):
    respuesta = await client.get("/api/v1/reportes/pedidos/dashboard")

    assert respuesta.status_code in (401, 403)
