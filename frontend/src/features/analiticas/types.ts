export type Rango = "hoy" | "7d" | "30d";

export interface ResumenPeriodo {
  pedidos_totales: number;
  pedidos_cancelados: number;
  tasa_cancelacion: number;
  ventas_totales: number;
  ticket_promedio: number;
  tiempo_promedio_preparacion_minutos: number;
}

export interface PuntoHora {
  hora: number;
  pedidos: number;
  pedidos_anterior: number;
}

export interface PuntoDia {
  fecha: string;
  pedidos: number;
  ventas: number;
}

export interface CanalResumen {
  canal: string;
  pedidos: number;
  cancelados: number;
  ventas: number;
  ticket_promedio: number;
  tiempo_promedio_minutos: number;
  tasa_demora: number;
  porcentaje_pedidos: number;
  porcentaje_ventas: number;
}

export interface ProductoVendido {
  nombre: string;
  cantidad: number;
  ventas: number;
}

export interface ClientesResumen {
  identificacion: string;
  clientes_unicos: number;
  clientes_recurrentes: number;
  tasa_recurrencia: number;
  pedidos_por_cliente: number;
  distribucion: { etiqueta: string; clientes: number }[];
  mas_frecuentes: { cliente: string; pedidos: number; ventas: number }[];
  pedidos_analizados: number;
}

export interface MetodoPagoItem {
  metodo: string;
  pedidos: number;
  ventas: number;
  porcentaje_pedidos: number;
  porcentaje_ventas: number;
}

export interface MetodosPago {
  disponible: boolean;
  sin_dato: number;
  cobertura: number;
  items: MetodoPagoItem[];
}

/** Respuesta de GET /api/v1/reportes/pedidos/dashboard?rango=... */
export interface DashboardPedidos {
  rango: Rango;
  desde: string;
  hasta: string;
  resumen: ResumenPeriodo;
  periodo_anterior: ResumenPeriodo;
  por_hora: PuntoHora[];
  hora_pico: { hora: number; pedidos: number } | null;
  por_dia: PuntoDia[];
  por_canal: CanalResumen[];
  umbral_demora_minutos: number;
  productos_mas_vendidos: ProductoVendido[];
  productos_menos_vendidos: ProductoVendido[];
  combos_mas_vendidos: ProductoVendido[];
  productos_distintos: number;
  clientes: ClientesResumen;
  metodos_pago: MetodosPago;
}
