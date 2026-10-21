import { Link } from "react-router-dom";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import fotoCabecera from "../../assets/login-vangalia.webp";
import CanalLogo from "../../shared/components/CanalLogo";
import Icon, { type NombreIcono } from "../../shared/components/Icon";
import { useCountUp } from "../../shared/hooks/useCountUp";
import { useAuthStore } from "../../shared/stores/authStore";
import { useOrdersStore } from "../../shared/stores/ordersStore";
import { fechaCorta, horaEtiqueta, minutos, moneda, numero } from "../../shared/utils/formato";
import { infoCanal } from "../pedidos/estadoUtils";
import compartido from "./Compartido.module.css";
import {
  COLOR_EJE,
  COLOR_GRILLA,
  COLOR_PRINCIPAL,
  COLOR_SECUNDARIO,
  estiloTooltip,
} from "./estilosGraficos";
import RankingProductos from "./RankingProductos";
import SelectorRango from "./SelectorRango";
import type { DashboardPedidos, ResumenPeriodo } from "./types";
import { RANGOS, useDashboard, useRango } from "./useDashboard";
import Variacion from "./Variacion";
import styles from "./DashboardPage.module.css";

const formatoFechaLarga = new Intl.DateTimeFormat(undefined, {
  weekday: "long",
  day: "numeric",
  month: "long",
});

function saludo(): string {
  const hora = new Date().getHours();
  if (hora < 12) return "Buenos días";
  if (hora < 19) return "Buenas tardes";
  return "Buenas noches";
}

interface Kpi {
  clave: keyof ResumenPeriodo;
  etiqueta: string;
  icono: NombreIcono;
  color: string;
  formato: (n: number) => string;
  menorEsMejor?: boolean;
  detalle: (r: ResumenPeriodo) => string;
}

const KPIS: Kpi[] = [
  {
    clave: "pedidos_totales",
    etiqueta: "Pedidos totales",
    icono: "bandeja",
    color: "#6b1e3c",
    formato: (n) => numero(n),
    detalle: (r) => `${numero(r.pedidos_cancelados)} cancelados`,
  },
  {
    clave: "ventas_totales",
    etiqueta: "Ventas",
    icono: "dinero",
    color: "#2cb1b1",
    formato: moneda,
    detalle: () => "Sin contar cancelados",
  },
  {
    clave: "ticket_promedio",
    etiqueta: "Ticket promedio",
    icono: "recibo",
    color: "#f4b942",
    formato: moneda,
    detalle: () => "Venta media por pedido",
  },
  {
    clave: "tiempo_promedio_preparacion_minutos",
    etiqueta: "Tiempo de preparación",
    icono: "reloj",
    color: "#2e3a46",
    formato: minutos,
    menorEsMejor: true,
    detalle: () => "Promedio hasta quedar listo",
  },
];

function TarjetaKpi({
  kpi,
  actual,
  anterior,
  contra,
  indice,
}: {
  kpi: Kpi;
  actual: ResumenPeriodo;
  anterior: ResumenPeriodo;
  contra: string;
  indice: number;
}) {
  const valor = actual[kpi.clave];
  const animado = useCountUp(valor);
  return (
    <article
      className={`${styles.kpi} animate-in`}
      style={{ ["--i" as string]: indice, ["--kpi-color" as string]: kpi.color }}
    >
      <div className={styles.kpiCabecera}>
        <h2 className={styles.kpiEtiqueta}>{kpi.etiqueta}</h2>
        <span className={styles.kpiIcono}>
          <Icon name={kpi.icono} size={20} />
        </span>
      </div>
      {/* El número animado se oculta a lectores de pantalla (leerían valores intermedios). */}
      <div className={styles.kpiValor} aria-hidden="true">
        {kpi.formato(animado)}
      </div>
      <span className="sr-only">{kpi.formato(valor)}</span>
      <div className={styles.kpiPie}>
        <Variacion
          actual={valor}
          anterior={anterior[kpi.clave]}
          menorEsMejor={kpi.menorEsMejor}
          contra={contra}
        />
        <span className={styles.kpiDetalle}>{kpi.detalle(actual)}</span>
      </div>
    </article>
  );
}

/** Lo que hay en cocina ahora mismo (en vivo, desde la cola), con acceso directo a cada columna. */
function CocinaAhora() {
  const pedidos = useOrdersStore((s) => s.pedidos);
  const lista = Object.values(pedidos);
  const cuenta = (estado: string) => lista.filter((p) => p.estado === estado).length;
  const columnas = [
    { estado: "NUEVA", titulo: "Pendientes", clase: styles.cocinaNueva },
    { estado: "EN_PREPARACION", titulo: "En preparación", clase: styles.cocinaPreparacion },
    { estado: "LISTA", titulo: "Listos para entregar", clase: styles.cocinaLista },
  ];

  return (
    <section className={styles.cocina} aria-labelledby="cocina-ahora">
      <h2 id="cocina-ahora" className={styles.cocinaTitulo}>
        <Icon name="cola" size={16} />
        Cocina ahora
      </h2>
      <div className={styles.cocinaTarjetas}>
        {columnas.map((c) => (
          <Link key={c.estado} to={`/cola?estado=${c.estado}`} className={`${styles.cocinaTarjeta} ${c.clase}`}>
            <span className={styles.cocinaNumero}>{cuenta(c.estado)}</span>
            <span className={styles.cocinaNombre}>{c.titulo}</span>
            <Icon name="flecha" size={16} className={styles.cocinaFlecha} />
          </Link>
        ))}
      </div>
    </section>
  );
}

function GraficoVentas({ datos }: { datos: DashboardPedidos }) {
  if (datos.rango === "hoy") {
    const total = datos.por_hora.reduce((s, p) => s + p.pedidos, 0);
    const totalAnterior = datos.por_hora.reduce((s, p) => s + p.pedidos_anterior, 0);
    return (
      <div className={compartido.panel}>
        <div className={compartido.panelCabecera}>
          <div>
            <h2 className={compartido.panelTitulo}>Pedidos por hora</h2>
            <p className={compartido.panelSub}>
              Hoy {numero(total)} · ayer {numero(totalAnterior)}
            </p>
          </div>
        </div>
        <div role="img" aria-label={`Pedidos por hora: ${total} hoy y ${totalAnterior} ayer`}>
          <ResponsiveContainer width="100%" height={250}>
            <AreaChart data={datos.por_hora} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
              <defs>
                <linearGradient id="gradPedidosHoy" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={COLOR_PRINCIPAL} stopOpacity={0.28} />
                  <stop offset="100%" stopColor={COLOR_PRINCIPAL} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke={COLOR_GRILLA} vertical={false} />
              <XAxis
                dataKey="hora"
                fontSize={11}
                tickLine={false}
                axisLine={false}
                stroke={COLOR_EJE}
                tickFormatter={(h: number) => `${h}h`}
              />
              <YAxis allowDecimals={false} fontSize={11} tickLine={false} axisLine={false} stroke={COLOR_EJE} />
              <Tooltip {...estiloTooltip} labelFormatter={(h: number) => horaEtiqueta(h)} />
              <Legend
                iconType="circle"
                iconSize={8}
                wrapperStyle={{ fontSize: 12, paddingTop: 8 }}
                formatter={(v: string) => (v === "pedidos" ? "Hoy" : "Ayer")}
              />
              <Area
                type="monotone"
                dataKey="pedidos_anterior"
                stroke={COLOR_SECUNDARIO}
                strokeWidth={2}
                strokeDasharray="5 4"
                fill="transparent"
                dot={false}
                animationDuration={900}
              />
              <Area
                type="monotone"
                dataKey="pedidos"
                stroke={COLOR_PRINCIPAL}
                strokeWidth={2.5}
                fill="url(#gradPedidosHoy)"
                dot={false}
                activeDot={{ r: 5, strokeWidth: 2, stroke: "#fff" }}
                animationDuration={900}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
    );
  }

  const ventas = datos.por_dia.reduce((s, d) => s + d.ventas, 0);
  const descripcion = RANGOS.find((r) => r.valor === datos.rango)?.descripcion ?? "";
  return (
    <div className={compartido.panel}>
      <div className={compartido.panelCabecera}>
        <div>
          <h2 className={compartido.panelTitulo}>Ventas por día</h2>
          <p className={compartido.panelSub}>
            {moneda(ventas)} en {descripcion}
          </p>
        </div>
      </div>
      <div role="img" aria-label={`Ventas por día en ${descripcion}: ${moneda(ventas)} en total`}>
        <ResponsiveContainer width="100%" height={250}>
          <BarChart data={datos.por_dia} margin={{ top: 8, right: 8, left: -8, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={COLOR_GRILLA} vertical={false} />
            <XAxis
              dataKey="fecha"
              fontSize={11}
              tickLine={false}
              axisLine={false}
              stroke={COLOR_EJE}
              tickFormatter={(f: string) => fechaCorta(f)}
              minTickGap={18}
            />
            <YAxis
              fontSize={11}
              tickLine={false}
              axisLine={false}
              stroke={COLOR_EJE}
              tickFormatter={(v: number) => moneda(v).replace(/[.,]00$/, "")}
            />
            <Tooltip
              {...estiloTooltip}
              labelFormatter={(f: string) => fechaCorta(f)}
              formatter={(v: number) => [moneda(v), "Ventas"]}
            />
            <Bar dataKey="ventas" fill={COLOR_PRINCIPAL} radius={[6, 6, 0, 0]} maxBarSize={36} animationDuration={800} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function EsqueletoDashboard() {
  return (
    <>
      <div className={styles.kpis} aria-hidden="true">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className={styles.kpi}>
            <div className="skeleton" style={{ height: 12, width: "50%", marginBottom: 22 }} />
            <div className="skeleton" style={{ height: 34, width: "55%", marginBottom: 14 }} />
            <div className="skeleton" style={{ height: 14, width: "70%" }} />
          </div>
        ))}
      </div>
      <div className={compartido.dosColumnas} aria-hidden="true">
        {[0, 1].map((i) => (
          <div key={i} className={compartido.panel}>
            <div className="skeleton" style={{ height: 14, width: "40%", marginBottom: 20 }} />
            <div className="skeleton" style={{ height: 230 }} />
          </div>
        ))}
      </div>
      <span className="sr-only" role="status">
        Cargando el resumen…
      </span>
    </>
  );
}

export default function DashboardPage() {
  const [rango, setRango] = useRango();
  const { datos, cargando, error, reintentar } = useDashboard(rango);
  const nombre = useAuthStore((s) => s.usuario?.nombre ?? "");
  const primerNombre = nombre.split(" ")[0];
  const contra = rango === "hoy" ? "que ayer" : `que ${RANGOS.find((r) => r.valor === rango)?.descripcion ?? "el periodo"} anteriores`;

  return (
    <div>
      <header className={styles.cabecera}>
        <img className={styles.cabeceraFoto} src={fotoCabecera} alt="" width={800} height={509} />
        <div className={styles.cabeceraTexto}>
          <p className={styles.saludo}>{saludo()}</p>
          <h1 className={styles.titulo}>{primerNombre || "Dashboard"}</h1>
          <p className={styles.fecha}>{formatoFechaLarga.format(new Date())}</p>
        </div>
        <div className={styles.cabeceraAcciones}>
          <SelectorRango valor={rango} onCambio={setRango} tono="claro" />
        </div>
      </header>

      {error && (
        <div className={`alert alert-error ${compartido.errorAnaliticas}`} role="alert">
          <Icon name="alerta" size={16} />
          <span className={compartido.errorTexto}>
            No se pudo cargar el resumen. Revisa la conexión e inténtalo de nuevo.
          </span>
          <button type="button" className="btn btn-secondary btn-sm" onClick={reintentar}>
            <Icon name="sync" size={14} />
            Reintentar
          </button>
        </div>
      )}

      {!datos && !error && <EsqueletoDashboard />}

      {datos && (
        <div className={cargando ? styles.actualizando : undefined} aria-busy={cargando}>
          <div className={styles.kpis}>
            {KPIS.map((kpi, i) => (
              <TarjetaKpi
                key={kpi.clave}
                kpi={kpi}
                actual={datos.resumen}
                anterior={datos.periodo_anterior}
                contra={contra}
                indice={i}
              />
            ))}
          </div>

          <CocinaAhora />

          <div className={compartido.dosColumnas}>
            <GraficoVentas datos={datos} />

            <div className={compartido.panel}>
              <div className={compartido.panelCabecera}>
                <div>
                  <h2 className={compartido.panelTitulo}>Platos más vendidos</h2>
                  <p className={compartido.panelSub}>Por unidades vendidas</p>
                </div>
                <Link to={`/analiticas${rango === "hoy" ? "" : `?rango=${rango}`}`} className={compartido.panelAccion}>
                  Ver analíticas
                </Link>
              </div>
              <RankingProductos
                items={datos.productos_mas_vendidos}
                vacio="Aún no hay ventas en este periodo."
              />
            </div>
          </div>

          <section className={compartido.panel} aria-labelledby="dash-canales">
            <div className={compartido.panelCabecera}>
              <div>
                <h2 id="dash-canales" className={compartido.panelTitulo}>
                  Canales de venta
                </h2>
                <p className={compartido.panelSub}>Local, Uber Eats, Rappi y PedidosYa</p>
              </div>
              <Link to={`/analiticas${rango === "hoy" ? "" : `?rango=${rango}`}`} className={compartido.panelAccion}>
                Comparar canales
              </Link>
            </div>
            {datos.por_canal.length === 0 ? (
              <div className={compartido.vacio}>
                <span>Aún no hay pedidos en este periodo.</span>
              </div>
            ) : (
              <ul className={styles.canales}>
                {datos.por_canal.map((c) => {
                  const { nombre: nombreCanal, color } = infoCanal(c.canal);
                  return (
                    <li key={c.canal} className={styles.canal}>
                      <CanalLogo canal={c.canal} color={color} nombre={nombreCanal} size={40} />
                      <div className={styles.canalDatos}>
                        <span className={styles.canalNombre}>{nombreCanal}</span>
                        <span className={styles.canalSub}>
                          {numero(c.pedidos)} {c.pedidos === 1 ? "pedido" : "pedidos"} · {minutos(c.tiempo_promedio_minutos)}
                        </span>
                      </div>
                      <span className={styles.canalVentas}>{moneda(c.ventas)}</span>
                    </li>
                  );
                })}
              </ul>
            )}
          </section>
        </div>
      )}
    </div>
  );
}
