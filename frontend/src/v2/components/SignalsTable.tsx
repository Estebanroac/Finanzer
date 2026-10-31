import type { Sections } from "@/lib/api";
import { toVTone } from "@/v2/lib/tone";

/** Señales de mercado (`sections.market.rows`): contexto, no puntúan. La usan La acción y Actualidad. */
export default function SignalsTable({ market }: { market: NonNullable<Sections["market"]> }) {
  return (
    <div className="techtable-wrap surface" tabIndex={0} role="region" aria-label="Señales de mercado">
      {/* v4 móvil (PM): stack-head: la cabecera una vez y cada señal con su cifra en la misma línea; el texto, debajo */}
      <table className="techtable stack-sm stack-head" style={{ "--stack-cols": 1, "--stack-template": "minmax(0, 1fr) minmax(0, max-content)" } as React.CSSProperties} data-testid="signals">
        <thead><tr><th scope="col">Señal</th><th scope="col" className="num">Valor</th><th scope="col" className="stack-wide">Qué dice</th></tr></thead>
        <tbody>{market.rows.map((r) => (
          <tr key={r.key}><th scope="row"><span className="metric-name">{r.label}</span></th>
            <td data-label="Valor" className={`num tone-${toVTone(r.tone)}`}>{r.value}</td><td className="wide">{r.text}</td></tr>
        ))}</tbody>
      </table>
    </div>
  );
}
