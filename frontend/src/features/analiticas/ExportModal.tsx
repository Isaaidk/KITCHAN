import { useEffect, useRef, useState } from "react";
import CanalLogo from "../../shared/components/CanalLogo";
import Icon from "../../shared/components/Icon";
import Modal from "../../shared/components/Modal";
import { infoCanal } from "../pedidos/estadoUtils";
import type { AnaliticasPedidos } from "./types";
import styles from "./ExportModal.module.css";

interface Props {
  datos: AnaliticasPedidos;
  onClose: () => void;
}

function generarCSV(datos: AnaliticasPedidos): string {
  const filas = [["canal", "pedidos_hoy"]];
  Object.entries(datos.por_canal).forEach(([canal, cantidad]) => {
    filas.push([canal, String(cantidad)]);
  });
  return filas.map((fila) => fila.join(",")).join("\n");
}

function nombreArchivo(): string {
  return `kitchan-analiticas-${new Date().toISOString().slice(0, 10)}.csv`;
}

export default function ExportModal({ datos, onClose }: Props) {
  const [copiado, setCopiado] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [verCsv, setVerCsv] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const csv = generarCSV(datos);

  const canales = Object.entries(datos.por_canal);
  const total = canales.reduce((suma, [, cantidad]) => suma + cantidad, 0);

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

  const descargar = () => {
    const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
    const enlace = document.createElement("a");
    enlace.href = url;
    enlace.download = nombreArchivo();
    enlace.click();
    URL.revokeObjectURL(url);
  };

  return (
    <Modal titulo="Exportar analíticas" onClose={onClose}>
      <p className={styles.intro}>
        Pedidos de hoy por canal, en formato CSV para abrir en Excel o Google Sheets.
      </p>

      <div className={styles.vista}>
        <div className={styles.vistaTitulo}>
          Vista previa
          <span className={styles.vistaResumen}>
            {canales.length} {canales.length === 1 ? "canal" : "canales"} · {total}{" "}
            {total === 1 ? "pedido" : "pedidos"}
          </span>
        </div>
        {canales.length === 0 ? (
          <div className={styles.vacio}>Aún no hay pedidos hoy, así que el archivo solo tendría la cabecera.</div>
        ) : (
          <ul className={styles.lista}>
            {canales.map(([canal, cantidad]) => {
              const { nombre, color } = infoCanal(canal);
              return (
                <li key={canal} className={styles.fila}>
                  <CanalLogo canal={canal} color={color} nombre={nombre} size={26} />
                  <span className={styles.canal}>{nombre}</span>
                  <span className={styles.cantidad}>{cantidad}</span>
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
      >
        <Icon name="flecha" size={13} className={verCsv ? styles.flechaAbierta : undefined} />
        {verCsv ? "Ocultar CSV" : "Ver CSV"}
      </button>
      {verCsv && <textarea className={`textarea ${styles.csv}`} readOnly value={csv} rows={Math.min(8, canales.length + 2)} />}

      {error && (
        <div className="alert alert-error">
          <Icon name="alerta" size={16} />
          {error}
        </div>
      )}

      <div className={styles.acciones}>
        <button className={`btn ${copiado ? "btn-success" : "btn-secondary"}`} onClick={copiar}>
          <Icon name={copiado ? "check" : "copiar"} size={16} />
          {copiado ? "Copiado" : "Copiar"}
        </button>
        <button className="btn btn-primary" onClick={descargar}>
          <Icon name="descargar" size={16} />
          Descargar CSV
        </button>
      </div>
    </Modal>
  );
}
