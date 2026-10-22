import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";

interface SonidoState {
  activo: boolean;
  alternar: () => void;
}

/** Preferencia de cada dispositivo: el aviso sonoro de pedidos nuevos (activado por defecto). */
export const useSonidoStore = create<SonidoState>()(
  persist(
    (set) => ({
      activo: true,
      alternar: () => set((s) => ({ activo: !s.activo })),
    }),
    {
      name: "kitchan-sonido",
      storage: createJSONStorage(() => localStorage),
    },
  ),
);
