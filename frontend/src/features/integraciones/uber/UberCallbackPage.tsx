import { useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { httpClient } from "../../../shared/api/httpClient";
import Icon from "../../../shared/components/Icon";
import { LogoCanal } from "../IntegracionesPage";
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
      <div className={styles.cabecera}>
        <LogoCanal canal="UBER_EATS" />
        <div>
          <div className={styles.titulo}>Conectando Uber Eats</div>
          <div className={styles.subtitulo}>Configurando tu tienda, no cierres esta ventana.</div>
        </div>
      </div>

      {statusCallback === "error" && (
        <div className="alert alert-error">
          <Icon name="alerta" size={16} />
          Uber rechazó la autorización. Intenta conectar la tienda nuevamente desde Integraciones.
        </div>
      )}

      {statusCallback === "success" && buscandoTienda && (
        <div className={styles.buscando}>
          <span className="spinner" />
          Buscando tienda vinculada...
        </div>
      )}

      {statusCallback === "success" && !buscandoTienda && !storeId && (
        <div className="alert alert-error">
          <Icon name="alerta" size={16} />
          No se encontró ninguna tienda vinculada para este restaurante.
        </div>
      )}

      {statusCallback === "success" && storeId && (
        <>
          <div className={styles.pasos}>
            {(["app_token", "provision", "menu_upload"] as PasoProvisioning[]).map((paso, i) => (
              <div key={paso} className={`${styles.paso} animate-in`} style={{ ["--i" as string]: i }}>
                <span className={`${styles.icono} ${styles[camel(estado[paso])]}`}>
                  <IconoPaso estado={estado[paso]} numero={i + 1} />
                </span>
                <span className={styles.etiqueta}>{ETIQUETAS[paso]}</span>
                {estado[paso] === "error" && (
                  <button className="btn btn-secondary btn-sm" onClick={() => reintentarPaso(paso)}>
                    <Icon name="sync" size={14} />
                    Reintentar
                  </button>
                )}
              </div>
            ))}
          </div>

          {todoListo && (
            <button className="btn btn-success btn-block animate-scale" onClick={() => navigate("/integraciones")}>
              <Icon name="check" size={16} strokeWidth={2.5} />
              Listo, ir a Integraciones
            </button>
          )}
          {ejecutando && (
            <p className={styles.procesando}>
              <span className="spinner" style={{ width: 14, height: 14 }} />
              Procesando...
            </p>
          )}
        </>
      )}
    </div>
  );
}

function IconoPaso({ estado, numero }: { estado: EstadoPaso; numero: number }) {
  if (estado === "hecho") return <Icon name="check" size={14} strokeWidth={3} />;
  if (estado === "error") return <Icon name="cerrar" size={14} strokeWidth={3} />;
  if (estado === "en_curso") return <span className={styles.giro} />;
  return <>{numero}</>;
}

function camel(estado: EstadoPaso): "pendiente" | "enCurso" | "hecho" | "error" {
  return estado === "en_curso" ? "enCurso" : estado;
}
