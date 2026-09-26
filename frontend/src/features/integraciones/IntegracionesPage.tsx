import { useEffect, useState } from "react";
import { API_URL, httpClient } from "../../shared/api/httpClient";
import Icon from "../../shared/components/Icon";
import { useAuthStore } from "../../shared/stores/authStore";
import { infoCanal } from "../pedidos/estadoUtils";
import OdooCard from "./OdooCard";
import styles from "./IntegracionesPage.module.css";

const CANALES_PROXIMAMENTE = ["RAPPI", "PEDIDOSYA", "WHATSAPP"];

const DESCRIPCION: Record<string, string> = {
  UBER_EATS: "Recibe y gestiona los pedidos de tu tienda de Uber Eats.",
  RAPPI: "Integración con la API de Restaurantes de Rappi.",
  PEDIDOSYA: "Integración POS con el Middleware de PedidosYa.",
  WHATSAPP: "Pedidos directos desde WhatsApp Business.",
};

/** Logo tipográfico con el color de marca del canal. */
export function LogoCanal({ canal }: { canal: string }) {
  const { nombre, color } = infoCanal(canal);
  return (
    <div className={styles.logo} style={{ ["--c" as string]: color }}>
      {nombre.charAt(0)}
    </div>
  );
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

  const conectarUber = () => {
    window.location.href = `${API_URL}/api/v1/integraciones/uber/auth/login?restaurante_id=${restauranteId}`;
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Integraciones</h1>
          <p className="page-subtitle">Conecta tus canales de venta y sistemas externos.</p>
        </div>
      </div>

      <div className={styles.grid}>
        <div className={`${styles.tarjeta} ${uberConectado ? styles.tarjetaActiva : ""} animate-in`}>
          <div className={styles.cabecera}>
            <LogoCanal canal="UBER_EATS" />
            <span
              className="badge badge-dot"
              style={{
                ["--badge-color" as string]:
                  uberConectado === true ? "#16a34a" : uberConectado === false ? "#64748b" : "#d97706",
              }}
            >
              {uberConectado === null && "Verificando..."}
              {uberConectado === true && "Conectado"}
              {uberConectado === false && "No conectado"}
            </span>
          </div>
          <div className={styles.canal}>Uber Eats</div>
          <p className={styles.descripcion}>{DESCRIPCION.UBER_EATS}</p>
          <button
            className={`btn btn-block ${uberConectado ? "btn-secondary" : "btn-primary"}`}
            onClick={conectarUber}
            disabled={uberConectado === true}
          >
            {uberConectado ? (
              <>
                <Icon name="check" size={16} strokeWidth={2.5} />
                Conectado
              </>
            ) : (
              <>
                Conectar Uber Eats
                <Icon name="flecha" size={16} />
              </>
            )}
          </button>
        </div>

        {CANALES_PROXIMAMENTE.map((canal, i) => (
          <div
            key={canal}
            className={`${styles.tarjeta} ${styles.tarjetaInactiva} animate-in`}
            style={{ ["--i" as string]: i + 1 }}
          >
            <div className={styles.cabecera}>
              <LogoCanal canal={canal} />
              <span className="badge">Próximamente</span>
            </div>
            <div className={styles.canal}>{infoCanal(canal).nombre}</div>
            <p className={styles.descripcion}>{DESCRIPCION[canal]}</p>
            <button className="btn btn-secondary btn-block" disabled>
              No disponible
            </button>
          </div>
        ))}

        <OdooCard />
      </div>
    </div>
  );
}
