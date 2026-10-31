"use client";
import { useState } from "react";
import { moneyCur, pct, perShareCur, signedPct } from "@/v2/lib/format";

export interface HistoryRow {
  year: number; revenue: number | null; net_income: number | null; free_cash_flow: number | null;
  operating_margin: number | null; net_margin: number | null; revenue_growth: number | null;
  diluted_eps?: number | null; operating_cash_flow?: number | null; capex?: number | null; gap_before?: boolean;
  /** Textos del motor (display.extended.history_10y), si los hay: mandan sobre el formato del cliente. */
  txt?: { revenue_txt: string; net_income_txt: string; fcf_txt: string; operating_margin_txt: string;
          net_margin_txt: string; revenue_growth_txt: string; reasons?: Record<string, string> };
}

const W = 640, H = 260, PAD = { l: 8, r: 8, t: 12, b: 8 };
const BARS = [
  { key: "revenue", label: "Ingresos", cls: "b1" },
  { key: "net_income", label: "Beneficio neto", cls: "b2" },
  { key: "free_cash_flow", label: "Flujo de caja libre", cls: "b3" },
] as const;
const LINES = [
  { key: "operating_margin", label: "Margen operativo", cls: "l1" },
  { key: "net_margin", label: "Margen neto", cls: "l2" },
] as const;

/**
 * Historia de 10 años (spec §3.4): barras de ingresos, beneficio neto y flujo de caja libre, y líneas de márgenes
 * (eje propio, en %). Datos brutos de EDGAR (`history_10y`); el cliente solo dibuja y formatea. Un año se elige con
 * clic en su columna o con los botones de año (teclado); sus cifras van en la tabla de al lado.
 */
export default function HistoryChart({ rows, currency }: { rows: HistoryRow[]; currency: string | null }) {
  const [sel, setSel] = useState(rows.length - 1);
  if (!rows.length) return null;
  const vals = rows.flatMap((r) => BARS.map((b) => r[b.key] ?? 0));
  const hi = Math.max(0, ...vals), lo = Math.min(0, ...vals);
  const margins = rows.flatMap((r) => LINES.map((l) => r[l.key])).filter((v): v is number => v != null);
  const mhi = Math.max(0, ...margins), mlo = Math.min(0, ...margins);
  const ih = H - PAD.t - PAD.b, iw = W - PAD.l - PAD.r;
  const y = (v: number) => PAD.t + ((hi - v) / (hi - lo || 1)) * ih;
  const ym = (v: number) => PAD.t + ((mhi - v) / (mhi - mlo || 1)) * ih;
  const col = iw / rows.length;
  const bw = (col * 0.7) / BARS.length;
  const cx = (i: number) => PAD.l + col * i + col / 2;
  const r = rows[sel];
  const line = (k: (typeof LINES)[number]["key"]) => rows
    .map((row, i) => (row[k] == null ? null : `${cx(i)},${ym(row[k] as number)}`)).filter(Boolean).join(" ");
  return (<>
    <div className="card surface histcard">
      <div className="legend" aria-hidden="true">
        {BARS.map((b) => <span key={b.key}><i className={`sw ${b.cls}`} />{b.label}</span>)}
        {LINES.map((l) => <span key={l.key}><i className={`sw line ${l.cls}`} />{l.label} (%)</span>)}
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} className="histsvg" role="img"
           aria-label={`Ingresos, beneficio neto y flujo de caja libre de ${rows[0].year} a ${rows[rows.length - 1].year}`}>
        <line x1={PAD.l} x2={W - PAD.r} y1={y(0)} y2={y(0)} className="axis0" />
        {rows.map((row, i) => (
          <g key={row.year} onClick={() => setSel(i)} className={i === sel ? "sel" : undefined}>
            <rect x={PAD.l + col * i} y={PAD.t} width={col} height={ih} className="colhit" />
            {BARS.map((b, j) => {
              const v = row[b.key];
              if (v == null) return null;
              const x = cx(i) - (bw * BARS.length) / 2 + j * bw;
              return <rect key={b.key} x={x} width={bw - 1} y={Math.min(y(v), y(0))} height={Math.max(1, Math.abs(y(v) - y(0)))} className={b.cls} />;
            })}
          </g>
        ))}
        {LINES.map((l) => <polyline key={l.key} points={line(l.key)} className={`ml ${l.cls}`} />)}
      </svg>
      <div className="years" role="group" aria-label="Elegir ejercicio">
        {rows.map((row, i) => (
          <button key={row.year} type="button" aria-pressed={i === sel} onClick={() => setSel(i)}
                  onKeyDown={(e) => {
                    if (e.key === "ArrowRight") { e.preventDefault(); setSel(Math.min(rows.length - 1, i + 1)); (e.currentTarget.nextElementSibling as HTMLElement | null)?.focus(); }
                    if (e.key === "ArrowLeft") { e.preventDefault(); setSel(Math.max(0, i - 1)); (e.currentTarget.previousElementSibling as HTMLElement | null)?.focus(); }
                  }}>
            {row.year}{row.gap_before ? "*" : ""}
          </button>
        ))}
      </div>
    </div>
    <div className="card surface" data-testid="history-year">
      <h4>Ejercicio {r.year}</h4>
      <dl className="kv fill" aria-live="polite">
        {([
          ["Ingresos", r.txt?.revenue_txt ?? moneyCur(r.revenue, currency)],
          ["Crecimiento de los ingresos", r.gap_before ? "Sin dato (falta el ejercicio anterior)"
            : r.txt?.revenue_growth_txt ?? signedPct(r.revenue_growth)],
          ["Beneficio neto", r.txt?.net_income_txt ?? moneyCur(r.net_income, currency)],
          ["Flujo de caja operativo", moneyCur(r.operating_cash_flow, currency)],
          ["Capex", moneyCur(r.capex, currency), "capex"],
          ["Flujo de caja libre", r.txt?.fcf_txt ?? moneyCur(r.free_cash_flow, currency), "fcf"],
          ["Margen operativo", r.txt?.operating_margin_txt ?? pct(r.operating_margin), "operating_margin"],
          ["Margen neto", r.txt?.net_margin_txt ?? pct(r.net_margin)],
          ["BPA diluido", perShareCur(r.diluted_eps, currency), "diluted_eps"],
        ] as Array<[string, string, string?]>).map(([k, v, why]) => {
          // V4b · 4 (PM): una cifra que EDGAR no trae, con el porqué del motor (history_10y.rows[].reasons)
          const reason = v === "—" && why ? r.txt?.reasons?.[why] : undefined;
          return <div key={k} className="kv-row"><dt>{k}</dt>
            <dd className={reason ? "missing" : "num"}>{reason ? <><strong>Sin dato:</strong> {reason}</> : v}</dd></div>;
        })}
      </dl>
    </div>
  </>);
}
