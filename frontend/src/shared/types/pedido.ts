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
  items: PedidoItem[];
  total: number;
  estado: EstadoPedido;
  estado_entrega: string | null;
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
