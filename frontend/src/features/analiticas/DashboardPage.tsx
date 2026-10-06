import { useEffect, useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { httpClient } from "../../shared/api/httpClient";
import Icon, { type NombreIcono } from "../../shared/components/Icon";
import { useCountUp } from "../../shared/hooks/useCountUp";
import { moneda, numero, porcentaje } from "../../shared/utils/formato";
import CanalBadge from "../pedidos/CanalBadge";
import { infoCanal } from "../pedidos/estadoUtils";
import ExportModal from "./ExportModal";
import type { AnaliticasPedidos } from "./types";
import styles from "./DashboardPage.module.css";

// Paleta fija para los gráficos (SVG de recharts no resuelve bien var()).
const PRIMARIO = "#2563eb";
const SECUNDARIO = "#94a3b8";
const GRILLA = "#eef1f6";
const EJE = "#94a3b8";

const estiloTooltip = {
  contentStyle: {
    borderRadius: 12,
    border: "1px solid #e5e8ef",
    boxShadow: "0 12px 28px -8px rgba(15,23,42,0.18)",
    fontSize: 12,
    padding: "8px 12px",
  },
  labelStyle: { fontWeight: 700, color: "#0f172a", marginBottom: 4 },
  cursor: { fill: "rgba(37,99,235,0.06)", stroke: "rgba(37,99,235,0.2)" },
};

interface Kpi {
  etiqueta: string;
  valor: number;
  formato: (n: number) => string;
  icono: NombreIcono;
  color: string;
  detalle: string;
}

function KpiCard({ kpi, indice }: { kpi: Kpi; indice: number }) {
  const animado = useCountUp(kpi.valor);
  return (
    <div
      className={`${styles.kpi} animate-in`}
      style={{ ["--i" as string]: indice, ["--kpi-color" as string]: kpi.color }}
    >
      <div className={styles.kpiCabecera}>
        <span className={styles.kpiLabel}>{kpi.etiqueta}</span>
        <span className={styles.kpiIcono}>
          <Icon name={kpi.icono} size={18} />
        </span>
      </div>
      {/* El número animado se oculta a lectores de pantalla (leerían valores
          intermedios); ellos reciben el valor final. */}
      <div className={styles.kpiValor} aria-hidden="true">
        {kpi.formato(animado)}
      </div>
      <span className="sr-only">{kpi.formato(kpi.valor)}</span>
      <div className={styles.kpiDetalle}>{kpi.detalle}</div>
    </div>
  );
}

function DashboardSkeleton() {
  return (
    <>
      <div className={styles.kpis}>
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className={styles.kpi}>
            <div className="skeleton" style={{ height: 12, width: "50%", marginBottom: 18 }} />
            <div className="skeleton" style={{ height: 28, width: "40%", marginBottom: 10 }} />
            <div className="skeleton" style={{ height: 10, width: "70%" }} />
          </div>
        ))}
      </div>
      <div className={styles.graficos}>
        {[0, 1].map((i) => (
          <div key={i} className={styles.panel}>
            <div className="skeleton" style={{ height: 14, width: "40%", marginBottom: 20 }} />
            <div className="skeleton" style={{ height: 240 }} />
          </div>
        ))}
      </div>
    </>
  );
}

export default function DashboardPage() {
  const [datos, setDatos] = useState<AnaliticasPedidos | null>(null);
  const [mostrarExport, setMostrarExport] = useState(false);
  const [error, setError] = useState(false);
  // Se incrementa para volver a pedir los datos tras un error.
  const [intento, setIntento] = useState(0);

  useEffect(() => {
    let vigente = true;
    setError(false);
    httpClient
      .get<AnaliticasPedidos>("/api/v1/reportes/pedidos/analiticas")
      .then(({ data }) => {
        if (vigente) setDatos(data);
      })
      .catch(() => {
        if (vigente) setError(true);
      });
    return () => {
      vigente = false;
    };
  }, [intento]);

  const encabezado = (
    <div className="page-header">
      <div>
        <h1 className="page-title">Analíticas</h1>
        <p className="page-subtitle">
          Resumen del día ·{" "}
          {new Date().toLocaleDateString(undefined, { weekday: "long", day: "numeric", month: "long" })}
        </p>
      </div>
      <button className="btn btn-primary" onClick={() => setMostrarExport(true)} disabled={!datos}>
        <Icon name="descargar" size={16} />
        Exportar
      </button>
    </div>
  );

  if (!datos) {
    return (
      <div>
        {encabezado}
        {error ? (
          <div className="alert alert-error" role="alert">
            <Icon name="alerta" size={16} />
            <span style={{ flex: 1 }}>No se pudieron cargar las analíticas. Revisa la conexión e inténtalo de nuevo.</span>
            <button type="button" className="btn btn-secondary btn-sm" onClick={() => setIntento((n) => n + 1)}>
              <Icon name="sync" size={14} />
              Reintentar
            </button>
          </div>
        ) : (
          <DashboardSkeleton />
        )}
      </div>
    );
  }

  const datosPorCanal = Object.entries(datos.por_canal).map(([canal, cantidad]) => ({
    canal,
    cantidad,
  }));
  const totalCanales = datosPorCanal.reduce((suma, c) => suma + c.cantidad, 0);

  const totalHoy = datos.comparacion_hoy_vs_ayer.reduce((suma, p) => suma + p.hoy, 0);
  const totalAyer = datos.comparacion_hoy_vs_ayer.reduce((suma, p) => suma + p.ayer, 0);
  const variacion = totalAyer > 0 ? ((totalHoy - totalAyer) / totalAyer) * 100 : null;
  const claseDelta =
    variacion === null || Math.round(variacion) === 0
      ? styles.deltaIgual
      : variacion > 0
        ? styles.deltaSube
        : styles.deltaBaja;
  const textoDelta =
    variacion === null ? "Sin datos de ayer" : `${variacion > 0 ? "+" : ""}${porcentaje(variacion)}`;

  const kpis: Kpi[] = [
    {
      etiqueta: "Pedidos hoy",
      valor: datos.pedidos_totales_hoy,
      formato: (n) => Math.round(n).toString(),
      icono: "recibo",
      color: "#2563eb",
      detalle: `${datosPorCanal.length} ${datosPorCanal.length === 1 ? "canal activo" : "canales activos"}`,
    },
    {
      etiqueta: "Ticket promedio",
      valor: datos.ticket_promedio,
      formato: moneda,
      icono: "dinero",
      color: "#16a34a",
      detalle: "Por pedido del día",
    },
    {
      etiqueta: "Tiempo prom. preparación",
      valor: datos.tiempo_promedio_preparacion_minutos,
      formato: (n) => `${numero(n, 1)} min`,
      icono: "reloj",
      color: "#d97706",
      detalle: "Desde que se acepta hasta lista",
    },
    {
      etiqueta: "Cancelados hoy",
      valor: datos.pedidos_cancelados_hoy,
      formato: (n) => Math.round(n).toString(),
      icono: "prohibido",
      color: "#dc2626",
      detalle:
        datos.pedidos_totales_hoy > 0
          ? `${porcentaje((datos.pedidos_cancelados_hoy / datos.pedidos_totales_hoy) * 100)} del total`
          : "Sin pedidos hoy",
    },
  ];

  // Los gráficos son SVG: se describen con texto para lectores de pantalla.
  const descripcionCanales = `Pedidos de hoy por canal: ${datosPorCanal
    .map(({ canal, cantidad }) => `${infoCanal(canal).nombre} ${cantidad}`)
    .join(", ")}`;
  const descripcionHoras = `Pedidos por hora: ${totalHoy} hoy y ${totalAyer} ayer`;

  return (
    <div>
      {encabezado}

      <div className={styles.kpis}>
        {kpis.map((kpi, i) => (
          <KpiCard key={kpi.etiqueta} kpi={kpi} indice={i} />
        ))}
      </div>

      <div className={styles.graficos}>
        <div className={`${styles.panel} animate-in`} style={{ ["--i" as string]: 4 }}>
          <div className={styles.panelCabecera}>
            <div>
              <div className={styles.panelTitulo}>Pedidos por canal</div>
              <div className={styles.panelSub}>Hoy</div>
            </div>
          </div>
          {datosPorCanal.length === 0 ? (
            <div className="empty">
              <div className="empty-icon">
                <Icon name="analiticas" size={20} />
              </div>
              Aún no hay pedidos hoy.
            </div>
          ) : (
            <div role="img" aria-label={descripcionCanales}>
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={datosPorCanal} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={GRILLA} vertical={false} />
                <XAxis
                  dataKey="canal"
                  interval={0}
                  fontSize={11}
                  tickLine={false}
                  axisLine={false}
                  stroke={EJE}
                  tickFormatter={(c: string) => infoCanal(c).nombre}
                />
                <YAxis allowDecimals={false} fontSize={11} tickLine={false} axisLine={false} stroke={EJE} />
                <Tooltip
                  {...estiloTooltip}
                  labelFormatter={(c: string) => infoCanal(c).nombre}
                  formatter={(v: number) => [v, "Pedidos"]}
                />
                <Bar dataKey="cantidad" radius={[8, 8, 0, 0]} maxBarSize={56} animationDuration={900}>
                  {datosPorCanal.map(({ canal }) => (
                    <Cell key={canal} fill={infoCanal(canal).color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
            </div>
          )}
        </div>

        <div className={`${styles.panel} animate-in`} style={{ ["--i" as string]: 5 }}>
          <div className={styles.panelCabecera}>
            <div>
              <div className={styles.panelTitulo}>Pedidos por hora</div>
              <div className={styles.panelSub}>Hoy vs ayer</div>
            </div>
            <div className={styles.comparativa}>
              <strong>{totalHoy}</strong>
              hoy · {totalAyer} ayer
              <span className={`${styles.delta} ${claseDelta}`}>{textoDelta}</span>
            </div>
          </div>
          <div role="img" aria-label={descripcionHoras}>
          <ResponsiveContainer width="100%" height={260}>
            <AreaChart data={datos.comparacion_hoy_vs_ayer} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
              <defs>
                <linearGradient id="gradHoy" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={PRIMARIO} stopOpacity={0.28} />
                  <stop offset="100%" stopColor={PRIMARIO} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke={GRILLA} vertical={false} />
              <XAxis
                dataKey="hora"
                fontSize={11}
                tickLine={false}
                axisLine={false}
                stroke={EJE}
                tickFormatter={(h: number) => `${h}h`}
              />
              <YAxis allowDecimals={false} fontSize={11} tickLine={false} axisLine={false} stroke={EJE} />
              <Tooltip {...estiloTooltip} labelFormatter={(h: number) => `${h}:00 h`} />
              <Legend
                iconType="circle"
                iconSize={8}
                wrapperStyle={{ fontSize: 12, paddingTop: 8 }}
                formatter={(valor: string) => (valor === "hoy" ? "Hoy" : "Ayer")}
              />
              <Area
                type="monotone"
                dataKey="ayer"
                stroke={SECUNDARIO}
                strokeWidth={2}
                strokeDasharray="5 4"
                fill="transparent"
                dot={false}
                animationDuration={1000}
              />
              <Area
                type="monotone"
                dataKey="hoy"
                stroke={PRIMARIO}
                strokeWidth={2.5}
                fill="url(#gradHoy)"
                dot={false}
                activeDot={{ r: 5, strokeWidth: 2, stroke: "#fff" }}
                animationDuration={1000}
              />
            </AreaChart>
          </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="table-wrap animate-in" style={{ ["--i" as string]: 6 }}>
        <table className="table">
          <caption className="sr-only">Pedidos de hoy por canal</caption>
          <thead>
            <tr>
              <th scope="col">Canal</th>
              <th scope="col">Participación</th>
              <th scope="col" className="table-num">
                Pedidos hoy
              </th>
            </tr>
          </thead>
          <tbody>
            {datosPorCanal.map(({ canal, cantidad }) => {
              const participacion = totalCanales > 0 ? (cantidad / totalCanales) * 100 : 0;
              return (
                <tr key={canal}>
                  <td>
                    <CanalBadge origen={canal} />
                  </td>
                  <td className={styles.participacion}>
                    <div className={styles.barraFondo} aria-hidden="true">
                      <div
                        className={styles.barraRelleno}
                        style={{ width: `${participacion}%`, background: infoCanal(canal).color }}
                      />
                    </div>
                    <span className={styles.porcentaje}>{porcentaje(participacion)}</span>
                  </td>
                  <td className="table-num">
                    <strong>{cantidad}</strong>
                  </td>
                </tr>
              );
            })}
            {datosPorCanal.length === 0 && (
              <tr>
                <td colSpan={3} className={styles.sinDatos}>
                  Sin pedidos registrados hoy.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {mostrarExport && <ExportModal datos={datos} onClose={() => setMostrarExport(false)} />}
    </div>
  );
}
