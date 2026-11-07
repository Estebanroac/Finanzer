"use client";
import type { PageProps } from "./DepthPage";
import PdfButton from "@/v2/components/PdfButton";
import { toVTone } from "@/v2/lib/tone";
import { STATE_LABELS } from "@/lib/generated/backendConfig";
import { chapterHref } from "@/v2/lib/routes";
import PillIndex from "@/v2/components/depth/PillIndex";
import Section, { Missing } from "@/v2/components/depth/Section";
import Methodology from "@/v2/components/depth/Methodology";
import AuditAnnex from "@/v2/components/depth/AuditAnnex";
import MetricTip from "@/v2/components/depth/MetricTip";

const PILLS = [{ id: "veredicto", label: "Veredicto" }, { id: "confianza", label: "Consistencia" },
  { id: "vigilar", label: "Qué vigilar" }, { id: "informe", label: "Informe" }, { id: "metodologia", label: "Metodología" }];
const GRID = ["", " one", "", " three"];
const cap = (t: string) => t.charAt(0).toUpperCase() + t.slice(1).toLowerCase();

/** Task 11 · Conclusión: veredicto completo y su composición, consistencia, qué vigilar, el PDF y el anexo de auditoría. */
export default function Conclusion({ analysis: a, symbol }: PageProps) {
  const d = a.display, s = d.summary, c = d.cover, conf = d.confidence, comp = s.composition;
  const warnings = d.sections.alerts.groups.find((g) => g.key === "warnings")?.items ?? [];
  const pm = d.sections.valuation.premortem;
  return (<>
    <PillIndex items={PILLS} />
    <div className="wrap depth-body">
      <Section id="veredicto" eyebrow="Conclusión" title={c.verdict.text}>
        <div className="card surface" data-testid="exec">
          <dl className="exec">{s.exec_items.map((e, i) => <div key={`${i}-${e.label}`}><dt>{cap(e.label)}</dt><dd>{e.text}</dd></div>)}</dl>
        </div>
        <div className="dgrid" data-sym-row>
          <div className="card surface" data-testid="comp-quality">
            <h4>{cap(comp.quality.title)} <span className={`num tone-${toVTone(comp.quality.tone)}`}>{comp.quality.score ?? "—"}/100</span>{comp.quality.level && ` · ${comp.quality.level}`}
              <MetricTip metricKey="quality" label="Calidad del negocio" value={comp.quality.score != null ? `${comp.quality.score}/100` : null} reading={comp.quality.level} bands={d.tooltips.quality} /></h4>
            <ul className="comp fill">{comp.quality.rows.map((r) => (
              <li key={r.label}><span>{r.label}</span>
                {r.kind === "bar"
                  ? <><span className="comp-bar"><i className={`tone-bg-${toVTone(r.tone)}`} style={{ width: `${r.pct}%` }} /></span><span className="num">{r.value} / {r.max}</span></>
                  : <span className="muted">No concluyente</span>}</li>
            ))}</ul>
            {comp.quality.note && <p className="muted small">{comp.quality.note}</p>}
          </div>
          <div className="card surface" data-testid="comp-price">
            <h4>{cap(comp.price.title)} <span className={`num tone-${toVTone(comp.price.tone)}`}>{comp.price.score ?? "—"}/100</span>{comp.price.level && ` · ${comp.price.level}`}</h4>
            <ul className="comp fill">{comp.price.rows.map((r) => (
              <li key={r.label}><span>{r.label}</span>
                <span className="comp-bar signed"><i className={`tone-bg-${toVTone(r.tone)}`} style={{
                  width: `${(Math.abs(r.value) / comp.price.signed_max) * 50}%`, [r.value < 0 ? "right" : "left"]: "50%" }} /></span>
                <span className="num">{r.value > 0 ? `+${r.value}` : r.value < 0 ? `−${Math.abs(r.value)}` : "0"}</span></li>
            ))}</ul>
            {comp.price.note && <p className="muted small">{comp.price.note}</p>}
          </div>
        </div>
        <p className="muted small">{comp.caption}</p>
        <div className="dgrid three sub" style={{ "--rows": 3 } as React.CSSProperties} data-sym-row>
          {s.cards.map((k) => (
            <div key={k.key} className="card surface tile">
              <span className="muted small">{k.label}{d.tooltips[k.key] && (
                <> <MetricTip metricKey={k.key} label={k.label} value={k.state === "con_dato" ? `${k.value}${k.unit}` : null} reading={k.pill} bands={d.tooltips[k.key]} /></>)}</span>
              {k.state === "con_dato"
                ? <><span className={`tile-value num tone-${toVTone(k.tone)}`}>{k.value}{k.unit}</span>
                  <span className="tile-foot">{k.pill && <span className={`pill ${toVTone(k.tone)}`}>{k.pill}</span>} {k.delta && <span className="num">{k.delta}</span>} {k.bench && <span className="muted small">{k.bench}</span>}</span></>
                : <><span className="tile-value tone-neutral">{k.pill || STATE_LABELS[k.state as keyof typeof STATE_LABELS] || STATE_LABELS.sin_dato}</span>
                  <span className="tile-foot"><span className="muted small">{k.text || k.bench}</span></span></>}
            </div>
          ))}
        </div>
      </Section>

      <Section id="confianza" eyebrow="Conclusión" title={`Consistencia ${conf?.level ?? "sin medir"}`}>
        {conf ? (
          <div className="card surface">
            {conf.verdict_text && <p>{conf.verdict_text}</p>}
            {conf.plain.length > 0 && <ul className="stack">{conf.plain.map((t) => <li key={t}>{t}</li>)}</ul>}
            <dl className="kv">{conf.dimensions.map((x) => <div key={x.key} className="kv-row"><dt>{x.label}</dt><dd>{x.level}</dd></div>)}</dl>
            <p className="muted small">{conf.summary} El detalle está en{" "}
              <a data-nav href={chapterHref(symbol, "riesgos", "no-sabemos")}>Riesgos → Lo que no sabemos</a>.</p>
          </div>
        ) : <Missing title="Consistencia" reason="el análisis no pudo medir si los métodos y los datos coinciden" />}
      </Section>

      <Section id="vigilar" eyebrow="Conclusión" title="Qué vigilar">
        {c.highlights.length > 0 && (
          <div className={`dgrid${GRID[Math.min(c.highlights.length, GRID.length - 1)]}`} data-sym-row>
            {c.highlights.map((h) => (
              <div key={h.kind + h.text} className="card surface"><span className={`pill ${toVTone(h.tone)}`}>{cap(h.kicker)}</span>
                <p className="fill">{h.text}</p></div>
            ))}
          </div>
        )}
        {warnings.length > 0
          ? <div className="card surface"><h4>Advertencias del análisis ({warnings.length})</h4>
              <ul className="stack">{warnings.map((w) => <li key={w.reason}><strong>{w.reason}</strong> · {w.category}</li>)}</ul></div>
          : <Missing title="Advertencias" reason="el análisis no detecta ninguna" />}
        {pm && pm.items.length > 0
          ? <p className="segs-head"><strong>{pm.title}</strong> {pm.items.join("; ")}. <a data-nav href={chapterHref(symbol, "riesgos", "premortem")}>Pre-mortem completo</a>.</p>
          : <Missing title="Pre-mortem" reason="no aplica ninguna de sus condiciones" />}
      </Section>

      <Section id="informe" eyebrow="Conclusión" title="El informe completo">
        <p className="segs-head">El informe en PDF recoge el análisis entero con las mismas cifras.{" "}
          <PdfButton symbol={symbol} testId="pdf" /></p>
        {d.annex.items.length > 0 ? <AuditAnnex annex={d.annex} /> : <Missing title={d.annex.title} reason="sin códigos internos para esta empresa" />}
      </Section>

      <Methodology items={[
        { label: "Puntuaciones", text: comp.caption },
        { label: "Consistencia", text: conf?.summary },
      ]} />
    </div>
  </>);
}
