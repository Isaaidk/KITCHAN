import { useEffect, useRef } from "react";
import { httpClient } from "../../shared/api/httpClient";
import { useAuthStore } from "../../shared/stores/authStore";
import { useOrdersStore } from "../../shared/stores/ordersStore";
import { useToastStore } from "../../shared/stores/toastStore";
import { crearSocketPedidos } from "../../shared/ws/socketClient";
import type { EventoPedidoWS, PedidosPaginados } from "../../shared/types/pedido";

const BACKOFF_INICIAL_MS = 1000;
const BACKOFF_MAX_MS = 30000;

async function hidratarPedidosActivos() {
  const { data } = await httpClient.get<PedidosPaginados>("/api/v1/pedidos");
  useOrdersStore.getState().setInitial(data.resultados);
}

function manejarEvento(evento: EventoPedidoWS) {
  useOrdersStore.getState().upsert(evento.pedido);

  const addToast = useToastStore.getState().add;
  if (evento.tipo === "PEDIDO_CREADO") {
    // Se adjunta el pedido para poder mostrar acciones rápidas
    // (Aceptar/Cancelar) directamente sobre el toast.
    addToast(`Nuevo pedido de ${evento.pedido.cliente}`, "normal", evento.pedido);
  } else if (evento.pedido.estado === "CANCELADA") {
    addToast(`Pedido de ${evento.pedido.cliente} cancelado`, "critica");
  } else if (evento.pedido.estado === "LISTA") {
    addToast(`Pedido de ${evento.pedido.cliente} listo`, "normal");
  }
}

/**
 * Hidrata el store de pedidos vía REST y mantiene una conexión WS con
 * reconexión (backoff exponencial); en cada reconexión re-sincroniza vía
 * GET por si se perdieron eventos mientras estuvo desconectado.
 */
export function useOrdersSocket() {
  const token = useAuthStore((s) => s.token);
  const backoffRef = useRef(BACKOFF_INICIAL_MS);
  const socketRef = useRef<WebSocket | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const activoRef = useRef(true);

  useEffect(() => {
    if (!token) return;
    activoRef.current = true;

    const conectar = () => {
      if (!activoRef.current) return;

      hidratarPedidosActivos().catch(() => {
        // Si falla el GET inicial, igual intentamos abrir el WS; el
        // próximo reintento de reconexión volverá a hidratar.
      });

      const socket = crearSocketPedidos(token);
      socketRef.current = socket;

      // Guarda contra el doble-montaje de React StrictMode en desarrollo
      // (efecto -> cleanup -> efecto): si este socket ya no es el vigente
      // (socketRef fue reemplazado o limpiado), sus eventos se ignoran.
      const esVigente = () => socketRef.current === socket;

      socket.onopen = () => {
        if (!esVigente()) return;
        backoffRef.current = BACKOFF_INICIAL_MS;
      };

      socket.onmessage = (event) => {
        if (!esVigente()) return;
        try {
          const data: EventoPedidoWS = JSON.parse(event.data);
          manejarEvento(data);
        } catch {
          // Mensaje no parseable, se ignora.
        }
      };

      socket.onclose = () => {
        if (!activoRef.current || !esVigente()) return;
        timerRef.current = setTimeout(conectar, backoffRef.current);
        backoffRef.current = Math.min(backoffRef.current * 2, BACKOFF_MAX_MS);
      };
    };

    conectar();

    return () => {
      activoRef.current = false;
      if (timerRef.current) clearTimeout(timerRef.current);
      const socket = socketRef.current;
      socketRef.current = null;
      socket?.close();
    };
  }, [token]);
}
