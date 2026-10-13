"use client";

import type { CompositionBlock, CompositionRow, Display } from "@/lib/api";
import { Help, Panel, PanelTitle, Pill, StateTag, ToneBar, toneClass } from "./ui";

/** Resumen ejecutivo (página 2 del PDF): tarjetas, composición de las dos puntuaciones y lectura. */
export default function SummarySection({ display }: { display: Display }) {
  const S = display.summary;
  const tips = display.tooltips;
  const ac = S.alert_counts;
  return (
    <div className="space-y-4 mb-10 fade-up delay-4">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
        {S.cards.map((c) => (
          <div key={c.key + c.label} className={`fz-card ${toneClass(c.state === "con_dato" ? c.tone : null)}`}>
            <div className="flex items-center justify-between gap-2">
              <span className="fz-kicker flex items-center gap-1.5">
                {c.label}
                <Help k={c.key} title={c.label} bands={tips[c.key]} value={`${c.value}${c.unit}`}
                  reading={c.state === "con_dato" && c.pill !== "—" ? { label: c.pill, tone: c.tone } : null}
                  readingAlt={display.readings[c.key]?.label} />
              </span>
              {c.state === "con_dato" ? <Pill tone={c.tone}>{c.pill}</Pill> : <StateTag state={c.state} />}
            </div>
            <div className="mt-2 flex items-baseline gap-1">
              <span className="text-3xl font-bold text-white tabular-nums">{c.value}</span>
              <span className="text-zinc-500">{c.unit}</span>
            </div>
            <div className="mt-1 text-[12px] text-zinc-500">
              {c.delta && <b className="fz-tone-fg mr-2">{c.delta}</b>}
              {c.bench}
            </div>
          </div>
        ))}
      </div>

      <Panel>
        <PanelTitle>Composición de las dos puntuaciones</PanelTitle>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 md:gap-8">
          <CompBlock b={S.composition.quality} signedMax={S.composition.price.signed_max} />
          <CompBlock b={S.composition.price} signedMax={S.composition.price.signed_max} />
        </div>
        <p className="fz-note mt-4">{S.composition.caption}</p>
        <p className="mt-2 text-[13px]">
          <b className="tone-pos fz-tone-fg">{ac.strengths}</b> fortaleza{ac.strengths !== 1 && "s"} ·{" "}
          <b className="tone-warn fz-tone-fg">{ac.warnings}</b> advertencia{ac.warnings !== 1 && "s"} ·{" "}
          <b className="tone-neg fz-tone-fg">{ac.red_flags}</b> riesgo{ac.red_flags !== 1 && "s"}
        </p>
      </Panel>

      {S.exec_items.length > 0 && (
        <Panel>
          <PanelTitle>Lectura del análisis</PanelTitle>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-x-10 gap-y-4">
            {S.exec_items.map((e) => (
              <div key={e.label}>
                <div className="text-[10px] font-semibold uppercase tracking-[0.12em] text-[#0cc06c] mb-1">{e.label}</div>
                <p className="text-sm text-zinc-300 leading-relaxed">{e.text}</p>
              </div>
            ))}
          </div>
        </Panel>
      )}
    </div>
  );
}

function CompBlock({ b, signedMax }: { b: CompositionBlock & { rows: CompositionRow[] }; signedMax: number }) {
  return (
    <div className={toneClass(b.tone)}>
      <div className="fz-kicker">{b.title}</div>
      <div className="flex items-baseline gap-2 mt-1 mb-1">
        <span className="text-2xl font-bold fz-tone-fg tabular-nums">{b.score ?? "—"}</span>
        <span className="text-zinc-500 text-sm">/100</span>
        <b className="text-sm fz-tone-fg">{b.level ?? "sin dato"}</b>
      </div>
      {b.note && <div className="text-[12px] tone-warn fz-tone-fg mb-2">{b.note}</div>}
      <div className="space-y-1.5 mt-2">
        {b.rows.map((r, i) => <CompRow key={i} r={r} signedMax={signedMax} />)}
      </div>
    </div>
  );
}

function CompRow({ r, signedMax }: { r: CompositionRow; signedMax: number }) {
  if (r.kind === "nc") {
    return (
      <div className="fz-comp-row">
        <span className="fz-comp-l">{r.label}</span>
        <span className="state-tag state-sin_dato">no concluyente</span>
        <span className="fz-comp-n">n/c</span>
      </div>
    );
  }
  if (r.kind === "signed") {
    const v = r.value;
    return (
      <div className="fz-comp-row">
        <span className="fz-comp-l">{r.label}</span>
        <ToneBar pct={(Math.abs(v) / signedMax) * 100} tone={r.tone} thin />
        <span className={`fz-comp-n ${toneClass(r.tone)} fz-tone-fg`}>{v > 0 ? `+${v}` : `${v}`}</span>
      </div>
    );
  }
  return (
    <div className="fz-comp-row">
      <span className="fz-comp-l">{r.label}</span>
      <ToneBar pct={r.pct} tone={r.tone} thin />
      <span className="fz-comp-n">{r.value}<span className="text-zinc-500">/{r.max}</span></span>
    </div>
  );
}
