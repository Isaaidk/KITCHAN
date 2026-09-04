import { httpClient } from "../../shared/api/httpClient";
import type { Pedido } from "../../shared/types/pedido";

// Cada integración maneja sus propios endpoints de accept/ready (arquitectura
// modular confirmada); hoy solo Uber está implementado en el backend.
const BASE_POR_ORIGEN: Record<string, string> = {
  UBER_EATS: "/api/v1/integraciones/uber/orders",
};

export function tieneIntegracionDisponible(origen: string): boolean {
  return origen in BASE_POR_ORIGEN;
}

export async function aceptarPedido(pedido: Pedido): Promise<void> {
  const base = BASE_POR_ORIGEN[pedido.origen];
  if (!base || !pedido.id_externo) return;
  await httpClient.post(`${base}/${pedido.id_externo}/accept`, null, {
    params: { restaurante_id: pedido.restaurante_id },
  });
}

export async function marcarPedidoListo(pedido: Pedido): Promise<void> {
  const base = BASE_POR_ORIGEN[pedido.origen];
  if (!base || !pedido.id_externo) return;
  await httpClient.post(`${base}/${pedido.id_externo}/ready`, null, {
    params: { restaurante_id: pedido.restaurante_id },
  });
}

// Uber distingue dos operaciones distintas según si el pedido ya fue
// aceptado: deny_pos_order (antes de aceptar) vs. cancel (después de
// aceptar) — cada una con su propio set de motivos válidos.
export const MOTIVOS_RECHAZO = [
  { value: "ITEM_AVAILABILITY", label: "Producto agotado" },
  { value: "STORE_CLOSED", label: "Cocina cerrada" },
  { value: "CAPACITY", label: "Sin capacidad para atender el pedido" },
  { value: "OTHER", label: "Otro motivo" },
] as const;

export const MOTIVOS_CANCELACION_ACEPTADO = [
  { value: "OUT_OF_ITEMS", label: "Producto agotado" },
  { value: "KITCHEN_CLOSED", label: "Cocina cerrada" },
  { value: "CUSTOMER_CALLED_TO_CANCEL", label: "El cliente llamó a cancelar" },
  { value: "RESTAURANT_TOO_BUSY", label: "Restaurante muy ocupado" },
  { value: "CANNOT_COMPLETE_CUSTOMER_NOTE", label: "No se puede cumplir la nota del cliente" },
  { value: "OTHER", label: "Otro motivo" },
] as const;

export function motivosCancelacionPara(pedido: Pedido) {
  return pedido.estado === "NUEVA" ? MOTIVOS_RECHAZO : MOTIVOS_CANCELACION_ACEPTADO;
}

export async function cancelarPedido(
  pedido: Pedido,
  reasonCode: string,
  explanation: string,
): Promise<void> {
  const base = BASE_POR_ORIGEN[pedido.origen];
  if (base && pedido.id_externo) {
    if (pedido.estado === "NUEVA") {
      // Todavía no aceptado: deny_pos_order.
      await httpClient.post(
        `${base}/${pedido.id_externo}/deny`,
        { reason_code: reasonCode, explanation },
        { params: { restaurante_id: pedido.restaurante_id } },
      );
    } else {
      // Ya aceptado: deny_pos_order ya no aplica, hay que usar cancel.
      await httpClient.post(
        `${base}/${pedido.id_externo}/cancel`,
        { reason: reasonCode, details: explanation },
        { params: { restaurante_id: pedido.restaurante_id } },
      );
    }
    return;
  }
  // Sin integración (ej. LOCAL): solo cancela internamente en KITCHAN.
  await httpClient.post(`/api/v1/pedidos/${pedido.id}/cancelar-interno`);
}

export async function marcarPedidoEntregado(pedido: Pedido): Promise<void> {
  await httpClient.post(`/api/v1/pedidos/${pedido.id}/completar`);
}
