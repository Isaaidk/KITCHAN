// El formato numérico sigue el idioma del navegador (Intl) en vez de
// depender de toFixed, que siempre usa punto decimal.
const formatos = new Map<number, Intl.NumberFormat>();

/** Número con una cantidad fija de decimales, según el idioma del navegador. */
export function numero(valor: number, decimales = 0): string {
  let formato = formatos.get(decimales);
  if (!formato) {
    formato = new Intl.NumberFormat(undefined, {
      minimumFractionDigits: decimales,
      maximumFractionDigits: decimales,
    });
    formatos.set(decimales, formato);
  }
  return formato.format(valor);
}

/** Monto en dólares con dos decimales, p. ej. "$20.20" o "$20,20" según el idioma. */
export function moneda(valor: number): string {
  return `$${numero(valor, 2)}`;
}

/** Porcentaje sin decimales a partir de un valor 0–100, p. ej. "42%". */
export function porcentaje(valor: number): string {
  return `${numero(valor, 0)}%`;
}
