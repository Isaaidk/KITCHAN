import { httpClient } from "../../shared/api/httpClient";
import type { Pedido } from "../../shared/types/pedido";

interface Motivo {
  value: string;
  label: string;
}

/**
 * Cada integración maneja sus propios endpoints de accept/ready/deny
 * (arquitectura modular). Lo que varía entre plataformas se declara aquí:
 * el body del rechazo, los motivos válidos y si permite cancelar un pedido
 * ya aceptado.
 */
interface ConfigIntegracion {
  base: string;
  /** Body del POST /deny (pedido todavía NUEVA). */
  bodyRechazo: (motivo: string, detalle: string) => Record<string, string>;
  motivosRechazo: readonly Motivo[];
  /** null = la plataforma no permite cancelar un pedido ya aceptado. */
  cancelacionAceptado: {
    body: (motivo: string, detalle: string) => Record<string, string>;
    motivos: readonly Motivo[];
  } | null;
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

// Valores de `cancel_type` que acepta Rappi en PUT .../orders/{id}/reject
// (ver DenyOrderRequest en integraciones/rappi/.../orders_api.py).
export const MOTIVOS_RECHAZO_RAPPI = [
  { value: "ITEM_OUT_OF_STOCK", label: "Producto agotado" },
  { value: "ITEM_NOT_FOUND", label: "Producto no existe en el menú" },
  { value: "ITEM_WRONG_PRICE", label: "Precio incorrecto" },
  { value: "ORDER_TOTAL_INCORRECT", label: "Total del pedido incorrecto" },
  { value: "ORDER_MISSING_INFORMATION", label: "Falta información del pedido" },
  { value: "ORDER_MISSING_ADDRESS_INFORMATION", label: "Falta información de la dirección" },
] as const;

const INTEGRACIONES: Record<string, ConfigIntegracion> = {
  UBER_EATS: {
    base: "/api/v1/integraciones/uber/orders",
    bodyRechazo: (motivo, detalle) => ({ reason_code: motivo, explanation: detalle }),
    motivosRechazo: MOTIVOS_RECHAZO,
    cancelacionAceptado: {
      body: (motivo, detalle) => ({ reason: motivo, details: detalle }),
      motivos: MOTIVOS_CANCELACION_ACEPTADO,
    },
  },
  RAPPI: {
    base: "/api/v1/integraciones/rappi/orders",
    bodyRechazo: (motivo, detalle) => ({ cancel_type: motivo, reason: detalle }),
    motivosRechazo: MOTIVOS_RECHAZO_RAPPI,
    // La API pública de Rappi no documenta cómo cancelar un pedido ya
    // tomado; /reject solo vale mientras el pedido está en SENT (NUEVA).
    cancelacionAceptado: null,
  },
};

export function tieneIntegracionDisponible(origen: string): boolean {
  return origen in INTEGRACIONES;
}

/**
 * true si el pedido se puede cancelar desde KITCHAN. Un pedido de una
 * plataforma que no permite cancelar después de aceptar (Rappi) no se
 * cancela solo internamente: el cliente seguiría esperando su pedido.
 */
export function permiteCancelar(pedido: Pedido): boolean {
  if (pedido.estado === "NUEVA") return true;
  if (pedido.estado !== "EN_PREPARACION") return false;
  const config = INTEGRACIONES[pedido.origen];
  return !config || config.cancelacionAceptado !== null;
}

export async function aceptarPedido(pedido: Pedido): Promise<void> {
  const config = INTEGRACIONES[pedido.origen];
  if (!config || !pedido.id_externo) return;
  await httpClient.post(`${config.base}/${pedido.id_externo}/accept`, null, {
    params: { restaurante_id: pedido.restaurante_id },
  });
}

export async function marcarPedidoListo(pedido: Pedido): Promise<void> {
  const config = INTEGRACIONES[pedido.origen];
  if (!config || !pedido.id_externo) return;
  await httpClient.post(`${config.base}/${pedido.id_externo}/ready`, null, {
    params: { restaurante_id: pedido.restaurante_id },
  });
}

export function motivosCancelacionPara(pedido: Pedido): readonly Motivo[] {
  const config = INTEGRACIONES[pedido.origen] ?? INTEGRACIONES.UBER_EATS;
  if (pedido.estado === "NUEVA") return config.motivosRechazo;
  return config.cancelacionAceptado?.motivos ?? config.motivosRechazo;
}

export async function cancelarPedido(
  pedido: Pedido,
  reasonCode: string,
  explanation: string,
): Promise<void> {
  const config = INTEGRACIONES[pedido.origen];
  if (config && pedido.id_externo) {
    if (pedido.estado === "NUEVA") {
      // Todavía no aceptado: rechazo (deny) en la plataforma.
      await httpClient.post(
        `${config.base}/${pedido.id_externo}/deny`,
        config.bodyRechazo(reasonCode, explanation),
        { params: { restaurante_id: pedido.restaurante_id } },
      );
    } else if (config.cancelacionAceptado) {
      // Ya aceptado: el rechazo ya no aplica, hay que usar cancel.
      await httpClient.post(
        `${config.base}/${pedido.id_externo}/cancel`,
        config.cancelacionAceptado.body(reasonCode, explanation),
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
