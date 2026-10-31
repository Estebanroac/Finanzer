"use client";
import { useEffect, useState } from "react";
import type { PageProps } from "./DepthPage";
import type { SegmentsResponse } from "@/lib/api";
import { fetchSegments } from "@/v2/lib/companyData";
import { toVTone } from "@/v2/lib/tone";
import { pct } from "@/v2/lib/format";
import AnnualTable from "@/v2/components/AnnualTable";
import PillIndex from "@/v2/components/depth/PillIndex";
import Section, { Missing } from "@/v2/components/depth/Section";
import Methodology from "@/v2/components/depth/Methodology";
import SegmentsChart from "@/v2/components/SegmentsChart";
import HistoryChart, { type HistoryRow } from "@/v2/components/HistoryChart";
import { isAbort } from "@/v2/lib/http";
import FlowTiles from "@/v2/components/depth/FlowTiles";

/** La base de la escalera de márgenes: los ingresos son el 100 %. */
const WHOLE = 1;
const PILLS = [{ id: "segmentos", label: "Segmentos" }, { id: "margenes", label: "Márgenes" }, { id: "historia", label: "Historia de 10 años" },
  { id: "estados", label: "Estados anuales" }];

function Segments({ symbol }: { symbol: string }) {
  const [seg, setSeg] = useState<SegmentsResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);
  // Revisión V6 (F12): caché del módulo y cancelación al desmontar.
  useEffect(() => {
    const ac = new AbortController();
    fetchSegments(symbol, ac.signal).then(setSeg).catch((e: Error) => { if (!isAbort(e)) setErr(e.message); });
    return () => ac.abort();
  }, [symbol]);
  if (err) return <Missing title="Ingresos por segmento" reason={err} />;
  if (!seg) return <p className="missing" aria-busy="true">Cargando los ingresos por segmento de la SEC…</p>;
  // Revisión V6 (F15): listas que faltan o vienen vacías no tumban la página (cada una, vacía por defecto)
  const segments = seg.segments ?? [], years = seg.fiscal_years ?? [];
  const dropped = (seg.dropped_axes ?? []).map((d) => (
    <p key={d.axis} className="missing" data-testid="dropped-axis"><strong>Eje descartado ({d.axis_label}):</strong> {d.reason}</p>
  ));
  if (seg.status !== "ok" || !segments.length || !years.length)
    return (<><Missing title="Ingresos por segmento" reason={seg.status !== "ok" ? seg.reason : "el informe no trae segmentos con importes"} />{dropped}</>);
  const okAxis = (ax: SegmentsResponse["secondary"]) => !!ax && Array.isArray(ax.segments) && ax.segments.length > 0;
  const main = { axis: seg.axis ?? "main", axis_label: seg.axis_label ?? "Segmentos", segments,
                 reconciles: seg.reconciles, gap_pct: seg.gap_pct, notes: seg.notes ?? [],
                 title: `${seg.axis_label ?? "Segmentos"} · eje principal` };
  const axes: Array<typeof main | NonNullable<SegmentsResponse["secondary"]>> =
    [main, ...(okAxis(seg.secondary) ? [seg.secondary!] : []), ...(seg.others ?? []).filter(okAxis)]
      .map((ax) => ({ ...ax, notes: ax.notes ?? [] }));
  const sameShape = new Set(axes.map((ax) => ax.segments.length)).size === 1;
  const src = seg.source;
  return (<>
    <p className="segs-head" data-testid="segments-coverage">
      <strong>{seg.concept_label}</strong>
      {src && <span className="muted"> · {src.form} presentado el {src.filed} (ejercicio a {src.period_end})</span>}
      {/* la nota de cobertura es una frase: texto con el tono de aviso, no pastilla (las pastillas no se parten) */}
      {seg.coverage_note && <span> · <strong className="tone-warn">{seg.coverage_note}</strong></span>}
    </p>
    {/* Rejilla interna compartida (título · barras · tabla · notas) solo si los ejes tienen los mismos segmentos. v4 (PM):
        con distinto número, una debajo de otra, cada una a su medida: estirar la corta separaba sus barras (espacio muerto) */}
    <div className={sameShape ? "dgrid sub" : "dgrid one"} style={{ "--rows": 4 } as React.CSSProperties} data-sym-row>
      {axes.map((ax, i) => (
        <SegmentsChart key={ax.axis} axis={ax} years={years} currency={seg.currency}
          title={"title" in ax ? ax.title : undefined} className={sameShape && axes.length % 2 === 1 && i === axes.length - 1 ? "span2" : ""} />
      ))}
    </div>
    {dropped}
  </>);
}

/** Task 4 · Cómo gana dinero: segmentos (SEC), márgenes y flujo de resultados (motor) e historia de 10 años (EDGAR). */
export default function Negocio({ analysis: a, symbol }: PageProps) {
  const d = a.display, ch = d.charts, prof = d.sections.profitability;
  const ladder = ch.profitability.margin_ladder;
  const flow = ch.results_flow;
  const h10 = a.history_10y;
  const h10txt = d.extended?.history_10y;
  const rows: HistoryRow[] = (h10?.rows ?? []).map((r) => ({ ...r, txt: h10txt?.rows.find((t) => t.year === r.year) }));
  const allFigures = prof.figures.flatMap((f) => [[f[0], f[1]], [f[2], f[3]]]).filter(([l, v]) => l && v);
  // Una cifra lleva algún dígito; lo demás es el motivo del motor ("No aplica a bancos…"): va en una línea por motivo
  const figures = allFigures.filter(([, v]) => /\d/.test(v));
  const absent = new Map<string, string[]>();
  allFigures.filter(([, v]) => !/\d/.test(v)).forEach(([l, v]) => absent.set(v, [...(absent.get(v) ?? []), l]));
  return (<>
    <PillIndex items={PILLS} />
    <div className="wrap depth-body">
      <Section id="segmentos" eyebrow="Cómo gana dinero" title="Ingresos por segmento">
        <Segments symbol={symbol} />
      </Section>

      <Section id="margenes" eyebrow="Cómo gana dinero" title="Márgenes y flujo de resultados">
        <div className="dgrid" data-sym-row>
          <div className="card surface">
            <h4>Escalera de márgenes{ladder.revenue_txt ? ` · sobre ${ladder.revenue_txt} de ingresos${ladder.period ? ` (${ladder.period.code})` : ""}` : ""}</h4>
            <ul className="ladder fill">
              {/* v4 (PM): la base de la escalera, los ingresos (el 100 %), como primera fila: las mismas filas que la tarjeta
                  vecina («De los ingresos al flujo de caja libre»), con el mismo ritmo y sin estirar las barras */}
              {ladder.revenue_txt && (
                <li key="revenue">
                  <span className="seg-label">Ingresos</span>
                  <span className="seg-track" aria-hidden="true"><span className="seg-fill" style={{ width: "100%" }} /></span>
                  <span className="num seg-val">{pct(WHOLE)}</span>
                  <span className="num muted seg-amt">{ladder.revenue_txt}</span>
                </li>
              )}
              {ladder.steps.map((s) => s.state === "con_dato" ? (
                <li key={s.key}>
                  <span className="seg-label">{s.label}</span>
                  <span className="seg-track" aria-hidden="true"><span className={`seg-fill ${toVTone(s.tone)}`} style={{ width: `${Math.max(1, Math.min(100, (s.pct ?? 0) * 100))}%` }} /></span>
                  <span className="num seg-val">{s.pct_txt}</span>
                  <span className="num muted seg-amt">{s.amount_txt ?? ""}</span>
                  {s.reading ? <span className={`pill ${toVTone(s.tone)}`}>{s.reading}</span>
                    : <span className="pill neutral">Sin referencia</span>}
                </li>
              ) : <li key={s.key} data-missing><strong>{s.label}:</strong> {s.text ?? "Sin dato"}</li>)}
            </ul>
          </div>
          <div className="card surface">
            <h4>De los ingresos al flujo de caja libre (12 meses)</h4>
            <dl className="kv fill">
              {flow.map((f) => (
                <div key={f.key} className="kv-row">
                  <dt>{f.label}</dt>
                  <dd className="num">{f.state === "con_dato" ? `${f.amount_txt ?? "—"}${f.pct_txt ? ` · ${f.pct_txt}` : ""}` : (f.text ?? "Sin dato")}</dd>
                </div>
              ))}
            </dl>
          </div>
        </div>
        <FlowTiles>
          {figures.map(([l, v]) => <div key={l} className="tile surface"><span className="tile-label">{l}</span><span className="tile-value num">{v}</span></div>)}
        </FlowTiles>
        {[...absent].map(([why, labels]) => <Missing key={why} title={labels.join(", ")} reason={why.charAt(0).toLowerCase() + why.slice(1)} />)}
        {/* V7 · P4: el DuPont (de dónde sale la rentabilidad sobre el capital) va en Calidad, con las demás lecturas de
            rentabilidad; aquí, el margen de flujo de caja, que sí dice cómo se convierten los ingresos en caja */}
        {(prof.quality_readings ?? []).some((q) => q.key === "fcf_margin") && (
          <div className="dgrid one" data-sym-row>
            {(prof.quality_readings ?? []).filter((q) => q.key === "fcf_margin").map((q) => (
              <div key={q.key} className="card surface"><h4>{q.label}</h4><p className="fill">{q.text}</p></div>
            ))}
          </div>
        )}
      </Section>

      <Section id="historia" eyebrow="Cómo gana dinero" title="Historia de 10 años">
        {h10?.status === "ok" && rows.length > 0 ? (<>
          <p className="muted small">
            Cifras en {h10.currency ?? "la moneda de los estados"} (moneda de los estados)
            {h10.reason ? ` · ${h10.reason}` : ""}{rows.some((r) => r.gap_before) ? " · * falta el ejercicio anterior en EDGAR: sin crecimiento." : ""}
            {" "}La historia de EDGAR no trae el número de acciones ni la deuda de cada año.
          </p>
          <div className="dgrid hist" data-sym-row><HistoryChart rows={rows} currency={h10.currency} /></div>
        </>) : <Missing title="Historia de 10 años" reason={h10?.reason ?? h10txt?.reason} />}
      </Section>

      <Section id="estados" eyebrow="Cómo gana dinero" title="Estados anuales">
        {a.yearly_financials?.length
          ? <><p className="segs-head">Los ejercicios con que el análisis calcula los crecimientos a 3 años, con la variación frente al año anterior y la tasa anual compuesta (CAGR).</p>
              <AnnualTable a={a} /></>
          : <Missing title="Estados anuales" reason="sin estados anuales del emisor" />}
      </Section>

      <Methodology items={[
        { label: "Segmentos", text: "Hechos XBRL con dimensión de segmento de la instancia del último informe anual en la SEC (10-K, 20-F o 40-F)." },
        { label: "Márgenes", text: d.methodology.ratios_text ? `Márgenes y flujo de resultados: ${d.methodology.ratios_text}.` : null },
        { label: "Historia", text: h10?.source },
      ]} />
    </div>
  </>);
}
