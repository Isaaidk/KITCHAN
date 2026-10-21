import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { httpClient } from "../../shared/api/httpClient";
import type { DashboardPedidos, Rango } from "./types";

export const RANGOS: { valor: Rango; etiqueta: string; descripcion: string }[] = [
  { valor: "hoy", etiqueta: "Hoy", descripcion: "hoy" },
  { valor: "7d", etiqueta: "7 días", descripcion: "los últimos 7 días" },
  { valor: "30d", etiqueta: "30 días", descripcion: "los últimos 30 días" },
];

/** El rango vive en la URL (?rango=7d): se puede compartir y recargar. */
export function useRango(): [Rango, (rango: Rango) => void] {
  const [params, setParams] = useSearchParams();
  const param = params.get("rango");
  const rango: Rango = RANGOS.some((r) => r.valor === param) ? (param as Rango) : "hoy";

  const cambiar = (nuevo: Rango) =>
    setParams(
      (previos) => {
        const nuevos = new URLSearchParams(previos);
        if (nuevo === "hoy") nuevos.delete("rango");
        else nuevos.set("rango", nuevo);
        return nuevos;
      },
      { replace: true },
    );

  return [rango, cambiar];
}

/** Carga el dashboard del rango pedido; conserva los datos anteriores mientras llegan los nuevos. */
export function useDashboard(rango: Rango) {
  const [datos, setDatos] = useState<DashboardPedidos | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(false);
  // Se incrementa para volver a pedir los datos tras un error.
  const [intento, setIntento] = useState(0);

  useEffect(() => {
    // `vigente` descarta respuestas de un rango que ya fue reemplazado.
    let vigente = true;
    setCargando(true);
    setError(false);
    httpClient
      .get<DashboardPedidos>("/api/v1/reportes/pedidos/dashboard", { params: { rango } })
      .then(({ data }) => {
        if (vigente) setDatos(data);
      })
      .catch(() => {
        if (!vigente) return;
        setDatos(null);
        setError(true);
      })
      .finally(() => {
        if (vigente) setCargando(false);
      });
    return () => {
      vigente = false;
    };
  }, [rango, intento]);

  return { datos, cargando, error, reintentar: () => setIntento((n) => n + 1) };
}
