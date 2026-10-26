/** Canales con página propia de analíticas: la ruta usa `slug` y el backend `codigo`. */
export const CANALES_ANALITICAS = [
  { slug: "uber-eats", codigo: "UBER_EATS" },
  { slug: "pedidosya", codigo: "PEDIDOS_YA" },
  { slug: "rappi", codigo: "RAPPI" },
  { slug: "whatsapp", codigo: "WHATSAPP" },
] as const;

export function canalPorSlug(slug: string | undefined) {
  return CANALES_ANALITICAS.find((c) => c.slug === slug);
}
