// Paleta fija para los gráficos (el SVG de recharts no resuelve bien var()).
export const COLOR_PRINCIPAL = "#6b1e3c";
export const COLOR_TURQUESA = "#2cb1b1";
export const COLOR_AMBAR = "#f4b942";
export const COLOR_SECUNDARIO = "#8a949f";
export const COLOR_GRILLA = "#eee9dc";
export const COLOR_EJE = "#7a8591";
// Barras que no son el máximo: granate muy suave, para que el pico resalte.
export const COLOR_BARRA_SUAVE = "#d9b9c5";

export const estiloTooltip = {
  contentStyle: {
    borderRadius: 12,
    border: "1px solid #e8e2d3",
    boxShadow: "0 12px 28px -8px rgba(46,58,70,0.2)",
    fontSize: 12,
    padding: "8px 12px",
  },
  labelStyle: { fontWeight: 700, color: "#2e3a46", marginBottom: 4 },
  cursor: { fill: "rgba(107,30,60,0.06)", stroke: "rgba(107,30,60,0.2)" },
};
