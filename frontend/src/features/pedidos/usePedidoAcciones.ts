import { useState } from "react";
import { mensajeDeError } from "../../shared/api/mensajeDeError";
import { useToastStore } from "../../shared/stores/toastStore";
import type { Pedido } from "../../shared/types/pedido";
import {
  aceptarPedido,
  cancelarPedido,
  marcarPedidoEntregado,
  marcarPedidoListo,
  permiteCancelar,
  tieneIntegracionDisponible,
} from "./integracionesApi";

export function usePedidoAcciones(pedido: Pedido) {
  const [procesando, setProcesando] = useState(false);
  const [mostrarCancelar, setMostrarCancelar] = useState(false);

  const integracionDisponible = tieneIntegracionDisponible(pedido.origen);
  const puedeAceptar = pedido.estado === "NUEVA" && integracionDisponible;
  const puedeMarcarListo = pedido.estado === "EN_PREPARACION" && integracionDisponible;
  const puedeCancelar = permiteCancelar(pedido);
  // Pedido en preparación de una plataforma que no permite cancelarlo por
  // API (Rappi): se muestra un aviso en vez del botón.
  const cancelacionSoloPorSoporte = pedido.estado === "EN_PREPARACION" && !puedeCancelar;
  const puedeCompletar = pedido.estado === "LISTA";

  const ejecutar = async (accion: (p: Pedido) => Promise<void>): Promise<boolean> => {
    setProcesando(true);
    try {
      // El cambio de estado llega por WS cuando el backend confirma con la
      // integración (o de inmediato para acciones internas); no se
      // actualiza el store de forma optimista.
      await accion(pedido);
      return true;
    } catch (err) {
      // Antes el error se perdía sin aviso; ahora se muestra el motivo
      // (ej. "Vuelve a conectar Uber Eats desde Integraciones").
      useToastStore
        .getState()
        .add(mensajeDeError(err, "No se pudo completar la acción. Inténtalo de nuevo."), "critica");
      return false;
    } finally {
      setProcesando(false);
    }
  };

  const confirmarCancelacion = async (reasonCode: string, explanation: string) => {
    setProcesando(true);
    try {
      await cancelarPedido(pedido, reasonCode, explanation);
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
    cancelacionSoloPorSoporte,
    mostrarCancelar,
    setMostrarCancelar,
    aceptar: () => ejecutar(aceptarPedido),
    marcarListo: () => ejecutar(marcarPedidoListo),
    marcarEntregado: () => ejecutar(marcarPedidoEntregado),
    // La cancelación deja que el error suba: el modal lo muestra en su
    // propio aviso y se mantiene abierto para reintentar.
    confirmarCancelacion,
  };
}
