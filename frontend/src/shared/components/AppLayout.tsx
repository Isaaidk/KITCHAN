import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";
import Topbar from "./Topbar";
import ToastContainer from "../../features/notificaciones/ToastContainer";
import { useOrdersSocket } from "../../features/pedidos/useOrdersSocket";
import styles from "./AppLayout.module.css";

export default function AppLayout() {
  useOrdersSocket();

  return (
    <div className={styles.contenedor}>
      <Sidebar />
      <div className={styles.principal}>
        <Topbar />
        <main className={styles.contenido}>
          <Outlet />
        </main>
      </div>
      <ToastContainer />
    </div>
  );
}
