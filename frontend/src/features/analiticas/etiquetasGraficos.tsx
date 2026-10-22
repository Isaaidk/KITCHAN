// Piezas de recharts compartidas: degradado de las barras y etiqueta directa del valor máximo.

/** Degradado vertical de un color que se desvanece hacia abajo (para usarlo con fill="url(#id)"). */
export function DegradadoVertical({ id, color, desde = 1, hasta = 0.5 }: { id: string; color: string; desde?: number; hasta?: number }) {
  return (
    <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stopColor={color} stopOpacity={desde} />
      <stop offset="100%" stopColor={color} stopOpacity={hasta} />
    </linearGradient>
  );
}

// recharts entrega las coordenadas como número o texto según el gráfico.
interface PropsEtiqueta {
  x?: number | string;
  y?: number | string;
  width?: number | string;
  value?: number | string;
  index?: number;
}

/**
 * Etiqueta sobre una sola barra (la de mayor valor): el dato se lee de un vistazo
 * sin una leyenda ni un tooltip. Va en `<LabelList content={...} />`.
 */
export function etiquetaDelMaximo(indiceMaximo: number, texto: (valor: number) => string, color: string) {
  return function EtiquetaMaximo({ x = 0, y = 0, width = 0, value, index }: PropsEtiqueta) {
    const numero = Number(value);
    if (index !== indiceMaximo || !numero) return null;
    return (
      <text x={Number(x) + Number(width) / 2} y={Number(y) - 7} textAnchor="middle" fontSize={11} fontWeight={700} fill={color}>
        {texto(numero)}
      </text>
    );
  };
}
