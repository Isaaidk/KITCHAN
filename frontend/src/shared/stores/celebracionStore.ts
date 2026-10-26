import { create } from "zustand";

interface CelebracionState {
  /** Cuenta de celebraciones pedidas; cada cambio lanza una animación nueva. */
  disparos: number;
  celebrar: () => void;
}

export const useCelebracionStore = create<CelebracionState>((set) => ({
  disparos: 0,
  celebrar: () => set((s) => ({ disparos: s.disparos + 1 })),
}));
