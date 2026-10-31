import type { Tone, Zone } from "@/lib/api";
import { toVTone } from "@/v2/lib/tone";

/** Escala horizontal con los tramos del motor (de su config) y el valor marcado. El cliente solo sitúa el marcador:
 *  la lectura y el tono vienen del motor. Sin valor situable (caja neta, EBIT negativo…), no hay marcador. */
/** Corte de un tramo como en la escala de la web actual: "1x", "1.5x", "25%". */
const tickTxt = (n: number, unit: string) => `${Number.isInteger(n) ? String(n) : n.toFixed(1)}${unit}`;

/** v4 (PM): `tone`, el del tramo donde cae el valor (lo da el motor con su lectura): el marcador lleva ese color. */
export default function Gauge({ zones, axisMax, value, label, unit = "", tone }: {
  zones: Zone[]; axisMax: number; value?: number | null; label: string; unit?: string | null; tone?: Tone | null;
}) {
  const at = value == null ? null : Math.max(0, Math.min(100, (value / axisMax) * 100));
  return (
    <div className="gauge" role="img" aria-label={label}>
      <div className="gauge-track">
        {zones.map((z) => (
          <span key={z.label + z.from} className={`gauge-zone ${toVTone(z.tone)}`}
                style={{ left: `${(z.from / axisMax) * 100}%`, width: `${((z.to - z.from) / axisMax) * 100}%` }} />
        ))}
        {at !== null && <span className={`gauge-mark ${toVTone(tone)}`} style={{ left: `${at}%` }} />}
      </div>
      <div className="gauge-ticks" aria-hidden="true">
        {zones.slice(0, -1).map((z) => <span key={z.to} style={{ left: `${(z.to / axisMax) * 100}%` }}>{tickTxt(z.to, unit ?? "")}</span>)}
      </div>
      {/* V4b (nada oculto): el nombre de cada tramo entero, como leyenda (bajo un tramo estrecho se cortaba con «…» y solo
          se leía al pasar el ratón) */}
      <div className="gauge-labels">
        {zones.map((z) => <span key={z.label + z.from}><i className={`sw zone-${toVTone(z.tone)}`} />{z.label}</span>)}
      </div>
    </div>
  );
}
