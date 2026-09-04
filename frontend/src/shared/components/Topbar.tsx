import { useNavigate } from "react-router-dom";
import { useAuthStore } from "../stores/authStore";
import styles from "./Topbar.module.css";

export default function Topbar() {
  const { usuario, logout } = useAuthStore();
  const navigate = useNavigate();

  const salir = () => {
    logout();
    navigate("/login", { replace: true });
  };

  return (
    <header className={styles.topbar}>
      <span className={styles.usuario}>
        {usuario?.nombre} · {usuario?.rol}
      </span>
      <button className={styles.logout} onClick={salir}>
        Cerrar sesión
      </button>
    </header>
  );
}
