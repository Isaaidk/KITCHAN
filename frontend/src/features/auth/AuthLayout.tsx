import type { ReactNode } from "react";
import { GorroChef } from "../../shared/components/KitchanLogo";
import fotoLogin from "../../assets/login-vangalia.webp";
import styles from "./LoginPage.module.css";

/** Marco compartido por Login y Registro: panel de marca Vangalia + formulario. */
export default function AuthLayout({ children, ancho = 520 }: { children: ReactNode; ancho?: number }) {
  return (
    <div className={styles.pantalla}>
      <aside className={styles.panelMarca}>
        <GorroChef tamano={470} className={styles.marcaDeco} />

        <div className={styles.marca}>
          <GorroChef tamano={96} className={styles.marcaGorro} />
          <h1 className={styles.marcaNombre}>Vangalia</h1>
          <div className={styles.marcaPlataforma}>KITCHAN</div>
          <p className={styles.lema}>
            Más que pedidos,
            <br />
            <span className={styles.lemaScript}>
              mejores momentos
              <svg className={styles.lemaTrazo} viewBox="0 0 220 12" fill="none" aria-hidden="true">
                <path d="M2 9C50 3 130 1 218 6" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" />
              </svg>
            </span>
          </p>
        </div>

        {/* Imagen decorativa: no aporta información que no esté ya en el texto */}
        <img className={styles.foto} src={fotoLogin} alt="" width={800} height={509} />
      </aside>

      <main className={styles.panelForm}>
        <GorroChef tamano={250} className={styles.decoGorro} />
        <div className={styles.tarjeta} style={{ maxWidth: ancho }}>
          {children}
        </div>
      </main>
    </div>
  );
}
