import { useEffect, useMemo, useState } from "react";
import { useCelebracionStore } from "../stores/celebracionStore";
import styles from "./Celebracion.module.css";

const COLORES = ["#f4b942", "#2cb1b1", "#6b1e3c", "#f8f6ef", "#e0809f"];
const PARTICULAS = 22;

function prefiereMenosMovimiento() {
  return typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

/**
 * Lluvia corta de confeti cuando se completa una entrega. Es solo decorativa
 * (aria-hidden) y no se muestra si la persona pidió menos movimiento.
 */
export default function Celebracion() {
  const disparos = useCelebracionStore((s) => s.disparos);
  const [visible, setVisible] = useState(false);

  // Cada disparo genera una tanda nueva de partículas con valores propios.
  const particulas = useMemo(
    () =>
      Array.from({ length: PARTICULAS }, (_, i) => ({
        id: `${disparos}-${i}`,
        dx: (Math.random() - 0.5) * 520,
        dy: -(160 + Math.random() * 260),
        giro: (Math.random() - 0.5) * 720,
        color: COLORES[i % COLORES.length],
        redonda: i % 3 === 0,
        demora: Math.random() * 120,
      })),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [disparos],
  );

  useEffect(() => {
    if (disparos === 0 || prefiereMenosMovimiento()) return;
    setVisible(true);
    const id = setTimeout(() => setVisible(false), 1700);
    return () => clearTimeout(id);
  }, [disparos]);

  if (!visible) return null;
  return (
    <div className={styles.capa} aria-hidden="true">
      {particulas.map((p) => (
        <span
          key={p.id}
          className={`${styles.particula} ${p.redonda ? styles.redonda : ""}`}
          style={{
            background: p.color,
            ["--dx" as string]: `${p.dx}px`,
            ["--dy" as string]: `${p.dy}px`,
            ["--giro" as string]: `${p.giro}deg`,
            animationDelay: `${p.demora}ms`,
          }}
        />
      ))}
    </div>
  );
}
