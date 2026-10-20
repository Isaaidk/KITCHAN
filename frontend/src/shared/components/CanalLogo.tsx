import type { ReactNode } from "react";

interface Props {
  /** Clave del canal: UBER_EATS, RAPPI, PEDIDOSYA, WHATSAPP, ODOO, LOCAL... */
  canal: string;
  color: string;
  nombre: string;
  size?: number;
  className?: string;
}

/**
 * Glifos simplificados (no son los logos oficiales) dibujados sobre el color
 * de marca de cada canal. Para usar los logos reales, reemplazar el contenido
 * del `case` correspondiente por el SVG oficial.
 */
function glifo(canal: string, nombre: string): ReactNode {
  const trazo = { fill: "none", stroke: "#fff", strokeWidth: 2, strokeLinecap: "round", strokeLinejoin: "round" } as const;
  switch (canal) {
    case "UBER_EATS":
      // Bolsa de pedido
      return (
        <>
          <path d="M5.5 8.5h13l-1 11h-11l-1-11z" {...trazo} />
          <path d="M9 8.5a3 3 0 0 1 6 0" {...trazo} />
        </>
      );
    case "RAPPI":
      // Bigote
      return (
        <path
          d="M2.5 13.5c2.2-4.2 5.6-4.6 9.5-1.4 3.9-3.2 7.3-2.8 9.5 1.4-2.2-1.2-4.4-.6-6.2 1.4-1.2 1.3-2.2 1.5-3.3 1.5s-2.1-.2-3.3-1.5c-1.8-2-4-2.6-6.2-1.4z"
          fill="#fff"
        />
      );
    case "PEDIDOS_YA":
    case "PEDIDOSYA":
      // Carita sonriente
      return (
        <>
          <circle cx="12" cy="12" r="8.5" {...trazo} />
          <path d="M8 13.5c1 2 2.4 3 4 3s3-1 4-3" {...trazo} />
          <circle cx="9" cy="9.8" r="1" fill="#fff" />
          <circle cx="15" cy="9.8" r="1" fill="#fff" />
        </>
      );
    case "WHATSAPP":
      return (
        <>
          <path d="M12 3.5a8.5 8.5 0 0 0-7.4 12.7L3.5 20.5l4.4-1.1A8.5 8.5 0 1 0 12 3.5z" {...trazo} />
          <path d="M9.2 8.6c-.3 2.9 2.7 5.9 5.9 6.2l1.2-1.4-2-1-.9.8c-1-.4-1.9-1.3-2.3-2.3l.8-.9-1-2z" fill="#fff" />
        </>
      );
    case "ODOO":
      // Dos aros, como las "oo" del nombre
      return (
        <>
          <circle cx="8.2" cy="12" r="4" {...trazo} strokeWidth={2.6} />
          <circle cx="16.2" cy="12" r="4" {...trazo} strokeWidth={2.6} />
        </>
      );
    case "LOCAL":
      return (
        <>
          <path d="M4 10.5 5.5 5h13L20 10.5" {...trazo} />
          <path d="M5 10.5v8.5h14v-8.5" {...trazo} />
          <path d="M10 19v-4.5h4V19" {...trazo} />
        </>
      );
    default:
      return (
        <text x="12" y="16.5" textAnchor="middle" fontSize="13" fontWeight="700" fill="#fff" fontFamily="inherit">
          {nombre.charAt(0).toUpperCase()}
        </text>
      );
  }
}

export default function CanalLogo({ canal, color, nombre, size = 40, className }: Props) {
  return (
    <span
      className={className}
      role="img"
      aria-label={nombre}
      style={{
        flexShrink: 0,
        display: "inline-grid",
        placeItems: "center",
        width: size,
        height: size,
        borderRadius: Math.round(size * 0.28),
        background: `linear-gradient(160deg, color-mix(in srgb, ${color} 88%, white), ${color})`,
        boxShadow: `inset 0 1px 0 rgba(255,255,255,0.28), 0 6px 14px -8px color-mix(in srgb, ${color} 75%, #0f172a)`,
      }}
    >
      <svg width={size * 0.6} height={size * 0.6} viewBox="0 0 24 24" aria-hidden="true">
        {glifo(canal, nombre)}
      </svg>
    </span>
  );
}
