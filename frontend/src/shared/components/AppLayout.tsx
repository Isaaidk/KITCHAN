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

  return (
    <div className={styles.contenedor}>
      <Sidebar abierto={menuAbierto} onNavegar={() => setMenuAbierto(false)} />
      <div
        className={`${styles.velo} ${menuAbierto ? styles.veloVisible : ""}`}
        onClick={() => setMenuAbierto(false)}
      />
      <div className={styles.principal}>
        <Topbar onMenu={() => setMenuAbierto(true)} />
        <main className={styles.contenido}>
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
