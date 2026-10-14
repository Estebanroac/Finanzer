"use client";

import type { StockAnalysis, YearRow } from "@/lib/api";
import { formatMoney, formatPct } from "@/lib/api";
import { useGrow } from "@/lib/useGrow";
import { AnnualBars, ChartPanel } from "../charts";
import { Collapsible, Help, Note } from "../ui";

type Col = { key: keyof YearRow; label: string; fmt: (v: number | null | undefined) => string };

/**
 * Histórico anual (dato bruto de los estados que usa el backend para los CAGR):
 * barras por serie con la variación interanual y el CAGR (display.charts.historical);
 * la tabla completa, a demanda. En pre-beneficio la serie de caja es FCF − SBC.
 */
export default function HistoricalTab({ data }: { data: StockAnalysis }) {
  const grown = useGrow();
  const rows = data.yearly_financials;
  const H = data.display.charts.historical;
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

  return (
    <div className="space-y-4">
      <ChartPanel grown={grown} title={<>Evolución anual<Help k="yearly" title="Histórico anual" /></>}
        aside={<span className="cz-hint">{H.years} ejercicios · variación frente al año anterior</span>}>
        {H.years ? <AnnualBars series={H.series} grown={grown} /> : (
          <p className="text-zinc-500 text-sm">Sin estados anuales disponibles.</p>
        )}
        <Note>Estados anuales del emisor (los mismos de los crecimientos a 3 años). ▲/▼: variación frente al ejercicio
          anterior; las barras rayadas son valores negativos.</Note>
      </ChartPanel>

      {rows.length > 0 && (
        <div className="cz-more">
          <Collapsible summary="Cifras por ejercicio">
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
          </Collapsible>
        </div>
      )}
    </div>
  );
}
