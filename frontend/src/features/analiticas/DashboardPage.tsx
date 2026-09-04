import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { httpClient } from "../../shared/api/httpClient";
import ExportModal from "./ExportModal";
import type { AnaliticasPedidos } from "./types";
import styles from "./DashboardPage.module.css";

export default function DashboardPage() {
  const [datos, setDatos] = useState<AnaliticasPedidos | null>(null);
  const [mostrarExport, setMostrarExport] = useState(false);

  useEffect(() => {
    httpClient.get<AnaliticasPedidos>("/api/v1/reportes/pedidos/analiticas").then(({ data }) => {
      setDatos(data);
    });
  }, []);

  if (!datos) return <div>Cargando...</div>;

  const datosPorCanal = Object.entries(datos.por_canal).map(([canal, cantidad]) => ({
    canal,
    cantidad,
  }));

  return (
    <div>
      <div className={styles.encabezado}>
        <h2>Analíticas</h2>
        <button className={styles.exportar} onClick={() => setMostrarExport(true)}>
          Exportar
        </button>
      </div>

      <div className={styles.kpis}>
        <div className={styles.kpi}>
          <div className={styles.kpiValor}>{datos.pedidos_totales_hoy}</div>
          <div className={styles.kpiLabel}>Pedidos hoy</div>
        </div>
        <div className={styles.kpi}>
          <div className={styles.kpiValor}>${datos.ticket_promedio.toFixed(2)}</div>
          <div className={styles.kpiLabel}>Ticket promedio</div>
        </div>
        <div className={styles.kpi}>
          <div className={styles.kpiValor}>
            {datos.tiempo_promedio_preparacion_minutos.toFixed(1)} min
          </div>
          <div className={styles.kpiLabel}>Tiempo prom. preparación</div>
        </div>
        <div className={styles.kpi}>
          <div className={styles.kpiValor}>{datos.pedidos_cancelados_hoy}</div>
          <div className={styles.kpiLabel}>Cancelados hoy</div>
        </div>
      </div>

      <div className={styles.graficos}>
        <div className={styles.panel}>
          <div className={styles.panelTitulo}>Pedidos por canal (hoy)</div>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={datosPorCanal}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="canal" fontSize={11} />
              <YAxis allowDecimals={false} fontSize={11} />
              <Tooltip />
              <Bar dataKey="cantidad" fill="var(--color-primary)" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className={styles.panel}>
          <div className={styles.panelTitulo}>Pedidos por hora: hoy vs ayer</div>
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={datos.comparacion_hoy_vs_ayer}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="hora" fontSize={11} />
              <YAxis allowDecimals={false} fontSize={11} />
              <Tooltip />
              <Line type="monotone" dataKey="hoy" stroke="var(--color-primary)" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="ayer" stroke="var(--color-text-muted)" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      <table className={styles.tabla}>
        <thead>
          <tr>
            <th>Canal</th>
            <th>Pedidos hoy</th>
          </tr>
        </thead>
        <tbody>
          {datosPorCanal.map(({ canal, cantidad }) => (
            <tr key={canal}>
              <td>{canal}</td>
              <td>{cantidad}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {mostrarExport && <ExportModal datos={datos} onClose={() => setMostrarExport(false)} />}
    </div>
  );
}
