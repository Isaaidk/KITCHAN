import type { EstadoPedido } from "../../shared/types/pedido";

export const ESTADOS_ACTIVOS: EstadoPedido[] = ["NUEVA", "EN_PREPARACION", "LISTA"];

export const ETIQUETA_ESTADO: Record<EstadoPedido, string> = {
  NUEVA: "Nueva",
  EN_PREPARACION: "En preparación",
  LISTA: "Lista",
  ENTREGADA: "Entregada",
  CANCELADA: "Cancelada",
};

export function colorVarEstado(estado: EstadoPedido): string {
  switch (estado) {
    case "NUEVA":
      return "var(--color-estado-nueva)";
    case "EN_PREPARACION":
      return "var(--color-estado-en-preparacion)";
    case "LISTA":
      return "var(--color-estado-lista)";
    case "ENTREGADA":
      return "var(--color-estado-entregada)";
    case "CANCELADA":
      return "var(--color-estado-cancelada)";
  }
}

export function minutosTranscurridos(fechaCreacion: string): number {
  const creado = new Date(fechaCreacion).getTime();
  return Math.floor((Date.now() - creado) / 60000);
}
