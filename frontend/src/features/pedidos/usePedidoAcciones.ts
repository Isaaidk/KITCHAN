import { useState } from "react";
import type { Pedido } from "../../shared/types/pedido";
import {
  aceptarPedido,
  cancelarPedido,
  marcarPedidoEntregado,
  marcarPedidoListo,
  tieneIntegracionDisponible,
} from "./integracionesApi";

export function usePedidoAcciones(pedido: Pedido) {
  const [procesando, setProcesando] = useState(false);
  const [mostrarCancelar, setMostrarCancelar] = useState(false);

  const integracionDisponible = tieneIntegracionDisponible(pedido.origen);
  const puedeAceptar = pedido.estado === "NUEVA" && integracionDisponible;
  const puedeMarcarListo = pedido.estado === "EN_PREPARACION" && integracionDisponible;
  const puedeCancelar = pedido.estado === "NUEVA" || pedido.estado === "EN_PREPARACION";
  const puedeCompletar = pedido.estado === "LISTA";

  const ejecutar = async (accion: (p: Pedido) => Promise<void>) => {
    setProcesando(true);
    try {
      // El cambio de estado llega por WS cuando el backend confirma con la
      // integración (o de inmediato para acciones internas); no se
      // actualiza el store de forma optimista.
      await accion(pedido);
    } finally {
      setProcesando(false);
    }
  };

  return {
    procesando,
    puedeAceptar,
    puedeMarcarListo,
    puedeCancelar,
    puedeCompletar,
    mostrarCancelar,
    setMostrarCancelar,
    aceptar: () => ejecutar(aceptarPedido),
    marcarListo: () => ejecutar(marcarPedidoListo),
    marcarEntregado: () => ejecutar(marcarPedidoEntregado),
    confirmarCancelacion: (reasonCode: string, explanation: string) =>
      ejecutar((p) => cancelarPedido(p, reasonCode, explanation)),
  };
}
