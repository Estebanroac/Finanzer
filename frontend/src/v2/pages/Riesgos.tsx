"use client";
import type { PageProps } from "./DepthPage";
import { toVTone } from "@/v2/lib/tone";
import PillIndex from "@/v2/components/depth/PillIndex";
import Section, { Missing } from "@/v2/components/depth/Section";
import Methodology from "@/v2/components/depth/Methodology";
import Concentration from "@/v2/components/Concentration";
import { alertGroupLabel, RED_FLAGS_LABEL } from "@/v2/lib/story";

const PILLS = [{ id: "premortem", label: "Pre-mortem" }, { id: "alertas", label: "Alertas" }, { id: "sector", label: "Del sector" }, { id: "concentracion", label: "Concentración" },
  { id: "no-sabemos", label: "Lo que no sabemos" }, { id: "metodologia", label: "Metodología" }];
const EMPTY: Record<string, string> = { red_flags: "la única alerta roja es la de valoración extrema (la sola con evidencia en la prueba hacia atrás) y no se activa; no quiere decir que no haya riesgos: abajo, la concentración de los ingresos y lo que el análisis no sabe", warnings: "el análisis no detecta ninguna",
  strengths: "el análisis no detecta ninguna", balance: "nada que señalar en el balance", valuation: "sin lecturas de valoración" };

/** Task 9 · Riesgos: pre-mortem, alertas por grupo y lo que el análisis no sabe (consistencia y cobertura). */
export default function Riesgos({ analysis: a }: PageProps) {
  const d = a.display, pm = d.sections.valuation.premortem, al = d.sections.alerts, conf = d.consistency ?? d.confidence;
  const sr = d.sections.sector_risks;
  const full = al.groups.filter((g) => g.items.length > 0), empty = al.groups.filter((g) => g.items.length === 0);
  const count = (k: string) => (al.counts as unknown as Record<string, number>)[k];
  // Los motivos que ya cuentan las tarjetas de las dimensiones no se repiten
  const said = (t: string | null) => !!t && (conf?.dimensions ?? []).some((x) => x.text.includes(t));
  const reasons = (conf?.reasons ?? []).filter((r) => !said(r.text));
  const reasonTexts = new Set((conf?.reasons ?? []).map((r) => r.text));
  const extra = [...new Set([...(conf?.plain ?? []), ...d.cover.confidence_reasons])].filter((t) => !reasonTexts.has(t) && !said(t));
  return (<>
    <PillIndex items={PILLS} />
    <div className="wrap depth-body">
      <Section id="premortem" eyebrow="Riesgos" title={pm?.title ?? "Pre-mortem"}>
        {pm && pm.items.length ? (
          <div className="card surface" data-testid="premortem">
            <ul className="stack">{pm.items.map((t) => <li key={t}>{t}</li>)}</ul>
            <p className="muted small">{pm.note}</p>
          </div>
        ) : <Missing title="Pre-mortem" reason="no aplica ninguna de sus tres condiciones (un método intrínseco del precio, una calidad sólida o excelente con el margen por encima de su mediana, una deuda en el tramo elevado)" />}
      </Section>

      <Section id="alertas" eyebrow="Riesgos" title={`Alertas: ${RED_FLAGS_LABEL.toLowerCase()}, ${al.counts.red_flags}${al.counts.unmeasured ? ` (${al.counts.unmeasured})` : ""}; ${al.counts.warnings} advertencias y ${al.counts.strengths} fortalezas; aparte, sin color: estado del balance (${al.counts.balance ?? 0}) y lectura de valoración (${al.counts.valuation ?? 0})`}>
        {full.length > 0 && (
          // Un grupo debajo de otro: con una alerta en un grupo y seis en otro, en fila quedaría un hueco al pie
          <div className="dgrid one" data-sym-row>
            {full.map((g) => (
              <div key={g.key} className="card surface" data-group={g.key}>
                <h4><span className={`pill ${toVTone(g.tone)}`}>{alertGroupLabel(g.key, g.title)}</span> <span className="num">{count(g.key)}</span></h4>
                <ul className="alerts fill">{g.items.map((it) => (
                  <li key={it.reason}><span className="muted small">{it.category}</span>
                    <strong>{it.reason}</strong><span>{it.detail}</span></li>
                ))}</ul>
              </div>
            ))}
          </div>
        )}
        {empty.map((g) => <Missing key={g.key} title={`${alertGroupLabel(g.key, g.title)}: 0`} reason={EMPTY[g.key] ?? "sin elementos"} />)}
      </Section>

      {/* F13 · paso 10: riesgos del sector, aparte de las alertas y sin puntuar */}
      <Section id="sector" eyebrow="Riesgos" title="Riesgos del sector (no puntúan)">
        {sr && sr.items.length > 0 ? (
          <div className="dgrid one" data-sym-row>
            {sr.items.map((x) => (
              <div key={x.key} className="card surface" data-sector-risk={x.level}>
                <h4><span className="pill warn">{x.level === "empresa" ? "De la empresa" : "De la industria"}</span> {x.title}</h4>
                {x.label && <p className="muted small">{x.label}</p>}
                <p className="fill">{x.text}</p>
              </div>
            ))}
            {sr.note && <p className="muted small">{sr.note}</p>}
          </div>
        ) : <Missing title="Riesgos del sector: 0" reason="ningún dato dispara un riesgo de la empresa y su industria no tiene uno de la lista cerrada que la alcance" />}
        {sr?.not_measured && <p className="muted small">No medido: {sr.not_measured}.</p>}
      </Section>

      {/* V7 · P2: de dónde depende la empresa (hechos del informe anual, enlazados a la página Negocio) */}
      <Section id="concentracion" eyebrow="Riesgos" title="Concentración de los ingresos">
        <Concentration symbol={a.symbol} />
      </Section>

      <Section id="no-sabemos" eyebrow="Riesgos" title="Lo que no sabemos">
        {conf ? (<>
          <p className="segs-head">{conf.summary}</p>
          <div className="dgrid" data-sym-row>
            {conf.dimensions.map((x) => (
              <div key={x.key} className="card surface">
                <h4>{x.label} <span className="pill neutral">{x.level}</span></h4>
                <p className="fill">{x.text}</p>
              </div>
            ))}
          </div>
          {reasons.length > 0 && (
            <div className="card surface"><h4>Por qué es mixta</h4>
              <ul className="stack">{reasons.map((r) => <li key={r.dimension + r.text}><strong>{r.dimension}</strong> ({r.level.replace("_", " ")}): {r.text}</li>)}</ul></div>
          )}
          {extra.length > 0 && <ul className="stack">{extra.map((t) => <li key={t}>{t}</li>)}</ul>}
        </>) : <Missing title="Consistencia" reason="el análisis no pudo medir si los métodos y los datos coinciden" />}
        {d.cover.coverage_notes.length > 0
          ? <div className="card surface"><h4>Cobertura de los datos</h4><ul className="stack">{d.cover.coverage_notes.map((t) => <li key={t}>{t}</li>)}</ul></div>
          : <Missing title="Cobertura de los datos" reason="el análisis no deja notas de cobertura para esta empresa" />}
      </Section>

      <Methodology items={[
        { label: "Pre-mortem", text: pm?.note },
        { label: "Alertas", text: "Las alertas salen de las mismas reglas que puntúan el análisis: riesgos (banderas rojas), advertencias y fortalezas, cada una con la cifra que la dispara." },
        { label: "Consistencia", text: conf?.summary },
      ]} />
    </div>
  </>);
}
