// GENERADO por backend/tools/gen_frontend_config.py desde backend/config/.
// NO EDITAR A MANO: cambia el TOML y vuelve a ejecutar el generador.
// tests/test_frontend_config_sync.py falla si este archivo se desincroniza.

/** Medianas sectoriales PROVISIONALES (sectors.toml [benchmarks]). */
export interface SectorBenchmarks { pe: number; forward_pe: number; pb: number; ev_ebitda: number; pfcf: number; peg: number; roe: number; roa: number; roic: number; net_margin: number; operating_margin: number; gross_margin: number; current_ratio: number; de: number; interest_coverage: number; fcf_yield: number; revenue_growth: number; earnings_growth: number; }

export const SECTOR_DEFAULTS: SectorBenchmarks = {
  pe: 22,
  forward_pe: 18,
  pb: 3.5,
  ev_ebitda: 14,
  pfcf: 25,
  peg: 1.5,
  roe: 0.15,
  roa: 0.06,
  roic: 0.1,
  net_margin: 0.1,
  operating_margin: 0.15,
  gross_margin: 0.4,
  current_ratio: 1.5,
  de: 0.8,
  interest_coverage: 8,
  fcf_yield: 0.04,
  revenue_growth: 0.08,
  earnings_growth: 0.1,
};

export const SECTOR_MAP: Record<string, Partial<SectorBenchmarks>> = {
  technology: { pe: 30, forward_pe: 25, pb: 8, ev_ebitda: 20, roe: 0.25, roa: 0.1, roic: 0.18, net_margin: 0.2, operating_margin: 0.25, gross_margin: 0.6, revenue_growth: 0.15, earnings_growth: 0.18 },
  healthcare: { pe: 25, forward_pe: 20, pb: 4, ev_ebitda: 16, roe: 0.18, net_margin: 0.15, gross_margin: 0.55, revenue_growth: 0.1 },
  financials: { pe: 13, forward_pe: 11, pb: 1.5, roe: 0.12, roa: 0.01, de: 2.5, net_margin: 0.25, current_ratio: 0, interest_coverage: 0 },
  consumer_cyclical: { pe: 20, forward_pe: 17, pb: 5, ev_ebitda: 13, roe: 0.2, net_margin: 0.08, gross_margin: 0.35, revenue_growth: 0.08 },
  consumer_defensive: { pe: 23, forward_pe: 20, pb: 6, ev_ebitda: 16, roe: 0.25, net_margin: 0.08, gross_margin: 0.35, de: 1.2, revenue_growth: 0.05, earnings_growth: 0.06 },
  communication: { pe: 18, forward_pe: 16, pb: 3, ev_ebitda: 10, roe: 0.12, net_margin: 0.12, gross_margin: 0.55 },
  energy: { pe: 10, forward_pe: 9, pb: 1.8, ev_ebitda: 6, roe: 0.15, net_margin: 0.08, de: 0.5, revenue_growth: 0.03 },
  industrials: { pe: 20, forward_pe: 18, pb: 4, ev_ebitda: 13, roe: 0.18, net_margin: 0.08, gross_margin: 0.3, revenue_growth: 0.06 },
  utilities: { pe: 18, forward_pe: 16, pb: 1.8, ev_ebitda: 12, roe: 0.1, de: 1.5, net_margin: 0.12, revenue_growth: 0.03 },
  real_estate: { pe: 35, forward_pe: 30, pb: 2.0, ev_ebitda: 20, roe: 0.06, de: 1.0, net_margin: 0.2 },
  materials: { pe: 14, forward_pe: 12, pb: 2, ev_ebitda: 8, roe: 0.12, net_margin: 0.08, de: 0.6 },
};

/** Niveles del score: Excelente / Favorable / Neutral / Precaución / Evitar (thresholds.toml [score.total]). */
export const SCORE_LEVEL_BANDS = [80, 60, 40, 20] as const;

/** Piotroski F-Score: Fuerte / Bueno / Neutral / Débil / Crítico (valuation.toml [models.piotroski]). */
export const PIOTROSKI_BANDS = [8, 6, 4, 2] as const;

/** Bandas de color de la UI (thresholds.toml [ui.metric_scale]). */
export const METRIC_SCALE_HIGHER: Record<string, [number, number]> = {
  roe: [0.15, 0.1],
  roa: [0.08, 0.05],
  roic: [0.12, 0.08],
  gross_margin: [0.4, 0.2],
  operating_margin: [0.15, 0.1],
  net_margin: [0.1, 0.05],
  ebitda_margin: [0.15, 0.1],
  fcf_yield: [0.05, 0.03],
  earnings_yield: [0.06, 0.03],
  revenue_growth: [0.08, 0.02],
  earnings_growth: [0.08, 0.02],
  current_ratio: [1.5, 1.0],
  quick_ratio: [1.0, 0.5],
  cash_ratio: [0.5, 0.2],
  interest_coverage: [5, 2],
};

export const METRIC_SCALE_LOWER: Record<string, [number, number]> = {
  pe: [15, 25],
  forward_pe: [15, 25],
  pb: [1, 3],
  ps: [2, 5],
  pfcf: [15, 25],
  p_fcf: [15, 25],
  ev_ebitda: [10, 15],
  peg: [1, 1.5],
  de: [0.5, 1.0],
  debt_to_assets: [0.3, 0.5],
  net_debt_to_ebitda: [1.5, 3.0],
};

/** Arquetipos (etapa 6, sectors.toml [archetypes.not_applicable]): componentes que no aplican. */
export type Archetype = "FINANCIAL" | "REIT" | "GROWTH_PRE_PROFIT" | "CYCLICAL" | "MATURE";

export const ARCHETYPE_NOT_APPLICABLE: Record<Archetype, readonly string[]> = {
  FINANCIAL: ["piotroski", "altman", "ocf", "fcf", "fcf_to_ni", "de", "ev_ebitda", "dcf", "graham", "pe", "peg", "forward_pe", "p_fcf", "garp", "current_ratio", "interest_coverage", "net_debt_ebitda", "roic_wacc", "operating_margin", "fcf_growth", "roce"],
  REIT: ["altman", "piotroski", "fcf_to_ni", "garp", "pe", "peg", "forward_pe", "p_fcf", "dcf", "roce"],
  GROWTH_PRE_PROFIT: ["pe", "peg", "forward_pe", "graham", "eps_growth"],
  CYCLICAL: ["pe", "peg", "forward_pe", "fcf_growth"],
  MATURE: [],
};

export const METRIC_SCALE_SPECIAL = {
  dividend_yield: [0.02, 0.01] as const,
  payout_ratio: [0.3, 0.6, 0.8] as const,
  buyback_yield: [0.005, -0.005] as const,
  shareholder_yield: [0.01, 0] as const,
  beta: [0.8, 1.2, 1.5] as const,
};
