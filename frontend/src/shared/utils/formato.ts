// El formato numérico sigue el idioma del navegador (Intl) en vez de
// depender de toFixed, que siempre usa punto decimal.
const formatoDecimal = new Intl.NumberFormat(undefined, {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

/** Monto en dólares con dos decimales, p. ej. "$20.20" o "$20,20" según el idioma. */
export function moneda(valor: number): string {
  return `$${formatoDecimal.format(valor)}`;
}
