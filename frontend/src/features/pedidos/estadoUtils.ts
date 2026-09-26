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

// Identidad visual de cada canal de venta (nombre legible + color de marca).
const CANALES: Record<string, { nombre: string; color: string }> = {
  UBER_EATS: { nombre: "Uber Eats", color: "#06C167" },
  RAPPI: { nombre: "Rappi", color: "#FF441F" },
  PEDIDOS_YA: { nombre: "PedidosYa", color: "#EA004B" },
  PEDIDOSYA: { nombre: "PedidosYa", color: "#EA004B" },
  WHATSAPP: { nombre: "WhatsApp", color: "#25D366" },
  LOCAL: { nombre: "Local", color: "#64748b" },
};

export function infoCanal(origen: string): { nombre: string; color: string } {
  return CANALES[origen] ?? { nombre: origen.replace(/_/g, " "), color: "#64748b" };
}

export function minutosTranscurridos(fechaCreacion: string): number {
  const creado = new Date(fechaCreacion).getTime();
  return Math.floor((Date.now() - creado) / 60000);
}
