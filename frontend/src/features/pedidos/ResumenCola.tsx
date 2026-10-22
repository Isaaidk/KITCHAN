import Icon, { type NombreIcono } from "../../shared/components/Icon";
import type { Pedido } from "../../shared/types/pedido";
import { numero } from "../../shared/utils/formato";
import { LIMITE_DEMORA_MINUTOS, minutosTranscurridos } from "./estadoUtils";
import styles from "./ResumenCola.module.css";

interface Dato {
  etiqueta: string;
  valor: string;
  detalle: string;
  icono: NombreIcono;
  alerta?: boolean;
}

/**
 * Estado de la cocina de un vistazo. Solo cuenta lo que falta preparar
 * (pendientes y en preparación): lo que ya está listo espera retiro, no demora la cocina.
 * `ahora` fuerza el recálculo cuando la página refresca los minutos.
 */
export default function ResumenCola({ pedidos }: { pedidos: Pedido[]; ahora: number }) {
  const activos = pedidos.length;
  const porPreparar = pedidos.filter((p) => p.estado === "NUEVA" || p.estado === "EN_PREPARACION");
  const esperas = porPreparar.map((p) => minutosTranscurridos(p.fecha_creacion));
  const demorados = esperas.filter((m) => m >= LIMITE_DEMORA_MINUTOS).length;
  const promedio = esperas.length ? Math.round(esperas.reduce((a, b) => a + b, 0) / esperas.length) : 0;
  const maximo = esperas.length ? Math.max(...esperas) : 0;

  const datos: Dato[] = [
    {
      etiqueta: "Pedidos activos",
      valor: numero(activos),
      detalle: `${numero(porPreparar.length)} por preparar`,
      icono: "bandeja",
    },
    {
      etiqueta: "Demorados",
      valor: numero(demorados),
      detalle: demorados === 0 ? "Todo en tiempo" : `Más de ${LIMITE_DEMORA_MINUTOS} min`,
      icono: "alerta",
      alerta: demorados > 0,
    },
    {
      etiqueta: "Espera promedio",
      valor: porPreparar.length ? `${promedio} min` : "—",
      detalle: "De lo que falta preparar",
      icono: "reloj",
    },
    {
      etiqueta: "Pedido más antiguo",
      valor: porPreparar.length ? `${maximo} min` : "—",
      detalle: "Esperando en cocina",
      icono: "cola",
      alerta: maximo >= LIMITE_DEMORA_MINUTOS,
    },
  ];

  return (
    <ul className={styles.resumen} aria-label="Resumen de la cocina">
      {datos.map((d) => (
        <li key={d.etiqueta} className={`${styles.dato} ${d.alerta ? styles.alerta : ""}`}>
          <span className={styles.icono}>
            <Icon name={d.icono} size={18} />
          </span>
          <span className={styles.valor}>{d.valor}</span>
          <span className={styles.etiqueta}>{d.etiqueta}</span>
          <span className={styles.detalle}>{d.detalle}</span>
        </li>
      ))}
    </ul>
  );
}
