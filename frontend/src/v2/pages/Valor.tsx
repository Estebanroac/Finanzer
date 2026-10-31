"use client";
import type { PageProps } from "./DepthPage";
import { SENS_BAND_TONES, toVTone } from "@/v2/lib/tone";
import { chapterHref } from "@/v2/lib/routes";
import PillIndex from "@/v2/components/depth/PillIndex";
import Section, { Missing } from "@/v2/components/depth/Section";
import Methodology from "@/v2/components/depth/Methodology";
import TechTable from "@/v2/components/depth/TechTable";
import MetricTip, { LabelTip } from "@/v2/components/depth/MetricTip";
import ScenarioPanel from "@/v2/components/ScenarioPanel";
import BreakdownTable from "@/v2/components/BreakdownTable";

const PILLS = [{ id: "escenarios", label: "Escenarios" }, { id: "exige", label: "Qué exige el precio" },
  { id: "multiplos", label: "Múltiplos" }, { id: "dcf", label: "DCF y sensibilidad" }, { id: "graham", label: "Graham" },
  { id: "metodologia", label: "Metodología" }];
const BAND_TONES = SENS_BAND_TONES;
const ROLE: Record<string, string> = { block: "en el bloque de múltiplos", scored: "puntúa aparte", informative: "informativo: no puntúa" };
const cap = (t: string) => t.charAt(0).toUpperCase() + t.slice(1);

/** Task 7 · Cuánto vale: escenarios del usuario (motor), qué exige el precio, múltiplos, DCF y su sensibilidad, Graham. */
export default function Valor({ analysis: a, symbol }: PageProps) {
  const d = a.display, v = d.sections.valuation, chv = d.charts.valuation, tips = d.tooltips;
  const si = a.scenario_inputs;
  const fair = chv.fair_value;
  // V4b · 4 (PM): las columnas de WACC que el modelo recorta (fuera de su rango) no se pintan; la nota lo dice
  const sensCols = new Set((v.sensitivity?.columns ?? []).map((_, j) => j)
    .filter((j) => (v.sensitivity?.rows ?? []).some((r) => r.cells[j] && r.cells[j].value !== "—")));
  const priceCat = d.sections.institutional.breakdown?.categories.find((c) => c.group === "price");
  const span = fair.axis ? fair.axis[1] - fair.axis[0] : 0;
  const at = (x?: number | null) => (x == null || !fair.axis || !span ? null : Math.max(0, Math.min(100, ((x - fair.axis[0]) / span) * 100)));
  return (<>
    <PillIndex items={PILLS} />
    <div className="wrap depth-body">
      <Section id="escenarios" eyebrow="Escenarios · lo calcula Finanzer con tus supuestos" title="Mueve los supuestos y mira el valor">
        {si?.status === "ok" && si.base && si.bounds
          ? <ScenarioPanel inputs={si} />
          : <Missing title="Escenarios" reason={si?.reason ?? "el DCF no da valor razonable para esta empresa"} />}
      </Section>

      <Section id="exige" eyebrow="Cuánto vale" title={v.reverse_dcf?.title ?? "Qué exige el precio"}>
        {v.reverse_dcf ? (
          <div className="card surface" data-testid="reverse-dcf">
            {v.reverse_dcf.lines.map((l) => (
              <p key={l.text}>{l.label && <span className={`pill ${toVTone(l.tone)}`}>{l.label}</span>} {l.text}</p>
            ))}
            <p><strong>Papel en el veredicto:</strong> {v.reverse_dcf.role}</p>
            <p className="muted small">{v.reverse_dcf.method}</p>
          </div>
        ) : <Missing title="Qué exige el precio" reason="el DCF inverso no aplica a este tipo de empresa" />}
      </Section>

      <Section id="multiplos" eyebrow="Cuánto vale" title="Múltiplos frente a la referencia">
        {v.intro && <p className="segs-head">{v.intro}</p>}
        <TechTable rows={v.rows} refLabel={cap(d.benchmark.short)} tooltips={tips} columns={v.columns} />
        {chv.multiples.length > 0 && (
          <p className="segs-head">{chv.multiples.map((m) => <span key={m.key}><span className="chip">{m.label}: {ROLE[m.role]}</span>{" "}</span>)}</p>
        )}
        {chv.block && <p className="missing"><strong>{chv.block.label}</strong> <span className={`num tone-${toVTone(chv.block.tone)}`}>{chv.block.sign}</span> · {chv.block.reason}</p>}
        {chv.scored.map((s) => (
          <p key={s.key} className="missing"><strong>{s.label}{s.value_txt ? ` ${s.value_txt}` : ""}</strong>
            {s.reading && <> · <span className={`pill ${toVTone(s.tone)}`}>{s.reading}</span></>}{s.sign && <> <span className="num">{s.sign}</span></>}{s.reason ? ` · ${s.reason}` : ""}</p>
        ))}
        {[v.market_note, v.reference_note, v.normalization_note].filter(Boolean).map((n) => <p key={n!} className="muted small">{n}</p>)}
        {priceCat && <BreakdownTable cat={priceCat} />}
      </Section>

      <Section id="dcf" eyebrow="Cuánto vale" title="DCF y sensibilidad">
        {fair.state === "con_dato" && fair.zones && fair.axis ? (
          <div className="card surface" data-testid="fair-value">
            <p><span className="muted">{fair.method} · valor por acción</span> <span className="tile-value num">{fair.fair_value_txt}</span>
              {" "}<span className="muted">frente a un precio de {fair.price_txt}</span>{fair.upside_txt && <> · <span className="num">{fair.upside_txt}</span></>}
              {fair.badge && <> <span className={`pill ${toVTone(fair.badge.tone)}`}>{fair.badge.label}</span></>}
              <MetricTip metricKey="dcf_fair_value" label="Valor razonable (DCF)" value={fair.fair_value_txt} /></p>
            <div className="fvscale" aria-hidden="true">
              {fair.zones.map((z) => <span key={z.from} className={`gauge-zone ${toVTone(z.tone)}`} style={{ left: `${at(z.from)}%`, width: `${(at(z.to) ?? 0) - (at(z.from) ?? 0)}%` }} />)}
              {at(fair.grid_low) != null && at(fair.grid_high) != null && <span className="fv-grid" style={{ left: `${at(fair.grid_low)}%`, width: `${at(fair.grid_high)! - at(fair.grid_low)!}%` }} />}
              {/* v4 (PM): el precio es lo que se sitúa frente al valor: su marca, en el color de su tramo (la lectura del motor) */}
              <span className={`fv-mark price ${toVTone(fair.badge?.tone)}`} style={{ left: `${at(fair.price)}%` }} />
              <span className="fv-mark fv" style={{ left: `${at(fair.fair_value)}%` }} />
            </div>
            <p className="legend"><span><i className="sw line pos" />Valor {fair.fair_value_txt}</span><span><i className={`sw line mk-${toVTone(fair.badge?.tone)}`} />Precio {fair.price_txt}{fair.badge && ` · ${fair.badge.label}`}</span>
              {fair.central_low_txt && <span><i className="sw b1" />Bloque central {fair.central_low_txt}–{fair.central_high_txt}</span>}
              {fair.grid_low_txt && <span><i className="sw b1" />Rango de la sensibilidad {fair.grid_low_txt}–{fair.grid_high_txt}</span>}
              {fair.zones.map((z) => <span key={z.label}><i className={`sw zone-${toVTone(z.tone)}`} />{z.label}</span>)}</p>
          </div>
        ) : <Missing title="DCF" reason={v.dcf_missing || fair.text} />}
        {fair.state === "con_dato" && fair.central_text && <p className="muted small">Valor {fair.fair_value_txt}: {fair.central_text}.</p>}
        {v.dcf_params && <p className="segs-head">{v.dcf_params}</p>}
        {v.dcf_reliability && <p className="missing"><span className={`pill ${toVTone(v.dcf_reliability_tone)}`}>Fiabilidad {v.dcf_reliability_level}</span> {v.dcf_reliability}</p>}
        {chv.dcf_composition && <p className="muted small">Composición del valor: {chv.dcf_composition.explicit_pct.toFixed(0)}% de los flujos de los próximos 10 años y {chv.dcf_composition.terminal_pct.toFixed(0)}% del valor terminal.</p>}
        {(v.wacc_breakdown?.length || v.wacc_note || v.ke_note) && (
          <div className="dgrid one" data-sym-row>
            {v.wacc_breakdown?.length ? (
              <div className="card surface"><h4>Coste del capital <span className="nobr">(WACC)<MetricTip metricKey="wacc" label="WACC" /></span></h4>
                <dl className="kv fill">{v.wacc_breakdown.map((w) => <div key={w.label} className="kv-row"><dt>{w.label}</dt><dd className="num">{w.value}</dd></div>)}</dl></div>
            ) : null}
            {(v.wacc_note || v.ke_note) && (
              <div className="card surface"><h4>Cómo se calcula</h4><div className="fill stack">{[v.wacc_note, v.ke_note].filter(Boolean).map((n) => <p key={n!}>{n}</p>)}</div></div>
            )}
          </div>
        )}
        {v.sensitivity ? (
          <div className="card surface" data-testid="report-sensitivity">
            <h4>Sensibilidad del <span className="nobr">informe<MetricTip metricKey="sensitivity" label="Sensibilidad" /></span></h4>
            <p className="small">{v.sensitivity.intro}</p>
            <div className="sens-wrap" tabIndex={0} role="region" aria-label="Sensibilidad del informe">
            <table className="segtable sens">
              <thead><tr><th scope="col" className="sens-corner" aria-label={v.sensitivity.corner}>g ↓ · WACC →</th>{v.sensitivity.columns.map((c, j) => sensCols.has(j) && <th key={c} scope="col" className="num">{c}</th>)}</tr></thead>
              <tbody>{v.sensitivity.rows.map((r) => (
                <tr key={r.label}><th scope="row" className="num">{r.label}</th>{r.cells.map((c, j) => sensCols.has(j) && (
                  <td key={j} className={`num band-${c.band == null ? "none" : BAND_TONES[c.band]}${c.base ? " base" : ""}`}>{c.value}</td>
                ))}</tr>
              ))}</tbody>
            </table></div>
            <p className="legend">{v.sensitivity.band_labels.map((l, i) => <span key={l}><i className={`sw zone-${BAND_TONES[i]}`} />{l}</span>)}</p>
            {v.sensitivity.note && <p className="muted small">{v.sensitivity.note}</p>}
          </div>
        ) : null}
      </Section>

      <Section id="graham" eyebrow="Cuánto vale" title="Graham y valor intrínseco">
        <div className="card surface" data-testid="intrinsic">
          {v.intrinsic.intro && <p>{v.intrinsic.intro}</p>}
          <dl className="kv">
            {v.intrinsic.rows.map((r) => (
              <div key={r.key} className="kv-row"><dt><LabelTip text={r.label}><MetricTip metricKey={r.key} label={r.label} value={r.value} reading={r.reading} bands={tips[r.key]} /></LabelTip></dt>
                <dd className={`num tone-${toVTone(r.tone)}`}>{r.state === "con_dato" ? r.value : (r.text ?? "Sin dato")}{r.reading && r.reading !== "—" ? ` · ${r.reading}` : ""}</dd></div>
            ))}
          </dl>
          {v.intrinsic.graham_note && <p className="muted small">{v.intrinsic.graham_note}</p>}
        </div>
        {v.premortem && <p className="segs-head">El pre-mortem («{v.premortem.title}») está en{" "}
          <a data-nav href={chapterHref(symbol, "riesgos", "premortem")}>Riesgos → Pre-mortem</a>.</p>}
      </Section>

      <Methodology items={[
        { label: "Modelos", text: `El valor intrínseco usa ${d.methodology.models_text}.` },
        { label: "Parámetros del DCF", text: v.dcf_params },
        { label: "Referencias", text: v.reference_note },
        { label: "Escenarios", text: "El panel de escenarios recalcula el mismo DCF del informe con tus supuestos; la sensibilidad usa los pasos de la tabla del informe. No cambian el veredicto." },
      ]} />
    </div>
  </>);
}
