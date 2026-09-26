import type { ReactNode } from "react";
import Icon from "../../shared/components/Icon";
import styles from "./LoginPage.module.css";

const CANALES = [
  { nombre: "Uber Eats", color: "#06C167" },
  { nombre: "Rappi", color: "#FF441F" },
  { nombre: "PedidosYa", color: "#EA004B" },
];

/** Marco compartido por Login y Registro: panel de marca + formulario. */
export default function AuthLayout({ children, ancho = 400 }: { children: ReactNode; ancho?: number }) {
  return (
    <div className={styles.pantalla}>
      <aside className={styles.panelMarca}>
        <div className={styles.marcaFila}>
          <div className={styles.logo}>K</div>
          <span className={styles.marcaNombre}>KITCHAN</span>
        </div>

        <div className={styles.mensaje}>
          <h1 className={styles.titular}>
            Todos tus pedidos,
            <br />
            una sola cocina.
          </h1>
          <p className={styles.bajada}>
            Centraliza los pedidos de tus plataformas de delivery en un tablero en tiempo real
            para tu equipo de cocina.
          </p>

          <ul className={styles.beneficios}>
            <li>
              <Icon name="rayo" size={16} /> Pedidos en vivo, sin recargar la página
            </li>
            <li>
              <Icon name="cola" size={16} /> Flujo claro: nueva, en preparación, lista
            </li>
            <li>
              <Icon name="analiticas" size={16} /> Métricas del día por canal
            </li>
          </ul>
        </div>

        <div className={styles.canales}>
          {CANALES.map((c, i) => (
            <span
              key={c.nombre}
              className={styles.canal}
              style={{ ["--c" as string]: c.color, ["--i" as string]: i }}
            >
              <span className={styles.canalPunto} />
              {c.nombre}
            </span>
          ))}
        </div>

        <div className={styles.orbe1} />
        <div className={styles.orbe2} />
      </aside>

      <main className={styles.panelForm}>
        <div className={styles.tarjeta} style={{ maxWidth: ancho }}>
          {children}
        </div>
      </main>
    </div>
  );
}
