import styles from "./KitchanLogo.module.css";

interface Props {
  /** "completo": gorro + nombre; "icono": solo el gorro. */
  variante?: "completo" | "icono";
  /** "oscuro" para fondos claros (granate + turquesa); "claro" para fondos oscuros (crema + turquesa). */
  tono?: "oscuro" | "claro";
  /** Alto del gorro en px; el nombre escala con él. */
  tamano?: number;
  className?: string;
}

/** Gorro de chef de la marca, dibujado en línea (hereda el color con currentColor). */
export function GorroChef({ tamano = 40, className }: { tamano?: number; className?: string }) {
  return (
    <svg
      className={className}
      width={tamano * (64 / 56)}
      height={tamano}
      viewBox="0 0 64 56"
      fill="none"
      stroke="currentColor"
      strokeWidth={4.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M19 36C10 35 5 27 9 20c3-6 11-7 16-3 2-7 12-7 14 0 5-4 13-3 16 3 4 7-1 15-10 16" />
      <path d="M19 36v12h26V36" />
      <path d="M19 42h26" strokeWidth={3} />
    </svg>
  );
}

export default function KitchanLogo({ variante = "completo", tono = "oscuro", tamano = 40, className }: Props) {
  return (
    <span
      className={`${styles.logo} ${tono === "claro" ? styles.claro : styles.oscuro} ${className ?? ""}`}
      role="img"
      aria-label="KITCHAN"
    >
      <GorroChef tamano={tamano} className={styles.gorro} />
      {variante === "completo" && (
        <span className={styles.nombre} style={{ fontSize: tamano * 0.62 }} aria-hidden="true">
          <span className={styles.kit}>KIT</span>
          <span className={styles.chan}>CHAN</span>
        </span>
      )}
    </span>
  );
}
