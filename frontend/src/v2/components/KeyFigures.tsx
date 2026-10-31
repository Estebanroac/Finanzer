import type { KeyFigure } from "@/v2/lib/story";
import MetricTip, { LabelTip } from "./depth/MetricTip";

export default function KeyFigures({ figures }: { figures: KeyFigure[] }) {
  return (
    // V4b · 4: las que haya (de 1 a 3), en una rejilla simétrica para ese número
    <div className="figures" data-sym-row style={{ "--n": figures.length } as React.CSSProperties}>
      {figures.map((f, i) => (
        <div key={`${f.label}-${i}`} className="figure surface">
          <div className="eyebrow">{f.term ? <LabelTip text={f.label}><MetricTip metricKey={f.term} label={f.label} /></LabelTip> : f.label}</div>
          <div className={`num fig-value tone-${f.tone}`}>{f.value}</div>
        </div>
      ))}
    </div>
  );
}
