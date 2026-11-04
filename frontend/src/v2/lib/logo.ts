import type { AnalysisWithLogo, CompanyLogoInfo, StockAnalysis } from "@/lib/api";
import { API_BASE } from "./http";

/** Palabras que no dan inicial: formas jurídicas y enlaces («Bank of America» → BA, «JPMorgan Chase & Co.» → JC). */
const SKIP = new Set(["inc", "corp", "corporation", "co", "company", "ltd", "limited", "plc", "sa", "ag", "nv", "se",
  "spa", "ab", "asa", "oyj", "the", "of", "and", "de", "la", "el", "y", "&"]);

/** La placa de una empresa sin logotipo: la inicial de sus dos primeras palabras con sentido; sin nombre, las dos
 *  primeras letras del ticker sin su bolsa («MC.PA» → MC). */
export function logoInitials(name: string | null | undefined, symbol: string): string {
  const words = (name ?? "").split(/[\s\-/,.]+/).filter((w) => w && !SKIP.has(w.toLowerCase()) && /\p{L}|\d/u.test(w));
  const fromName = words.slice(0, 2).map((w) => (w.match(/[\p{L}\d]/u) ?? [""])[0]).join("").toUpperCase();
  return fromName || symbol.split(/[.\-]/)[0].slice(0, 2).toUpperCase();
}

/** URL del logotipo: la que trae el análisis (con su versión) o, en listas (cintillo, buscador, rivales), la del
 *  endpoint del símbolo. null: el backend ya dijo que no hay (placa sin pedir nada). */
export function logoSrc(symbol: string, info?: CompanyLogoInfo | null): string | null {
  if (info === null) return null;
  const path = info?.url ?? `/api/v2/logo/${encodeURIComponent(symbol.toUpperCase())}`;
  return `${API_BASE}${path}`;
}

/** El logotipo de un análisis: undefined si el análisis no lo trae (de antes de los logotipos, o de la caché). */
export function analysisLogo(a: StockAnalysis): CompanyLogoInfo | null | undefined {
  return (a as AnalysisWithLogo).logo;
}
