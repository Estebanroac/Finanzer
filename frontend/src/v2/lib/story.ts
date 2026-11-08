import type { StockAnalysis, Row, Kpi } from "@/lib/api";
import { STATE_LABELS } from "@/lib/generated/backendConfig";
import { toVTone, type VTone } from "./tone";

export { toVTone, type VTone };
import type { ChapterSlug } from "./routes";
import { marketTerm } from "./terms";
import { inline, profileNames } from "@/lib/names";
/** Cada sección del análisis (V4b) tiene la ruta de su página: mismo identificador que la URL. */
export type ChapterId = ChapterSlug;
/** `term`: la definición que explica la cifra (V7 · P3: «?» en las de «La acción»). */
export interface KeyFigure { label: string; value: string; tone: VTone; term?: string }
/** Titular (E2a: con resumen, imagen e idioma original cuando el motor los trae en display.extended). */
export interface NewsItem {
  date: string | null; source: string | null; headline: string; url: string | null;
  summary?: string | null; image?: string | null; lang?: string | null;
}
/** La lectura con la que abre cada sección (V4b: lo que era el bloque del capítulo en la página-historia, sin su visual,
 *  que resumía el detalle que la sección ya enseña completo debajo). */
export interface ChapterModel { id: ChapterId; index: number; navLabel: string; eyebrow: string; title: string; lead: string; figures: KeyFigure[];
  /** V7 · P4: la lectura sale de los segmentos (llegan aparte); `lead` es la de reserva y la que se ve mientras. */
  leadFrom?: "segments" }

export const CHAPTER_ORDER: ChapterId[] = ["empresa", "negocio", "accion", "calidad", "valor", "rivales", "riesgos", "actualidad", "conclusion"];
/** Nombre de cada sección (pestaña, título de la página y «Siguiente sección»). */
export const SECTION_LABELS: Record<ChapterId, string> = {
  empresa: "La empresa", negocio: "Cómo gana dinero", accion: "La acción", calidad: "Calidad", valor: "Cuánto vale",
  rivales: "Rivales", riesgos: "Riesgos", actualidad: "Actualidad", conclusion: "Conclusión",
};
/** Cifras clave de cada sección, como mucho (V4b · 4, PM: las que haya, sin cajas de relleno «— / Sin dato»). */
export const FIGURES_PER_CHAPTER = 3;
const NO_APLICA = STATE_LABELS.no_aplica;
const MISSING = /^(—|Sin dato)$/;

const fromRow = (r: Row | undefined, label?: string): KeyFigure | null =>
  r && r.state === "con_dato" ? { label: label ?? r.label, value: r.value, tone: toVTone(r.tone) } : null;
const fromKpi = (k: Kpi | undefined): KeyFigure | null =>
  k && k.state === "con_dato" ? { label: k.label, value: k.value, tone: "neutral" } : null;
/** Las cifras con valor, hasta FIGURES_PER_CHAPTER (una sin dato no ocupa una caja: su motivo está en el detalle). */
const pick = (fs: Array<KeyFigure | null>): KeyFigure[] =>
  fs.filter((f): f is KeyFigure => !!f && !!f.value.trim() && !MISSING.test(f.value.trim())).slice(0, FIGURES_PER_CHAPTER);
/** V7 · P2: el grupo de alertas rojas se llama por lo que es (lo que marca el modelo), no «Riesgos». */
/** Fase 1 · pendientes (7-nov-2026): una sola alerta roja, la de valoración extrema (la única con evidencia). */
export const RED_FLAGS_LABEL = "Alerta roja";
export const alertGroupLabel = (key: string, title: string) => (key === "red_flags" ? RED_FLAGS_LABEL : title);
const firstText = (...xs: Array<string | null | undefined>) => xs.find((x) => x && x.trim()) ?? "";
const cap = (t: string) => t.charAt(0).toUpperCase() + t.slice(1);
/** Frases de un texto del motor (para colocar cada una donde toca). */
const sentences = (t: string | null | undefined) => (t ?? "").split(/(?<=\.)\s+/).filter((x) => x.trim());
const dot = (t: string) => (/[.…]$/.test(t) ? t : `${t}.`);
const joinText = (...xs: Array<string | null | undefined>) => xs.filter((x): x is string => !!x && !!x.trim()).map((x) => dot(cap(x.trim()))).join(" ");
const hasValue = (v: string) => !v.startsWith(NO_APLICA) && v !== "—";

/** La lectura de las nueve secciones: título, texto y tres cifras clave. */
export function buildReadings(a: StockAnalysis): ChapterModel[] {
  const d = a.display, cover = d.cover, s = d.sections;
  const agg = d.benchmark.short === "pares" ? "la mediana" : "el agregado";
  const names = profileNames(a);   // V7: sector e industria en español
  const kpis = cover.kpis;
  const verdict = cover.verdict.text;
  const conf = d.consistency ?? d.confidence;
  const exec = (label: string) => d.summary.exec_items.find((e) => e.label === label)?.text;
  const highlight = (kind: string) => cover.highlights.find((h) => h.kind === kind);
  const market = s.market ?? null;
  const trend = market?.rows.find((r) => r.key === "trend");
  const comparison = d.charts.comparison.groups.flatMap((g) => g.items);
  const prof = s.profitability;
  // profitability.figures: cada fila trae dos parejas [etiqueta, valor, etiqueta, valor].
  const finFacts = prof.figures.flatMap((f) => [[f[0], f[1]], [f[2], f[3]]])
    .filter(([label, value]) => label && value && hasValue(value)).map(([label, value]) => ({ label, value }));
  const margins = prof.rows.filter((r) => r.state === "con_dato" && /margin|margen/.test(r.key));
  const returnsOrder = ["roic", "roce", "roe", "roa"];
  const rank = (key: string) => { const i = returnsOrder.indexOf(key); return i < 0 ? returnsOrder.length : i; };
  const returns = prof.rows.filter((r) => r.state === "con_dato" && !/margin|margen/.test(r.key))
    .sort((x, y) => rank(x.key) - rank(y.key));
  // Tarjetas institucionales con dato (Piotroski primero; después salud financiera, runway, Altman…).
  const cards = s.institutional.cards.filter((c) => c.state === "con_dato")
    .sort((x, y) => Number(y.key === "piotroski") - Number(x.key === "piotroski"))
    .map((c) => ({ label: c.title, value: c.value, tone: toVTone(c.tone) }));
  // Con escalera de márgenes completa (3+ escalones, en «Cómo gana dinero»), las cifras clave son lo que ella no enseña.
  const LADDER_MIN = 3;
  const ladderSrc = d.charts.profitability.margin_ladder;
  const ladderSteps = (ladderSrc.revenue_txt ? 1 : 0) + ladderSrc.steps.filter((x) => x.state === "con_dato" && x.pct !== undefined).length;
  const inLadder = new Set(ladderSteps >= LADDER_MIN ? ["Ingresos", "EBITDA", "Beneficio operativo", "Beneficio neto"] : []);
  const negocioFigures = [...finFacts.filter((f) => !inLadder.has(f.label)).map((f) => ({ label: f.label, value: f.value, tone: "neutral" as VTone })),
    ...margins.map((r) => fromRow(r))];
  const revDcf = s.valuation.reverse_dcf;
  // Rivales: «mejor en X de Y» con una métrica en la que gana y otra en la que pierde (tono del motor); primero lo
  // fundamental (lo que no está en «Cuánto vale») y después los múltiplos.
  const multipleKeys = new Set(d.charts.valuation.multiples.map((m) => m.key));
  const fundamentals = comparison.filter((c) => !multipleKeys.has(c.key));
  const rivalsRows = [...fundamentals, ...comparison.filter((c) => !fundamentals.includes(c))];
  const best = rivalsRows.find((c) => c.tone === "pos") ?? null;
  const worst = rivalsRows.find((c) => c.tone === "neg") ?? null;
  const nextEarnings = d.extended?.next_earnings;
  const watch = highlight("watch");

  const ch = (id: ChapterId, title: string, lead: string, figures: Array<KeyFigure | null>): ChapterModel => ({
    id, index: CHAPTER_ORDER.indexOf(id) + 1, navLabel: SECTION_LABELS[id], eyebrow: `${CHAPTER_ORDER.indexOf(id) + 1} · ${SECTION_LABELS[id]}`,
    title, lead: lead || verdict, figures: pick(figures),
  });

  return [
    ch("empresa", `Qué es ${a.profile.name}`,
      joinText(`${a.profile.name} opera en ${inline(names.industry)} (${inline(names.sector)})`, exec("CRECIMIENTO Y RETORNO")),
      [fromKpi(kpis.find((k) => k.key === "market_cap")), { label: "Tipo de negocio", value: cover.archetype_label, tone: "neutral" },
       { label: "Bolsa", value: a.profile.exchange, tone: "neutral" }]),
    // V7 · P4: de dónde vienen los ingresos, con los segmentos de la SEC (/api/v2/segments); sin ellos, la lectura
    // general de la rentabilidad (`lead`, que es también lo que se ve mientras llegan).
    { ...ch("negocio", "De dónde vienen sus ingresos", joinText(firstText(exec("RENTABILIDAD"), prof.intro)), negocioFigures),
      leadFrom: "segments" as const },
    ch("accion", "Cómo se ha movido el precio",
      joinText(exec("CONTEXTO DE MERCADO"), trend?.text) || joinText(s.growth.range52?.caption),
      [...(market?.rows ?? []).filter((r) => r.key === "momentum" || r.key === "trend").map((r) => ({ label: r.label, value: r.value, tone: toVTone(r.tone), term: marketTerm(r.key) })),
       ...(s.growth.range52?.reading ? [{ label: "Rango de 52 semanas", value: s.growth.range52.reading.label, tone: toVTone(s.growth.range52.reading.tone), term: marketTerm("pos52") }] : []),
       ...(market?.rows ?? []).map((r) => ({ label: r.label, value: r.value, tone: toVTone(r.tone), term: marketTerm(r.key) }))]),
    // De «Creación de valor», la primera frase (ROIC frente al WACC): el ROCE ya va en las cifras clave.
    ch("calidad", "Qué tan buena es la empresa",
      joinText(exec("CALIDAD DEL NEGOCIO"), sentences(exec("CREACIÓN DE VALOR"))[0]) || joinText(cover.quality.note),
      [...returns.slice(0, FIGURES_PER_CHAPTER - 1).map((r) => fromRow(r)), ...cards, ...returns.slice(FIGURES_PER_CHAPTER - 1).map((r) => fromRow(r)), ...margins.map((r) => fromRow(r))]),
    ch("valor", "Lo que exige el precio",
      joinText(...(revDcf?.lines ?? []).map((l) => l.text)) || joinText(firstText(exec("ATRACTIVO DEL PRECIO"), s.valuation.intro)),
      [{ label: cover.price.title, value: `${cover.price.score ?? "—"} / 100 · ${cover.price.level ?? "—"}`, tone: toVTone(cover.price.tone) },
       ...(revDcf?.lines[0]?.label ? [{ label: revDcf.title, value: revDcf.lines[0].label, tone: toVTone(revDcf.lines[0].tone) }] : []),
       ...(s.valuation.dcf_reliability_level ? [{ label: "Fiabilidad del DCF", value: s.valuation.dcf_reliability_level, tone: toVTone(s.valuation.dcf_reliability_tone) }] : []),
       ...s.valuation.rows.filter((r) => r.state === "con_dato").map((r) => fromRow(r))]),
    ch("rivales", "Frente a sus rivales",
      // F10 · N2: sin la propia empresa, la referencia puede ser la mediana de sus pares (no un agregado)
      joinText(`Comparada con ${agg} ${d.benchmark.ref}, es mejor en ${d.charts.comparison.better} de ${d.charts.comparison.total} métricas`),
      [{ label: `Mejor que ${agg}`, value: `${d.charts.comparison.better} de ${d.charts.comparison.total}`, tone: "neutral" },
       ...[best, worst].filter((c): c is NonNullable<typeof c> => !!c).map((c, k) => ({
         label: `${k === 0 && best ? "Mejor" : "Peor"} · ${c.label}`, value: `${c.value_txt} · ${c.reading}`, tone: toVTone(c.tone) }))]),
    ch("riesgos", "Qué puede salir mal",
      joinText(exec("SOLIDEZ"), watch ? `${cap(watch.kicker.toLowerCase())}: ${watch.text}` : null),
      // V7 · P2: «Riesgos 0» se leía «no hay riesgos»: es lo que marca el modelo
      [...s.alerts.groups.filter((g) => g.tone !== "pos").map((g) => ({ label: alertGroupLabel(g.key, g.title), value: String(g.items.length), tone: g.items.length ? toVTone(g.tone) : "neutral" as VTone })),
       ...cards.filter((c) => !/Piotroski/.test(c.label))]),
    ch("actualidad", "Qué está pasando",
      joinText(market?.note),
      [...(nextEarnings ? [{ label: "Próximos resultados", tone: "neutral" as VTone,
          value: nextEarnings.status === "ok" ? `${nextEarnings.date_txt} · ${nextEarnings.kind}` : (nextEarnings.reason ?? "Sin fecha anunciada") }] : []),
       ...(market?.rows ?? []).slice(FIGURES_PER_CHAPTER).map((r) => ({ label: r.label, value: r.value, tone: toVTone(r.tone) }))]),
    ch("conclusion", "Nuestra lectura",
      joinText(cover.verdict.full ?? verdict),
      [{ label: "Calidad", value: `${cover.quality.score ?? "—"} / 100 · ${cover.quality.level ?? "—"}`, tone: toVTone(cover.quality.tone) },
       { label: "Precio", value: `${cover.price.score ?? "—"} / 100 · ${cover.price.level ?? "—"}`, tone: toVTone(cover.price.tone) },
       { label: "Consistencia", value: conf?.level ? cap(conf.level) : "—", tone: toVTone(conf?.tone) }]),
  ];
}
