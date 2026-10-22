import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { API_URL, httpClient } from "../../shared/api/httpClient";
import CanalLogo from "../../shared/components/CanalLogo";
import Icon from "../../shared/components/Icon";
import Ilustracion from "../../shared/components/Ilustracion";
import { useAuthStore } from "../../shared/stores/authStore";
import { hace, numero } from "../../shared/utils/formato";
import { CANALES_ANALITICAS } from "../analiticas/canales";
import { infoCanal } from "../pedidos/estadoUtils";
import { useActividadCanales, type ActividadCanal } from "./datosIntegraciones";
import OdooCard from "./OdooCard";
import styles from "./IntegracionesPage.module.css";

const DESCRIPCION: Record<string, string> = {
  UBER_EATS: "Recibe y gestiona los pedidos de tu tienda de Uber Eats.",
  RAPPI: "Recibe pedidos de Rappi y acéptalos, recházalos o márcalos listos desde la cola.",
  PEDIDOS_YA: "Recibe pedidos de PedidosYa y acéptalos, recházalos, cancélalos o márcalos listos desde la cola.",
  WHATSAPP: "Pedidos directos desde WhatsApp Business.",
};

// Canales de venta que ya reciben pedidos, en el orden en que se muestran.
const CANALES_ACTIVOS = ["UBER_EATS", "RAPPI", "PEDIDOS_YA"] as const;

/** Logo del canal con su color de marca. */
export function LogoCanal({ canal, tamano = 44 }: { canal: string; tamano?: number }) {
  const { nombre, color } = infoCanal(canal);
  return <CanalLogo className={styles.logo} canal={canal} color={color} nombre={nombre} size={tamano} />;
}

function enlaceAnaliticas(canal: string) {
  const slug = CANALES_ANALITICAS.find((c) => c.codigo === canal)?.slug;
  return slug ? `/analiticas/${slug}` : "/analiticas";
}

interface EstadoCanal {
  etiqueta: string;
  tono: "ok" | "info" | "alerta" | "cargando";
}

function ResumenCanales({
  actividad,
  uberConectado,
}: {
  actividad: Record<string, ActividadCanal> | null;
  uberConectado: boolean | null;
}) {
  if (!actividad) {
    return (
      <div className={styles.resumen} aria-busy="true">
        <div className="skeleton" style={{ height: 18, width: "40%", marginBottom: 14 }} />
        <div className="skeleton" style={{ height: 36 }} />
      </div>
    );
  }

  const conPedidos = CANALES_ACTIVOS.filter((c) => (actividad[c]?.pedidos_hoy ?? 0) > 0);
  const ultimo = CANALES_ACTIVOS.map((c) => actividad[c])
    .filter((a): a is ActividadCanal => !!a?.ultimo_pedido)
    .sort((a, b) => b.ultimo_pedido!.localeCompare(a.ultimo_pedido!))[0];

  return (
    <section className={styles.resumen} aria-labelledby="int-resumen">
      <div className={styles.resumenTexto}>
        <h2 id="int-resumen" className={styles.resumenTitulo}>
          <span className={styles.resumenNumero}>{conPedidos.length}</span> de {CANALES_ACTIVOS.length} canales
          recibieron pedidos hoy
        </h2>
        <p className={styles.resumenSub}>
          {ultimo
            ? `El último pedido fue de ${infoCanal(ultimo.canal).nombre}, ${hace(ultimo.ultimo_pedido!)}.`
            : "Todavía no hay pedidos registrados en los últimos 30 días."}
        </p>
      </div>
      <ul className={styles.chips}>
        {CANALES_ACTIVOS.map((canal) => {
          const hoy = actividad[canal]?.pedidos_hoy ?? 0;
          const desconectado = canal === "UBER_EATS" && uberConectado === false;
          return (
            <li key={canal} className={styles.chip}>
              <LogoCanal canal={canal} tamano={28} />
              <span className={styles.chipTexto}>
                <span className={styles.chipNombre}>{infoCanal(canal).nombre}</span>
                <span className={desconectado ? styles.chipAlerta : styles.chipDato}>
                  {desconectado ? "Desconectado" : `${numero(hoy)} ${hoy === 1 ? "pedido" : "pedidos"} hoy`}
                </span>
              </span>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

function TarjetaCanal({
  canal,
  estado,
  actividad,
  accion,
  indice,
}: {
  canal: string;
  estado: EstadoCanal;
  actividad: ActividadCanal | undefined | null;
  accion: React.ReactNode;
  indice: number;
}) {
  const { nombre } = infoCanal(canal);
  const hoy = actividad?.pedidos_hoy ?? 0;
  return (
    <article className={`${styles.tarjeta} animate-in`} style={{ ["--i" as string]: indice }}>
      <header className={styles.tarjetaCabecera}>
        <LogoCanal canal={canal} tamano={52} />
        <div className={styles.tarjetaTitulo}>
          <h3 className={styles.canal}>{nombre}</h3>
          {estado.tono === "cargando" ? (
            <>
              <span className={`skeleton ${styles.estadoSkeleton}`} aria-hidden="true" />
              <span className="sr-only" role="status">
                Verificando conexión…
              </span>
            </>
          ) : (
            <span
              className={`${styles.estado} ${estado.tono === "ok" ? styles.estadoOk : ""} ${estado.tono === "alerta" ? styles.estadoAlerta : ""} ${estado.tono === "info" ? styles.estadoInfo : ""}`}
              role="status"
            >
              {estado.etiqueta}
            </span>
          )}
        </div>
      </header>

      <p className={styles.descripcion}>{DESCRIPCION[canal]}</p>

      <dl className={styles.datos}>
        <div>
          <dt>Pedidos hoy</dt>
          <dd className={styles.cifra}>{actividad === null ? "—" : numero(hoy)}</dd>
        </div>
        <div>
          <dt>Último pedido</dt>
          <dd className={styles.ultimo}>
            {actividad === null ? "—" : actividad?.ultimo_pedido ? hace(actividad.ultimo_pedido) : "Sin pedidos aún"}
          </dd>
        </div>
      </dl>

      <footer className={styles.pie}>
        {accion}
        <Link to={enlaceAnaliticas(canal)} className={styles.enlace}>
          Ver analíticas
          <Icon name="flecha" size={13} />
        </Link>
      </footer>
    </article>
  );
}

export default function IntegracionesPage() {
  const restauranteId = useAuthStore((s) => s.usuario?.restaurante_id);
  const [uberConectado, setUberConectado] = useState<boolean | null>(null);
  const { actividad } = useActividadCanales();

  useEffect(() => {
    if (!restauranteId) return;
    httpClient
      .get("/api/v1/integraciones/uber/auth/stores", { params: { restaurante_id: restauranteId } })
      .then(() => setUberConectado(true))
      .catch(() => setUberConectado(false));
  }, [restauranteId]);

  // Es una navegación (redirección OAuth a Uber), así que va como enlace real:
  // permite abrirla en otra pestaña y la anuncia como enlace, no como botón.
  const urlConectarUber = `${API_URL}/api/v1/integraciones/uber/auth/login?restaurante_id=${restauranteId}`;

  const estadoUber: EstadoCanal =
    uberConectado === null
      ? { etiqueta: "", tono: "cargando" }
      : uberConectado
        ? { etiqueta: "Conectado", tono: "ok" }
        : { etiqueta: "No conectado", tono: "alerta" };
  // Rappi y PedidosYa usan credenciales fijas del servidor, no un flujo de conexión por local.
  const estadoCredenciales: EstadoCanal = { etiqueta: "Disponible", tono: "info" };
  const notaTecnica = <span className={styles.nota}>Lo configura el equipo técnico</span>;

  return (
    <div className={styles.pagina}>
      <div className="page-header">
        <div>
          <h1 className="page-title">Integraciones</h1>
          <p className="page-subtitle">Conecta tus canales de venta y sistemas externos.</p>
        </div>
      </div>

      <ResumenCanales actividad={actividad} uberConectado={uberConectado} />

      <section className={styles.seccion} aria-labelledby="int-canales">
        <h2 id="int-canales" className={styles.seccionTitulo}>
          Canales de venta <span className={styles.seccionCuenta}>{CANALES_ACTIVOS.length}</span>
        </h2>
        <div className={styles.rejilla}>
          <TarjetaCanal
            canal="UBER_EATS"
            indice={0}
            estado={estadoUber}
            actividad={actividad && (actividad.UBER_EATS ?? undefined)}
            accion={
              uberConectado === false ? (
                <a className="btn btn-primary btn-sm" href={urlConectarUber}>
                  Conectar Uber Eats
                  <Icon name="flecha" size={14} />
                </a>
              ) : (
                <span className={styles.nota}>{uberConectado ? "Conexión activa" : ""}</span>
              )
            }
          />
          <TarjetaCanal
            canal="RAPPI"
            indice={1}
            estado={estadoCredenciales}
            actividad={actividad && (actividad.RAPPI ?? undefined)}
            accion={notaTecnica}
          />
          <TarjetaCanal
            canal="PEDIDOS_YA"
            indice={2}
            estado={estadoCredenciales}
            actividad={actividad && (actividad.PEDIDOS_YA ?? undefined)}
            accion={notaTecnica}
          />
        </div>
      </section>

      <section className={styles.seccion} aria-labelledby="int-sistemas">
        <h2 id="int-sistemas" className={styles.seccionTitulo}>
          Facturación electrónica
        </h2>
        <OdooCard />
      </section>

      <section className={styles.seccion} aria-labelledby="int-pronto">
        <h2 id="int-pronto" className={styles.seccionTitulo}>
          Próximamente <span className={styles.seccionCuenta}>1</span>
        </h2>
        <article className={`${styles.pronto} animate-in`}>
          <div className={styles.prontoDibujo}>
            <Ilustracion tipo="taza" ancho={96} />
          </div>
          <div className={styles.prontoTexto}>
            <div className={styles.prontoCabecera}>
              <LogoCanal canal="WHATSAPP" tamano={36} />
              <h3 className={styles.canal}>WhatsApp</h3>
              <span className={styles.estado}>En desarrollo</span>
            </div>
            <p className={styles.descripcion}>{DESCRIPCION.WHATSAPP}</p>
          </div>
        </article>
      </section>
    </div>
  );
}
