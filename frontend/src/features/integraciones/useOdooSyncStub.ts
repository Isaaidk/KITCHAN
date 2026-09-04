import { useState } from "react";

export type EstadoOdoo = "idle" | "sincronizando" | "no_disponible";

/**
 * La integración con Odoo hoy es solo estructura en el backend (puerto +
 * adaptador stub, sin endpoint expuesto — decisión confirmada), así que acá
 * solo simulamos la animación de carga sin llamar a ningún endpoint real.
 */
export function useOdooSyncStub() {
  const [estado, setEstado] = useState<EstadoOdoo>("idle");

  const ejecutar = () => {
    setEstado("sincronizando");
    setTimeout(() => setEstado("no_disponible"), 1200);
  };

  return { estado, ejecutar };
}
