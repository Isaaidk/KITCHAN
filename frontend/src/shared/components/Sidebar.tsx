import { NavLink } from "react-router-dom";
import { useAuthStore } from "../stores/authStore";
import { useOrdersStore } from "../stores/ordersStore";
import Icon, { type NombreIcono } from "./Icon";
import styles from "./Sidebar.module.css";

const enlace = ({ isActive }: { isActive: boolean }) =>
  isActive ? `${styles.link} ${styles.linkActivo}` : styles.link;

interface Props {
  abierto: boolean;
  onNavegar: () => void;
}

function Enlace({
  to,
  icono,
  children,
  end,
  contador,
  onNavegar,
}: {
  to: string;
  icono: NombreIcono;
  children: string;
  end?: boolean;
  contador?: number;
  onNavegar: () => void;
}) {
  return (
    <NavLink to={to} end={end} className={enlace} onClick={onNavegar}>
      <Icon name={icono} size={18} className={styles.icono} />
      <span className={styles.texto}>{children}</span>
      {!!contador && <span className={styles.contador}>{contador}</span>}
    </NavLink>
  );
}

export default function Sidebar({ abierto, onNavegar }: Props) {
  const rol = useAuthStore((s) => s.usuario?.rol);
  // Pedidos nuevos esperando: se muestran como contador junto a la cola.
  const nuevos = useOrdersStore(
    (s) => Object.values(s.pedidos).filter((p) => p.estado === "NUEVA").length,
  );

  return (
    <nav className={`${styles.sidebar} ${abierto ? styles.abierto : ""}`}>
      <div className={styles.marca}>
        <div className={styles.logo}>K</div>
        <div>
          <div className={styles.marcaNombre}>KITCHAN</div>
          <div className={styles.marcaSub}>Gestión de pedidos</div>
        </div>
      </div>

      <div className={styles.seccion}>Operación</div>
      <Enlace to="/" end icono="cola" contador={nuevos} onNavegar={onNavegar}>
        Cola de pedidos
      </Enlace>
      <Enlace to="/historial" icono="historial" onNavegar={onNavegar}>
        Historial
      </Enlace>

      {rol === "ADMIN" && (
        <>
          <div className={styles.seccion}>Administración</div>
          <Enlace to="/analiticas" icono="analiticas" onNavegar={onNavegar}>
            Analíticas
          </Enlace>
          <Enlace to="/usuarios" icono="usuarios" onNavegar={onNavegar}>
            Usuarios
          </Enlace>
          <Enlace to="/integraciones" icono="integraciones" onNavegar={onNavegar}>
            Integraciones
          </Enlace>
        </>
      )}

      <div className={styles.pie}>
        <Icon name="rayo" size={14} />
        <span>Pedidos en tiempo real</span>
      </div>
    </nav>
  );
}
