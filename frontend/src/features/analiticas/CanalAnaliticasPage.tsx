import { Link, Navigate, useParams } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import CanalLogo from "../../shared/components/CanalLogo";
import Icon, { type NombreIcono } from "../../shared/components/Icon";
import { fechaCorta, horaEtiqueta, minutos, moneda, numero, porcentaje } from "../../shared/utils/formato";
import { infoCanal } from "../pedidos/estadoUtils";
import { Clientes, Horarios, MetodosPago } from "./AnaliticasPage";
import { canalPorSlug } from "./canales";
import compartido from "./Compartido.module.css";
import { COLOR_BARRA_SUAVE, COLOR_EJE, COLOR_GRILLA, COLOR_PRINCIPAL, estiloTooltip } from "./estilosGraficos";
import RankingProductos from "./RankingProductos";
import SelectorRango from "./SelectorRango";
import type { DashboardPedidos, ResumenPeriodo } from "./types";
import { RANGOS, useDashboard, useRango } from "./useDashboard";
import Variacion from "./Variacion";
import analiticas from "./AnaliticasPage.module.css";
import styles from "./CanalAnaliticasPage.module.css";

const DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"];

interface Dato {
  clave: keyof ResumenPeriodo;
  etiqueta: string;
  icono: NombreIcono;
  formato: (n: number) => string;
  menorEsMejor?: boolean;
}

const DATOS: Dato[] = [
  { clave: "pedidos_totales", etiqueta: "Pedidos", icono: "bandeja", formato: numero },
  { clave: "ventas_totales", etiqueta: "Ventas", icono: "dinero", formato: moneda },
  { clave: "ticket_promedio", etiqueta: "Ticket promedio", icono: "recibo", formato: moneda },
  {
    clave: "tiempo_promedio_preparacion_minutos",
    etiqueta: "Preparación",
    icono: "reloj",
    formato: (n) => (n > 0 ? minutos(n) : "—"),
    menorEsMejor: true,
  },
  {
    clave: "tasa_cancelacion",
    etiqueta: "Cancelados",
    icono: "prohibido",
    formato: porcentaje,
    menorEsMejor: true,
  },
  { clave: "unidades_por_pedido", etiqueta: "Ítems por pedido", icono: "cola", formato: (n) => numero(n, 1) },
];

/** Lo más llamativo del canal en una línea cada uno: plato estrella, el que menos sale, hora y día fuertes. */
function Destacados({ datos }: { datos: DashboardPedidos }) {
  const estrella = datos.productos_mas_vendidos[0];
  const flojo = datos.productos_menos_vendidos[0];
  const pico = datos.hora_pico;
  const diaFuerte = datos.por_dia_semana.reduce((a, b) => (b.pedidos > a.pedidos ? b : a));

  const items = [
    estrella && {
      icono: "rayo" as const,
      titulo: "Plato estrella",
      valor: estrella.nombre,
      detalle: `${numero(estrella.cantidad)} ${estrella.cantidad === 1 ? "unidad" : "unidades"}`,
    },
    flojo && {
      icono: "alerta" as const,
      titulo: "Menos pedido",
      valor: flojo.nombre,
      detalle: `${numero(flojo.cantidad)} ${flojo.cantidad === 1 ? "unidad" : "unidades"}`,
    },
    pico && {
      icono: "reloj" as const,
      titulo: "Hora pico",
      valor: horaEtiqueta(pico.hora),
      detalle: `${numero(pico.pedidos)} ${pico.pedidos === 1 ? "pedido" : "pedidos"}`,
    },
    diaFuerte.pedidos > 0 && {
      icono: "panel" as const,
      titulo: "Día más fuerte",
      valor: DIAS[diaFuerte.dia],
      detalle: `${numero(diaFuerte.pedidos)} ${diaFuerte.pedidos === 1 ? "pedido" : "pedidos"}`,
    },
  ].filter((x) => !!x);

  if (items.length === 0) return null;
  return (
    <ul className={styles.destacados} aria-label="Lo más destacado del canal">
      {items.map((d) => (
        <li key={d.titulo} className={styles.destacado}>
          <span className={styles.destacadoIcono}>
            <Icon name={d.icono} size={16} />
          </span>
          <span className={styles.destacadoTitulo}>{d.titulo}</span>
          <strong className={styles.destacadoValor} title={d.valor}>
            {d.valor}
          </strong>
          <span className={styles.destacadoDetalle}>{d.detalle}</span>
        </li>
      ))}
    </ul>
  );
}

function DiasSemana({ datos }: { datos: DashboardPedidos }) {
  const total = datos.por_dia_semana.reduce((s, d) => s + d.pedidos, 0);
  const maximo = Math.max(...datos.por_dia_semana.map((d) => d.pedidos));
  const filas = datos.por_dia_semana.map((d) => ({ ...d, nombre: DIAS[d.dia].slice(0, 3) }));
  return (
    <section className={compartido.panel} aria-labelledby="canal-dias">
      <div className={compartido.panelCabecera}>
        <div>
          <h2 id="canal-dias" className={compartido.panelTitulo}>
            Días de la semana
          </h2>
          <p className={compartido.panelSub}>Qué días usan más este canal</p>
        </div>
      </div>
      {total === 0 ? (
        <div className={compartido.vacio}>
          <span>Aún no hay pedidos en este periodo.</span>
        </div>
      ) : (
        <div role="img" aria-label={`Pedidos por día de la semana: ${filas.map((f) => `${f.nombre} ${f.pedidos}`).join(", ")}`}>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={filas} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={COLOR_GRILLA} vertical={false} />
              <XAxis dataKey="nombre" fontSize={11} tickLine={false} axisLine={false} stroke={COLOR_EJE} />
              <YAxis allowDecimals={false} fontSize={11} tickLine={false} axisLine={false} stroke={COLOR_EJE} />
              <Tooltip
                {...estiloTooltip}
                labelFormatter={(_: string, items: { payload?: { dia: number } }[]) =>
                  DIAS[items?.[0]?.payload?.dia ?? 0]
                }
                formatter={(v: number) => [v, "Pedidos"]}
              />
              <Bar dataKey="pedidos" radius={[5, 5, 0, 0]} maxBarSize={32} animationDuration={800}>
                {filas.map((f) => (
                  <Cell key={f.dia} fill={f.pedidos === maximo ? COLOR_PRINCIPAL : COLOR_BARRA_SUAVE} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </section>
  );
}

function Contenido({ datos, contra }: { datos: DashboardPedidos; contra: string }) {
  return (
    <div className={analiticas.secciones}>
      <dl className={styles.datos}>
        {DATOS.map((d) => (
          <div key={d.clave} className={styles.dato}>
            <dt className={styles.datoEtiqueta}>
              <Icon name={d.icono} size={14} />
              {d.etiqueta}
            </dt>
            <dd className={styles.datoValor}>{d.formato(datos.resumen[d.clave])}</dd>
            <Variacion
              actual={datos.resumen[d.clave]}
              anterior={datos.periodo_anterior[d.clave]}
              menorEsMejor={d.menorEsMejor}
              contra={contra}
            />
          </div>
        ))}
      </dl>

      <Destacados datos={datos} />

      <div className={compartido.dosColumnas}>
        <section className={compartido.panel} aria-labelledby="canal-mas">
          <div className={compartido.panelCabecera}>
            <div>
              <h2 id="canal-mas" className={compartido.panelTitulo}>
                Platos más pedidos
              </h2>
              <p className={compartido.panelSub}>Por unidades vendidas</p>
            </div>
          </div>
          <RankingProductos items={datos.productos_mas_vendidos} vacio="Aún no hay ventas en este periodo." />
        </section>

        <section className={compartido.panel} aria-labelledby="canal-menos">
          <div className={compartido.panelCabecera}>
            <div>
              <h2 id="canal-menos" className={compartido.panelTitulo}>
                Platos menos pedidos
              </h2>
              <p className={compartido.panelSub}>Los que menos salen entre los que sí se vendieron</p>
            </div>
          </div>
          <RankingProductos
            menos
            items={datos.productos_menos_vendidos}
            vacio={
              datos.productos_distintos === 0
                ? "Aún no hay ventas en este periodo."
                : "Hay muy pocos platos distintos para armar este ranking."
            }
          />
        </section>
      </div>

      <div className={compartido.dosColumnas}>
        <Horarios datos={datos} />
        <DiasSemana datos={datos} />
      </div>

      <div className={compartido.dosColumnas}>
        <section className={compartido.panel} aria-labelledby="canal-ingreso">
          <div className={compartido.panelCabecera}>
            <div>
              <h2 id="canal-ingreso" className={compartido.panelTitulo}>
                Platos que más dinero dejan
              </h2>
              <p className={compartido.panelSub}>Ordenados por ventas, no por unidades</p>
            </div>
          </div>
          <RankingProductos
            items={datos.productos_mayor_ingreso}
            porVentas
            vacio="Aún no hay ventas en este periodo."
          />
        </section>
        <Clientes datos={datos} />
      </div>

      <MetodosPago datos={datos} />
    </div>
  );
}

export default function CanalAnaliticasPage() {
  const { canal: slug } = useParams();
  const canal = canalPorSlug(slug);
  const [rango, setRango] = useRango();
  const { datos, cargando, error, reintentar } = useDashboard(rango, canal?.codigo);

  if (!canal) return <Navigate to="/analiticas" replace />;

  const { nombre, color } = infoCanal(canal.codigo);
  const descripcion = RANGOS.find((r) => r.valor === rango)?.descripcion ?? "";
  const contra = rango === "hoy" ? "que ayer" : `que ${descripcion} anteriores`;
  const vacio = datos && datos.resumen.pedidos_totales === 0;

  return (
    <div>
      <Link to={rango === "hoy" ? "/analiticas" : `/analiticas?rango=${rango}`} className={styles.volver}>
        <Icon name="flecha" size={14} />
        Todas las analíticas
      </Link>

      <div className="page-header">
        <div className={styles.titulo}>
          <CanalLogo canal={canal.codigo} color={color} nombre={nombre} size={52} />
          <div>
            <h1 className="page-title">{nombre}</h1>
            <p className="page-subtitle" aria-live="polite">
              Analíticas de {descripcion}
              {datos && datos.rango !== "hoy" ? ` · del ${fechaCorta(datos.desde)} al ${fechaCorta(datos.hasta)}` : ""}
            </p>
          </div>
        </div>
        <SelectorRango valor={rango} onCambio={setRango} />
      </div>

      {error && (
        <div className={`alert alert-error ${compartido.errorAnaliticas}`} role="alert">
          <Icon name="alerta" size={16} />
          <span className={compartido.errorTexto}>
            No se pudieron cargar las analíticas de {nombre}. Revisa la conexión e inténtalo de nuevo.
          </span>
          <button type="button" className="btn btn-secondary btn-sm" onClick={reintentar}>
            <Icon name="sync" size={14} />
            Reintentar
          </button>
        </div>
      )}

      {!datos && !error && (
        <div className={compartido.panel} aria-busy="true">
          <div className="skeleton" style={{ height: 14, width: "30%", marginBottom: 20 }} />
          <div className="skeleton" style={{ height: 220 }} />
          <span className="sr-only" role="status">
            Cargando las analíticas de {nombre}…
          </span>
        </div>
      )}

      {vacio && (
        <div className={compartido.panel}>
          <div className={compartido.vacio}>
            <CanalLogo canal={canal.codigo} color={color} nombre={nombre} size={44} />
            <span className={compartido.vacioTitulo}>Sin pedidos de {nombre} en este periodo</span>
            <span>
              {canal.codigo === "WHATSAPP"
                ? "WhatsApp todavía no está conectado a KITCHAN; cuando entren pedidos por ahí verás sus datos aquí."
                : "Prueba con un rango más amplio o espera a que lleguen pedidos de este canal."}
            </span>
          </div>
        </div>
      )}

      {datos && !vacio && (
        <div className={cargando ? analiticas.actualizando : undefined} aria-busy={cargando}>
          <Contenido datos={datos} contra={contra} />
        </div>
      )}
    </div>
  );
}
