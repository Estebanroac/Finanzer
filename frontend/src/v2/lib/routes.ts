// Rutas de /v2 (E3): /v2/{T} es la historia y /v2/{T}/{capitulo} su página de profundidad. Export estático: el cliente
// lee la URL (una sola ruta catch-all).
export const CHAPTER_SLUGS = ["empresa", "negocio", "accion", "calidad", "valor", "rivales", "riesgos", "actualidad", "conclusion"] as const;
export type ChapterSlug = typeof CHAPTER_SLUGS[number];

const isSlug = (s: string): s is ChapterSlug => (CHAPTER_SLUGS as readonly string[]).includes(s);

/** Lo que parece un ticker (AAPL, BRK.B, MC.PA, BRK-B): el símbolo de la ruta y el Enter del buscador. */
export const TICKER_LIKE = /^[A-Za-z][A-Za-z0-9]{0,5}([.-][A-Za-z0-9]{1,3})?$/;

/** decodeURIComponent sin lanzar: una ruta mal codificada ("%E0%A4%A") es null, no una excepción. */
function safeDecode(s: string): string | null {
  try {
    return decodeURIComponent(s);
  } catch {
    return null;
  }
}

export interface V2Route { symbol: string | null; chapter: ChapterSlug | null; invalid: boolean }

/** Símbolo (en mayúsculas) y capítulo de una ruta /v2/…; un capítulo desconocido es null (se muestra la historia).
 *  Revisión V6 (F6): un símbolo mal codificado o que no parece un ticker no se pide al backend: `invalid` (la página
 *  dice «Ticker no válido»). */
export function parseV2Path(pathname: string): V2Route {
  const segs = pathname.split("/").filter(Boolean);
  const i = segs.indexOf("v2");
  const raw = i >= 0 ? segs[i + 1] : undefined;
  const ch = i >= 0 ? segs[i + 2] : undefined;
  if (!raw) return { symbol: null, chapter: null, invalid: false };
  const sym = safeDecode(raw)?.trim();
  if (!sym || !TICKER_LIKE.test(sym)) return { symbol: null, chapter: null, invalid: true };
  const chapter = ch ? safeDecode(ch)?.toLowerCase() ?? null : null;
  return { symbol: sym.toUpperCase(), chapter: chapter && isSlug(chapter) ? chapter : null, invalid: false };
}

/** "/v2/AAPL", "/v2/AAPL/calidad" o "/v2/AAPL/calidad#piotroski". */
export function chapterHref(symbol: string, chapter?: ChapterSlug, anchor?: string): string {
  const base = `/v2/${encodeURIComponent(symbol)}`;
  if (!chapter) return base;
  return `${base}/${chapter}${anchor ? `#${anchor}` : ""}`;
}
