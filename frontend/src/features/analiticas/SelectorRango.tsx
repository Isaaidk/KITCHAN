import type { Rango } from "./types";
import { RANGOS } from "./useDashboard";
import styles from "./SelectorRango.module.css";

interface Props {
  valor: Rango;
  onCambio: (rango: Rango) => void;
  /** "claro" para usarlo sobre fondos oscuros (la cabecera granate del dashboard). */
  tono?: "normal" | "claro";
}

/** Selector segmentado del periodo (Hoy, 7 días, 30 días). */
export default function SelectorRango({ valor, onCambio, tono = "normal" }: Props) {
  return (
    <div
      className={`${styles.grupo} ${tono === "claro" ? styles.claro : ""}`}
      role="group"
      aria-label="Periodo a analizar"
    >
      {RANGOS.map((r) => (
        <button
          key={r.valor}
          type="button"
          aria-pressed={valor === r.valor}
          className={`${styles.opcion} ${valor === r.valor ? styles.activa : ""}`}
          onClick={() => onCambio(r.valor)}
        >
          {r.etiqueta}
        </button>
      ))}
    </div>
  );
}
