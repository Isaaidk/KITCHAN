import { useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { httpClient } from "../../../shared/api/httpClient";
import Icon from "../../../shared/components/Icon";
import { LogoCanal } from "../IntegracionesPage";
import {
  EstadoPaso,
  PASOS,
  PasoProvisioning,
  useUberProvisioning,
} from "./useUberProvisioning";
import styles from "./UberCallbackPage.module.css";

// Texto de cada paso según su estado: pendiente / en curso / hecho / error.
const ETIQUETAS: Record<PasoProvisioning, Record<EstadoPaso, string>> = {
  app_token: {
    pendiente: "Generar token de aplicación",
    en_curso: "Generando token de aplicación…",
    hecho: "Token de aplicación generado",
    error: "No se pudo generar el token de aplicación",
  },
  provision: {
    pendiente: "Provisionar tienda en Uber Eats",
    en_curso: "Provisionando tienda en Uber Eats…",
    hecho: "Tienda provisionada en Uber Eats",
    error: "No se pudo provisionar la tienda",
  },
  menu_upload: {
    pendiente: "Subir menú",
    en_curso: "Subiendo menú…",
    hecho: "Menú subido",
    error: "No se pudo subir el menú",
  },
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

  const hechos = PASOS.filter((p) => estado[p] === "hecho").length;
  const todoListo = hechos === PASOS.length;
  const hayError = PASOS.some((p) => estado[p] === "error");
  const sinTienda = statusCallback === "success" && !buscandoTienda && !storeId;
  const fallaInicial = statusCallback === "error" || sinTienda || (statusCallback !== "success" && statusCallback !== "error");

  const volver = () => navigate("/integraciones");

  let titulo = "Conectando Uber Eats";
  let subtitulo = "Configurando tu tienda. No cierres esta ventana.";
  if (todoListo) {
    titulo = "Uber Eats conectado";
    subtitulo = "Tu tienda quedó vinculada y el menú está sincronizado.";
  } else if (fallaInicial) {
    titulo = "No se pudo conectar Uber Eats";
    subtitulo = "La conexión no se completó.";
  } else if (hayError && !ejecutando) {
    titulo = "La conexión quedó incompleta";
    subtitulo = "Un paso falló. Puedes reintentarlo sin repetir los anteriores.";
  }

  return (
    <div className={styles.pantalla}>
      <div className={styles.cabecera}>
        <LogoCanal canal="UBER_EATS" />
        <div aria-live="polite">
          <div className={styles.titulo}>{titulo}</div>
          <div className={styles.subtitulo}>{subtitulo}</div>
        </div>
      </div>

      {statusCallback === "error" && (
        <div className="alert alert-error" role="alert">
          <Icon name="alerta" size={16} />
          Uber rechazó la autorización. Intenta conectar la tienda nuevamente desde Integraciones.
        </div>
      )}

      {statusCallback !== "success" && statusCallback !== "error" && (
        <div className="alert alert-warning" role="alert">
          <Icon name="alerta" size={16} />
          No recibimos una respuesta de Uber. Vuelve a Integraciones e inicia la conexión de nuevo.
        </div>
      )}

      {statusCallback === "success" && buscandoTienda && (
        <div className={styles.buscando}>
          <span className="spinner" />
          Buscando tienda vinculada…
        </div>
      )}

      {sinTienda && (
        <div className="alert alert-error" role="alert">
          <Icon name="alerta" size={16} />
          No se encontró ninguna tienda vinculada para este restaurante.
        </div>
      )}

      {statusCallback === "success" && storeId && (
        <>
          <div className={styles.progreso} aria-hidden="true">
            <div className={styles.progresoBarra} style={{ width: `${(hechos / PASOS.length) * 100}%` }} />
          </div>
          <div className={styles.progresoTexto}>
            {hechos} de {PASOS.length} pasos completados
          </div>

          <ol className={styles.pasos}>
            {PASOS.map((paso, i) => (
              <li
                key={paso}
                className={`${styles.paso} ${estado[paso] === "pendiente" ? styles.pasoPendiente : ""} animate-in`}
                style={{ ["--i" as string]: i }}
              >
                <span className={`${styles.icono} ${styles[camel(estado[paso])]}`}>
                  <IconoPaso estado={estado[paso]} numero={i + 1} />
                </span>
                <span className={`${styles.etiqueta} ${estado[paso] === "error" ? styles.etiquetaError : ""}`}>
                  {ETIQUETAS[paso][estado[paso]]}
                </span>
                {estado[paso] === "error" && (
                  <button
                    className="btn btn-secondary btn-sm"
                    onClick={() => reintentarPaso(paso)}
                    disabled={ejecutando}
                  >
                    <Icon name="sync" size={14} />
                    Reintentar
                  </button>
                )}
              </li>
            ))}
          </ol>
        </>
      )}

      <div className={styles.acciones}>
        {todoListo ? (
          <button className="btn btn-success btn-block animate-scale" onClick={volver}>
            <Icon name="check" size={16} strokeWidth={2.5} />
            Listo, ir a Integraciones
          </button>
        ) : (
          (fallaInicial || (hayError && !ejecutando)) && (
            <button className="btn btn-secondary btn-block" onClick={volver}>
              <Icon name="flecha" size={14} style={{ transform: "rotate(180deg)" }} />
              Volver a Integraciones
            </button>
          )
        )}
      </div>
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
