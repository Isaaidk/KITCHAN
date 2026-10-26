import { useTemaStore } from "../../shared/stores/temaStore";

// Paletas fijas para los gráficos (el SVG de recharts no resuelve bien var()):
// una para el tema claro y otra para el oscuro de cocina.
const CLARO = {
  principal: "#6b1e3c",
  turquesa: "#2cb1b1",
  ambar: "#f4b942",
  secundario: "#8a949f",
  grilla: "#eee9dc",
  eje: "#7a8591",
  barraSuave: "#d9b9c5",
  pizarra: "#2e3a46",
  tooltipFondo: "#ffffff",
  tooltipBorde: "#e8e2d3",
  tooltipTexto: "#2e3a46",
  cursor: { fill: "rgba(107,30,60,0.06)", stroke: "rgba(107,30,60,0.2)" },
};

const OSCURO: typeof CLARO = {
  principal: "#d4698f",
  turquesa: "#3cc4c4",
  ambar: "#f4b942",
  secundario: "#8b97a3",
  grilla: "#2f3a46",
  eje: "#8b97a3",
  barraSuave: "#5b3447",
  pizarra: "#b9c4cf",
  tooltipFondo: "#252e38",
  tooltipBorde: "#3a4756",
  tooltipTexto: "#eef0ea",
  cursor: { fill: "rgba(212,105,143,0.1)", stroke: "rgba(212,105,143,0.35)" },
};

/** Colores de los gráficos según el tema activo. */
export function useGraficos() {
  const tema = useTemaStore((s) => s.tema);
  const c = tema === "oscuro" ? OSCURO : CLARO;
  return {
    ...c,
    tooltip: {
      contentStyle: {
        borderRadius: 12,
        border: `1px solid ${c.tooltipBorde}`,
        background: c.tooltipFondo,
        color: c.tooltipTexto,
        boxShadow: "0 12px 28px -8px rgba(0,0,0,0.3)",
        fontSize: 12,
        padding: "8px 12px",
      },
      labelStyle: { fontWeight: 700, color: c.tooltipTexto, marginBottom: 4 },
      cursor: c.cursor,
    },
  };
}
