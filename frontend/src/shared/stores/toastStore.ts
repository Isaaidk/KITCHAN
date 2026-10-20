import { create } from "zustand";
import type { Pedido } from "../types/pedido";

export type VarianteToast = "normal" | "critica";

export interface Toast {
  id: string;
  mensaje: string;
  variante: VarianteToast;
  pedido?: Pedido;
}

interface ToastState {
  toasts: Toast[];
  add: (mensaje: string, variante?: VarianteToast, pedido?: Pedido) => void;
  remove: (id: string) => void;
}

export const useToastStore = create<ToastState>((set) => ({
  toasts: [],
  add: (mensaje, variante = "normal", pedido) =>
    set((state) => ({
      toasts: [...state.toasts, { id: crypto.randomUUID(), mensaje, variante, pedido }],
    })),
  remove: (id) =>
    set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) })),
}));
