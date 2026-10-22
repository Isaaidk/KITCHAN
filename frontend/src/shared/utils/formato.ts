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

/** Duración en minutos con un decimal, p. ej. "12,6 min". */
export function minutos(valor: number): string {
  return `${numero(valor, 1)} min`;
}

/**
 * Variación porcentual entre dos periodos. Devuelve null cuando no hay un valor
 * anterior con el que comparar (dividir por cero no tiene sentido).
 */
export function variacion(actual: number, anterior: number): number | null {
  if (!anterior) return null;
  return ((actual - anterior) / anterior) * 100;
}

/** "13:00" para la hora 13 (formato de reloj de 24 h). */
export function horaEtiqueta(hora: number): string {
  return `${String(hora).padStart(2, "0")}:00`;
}

const formatoDiaCorto = new Intl.DateTimeFormat(undefined, { day: "numeric", month: "short" });

/** "8 oct" a partir de una fecha ISO (AAAA-MM-DD); se interpreta como fecha local, sin desfase. */
export function fechaCorta(iso: string): string {
  const [anio, mes, dia] = iso.split("-").map(Number);
  return formatoDiaCorto.format(new Date(anio, mes - 1, dia));
}

const formatoFechaHora = new Intl.DateTimeFormat(undefined, {
  day: "numeric",
  month: "short",
  hour: "2-digit",
  minute: "2-digit",
});

/** "21 oct, 14:05" a partir de una fecha ISO con zona horaria. */
export function fechaHora(iso: string): string {
  return formatoFechaHora.format(new Date(iso));
}

const formatoRelativo = new Intl.RelativeTimeFormat(undefined, { numeric: "auto" });

/** "hace 5 minutos", "ayer", "hace 3 días"; pasado el mes, la fecha. */
export function hace(iso: string, ahora: number = Date.now()): string {
  const minutos = Math.floor((ahora - new Date(iso).getTime()) / 60000);
  if (minutos < 60) return formatoRelativo.format(-Math.max(minutos, 0), "minute");
  const horas = Math.floor(minutos / 60);
  if (horas < 24) return formatoRelativo.format(-horas, "hour");
  const dias = Math.floor(horas / 24);
  if (dias < 30) return formatoRelativo.format(-dias, "day");
  return fechaHora(iso);
}
