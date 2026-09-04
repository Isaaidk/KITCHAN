import { useEffect, useState } from "react";
import { API_URL, httpClient } from "../../shared/api/httpClient";
import { useAuthStore } from "../../shared/stores/authStore";
import OdooCard from "./OdooCard";
import styles from "./IntegracionesPage.module.css";

const CANALES_PROXIMAMENTE = ["RAPPI", "PEDIDOSYA", "WHATSAPP"];

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
      <h2>Integraciones</h2>
      <div className={styles.grid} style={{ marginTop: 20 }}>
        <div className={styles.tarjeta}>
          <div className={styles.canal}>UBER EATS</div>
          <div className={`${styles.estado} ${uberConectado ? styles.conectado : styles.desconectado}`}>
            {uberConectado === null && "Verificando..."}
            {uberConectado === true && "Conectado"}
            {uberConectado === false && "No conectado"}
          </div>
          <button className={styles.boton} onClick={conectarUber} disabled={uberConectado === true}>
            {uberConectado ? "Conectado" : "Conectar Uber Eats"}
          </button>
        </div>

        {CANALES_PROXIMAMENTE.map((canal) => (
          <div key={canal} className={styles.tarjeta}>
            <div className={styles.canal}>{canal}</div>
            <div className={`${styles.estado} ${styles.desconectado}`}>Próximamente</div>
            <button className={styles.boton} disabled>
              No disponible
            </button>
          </div>
        ))}

        <OdooCard />
      </div>
    </div>
  );
}
