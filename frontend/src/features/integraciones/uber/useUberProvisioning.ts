import { useCallback, useState } from "react";
import { httpClient } from "../../../shared/api/httpClient";

export type PasoProvisioning = "app_token" | "provision" | "menu_upload";
export type EstadoPaso = "pendiente" | "en_curso" | "hecho" | "error";

export interface EstadoProvisioning {
  app_token: EstadoPaso;
  provision: EstadoPaso;
  menu_upload: EstadoPaso;
}

export const PASOS: PasoProvisioning[] = ["app_token", "provision", "menu_upload"];

const ESTADO_INICIAL: EstadoProvisioning = {
  app_token: "pendiente",
  provision: "pendiente",
  menu_upload: "pendiente",
};

/**
 * Orquesta secuencialmente app-token -> provision -> menu/upload. Cada paso
 * reporta su propio error y se puede reintentar individualmente sin
 * reiniciar todo el flujo.
 */
export function useUberProvisioning(restauranteId: string, storeId: string | null) {
  const [estado, setEstado] = useState<EstadoProvisioning>(ESTADO_INICIAL);
  const [ejecutando, setEjecutando] = useState(false);

  const ejecutarPaso = useCallback(
    async (paso: PasoProvisioning) => {
      setEstado((s) => ({ ...s, [paso]: "en_curso" }));
      try {
        if (paso === "app_token") {
          await httpClient.post("/api/v1/integraciones/uber/auth/app-token", null, {
            params: { restaurante_id: restauranteId },
          });
        } else if (paso === "provision") {
          if (!storeId) throw new Error("Falta store_id");
          await httpClient.post("/api/v1/integraciones/uber/auth/provision", {
            restaurante_id: restauranteId,
            store_id: storeId,
          });
        } else if (paso === "menu_upload") {
          if (!storeId) throw new Error("Falta store_id");
          await httpClient.put(
            `/api/v1/integraciones/uber/auth/menu/upload/${storeId}`,
            null,
            { params: { restaurante_id: restauranteId } },
          );
        }
        setEstado((s) => ({ ...s, [paso]: "hecho" }));
        return true;
      } catch {
        setEstado((s) => ({ ...s, [paso]: "error" }));
        return false;
      }
    },
    [restauranteId, storeId],
  );

  // Ejecuta `desde` y los pasos que le siguen; se detiene en el primer error.
  const ejecutarDesde = useCallback(
    async (desde: PasoProvisioning) => {
      setEjecutando(true);
      for (const paso of PASOS.slice(PASOS.indexOf(desde))) {
        const ok = await ejecutarPaso(paso);
        if (!ok) break;
      }
      setEjecutando(false);
    },
    [ejecutarPaso],
  );

  const ejecutarSecuencia = useCallback(() => ejecutarDesde("app_token"), [ejecutarDesde]);

  // Reintentar un paso que falló continúa con los siguientes: si no, el flujo
  // quedaría a medias aunque el reintento funcione.
  return { estado, ejecutando, ejecutarSecuencia, reintentarPaso: ejecutarDesde };
}
