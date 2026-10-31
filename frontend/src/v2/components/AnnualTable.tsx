"use client";
import { Fragment, useEffect, useRef } from "react";
import type { StockAnalysis, YearRow } from "@/lib/api";
import { moneyCur, pct } from "@/v2/lib/format";
import { SHEET_QUERY } from "./Floating";

const NS_NOTE = "primer o último ejercicio ≤ 0";

type Col = { key: keyof YearRow; label: string; money: boolean };
/** Las cifras de los estados que la web actual mostraba en su tabla; aquí, las que no trae ya una serie del motor. */
const AMOUNTS: Col[] = [
  { key: "revenue", label: "Ingresos", money: true }, { key: "net_income", label: "Beneficio neto", money: true },
  { key: "free_cash_flow", label: "Flujo de caja libre", money: true },
];
const MARGINS: Col[] = [
  { key: "sbc", label: "Compensación en acciones", money: true }, { key: "fcf_minus_sbc", label: "FCF − SBC", money: true },
  { key: "gross_margin", label: "Margen bruto", money: false }, { key: "operating_margin", label: "Margen operativo", money: false },
  { key: "net_margin", label: "Margen neto", money: false }, { key: "fcf_margin", label: "Margen FCF", money: false },
  { key: "fcf_minus_sbc_margin", label: "Margen (FCF − SBC)", money: false },
];

/**
 * Estados anuales que usa el motor para los crecimientos a 3 años (`yearly_financials` y `charts.historical`): cada
 * serie con su cifra, la variación frente al año anterior y el CAGR; debajo, márgenes y SBC. Todo a la vista.
 */
export default function AnnualTable({ a }: { a: StockAnalysis }) {
  const H = a.display.charts.historical, rows = a.yearly_financials ?? [];
  const na = a.display.sections.historical.not_applicable;
  const years = rows.map((r) => r.year);
  const inSeries = new Set(H.series.filter((s) => s.state === "con_dato").map((s) => s.key));
  const extra = [...AMOUNTS, ...MARGINS].filter((c) => !inSeries.has(c.key) && rows.some((r) => r[c.key] !== undefined));
  // v4 móvil (PM): si la tabla no cabe, arranca en el final (el último ejercicio y el CAGR); el concepto queda fijo
  const wrap = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const w = wrap.current;
    if (w && w.scrollWidth > w.clientWidth && window.matchMedia(SHEET_QUERY).matches) w.scrollLeft = w.scrollWidth;
  }, []);
  const cols = years.length + 2;
  /** Notas largas de una fila: dentro de su celda en escritorio; en el móvil, en una línea a todo el ancho bajo la fila. */
  const noteRow = (key: string, notes: Array<string | null | undefined>) => {
    const t = notes.filter(Boolean);
    return t.length ? <tr key={`${key}-note`} className="row-note"><td colSpan={cols}><span className="row-text">{t.join(" · ")}</span></td></tr> : null;
  };
  return (
    <div ref={wrap} className="techtable-wrap surface" tabIndex={0} role="region" aria-label="Estados anuales" data-scroll-ok>
      <table className="techtable annual numtable" data-testid="annual">
        <thead><tr><th scope="col">Concepto</th>{years.map((y) => <th key={y} scope="col" className="num">{y}</th>)}<th scope="col" className="num">CAGR</th></tr></thead>
        <tbody>
          {H.series.map((s) => (<Fragment key={s.key}>
            <tr><th scope="row">{s.label}</th>
              {s.state === "con_dato" && s.points
                ? <>{years.map((y) => { const p = s.points!.find((q) => q.year === y);
                    return <td key={y} data-label={String(y)} className="num">{p?.value_txt ?? "—"}{p?.yoy_txt && <span className="metric-sub">{p.yoy_txt}</span>}{p?.reason && <span className="metric-sub cell-note">{p.reason}</span>}</td>; })}
                    {/* V4b · 4 (PM): sin CAGR con dos o más ejercicios es que un extremo es ≤ 0 (el motor solo lo calcula con los
                        dos positivos): «n. s.» con su porqué */}
                    <td data-label="CAGR" className="num">{s.cagr_txt ? <>{s.cagr_txt}{s.cagr_note && <span className="metric-sub cell-note">{s.cagr_note}</span>}</> : <>n. s.<span className="metric-sub cell-note">{NS_NOTE}</span></>}</td></>
                : <td colSpan={years.length + 1} className="row-missing wide"><span className="row-text">{s.text ?? "Sin dato"}</span></td>}
            </tr>
            {s.state === "con_dato" && s.points && noteRow(s.key, [...years.map((y) => s.points!.find((q) => q.year === y)?.reason
              ? `${y}: ${s.points!.find((q) => q.year === y)!.reason}` : null), s.cagr_txt ? s.cagr_note : `CAGR n. s.: ${NS_NOTE}`])}
          </Fragment>))}
          {extra.map((c) => (
            <tr key={c.key}><th scope="row">{c.label}</th>
              {na[c.key] && rows.every((r) => r[c.key] == null)
                ? <td colSpan={years.length + 1} className="row-missing wide"><span className="row-text">{na[c.key]}</span></td>
                : <>{rows.map((r) => { const v = r[c.key] as number | null | undefined;
                    return <td key={r.year} data-label={String(r.year)} className="num">{v == null ? (na[c.key] ?? "—") : c.money ? moneyCur(v) : pct(v)}</td>; })}
                    {/* V4b · 4 (PM): un margen no se compone; la SBC no es una serie del motor con CAGR */}
                    <td data-label="CAGR" className="num muted small">{c.money ? "sin CAGR" : "no se compone"}</td></>}
            </tr>
          ))}
        </tbody>
      </table>
      {H.growth_currency_note && <p className="muted small">{H.growth_currency_note}</p>}
    </div>
  );
}
