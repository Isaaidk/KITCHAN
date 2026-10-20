export interface PuntoComparacionHora {
  hora: number;
  hoy: number;
  ayer: number;
}

export interface AnaliticasPedidos {
  pedidos_totales_hoy: number;
  ticket_promedio: number;
  tiempo_promedio_preparacion_minutos: number;
  pedidos_cancelados_hoy: number;
  por_canal: Record<string, number>;
  comparacion_hoy_vs_ayer: PuntoComparacionHora[];
}
