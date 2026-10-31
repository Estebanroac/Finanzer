import type { BreakdownCategory } from "@/lib/api";
import { toVTone } from "@/v2/lib/tone";

/** Una categoría de la puntuación (institutional.breakdown): sus puntos y cada indicador con su ajuste y su motivo. */
export default function BreakdownTable({ cat }: { cat: BreakdownCategory }) {
  return (
    <div className="techtable-wrap surface" data-testid={`breakdown-${cat.name}`} tabIndex={0} role="region" aria-label={`Desglose de ${cat.name}`}>
      {/* v4 móvil (PM): stack-head: la cabecera una vez; indicador, valor y ajuste en una línea y el motivo debajo */}
      <table className="techtable bdtable stack-sm stack-head" style={{ "--stack-cols": 2, "--stack-template": "minmax(0, 1fr) minmax(0, max-content) max-content" } as React.CSSProperties}>
        <caption><strong>{cat.name}</strong> · {/* F8 · P3: la no concluyente no enseña puntos; su texto ya dice que queda fuera. */}
          {cat.text ?? <span className={`tone-${toVTone(cat.tone)}`}>{cat.score_txt}</span>}</caption>
        <colgroup><col className="b-metric" /><col className="b-val" /><col className="b-adj" /><col className="b-why" /></colgroup>
        <thead><tr><th scope="col">Indicador</th><th scope="col" className="num">Valor</th><th scope="col" className="num">Ajuste</th><th scope="col" className="stack-wide">Motivo</th></tr></thead>
        <tbody>{cat.items.map((i) => {
          // V4b · 4 (PM): un ajuste que no aplica a este tipo de empresa dice «No aplica» (y a qué indicadores) con su
          // motivo, nunca «Sin dato»
          const na = i.state === "no_aplica";
          return (
            <tr key={i.metric + i.value}>
              <th scope="row"><span className="metric-name">{na ? i.value : i.metric}</span>
                {na ? <span className="metric-sub">no puntúan en este tipo de empresa</span>
                  : i.in_block ? <span className="metric-sub">en el bloque de múltiplos</span> : null}</th>
              <td data-label="Valor" className={`num${i.state === "con_dato" ? "" : " tone-neutral"}`}>{i.state === "con_dato" ? i.value : na ? "No aplica" : "Sin dato"}</td>
              <td data-label="Ajuste" className={`num tone-${toVTone(i.tone)}`}>{na ? "No puntúa" : i.sign}</td>
              <td data-label="Motivo" className="wide">{i.reason}</td>
            </tr>
          );
        })}</tbody>
      </table>
    </div>
  );
}
