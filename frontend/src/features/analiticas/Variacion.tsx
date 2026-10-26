import { variacion } from "../../shared/utils/formato";
import styles from "./Variacion.module.css";

interface Props {
  actual: number;
  anterior: number;
  /** En tiempos y cancelaciones bajar es bueno: el color se invierte. */
  menorEsMejor?: boolean;
  /** Frase para lectores de pantalla, p. ej. "que ayer". */
  contra?: string;
}

/** Chip con la variación frente al periodo anterior (▲ +12% / ▼ −5%). */
export default function Variacion({ actual, anterior, menorEsMejor = false, contra = "que el periodo anterior" }: Props) {
  const cambio = variacion(actual, anterior);
  if (cambio === null) {
    return <span className={`${styles.chip} ${styles.neutro}`}>Sin periodo anterior</span>;
  }

  const redondeado = Math.round(cambio);
  const direccion = redondeado === 0 ? "igual" : redondeado > 0 ? "sube" : "baja";
  const bueno = direccion === "igual" ? null : (direccion === "sube") !== menorEsMejor;
  const clase = bueno === null ? styles.neutro : bueno ? styles.bueno : styles.malo;
  const signo = redondeado > 0 ? "+" : redondeado < 0 ? "−" : "";
  const texto = `${signo}${Math.abs(redondeado)}%`;

  return (
    <span className={`${styles.chip} ${clase}`}>
      <span aria-hidden="true">{direccion === "sube" ? "▲" : direccion === "baja" ? "▼" : "●"}</span>
      {texto}
      <span className="sr-only">
        {direccion === "igual" ? ` igual ${contra}` : ` ${direccion === "sube" ? "más" : "menos"} ${contra}`}
      </span>
    </span>
  );
}
