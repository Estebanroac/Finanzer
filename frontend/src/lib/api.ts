import type { Archetype } from "./generated/backendConfig";

export type { Archetype };

// Solo el dev server de Next (puerto 3000) necesita apuntar al backend en
// localhost:8000; en cualquier otro caso (producción en Render, uvicorn local
// sirviendo el export estático, proxies) la API es same-origin.
const API_BASE = process.env.NEXT_PUBLIC_API_URL ||
  (typeof window !== "undefined" && window.location.port === "3000" ? "http://localhost:8000" : "");

export interface SearchResult {
  ticker: string;
  name: string;
  score: number;
}

/* ══════════════════════════════════════════════════════════════════════════
   Contrato con el backend (etapa 9b)
   La web NO decide nada de análisis: pinta el bloque `display` que calcula
   backend/lib/display.py, el mismo que maqueta el PDF. Estos tipos son el
   contrato: scripts/check-contract.mjs falla si declaran un campo que el
   backend no expone, y tsc impide leer un campo que no esté aquí.
   ══════════════════════════════════════════════════════════════════════════ */

export type Tone = "pos" | "neg" | "warn" | "neu";
export type RowState = "con_dato" | "sin_dato" | "no_aplica" | "no_significativo";

export interface Reading {
  label: string;
  tone: Tone;
  text: string;
}

/** Fila de una tabla de sección (múltiplos, rentabilidad, solidez, crecimiento…). */
export interface Row {
  key: string;
  label: string;
  value: string;
  bench: string | null;
  gap: string | null;
  reading: string;
  tone: Tone | null;
  state: RowState;
  text: string | null;
}

export interface ScoreBlock {
  title: string;
  question: string;
  score: number | null;
  level: string | null;
  tone: Tone;
  note: string | null;
}

export interface PriceBlock extends ScoreBlock {
  raw: number | null;
  contracted: boolean;
}

export interface CategoryItem {
  name: string;
  score: number;
  max: number;
  pct: number;
  tone: Tone;
  conclusive: boolean;
  coverage: number | null;
  applicable: boolean;
  text: string | null;
}

export interface Kpi {
  key: string;
  label: string;
  value: string;
  state: RowState;
}

export interface Highlight {
  kind: string;
  kicker: string;
  text: string;
  tone: Tone;
}

export interface Cover {
  /** Etapa 11b: conversión de moneda y clase de acciones aplicada a los estados (o null). */
  currency_note: string | null;
  /** Fase 2b: fecha de los estados del análisis (corte), o null. */
  as_of_note: string | null;
  /** Fase 2b: avisos de datos (resultados publicados y aún no incorporados; datos de otro periodo descartados). */
  data_notices: string[];
  /** Fase 2b (D7): insignia "Sin fuente oficial" junto a la confianza (emisor sin estados en la SEC), o null. */
  official_source_badge: { label: string; tooltip: string } | null;
  archetype: string;
  archetype_label: string;
  classification_notes: string[];
  quality: ScoreBlock;
  price: PriceBlock;
  categories: Array<{ title: string; items: CategoryItem[] }>;
  verdict: { text: string; full: string | null; confidence_text: string | null; confidence_tone: Tone };
  confidence_reasons: string[];
  coverage_notes: string[];
  kpis: Kpi[];
  highlights: Highlight[];
}

export interface MetricCard {
  key: string;
  label: string;
  value: string;
  unit: string;
  pill: string;
  tone: Tone;
  delta: string;
  bench: string;
  state: RowState;
}

/** Fila de la composición: barra de categoría, categoría no concluyente o ajuste ± de Valoración. */
export type CompositionRow =
  | { label: string; kind: "bar"; value: number; max: number; pct: number; tone: Tone }
  | { label: string; kind: "nc" }
  | { label: string; kind: "signed"; value: number; tone: Tone };

export interface CompositionBlock {
  title: string;
  score: number | null;
  level: string | null;
  tone: Tone;
  note: string | null;
}

export interface Summary {
  cards: MetricCard[];
  exec_items: Array<{ label: string; text: string }>;
  composition: {
    quality: CompositionBlock & { rows: Array<Extract<CompositionRow, { kind: "bar" | "nc" }>> };
    price: CompositionBlock & { rows: Array<Extract<CompositionRow, { kind: "signed" }>>; signed_max: number };
    caption: string;
  };
  alert_counts: { red_flags: number; warnings: number; strengths: number };
}

export interface ConfidenceReason {
  dimension: string;
  level: string;
  text: string | null;
}

export interface Confidence {
  level: string;
  tone: Tone;
  verdict_text: string | null;
  plain: string[];
  reasons: ConfidenceReason[];
  dimensions: Array<{ key: string; label: string; level: string; text: string }>;
  summary: string;
}

export interface SensitivityCell {
  value: string;
  band: number | null;
  base: boolean;
}

export interface Sensitivity {
  intro: string;
  corner: string;
  columns: string[];
  rows: Array<{ label: string; cells: SensitivityCell[] }>;
  base_growth_idx: number | null;
  base_discount_idx: number | null;
  band_labels: string[];
  note: string | null;
}

export interface Range52 {
  pos: number;
  low: string;
  high: string;
  price: string;
  zones: Array<{ from: number; to: number }>;
  axis: string;
  reading: Reading | null;
  caption: string;
  zones_note: string;
}

export interface InstitutionalCard {
  key: string;
  value: string;
  tone: Tone;
  title: string;
  subtitle: string;
  state: RowState;
  body: string;
}

export interface BreakdownItem {
  metric: string;
  value: string;
  sign: string;
  tone: Tone;
  reason: string;
  in_block: boolean;
  state: RowState;
}

export interface BreakdownCategory {
  name: string;
  score: number;
  max: number;
  pct: number;
  tone: Tone;
  conclusive: boolean;
  group: "quality" | "price" | null;
  text: string | null;
  items: BreakdownItem[];
}

export interface AlertItem {
  category: string;
  reason: string;
  detail: string;
}

/** Fase 3 (T6): lectura de calidad que informa y no puntúa (DuPont, margen FCF, regla de 40, cobertura…). */
export interface QualityReading { key: string; label: string; text: string; tone: Tone }

export interface Sections {
  valuation: {
    intro: string | null;
    columns: string[];
    rows: Row[];
    market_note: string | null;
    provisional_note: string | null;
    normalization_note: string | null;
    intrinsic: { intro: string | null; rows: Row[]; graham_note: string | null };
    dcf_params: string | null;
    dcf_reliability: string | null;
    dcf_reliability_level: string | null;
    dcf_reliability_tone: Tone | null;
    dcf_missing: string | null;
    reverse_dcf: {
      title: string;
      lines: Array<{ text: string; label: string | null; tone: Tone }>;
      role: string;
      method: string;
    } | null;
    premortem?: { title: string; items: string[]; note: string } | null;
    ke_note: string | null;
    wacc_note: string | null;
    wacc_breakdown: Array<{ label: string; value: string }> | null;
    sensitivity: Sensitivity | null;
  };
  profitability: {
    intro: string | null;
    columns: string[];
    rows: Row[];
    divergence_note: string | null;
    roce_reading: string | null;
    figures: string[][];
    quality_readings?: QualityReading[];
  };
  solvency: { intro: string | null; columns: string[]; rows: Row[]; balance: string;
    quality_readings?: QualityReading[] };
  growth: {
    intro: string | null;
    columns: string[];
    rows: Row[];
    eps_vs_revenue_note: string | null;
    score_components: Array<{ metric: string; value: string; reason: string }>;
    range52: Range52 | null;
  };
  /** Fase 5 (D5): contexto de mercado y lectura conductual; no puntúa. */
  market?: {
    title: string;
    note: string;
    rows: Array<{ key: string; label: string; value: string; text: string; tone: Tone }>;
    status_note: string | null;
    behavioral_title: string;
    behavioral: string[];
    news: Array<{ date: string | null; source: string | null; headline: string; url: string | null }>;
    news_note: string | null;
    pead_note: string;
    source: string;
  } | null;
  institutional: {
    cards: InstitutionalCard[];
    piotroski_criteria: Array<{ key: string; label: string; detail: string; status: string; tone: Tone }>;
    breakdown: { intro: string; coverage_notes: string[]; categories: BreakdownCategory[] } | null;
  };
  /** Histórico (dato bruto): columnas que no aplican al arquetipo y su texto. */
  historical: { not_applicable: Record<string, string> };
  alerts: {
    counts: { red_flags: number; warnings: number; strengths: number };
    groups: Array<{ key: string; title: string; tone: Tone; items: AlertItem[] }>;
  };
}

export interface BandTable {
  title: string;
  bands: Array<{ range: string; label: string; tone: Tone }>;
}

/** Bandas aplicadas a esta empresa (arquetipo y benchmark), desde la config del score. */
export interface MetricBands {
  tables: BandTable[];
  note: string | null;
}

/* ── Etapa 9c: datos de los gráficos (display.charts) ──
   Cada gráfico trae su valor, su referencia, sus zonas (de la misma config que las
   lecturas) y su tono; si no hay dato, `state` y el motivo en `text`. */

/** Tramo de una escala: [from, to] en las unidades del eje, con su lectura y tono. */
export interface Zone {
  from: number;
  to: number;
  label: string;
  tone: Tone;
}

/** Métrica frente a la referencia (sector o mercado): barra con marcador y chip de brecha. */
export interface VsBench {
  key: string;
  label: string;
  higher_is_better: boolean;
  fmt: "mult" | "pct";
  state: RowState;
  text: string | null;
  value?: number;
  value_txt?: string;
  bench?: number | null;
  bench_txt?: string | null;
  gap_txt?: string | null;
  gap_pct?: number | null;
  reading?: string;
  tone?: Tone | null;
}

/** Múltiplo de Valoración con su papel en el score: miembro del bloque, puntúa aparte o informativo (no puntúa). */
export interface Multiple extends VsBench {
  role: "block" | "scored" | "informative";
}

/** Métrica que puntúa en Valoración sin barra frente a la referencia (normalizados, P/B vs ROE, P/FFO…). */
export interface ScoredItem {
  key: string;
  label: string;
  in_block: boolean;
  value_txt: string | null;
  reading: string | null;
  tone: Tone | null;
  sign: string | null;
  reason: string | null;
}

export interface FairValueChart {
  state: RowState;
  text: string | null;
  /** Método de la escala (la insignia y el título lo nombran). */
  method?: string;
  price?: number;
  fair_value?: number;
  grid_low?: number | null;
  grid_high?: number | null;
  price_txt?: string;
  fair_value_txt?: string;
  grid_low_txt?: string | null;
  grid_high_txt?: string | null;
  axis?: number[];
  zones?: Zone[];
  badge?: { label: string; tone: Tone };
  upside_txt?: string;
  reliability?: string | null;
  reliability_tone?: Tone | null;
}

export interface GaugeChart {
  key: string;
  label: string;
  state: RowState;
  text: string | null;
  value?: number | null;
  value_txt?: string;
  axis_max?: number;
  clamped?: boolean;
  zones?: Zone[];
  unit?: string;
  reading?: string;
  tone?: Tone | null;
  /** Deuda neta negativa: caja neta (no se sitúa en la escala). */
  net_cash?: boolean;
  /** Cobertura negativa (EBIT < 0): no se sitúa en la escala. */
  negative?: boolean;
  /** D/E informativo (REIT): sin zonas ni juicio. */
  informative?: boolean;
}

export interface RunwayChart {
  state: RowState;
  text: string | null;
  years?: number;
  years_txt?: string;
  axis_max?: number;
  zones?: Zone[];
  self_funded?: boolean;
  reading?: string;
  tone?: Tone;
}

export interface StructureChart {
  state: RowState;
  assets?: number;
  debt?: number | null;
  equity?: number | null;
  cash?: number | null;
  net_debt?: number | null;
  debt_pct?: number | null;
  equity_pct?: number | null;
  cash_pct?: number | null;
  assets_txt?: string | null;
  debt_txt?: string | null;
  equity_txt?: string | null;
  cash_txt?: string | null;
  net_debt_txt?: string | null;
}

export interface LadderStep {
  key: string;
  label: string;
  state: RowState;
  text?: string | null;
  pct?: number;
  pct_txt?: string;
  amount?: number | null;
  amount_txt?: string | null;
  tone?: Tone | null;
  reading?: string | null;
}

export interface GrowthBar {
  key: string;
  label: string;
  state: RowState;
  text?: string | null;
  value?: number;
  value_txt?: string;
  tone?: Tone;
  reading?: string;
  /** Negativo en todos los ejercicios: sin tasa, puntúa en el peor tramo. */
  sustained_negative?: boolean;
}

export interface FlowItem {
  key: string;
  label: string;
  state: RowState;
  text?: string | null;
  amount?: number | null;
  amount_txt?: string | null;
  pct_of_revenue?: number | null;
  pct_txt?: string | null;
  sign?: "pos" | "neg" | null;
}

export interface HistSeries {
  key: string;
  label: string;
  state: RowState;
  text?: string | null;
  cagr?: number | null;
  cagr_txt?: string | null;
  points?: Array<{ year: number; value: number | null; value_txt: string; yoy_pct: number | null; yoy_txt: string | null }>;
}

export interface AltmanChart {
  state: RowState;
  text: string | null;
  value?: number;
  value_txt?: string;
  model?: string;
  axis_max?: number;
  zones?: Zone[];
  zone?: string | null;
}

export interface ComparisonItem {
  key: string;
  label: string;
  fmt: "mult" | "pct";
  value: number;
  bench: number;
  value_txt: string;
  bench_txt: string;
  gap_pct: number;
  gap_txt: string | null;
  higher_is_better: boolean;
  reading: string;
  tone: Tone;
  text: string;
}

export interface Charts {
  version: number;
  price_card: {
    price: number | null;
    price_txt: string;
    currency: string | null;
    exchange: string | null;
    from_high_pct: number | null;
    from_high_txt: string | null;
    low: number | null;
    high: number | null;
    low_txt: string | null;
    high_txt: string | null;
  };
  valuation: {
    fair_value: FairValueChart;
    multiples: Multiple[];
    /** Línea del bloque de múltiplos del desglose (ajuste total) o null. */
    block: { label: string; sign: string; tone: Tone; reason: string } | null;
    scored: ScoredItem[];
    dcf_composition: { explicit_pct: number; terminal_pct: number } | null;
  };
  profitability: {
    returns: VsBench[];
    margins: VsBench[];
    spread: { state: RowState; text: string | null; value?: number; value_txt?: string; tone?: Tone; reading?: string };
    /** Fase 1: ROCE visible junto a ROIC − WACC; la lectura es la comparación con el ROIC (sin bandas). */
    roce: {
      state: RowState; text: string | null; value_txt?: string; label?: string; basis?: string;
      avg?: { label: string; value_txt: string; years: number; incomplete: boolean } | null;
    };
    margin_ladder: { revenue: number | null; revenue_txt: string | null; steps: LadderStep[] };
  };
  solvency: { gauges: GaugeChart[]; runway: RunwayChart | null; structure: StructureChart };
  growth: GrowthBar[];
  results_flow: FlowItem[];
  historical: { years: number; series: HistSeries[] };
  institutional: { altman: AltmanChart };
  comparison: {
    groups: Array<{ title: string; items: ComparisonItem[] }>;
    better: number;
    total: number;
    ref: string;
    note: string;
    market_note: string | null;
  };
}

export interface Display {
  version: number;
  archetype: string;
  archetype_label: string;
  na_keys: string[];
  benchmark: { profile: "market" | "sector"; ref: string; column: string; vs: string; thresholds_key: string };
  readings: Record<string, Reading | null>;
  cover: Cover;
  summary: Summary;
  confidence: Confidence | null;
  /** Fase 1 (D1): códigos y motivos técnicos para el anexo del PDF; la web no lo muestra. */
  annex: { title: string; items: Array<{ label: string; text: string }> };
  sections: Sections;
  methodology: { models: string[]; models_text: string };
  tooltips: Record<string, MetricBands>;
  charts: Charts;
}

/** Fila del histórico anual: dato bruto de los estados (sin lecturas ni colores). */
export interface YearRow {
  year: number;
  revenue: number | null;
  net_income: number | null;
  free_cash_flow: number | null;
  gross_margin: number | null;
  operating_margin: number | null;
  net_margin: number | null;
  fcf_margin: number | null;
  sbc?: number | null;
  fcf_minus_sbc?: number | null;
  fcf_minus_sbc_margin?: number | null;
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
  };
  price: number | null;
  classification: { archetype: Archetype; reason: string };
  display: Display;
  yearly_financials: YearRow[];
  errors: string[];
}

export async function searchStocks(query: string): Promise<SearchResult[]> {
  const res = await fetch(`${API_BASE}/api/search?q=${encodeURIComponent(query)}`);
  if (!res.ok) return [];
  return res.json();
}

/** 422: el backend no analiza el símbolo y explica por qué (ETF o fondo; estados sin tipo de cambio). */
const HTTP_NOT_ANALYZABLE = 422;

export async function analyzeStock(symbol: string): Promise<StockAnalysis> {
  const res = await fetch(`${API_BASE}/api/analysis/${encodeURIComponent(symbol)}`);
  if (!res.ok) {
    // 422: el backend explica por qué no analiza (ETF o fondo, estados sin tipo de cambio):
    // ese motivo se muestra tal cual.
    let detail: string | null = null;
    try {
      const body = await res.json();
      if (typeof body?.detail === "string") detail = body.detail;
    } catch {
      /* respuesta sin JSON */
    }
    throw new Error(res.status === HTTP_NOT_ANALYZABLE && detail ? detail : `Failed to analyze ${symbol}: ${res.status}`);
  }
  return res.json();
}

/** URL del PDF: misma regla que API_BASE. */
export function pdfUrl(symbol: string): string {
  return `${API_BASE}/api/pdf/${encodeURIComponent(symbol)}`;
}

// ── Formato de dato bruto (histórico): sin juicio, solo unidades ──
const UNITS: Array<[number, string]> = [[1e12, "T"], [1e9, "B"], [1e6, "M"], [1e3, "K"]];

export function formatMoney(val: number | null | undefined): string {
  if (val == null || !Number.isFinite(val)) return "—";
  const abs = Math.abs(val);
  const sign = val < 0 ? "−" : "";
  for (const [div, suffix] of UNITS) {
    if (abs >= div) return `${sign}$${(abs / div).toFixed(2)}${suffix}`;
  }
  return `${sign}$${abs.toFixed(2)}`;
}

export function formatPct(val: number | null | undefined): string {
  if (val == null || !Number.isFinite(val)) return "—";
  return `${(val * 100).toFixed(1)}%`;
}

export function formatPrice(val: number | null | undefined): string {
  if (val == null || !Number.isFinite(val)) return "—";
  return `$${val.toFixed(2)}`;
}
