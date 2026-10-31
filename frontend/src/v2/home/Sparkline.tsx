import { useId } from "react";
import { SPARK_H, SPARK_W, sparkGeometry, type SparkItem } from "@/v2/lib/sparklines";

/** P8: mini-gráfica del periodo en SVG ligero (no Lightweight Charts): curva suave de 1,6 px, relleno con degradado del
 *  color de la serie (opacidad 0,14 → 0), referencia punteada y gris en el precio de partida, y el último precio con
 *  su halo. Color por el signo de la variación (tokens del tema, también en oscuro). Decorativa: la cifra va al lado. */
export default function Sparkline({ item }: { item: SparkItem | undefined }) {
  const id = useId().replace(/:/g, "");
  const g = item ? sparkGeometry(item) : null;
  if (!g) {
    return <svg className="spark empty" viewBox={`0 0 ${SPARK_W} ${SPARK_H}`} aria-hidden="true" focusable="false"
      data-testid="spark-empty"><title>{item?.reason ?? "Cargando la gráfica"}</title></svg>;
  }
  return (
    <svg className={`spark ${g.tone}`} viewBox={`0 0 ${SPARK_W} ${SPARK_H}`} aria-hidden="true" focusable="false"
      data-testid="spark">
      <defs>
        <linearGradient id={`sg${id}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="currentColor" stopOpacity=".14" />
          <stop offset="1" stopColor="currentColor" stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={g.area} fill={`url(#sg${id})`} />
      <line className="spark-ref" x1="0" x2={SPARK_W} y1={g.refY} y2={g.refY} />
      <path className="spark-line" d={g.line} />
      <circle cx={g.dot.x} cy={g.dot.y} r="5" fill="currentColor" opacity=".14" />
      <circle className="spark-dot" cx={g.dot.x} cy={g.dot.y} r="2.4" />
    </svg>
  );
}
