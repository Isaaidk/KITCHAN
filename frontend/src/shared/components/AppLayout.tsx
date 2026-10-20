import { useEffect, useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import Sidebar from "./Sidebar";
import Topbar from "./Topbar";
import ToastContainer from "../../features/notificaciones/ToastContainer";
import { useOrdersSocket } from "../../features/pedidos/useOrdersSocket";
import styles from "./AppLayout.module.css";

export default function AppLayout() {
  useOrdersSocket();
  const { pathname } = useLocation();
  // Drawer del sidebar en tablet/móvil.
  const [menuAbierto, setMenuAbierto] = useState(false);

  useEffect(() => {
    setMenuAbierto(false);
  }, [pathname]);

  // Escape cierra el drawer (alternativa de teclado al clic en el velo).
  useEffect(() => {
    if (!menuAbierto) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setMenuAbierto(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [menuAbierto]);

  return (
    <div className={styles.contenedor}>
      <a href="#contenido" className="skip-link">
        Saltar al contenido
      </a>
      <Sidebar abierto={menuAbierto} onNavegar={() => setMenuAbierto(false)} />
      <div
        className={`${styles.velo} ${menuAbierto ? styles.veloVisible : ""}`}
        onClick={() => setMenuAbierto(false)}
        aria-hidden="true"
      />
      <div className={styles.principal}>
        <Topbar onMenu={() => setMenuAbierto(true)} />
        <main id="contenido" tabIndex={-1} className={styles.contenido}>
          {/* key por ruta: cada cambio de página reproduce la transición de entrada. */}
          <div key={pathname} className={styles.pagina}>
            <Outlet />
          </div>
        </main>
      </div>
      <ToastContainer />
    </div>
  );
}
