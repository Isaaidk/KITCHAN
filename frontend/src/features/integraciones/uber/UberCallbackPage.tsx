import { useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { httpClient } from "../../../shared/api/httpClient";
import {
  EstadoPaso,
  PasoProvisioning,
  useUberProvisioning,
} from "./useUberProvisioning";
import styles from "./UberCallbackPage.module.css";

const ETIQUETAS: Record<PasoProvisioning, string> = {
  app_token: "Generando token de aplicación",
  provision: "Provisionando tienda en Uber Eats",
  menu_upload: "Subiendo menú",
};

const ICONO: Record<EstadoPaso, string> = {
  pendiente: "•",
  en_curso: "…",
  hecho: "✓",
  error: "✕",
};

export default function UberCallbackPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();

  const restauranteId = params.get("restaurante_id") ?? "";
  const statusCallback = params.get("status");
  const [storeId, setStoreId] = useState<string | null>(params.get("store_id"));
  const [buscandoTienda, setBuscandoTienda] = useState(!params.get("store_id"));
  const yaEjecutadoRef = useRef(false);

  const { estado, ejecutando, ejecutarSecuencia, reintentarPaso } = useUberProvisioning(
    restauranteId,
    storeId,
  );

  useEffect(() => {
    if (storeId || statusCallback !== "success") {
      setBuscandoTienda(false);
      return;
    }
    // El callback no devolvió store_id (0 o varias tiendas mapeadas):
    // buscamos la tienda vinculada (1 restaurante = 1 tienda, confirmado).
    httpClient
      .get("/api/v1/integraciones/uber/auth/stores", { params: { restaurante_id: restauranteId } })
      .then(({ data }) => {
        const stores = data?.stores?.stores ?? data?.stores ?? [];
        if (Array.isArray(stores) && stores.length > 0) {
          setStoreId(stores[0].store_id);
        }
      })
      .finally(() => setBuscandoTienda(false));
  }, [restauranteId, statusCallback, storeId]);

  useEffect(() => {
    // Guarda contra el doble-montaje de React StrictMode en desarrollo:
    // sin esto, app-token/provision/menu-upload se disparan dos veces.
    if (yaEjecutadoRef.current) return;
    if (statusCallback === "success" && storeId && !buscandoTienda) {
      yaEjecutadoRef.current = true;
      ejecutarSecuencia();
    }
    // Se ejecuta una sola vez cuando ya tenemos store_id resuelto.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusCallback, storeId, buscandoTienda]);

  const todoListo = estado.app_token === "hecho" && estado.provision === "hecho" && estado.menu_upload === "hecho";

  return (
    <div className={styles.pantalla}>
      <div className={styles.titulo}>Conectando Uber Eats</div>

      {statusCallback === "error" && (
        <div className={styles.errorGlobal}>
          Uber rechazó la autorización. Intenta conectar la tienda nuevamente desde
          Integraciones.
        </div>
      )}

      {statusCallback === "success" && buscandoTienda && <div>Buscando tienda vinculada...</div>}

      {statusCallback === "success" && !buscandoTienda && !storeId && (
        <div className={styles.errorGlobal}>
          No se encontró ninguna tienda vinculada para este restaurante.
        </div>
      )}

      {statusCallback === "success" && storeId && (
        <>
          {(["app_token", "provision", "menu_upload"] as PasoProvisioning[]).map((paso) => (
            <div key={paso} className={styles.paso}>
              <span className={`${styles.icono} ${styles[camel(estado[paso])]}`}>
                {ICONO[estado[paso]]}
              </span>
              <span className={styles.etiqueta}>{ETIQUETAS[paso]}</span>
              {estado[paso] === "error" && (
                <button className={styles.reintentar} onClick={() => reintentarPaso(paso)}>
                  Reintentar
                </button>
              )}
            </div>
          ))}

          {todoListo && (
            <button className={styles.continuar} onClick={() => navigate("/integraciones")}>
              Listo, ir a Integraciones
            </button>
          )}
          {ejecutando && <p>Procesando...</p>}
        </>
      )}
    </div>
  );
}

function camel(estado: EstadoPaso): "pendiente" | "enCurso" | "hecho" | "error" {
  return estado === "en_curso" ? "enCurso" : estado;
}
