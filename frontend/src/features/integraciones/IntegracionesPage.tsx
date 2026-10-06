import { useEffect, useState } from "react";
import { API_URL, httpClient } from "../../shared/api/httpClient";
import CanalLogo from "../../shared/components/CanalLogo";
import Icon from "../../shared/components/Icon";
import { useAuthStore } from "../../shared/stores/authStore";
import { infoCanal } from "../pedidos/estadoUtils";
import OdooCard from "./OdooCard";
import styles from "./IntegracionesPage.module.css";

const CANALES_PROXIMAMENTE = ["PEDIDOSYA", "WHATSAPP"];

const DESCRIPCION: Record<string, string> = {
  UBER_EATS: "Recibe y gestiona los pedidos de tu tienda de Uber Eats.",
  RAPPI:
    "Recibe pedidos de Rappi y acéptalos, recházalos o márcalos listos desde la cola. Las credenciales las configura el equipo técnico.",
  PEDIDOSYA: "Integración POS con el Middleware de PedidosYa.",
  WHATSAPP: "Pedidos directos desde WhatsApp Business.",
};

/** Logo del canal con su color de marca. */
export function LogoCanal({ canal }: { canal: string }) {
  const { nombre, color } = infoCanal(canal);
  return <CanalLogo className={styles.logo} canal={canal} color={color} nombre={nombre} size={44} />;
}

export default function IntegracionesPage() {
  const restauranteId = useAuthStore((s) => s.usuario?.restaurante_id);
  const [uberConectado, setUberConectado] = useState<boolean | null>(null);

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

  return (
    <div className={styles.pagina}>
      <div className="page-header">
        <div>
          <h1 className="page-title">Integraciones</h1>
          <p className="page-subtitle">Conecta tus canales de venta y sistemas externos.</p>
        </div>
      </div>

      <section className={styles.seccion} aria-labelledby="int-canales">
        <h2 id="int-canales" className={styles.seccionTitulo}>
          Canales de venta <span className={styles.seccionCuenta}>2</span>
        </h2>
        <div className={styles.lista}>
          <div className={`${styles.fila} animate-in`}>
            <LogoCanal canal="UBER_EATS" />
            <div className={styles.texto}>
              <div className={styles.canal}>Uber Eats</div>
              <p className={styles.descripcion}>{DESCRIPCION.UBER_EATS}</p>
            </div>
            {uberConectado === null ? (
              <>
                <span className={`skeleton ${styles.estadoSkeleton}`} aria-hidden="true" />
                <span className="sr-only" role="status">
                  Verificando conexión…
                </span>
              </>
            ) : (
              <span className={`${styles.estado} ${uberConectado ? styles.estadoOk : ""}`} role="status">
                {uberConectado ? "Conectado" : "No conectado"}
              </span>
            )}
            <div className={styles.accion}>
              {uberConectado === false && (
                <a className="btn btn-primary btn-sm" href={urlConectarUber}>
                  Conectar Uber Eats
                  <Icon name="flecha" size={14} />
                </a>
              )}
            </div>
          </div>

          {/* Rappi usa client-credentials configuradas en el backend (.env),
              no un flujo OAuth por restaurante como Uber: no hay botón de conectar. */}
          <div className={`${styles.fila} animate-in`} style={{ ["--i" as string]: 1 }}>
            <LogoCanal canal="RAPPI" />
            <div className={styles.texto}>
              <div className={styles.canal}>Rappi</div>
              <p className={styles.descripcion}>{DESCRIPCION.RAPPI}</p>
            </div>
            <span className={`${styles.estado} ${styles.estadoInfo}`}>Disponible</span>
            <div className={styles.accion}>
              <span className={styles.nota}>Lo configura el equipo técnico</span>
            </div>
          </div>
        </div>
      </section>

      <section className={styles.seccion} aria-labelledby="int-sistemas">
        <h2 id="int-sistemas" className={styles.seccionTitulo}>
          Sistemas externos <span className={styles.seccionCuenta}>1</span>
        </h2>
        <div className={styles.lista}>
          <OdooCard />
        </div>
      </section>

      <section className={styles.seccion} aria-labelledby="int-pronto">
        <h2 id="int-pronto" className={styles.seccionTitulo}>
          Próximamente <span className={styles.seccionCuenta}>{CANALES_PROXIMAMENTE.length}</span>
        </h2>
        <div className={styles.lista}>
          {CANALES_PROXIMAMENTE.map((canal, i) => (
            <div
              key={canal}
              className={`${styles.fila} ${styles.filaInactiva} animate-in`}
              style={{ ["--i" as string]: i + 2 }}
            >
              <LogoCanal canal={canal} />
              <div className={styles.texto}>
                <div className={styles.canal}>{infoCanal(canal).nombre}</div>
                <p className={styles.descripcion}>{DESCRIPCION[canal]}</p>
              </div>
              <span className={styles.estado}>En desarrollo</span>
              <div className={styles.accion} />
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
