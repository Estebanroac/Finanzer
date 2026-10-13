"use client";

import type { StockAnalysis, YearRow } from "@/lib/api";
import { formatMoney, formatPct } from "@/lib/api";
import { Help, Note, Panel, PanelTitle } from "../ui";

type Col = { key: keyof YearRow; label: string; fmt: (v: number | null | undefined) => string };

/**
 * Histórico anual (decisión D de la etapa 9b): dato BRUTO de los estados anuales que
 * usa el backend para los CAGR. Sin colores ni lecturas de bandas: solo cifras, y un
 * gráfico en grises. En pre-beneficio se añaden la compensación en acciones y FCF − SBC.
 */
export default function HistoricalTab({ data }: { data: StockAnalysis }) {
  const rows = data.yearly_financials;
  // Columnas que no aplican al arquetipo (p. ej. FCF y márgenes en bancos): se dice, no "N/A".
  const na = data.display.sections.historical.not_applicable;
  const cell = (c: Col, r: YearRow) => {
    const v = r[c.key] as number | null | undefined;
    return v == null && na[c.key as string] ? na[c.key as string] : c.fmt(v);
  };
  const sbc = rows.some((r) => r.sbc !== undefined);
  const cols: Col[] = [
    { key: "revenue", label: "Ingresos", fmt: formatMoney },
    { key: "net_income", label: "Beneficio neto", fmt: formatMoney },
    { key: "free_cash_flow", label: "Flujo de caja libre", fmt: formatMoney },
    ...(sbc ? [{ key: "sbc", label: "Compensación en acciones", fmt: formatMoney } as Col,
      { key: "fcf_minus_sbc", label: "FCF − SBC", fmt: formatMoney } as Col] : []),
    { key: "gross_margin", label: "Margen bruto", fmt: formatPct },
    { key: "operating_margin", label: "Margen operativo", fmt: formatPct },
    { key: "net_margin", label: "Margen neto", fmt: formatPct },
    { key: "fcf_margin", label: "Margen FCF", fmt: formatPct },
    ...(sbc ? [{ key: "fcf_minus_sbc_margin", label: "Margen (FCF − SBC)", fmt: formatPct } as Col] : []),
  ];
  if (rows.length === 0) {
    return <Panel><p className="text-zinc-500 text-sm">Sin estados anuales disponibles.</p></Panel>;
  }
  const series: Col[] = cols.filter((c) => ["revenue", "net_income", sbc ? "fcf_minus_sbc" : "free_cash_flow"]
    .includes(c.key as string));
  const peak = Math.max(...rows.flatMap((r) => series.map((c) => Math.abs((r[c.key] as number | null) ?? 0))));

  return (
    <div className="space-y-4">
      <Panel>
        <PanelTitle aside={<Help k="yearly" title="Histórico anual" />}>Evolución anual</PanelTitle>
        <div className="fz-hist-chart" role="img" aria-label="Ingresos, beneficio neto y flujo de caja por ejercicio">
          {rows.map((r) => (
            <div key={r.year} className="fz-hist-year">
              <div className="fz-hist-bars">
                {series.map((c, i) => {
                  const v = (r[c.key] as number | null) ?? null;
                  const h = v == null || !peak ? 0 : (Math.abs(v) / peak) * 100;
                  return (
                    <span key={c.key as string} className={`fz-hist-bar s${i} ${v != null && v < 0 ? "is-neg" : ""}`}
                      style={{ height: `${h}%` }} title={`${c.label}: ${cell(c, r)}`} />
                  );
                })}
              </div>
              <span className="fz-hist-label">{r.year}</span>
            </div>
          ))}
        </div>
        <div className="fz-hist-legend">
          {series.map((c, i) => <span key={c.key as string}><i className={`s${i}`} />{c.label}</span>)}
          <span><i className="is-neg-swatch" />Valor negativo</span>
        </div>
      </Panel>

      <Panel>
        <PanelTitle>Cifras por ejercicio</PanelTitle>
        <div className="overflow-x-auto -mx-1 px-1">
          <table className="fz-hist-table">
            <thead>
              <tr><th>Concepto</th>{rows.map((r) => <th key={r.year}>{r.year}</th>)}</tr>
            </thead>
            <tbody>
              {cols.map((c) => (
                <tr key={c.key as string}>
                  <th>{c.label}</th>
                  {na[c.key as string] && rows.every((r) => r[c.key] == null) ? (
                    <td colSpan={rows.length} className="fz-hist-na">{na[c.key as string]}</td>
                  ) : rows.map((r) => (
                    <td key={r.year} className={na[c.key as string] && r[c.key] == null ? "fz-hist-na" : ""}>
                      {cell(c, r)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <Note>Estados anuales del emisor (los mismos de los crecimientos a 3 años). Dato bruto: sin lecturas ni colores.</Note>
      </Panel>
    </div>
  );
}
