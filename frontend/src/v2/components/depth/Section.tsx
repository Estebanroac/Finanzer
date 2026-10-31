import { STATE_LABELS } from "@/lib/generated/backendConfig";

/** Bloque de una página de profundidad: ancla (para su píldora), eyebrow y título; el contenido va en rejilla
 *  simétrica (`.dgrid` de 2 columnas o `.dgrid.three`). */
export default function Section({ id, eyebrow, title, children }: {
  id: string; eyebrow?: string; title: string; children: React.ReactNode;
}) {
  return (
    <section id={id} className="dsec" aria-labelledby={`${id}-t`}>
      <div className="dsec-head">
        {eyebrow && <div className="eyebrow">{eyebrow}</div>}
        <h3 id={`${id}-t`}>{title}</h3>
      </div>
      {children}
    </section>
  );
}

/** Dato ausente en UNA línea (título y motivo): nunca una caja reservada vacía. */
export function Missing({ title, reason }: { title: string; reason: string | null | undefined }) {
  return <p className="missing" data-missing><strong>{title}:</strong> {reason || "Sin dato"}</p>;
}

/** V4b · 4 (PM): una cifra que el motor no da, con su estado («No aplica», «No significativo», «Sin dato») y su porqué,
 *  nunca un «Sin dato» a secas. Si el motivo ya empieza por el estado («No aplica a REIT: …»), no se repite. */
export function StateNote({ state, text, rows }: {
  state: string; text: string | null | undefined;
  /** En una tarjeta de subrejilla (.dgrid.sub): las filas que ocupa la nota (la de la cifra y la de su lectura). */
  rows?: number;
}) {
  const label = (STATE_LABELS as Record<string, string>)[state] ?? STATE_LABELS.sin_dato;
  const t = (text ?? "").trim();
  const style = rows ? { gridRow: `span ${rows}` } : undefined;
  if (t && t.toLowerCase().startsWith(label.toLowerCase())) return <p className="missing" data-missing style={style}><strong>{t}</strong></p>;
  return <p className="missing" data-missing style={style}><strong>{label}{t ? ":" : ""}</strong>{t ? ` ${t}` : ""}</p>;
}
