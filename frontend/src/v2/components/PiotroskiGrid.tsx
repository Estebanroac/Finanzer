import type { Display, Tone } from "@/lib/api";
import { toVTone } from "@/v2/lib/tone";
import { PIOTROSKI_PLAIN } from "@/v2/lib/piotroski";

type Crit = Display["sections"]["institutional"]["piotroski_criteria"][number];
type Val = NonNullable<Display["extended"]>["piotroski_values"][number];

const norm = (t: string) => t.toLowerCase().replace(/[^a-záéíóúüñ0-9]+/g, " ").trim();

/** Piotroski en 9 tarjetas (maqueta 2): criterio, Cumple / No cumple / Sin dato del motor, sus valores (E2a) y la
 *  frase llana. Las tarjetas de una fila comparten rejilla interna (cabecera · valores · frase): el espacio sobrante
 *  se reparte por filas, no queda al pie de la más corta. */
export default function PiotroskiGrid({ criteria, values }: { criteria: Crit[]; values: Val[] }) {
  return (
    <div className="dgrid three pio sub" style={{ "--rows": 3 } as React.CSSProperties} data-sym-row data-testid="piotroski-grid">
      {criteria.map((c) => {
        const v = values.find((x) => x.key === c.key);
        const tone = toVTone(c.tone as Tone);
        let shown: string | null = null;
        if (v?.cur_txt) {
          shown = v.compare === "prior_year" && v.prev_txt ? `${v.prev_txt} → ${v.cur_txt} (frente al año anterior)`
            : v.compare === "ni" && v.prev_txt ? `${v.cur_txt} frente a ${v.prev_txt} de beneficio neto`
            : v.cur_txt;
        }
        // "FY2025: ROA positivo" solo repite el nombre del criterio: queda el periodo junto a los valores
        const m = c.detail.match(/^(FY\s?\d{4})\s*[:·-]\s*(.*)$/);
        const repeats = !!m && norm(m[2]) === norm(c.label);
        const period = repeats ? m![1] : null;
        return (
          <div key={c.key} className="card surface" data-crit={c.key}>
            <div className="pio-head"><h4>{c.label}</h4><span className={`pill ${tone}`}>{c.status}</span></div>
            <div className="pio-body">
              {(shown || period) && <p className="num pio-val">{period && <span className="muted">{period}{shown ? ": " : ""}</span>}{shown}</p>}
              {!repeats && <p>{c.detail}</p>}
            </div>
            <p className="muted small">{PIOTROSKI_PLAIN[c.key] ?? ""}</p>
          </div>
        );
      })}
    </div>
  );
}
