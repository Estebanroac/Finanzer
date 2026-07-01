const API_BASE = process.env.NEXT_PUBLIC_API_URL || (typeof window !== "undefined" && window.location.hostname !== "localhost" ? "" : "http://localhost:8000");

export interface SearchResult {
  ticker: string;
  name: string;
  score: number;
}

export interface ScoreAdjustment {
  metric: string;
  value: string;
  adjustment: number;
  reason: string;
  severity: string;
}

export interface ScoreBreakdownCategory {
  score: number;
  max: number;
  details: string[];
  adjustments?: ScoreAdjustment[];
}

export interface StockAnalysis {
  symbol: string;
  profile: {
    name: string;
    sector: string;
    industry: string;
    country: string;
    currency: string;
    exchange: string;
    market_cap: number | null;
    description: string;
  };
  price: number | null;
  key_metrics: Record<string, number | null>;
  ratios: Record<string, number | null>;
  score: {
    total_score: number;
    max_score: number;
    level: string;
    breakdown: Record<string, ScoreBreakdownCategory>;
  } | null;
  company_type: string;
  is_growth: boolean;
  sector_info: { sector: string; mapped_sector: string; sector_etf: string };
  altman_z: { z_score: number; zone: string; interpretation: string; model?: string; details?: Record<string, unknown> } | null;
  piotroski_f: { score: number; max_score: number; level: string; interpretation: string; details?: Record<string, { passed: boolean; detail: string }>; fiscal_year?: string } | null;
  financial_health: { score: number; level: string } | null;
  graham_number: number | null;
  graham_margin: number | null;
  dcf: {
    fair_value: number | null;
    wacc: number | null;
    growth_rate: number | null;
    terminal_growth: number | null;
    margin_of_safety: number | null;
    upside: number | null;
    value_composition: Record<string, number> | null;
  } | null;
  sensitivity: {
    // Cells are null where the DCF is undefined for that scenario
    // (e.g. discount_rate <= terminal_growth). Consumers must guard for null.
    matrix: (number | null)[][];
    growth_rates: number[];
    discount_rates: number[];
    base_growth_idx: number;
    base_discount_idx: number;
    statistics: { min: number; max: number; median: number };
  } | null;
  alerts: {
    red_flags: Array<{ category: string; reason: string; detail: string }>;
    warnings: Array<{ category: string; reason: string; detail: string }>;
    strengths: Array<{ category: string; reason: string; detail: string }>;
  } | null;
  price_history: { "52w_high": number | null; "52w_low": number | null; beta: number | null } | null;
  yearly_financials?: Array<{ year: number; revenue: number | null; earnings: number | null }>;
  errors: string[];
}

export async function searchStocks(query: string): Promise<SearchResult[]> {
  const res = await fetch(`${API_BASE}/api/search?q=${encodeURIComponent(query)}`);
  if (!res.ok) return [];
  return res.json();
}

export async function analyzeStock(symbol: string): Promise<StockAnalysis> {
  const res = await fetch(`${API_BASE}/api/analysis/${encodeURIComponent(symbol)}`);
  if (!res.ok) {
    throw new Error(`Failed to analyze ${symbol}: ${res.status}`);
  }
  return res.json();
}

export async function getPopularStocks(): Promise<{ ticker: string; name: string }[]> {
  const res = await fetch(`${API_BASE}/api/stocks/popular`);
  if (!res.ok) return [];
  return res.json();
}

// ── Formatting helpers ──

export function formatNumber(val: number | null | undefined): string {
  if (val == null || !Number.isFinite(val)) return "N/A";
  const abs = Math.abs(val);
  const sign = val < 0 ? "-" : "";
  if (abs >= 1e12) return `${sign}$${(abs / 1e12).toFixed(2)}T`;
  if (abs >= 1e9) return `${sign}$${(abs / 1e9).toFixed(2)}B`;
  if (abs >= 1e6) return `${sign}$${(abs / 1e6).toFixed(2)}M`;
  if (abs >= 1e3) return `${sign}$${(abs / 1e3).toFixed(1)}K`;
  return `${sign}$${abs.toFixed(2)}`;
}

export function formatPercent(val: number | null | undefined): string {
  if (val == null || !Number.isFinite(val)) return "N/A";
  // All ratios reach here as decimals (0.15 = 15%, 1.3 = 130%), so always
  // scale by 100. The old `< 1` heuristic left any value ≥ 100% unscaled — a
  // 130% payout ratio rendered as "1.30%" and a 200% ROE as "2.00%", hiding
  // exactly the extreme readings (unsustainable dividends, huge returns) a
  // reader most needs to see.
  return `${(val * 100).toFixed(2)}%`;
}

export function formatMultiple(val: number | null | undefined): string {
  if (val == null || !Number.isFinite(val)) return "N/A";
  return `${val.toFixed(2)}x`;
}

export function formatPrice(val: number | null | undefined): string {
  if (val == null || !Number.isFinite(val)) return "N/A";
  return `$${val.toFixed(2)}`;
}

export function getScoreColor(pct: number): string {
  if (pct >= 80) return "#00d632";
  if (pct >= 65) return "#4ade80";
  if (pct >= 50) return "#fbbf24";
  if (pct >= 35) return "#f97316";
  return "#ff4d4d";
}

export function getScoreLabel(pct: number): string {
  if (pct >= 80) return "Excelente";
  if (pct >= 65) return "Favorable";
  if (pct >= 50) return "Neutral";
  if (pct >= 35) return "Precaución";
  return "Evitar";
}
