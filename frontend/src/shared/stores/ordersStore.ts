import { create } from "zustand";
import type { Pedido } from "../types/pedido";

interface OrdersState {
  pedidos: Record<string, Pedido>;
  // Flags solo de presentación: `cargado` habilita los skeletons de la
  // cola mientras llega la primera hidratación y `conectado` alimenta el
  // indicador "En vivo" del topbar.
  cargado: boolean;
  conectado: boolean;
  setInitial: (pedidos: Pedido[]) => void;
  upsert: (pedido: Pedido) => void;
  setConectado: (conectado: boolean) => void;
}

export const useOrdersStore = create<OrdersState>((set) => ({
  pedidos: {},
  cargado: false,
  conectado: false,
  setInitial: (pedidos) =>
    set({ pedidos: Object.fromEntries(pedidos.map((p) => [p.id, p])), cargado: true }),
  upsert: (pedido) =>
    set((state) => ({ pedidos: { ...state.pedidos, [pedido.id]: pedido } })),
  setConectado: (conectado) => set({ conectado }),
}));
