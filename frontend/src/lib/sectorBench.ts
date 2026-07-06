// Benchmarks sectoriales aproximados (medianas de la industria) usados para
// contextualizar métricas en la UI. Espejo de _get_sector_benchmarks del
// backend (main.py) — mantener ambos en sincronía.

export interface SectorBenchmarks {
  pe: number; forward_pe: number; pb: number; ev_ebitda: number; pfcf: number; peg: number;
  roe: number; roa: number; roic: number; net_margin: number; operating_margin: number; gross_margin: number;
  current_ratio: number; de: number; interest_coverage: number; fcf_yield: number;
  revenue_growth: number; earnings_growth: number;
}

const DEFAULTS: SectorBenchmarks = {
  pe: 22, forward_pe: 18, pb: 3.5, ev_ebitda: 14, pfcf: 25, peg: 1.5,
  roe: 0.15, roa: 0.06, roic: 0.10, net_margin: 0.10, operating_margin: 0.15, gross_margin: 0.40,
  current_ratio: 1.5, de: 0.8, interest_coverage: 8, fcf_yield: 0.04,
  revenue_growth: 0.08, earnings_growth: 0.10,
};

const SECTOR_MAP: Record<string, Partial<SectorBenchmarks>> = {
  technology: { pe: 30, forward_pe: 25, pb: 8, ev_ebitda: 20, roe: 0.25, roa: 0.10, roic: 0.18, net_margin: 0.20, operating_margin: 0.25, gross_margin: 0.60, revenue_growth: 0.15, earnings_growth: 0.18 },
  healthcare: { pe: 25, forward_pe: 20, pb: 4, ev_ebitda: 16, roe: 0.18, net_margin: 0.15, gross_margin: 0.55, revenue_growth: 0.10 },
  financials: { pe: 13, forward_pe: 11, pb: 1.5, roe: 0.12, roa: 0.01, de: 2.5, net_margin: 0.25, current_ratio: 0, interest_coverage: 0 },
  consumer_cyclical: { pe: 20, forward_pe: 17, pb: 5, ev_ebitda: 13, roe: 0.20, net_margin: 0.08, gross_margin: 0.35, revenue_growth: 0.08 },
  consumer_defensive: { pe: 23, forward_pe: 20, pb: 6, ev_ebitda: 16, roe: 0.25, net_margin: 0.08, gross_margin: 0.35, de: 1.2, revenue_growth: 0.05, earnings_growth: 0.06 },
  communication: { pe: 18, forward_pe: 16, pb: 3, ev_ebitda: 10, roe: 0.12, net_margin: 0.12, gross_margin: 0.55 },
  energy: { pe: 10, forward_pe: 9, pb: 1.8, ev_ebitda: 6, roe: 0.15, net_margin: 0.08, de: 0.5, revenue_growth: 0.03 },
  industrials: { pe: 20, forward_pe: 18, pb: 4, ev_ebitda: 13, roe: 0.18, net_margin: 0.08, gross_margin: 0.30, revenue_growth: 0.06 },
  utilities: { pe: 18, forward_pe: 16, pb: 1.8, ev_ebitda: 12, roe: 0.10, de: 1.5, net_margin: 0.12, revenue_growth: 0.03 },
  real_estate: { pe: 35, forward_pe: 30, pb: 2.0, ev_ebitda: 20, roe: 0.06, de: 1.0, net_margin: 0.20 },
  materials: { pe: 14, forward_pe: 12, pb: 2, ev_ebitda: 8, roe: 0.12, net_margin: 0.08, de: 0.6 },
};

export function getSectorBenchmarks(sector: string): SectorBenchmarks {
  const key = sector.toLowerCase().replace(/[\s-]+/g, "_");
  return { ...DEFAULTS, ...(SECTOR_MAP[key] || {}) };
}
