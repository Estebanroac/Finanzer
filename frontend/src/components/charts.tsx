"use client";

import type { CSSProperties, ReactNode } from "react";
import type {
  AltmanChart, FairValueChart, FlowItem, GaugeChart, GrowthBar, HistSeries, LadderStep, MetricBands, Range52,
  Multiple, RowState, RunwayChart, ScoredItem, StructureChart, Tone, VsBench, Zone,
} from "@/lib/api";
import { STATE_LABELS } from "@/lib/generated/backendConfig";
import { useCountUp, useGrow } from "@/lib/useGrow";
import { Help, toneClass } from "./ui";

/*
 * Kit de gráficos de la web (etapa 9c): SVG y CSS a mano, sin librería.
 * Recupera la forma del sitio anterior (anillos con brillo, termómetros frente al
 * sector, escalas con zonas, cascada de márgenes, donut, barras anuales) pero no
 * decide nada: valores, zonas, lecturas y tonos llegan de display.charts. Aquí solo
 * hay geometría (posición = valor sobre el eje) y la traducción del tono a color.
 * Cada estado sin dato tiene su diseño propio (NotApplicable): nunca un panel vacío.
 */

type Tips = Record<string, MetricBands>;

const clamp01 = (x: number) => Math.min(1, Math.max(0, x));
/** Posición en % de `v` sobre el eje [lo, hi]. */
const at = (v: number, lo: number, hi: number) => (hi === lo ? 0 : clamp01((v - lo) / (hi - lo)) * 100);
/** Etiqueta de un marcador: el texto no se sale del panel en los extremos. */
const labelAt = (p: number) => Math.min(88, Math.max(12, p));
const lowerFirst = (t: string) => (t ? t[0].toLowerCase() + t.slice(1) : t);
const toneStyle = (tone: Tone | null | undefined): CSSProperties | undefined =>
  tone ? ({ "--tone": `var(--${tone})` } as CSSProperties) : undefined;

/** Número de un corte de zona (1.5, 0.8, 10): sin decimales de más. */
function tickTxt(n: number, unit = ""): string {
  const s = Number.isInteger(n) ? String(n) : n.toFixed(1);
  return `${s}${unit}`;
}

/* ────────────────────────── Estados sin dato ────────────────────────── */

const NA_ICON: Record<RowState, string> = { con_dato: "", no_aplica: "⊘", sin_dato: "∅", no_significativo: "≈" };

/** Estado propio de un gráfico que no aplica, no tiene dato o no es significativo (con su motivo). */
export function NotApplicable({ state, text, title, inline }: {
  state: RowState; text?: string | null; title?: string; inline?: boolean;
}) {
  const label = STATE_LABELS[state === "con_dato" ? "sin_dato" : state];
  return (
    <div className={`cz-na ${inline ? "is-inline" : ""}`} role="note">
      <span className="cz-na-ic" aria-hidden="true">{NA_ICON[state === "con_dato" ? "sin_dato" : state]}</span>
      <div className="min-w-0">
        <div className="cz-na-t">{title ? `${title} · ${label}` : label}</div>
        {text && <div className="cz-na-d">{text[0].toUpperCase() + text.slice(1)}</div>}
      </div>
    </div>
  );
}

/** Pastilla de lectura con punto luminoso (veredicto de un gráfico); el texto lleva la lectura. */
export function Badge({ tone, children }: { tone: Tone | null | undefined; children: ReactNode }) {
  return <span className={`cz-badge ${toneClass(tone)}`}>{children}</span>;
}

/** Panel con halo de color del tono (o de marca) y cabecera. */
export function ChartPanel({ title, aside, tone, children, className = "", grown }: {
  title?: ReactNode; aside?: ReactNode; tone?: Tone | null; children: ReactNode; className?: string; grown?: boolean;
}) {
  return (
    <section className={`cz-panel ${tone ? toneClass(tone) : ""} ${grown ? "viz-in" : ""} ${className}`}>
      {(title || aside) && (
        <div className="cz-head">
          {title ? <h3 className="cz-title">{title}</h3> : <span />}
          {aside}
        </div>
      )}
      {children}
    </section>
  );
}

/** Las 2–3 líneas de lectura bajo el gráfico. */
export function ReadingLines({ lines }: { lines: Array<string | null | undefined> }) {
  const ls = lines.filter((l): l is string => !!l);
  if (!ls.length) return null;
  return (
    <div className="cz-reading">
      {ls.map((l, i) => <p key={i} className="cz-lead">{l[0].toUpperCase() + l.slice(1)}</p>)}
    </div>
  );
}

/* ────────────────────────── Anillo animado ────────────────────────── */

/** Anillo con brillo y número que cuenta hacia arriba (puntuaciones, comparativa). */
export function Ring({ value, max, tone, size = 132, stroke = 11, caption }: {
  value: number | null; max: number; tone: Tone | null; size?: number; stroke?: number; caption?: string;
}) {
  const grown = useGrow();
  const n = useCountUp(value);
  const pct = value == null || !max ? 0 : clamp01(value / max) * 100;
  const r = (size - stroke) / 2;
  const c = size / 2;
  return (
    <div className={`cz-ring ${toneClass(value == null ? null : tone)}`} style={{ width: size, height: size }}
      role="img" aria-label={value == null ? "sin dato" : `${value} de ${max}`}>
      <span className="cz-ring-glow" aria-hidden="true" />
      <svg viewBox={`0 0 ${size} ${size}`} aria-hidden="true">
        <circle className="cz-ring-bg" cx={c} cy={c} r={r} strokeWidth={stroke} />
        <circle className="cz-ring-fg" cx={c} cy={c} r={r} strokeWidth={stroke} pathLength={100}
          strokeDasharray={100} strokeDashoffset={grown ? 100 - pct : 100} />
      </svg>
      <div className="cz-ring-c">
        <span className="cz-ring-n" style={{ fontSize: size * 0.3 }}>{n ?? "—"}</span>
        <span className="cz-ring-d">{caption ?? `/ ${max}`}</span>
      </div>
    </div>
  );
}

/* ────────────────────────── Escala con zonas ────────────────────────── */

interface Marker { value: number; label: string; valueTxt: string }

/**
 * Escala horizontal con las zonas de la lectura (del backend), la zona activa resaltada
 * por etiqueta, un marcador principal (punto que late) y una referencia (línea).
 */
export function ZoneScale({ zones, lo, hi, active, marker, reference, band, compact }: {
  zones: Zone[]; lo: number; hi: number; active: string | null | undefined; marker: Marker;
  reference?: Marker; band?: { from: number; to: number; label: string } | null; compact?: boolean;
}) {
  const p = at(marker.value, lo, hi);
  const rp = reference ? at(reference.value, lo, hi) : 0;
  return (
    <div className={`cz-scale ${compact ? "is-compact" : ""}`}>
      <div className="cz-mk" style={{ left: `${labelAt(p)}%` }}>
        <span className="cz-mk-lab">{marker.label}</span>
        <span className="cz-mk-val">{marker.valueTxt}</span>
      </div>
      <span className="cz-mk-dot" style={{ left: `${p}%`, transform: "translateX(-50%)" }} aria-hidden="true" />
      <div className="cz-zones" role="img"
        aria-label={`${marker.label} ${marker.valueTxt}${active ? `: ${active}` : ""}`}>
        {zones.map((z) => (
          <span key={z.label} className={`cz-zone ${toneClass(z.tone)} ${z.label === active ? "is-on" : ""}`}
            style={{ flex: `${Math.max(0, z.to - z.from)} 1 0` }} />
        ))}
      </div>
      {band && (
        <div className="relative h-[10px]" aria-hidden="true">
          <span className="cz-band" style={{ left: `${at(band.from, lo, hi)}%`,
            width: `${at(band.to, lo, hi) - at(band.from, lo, hi)}%` }} title={band.label} />
        </div>
      )}
      {reference && (
        <div className="relative h-[44px]">
          <div className="cz-ref" style={{ left: `${rp}%` }}>
            <span className="cz-ref-line" aria-hidden="true" />
          </div>
          <div className="cz-ref" style={{ left: `${labelAt(rp)}%`, top: 18 }}>
            <span className="cz-mk-lab">{reference.label}</span>
            <span className="cz-mk-val">{reference.valueTxt}</span>
          </div>
        </div>
      )}
      <div className="cz-zone-lbls" aria-hidden="true">
        {zones.map((z) => (
          <span key={z.label} className={`cz-zone-lbl ${toneClass(z.tone)} ${z.label === active ? "is-on" : ""}`}
            style={{ flex: `${Math.max(0, z.to - z.from)} 1 0` }} title={z.label}>{z.label}</span>
        ))}
      </div>
    </div>
  );
}

/* ─────────────── Valoración: precio frente al valor razonable ─────────────── */

export function FairValueScale({ fv, grown, tips }: { fv: FairValueChart; grown: boolean; tips: Tips }) {
  if (fv.state !== "con_dato" || !fv.zones || !fv.axis || fv.price == null || fv.fair_value == null) {
    return <NotApplicable state={fv.state} text={fv.text} title="Valor razonable (DCF)" />;
  }
  const lo = fv.axis[0];
  const hi = fv.axis[fv.axis.length - 1];
  const active = fv.badge?.label?.replace(" (fiabilidad baja)", "");
  // Etapa 9c: la escala y su insignia nombran el método (solo la lectura combinada de la cabecera va sin método).
  const method = fv.method ?? "DCF";
  return (
    <div className={grown ? "viz-in" : ""}>
      <div className="flex items-center justify-between gap-3 flex-wrap mb-1">
        <span className="cz-title">
          Precio frente al valor razonable ({method})
          <Help k="dcf_fair_value" title="Valor razonable (DCF)" bands={tips.dcf_upside} value={fv.upside_txt}
            reading={fv.badge ? { label: fv.badge.label, tone: fv.badge.tone } : null} text={fv.text} />
        </span>
        {fv.badge && <Badge tone={fv.badge.tone}>Según {method}: {lowerFirst(fv.badge.label)}</Badge>}
      </div>
      <ZoneScale zones={fv.zones} lo={lo} hi={hi} active={active}
        marker={{ value: fv.price, label: "Precio", valueTxt: fv.price_txt ?? "" }}
        reference={{ value: fv.fair_value, label: "Valor razonable", valueTxt: fv.fair_value_txt ?? "" }}
        band={fv.grid_low != null && fv.grid_high != null
          ? { from: fv.grid_low, to: fv.grid_high, label: "Rango del grid de sensibilidad" } : null} />
      <div className="cz-foot">
        <div className="cz-stat">
          <span className="cz-stat-k">Upside del DCF</span>
          <span className={`cz-stat-v ${toneClass(fv.badge?.tone)} fz-tone-fg`}>{fv.upside_txt}</span>
        </div>
        {fv.grid_low_txt && fv.grid_high_txt && (
          <div className="cz-stat">
            <span className="cz-stat-k">Rango del grid</span>
            <span className="cz-stat-v">{fv.grid_low_txt} – {fv.grid_high_txt}</span>
          </div>
        )}
        {fv.reliability && (
          <div className="cz-stat">
            <span className="cz-stat-k">Fiabilidad del DCF</span>
            <span className={`cz-stat-v ${toneClass(fv.reliability_tone)} fz-tone-fg`}>{fv.reliability}</span>
          </div>
        )}
      </div>
    </div>
  );
}

/** Composición del valor del DCF: explícito frente a terminal. */
export function DcfComposition({ comp, grown }: { comp: { explicit_pct: number; terminal_pct: number }; grown: boolean }) {
  const e = Math.max(0, Math.min(100, comp.explicit_pct));
  const t = Math.max(0, Math.min(100, comp.terminal_pct));
  return (
    <div>
      <div className="cz-dcfc" role="img" aria-label={`Valor explícito ${e.toFixed(0)}%, valor terminal ${t.toFixed(0)}%`}>
        <div className="cz-dcfc-s cz-dcfc-e" style={{ width: grown ? `${e}%` : 0 }}>{e.toFixed(0)}%</div>
        <div className="cz-dcfc-s cz-dcfc-t" style={{ width: grown ? `${t}%` : 0 }}>{t.toFixed(0)}%</div>
      </div>
      <div className="cz-dcfc-key">
        <span><i style={{ background: "var(--brand)" }} />Valor explícito · años proyectados</span>
        <span><i style={{ background: "rgba(255,255,255,0.14)" }} />Valor terminal · a perpetuidad</span>
      </div>
    </div>
  );
}

/* ─────────────── Métrica frente a la referencia (termómetro) ─────────────── */

/** Barra con el valor de la empresa, el marcador de la referencia y el chip de brecha. */
export function BenchBar({ item, grown, tips, refShort, dim }: {
  item: VsBench; grown: boolean; tips: Tips; refShort: string; dim?: boolean;
}) {
  const v = item.value ?? 0;
  const b = item.bench ?? null;
  const scale = Math.max(Math.abs(v), b ?? 0) * 1.3 || 1;
  const fill = clamp01(Math.max(0, v) / scale) * 100;
  const tick = b == null ? null : clamp01(b / scale) * 100;
  return (
    <div className={`cz-vs ${toneClass(item.tone)} ${dim ? "is-dim" : ""}`}>
      <div className="cz-vs-top">
        <span className="cz-vs-k">
          {item.label}
          <Help k={item.key} title={item.label} bands={tips[item.key]} value={item.value_txt}
            reading={item.reading ? { label: item.reading, tone: item.tone ?? null } : null} text={item.text} />
        </span>
        <span className="cz-vs-r">
          {item.gap_txt && <span className="cz-chip">{item.gap_txt} vs {refShort}</span>}
          <span className="cz-vs-v">{item.value_txt}</span>
        </span>
      </div>
      <div className="cz-track">
        <div className="cz-fill" style={{ width: grown ? `${fill}%` : 0 }} />
        {tick != null && <i className="cz-tick" style={{ left: `${tick}%` }} aria-hidden="true" />}
      </div>
      <div className="cz-vs-sub">
        <span>
          {dim && <span className="cz-info-tag">informativo, no puntúa</span>}
          {b != null ? `Referencia ${item.bench_txt}` : "Sin referencia"}
        </span>
        {item.reading && <b>{item.reading}</b>}
      </div>
    </div>
  );
}

/** Lista de termómetros + los que no aplican, agrupados en una línea con su motivo. */
export function BenchList({ items, grown, tips, refShort }: { items: VsBench[]; grown: boolean; tips: Tips; refShort: string }) {
  const shown = items.filter((i) => i.state === "con_dato");
  const rest = items.filter((i) => i.state !== "con_dato");
  return (
    <div>
      {shown.length > 0 && (
        <div className="cz-legend"><span><i />Marcador: referencia ({refShort})</span></div>
      )}
      {shown.map((i) => <BenchBar key={i.key} item={i} grown={grown} tips={tips} refShort={refShort} />)}
      {rest.length > 0 && (
        <div className={shown.length ? "mt-3" : ""}>
          {groupNa(rest).map((g) => (
            <div key={g.text ?? g.state} className="mb-2 last:mb-0">
              <NotApplicable inline state={g.state} title={g.labels.join(", ")} text={g.text} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/** Métrica que puntúa sin barra frente a la referencia: valor, lectura y su ajuste. */
function ScoredRow({ it, tips }: { it: ScoredItem; tips: Tips }) {
  return (
    <div className={`cz-sc ${toneClass(it.tone)}`}>
      <span className="cz-vs-k">
        {it.label}
        <Help k={it.key} title={it.label} bands={tips[it.key]} value={it.value_txt ?? undefined}
          reading={it.reading ? { label: it.reading, tone: it.tone } : null} text={it.reason} />
      </span>
      <span className="cz-vs-r">
        {it.reading && <span className="fz-pill">{it.reading}</span>}
        {it.sign && <span className="cz-sc-sign fz-tone-fg" title={it.in_block ? "ajuste individual: puntúa a través del bloque" : "ajuste a Valoración"}>{it.sign}</span>}
        <span className="cz-vs-v">{it.value_txt}</span>
      </span>
    </div>
  );
}

/**
 * Múltiplos de Valoración separados por su papel en el score: primero el bloque que puntúa
 * (con su ajuste total), luego lo que puntúa aparte y, tenues y rotulados, los informativos.
 */
export function MultiplesView({ items, block, scored, grown, tips, refShort }: {
  items: Multiple[]; block: { label: string; sign: string; tone: Tone; reason: string } | null; scored: ScoredItem[];
  grown: boolean; tips: Tips; refShort: string;
}) {
  const live = items.filter((i) => i.state === "con_dato");
  const members = live.filter((i) => i.role === "block");
  const memberRows = scored.filter((s) => s.in_block);
  const apart = [...live.filter((i) => i.role === "scored")];
  const apartRows = scored.filter((s) => !s.in_block);
  const info = live.filter((i) => i.role === "informative");
  const rest = items.filter((i) => i.state !== "con_dato");
  return (
    <div>
      {(members.length > 0 || memberRows.length > 0) && (
        <div className="cz-group">
          <div className="cz-group-h">
            <span className="cz-title">{block?.label ?? "Bloque de múltiplos"} · puntúa</span>
            {block && <span className={`cz-chip ${toneClass(block.tone)}`}>{block.sign} a Valoración</span>}
          </div>
          {members.length > 0 && <div className="cz-legend"><span><i />Marcador: referencia ({refShort})</span></div>}
          {members.map((i) => <BenchBar key={i.key} item={i} grown={grown} tips={tips} refShort={refShort} />)}
          {memberRows.map((s) => <ScoredRow key={s.key} it={s} tips={tips} />)}
          <p className="cz-group-n">Entre paréntesis, el ajuste individual de cada miembro: puntúa a través del bloque.</p>
        </div>
      )}
      {(apart.length > 0 || apartRows.length > 0) && (
        <div className="cz-group">
          <div className="cz-group-h"><span className="cz-title">Puntúan aparte</span></div>
          {apart.map((i) => <BenchBar key={i.key} item={i} grown={grown} tips={tips} refShort={refShort} />)}
          {apartRows.map((s) => <ScoredRow key={s.key} it={s} tips={tips} />)}
        </div>
      )}
      {info.length > 0 && (
        <div className="cz-group is-info">
          <div className="cz-group-h"><span className="cz-title">Informativos · no puntúan</span></div>
          {info.map((i) => <BenchBar key={i.key} item={i} grown={grown} tips={tips} refShort={refShort} dim />)}
        </div>
      )}
      {rest.length > 0 && (
        <div className="mt-3">
          {groupNa(rest).map((g) => (
            <div key={g.text ?? g.state} className="mb-2 last:mb-0">
              <NotApplicable inline state={g.state} title={g.labels.join(", ")} text={g.text} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/** Agrupa métricas sin dato por (estado, motivo) para no repetir el mismo aviso. */
export function groupNa<T extends { label: string; state: RowState; text?: string | null }>(xs: T[]) {
  const out: Array<{ state: RowState; text: string | null; labels: string[] }> = [];
  for (const x of xs) {
    const g = out.find((o) => o.state === x.state && o.text === (x.text ?? null));
    if (g) g.labels.push(x.label);
    else out.push({ state: x.state, text: x.text ?? null, labels: [x.label] });
  }
  return out;
}

/* ─────────────── Cascada de márgenes "de cada $1 de ingreso" ─────────────── */

export function MarginLadder({ revenueTxt, steps, grown, tips }: {
  revenueTxt: string | null; steps: LadderStep[]; grown: boolean; tips: Tips;
}) {
  const live = steps.filter((s) => s.state === "con_dato" && s.pct != null);
  const na = steps.filter((s) => s.state !== "con_dato");
  // Margen del paso anterior (el primero parte del 100% de los ingresos): la franja perdida.
  const prevOf = live.map((_, i) => (i === 0 ? 1 : Math.max(0, live[i - 1].pct ?? 0)));
  return (
    <div>
      <div className="cz-fall">
        <div className="cz-step">
          <div className="cz-step-top">
            <span className="cz-step-l">Ingresos</span>
            <span className="cz-step-v">{revenueTxt && <span className="cz-step-amt">{revenueTxt}</span>}100%</span>
          </div>
          <div className="cz-step-track"><div className="cz-step-fill is-base" style={{ width: grown ? "100%" : 0 }} /></div>
        </div>
        {live.map((s, i) => {
          const pct = s.pct ?? 0;
          const neg = pct < 0;
          const w = Math.min(100, Math.abs(pct) * 100);
          const lostFrom = Math.max(0, pct) * 100;
          const lost = Math.max(0, prevOf[i] * 100 - lostFrom);
          return (
            <div key={s.key} className={`cz-step ${i === live.length - 1 ? "is-net" : ""}`} style={toneStyle(s.tone)}>
              <div className="cz-step-top">
                <span className="cz-step-l">
                  {s.label}
                  <Help k={s.key} title={s.label} bands={tips[s.key]} value={s.pct_txt}
                    reading={s.reading ? { label: s.reading, tone: s.tone ?? null } : null} />
                </span>
                <span className="cz-step-v">
                  {s.amount_txt && <span className="cz-step-amt">{s.amount_txt}</span>}
                  {s.pct_txt}
                </span>
              </div>
              <div className="cz-step-track">
                {lost > 0 && <div className="cz-lost" style={{ left: `${lostFrom}%`, width: `${lost}%` }} aria-hidden="true" />}
                <div className={`cz-step-fill ${neg ? "is-neg" : ""}`} style={{ width: grown ? `${w}%` : 0 }} />
              </div>
              {(neg || s.reading) && (
                <div className="mt-1 text-[11.5px] text-zinc-500">
                  {neg ? "Margen negativo: pérdida sobre cada dólar de ingreso" : null}
                  {!neg && s.reading && <span className={`${toneClass(s.tone)} fz-tone-fg font-semibold`}>{s.reading}</span>}
                </div>
              )}
            </div>
          );
        })}
      </div>
      {na.length > 0 && (
        <div className="mt-4 space-y-2">
          {groupNa(na).map((g) => <NotApplicable key={g.labels.join()} inline state={g.state} title={g.labels.join(", ")} text={g.text} />)}
        </div>
      )}
    </div>
  );
}

/* ─────────────── Flujo de resultados (TTM) ─────────────── */

export function FlowCards({ flows, grown }: { flows: FlowItem[]; grown: boolean }) {
  return (
    <div className="cz-flow">
      {flows.map((f) => {
        if (f.state !== "con_dato" || f.amount == null) {
          return (
            <div key={f.key} className="cz-fc is-na">
              <span className="cz-fc-k">{f.label}</span>
              <span className="cz-fc-v">{STATE_LABELS[f.state === "con_dato" ? "sin_dato" : f.state]}</span>
              {f.text && <span className="cz-fc-p">{f.text}</span>}
            </div>
          );
        }
        const neg = f.sign === "neg";
        return (
          <div key={f.key} className="cz-fc">
            <span className="cz-fc-k">{f.label}</span>
            <span className={`cz-fc-v ${neg ? "is-neg" : ""}`}>{f.amount_txt}</span>
            <span className="cz-fc-p">{f.key === "revenue" ? "base: 100%" : `${f.pct_txt} de los ingresos`}{neg ? " · pérdida" : ""}</span>
            <span className="cz-fc-bar" aria-hidden="true">
              <i className={neg ? "is-neg" : ""} style={{ width: grown ? `${Math.min(100, Math.abs(f.pct_of_revenue ?? 0))}%` : 0 }} />
            </span>
          </div>
        );
      })}
    </div>
  );
}

/* ─────────────── Solidez: medidores con zonas ─────────────── */

export function GaugeView({ g, grown, tips }: { g: GaugeChart; grown: boolean; tips: Tips }) {
  const help = (
    <Help k={g.key} title={g.label} bands={tips[g.key]} value={g.value_txt}
      reading={g.reading ? { label: g.reading, tone: g.tone ?? null } : null} text={g.text} />
  );
  if (g.state !== "con_dato") {
    return (
      <div className="cz-g">
        <div className="cz-g-top"><span className="cz-g-l">{g.label}</span></div>
        <NotApplicable inline state={g.state} text={g.text} />
      </div>
    );
  }
  const head = (
    <div className="cz-g-top">
      <span className="cz-g-l">{g.label}{help}</span>
      <span className={`cz-g-r ${toneClass(g.tone)}`}>
        {g.reading && <span className="fz-pill">{g.reading}</span>}
        <span className="cz-g-v">{g.value_txt}</span>
      </span>
    </div>
  );
  if (g.informative || g.negative || g.net_cash || !g.zones || g.value == null || !g.axis_max) {
    const why = g.net_cash ? "Caja neta: la caja supera a la deuda, el ratio no se sitúa en la escala."
      : g.negative ? "Resultado operativo negativo: la cobertura no se sitúa en la escala."
        : g.informative ? "Dato informativo: sin lectura en este tipo de empresa." : null;
    return (
      <div className={`cz-g ${toneClass(g.tone)}`}>
        {head}
        {why && <div className="cz-g-note">{why}</div>}
        {g.text && <p className="cz-g-text">{g.text[0].toUpperCase() + g.text.slice(1)}.</p>}
      </div>
    );
  }
  const max = g.axis_max;
  const p = at(g.value, 0, max);
  const inner = g.zones.slice(0, -1);
  return (
    <div className={`cz-g ${toneClass(g.tone)}`}>
      {head}
      <div className="cz-g-track" role="img" aria-label={`${g.label} ${g.value_txt}: ${g.reading ?? ""}`}>
        <div className="cz-g-zones" aria-hidden="true">
          {g.zones.map((z) => (
            <span key={z.label} className={toneClass(z.tone)} style={{ flex: `${Math.max(0, z.to - z.from)} 1 0` }} title={z.label} />
          ))}
        </div>
        <div className="cz-g-fill" style={{ width: grown ? `${p}%` : 0 }} />
        <span className={`cz-g-pin ${g.clamped ? "is-clamped" : ""}`} style={{ left: grown ? `${p}%` : 0 }} aria-hidden="true" />
      </div>
      <div className="cz-g-ticks" aria-hidden="true">
        {inner.map((z) => <span key={z.label} style={{ left: `${at(z.to, 0, max)}%` }}>{tickTxt(z.to, g.unit ?? "")}</span>)}
      </div>
    </div>
  );
}

/** Runway de un pre-beneficio: escala en años o "autofinanciada". */
export function RunwayView({ rw, grown, tips }: { rw: RunwayChart; grown: boolean; tips: Tips }) {
  if (rw.state !== "con_dato") return <NotApplicable state={rw.state} text={rw.text} title="Runway" />;
  if (rw.self_funded || rw.years == null || !rw.zones || !rw.axis_max) {
    return (
      <div className={`cz-g-note ${toneClass(rw.tone)}`}>
        <span className="cz-ic" aria-hidden="true"><IconCheck /></span>
        <span><b className="fz-tone-fg">{rw.reading}</b>{rw.text ? ` · ${rw.text}` : ""}</span>
      </div>
    );
  }
  return (
    <GaugeView grown={grown} tips={tips} g={{ key: "runway", label: "Runway (años de caja)", state: "con_dato", value: rw.years,
      value_txt: rw.years_txt, axis_max: rw.axis_max, zones: rw.zones, unit: "", reading: rw.reading, tone: rw.tone,
      text: rw.text, clamped: rw.years > rw.axis_max }} />
  );
}

/** Estructura del balance: donut de los activos (deuda, patrimonio, otros pasivos) + deuda frente a caja. */
export function BalanceDonut({ s, grown }: { s: StructureChart; grown: boolean }) {
  if (s.state !== "con_dato" || s.debt_pct == null) return <NotApplicable state={s.state} title="Estructura del balance" />;
  const debt = clamp01(s.debt_pct / 100) * 100;
  const eqRaw = s.equity_pct ?? 0;
  const eq = Math.min(100 - debt, Math.max(0, eqRaw));
  const oth = Math.max(0, 100 - debt - eq);
  const seg = (len: number, start: number) => ({
    strokeDasharray: grown ? `${len} ${100 - len}` : `0 100`, strokeDashoffset: -start,
  });
  const big = Math.max(s.debt ?? 0, s.cash ?? 0) || 1;
  return (
    <div>
      <div className="cz-donut-wrap">
        <div className="cz-donut" role="img" aria-label={`Deuda ${debt.toFixed(0)}% de los activos`}>
          <svg viewBox="0 0 120 120" aria-hidden="true">
            <circle className="d-bg" cx="60" cy="60" r="50" />
            <circle className="d-oth" cx="60" cy="60" r="50" pathLength={100} style={seg(oth, debt + eq)} />
            <circle className="d-eq" cx="60" cy="60" r="50" pathLength={100} style={seg(eq, debt)} />
            <circle className="d-debt" cx="60" cy="60" r="50" pathLength={100} style={seg(debt, 0)} />
          </svg>
          <div className="cz-donut-c">
            <span className="cz-donut-n">{debt.toFixed(0)}<span className="text-[14px] text-zinc-500">%</span></span>
            <span className="cz-donut-cap">Deuda / activos</span>
          </div>
        </div>
        <div className="cz-key">
          <div className="cz-key-row"><i className="cz-key-sw" style={{ background: "#e4e4e7" }} /><span className="cz-key-k">Deuda</span>
            <span className="cz-key-v">{s.debt_txt}<span className="cz-key-s">{debt.toFixed(0)}%</span></span></div>
          <div className="cz-key-row"><i className="cz-key-sw" style={{ background: "var(--brand)" }} />
            <span className="cz-key-k">Patrimonio<Help k="total_equity" title="Patrimonio" /></span>
            <span className="cz-key-v">{s.equity_txt}<span className="cz-key-s">{eqRaw < 0 ? "negativo" : `${eq.toFixed(0)}%`}</span></span></div>
          <div className="cz-key-row"><i className="cz-key-sw" style={{ background: "#55555b" }} /><span className="cz-key-k">Otros pasivos</span>
            <span className="cz-key-v"><span className="cz-key-s">{oth.toFixed(0)}%</span></span></div>
          <div className="cz-key-row"><span className="cz-key-k">Activos totales</span><span className="cz-key-v">{s.assets_txt}</span></div>
        </div>
      </div>
      <div className="mt-5">
        <div className="cz-title mb-2">Deuda frente a caja</div>
        <div className="cz-dvc">
          <span className="cz-dvc-l">Deuda</span>
          <span className="cz-dvc-b is-debt" style={{ width: grown ? `${clamp01((s.debt ?? 0) / big) * 100}%` : 0 }} />
          <span className="cz-dvc-v">{s.debt_txt}</span>
          <span className="cz-dvc-l">Caja<Help k="cash" title="Efectivo" /></span>
          <span className="cz-dvc-b is-cash" style={{ width: grown ? `${clamp01((s.cash ?? 0) / big) * 100}%` : 0 }} />
          <span className="cz-dvc-v">{s.cash_txt}</span>
        </div>
        {s.net_debt_txt && (
          <p className="mt-3 text-[12.5px] text-zinc-400">
            Deuda neta (deuda − caja): <b className="text-zinc-100 tabular-nums">{s.net_debt_txt}</b>
            {(s.net_debt ?? 0) < 0 && " · la caja supera a la deuda"}
          </p>
        )}
      </div>
    </div>
  );
}

/* ─────────────── Crecimiento: barras de CAGR ─────────────── */

export function GrowthBars({ bars, grown }: { bars: GrowthBar[]; grown: boolean }) {
  const live = bars.filter((b) => b.state === "con_dato");
  const peak = Math.max(...live.map((b) => Math.abs(b.value ?? 0)), 0) || 1;
  const anyNeg = live.some((b) => (b.value ?? 0) < 0 || b.sustained_negative);
  const axis = anyNeg ? 50 : 0;
  return (
    <div>
      {bars.map((b) => {
        if (b.state !== "con_dato") {
          return (
            <div key={b.key} className="cz-gr">
              <span className="cz-gr-l">{b.label}</span>
              <div className="col-span-3 md:col-span-3"><NotApplicable inline state={b.state} text={b.text} /></div>
            </div>
          );
        }
        const v = b.value ?? 0;
        const neg = v < 0 || !!b.sustained_negative;
        const span = 100 - axis;
        const w = b.sustained_negative ? axis : (Math.abs(v) / peak) * (neg ? axis : span);
        return (
          <div key={b.key} className={`cz-gr ${toneClass(b.tone)}`}>
            <span className="cz-gr-l">{b.label}</span>
            <div className="cz-gr-track" role="img" aria-label={`${b.label}: ${b.value_txt ?? ""} ${b.reading ?? ""}`}>
              {anyNeg && <i className="cz-gr-axis" style={{ left: `${axis}%` }} aria-hidden="true" />}
              <div className={`cz-gr-fill ${neg ? "is-left" : ""} ${b.sustained_negative ? "is-hatch" : ""}`}
                style={neg ? { right: `${100 - axis}%`, width: grown ? `${w}%` : 0 } : { left: `${axis}%`, width: grown ? `${w}%` : 0 }} />
            </div>
            <span className="cz-gr-v">{b.sustained_negative ? "Negativo" : b.value_txt}</span>
            <span className="cz-gr-r">{b.reading}</span>
          </div>
        );
      })}
    </div>
  );
}

/* ─────────────── Rango de 52 semanas (contexto, sin juicio) ─────────────── */

export function Range52Bar({ r, mini, grown }: { r: Range52; mini?: boolean; grown: boolean }) {
  const p = clamp01(r.pos / 100) * 100;
  return (
    <div className={`cz-r52 ${mini ? "is-mini" : ""}`}>
      {!mini && <span className="cz-r52-lab" style={{ left: grown ? `${labelAt(p)}%` : "12%" }}>{r.price}</span>}
      <div className="cz-r52-track" role="img" aria-label={`Precio ${r.price} en el rango de 52 semanas (${r.low} – ${r.high}): ${Math.round(r.pos)}%`}>
        {!mini && r.zones.slice(0, -1).map((z, i) => <i key={i} className="cz-r52-seg" style={{ left: `${z.to}%` }} aria-hidden="true" />)}
        <span className="cz-r52-fill" style={{ width: grown ? `${p}%` : 0 }} />
        <span className="cz-r52-mk" style={{ left: grown ? `${p}%` : 0 }} aria-hidden="true" />
      </div>
      <div className="cz-r52-ends">
        <span><b>Mínimo 52s</b>{r.low}</span>
        <span className="text-right"><b>Máximo 52s</b>{r.high}</span>
      </div>
    </div>
  );
}

/* ─────────────── Evaluación institucional: Altman ─────────────── */

export function AltmanScale({ al, grown, tips }: { al: AltmanChart; grown: boolean; tips: Tips }) {
  if (al.state !== "con_dato" || !al.zones || al.value == null || !al.axis_max) {
    return <NotApplicable state={al.state} text={al.text} title="Altman Z-Score" />;
  }
  const z = al.zones.find((x) => x.label === al.zone);
  return (
    <div className={grown ? "viz-in" : ""}>
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <span className="cz-title">
          {al.model ?? "Altman Z-Score"}
          <Help k="altman" title="Altman Z-Score" bands={tips.altman} value={al.value_txt}
            reading={z ? { label: z.label, tone: z.tone } : null} text={al.text} />
        </span>
        {z && <Badge tone={z.tone}>{z.label}</Badge>}
      </div>
      <ZoneScale compact zones={al.zones} lo={0} hi={al.axis_max} active={al.zone}
        marker={{ value: al.value, label: "Z-Score", valueTxt: al.value_txt ?? "" }} />
    </div>
  );
}

/* ─────────────── Histórico: barras anuales con variación y CAGR ─────────────── */

const SERIES_ACC = ["#0cc06c", "#5ac8fa", "#bf9bff"];

export function AnnualBars({ series, grown }: { series: HistSeries[]; grown: boolean }) {
  return (
    <div className="cz-hist">
      {series.map((s, si) => {
        const acc = { "--acc": SERIES_ACC[si % SERIES_ACC.length] } as CSSProperties;
        if (s.state !== "con_dato" || !s.points) {
          return (
            <div key={s.key} className="cz-hs" style={acc}>
              <div className="cz-hs-head"><span className="cz-hs-t"><i />{s.label}</span></div>
              <NotApplicable state={s.state} text={s.text} />
            </div>
          );
        }
        const vals = s.points.map((p) => p.value ?? 0);
        const posMax = Math.max(0, ...vals);
        const negMax = Math.max(0, ...vals.map((v) => -v));
        const total = posMax + negMax || 1;
        return (
          <div key={s.key} className="cz-hs" style={acc}>
            <div className="cz-hs-head">
              <span className="cz-hs-t"><i />{s.label}</span>
              <span className="cz-hs-cagr">{s.cagr_txt ? `CAGR ${s.cagr_txt}` : "CAGR n/c"}</span>
            </div>
            <div className="cz-hs-plot" role="img" aria-label={`${s.label} por ejercicio: ${s.points.map((p) => `${p.year} ${p.value_txt}`).join(", ")}`}>
              {s.points.map((p) => {
                const v = p.value ?? 0;
                const up = (p.yoy_pct ?? 0) > 0;
                return (
                  <div key={p.year} className="cz-hs-col">
                    <span className={`cz-hs-yoy ${p.yoy_pct == null ? "" : up ? "is-up" : "is-down"}`}>
                      {p.yoy_txt ? `${up ? "▲" : "▼"} ${p.yoy_txt}` : ""}
                    </span>
                    <div className="cz-hs-pos" style={{ flex: `${posMax / total} 1 0` }}>
                      {v > 0 && <span className="cz-hs-bar" style={{ height: grown ? `${(v / posMax) * 100}%` : 0 }} />}
                    </div>
                    <span className="cz-hs-base" aria-hidden="true" />
                    <div className="cz-hs-neg" style={{ flex: `${negMax / total} 1 0` }}>
                      {v < 0 && <span className="cz-hs-bar is-neg" style={{ height: grown ? `${(-v / negMax) * 100}%` : 0 }} />}
                    </div>
                    <span className="cz-hs-yr">{p.year}</span>
                    <span className="cz-hs-val">{p.value_txt}</span>
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}

/* ─────────────── Iconos (alertas, estados) ─────────────── */

export function IconAlert() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" /><path d="M12 9v4M12 17h.01" />
    </svg>
  );
}
export function IconWarn() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="9.5" /><path d="M12 7.5v5M12 16.5h.01" />
    </svg>
  );
}
export function IconCheck() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 2.8 4.5 5.6v6.1c0 4.7 3.2 8.4 7.5 9.5 4.3-1.1 7.5-4.8 7.5-9.5V5.6z" /><path d="m8.8 12.2 2.2 2.2 4.3-4.6" />
    </svg>
  );
}

