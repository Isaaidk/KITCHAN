import type { ReactNode } from "react";
import styles from "./Ilustracion.module.css";

export type TipoIlustracion = "taza" | "gorro" | "cloche" | "lupa";

/**
 * Ilustraciones de cocina para los estados vacíos. Se dibujan con las variables de
 * color del sistema, así que se adaptan solas al modo oscuro.
 */
const DIBUJOS: Record<TipoIlustracion, ReactNode> = {
  // Taza de café con vapor
  taza: (
    <>
      <ellipse cx="70" cy="92" rx="42" ry="8" className={styles.relleno2} />
      <path d="M44 48h52v18c0 14-11 24-26 24S44 80 44 66z" className={styles.relleno} />
      <path d="M96 54h6a8 8 0 0 1 0 17h-8" fill="none" />
      <ellipse cx="70" cy="48" rx="26" ry="5" className={styles.cafe} />
      <path className={`${styles.vapor} ${styles.vapor1}`} d="M58 36c-4-6 4-8 0-14" />
      <path className={`${styles.vapor} ${styles.vapor2}`} d="M70 34c-4-6 4-8 0-14" />
      <path className={`${styles.vapor} ${styles.vapor3}`} d="M82 36c-4-6 4-8 0-14" />
    </>
  ),
  // Gorro de chef
  gorro: (
    <>
      <circle cx="52" cy="44" r="16" className={styles.relleno} />
      <circle cx="70" cy="36" r="18" className={styles.relleno} />
      <circle cx="88" cy="44" r="16" className={styles.relleno} />
      <rect x="44" y="52" width="52" height="32" rx="6" className={styles.relleno} />
      <path d="M44 72h52" className={styles.franja} />
      <path d="M26 30v8M22 34h8" className={styles.destello} />
      <path d="M112 24v6M109 27h6" className={styles.destello} />
    </>
  ),
  // Cloche (campana de servicio)
  cloche: (
    <>
      <path d="M28 76a42 38 0 0 1 84 0z" className={styles.relleno} />
      <rect x="20" y="76" width="100" height="9" rx="4.5" className={styles.relleno2} />
      <circle cx="70" cy="34" r="5" className={styles.ambar} />
      <path d="M44 66a28 26 0 0 1 14-20" fill="none" opacity="0.6" />
      <path d="M26 24v6M23 27h6" className={styles.destello} />
      <path d="M114 36v6M111 39h6" className={styles.destello} />
    </>
  ),
  // Lupa sobre un plato (sin resultados)
  lupa: (
    <>
      <circle cx="60" cy="52" r="30" className={styles.relleno} />
      <circle cx="60" cy="52" r="17" fill="none" strokeDasharray="3 5" />
      <path d="M82 74l22 22" className={styles.mango} />
      <path d="M52 52h16" opacity="0.5" />
    </>
  ),
};

interface Props {
  tipo: TipoIlustracion;
  /** Ancho en px; la altura se ajusta sola. */
  ancho?: number;
}

export default function Ilustracion({ tipo, ancho = 132 }: Props) {
  return (
    <svg
      className={styles.ilustracion}
      width={ancho}
      viewBox="0 0 140 110"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.4"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {DIBUJOS[tipo]}
    </svg>
  );
}
