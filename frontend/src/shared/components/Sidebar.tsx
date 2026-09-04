import { NavLink } from "react-router-dom";
import { useAuthStore } from "../stores/authStore";
import styles from "./Sidebar.module.css";

const enlace = ({ isActive }: { isActive: boolean }) =>
  isActive ? `${styles.link} ${styles.linkActivo}` : styles.link;

export default function Sidebar() {
  const rol = useAuthStore((s) => s.usuario?.rol);

  return (
    <nav className={styles.sidebar}>
      <div className={styles.marca}>KITCHAN</div>
      <NavLink to="/" end className={enlace}>
        Cola de pedidos
      </NavLink>
      <NavLink to="/historial" className={enlace}>
        Historial
      </NavLink>
      {rol === "ADMIN" && (
        <>
          <NavLink to="/analiticas" className={enlace}>
            Analíticas
          </NavLink>
          <NavLink to="/usuarios" className={enlace}>
            Usuarios
          </NavLink>
          <NavLink to="/integraciones" className={enlace}>
            Integraciones
          </NavLink>
        </>
      )}
    </nav>
  );
}
