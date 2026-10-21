import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuthStore } from "../stores/authStore";
import { useOrdersStore } from "../stores/ordersStore";
import Icon from "./Icon";
import styles from "./Topbar.module.css";

const formatoReloj = new Intl.DateTimeFormat(undefined, { hour: "2-digit", minute: "2-digit" });

const TITULOS: Array<[string, string]> = [
  ["/integraciones", "Integraciones"],
  ["/analiticas", "Analíticas"],
  ["/usuarios", "Usuarios"],
  ["/historial", "Historial"],
  ["/cola", "Cola de pedidos"],
  ["/", "Dashboard"],
];

function tituloPara(pathname: string) {
  return TITULOS.find(([ruta]) => (ruta === "/" ? pathname === "/" : pathname.startsWith(ruta)))?.[1] ?? "";
}

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
  const { pathname } = useLocation();

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

      <nav className={styles.migas} aria-label="Ubicación">
        <span className={styles.migaRaiz}>KITCHAN</span>
        <span className={styles.separador}>/</span>
        <span className={styles.titulo} key={pathname}>
          {tituloPara(pathname)}
        </span>
      </nav>

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
