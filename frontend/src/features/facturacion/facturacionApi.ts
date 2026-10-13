import { httpClient } from "../../shared/api/httpClient";

export type EstadoFactura = "PENDIENTE_SRI" | "AUTORIZADA" | "CON_ERROR" | "ANULADA";

export interface Factura {
  pedido_id: string;
  numero: string | null;
  estado: EstadoFactura;
  total: number;
  numero_autorizacion: string | null;
  fecha_autorizacion: string | null;
  mensaje_error: string | null;
}

export const ETIQUETA_FACTURA: Record<EstadoFactura, string> = {
  PENDIENTE_SRI: "Esperando autorización del SRI",
  AUTORIZADA: "Autorizada por el SRI",
  CON_ERROR: "Rechazada",
  ANULADA: "Anulada",
};

export async function obtenerFactura(pedidoId: string): Promise<Factura | null> {
  const { data } = await httpClient.get<Factura | null>(
    `/api/v1/facturacion/pedidos/${pedidoId}`,
  );
  return data;
}

export async function facturarPedido(pedidoId: string): Promise<Factura> {
  const { data } = await httpClient.post<Factura>(`/api/v1/facturacion/pedidos/${pedidoId}`);
  return data;
}

export async function odooConfigurado(): Promise<boolean> {
  const { data } = await httpClient.get<{ configurado: boolean }>("/api/v1/facturacion/estado");
  return data.configurado;
}

export async function conciliarFacturas(): Promise<number> {
  const { data } = await httpClient.post<{ actualizadas: number }>(
    "/api/v1/facturacion/conciliar",
  );
  return data.actualizadas;
}
