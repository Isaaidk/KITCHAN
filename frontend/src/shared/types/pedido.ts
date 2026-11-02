export type EstadoPedido =
  | "NUEVA"
  | "EN_PREPARACION"
  | "LISTA"
  | "ENTREGADA"
  | "CANCELADA";

export interface PedidoItem {
  nombre: string;
  cantidad: number;
  precio_unitario: number;
  notas?: string | null;
}

export interface Pedido {
  id: string;
  restaurante_id: string;
  origen: string;
  id_externo: string | null;
  cliente: string;
  nota_cliente: string | null;
  /** Contacto y entrega; null cuando el canal no los informa. */
  telefono_cliente?: string | null;
  tipo_entrega?: "DOMICILIO" | "RETIRO" | null;
  direccion_entrega?: string | null;
  items: PedidoItem[];
  total: number;
  estado: EstadoPedido;
  estado_entrega: string | null;
  /** Cómo se pagó (EFECTIVO, TARJETA…); null cuando el canal no lo informa. */
  metodo_pago?: string | null;
  fecha_creacion: string;
}

export interface PedidosPaginados {
  resultados: Pedido[];
  total: number;
}

export interface EventoPedidoWS {
  tipo: "PEDIDO_CREADO" | "PEDIDO_ACTUALIZADO";
  restaurante_id: string;
  pedido: Pedido;
}
