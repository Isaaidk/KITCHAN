import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuthStore } from "../stores/authStore";
import { useOrdersStore } from "../stores/ordersStore";
import { useTemaStore } from "../stores/temaStore";
import Icon from "./Icon";
import styles from "./Topbar.module.css";

const formatoReloj = new Intl.DateTimeFormat(undefined, { hour: "2-digit", minute: "2-digit" });

function iniciales(nombre?: string) {
  if (!nombre) return "?";
  return nombre
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase())
    .join("");
}

interface Props {
  onMenu: () => void;
}

export default function Topbar({ onMenu }: Props) {
  const { usuario, logout } = useAuthStore();
  const conectado = useOrdersStore((s) => s.conectado);
  const navigate = useNavigate();
  const tema = useTemaStore((s) => s.tema);
  const alternarTema = useTemaStore((s) => s.alternar);

  // La hora se actualiza cada 15 s: basta para ver minutos sin recargar el componente a cada segundo.
  const [ahora, setAhora] = useState(() => new Date());
  useEffect(() => {
    const intervalo = setInterval(() => setAhora(new Date()), 15000);
    return () => clearInterval(intervalo);
  }, []);

  const salir = () => {
    logout();
    navigate("/login", { replace: true });
  };

  return (
    <header className={styles.topbar}>
      <button className={`btn btn-ghost btn-icon ${styles.menu}`} onClick={onMenu} aria-label="Abrir menú">
        <Icon name="menu" size={20} />
      </button>

      <div className={styles.derecha}>
        {/* Reloj de cocina, como el del KDS de la marca */}
        <time className={styles.reloj} dateTime={ahora.toISOString()}>
          <Icon name="reloj" size={14} />
          {formatoReloj.format(ahora)}
        </time>

        <span
          className={`${styles.enVivo} ${conectado ? styles.conectado : ""}`}
          title={conectado ? "Recibiendo pedidos en tiempo real" : "Reconectando…"}
          role="status"
        >
          <span className={styles.punto} />
          <span className={styles.enVivoTexto}>{conectado ? "En vivo" : "Reconectando"}</span>
        </span>

        <button
          type="button"
          className={`btn btn-ghost btn-icon ${styles.tema}`}
          onClick={alternarTema}
          aria-pressed={tema === "oscuro"}
          aria-label="Modo oscuro de cocina"
          title={tema === "oscuro" ? "Volver al modo claro" : "Modo oscuro de cocina"}
        >
          <Icon name={tema === "oscuro" ? "sol" : "luna"} size={18} />
        </button>

        <div className={styles.usuario}>
          <div className={styles.avatar}>{iniciales(usuario?.nombre)}</div>
          <div className={styles.usuarioDatos}>
            <span className={styles.nombre}>{usuario?.nombre}</span>
            <span className={styles.rol}>{usuario?.rol}</span>
          </div>
        </div>

        <button className="btn btn-secondary btn-sm" onClick={salir} title="Cerrar sesión" aria-label="Cerrar sesión">
          <Icon name="salir" size={16} />
          <span className={styles.salirTexto}>Cerrar sesión</span>
        </button>
      </div>
    </header>
  );
}
