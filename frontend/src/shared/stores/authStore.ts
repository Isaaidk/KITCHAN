import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";
import type { Usuario } from "../types/usuario";

interface AuthState {
  token: string | null;
  usuario: Usuario | null;
  login: (token: string, usuario: Usuario) => void;
  logout: () => void;
}

const CLAVE = "kitchan-auth";

// "Recordarme": con la casilla marcada la sesión sobrevive al cerrar el navegador
// (localStorage); desmarcada, dura mientras la pestaña esté abierta (sessionStorage).
// Si al arrancar ya hay una sesión de pestaña, se respeta esa elección.
let recordar = sessionStorage.getItem(CLAVE) === null;

/** Define dónde se guardará la sesión que se está por iniciar. Llamar antes de `login`. */
export function recordarSesion(valor: boolean) {
  recordar = valor;
}

const almacenamiento = {
  getItem: (nombre: string) => localStorage.getItem(nombre) ?? sessionStorage.getItem(nombre),
  setItem: (nombre: string, valor: string) => {
    const destino = recordar ? localStorage : sessionStorage;
    const otro = recordar ? sessionStorage : localStorage;
    otro.removeItem(nombre);
    destino.setItem(nombre, valor);
  },
  removeItem: (nombre: string) => {
    localStorage.removeItem(nombre);
    sessionStorage.removeItem(nombre);
  },
};

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      usuario: null,
      login: (token, usuario) => set({ token, usuario }),
      logout: () => set({ token: null, usuario: null }),
    }),
    { name: CLAVE, storage: createJSONStorage(() => almacenamiento) },
  ),
);
