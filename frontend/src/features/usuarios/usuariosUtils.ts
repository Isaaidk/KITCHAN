import type { RolUsuario } from "../../shared/types/usuario";

export const ETIQUETA_ROL: Record<RolUsuario, string> = {
  ADMIN: "Administrador",
  OPERADOR: "Operador",
};

export function iniciales(nombre: string) {
  return nombre
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase())
    .join("");
}

// Color de avatar estable a partir del nombre.
const TONOS = ["#6b1e3c", "#1f8f8f", "#2e3a46", "#9a6410", "#b4533a", "#5f7d4e"];
export function tonoPara(nombre: string) {
  let h = 5381;
  for (const c of nombre) h = (Math.imul(h, 33) + c.charCodeAt(0)) >>> 0;
  h = (h ^ (h >>> 15)) >>> 0;
  return TONOS[h % TONOS.length];
}
