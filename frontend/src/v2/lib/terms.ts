// V7 · P3: qué definición (src/lib/tooltips.ts) explica cada etiqueta del bloque superior y del capítulo 3. El motor da
// las categorías y las filas del precio por su nombre; las dimensiones de la confianza y las señales de mercado, por
// su clave.
import { DEFINITIONS } from "@/lib/tooltips";

const CATEGORY: Record<string, string> = {
  "Solidez Financiera": "cat_solidez", "Rentabilidad": "cat_rentabilidad", "Calidad de Ganancias": "cat_calidad_ganancias",
  "Crecimiento": "cat_crecimiento", "Valoración": "cat_valoracion",
};

/** Filas del atractivo del precio («Bloque de múltiplos · …», «DCF inverso (FFO)»…): por cómo empieza la etiqueta. */
const PRICE_ROW: Array<[string, string]> = [
  ["Bloque de múltiplos", "multiples_block"], ["Bloque P/B y P/TBV", "pb_block"], ["DCF inverso", "reverse_dcf"],
  ["DCF", "dcf_upside"], ["P/FFO", "p_ffo"], ["Rentabilidad por dividendo", "dividend_yield"],
  ["P/B frente al ROE", "pb_roe"], ["EV/Ventas", "ev_sales"], ["Regla de 40", "rule_of_40"],
  ["Valoración", "cat_valoracion"], ["Ajuste por confianza", "confidence_adjustment"],
];

const known = (k: string | undefined): string | undefined => (k && DEFINITIONS[k] ? k : undefined);

export const categoryTerm = (name: string): string | undefined => known(CATEGORY[name]);
export const priceRowTerm = (label: string): string | undefined => known(PRICE_ROW.find(([p]) => label.startsWith(p))?.[1]);
export const confidenceTerm = (key: string): string | undefined => known(`conf_${key}`);
/** v4 (PM): la cifra de la beta puede ser la ajustada, la de la industria o la bruta (la etiqueta del motor dice cuál):
 *  la definición es la de la cifra que se ve. */
const BETA_LABEL: Array<[string, string]> = [["Beta ajustada", "beta_blume"], ["Beta de la industria", "beta_industry"]];
export const definitionKey = (key: string, label: string): string =>
  (key === "beta" && known(BETA_LABEL.find(([p]) => label.startsWith(p))?.[1])) || key;
/** Señales de mercado (`market.rows[].key`) y el rango de 52 semanas. */
export const marketTerm = (key: string): string | undefined => known(key);
