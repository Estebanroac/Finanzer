"use client";
import { useEffect, useRef, useState } from "react";
import type { ScenarioInputs, ScenarioResponse, ScenarioUserAssumptions } from "@/lib/api";
import { postScenario } from "@/v2/lib/companyData";
import { estimateCur, pct, perShareCur, signedPct } from "@/v2/lib/format";
import { isAbort } from "@/v2/lib/http";
import { SENS_BAND_TONES, toVTone } from "@/v2/lib/tone";

const DEBOUNCE_MS = 250;
const bandTone = (b: number | null | undefined) => (b == null ? "none" : SENS_BAND_TONES[b] ?? "none");
/** V4b · 4: qué quiere decir el porqué del motor en una celda de la sensibilidad sin valor. */
const SENS_WHY: Record<string, string> = {
  "≤ 0": "con esos supuestos el valor por acción sale cero o negativo",
  fuera: "crecimiento o coste del capital fuera de los límites del análisis",
};
const PCT_STEP = 0.001;          // los controles se mueven de 0.1 en 0.1 puntos
type Preset = "pessimistic" | "base" | "optimistic";
const PRESETS: Array<[Preset, string]> = [["pessimistic", "Pesimista"], ["base", "Base"], ["optimistic", "Optimista"]];

/** Un supuesto: deslizador accesible con su número editable al lado (en %). */
function Control({ id, label, value, min, max, onChange }: {
  id: string; label: string; value: number; min: number; max: number; onChange: (v: number) => void;
}) {
  const [text, setText] = useState((value * 100).toFixed(1));
  useEffect(() => { setText((value * 100).toFixed(1)); }, [value]);
  return (
    <div className="ctl">
      <label htmlFor={id}>{label}</label>
      <input id={id} type="range" min={min} max={max} step={PCT_STEP} value={value}
             aria-valuetext={pct(value)} onChange={(e) => onChange(Number(e.target.value))} />
      <span className="ctl-num">
        <input type="number" aria-label={`${label} (%)`} value={text} step={0.1} min={(min * 100).toFixed(1)} max={(max * 100).toFixed(1)}
               onChange={(e) => setText(e.target.value)}
               onBlur={() => { const v = Number(text) / 100; if (Number.isFinite(v)) onChange(Math.min(max, Math.max(min, v))); }}
               onKeyDown={(e) => { if (e.key === "Enter") (e.target as HTMLInputElement).blur(); }} />%
      </span>
    </div>
  );
}

/**
 * Escenarios (maqueta 2): preajustes, cuatro controles y el resultado que calcula el motor (/api/v2/scenario):
 * valor por acción, diferencia con el precio, qué exige el precio con estos supuestos y la sensibilidad. Nunca cambia
 * el veredicto.
 */
export default function ScenarioPanel({ inputs }: { inputs: ScenarioInputs }) {
  const base = inputs.base!, b = inputs.bounds!;
  const baseA: ScenarioUserAssumptions = { high_growth_rate: base.high_growth_rate, discount_rate: base.discount_rate,
    terminal_growth: base.terminal_growth, fcf_margin: inputs.fcf_margin ?? null };
  const [a, setA] = useState<ScenarioUserAssumptions>(baseA);
  const [preset, setPreset] = useState<Preset | null>("base");
  const [res, setRes] = useState<ScenarioResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const ctl = useRef<AbortController | null>(null);

  useEffect(() => {
    const t = setTimeout(() => {
      ctl.current?.abort();
      const c = new AbortController();
      ctl.current = c;
      const assumptions: Record<string, number> = { high_growth_rate: a.high_growth_rate, discount_rate: a.discount_rate,
        terminal_growth: a.terminal_growth };
      if (a.fcf_margin != null) assumptions.fcf_margin = a.fcf_margin;
      // Un 422 trae el motivo del motor (`detail`) y se enseña tal cual (revisión V6, F17)
      postScenario({ inputs, assumptions }, c.signal).then((r) => { setRes(r); setErr(null); })
        .catch((e: Error) => { if (!isAbort(e)) setErr(e.message); });
    }, DEBOUNCE_MS);
    return () => clearTimeout(t);
  }, [a, inputs]);
  // Al desmontar (otra página), la petición en vuelo se cancela (revisión V6, F17).
  useEffect(() => () => ctl.current?.abort(), []);

  const set = (k: keyof ScenarioUserAssumptions) => (v: number) => { setPreset(null); setA((p) => ({ ...p, [k]: v })); };
  const choose = (p: Preset) => {
    setPreset(p);
    setA(p === "base" ? baseA : { ...inputs.presets![p] });
  };
  const price = inputs.price ?? null, cur = inputs.currency;
  const fv = res?.fair_value ?? null;
  const ig = res?.implied_growth;
  const scaleMax = Math.max(price ?? 0, fv ?? 0) || 1;
  return (
    <div className="dgrid scenario" data-sym-row data-testid="scenario">
      <div className="card surface">
        <div className="presets" role="group" aria-label="Preajustes">
          {PRESETS.map(([k, l]) => <button key={k} type="button" className="btn" aria-pressed={preset === k} onClick={() => choose(k)}>{l}</button>)}
        </div>
        <div className="fill">
          <Control id="sc-g" label="Crecimiento del flujo de caja (años 1–5)" value={a.high_growth_rate} min={b.growth[0]} max={b.growth[1]} onChange={set("high_growth_rate")} />
          <Control id="sc-t" label="Crecimiento a largo plazo" value={a.terminal_growth} min={b.terminal[0]} max={b.terminal[1]} onChange={set("terminal_growth")} />
          <Control id="sc-d" label="Coste del capital (WACC)" value={a.discount_rate} min={b.discount[0]} max={b.discount[1]} onChange={set("discount_rate")} />
          {b.fcf_margin && a.fcf_margin != null
            ? <Control id="sc-m" label="Margen de flujo de caja" value={a.fcf_margin} min={b.fcf_margin[0]} max={b.fcf_margin[1]} onChange={set("fcf_margin")} />
            : <p className="missing"><strong>Margen de flujo de caja:</strong> sin ingresos base con los que calcularlo.</p>}
          <p className="muted small">Valores iniciales = los del informe. Rangos acotados por el análisis; el margen, entre la mitad y vez y media del propio.</p>
        </div>
      </div>
      <div className="card surface" aria-live="polite">
        <h4>Resultado del escenario</h4>
        <div className="fill scenario-result">
          {err ? <p className="missing"><strong>Escenario:</strong> {err}</p>
            : !res ? <p className="missing" aria-busy="true">Calculando…</p>
            : res.status !== "ok" ? <p className="missing"><strong>Sin valor:</strong> {res.reason}</p>
            : (<>
              <p><span className="muted">Valor por acción</span><br /><span className="tile-value num" data-testid="scenario-value">{estimateCur(fv, cur)}</span>
                {res.upside != null && <span className={`num tone-${toVTone(res.upside_reading?.tone ?? res.upside_tone)}`}> {signedPct(res.upside)} frente al precio ({perShareCur(price, cur)})</span>}
                {res.upside_reading && <> <span className={`pill ${toVTone(res.upside_reading.tone)}`} data-testid="scenario-reading">{res.upside_reading.label}</span></>}</p>
              <div className="vbars" aria-hidden="true">
                <div><span className="vb-label">valor {estimateCur(fv, cur)}</span><span className={`vb val ${toVTone(res.upside_reading?.tone)}`} style={{ width: `${((fv ?? 0) / scaleMax) * 100}%` }} /></div>
                <div><span className="vb-label">precio {perShareCur(price, cur)}</span><span className="vb pr" style={{ width: `${((price ?? 0) / scaleMax) * 100}%` }} /></div>
              </div>
              <p data-testid="scenario-implied">
                <strong>Qué exige el precio:</strong>{" "}
                {ig?.state === "ok" && ig.g10 != null
                  ? <>un crecimiento del flujo de caja de {pct(ig.g10)} anual durante 10 años ({pct(ig.g_star)} los 5 primeros), con estos mismos supuestos de capital y largo plazo.</>
                  : ig?.reason ?? "sin DCF inverso con el que compararlo."}
              </p>
              {res.clamped.length > 0 && <p className="muted small">Recortado a los límites del análisis: {res.clamped.join(", ")}.</p>}
            </>)}
          <p className="small"><strong>Los escenarios son para explorar: no cambian el veredicto.</strong> El informe usa el escenario base.</p>
        </div>
      </div>
      {res?.sensitivity && (
        <div className="card surface span2">
          <h4>Sensibilidad · valor por acción según crecimiento (filas) y coste del capital (columnas)</h4>
          <div className="sens-wrap" tabIndex={0} role="region" aria-label="Sensibilidad del escenario">
          <table className="segtable sens" data-testid="scenario-sensitivity">
            <thead><tr><th scope="col" className="sens-corner" aria-label="Crecimiento (filas) y coste del capital (columnas)">g ↓ · WACC →</th>{res.sensitivity.discount.map((d) => <th key={d} scope="col" className="num">{pct(d)}</th>)}</tr></thead>
            <tbody>{[...res.sensitivity.growth].map((g, i) => ({ g, i, row: res.sensitivity!.values[i] ?? [] })).map(({ g, i, row }) => (
              <tr key={g}><th scope="row" className="num">{pct(g)}</th>{row.map((v, j) => (
                <td key={j} className={`num band-${bandTone(res.sensitivity!.bands?.[i]?.[j])}`}>{v == null ? <span className="muted" title={SENS_WHY[res.sensitivity!.why?.[i]?.[j] ?? ""]}>{res.sensitivity!.why?.[i]?.[j] ?? "Sin dato"}</span> : (<>
                  {/* revisión de COST: el redondeo del valor justo del informe (dos cifras), que ya cabe en un teléfono */}
                  {estimateCur(v, cur)}</>)}</td>
              ))}</tr>
            ))}</tbody>
          </table></div>
          {/* Revisión V6 (F17): el color de cada celda lo decide el motor (banda frente al precio, como en el informe) */}
          {res.sensitivity.band_labels && <p className="legend">{res.sensitivity.band_labels.map((l, k) => <span key={l}><i className={`sw zone-${SENS_BAND_TONES[k]}`} />{l}</span>)}</p>}
          <p className="muted small">El centro es tu escenario.
            {/* V4b · 4: una celda vacía dice por qué (del motor), nunca un «—» */}
            {res.sensitivity.why?.some((r) => r.some((w) => w === "≤ 0")) && <> «≤ 0»: {SENS_WHY["≤ 0"]}.</>}
            {res.sensitivity.why?.some((r) => r.some((w) => w === "fuera")) && <> «fuera»: {SENS_WHY.fuera}.</>}</p>
        </div>
      )}
    </div>
  );
}
