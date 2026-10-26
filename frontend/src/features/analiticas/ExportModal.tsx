import { useEffect, useRef, useState } from "react";
import CanalLogo from "../../shared/components/CanalLogo";
import Icon from "../../shared/components/Icon";
import Modal from "../../shared/components/Modal";
import { httpClient } from "../../shared/api/httpClient";
import { moneda, numero } from "../../shared/utils/formato";
import { infoCanal } from "../pedidos/estadoUtils";
import type { DashboardPedidos } from "./types";
import styles from "./ExportModal.module.css";

interface Props {
  datos: DashboardPedidos;
  onClose: () => void;
}

// Con puntos decimales fijos y sin separador de miles: el CSV debe abrirse igual en cualquier Excel.
const dos = (n: number) => n.toFixed(2);

function generarCSV(datos: DashboardPedidos): string {
  const filas = [
    ["canal", "pedidos", "cancelados", "ventas", "ticket_promedio", "tiempo_promedio_min", "porcentaje_demorados"],
  ];
  datos.por_canal.forEach((c) => {
    filas.push([
      c.canal,
      String(c.pedidos),
      String(c.cancelados),
      dos(c.ventas),
      dos(c.ticket_promedio),
      c.tiempo_promedio_minutos.toFixed(1),
      c.tasa_demora.toFixed(1),
    ]);
  });
  return filas.map((fila) => fila.join(",")).join("\n");
}

// Fecha local (AAAA-MM-DD): toISOString usa UTC y de noche daría la fecha de mañana.
const formatoFecha = new Intl.DateTimeFormat("sv-SE", { year: "numeric", month: "2-digit", day: "2-digit" });

function nombreArchivo(rango: string, extension: "csv" | "xlsx" | "pdf"): string {
  return `kitchan-analiticas-${rango}-${formatoFecha.format(new Date())}.${extension}`;
}

export default function ExportModal({ datos, onClose }: Props) {
  const [copiado, setCopiado] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [verCsv, setVerCsv] = useState(false);
  const [generando, setGenerando] = useState<"xlsx" | "pdf" | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const csv = generarCSV(datos);

  const canales = datos.por_canal;
  const ventas = canales.reduce((suma, c) => suma + c.ventas, 0);
  const pedidos = canales.reduce((suma, c) => suma + c.pedidos, 0);

  useEffect(
    () => () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    },
    [],
  );

  const copiar = async () => {
    setError(null);
    try {
      await navigator.clipboard.writeText(csv);
      setCopiado(true);
      timerRef.current = setTimeout(() => setCopiado(false), 2000);
    } catch {
      setError("No se pudo copiar. Descarga el archivo o selecciona el texto manualmente.");
      setVerCsv(true);
    }
  };

  const descargarBlob = (blob: Blob, nombre: string) => {
    const url = URL.createObjectURL(blob);
    const enlace = document.createElement("a");
    enlace.href = url;
    enlace.download = nombre;
    // Firefox exige el enlace dentro del documento; y se libera la URL un
    // poco después para no cancelar la descarga en Safari.
    document.body.appendChild(enlace);
    enlace.click();
    enlace.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };

  const descargar = () =>
    descargarBlob(new Blob([csv], { type: "text/csv;charset=utf-8" }), nombreArchivo(datos.rango, "csv"));

  // Excel y PDF los genera el backend (mismas métricas que ve el dashboard).
  const descargarServidor = async (formato: "xlsx" | "pdf") => {
    setError(null);
    setGenerando(formato);
    try {
      const { data } = await httpClient.get<Blob>("/api/v1/reportes/pedidos/analiticas/exportar", {
        params: { formato, rango: datos.rango, ...(datos.canal ? { canal: datos.canal } : {}) },
        responseType: "blob",
      });
      descargarBlob(data, nombreArchivo(datos.rango, formato));
    } catch {
      setError(`No se pudo generar el archivo ${formato === "xlsx" ? "Excel" : "PDF"}. Inténtalo de nuevo.`);
    } finally {
      setGenerando(null);
    }
  };

  return (
    <Modal titulo="Exportar analíticas" onClose={onClose}>
      <p className={styles.intro}>
        Analíticas del periodo ({datos.desde === datos.hasta ? datos.desde : `${datos.desde} al ${datos.hasta}`}) en
        Excel o PDF con el dashboard completo, o el CSV de comparación de canales.
      </p>

      <div className={styles.vista}>
        <div className={styles.vistaTitulo}>
          Vista previa
          <span className={styles.vistaResumen}>
            {canales.length} {canales.length === 1 ? "canal" : "canales"}, {numero(pedidos)}{" "}
            {pedidos === 1 ? "pedido" : "pedidos"} y {moneda(ventas)} en ventas
          </span>
        </div>
        {canales.length === 0 ? (
          <div className={styles.vacio}>Aún no hay pedidos en este periodo, así que el archivo solo tendría la cabecera.</div>
        ) : (
          <ul className={styles.lista}>
            {canales.map((c) => {
              const { nombre, color } = infoCanal(c.canal);
              return (
                <li key={c.canal} className={styles.fila}>
                  <CanalLogo canal={c.canal} color={color} nombre={nombre} size={26} />
                  <span className={styles.canal}>{nombre}</span>
                  <span className={styles.cantidad}>{moneda(c.ventas)}</span>
                </li>
              );
            })}
          </ul>
        )}
      </div>

      <button
        type="button"
        className={styles.alternar}
        onClick={() => setVerCsv((v) => !v)}
        aria-expanded={verCsv}
        aria-controls="export-csv"
      >
        <Icon name="flecha" size={13} className={verCsv ? styles.flechaAbierta : undefined} />
        {verCsv ? "Ocultar CSV" : "Ver CSV"}
      </button>
      {verCsv && (
        <textarea
          id="export-csv"
          name="csv"
          className={`textarea ${styles.csv}`}
          aria-label="Contenido del archivo CSV"
          readOnly
          spellCheck={false}
          translate="no"
          value={csv}
          rows={Math.min(8, canales.length + 2)}
        />
      )}

      {error && (
        <div className="alert alert-error" role="alert">
          <Icon name="alerta" size={16} />
          {error}
        </div>
      )}

      <div className={styles.acciones}>
        <button className={`btn ${copiado ? "btn-success" : "btn-secondary"}`} onClick={copiar}>
          <Icon name={copiado ? "check" : "copiar"} size={16} />
          {copiado ? "Copiado" : "Copiar"}
        </button>
        {/* Anuncia el resultado a lectores de pantalla; el botón ya lo muestra visualmente. */}
        <span className="sr-only" role="status">
          {copiado ? "CSV copiado al portapapeles" : ""}
        </span>
        <button className="btn btn-secondary" onClick={descargar}>
          <Icon name="descargar" size={16} />
          CSV
        </button>
        <button
          className="btn btn-secondary"
          onClick={() => descargarServidor("pdf")}
          disabled={generando !== null}
        >
          <Icon name="descargar" size={16} />
          {generando === "pdf" ? "Generando…" : "PDF"}
        </button>
        <button
          className="btn btn-primary"
          onClick={() => descargarServidor("xlsx")}
          disabled={generando !== null}
        >
          <Icon name="descargar" size={16} />
          {generando === "xlsx" ? "Generando…" : "Excel"}
        </button>
      </div>
    </Modal>
  );
}
