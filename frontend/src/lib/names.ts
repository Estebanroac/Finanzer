import type { StockAnalysis } from "./api";

/** V7 (nombres en español): sector, industria y país del perfil en español (display.profile, backend/lib/names.py);
 *  sin ese bloque (un análisis anterior en caché), los de la fuente. */
export function profileNames(a: StockAnalysis): { sector: string | null; industry: string | null; country: string | null } {
  const es = a.display?.profile;
  return { sector: es?.sector || a.profile.sector || null, industry: es?.industry || a.profile.industry || null,
           country: es?.country || a.profile.country || null };
}

/** El nombre a mitad de frase: «Electrónica de consumo» → «electrónica de consumo»; las siglas se quedan («REIT…»). */
export function inline(name: string | null | undefined): string {
  const n = (name ?? "").trim();
  return n.length > 1 && n[1] === n[1].toLowerCase() && n[1] !== n[1].toUpperCase() ? n[0].toLowerCase() + n.slice(1) : n;
}
