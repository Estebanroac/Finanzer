import type { StockAnalysis } from "@/lib/api";
import { SCORE_BANDS } from "@/lib/generated/backendConfig";
import { buildScale, buildLevelScale } from "@/v2/lib/scale";
import { ticksFitAttr } from "@/v2/lib/scaleFit";
import { toVTone } from "@/v2/lib/tone";
import ScoreScale, { type Breakdown } from "./ScoreScale";
import { perShareCur } from "@/v2/lib/format";
import { categoryTerm, confidenceTerm, priceRowTerm } from "@/v2/lib/terms";
import { confidenceLine } from "@/v2/lib/confidence";
import { profileNames } from "@/lib/names";
import { chapterHref } from "@/v2/lib/routes";
import { analysisLogo } from "@/v2/lib/logo";
import CompanyLogo from "./CompanyLogo";

const signed = (v: number) => (v > 0 ? `+${v}` : v === 0 ? "0" : `−${Math.abs(v)}`);
const NUMBER_WORDS = ["cero", "una", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve", "diez"];
const cap1 = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);
/** "Excelente desde 80, sólida desde 65, media desde 45; débil por debajo." (bandas de la config). */
const bandsSentence = (kind: "quality" | "price") => {
  const { bands, labels } = SCORE_BANDS[kind];
  const from = bands.map((b, i) => `${labels[i]} desde ${b}`).join(", ");
  return `${cap1(from)}; ${labels[labels.length - 1]} por debajo.`;
};
/** V7 (PM): cómo se forman las dos puntuaciones, en palabras y con las cifras de la config (sin «motor», «reescalado» ni
 *  «factor»). */
export const QUALITY_NOTE = `La calidad suma ${NUMBER_WORDS[SCORE_BANDS.quality.categories] ?? SCORE_BANDS.quality.categories} `
  + `categorías de ${SCORE_BANDS.category.max} puntos y se expresa sobre ${SCORE_BANDS.scale}. ${bandsSentence("quality")}`;
export const PRICE_NOTE = `El atractivo del precio parte de ${SCORE_BANDS.category.base} sobre ${SCORE_BANDS.category.max} `
  + `y suma lo que dicen los múltiplos y el DCF; se expresa sobre ${SCORE_BANDS.scale} y, cuanto menor es la confianza, `
  + `más se acerca a ${SCORE_BANDS.price.neutral}. ${bandsSentence("price")}`;
/** Frases de un texto del motor (para citar solo la que toca). */
const sentences = (t: string | null | undefined) => (t ?? "").split(/(?<=\.)\s+/).filter(Boolean);
/** El motor da la confianza entre paréntesis y con su nivel delante, para pegarla al veredicto
 *  ("(confianza alta: …)"); aquí el nivel ya está en grande, así que va solo el motivo. */
const unwrap = (s: string | null | undefined) => {
  const t = (s ?? "").replace(/^\((.*)\)$/, "$1").replace(/^confianza\s+\S+:\s*/i, "");
  return t.charAt(0).toUpperCase() + t.slice(1);
};

/** V4-F8 (PM): la nota de una puntuación. La cabecera resume (forma corta, `note_short`) y la sección «La empresa»
 *  detalla (la frase completa, `note`): nada se oculta. Vale para cualquier nota que el motor añada. */
function noteFor(block: { note: string | null; note_short?: string | null }, full: boolean): string | null {
  return full ? block.note : (block.note_short ?? block.note);
}

/** Las tres puntuaciones (calidad, precio y confianza) con su escala y su base. Con `withBreakdown`, además su desglose
 *  completo (V4b, «nada oculto»: en la sección «La empresa», `ScoreBreakdowns`); sin él, la cabecera de todas las
 *  secciones. `ids`: el prefijo de sus identificadores de prueba (los de la cabecera son los de siempre). */
function ScoreCards({ analysis, withBreakdown, ids }: { analysis: StockAnalysis; withBreakdown: boolean; ids: { quality: string; price: string; confidence: string } }) {
  const d = analysis.display, cover = d.cover;
  const q = cover.quality, p = cover.price;
  const comp = d.summary.composition;
  const cats = cover.categories.flatMap((c) => c.items);
  const qualityCats = cats.filter((i) => i.applicable && i.name !== "Valoración");
  const valuation = cats.find((i) => i.name === "Valoración");
  const conf = d.confidence;
  const contraction = sentences(conf?.summary).find((x) => x.startsWith("Contrae"));

  const qualityBd: Breakdown = {
    title: `Cómo sale el ${q.score ?? "—"}`,
    rows: qualityCats.map((c) => ({ name: c.name, value: c.score_txt, tone: toVTone(c.tone), term: categoryTerm(c.key ?? c.name) })),
    total: { name: "Calidad del negocio", value: `${q.score ?? "—"} / 100` },
    notes: [QUALITY_NOTE],
  };
  const priceBd: Breakdown = {
    title: `Cómo sale el ${p.score ?? "—"}`,
    rows: comp.price.rows.map((r) => ({ name: r.label, value: signed(r.value), tone: toVTone(r.tone), term: priceRowTerm(r.label) })),
    total: valuation ? { name: "Valoración", value: `${valuation.score_txt} → ${p.raw ?? "—"} / 100`,
      tone: toVTone(valuation.tone), term: categoryTerm("Valoración") } : undefined,
    after: p.contracted ? [{ name: "Ajuste por confianza", value: `${p.raw ?? "—"} → ${p.score ?? "—"}`, term: priceRowTerm("Ajuste por confianza") }] : [],
    notes: [PRICE_NOTE, ...(p.contracted && contraction ? [contraction] : [])],
  };
  const confBd: Breakdown | null = conf ? {
    title: "En qué se apoya",
    rows: conf.dimensions.map((x) => ({ name: x.label, value: x.level, term: confidenceTerm(x.key) })),
    notes: [],
  } : null;
  const perCat = qualityCats[0]?.max;
  const models = { quality: buildScale("quality", q.score, q.level), price: buildScale("price", p.score, p.level),
    confidence: buildLevelScale("confidence", conf?.level ?? null) };
  const fit = ticksFitAttr(Object.values(models));
  return (
    <div className="scores" data-sym-row>
      <ScoreScale testId={ids.quality} model={models.quality} fit={fit} title={q.title} question={q.question}
        display={q.score === null ? "—" : String(q.score)} suffix={q.score === null ? null : `/ 100 · ${q.level}`} tone={toVTone(q.tone)}
        base={noteFor(q, withBreakdown) ?? `${qualityCats.length} categorías × ${perCat} puntos`}
        breakdown={withBreakdown ? qualityBd : null} term="quality" />
      <ScoreScale testId={ids.price} model={models.price} fit={fit} title={p.title} question={p.question}
        display={p.score === null ? "—" : String(p.score)} suffix={p.score === null ? null : `/ 100 · ${p.level}`} tone={toVTone(p.tone)}
        base={noteFor(p, withBreakdown) ?? "Múltiplos frente a la referencia + DCF"}
        breakdown={withBreakdown ? priceBd : null} term="price" />
      <ScoreScale testId={ids.confidence} model={models.confidence} fit={fit}
        title="Confianza del veredicto" question="¿cuánto fiarse?"
        display={conf?.level ? conf.level.charAt(0).toUpperCase() + conf.level.slice(1) : "—"} suffix={null} tone="neutral" levelTone={toVTone(conf?.tone)}
        base={unwrap(conf?.verdict_text ?? cover.verdict.confidence_text) || "Sin dato"}
        line={withBreakdown ? confidenceLine(conf) : null}
        breakdown={withBreakdown ? confBd : null} term="confidence" />
    </div>
  );
}

/** V4b (PM): el desglose completo de las tres puntuaciones, a la vista en la sección «La empresa» (en todos los tamaños).
 *  La cabecera de cada sección enseña la cifra, la banda y la base, y enlaza aquí. */
export function ScoreBreakdowns({ analysis }: { analysis: StockAnalysis }) {
  return <ScoreCards analysis={analysis} withBreakdown ids={{ quality: "desglose-quality", price: "desglose-price", confidence: "desglose-confidence" }} />;
}

/** Cabecera de la empresa: identidad, precio, conclusión y las tres puntuaciones (cifra, banda y base; su desglose, en
 *  «La empresa», con un enlace). `compact` (V4b): la que queda fija arriba al bajar por la sección, con las tres
 *  puntuaciones en una línea. Repite la cabecera completa (que sigue arriba, en su sitio), así que es solo visual: sin
 *  «?», sin identificadores de prueba y oculta a los lectores de pantalla (aria-hidden). */
export default function CompanyHeader({ analysis, compact = false }: { analysis: StockAnalysis; compact?: boolean }) {
  const d = analysis.display, cover = d.cover;
  const dayChange = d.extended?.price_change;   // E2a: variación frente al cierre anterior
  const q = cover.quality, p = cover.price;
  const conf = d.confidence;
  return (
    <section className={`company-header${compact ? " compact" : ""}`} {...(compact ? { "aria-hidden": true } : { "aria-label": "Resumen de la empresa" })}>
      <div className="ident">
        {/* Logotipos: a la izquierda de la identidad, como en los brókers (en la fija, más pequeño) */}
        <div className="ident-lead">
        <CompanyLogo symbol={analysis.symbol} name={analysis.profile.name} logo={analysisLogo(analysis)}
          size={compact ? "sm" : "lg"} className="ident-logo" testId={compact ? null : "company-logo"} />
        <div className="ident-main">
          <div className="ident-name"><b className="name">{analysis.profile.name}</b>
            <span className="muted"> · {analysis.symbol} · {analysis.profile.exchange} · {profileNames(analysis).sector} · {profileNames(analysis).industry}</span></div>
          {/* Precio y variación del día juntos (no se separan al partirse la línea; en móvil, al lado del precio). */}
          <span className="quote">
            {/* Revisión V6 (F5): en la moneda de la cotización (MC.PA en EUR), no con «$» fijo */}
            <span className="price num" data-testid={compact ? undefined : "price"}>{perShareCur(analysis.price, analysis.profile.currency)}</span>
            {dayChange?.status === "ok" && dayChange.value_txt && (
              <span className={`day-change num tone-${toVTone(dayChange.tone)}`} data-testid={compact ? undefined : "day-change"}>
                {dayChange.value_txt} ({dayChange.pct_txt})</span>)}
          </span>
          {/* V4b (nada oculto): frente a qué cierre, a la vista (antes, al pasar el ratón) */}
          {!compact && dayChange?.status === "ok" && dayChange.session && (
            <span className="muted day-ref" data-testid="day-ref">frente al cierre anterior a la sesión del {dayChange.session.split("-").reverse().join("/")}</span>)}
        </div>
        </div>
        <div className="verdict" data-testid={compact ? undefined : "verdict"}>
          <span className="eyebrow">Conclusión</span>
          <span className="verdict-text">{cover.verdict.text}</span>
        </div>
      </div>
      {compact ? (
        <dl className="scores-line">
          <div><dt>Calidad</dt><dd><span className={`num tone-${toVTone(q.tone)}`}>{q.score ?? "—"}</span>{q.score !== null && <span className="muted"> / 100 · {q.level}</span>}</dd></div>
          <div><dt>Precio</dt><dd><span className={`num tone-${toVTone(p.tone)}`}>{p.score ?? "—"}</span>{p.score !== null && <span className="muted"> / 100 · {p.level}</span>}</dd></div>
          <div><dt>Confianza</dt><dd className={`tone-${toVTone(conf?.tone)}`}>{conf?.level ? conf.level.charAt(0).toUpperCase() + conf.level.slice(1) : "—"}</dd></div>
        </dl>
      ) : (<>
        <ScoreCards analysis={analysis} withBreakdown={false} ids={{ quality: "score-quality", price: "score-price", confidence: "confidence" }} />
        <a className="bd-link" data-nav data-testid="bd-link" href={chapterHref(analysis.symbol, "empresa", "desglose")}>Ver desglose en La empresa →</a>
      </>
      )}
    </section>
  );
}
