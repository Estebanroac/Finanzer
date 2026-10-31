// Qué significa cada criterio de Piotroski (2000) en lenguaje llano. Definiciones, como src/lib/tooltips.ts: sin
// umbrales ni lecturas (si se cumple o no lo dice el motor en institutional.piotroski_criteria).
export const PIOTROSKI_PLAIN: Record<string, string> = {
  roa_positive: "Gana dinero sobre lo que tiene.",
  cfo_positive: "El negocio genera caja de verdad.",
  roa_improved: "Cada año saca más de sus activos.",
  earnings_quality: "El flujo de caja llega al beneficio contable.",
  debt_reduced: "No se apalanca más.",
  current_ratio_improved: "Más margen para pagar a corto plazo.",
  no_dilution: "No emite acciones nuevas.",
  gross_margin_improved: "Vende con más margen.",
  asset_turnover_improved: "Usa mejor sus activos para vender.",
};
