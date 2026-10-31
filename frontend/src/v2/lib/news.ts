import type { NewsItem } from "./story";

/** Idioma original del medio (Finnhub publica medios en inglés): la marca de la tarjeta. */
const LANG_LABEL: Record<string, string> = { en: "En inglés" };

/** Revisión V6 (F3): solo enlaces http(s) bien formados; cualquier otro esquema (javascript:, data:…) es una tarjeta
 *  sin enlace. */
export function safeNewsUrl(u: string | null | undefined): string | null {
  if (!u || !/^https?:\/\//i.test(u.trim())) return null;
  try {
    const url = new URL(u.trim());
    return url.protocol === "https:" || url.protocol === "http:" ? url.href : null;
  } catch {
    return null;
  }
}

/** Lo que enseña una tarjeta de noticia: fecha (dd/mm/aaaa), medio, titular, resumen, imagen y su idioma. */
export function newsCard(n: NewsItem) {
  return {
    meta: [n.date ? n.date.split("-").reverse().join("/") : null, n.source].filter(Boolean).join(" · "),
    headline: n.headline,
    summary: n.summary ?? null,
    // Solo imágenes https (el motor ya descarta las demás). Decorativa (alt vacío, V6 F24): el titular ya es el texto.
    image: n.image && n.image.startsWith("https://") ? { src: n.image, alt: "" } : null,
    lang: n.lang ? (LANG_LABEL[n.lang] ?? null) : null,
    url: safeNewsUrl(n.url),
  };
}
