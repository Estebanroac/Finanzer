"use client";
import type { PageProps } from "./DepthPage";
import { profileNames } from "@/lib/names";
import { STATE_LABELS } from "@/lib/generated/backendConfig";
import { ScoreBreakdowns } from "@/v2/components/CompanyHeader";
import PillIndex from "@/v2/components/depth/PillIndex";
import Section, { Missing } from "@/v2/components/depth/Section";
import Methodology from "@/v2/components/depth/Methodology";
import MetricTip, { LabelTip } from "@/v2/components/depth/MetricTip";
import FlowTiles from "@/v2/components/depth/FlowTiles";

/** Etiquetas de cifra clave que no caben en una línea en la ficha normal (11rem): hasta 22 caracteres caben en el panel.
 *  El «?», que va pegado a la etiqueta, ocupa lo que unas 4 letras (TIP_CHARS). */
const LONG_TILE_LABEL = 24, TIP_CHARS = 4;
const PILLS = [{ id: "desglose", label: "Puntuaciones" }, { id: "ficha", label: "Ficha" }, { id: "clasificacion", label: "Clasificación" }, { id: "cifras", label: "Cifras clave" }];

/** Task 3 · La empresa: ficha de EDGAR, clasificación del motor y cifras clave (todo del contrato, sin cálculo). */
export default function Empresa({ analysis: a, symbol }: PageProps) {
  const d = a.display, cover = d.cover, ext = d.extended;
  const cp = ext?.company_profile;
  const hasCp = cp?.status === "ok" && cp.rows.length > 0;
  const prof = a.profile;
  const names = profileNames(a);   // V7: sector e industria en español, como en la cabecera
  const basics: Array<[string, string | null | undefined]> = [
    ["Nombre", prof.name], ["Ticker", symbol], ["Bolsa", prof.exchange], ["Sector", names.sector],
    ["Industria", names.industry], ["País", names.country], ["Moneda de cotización", prof.currency],
  ];
  const notes = [cover.as_of_note, cover.currency_note, ...cover.data_notices].filter((x): x is string => !!x);
  const missingKpis = cover.kpis.filter((k) => k.state !== "con_dato" && k.text);
  return (<>
    <PillIndex items={PILLS} />
    <div className="wrap depth-body">
      {/* V4b (PM): el desglose completo de las tres puntuaciones, aquí y a la vista; la cabecera de cada sección enlaza */}
      <Section id="desglose" eyebrow="La empresa" title="Cómo salen las tres puntuaciones">
        <ScoreBreakdowns analysis={a} />
      </Section>
      <Section id="ficha" eyebrow="La empresa" title="Ficha">
        {!hasCp && <Missing title="Ficha de la SEC" reason={cp?.reason ?? "el emisor no presenta estados en la SEC"} />}
        <div className={`dgrid${hasCp ? "" : " one"}`} data-sym-row>
          <div className="card surface">
            <h4>Datos de mercado</h4>
            <dl className="kv fill">
              {basics.filter(([, v]) => v).map(([k, v]) => <div key={k} className="kv-row"><dt>{k}</dt><dd>{v}</dd></div>)}
            </dl>
          </div>
          {hasCp && cp && (
            <div className="card surface">
              <h4>Registro en la SEC</h4>
              <dl className="kv fill">
                {cp.rows.map((r) => <div key={r.key} className="kv-row"><dt>{r.label}</dt><dd>{r.value}</dd></div>)}
              </dl>
              {cp.source && <p className="muted small">Fuente: {cp.source}</p>}
            </div>
          )}
        </div>
      </Section>

      <Section id="clasificacion" eyebrow="La empresa" title="Clasificación">
        {/* Una columna: dos textos de largo muy distinto, uno junto al otro, dejan un hueco al pie del corto */}
        <div className="dgrid one" data-sym-row>
          <div className="card surface">
            <h4>Tipo de empresa: {cover.archetype_label}</h4>
            <div className="fill stack">
              {cover.classification_notes.map((n) => <p key={n}>{n}</p>)}
              {cover.official_source_badge && (
                <p><span className="pill warn">{cover.official_source_badge.label}</span> {cover.official_source_badge.tooltip}</p>
              )}
            </div>
          </div>
          {notes.length > 0 && (
            <div className="card surface">
              <h4>Datos del análisis</h4>
              <div className="fill stack">{notes.map((n) => <p key={n}>{n}</p>)}</div>
            </div>
          )}
        </div>
      </Section>

      <Section id="cifras" eyebrow="La empresa" title="Cifras clave">
        <FlowTiles>
          {cover.kpis.map((k) => (
            // Una etiqueta larga («P/E reportado (último ejercicio)») se partía en dos líneas y, en las fichas vecinas de
            // la fila, dejaba 25 px entre la etiqueta y la cifra (verificación V1, UL): su ficha parte más ancha
            <div key={k.key} className={`tile surface${k.label.length + (a.display.tooltips[k.key] ? TIP_CHARS : 0) > LONG_TILE_LABEL ? " wide" : ""}${k.state === "con_dato" ? "" : " full"}`}>
              {/* v4 (PM; V1 a 375 px, MC.PA): el «?» va pegado a la etiqueta, no a la cifra: «EUR 397.00» y su botón no
                  cabían en media fila y la ficha bajaba la cifra de su vecina */}
              <span className="tile-label">{a.display.tooltips[k.key]
                ? <LabelTip text={k.label}><MetricTip metricKey={k.key} label={k.label} value={k.state === "con_dato" ? k.value : null} bands={a.display.tooltips[k.key]} /></LabelTip>
                : k.label}</span>
              <span className={`tile-value num${k.state === "con_dato" ? "" : " tone-neutral"}`}>
                {k.state === "con_dato" ? k.value : (STATE_LABELS[k.state as keyof typeof STATE_LABELS] ?? STATE_LABELS.sin_dato)}</span>
            </div>
          ))}
        </FlowTiles>
        {/* V4b · 4: sin cifra, el porqué del motor, en una nota bajo la fila (dentro de la ficha la alargaba y dejaba
            hueco en las vecinas) */}
        {missingKpis.length > 0 && <p className="muted small table-foot" data-testid="kpi-notes">
          {missingKpis.map((k, i) => <span key={k.key}>{i > 0 && " "}<strong>{k.label}:</strong> {k.text}.</span>)}</p>}
      </Section>

      <Methodology items={[
        { label: "Ficha", text: hasCp ? cp?.source : null },
        { label: "Datos de mercado", text: "Precio, capitalización, sector e industria del proveedor de mercado (Yahoo Finance)." },
        { label: "Cifras", text: d.methodology.ratios_text ? `Las cifras clave son ${d.methodology.ratios_text}.` : null },
      ]} />
    </div>
  </>);
}
