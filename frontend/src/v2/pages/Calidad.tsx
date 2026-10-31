"use client";
import type { PageProps } from "./DepthPage";
import type { GaugeChart, QualityReading } from "@/lib/api";
import { toVTone } from "@/v2/lib/tone";
import { chapterHref } from "@/v2/lib/routes";
import PillIndex from "@/v2/components/depth/PillIndex";
import Section, { Missing, StateNote } from "@/v2/components/depth/Section";
import Methodology from "@/v2/components/depth/Methodology";
import TechTable from "@/v2/components/depth/TechTable";
import MetricTip, { LabelTip } from "@/v2/components/depth/MetricTip";
import Gauge from "@/v2/components/Gauge";
import PiotroskiGrid from "@/v2/components/PiotroskiGrid";
import BreakdownTable from "@/v2/components/BreakdownTable";

/** Entradas mínimas de cada tarjeta para ir lado a lado en «Crecimiento» (con menos, la corta deja hueco al pie). */
const SIDE_BY_SIDE_MIN = 2;

const PILLS = [
  { id: "rentabilidad", label: "Rentabilidad" }, { id: "solidez", label: "Solidez" }, { id: "crecimiento", label: "Crecimiento" },
  { id: "ganancias", label: "Calidad de ganancias" }, { id: "piotroski", label: "Piotroski" }, { id: "altman", label: "Altman" },
  { id: "desglose", label: "Desglose" }, { id: "historia", label: "Historia de 10 años" },
];
const cap = (t: string) => t.charAt(0).toUpperCase() + t.slice(1);

function Readings({ items }: { items?: QualityReading[] }) {
  if (!items?.length) return null;
  return (
    <div className={`dgrid${items.length % 2 ? " one" : ""}`} data-sym-row>
      {items.map((q) => <div key={q.key} className="card surface"><h4>{q.label}</h4><p className={`fill tone-${toVTone(q.tone)}`}>{q.text}</p></div>)}
    </div>
  );
}

function GaugeCard({ g, tooltips }: { g: GaugeChart; tooltips: PageProps["analysis"]["display"]["tooltips"] }) {
  // Cuatro filas (título · valor · escala · texto) compartidas con las demás escalas de la fila (.dgrid.sub)
  const scale = g.state === "con_dato" && g.zones && g.axis_max && !g.net_cash && !g.negative && !g.informative;
  return (
    <div className="card surface" data-gauge={g.key}>
      <h4><LabelTip text={g.label}><MetricTip metricKey={g.key} label={g.label} value={g.value_txt} reading={g.reading} bands={tooltips[g.key]} /></LabelTip></h4>
      {g.state === "con_dato"
        ? <p><span className={`tile-value num tone-${toVTone(g.tone)}`}>{g.value_txt}</span>
            {g.reading && <> <span className={`pill ${toVTone(g.tone)}`}>{g.reading}</span></>}</p>
        : <StateNote state={g.state} text={g.text ?? "el proveedor no lo da"} />}
      <div className="gauge-row">{scale ? <Gauge zones={g.zones!} axisMax={g.axis_max!} value={g.value} unit={g.unit} tone={g.tone} label={`${g.label}: ${g.value_txt}${g.reading ? `, ${g.reading}` : ""}`} /> : null}</div>
      <p className="muted small">{g.state === "con_dato" ? (g.text ?? "") : ""}</p>
    </div>
  );
}

/** Task 6 · Calidad: rentabilidad, solidez, crecimiento, calidad de ganancias, Piotroski, Altman y el desglose. */
export default function Calidad({ analysis: a, symbol }: PageProps) {
  const d = a.display, s = d.sections, ch = d.charts, tips = d.tooltips;
  const refLabel = cap(d.benchmark.short);
  const prof = s.profitability, solv = s.solvency, gr = s.growth, ins = s.institutional;
  const spread = ch.profitability.spread, roce = ch.profitability.roce;
  const struct = ch.solvency.structure, runway = ch.solvency.runway;
  const cats = ins.breakdown?.categories ?? [];
  const eq = cats.find((c) => (c.key ?? c.name) === "Calidad de Ganancias");   // clave del motor
  const pioCard = ins.cards.find((c) => c.key === "piotroski");
  const altCard = ins.cards.find((c) => c.key === "altman");
  // Tarjetas institucionales propias del tipo de empresa (salud financiera de un banco…): Piotroski, Altman y la pista
  // de caja ya tienen su sección
  const otherCards = ins.cards.filter((c) => !["piotroski", "altman", "runway"].includes(c.key));
  const altman = ch.institutional.altman;
  return (<>
    <PillIndex items={otherCards.length
      ? PILLS.flatMap((p) => p.id === "solidez" ? [p, { id: "institucional", label: "Evaluación institucional" }] : [p]) : PILLS} />
    <div className="wrap depth-body">
      <Section id="rentabilidad" eyebrow="Calidad" title="Rentabilidad y eficiencia">
        {prof.intro && <p className="segs-head">{prof.intro}</p>}
        <TechTable rows={prof.rows} refLabel={refLabel} tooltips={tips} caption={`Frente a la referencia ${d.benchmark.ref}`} columns={prof.columns} />
        {/* Tres filas compartidas (título · cifra · lectura): el espacio se reparte por filas; sin cifra, la nota del
            motor ocupa las dos últimas */}
        <div className="dgrid sub" style={{ "--rows": 3 } as React.CSSProperties} data-sym-row>
          <div className="card surface">
            <h4>ROIC −<span className="nobr"> WACC<MetricTip metricKey="roic_wacc_spread" label="ROIC − WACC" value={spread.value_txt} reading={spread.reading} bands={tips.roic_wacc_spread} /></span></h4>
            {spread.state === "con_dato"
              ? <p><span className={`tile-value num tone-${toVTone(spread.tone)}`}>{spread.value_txt}</span>{spread.reading && <> <span className={`pill ${toVTone(spread.tone)}`}>{spread.reading}</span></>}</p>
              : <StateNote state={spread.state} text={spread.text} rows={2} />}
            {spread.state === "con_dato" && <p>{spread.text}</p>}
          </div>
          <div className="card surface">
            <h4><LabelTip text={roce.label ?? "ROCE"}><MetricTip metricKey="roce" label="ROCE" value={roce.value_txt} /></LabelTip></h4>
            {roce.state === "con_dato"
              ? <div><p><span className="tile-value num">{roce.value_txt}</span>{roce.basis && <span className="muted"> · {roce.basis}</span>}</p>
                  {roce.avg && <p className="small">{roce.avg.label}: <span className="num">{roce.avg.value_txt}</span> ({roce.avg.years} años{roce.avg.incomplete ? ", incompleto" : ""})</p>}</div>
              : <StateNote state={roce.state} text={roce.text} rows={2} />}
            {roce.state === "con_dato" && <p>{prof.roce_reading ?? roce.text}</p>}
          </div>
        </div>
        {prof.divergence_note && prof.divergence_note !== prof.roce_reading && <p className="missing">{prof.divergence_note}</p>}
        <Readings items={prof.quality_readings} />
      </Section>

      <Section id="solidez" eyebrow="Calidad" title="Solidez financiera">
        {solv.intro && <p className="segs-head">{solv.intro}</p>}
        <TechTable rows={solv.rows} refLabel={refLabel} tooltips={tips} columns={solv.columns} />
        <p className="segs-head num">{solv.balance}</p>
        <div className="dgrid sub" style={{ "--rows": 4 } as React.CSSProperties} data-sym-row>{ch.solvency.gauges.map((g) => <GaugeCard key={g.key} g={g} tooltips={tips} />)}</div>
        {/* Una columna: la estructura del balance y la pista de caja tienen formas distintas; juntas dejaban hueco */}
        <div className="dgrid one" data-sym-row>
          {struct.state === "con_dato" ? (
            <div className="card surface" data-testid="structure">
              <h4>Estructura del balance · activos {struct.assets_txt}</h4>
              <div className="fill">
                <div className="stackbar" aria-hidden="true">
                  {struct.debt_pct != null && <span className="sb debt" style={{ width: `${struct.debt_pct}%` }} />}
                  {struct.equity_pct != null && <span className="sb equity" style={{ width: `${struct.equity_pct}%` }} />}
                  {struct.cash_pct != null && <span className="sb cash" style={{ width: `${struct.cash_pct}%` }} />}
                </div>
                <dl className="kv kv-tight">
                  {([["Deuda", struct.debt_txt, struct.debt_pct], ["Patrimonio", struct.equity_txt, struct.equity_pct], ["Caja", struct.cash_txt, struct.cash_pct],
                    ["Deuda neta", struct.net_debt_txt, null]] as Array<[string, string | undefined, number | null | undefined]>)
                    .filter(([, v]) => v).map(([k, v, p]) => <div key={k} className="kv-row"><dt><i className={`sw sb-${k}`} />{k}</dt>
                      <dd className="num">{v}{p != null && <span className="muted nobr"> · {p < 0 ? "negativo" : <>{Math.round(p)}%<span className="of-assets"> de los activos</span></>}</span>}</dd></div>)}
                </dl>
              </div>
            </div>
          ) : <Missing title="Estructura del balance" reason="sin activos en los estados" />}
          {runway && (
            <div className="card surface">
              <h4>Pista de caja</h4>
              <div className="fill">
                {runway.state === "con_dato" ? (<>
                  <p><span className={`tile-value num tone-${toVTone(runway.tone)}`}>{runway.self_funded ? "Se financia sola" : runway.years_txt}</span>
                    {runway.reading && <> <span className={`pill ${toVTone(runway.tone)}`}>{runway.reading}</span></>}</p>
                  {runway.zones && runway.axis_max && !runway.self_funded && <Gauge zones={runway.zones} axisMax={runway.axis_max} value={runway.years} tone={runway.tone} label={`Pista de caja: ${runway.years_txt}`} />}
                </>) : null}
                {runway.text && <p className="muted small">{runway.text}</p>}
              </div>
            </div>
          )}
        </div>
        <Readings items={solv.quality_readings} />
      </Section>

      {otherCards.length > 0 && (
        <Section id="institucional" eyebrow="Calidad" title="Evaluación institucional">
          <div className={`dgrid${otherCards.length % 2 ? " one" : ""}`} data-sym-row>
            {otherCards.map((c) => (
              <div key={c.key} className="card surface"><h4>{c.title} <span className={`num tone-${toVTone(c.tone)}`}>{c.value}</span>
                {c.subtitle && <> <span className={`pill ${toVTone(c.tone)}`}>{c.subtitle}</span></>}</h4>
                <p className="fill">{c.body}</p></div>
            ))}
          </div>
        </Section>
      )}

      <Section id="crecimiento" eyebrow="Calidad" title="Crecimiento">
        {gr.intro && <p className="segs-head">{gr.intro}</p>}
        <TechTable rows={gr.rows} refLabel={refLabel} tooltips={tips} columns={gr.columns} />
        {/* Verificación V1 (AMZN): con una sola entrada en una de las dos tarjetas, lado a lado quedaba un hueco al pie
            de la corta; entonces van una debajo de otra (y sin componentes, sin su tarjeta) */}
        <div className={`dgrid${ch.growth.length < SIDE_BY_SIDE_MIN || gr.score_components.length < SIDE_BY_SIDE_MIN ? " one" : ""}`} data-sym-row>
          <div className="card surface">
            <h4>Crecimiento anual compuesto (3 años)</h4>
            <ul className="segbars fill">
              {ch.growth.map((g) => g.state === "con_dato" ? (
                <li key={g.key}><span className="seg-label">{g.label}</span>
                  <span className={`num seg-val tone-${toVTone(g.tone)}`}>{g.value_txt}</span>
                  {/* la lectura puede ser una frase (REIT: retorno total): texto con su tono, no pastilla */}
                  {g.reading ? <span className={`small seg-note tone-${toVTone(g.tone)}`}>{g.reading}</span> : <span className="seg-note" />}</li>
              ) : <li key={g.key} data-missing><strong>{g.label}:</strong> {g.text ?? "Sin dato"}</li>)}
            </ul>
          </div>
          {gr.score_components.length > 0 && <div className="card surface">
            <h4>Lo que puntúa en Crecimiento</h4>
            <dl className="kv fill">
              {gr.score_components.map((c) => <div key={c.metric} className="kv-row"><dt>{c.metric} · <span className="num">{c.value}</span></dt><dd>{c.reason}</dd></div>)}
            </dl>
          </div>}
        </div>
        {gr.eps_vs_revenue_note && <p className="missing">{gr.eps_vs_revenue_note}</p>}
      </Section>

      <Section id="ganancias" eyebrow="Calidad" title="Calidad de ganancias">
        {eq ? <BreakdownTable cat={eq} /> : <Missing title="Calidad de ganancias" reason="la categoría no aplica a este tipo de empresa" />}
      </Section>

      <Section id="piotroski" eyebrow="Calidad" title={`Piotroski F-Score${pioCard ? ` · ${pioCard.value}` : ""}`}>
        {pioCard && <p className="segs-head"><span className={`pill ${toVTone(pioCard.tone)}`}>{pioCard.subtitle}</span> {pioCard.body}
          <MetricTip metricKey="piotroski" label="Piotroski F-Score" value={pioCard.value} bands={tips.piotroski} /></p>}
        {ins.piotroski_criteria.length
          ? <PiotroskiGrid criteria={ins.piotroski_criteria} values={d.extended?.piotroski_values ?? []} />
          : <Missing title="Criterios de Piotroski" reason="sin dos ejercicios comparables" />}
      </Section>

      <Section id="altman" eyebrow="Calidad" title={`Altman Z-Score${altCard ? ` · ${altCard.value}` : ""}`}>
        {altman.state === "con_dato" && altman.zones && altman.axis_max ? (
          <div className="card surface" data-testid="altman">
            <p><span className="tile-value num">{altman.value_txt}</span> <span className="muted">{altman.model}</span>
              {altman.zone && <> · <strong>{altman.zone}</strong></>}
              <MetricTip metricKey="altman" label="Altman Z-Score" value={altman.value_txt} reading={altman.zone} bands={tips.altman} /></p>
            <Gauge zones={altman.zones} axisMax={altman.axis_max} value={altman.value} tone={altman.zones.find((z) => z.label === altman.zone)?.tone} label={`Altman ${altman.value_txt}: ${altman.zone ?? ""}`} />
            {altCard?.body && <p>{altCard.body}</p>}
            {altman.text && <p className="muted small">{altman.text}</p>}
          </div>
        ) : <Missing title="Altman Z-Score" reason={altman.text ?? altCard?.body} />}
      </Section>

      <Section id="desglose" eyebrow="Calidad" title="Desglose de la puntuación de calidad">
        {ins.breakdown ? (<>
          <p className="segs-head">{ins.breakdown.intro} <MetricTip metricKey="category" label="Puntos de la categoría" bands={tips.category} /></p>
          {ins.breakdown.coverage_notes.map((n) => <p key={n} className="missing">{n}</p>)}
          {cats.filter((c) => c.group === "quality").map((c) => <BreakdownTable key={c.name} cat={c} />)}
        </>) : <Missing title="Desglose" reason="sin desglose de la puntuación" />}
      </Section>

      <Section id="historia" eyebrow="Calidad" title="Historia de 10 años">
        <p className="segs-head">La historia de ingresos, beneficio, flujo de caja y márgenes de los últimos 10 ejercicios está en{" "}
          <a data-nav href={chapterHref(symbol, "negocio", "historia")}>Cómo gana dinero → Historia de 10 años</a>.</p>
      </Section>

      <Methodology items={[
        { label: "Referencias", text: ch.comparison.note },
        { label: "Periodo", text: d.methodology.ratios_text ? `Ratios: ${d.methodology.ratios_text}.` : null },
        { label: "Modelos", text: `La puntuación de calidad combina las categorías del desglose; usa ${d.methodology.models_text}.` },
      ]} />
    </div>
  </>);
}
