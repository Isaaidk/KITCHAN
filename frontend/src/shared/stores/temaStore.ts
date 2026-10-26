import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";

export type Tema = "claro" | "oscuro";

interface TemaState {
  tema: Tema;
  alternar: () => void;
}

/** Tema de la aplicación (modo oscuro de cocina). Se recuerda en cada dispositivo. */
export const useTemaStore = create<TemaState>()(
  persist(
    (set) => ({
      tema: "claro",
      alternar: () => set((s) => ({ tema: s.tema === "claro" ? "oscuro" : "claro" })),
    }),
    {
      name: "kitchan-tema",
      storage: createJSONStorage(() => localStorage),
    },
  ),
);
