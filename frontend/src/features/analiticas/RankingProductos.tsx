import { moneda, numero } from "../../shared/utils/formato";
import type { ProductoVendido } from "./types";
import styles from "./Compartido.module.css";

interface Props {
  items: ProductoVendido[];
  /** Estilo ámbar para el ranking de lo que menos se pide. */
  menos?: boolean;
  /** Mide cada plato por lo que facturó (la barra y la cifra principal son dinero) en vez de por unidades. */
  porVentas?: boolean;
  /** Texto cuando todavía no hay ventas que mostrar. */
  vacio: string;
}

/** Lista numerada de platos con una barra proporcional a las unidades vendidas. */
export default function RankingProductos({ items, menos = false, porVentas = false, vacio }: Props) {
  if (items.length === 0) {
    return (
      <div className={styles.vacio}>
        <span>{vacio}</span>
      </div>
    );
  }

  const medida = (item: ProductoVendido) => (porVentas ? item.ventas : item.cantidad);
  const maximo = Math.max(...items.map(medida), 1);
  return (
    <ol className={`${styles.ranking} ${menos ? styles.menos : ""}`}>
      {items.map((item, i) => (
        <li key={item.nombre} className={styles.puesto}>
          <span className={styles.posicion}>{i + 1}</span>
          <span className={styles.puestoNombre} title={item.nombre}>
            {item.nombre}
          </span>
          <span className={styles.puestoCifras}>
            {porVentas ? (
              <>
                <strong>{moneda(item.ventas)}</strong> en {numero(item.cantidad)} {item.cantidad === 1 ? "unidad" : "unidades"}
              </>
            ) : (
              <>
                <strong>{numero(item.cantidad)}</strong> {item.cantidad === 1 ? "unidad" : "unidades"} por {moneda(item.ventas)}
              </>
            )}
          </span>
          <span className={styles.barraFondo} aria-hidden="true">
            <span className={styles.barraRelleno} style={{ width: `${(medida(item) / maximo) * 100}%` }} />
          </span>
        </li>
      ))}
    </ol>
  );
}
