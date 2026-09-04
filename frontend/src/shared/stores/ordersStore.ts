import { create } from "zustand";
import type { Pedido } from "../types/pedido";

interface OrdersState {
  pedidos: Record<string, Pedido>;
  setInitial: (pedidos: Pedido[]) => void;
  upsert: (pedido: Pedido) => void;
}

export const useOrdersStore = create<OrdersState>((set) => ({
  pedidos: {},
  setInitial: (pedidos) =>
    set({ pedidos: Object.fromEntries(pedidos.map((p) => [p.id, p])) }),
  upsert: (pedido) =>
    set((state) => ({ pedidos: { ...state.pedidos, [pedido.id]: pedido } })),
}));
