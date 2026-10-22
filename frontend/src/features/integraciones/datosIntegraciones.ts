import { useCallback, useEffect, useState } from "react";
import { httpClient } from "../../shared/api/httpClient";

export interface ActividadCanal {
  canal: string;
  pedidos_hoy: number;
  pedidos_30d: number;
  ultimo_pedido: string | null;
}

/**
 * Actividad de cada canal (pedidos de hoy y último pedido). Devuelve `null` mientras
 * carga y un mapa vacío si falla: la pantalla sigue siendo útil sin estas cifras.
 */
export function useActividadCanales() {
  const [actividad, setActividad] = useState<Record<string, ActividadCanal> | null>(null);

  const cargar = useCallback(() => {
    httpClient
      .get<ActividadCanal[]>("/api/v1/reportes/canales/actividad")
      .then(({ data }) => setActividad(Object.fromEntries(data.map((c) => [c.canal, c]))))
      .catch(() => setActividad({}));
  }, []);

  useEffect(cargar, [cargar]);
  return { actividad, recargar: cargar };
}
