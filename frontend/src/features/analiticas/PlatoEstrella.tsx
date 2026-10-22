import Ilustracion from "../../shared/components/Ilustracion";
import { horaEtiqueta, moneda, numero } from "../../shared/utils/formato";
import type { DashboardPedidos } from "./types";
import styles from "./PlatoEstrella.module.css";

/** El plato favorito del periodo: el más vendido, con sus unidades, lo que facturó y la hora pico. */
export default function PlatoEstrella({ datos, periodo }: { datos: DashboardPedidos; periodo: string }) {
  const plato = datos.productos_mas_vendidos[0];
  const pico = datos.hora_pico;

  return (
    <section className={styles.tarjeta} aria-labelledby="plato-estrella">
      <div className={styles.dibujo}>
        <Ilustracion tipo="cloche" ancho={104} />
      </div>
      <div className={styles.texto}>
        <p className={styles.etiqueta} id="plato-estrella">
          Plato estrella
        </p>
        {plato ? (
          <>
            <p className={styles.nombre}>{plato.nombre}</p>
            <p className={styles.detalle}>
              <strong>
                {numero(plato.cantidad)} {plato.cantidad === 1 ? "unidad" : "unidades"}
              </strong>{" "}
              por {moneda(plato.ventas)} en {periodo}
              {pico && <>, con hora pico a las {horaEtiqueta(pico.hora)}</>}
            </p>
          </>
        ) : (
          <p className={styles.detalle}>Cuando salgan los primeros pedidos, aquí verás cuál es el favorito.</p>
        )}
      </div>
    </section>
  );
}
