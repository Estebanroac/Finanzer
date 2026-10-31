import type { MetricBands, Row } from "@/lib/api";
import { definitionFor } from "@/lib/tooltips";
import { toVTone } from "@/v2/lib/tone";
import MetricTip from "./MetricTip";

/** Primera frase de una definición (el significado llano bajo el nombre técnico). */
const firstSentence = (t: string) => (t.match(/^.*?[.!?](\s|$)/)?.[0] ?? t).trim();
const shown = (v: string | null | undefined) => !!v && v !== "—";
/** Con referencia (de su industria o del mercado): referencia o brecha publicadas. */
const hasRef = (r: Row) => shown(r.bench) || shown(r.gap);
/** Tabla de tres columnas del motor (MÉTRICA, VALOR, LECTURA: solidez, crecimiento). */
const THREE = 3;

/** La lectura de una fila con cifra: la del motor en pastilla con su tono; sin lectura, una pastilla gris que lo dice
 *  (V4b · 4: nunca una celda vacía). */
function Reading({ r, none }: { r: Row; none: string }) {
  return shown(r.reading) ? <span className={`pill ${toVTone(r.tone)}`}>{r.reading}</span> : <span className="pill neutral">{none}</span>;
}

function MetricHead({ r, tooltips }: { r: Row; tooltips: Record<string, MetricBands> }) {
  const def = definitionFor(r.key, r.label);
  const has = r.state === "con_dato";
  return (
    <th scope="row">
      <span className="metric-name">{r.label}</span>
      <MetricTip metricKey={r.key} label={r.label} value={has ? r.value : null} reading={has ? r.reading : null} bands={tooltips[r.key]} />
      {def.description && <span className="metric-sub">{firstSentence(def.description)}</span>}
    </th>
  );
}

/** Fila sin dato (o sin lectura porque no aplica): sus cifras, si las hay, y el motivo del motor. */
function MissingCells({ r, refLabel, companyLabel, span, withRef }: {
  r: Row; refLabel: string; companyLabel: string; span: number; withRef: boolean;
}) {
  const why = <><strong>{shown(r.reading) ? r.reading : "Sin lectura"}</strong>{r.text ? ` · ${r.text}` : ""}</>;
  if (shown(r.value) || (withRef && shown(r.bench))) return (<>
    {/* Con cifra o referencia pero sin lectura (no aplica a este tipo de empresa): las cifras y el motivo */}
    <td className="num tone-neutral" data-label={companyLabel}>{shown(r.value) ? r.value : "No aplica"}</td>
    {withRef && <td className="num" data-label={refLabel}>{shown(r.bench) ? r.bench : "Sin referencia"}</td>}
    <td colSpan={span - (withRef ? 3 : 2)} className="row-missing">{why}</td>
  </>);
  return <td colSpan={span - 1} className="row-missing"><strong>{r.reading || "Sin dato"}</strong>{r.text ? ` · ${r.text}` : ""}</td>;
}

/** Tabla de cinco columnas: Métrica · Empresa · Referencia · Brecha · Lectura, para las filas con referencia. */
function RefTable({ rows, refLabel, tooltips, caption, companyLabel, withText }: {
  rows: Row[]; refLabel: string; tooltips: Record<string, MetricBands>; caption?: string; companyLabel: string; withText: boolean;
}) {
  return (
    <div className="techtable-wrap surface" tabIndex={0} role="region" aria-label={caption ?? "Tabla técnica"}>
      <table className="techtable metrics">
        {caption && <caption>{caption}</caption>}
        {/* Mismos anchos en todas las tablas técnicas: apiladas, sus columnas caen en el mismo sitio */}
        <colgroup><col className="c-metric" /><col className="c-num" /><col className="c-num" /><col className="c-gap" /><col className="c-read" /></colgroup>
        <thead>
          <tr>
            <th scope="col">Métrica</th>
            <th scope="col" className="num">{companyLabel}</th>
            <th scope="col" className="num">{refLabel}</th>
            <th scope="col" className="num">Brecha</th>
            <th scope="col">Lectura</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.key + r.label} data-key={r.key}>
              <MetricHead r={r} tooltips={tooltips} />
              {r.state === "con_dato" ? (<>
                <td className={`num tone-${toVTone(r.tone)}`} data-label={companyLabel}>{r.value}</td>
                <td className="num" data-label={refLabel}>{r.bench}</td>
                {/* Referencia que es un umbral («> 0»): sin brecha que medir */}
                <td className="num" data-label="Brecha">{shown(r.gap) ? r.gap : <span className="muted">umbral</span>}</td>
                <td className="reading" data-label="Lectura"><Reading r={r} none="Sin lectura" />
                  {withText && r.text && <span className="metric-sub">{r.text}</span>}</td>
              </>) : <MissingCells r={r} refLabel={refLabel} companyLabel={companyLabel} span={5} withRef />}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Tabla de tres columnas: Métrica · Empresa · Lectura. La referencia que alguna fila tenga (D/E, cobertura, en
 *  solidez) va bajo su cifra. */
function PlainTable({ rows, refLabel, tooltips, caption, companyLabel, none, withText }: {
  rows: Row[]; refLabel: string; tooltips: Record<string, MetricBands>; caption?: string; companyLabel: string; none: string; withText: boolean;
}) {
  return (
    <div className="techtable-wrap surface" tabIndex={0} role="region" aria-label={caption ?? "Tabla técnica"}>
      <table className="techtable metrics three">
        {caption && <caption>{caption}</caption>}
        <colgroup><col className="c-metric" /><col className="c-num" /><col className="c-read" /></colgroup>
        <thead>
          <tr>
            <th scope="col">Métrica</th>
            <th scope="col" className="num">{companyLabel}</th>
            <th scope="col">Lectura</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.key + r.label} data-key={r.key}>
              <MetricHead r={r} tooltips={tooltips} />
              {r.state === "con_dato" ? (<>
                <td className={`num tone-${toVTone(r.tone)}`} data-label={companyLabel}>{r.value}
                  {hasRef(r) && <span className="metric-sub">{refLabel} {shown(r.bench) ? r.bench : ""}{shown(r.gap) ? ` · ${r.gap}` : ""}</span>}</td>
                <td className="reading" data-label="Lectura"><Reading r={r} none={none} />
                  {withText && r.text && <span className="metric-sub">{r.text}</span>}</td>
              </>) : <MissingCells r={r} refLabel={refLabel} companyLabel={companyLabel} span={3} withRef={false} />}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/**
 * Tabla técnica (maqueta 4): Métrica (nombre técnico, "?" y significado) · Empresa · Referencia · Brecha · Lectura.
 * Todo viene del motor (valor, referencia, brecha, lectura y tono); una fila sin dato dice "Sin dato" y su motivo.
 * V4b · 4 (PM, ausencias):
 *  - una sección del motor de tres columnas (`columns`: MÉTRICA, VALOR, LECTURA) es una tabla de tres columnas, sin
 *    columnas de referencia y brecha vacías;
 *  - en las de cinco, las filas sin referencia publicada van aparte, en una tabla de tres columnas con una nota que las
 *    nombra (nunca un «—» por celda);
 *  - una cifra sin lectura lo dice en gris («Sin referencia» o «Informativa»), nunca una celda vacía.
 */
export default function TechTable({ rows, refLabel, tooltips, caption, companyLabel = "Empresa", withText = false, columns }: {
  rows: Row[]; refLabel: string; tooltips: Record<string, MetricBands>; caption?: string; companyLabel?: string;
  /** Muestra bajo la lectura la frase del motor de cada fila (la comparativa de Rivales). */
  withText?: boolean;
  /** Las columnas de la sección del motor (`sections.*.columns`): con tres, la tabla es de tres. */
  columns?: string[];
}) {
  if (columns?.length === THREE)
    return <PlainTable rows={rows} refLabel={refLabel} tooltips={tooltips} caption={caption} companyLabel={companyLabel} none="Informativa" withText={withText} />;
  const noRef = rows.filter((r) => r.state === "con_dato" && !hasRef(r));
  const withRef = rows.filter((r) => !noRef.includes(r));
  const ref = refLabel.toLowerCase();
  return (<>
    {withRef.length > 0 && <RefTable rows={withRef} refLabel={refLabel} tooltips={tooltips} caption={caption} companyLabel={companyLabel} withText={withText} />}
    {noRef.length > 0 && (<>
      <PlainTable rows={noRef} refLabel={refLabel} tooltips={tooltips} companyLabel={companyLabel} none="Sin referencia" withText={withText}
                  caption={withRef.length ? `Sin referencia de ${ref}` : caption} />
      <p className="muted small table-foot" data-testid="no-ref-note">
        Sin referencia de {ref} publicada para: {noRef.map((r) => r.label).join(", ")}.</p>
    </>)}
  </>);
}
