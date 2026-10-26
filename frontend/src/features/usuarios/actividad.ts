import { useEffect, useState } from "react";
import { httpClient } from "../../shared/api/httpClient";
import type { Rango } from "../analiticas/types";

export interface ResumenActividad {
  pedidos_atendidos: number;
  pedidos_cancelados: number;
  ventas: number;
  tiempo_promedio_minutos: number;
  tasa_demora: number;
  ultima_actividad: string | null;
}

export interface ActividadUsuario extends ResumenActividad {
  usuario_id: string;
}

export interface DetalleActividad extends ActividadUsuario {
  por_canal: { canal: string; pedidos: number }[];
  recientes: {
    canal: string;
    cliente: string;
    total: number;
    estado: string;
    fecha: string;
    minutos_preparacion: number | null;
  }[];
}

export interface RespuestaActividad {
  rango: Rango;
  desde: string;
  hasta: string;
  /** Pedidos aceptados cuyo usuario no quedó registrado (anteriores o del sistema). */
  sin_atribuir: number;
  usuarios: ActividadUsuario[];
  detalle: DetalleActividad | null;
}

/**
 * Actividad del personal. Sin `usuarioId` trae el resumen de todos; con él, además
 * el detalle de esa persona. Si falla, devuelve `error` y la pantalla sigue sin
 * las cifras de actividad (no es crítica para administrar usuarios).
 */
export function useActividad(rango: Rango, usuarioId?: string) {
  const [datos, setDatos] = useState<RespuestaActividad | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let vigente = true;
    setError(false);
    const ruta = usuarioId
      ? `/api/v1/reportes/usuarios/${usuarioId}/actividad`
      : "/api/v1/reportes/usuarios/actividad";
    httpClient
      .get<RespuestaActividad>(ruta, { params: { rango } })
      .then(({ data }) => vigente && setDatos(data))
      .catch(() => {
        if (!vigente) return;
        setDatos(null);
        setError(true);
      });
    return () => {
      vigente = false;
    };
  }, [rango, usuarioId]);

  return { datos, error, cargando: !datos && !error };
}
