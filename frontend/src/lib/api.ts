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
  /** V4-F8: la nota en forma corta para la cabecera; la frase completa (`note`) va en el desglose de «La empresa». */
  note_short?: string | null;
}

export interface PriceBlock extends ScoreBlock {
  raw: number | null;
  contracted: boolean;
}

export interface CategoryItem {
  /** Clave del motor ("Solidez Financiera"); `name`, cómo se escribe ([score.category_labels]). */
  key?: string;
  name: string;
  score: number;
  max: number;
  pct: number;
  tone: Tone;
  conclusive: boolean;
  coverage: number | null;
  /** F8 · P3: la puntuación como se muestra («12 / 20» o «no concluyente», que no enseña puntos). */
  score_txt: string;
  applicable: boolean;
  text: string | null;
}

export interface Kpi {
  key: string;
  label: string;
  value: string;
  state: RowState;
  /** V4b: sin dato o no significativa, el porqué (si el análisis lo tiene). */
  text?: string;
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
  /** F10 · B1: sin cifra, su motivo (lib/empty_reasons.py) */
  text?: string | null;
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
  alert_counts: { red_flags: number; warnings: number; strengths: number; /** Fase 1 · pendientes: sin color. */ balance?: number; valuation?: number; /** F9 · R6: «el riesgo de crédito no está medido» (banco). */ unmeasured?: string | null };
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
  /** Clave del motor; `name`, cómo se escribe ([score.category_labels]). */
  key?: string;
  name: string;
  score: number;
  max: number;
  pct: number;
  tone: Tone;
  conclusive: boolean;
  /** F8 · P3: la puntuación como se muestra («12 / 20» o «no concluyente», que no enseña puntos). */
  score_txt: string;
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
    reference_note: string | null;
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
    /** F9 · R3: «Cifras de los últimos doce meses (TTM, a …)» o «Cifras del ejercicio cerrado el … (FY)». */
    figures_title?: string;
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
    counts: { red_flags: number; warnings: number; strengths: number; /** Fase 1 · pendientes: sin color. */ balance?: number; valuation?: number; /** F9 · R6: «el riesgo de crédito no está medido» (banco). */ unmeasured?: string | null };
    groups: Array<{ key: string; title: string; tone: Tone; items: AlertItem[] }>;
  };
  /** F13 · paso 10: riesgos del sector, aparte y sin puntuar (de la empresa, con dato; de su industria, no verificados en ella). */
  sector_risks?: {
    items: Array<{ level: "empresa" | "industria"; key: string; title: string; label: string | null; text: string }>;
    note: string | null;
    not_measured: string | null;
  } | null;
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
  /** F8 · P3: rango del bloque central de la tabla de sensibilidad (mínimo y máximo, declarado; no un p10–p90). */
  central_low?: number | null; central_high?: number | null; central_text?: string | null;
  central_low_txt?: string | null; central_high_txt?: string | null;
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
  /** F9 · R3: «regresión log-lineal: el año inicial es anómalo» cuando la cifra no es el CAGR de punta a punta. */
  cagr_note?: string | null;
  points?: Array<{ year: number; value: number | null; value_txt: string; yoy_pct: number | null; yoy_txt: string | null;
    /** F10 · B1: sin cifra, por qué */ reason?: string | null }>;
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
    /** F9 · R3: `period`, de qué periodo son los ingresos (TTM o FY). */
    margin_ladder: { revenue: number | null; revenue_txt: string | null; period?: { code: "TTM" | "FY"; of: string } | null; steps: LadderStep[] };
  };
  solvency: { gauges: GaugeChart[]; runway: RunwayChart | null; structure: StructureChart };
  growth: GrowthBar[];
  results_flow: FlowItem[];
  /** F9 · R3: `growth_currency_note`, si los crecimientos se miden en la moneda de los estados (ADR). */
  historical: { years: number; series: HistSeries[]; growth_currency_note?: string | null };
  institutional: { altman: AltmanChart };
  comparison: {
    groups: Array<{ title: string; items: ComparisonItem[] }>;
    better: number;
    total: number;
    ref: string;
    note: string | null;
    market_note: string | null;
  };
}

export interface Display {
  version: number;
  archetype: string;
  archetype_label: string;
  na_keys: string[];
  benchmark: { profile: "market" | "sector"; ref: string; column: string; short: string; vs: string; thresholds_key: string };
  readings: Record<string, Reading | null>;
  cover: Cover;
  summary: Summary;
  /** Fase 1 · pendientes (7-nov-2026): la consistencia (dos niveles, «consistente» o «mixta», con la coincidencia de
   *  métodos y la cobertura de datos). */
  consistency?: Confidence | null;
  /** @deprecated Alias de `consistency` durante una versión (mismo contenido); se retira en la siguiente. */
  confidence: Confidence | null;
  /** Fase 1 (D1): códigos y motivos técnicos para el anexo del PDF; la web no lo muestra. */
  annex: { title: string; items: Array<{ label: string; text: string }> };
  /** V7: sector e industria del perfil en español (el original, en el anexo). */
  profile?: { sector: string | null; industry: string | null; country?: string | null };
  sections: Sections;
  methodology: { models: string[]; models_text: string; ratios_text: string };
  tooltips: Record<string, MetricBands>;
  charts: Charts;
  /** Rediseño E2a: datos nuevos del motor, ya formateados, para /v2 (opcional: la web actual no lo lee). */
  extended?: Extended;
}

/** Rediseño E2a: display.extended (backend/lib/display.py, _extended_block). Datos, no lecturas. */
export interface Extended {
  price_change: { status: string; value_txt: string | null; pct_txt: string | null; tone: Tone; session: string | null };
  company_profile: { status: string; rows: Array<{ key: string; label: string; value: string }>; source: string | null; reason: string | null };
  history_10y: {
    status: string; currency: string | null; source: string | null; reason: string | null;
    rows: Array<{ year: number; revenue_txt: string; net_income_txt: string; fcf_txt: string;
                  operating_margin_txt: string; net_margin_txt: string; revenue_growth_txt: string;
                  /** El ejercicio anterior falta en EDGAR: sin crecimiento (no se compara contra dos años atrás). */
                  gap_before: boolean;
                  /** V4b: por qué falta una cifra del ejercicio (claves: operating_margin, diluted_eps, capex, fcf). */
                  reasons: Record<string, string> }>;
  };
  piotroski_values: Array<{ key: string; cur_txt: string | null; prev_txt: string | null; compare: "zero" | "ni" | "prior_year" }>;
  next_earnings: { status: string; date_txt: string | null; kind: "anunciada" | "estimada" | null; basis: string | null; reason: string | null };
  news: Array<ExtendedNews>;
  /** El centro de noticias: los titulares con foto propia primero, por fecha (un análisis guardado antes no lo trae). */
  news_featured?: Array<ExtendedNews>;
}

type ExtendedNews = { date: string | null; datetime: string | null; source: string | null; headline: string; url: string | null;
                      summary: string | null; image: string | null; lang: string | null };

/** Rediseño E2a: supuestos con los que el motor calculó su DCF (escenarios del usuario, POST /api/v2/scenario). */
export interface ScenarioAssumptions {
  high_growth_rate: number; high_growth_years: number; transition_years: number; terminal_growth: number;
  discount_rate: number;
}
/** Supuestos que mueve el usuario en /v2 (E3 añade el margen de flujo de caja). */
export interface ScenarioUserAssumptions {
  high_growth_rate: number; discount_rate: number; terminal_growth: number; fcf_margin: number | null;
}
export interface ScenarioInputs {
  status: string; reason: string | null;
  fcf?: number | null; shares_outstanding?: number | null; net_debt?: number | null; price?: number | null;
  currency?: string | null; base?: ScenarioAssumptions & { decay_type: string | null };
  /** E3: ingresos base del FCF, margen de flujo de caja (FCF / ingresos), arquetipo, límites de cada control y
   *  preajustes (absolutos, dentro de los límites). */
  revenue?: number | null; fcf_margin?: number | null; archetype?: string | null;
  bounds?: { growth: number[]; discount: number[]; terminal: number[]; fcf_margin: number[] | null };
  presets?: { pessimistic: ScenarioUserAssumptions; optimistic: ScenarioUserAssumptions };
  reverse?: { flow_per_share: number; net_debt_per_share: number; rate: number; terminal_growth: number };
}
export interface ScenarioRequest { inputs: ScenarioInputs; assumptions: Partial<ScenarioUserAssumptions & ScenarioAssumptions> }
export interface ScenarioResponse {
  status: string; fair_value: number | null; upside: number | null;
  assumptions_used: (ScenarioAssumptions & { fcf_margin?: number }) | null;
  clamped: string[]; reason: string | null;
  /** E3: qué crecimiento exige el precio con estos supuestos (el DCF inverso del motor). */
  implied_growth: { state: string; g_star: number | null; g10: number | null; side: string | null; reason: string | null } | null;
  /** E3: valor por acción con crecimiento (filas, de menos a más) y WACC (columnas) alrededor de estos supuestos. */
  sensitivity: { growth: number[]; discount: number[]; values: Array<Array<number | null>>; price: number | null;
    /** Revisión V6 (F17): banda de cada celda frente al precio (0 muy por encima … 4 muy por debajo) y su leyenda,
     *  del motor: la misma regla que la sensibilidad del informe. */
    bands?: Array<Array<number | null>>; band_labels?: string[];
    /** V4b · 4: por qué una celda no tiene valor («fuera» de los límites del análisis o «≤ 0»); None si lo tiene. */
    why?: Array<Array<string | null>> } | null;
  /** Revisión V6 (F17): tono del resultado frente al precio, del motor. */
  upside_tone?: Tone | null;
  /** v4: la lectura del escenario con las bandas del DCF del informe (etiqueta y tono del tramo). */
  upside_reading?: { label: string; tone: Tone } | null;
}

/** Rediseño E2a: un ejercicio de la historia de 10 años (dato bruto de EDGAR). */
export interface HistoryRow10 {
  year: number; fy_end: string | null; revenue: number | null; net_income: number | null; free_cash_flow: number | null;
  operating_income: number | null; operating_cash_flow: number | null; capex: number | null; diluted_eps: number | null;
  operating_margin: number | null; net_margin: number | null; revenue_growth: number | null; gap_before: boolean;
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

/** Logotipo de la empresa (backend/lib/logos.py): `url` con su versión (?v=) o, si aún se descargaba, sin ella y
 *  `source` null. Lo añade el endpoint /api/analysis (main._with_logo), no el cálculo del análisis: va fuera de
 *  StockAnalysis y de su contrato con los golden (backend/tests/test_logos.py lo comprueba). null: no hay logotipo. */
export interface CompanyLogoInfo { url: string; source: string | null }
export type AnalysisWithLogo = StockAnalysis & { logo?: CompanyLogoInfo | null };

export interface StockAnalysis {
  symbol: string;
  profile: {
    name: string;
    sector: string;
    industry: string;
    country: string;
    currency: string;
    exchange: string;        // E2a: nombre de la bolsa ("Nasdaq"), no el código del proveedor
    exchange_code: string;   // E2a: código original del proveedor ("NMS")
  };
  price: number | null;
  classification: { archetype: Archetype; reason: string };
  display: Display;
  yearly_financials: YearRow[];
  errors: string[];
  /** Rediseño E2a: opcional; la web actual no lo lee (E3: escenarios). */
  scenario_inputs?: ScenarioInputs;
  /** Rediseño E2a: historia de 10 ejercicios de EDGAR (dato bruto, como yearly_financials); E3 la dibuja. */
  history_10y?: { status: string; currency: string | null; source: string | null; reason: string | null;
                  rows: HistoryRow10[] };
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

/** Rediseño E5: el informe PDF nuevo (lib/pdf_v2). Lo usa /v2; la web actual sigue con `pdfUrl`. */
export function pdfV2Url(symbol: string): string {
  return `${API_BASE}/api/v2/pdf/${encodeURIComponent(symbol)}`;
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

// ── Rediseño E2b: datos nuevos de /api/v2 (aditivos; sin UI hasta E3/E4). Formas exactas de los endpoints. ──

/** Un segmento: ingresos por ejercicio fiscal ("2025" = año del fin del ejercicio) y su peso en el último. */
export interface SegmentItem {
  member: string;
  label: string;
  values: Record<string, number>;
  share_last: number;
}

export interface SegmentAxis {
  axis: string;
  axis_label: string;
  concept: string;
  segments: SegmentItem[];
  reconciles: boolean;
  gap_pct: number | null;
  notes: string[];
}

/** GET /api/v2/segments/{symbol} (backend/lib/segments.py). Sin desglose: status "sin_dato" y `reason`. */
/** V7 · P2, P4: hechos de los segmentos ya formateados por el backend (segments.summary). */
export interface SegmentsSummaryLine { axis: string | null; axis_label: string | null; items: Array<{ label: string; share: number; share_txt: string }>; more: number }
export interface SegmentsSummary {
  fy: string; prev_fy: string | null; concept_label: string | null; covers_total: boolean | null; coverage_note: string | null;
  first: SegmentsSummaryLine; second: SegmentsSummaryLine | null;
  /** La frase del capítulo 2 (y del PDF) y la segunda línea (geografía), del backend. */
  text: string | null; second_text: string | null;
  top: { label: string; share: number; share_txt: string; axis_label: string | null } | null;
  falling: Array<{ label: string; change: number; change_txt: string; axis_label: string | null }>;
  source: { form: string; filed: string; accn: string; period_end: string | null } | null;
}
export interface SegmentsResponse {
  summary?: SegmentsSummary | null;
  status: "ok" | "sin_dato";
  fiscal_years: string[];
  axis: string | null;
  axis_label: string | null;
  concept: string | null;
  /** El concepto en español ("Ingresos", "Comisiones"…). */
  concept_label: string | null;
  /** Suma de los segmentos del último ejercicio / ingresos consolidados del emisor (BCS: comisiones, 0.38). */
  coverage: number | null;
  covers_total: boolean;
  coverage_source: { concept: string; from: string; value: number } | null;
  /** Frase para el lector si no cubren los ingresos consolidados ("Comisiones · cubren el 38% de …"). */
  coverage_note: string | null;
  segments: SegmentItem[];
  total_reported: Record<string, number>;
  /** Si no concilia con el ingreso consolidado se publica igual: `gap_pct` = suma / total − 1. */
  reconciles: boolean;
  gap_pct: number | null;
  notes: string[];
  secondary: SegmentAxis | null;
  others: SegmentAxis[];
  /** Ejes descartados con su motivo (un miembro de más del 95 %: componentes del ingreso, no segmentos). */
  dropped_axes: Array<{ axis: string; axis_label: string; reason: string }>;
  currency: string | null;
  source: { form: string; filed: string; accn: string; period_end: string | null } | null;
  reason: string | null;
}

export interface PeerMetric {
  value: number | null;
  value_txt: string;
  /** V7 · P5: por qué la cifra no es significativa («n. s.»: P/E por encima de [peers] pe_meaningful_max). */
  note?: string;
}

/** Resumen compacto del análisis de un rival: mismas cifras y textos que su página. */
export interface PeerSummary {
  symbol: string;
  name: string | null;
  price: number | null;
  currency: string | null;
  quality: { score: number | null; level: string | null };
  price_score: { score: number | null; level: string | null };
  /** Fase 1 · pendientes (7-nov-2026): «consistente» o «mixta» (antes, la confianza). */
  consistency: string | null;
  metrics: Record<string, PeerMetric>;
  /** Industria de Damodaran que resolvió su análisis (la de la referencia sectorial); null si no es una industria. */
  reference: { industry: string; region: string | null; basis: string } | null;
  /** V6 (B13): hora UTC del análisis del resumen (ISO 8601). */
  as_of?: string;
}

export type PeerStatus = "en_cola" | "analizando" | "listo" | "fallo";

export interface PeerRival {
  symbol: string;
  status: PeerStatus;
  summary?: PeerSummary;
  reason?: string;
  /** V6 (B7): con "en_cola", la cola estaba llena y la próxima consulta lo vuelve a intentar. */
  retry?: boolean;
}

/** GET /api/v2/peers/{symbol}[?symbols=A,B] (backend/lib/peers.py): repetir cada `poll_s` mientras "calculando". */
export interface PeersResponse {
  status: "listo" | "calculando" | "sin_dato";
  symbol: string;
  industry: string | null;
  source: "automaticos" | "elegidos";
  rivals: PeerRival[];
  note: string | null;
  poll_s: number;
  /** Rivales que admite `?symbols=` (market.peers.peers_count). */
  max_symbols: number;
  /** Resumen de la propia empresa (fila de arriba de la tabla) en cuanto está analizada; null mientras tanto. */
  company: PeerSummary | null;
}

/** Un resultado del buscador de /v2 (rediseño E4): `exchange`, nombre legible de la bolsa; null si no se conoce. */
export interface SearchHit {
  ticker: string;
  name: string;
  exchange: string | null;
}

/** GET /api/v2/search?q= (backend/lib/search_v2.py): solo acciones, como mucho 8. */
export interface SearchResponse {
  results: SearchHit[];
}

/** Calidad y precio del motor de una tarjeta de tendencias (rediseño E4: cola compartida con los rivales, prioridad
 *  `prewarm`). `quality` y `price_score` solo con `status` "listo". */
export interface TrendingEngine {
  status: PeerStatus;
  quality: { score: number | null; level: string | null } | null;
  price_score: { score: number | null; level: string | null } | null;
  /** V6 (B13): hora UTC del análisis de la tarjeta (ISO 8601); null sin resumen. */
  as_of?: string | null;
  /** Motivo del fallo (solo con `status` "fallo"). */
  reason: string | null;
}

export interface TrendingItem {
  symbol: string;
  name: string | null;
  price: number;
  change_pct: number;
  dollar_volume: number | null;
  /** P8: sector GICS (clave en inglés; la etiqueta en español va en `sector_status`). */
  sector?: string | null;
  /** null: ni analizada ni en marcha (cupo diario de precalentado agotado, cola llena o análisis caducado). */
  engine: TrendingEngine | null;
}

/** P8: estado de la lista de un sector: con menos valores de los que pide el backend, no disponible y por qué. */
export interface TrendingSectorStatus {
  label: string;
  count: number;
  available: boolean;
  reason: string | null;
}

/** P8b: periodos de la portada (los de las listas y los de las mini-gráficas: backend [trending] periods). */
export type TrendingPeriod = "1D" | "1S" | "1M" | "6M";

export interface TrendingLists { most_traded: TrendingItem[]; gainers: TrendingItem[]; losers: TrendingItem[] }

/** P8b: un periodo de las listas: sesiones hacia atrás y fechas de partida y final (ISO). */
export interface TrendingPeriodInfo { label: string; sessions: number; from: string | null; to: string; count: number }

export interface TrendingData {
  session: string;
  as_of: string;
  /** P8b: las listas se calculan en cada periodo (variación con el cierre ajustado de hace N sesiones). */
  periods: Record<TrendingPeriod, TrendingPeriodInfo>;
  lists: Record<TrendingPeriod, TrendingLists>;
  /** «Suben más» solo trae valores que suben (y «Bajan más» los que bajan): si no llegan, el motivo. */
  list_notes: Record<TrendingPeriod, { gainers: string | null; losers: string | null }>;
  /** P8: por sector GICS, los de más volumen en dólares (en el orden de config) y su estado, por periodo. */
  sectors?: Record<TrendingPeriod, Record<string, TrendingItem[]>>;
  sector_status?: Record<TrendingPeriod, Record<string, TrendingSectorStatus>>;
  universe_date: string | null;
  count: number;
  failed_batches: number;
  note: string | null;
}

/** GET /api/v2/trending (backend/lib/trending.py): la última lista buena; "calculando" tras un reinicio. Repetir cada
 *  `poll_s` mientras "calculando" o mientras alguna tarjeta tenga el motor en cola o analizando. */
export interface TrendingResponse {
  status: "listo" | "calculando" | "sin_dato";
  data: TrendingData | null;
  refreshing: boolean;
  reason: string | null;
  poll_s: number;
}
