import type { SegmentAxis } from "@/lib/api";
import { capFirst, moneyCur, pct } from "@/v2/lib/format";

/**
 * Un eje de segmentos (maqueta 2): barras del último ejercicio (peso del motor, `share_last`) y tabla por ejercicio.
 * Si no concilia con los ingresos consolidados del mismo concepto, lo dice con la diferencia del motor (`gap_pct`).
 */
export default function SegmentsChart({ axis, years, currency, title, className = "" }: {
  axis: Pick<SegmentAxis, "axis_label" | "segments" | "reconciles" | "gap_pct" | "notes">;
  years: string[]; currency: string | null; title?: string; className?: string;
}) {
  const last = years[years.length - 1];
  return (
    <div className={`card surface segcard ${className}`.trim()} data-testid="segments-axis">
      <h4>{capFirst(title ?? axis.axis_label)}</h4>
      <ul className="segbars" aria-label={`Peso de cada segmento en ${last}`}>
        {axis.segments.map((s) => (
          <li key={s.member}>
            <span className="seg-label">{s.label}</span>
            <span className="seg-track" aria-hidden="true"><span className="seg-fill" style={{ width: `${Math.max(1, s.share_last * 100)}%` }} /></span>
            <span className="num seg-val">{pct(s.share_last)}</span>
          </li>
        ))}
      </ul>
      {/* v4 móvil: si las cifras no caben, se desplaza con la primera columna fija (data-scroll-ok) */}
      <div className="segtable-wrap" data-scroll-ok tabIndex={0} role="region" aria-label={`Ingresos por ${axis.axis_label} y ejercicio`}>
        {/* v4 móvil (PM): tabla numérica (.numtable): cabecera una vez y cifras en columna, no fichas que repiten «FY» */}
        <table className="segtable numtable">
          <caption className="sr-only">Ingresos por segmento y ejercicio</caption>
          <thead><tr><th scope="col">Segmento</th>{years.map((y) => <th key={y} scope="col" className="num">FY{y}</th>)}</tr></thead>
          <tbody>
            {axis.segments.map((s) => (
              <tr key={s.member}><th scope="row">{s.label}</th>{years.map((y) => <td key={y} data-label={`FY${y}`} className="num">{moneyCur(s.values?.[y] ?? null, currency)}</td>)}</tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="seg-notes">
        {(!axis.reconciles && axis.gap_pct != null) && (
          <p className="muted small">
            Los segmentos suman un {pct(Math.abs(axis.gap_pct))} {axis.gap_pct > 0 ? "más" : "menos"} que los ingresos
            consolidados de este concepto (eliminaciones entre segmentos o partidas que no se asignan a ninguno).
          </p>
        )}
        {axis.notes.map((n) => <p key={n} className="muted small">{n}</p>)}
      </div>
    </div>
  );
}
