import { useEffect, useState } from "react";

/**
 * Anima un número desde 0 hasta `objetivo` (ease-out cúbico) para las
 * métricas del dashboard. Respeta prefers-reduced-motion.
 */
export function useCountUp(objetivo: number, duracionMs = 900): number {
  const [valor, setValor] = useState(0);

  useEffect(() => {
    const reducir = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    if (reducir || !Number.isFinite(objetivo)) {
      setValor(objetivo);
      return;
    }

    let frame = 0;
    const inicio = performance.now();
    const paso = (ahora: number) => {
      const t = Math.min(1, (ahora - inicio) / duracionMs);
      const eased = 1 - Math.pow(1 - t, 3);
      setValor(objetivo * eased);
      if (t < 1) frame = requestAnimationFrame(paso);
    };
    frame = requestAnimationFrame(paso);
    return () => cancelAnimationFrame(frame);
  }, [objetivo, duracionMs]);

  return valor;
}
