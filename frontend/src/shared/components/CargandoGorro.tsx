import { GorroChef } from "./KitchanLogo";
import styles from "./CargandoGorro.module.css";

/** Indicador de carga de las pantallas de datos: el gorro de chef rebota mientras llega la información. */
export default function CargandoGorro({ texto = "Cargando…" }: { texto?: string }) {
  return (
    <div className={styles.contenedor} role="status">
      <GorroChef tamano={56} className={styles.gorro} />
      <span className={styles.sombra} aria-hidden="true" />
      <span className={styles.texto}>{texto}</span>
    </div>
  );
}
