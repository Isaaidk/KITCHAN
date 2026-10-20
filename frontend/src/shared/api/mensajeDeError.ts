/**
 * Extrae un mensaje legible de un error de axios. El backend puede devolver
 * `detail` como texto, como lista de errores de validación o como objeto
 * `{ error, respuesta }` (errores de una plataforma externa como Uber).
 */
export function mensajeDeError(err: any, porDefecto: string): string {
  const detail = err?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length > 0 && typeof detail[0]?.msg === "string") {
    return detail[0].msg;
  }
  if (detail && typeof detail.error === "string") return detail.error;
  return porDefecto;
}
