"use client";

import { formatPrice, type StockAnalysis } from "@/lib/api";
import InfoTooltip from "@/components/InfoTooltip";
import { INTRINSIC, PROFITABILITY } from "@/lib/tooltips";
import { useGrow } from "@/lib/useGrow";

export default function IntrinsicTab({ data }: { data: StockAnalysis }) {
  const price = data.price;
  const graham = data.graham_number;
  const grahamMargin = data.graham_margin;
  const dcf = data.dcf;
  const grown = useGrow();

  const fv = dcf?.fair_value ?? null;
  const hasGauge = fv != null && fv > 0 && price != null && price > 0;

  return (
    <div className={`space-y-6 ${grown ? "viz-in" : ""}`}>
      {hasGauge ? (
        <ValuationGauge price={price} fv={fv} dcf={dcf!} graham={graham} grahamMargin={grahamMargin} />
      ) : (
        <NoDcfView price={price} graham={graham} grahamMargin={grahamMargin}
          isFinancial={(data.sector_info?.mapped_sector || "").toLowerCase().includes("financ")} />
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-start">
        {/* Parámetros DCF */}
        {dcf && (
          <div className="rounded-xl border border-white/[0.06] bg-[#0a0a0d]/85 px-5 py-4">
            <h4 className="text-xs text-zinc-500 uppercase tracking-widest mb-1 font-medium">
              Parámetros DCF
            </h4>
            <ParamRow
              label="WACC"
              value={dcf.wacc != null ? `${(dcf.wacc * 100).toFixed(1)}%` : "N/A"}
              hint="Tasa de descuento"
              tooltip={<InfoTooltip content={PROFITABILITY.wacc} value={dcf.wacc} valueLabel={dcf.wacc != null ? `${(dcf.wacc * 100).toFixed(1)}%` : "N/A"} />}
            />
            <ParamRow label="Crecimiento" value={dcf.growth_rate != null ? `${(dcf.growth_rate * 100).toFixed(1)}%` : "N/A"} hint="Alto crecimiento" />
            <ParamRow label="Crecimiento terminal" value={dcf.terminal_growth != null ? `${(dcf.terminal_growth * 100).toFixed(1)}%` : "N/A"} hint="Perpetuo" />
            <ParamRow
              label="Margen de seguridad"
              value={dcf.margin_of_safety != null ? `${(dcf.margin_of_safety * 100).toFixed(1)}%` : "N/A"}
              hint="(FV − precio) / FV"
              tooltip={<InfoTooltip content={INTRINSIC.margin_safety} value={dcf.margin_of_safety} valueLabel={dcf.margin_of_safety != null ? `${(dcf.margin_of_safety * 100).toFixed(1)}%` : "N/A"} />}
            />
          </div>
        )}

        {/* Composición del valor DCF */}
        {dcf?.value_composition && (
          <DcfComposition composition={dcf.value_composition} grown={grown} />
        )}
      </div>

      {/* Sensibilidad */}
      {data.sensitivity && <SensitivityTable sensitivity={data.sensitivity} price={price} />}
    </div>
  );
}

/* ── Regla de valoración: margen seguridad → subvalorado → fair → sobrevalorado ── */
function ValuationGauge({ price, fv, dcf, graham, grahamMargin }: {
  price: number;
  fv: number;
  dcf: NonNullable<StockAnalysis["dcf"]>;
  graham: number | null;
  grahamMargin: number | null;
}) {
  // dominio en $: desde 0.5×FV hasta cubrir el precio si está por encima
  const d0 = fv * 0.5;
  const d1 = Math.max(fv * 1.5, price * 1.12);
  const pos = (x: number) => Math.max(2, Math.min(98, ((x - d0) / (d1 - d0)) * 100));

  // límites de zona en $: 75%FV | 90%FV | 110%FV
  const msB = fv * 0.75, underB = fv * 0.9, fairB = fv * 1.1;
  const zones = [
    { cls: "z-safe", flex: pos(msB) - 0 },
    { cls: "z-under", flex: pos(underB) - pos(msB) },
    { cls: "z-fair", flex: pos(fairB) - pos(underB) },
    { cls: "z-over", flex: 100 - pos(fairB) },
  ];
  const labels = ["Margen\nseguridad", "Subvalorado", "Fair value", "Sobrevalorado"];

  const upside = dcf.upside ?? ((fv - price) / price) * 100;
  let verdict = "Precio justo", tone: "pos" | "warn" | "neg" = "warn";
  if (upside >= 30) { verdict = "Muy infravalorada"; tone = "pos"; }
  else if (upside >= 15) { verdict = "Infravalorada"; tone = "pos"; }
  else if (upside <= -30) { verdict = "Sobrevalorada"; tone = "neg"; }
  else if (upside <= -15) { verdict = "Prima sobre fair value"; tone = "neg"; }
  else if (upside < 0) { verdict = "Precio justo · algo caro"; tone = "warn"; }

  const prima = ((price / fv) - 1) * 100;

  return (
    <div className="rounded-xl border border-white/[0.06] bg-[#0a0a0d]/85 px-6 py-5">
      <div className="vg-head">
        <h4 className="text-xs text-zinc-500 uppercase tracking-widest font-medium flex items-center gap-1.5">
          Valor intrínseco
          <InfoTooltip content={INTRINSIC.dcf} value={fv} valueLabel={formatPrice(fv)} />
        </h4>
        <span className={`vg-verdict ${tone}`}>{verdict}</span>
      </div>

      <div className="vg-scale">
        {/* Precio actual: dot pulsante, etiqueta arriba */}
        <div className="vg-price" style={{ left: `${pos(price)}%` }}>
          <div className="vg-mk vg-mk-price">
            <span className="lab">Precio actual</span>
            <span className="val">{formatPrice(price)}</span>
          </div>
          <div className="vg-dot" />
        </div>

        <div className="vg-zones">
          {zones.map((z, i) => <div key={i} className={`vg-zone ${z.cls}`} style={{ flex: z.flex }} />)}
        </div>

        {/* Fair value: tick, etiqueta debajo */}
        <div className="vg-fair" style={{ left: `${pos(fv)}%` }}>
          <div className="vg-fair-line" />
          <div className="vg-mk vg-mk-fair">
            <span className="lab">Fair value</span>
            <span className="val">{formatPrice(fv)}</span>
          </div>
        </div>

        {/* Ejes $ (el límite fair se omite: su etiqueta ya está bajo la pista) */}
        <div className="vg-axis" aria-hidden="true">
          {[msB, price].map((x, i) => (
            <span key={i} className="vg-tick" style={{ left: `${pos(x)}%` }}>
              <i /><span className="num">${x.toFixed(0)}</span>
            </span>
          ))}
        </div>

        <div className="vg-labels">
          {zones.map((z, i) => (
            <div key={i} className="vg-lbl" style={{ flex: z.flex }}>
              <span>{labels[i].split("\n").map((l, j) => <span key={j}>{l}<br /></span>)}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="vg-foot">
        <div className="vg-stat">
          <span className="vg-k">Upside DCF</span>
          <span className={`vg-v ${upside >= 15 ? "pos" : upside <= -15 ? "neg" : "warn"}`}>
            {upside >= 0 ? "+" : "−"}{Math.abs(upside).toFixed(1)}%
          </span>
        </div>
        <div className="vg-sep" />
        <div className="vg-stat">
          <span className="vg-k">Prima vs fair value</span>
          <span className={`vg-v ${prima <= 0 ? "pos" : prima < 15 ? "warn" : "neg"}`}>
            {prima >= 0 ? "+" : "−"}{Math.abs(prima).toFixed(1)}%
          </span>
        </div>
        {graham != null && (
          <>
            <div className="vg-sep" />
            <div className="vg-stat">
              <span className="vg-k flex items-center gap-1">Nº de Graham <InfoTooltip content={INTRINSIC.graham} value={graham} valueLabel={formatPrice(graham)} /></span>
              <span className="vg-v">
                {formatPrice(graham)}
                {/* el % solo cuando es informativo; en growth de calidad el
                    criterio de 1949 queda tan lejos que el número solo asusta */}
                {grahamMargin != null && Math.abs(grahamMargin) <= 1 && (
                  <span
                    className="text-xs font-normal ml-1.5"
                    style={{ color: grahamMargin >= 0 ? "#0cc06c" : "#ff453a" }}
                  >
                    ({grahamMargin >= 0 ? "+" : ""}{(grahamMargin * 100).toFixed(0)}% margen)
                  </span>
                )}
              </span>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

/* ── Sin DCF (p. ej. financieras): precio + Graham ── */
function NoDcfView({ price, graham, grahamMargin, isFinancial }: {
  price: number | null;
  graham: number | null;
  grahamMargin: number | null;
  isFinancial: boolean;
}) {
  return (
    <div className="rounded-xl border border-white/[0.06] bg-[#0a0a0d]/85 px-6 py-5">
      <h4 className="text-xs text-zinc-500 uppercase tracking-widest mb-3 font-medium">
        Valor intrínseco
      </h4>
      <div className="flex flex-wrap gap-8">
        <div className="vg-stat">
          <span className="vg-k">Precio de mercado</span>
          <span className="vg-v">{formatPrice(price)}</span>
        </div>
        <div className="vg-stat">
          <span className="vg-k flex items-center gap-1">Nº de Graham <InfoTooltip content={INTRINSIC.graham} value={graham} valueLabel={formatPrice(graham)} /></span>
          <span className="vg-v">
            {formatPrice(graham)}
            {grahamMargin != null && Math.abs(grahamMargin) <= 1 && (
              <span
                className="text-xs font-normal ml-1.5"
                style={{ color: grahamMargin >= 0 ? "#0cc06c" : "#ff453a" }}
              >
                ({grahamMargin >= 0 ? "+" : ""}{(grahamMargin * 100).toFixed(0)}% margen)
              </span>
            )}
          </span>
        </div>
      </div>
      <p className="text-xs text-zinc-500 mt-4 leading-relaxed">
        {isFinancial
          ? "El modelo DCF no aplica a instituciones financieras (el flujo de caja libre no es interpretable en banca); se valoran sobre libros y retornos."
          : "El modelo DCF no está disponible con los datos actuales (requiere flujo de caja libre positivo)."}
      </p>
    </div>
  );
}

/* ── Composición del valor DCF: explícito vs terminal ── */
function DcfComposition({ composition, grown }: {
  composition: Record<string, number>;
  grown: boolean;
}) {
  const s1 = composition.stage1_pct ?? 0;
  const s2 = composition.stage2_pct ?? 0;
  const terminal = composition.terminal_pct ?? 0;
  const explicit = Math.max(0, Math.min(100, s1 + s2));
  const term = Math.max(0, Math.min(100, terminal));
  if (explicit <= 0 && term <= 0) return null;

  return (
    <div className="rounded-xl border border-white/[0.06] bg-[#0a0a0d]/85 px-5 py-4">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-xs text-zinc-500 uppercase tracking-widest font-medium">
          Composición del valor DCF
        </h4>
        <span className="pf-hint">de dónde viene el fair value</span>
      </div>
      <div className="dcfc-bar">
        <div className="dcfc-seg dcfc-explicit" style={{ width: grown ? `${explicit}%` : 0 }}>
          {explicit >= 12 && <span className="dcfc-in">{explicit.toFixed(0)}%</span>}
        </div>
        <div className="dcfc-seg dcfc-terminal" style={{ width: grown ? `${term}%` : 0 }}>
          {term >= 12 && <span className="dcfc-in">{term.toFixed(0)}%</span>}
        </div>
      </div>
      <div className="dcfc-key">
        <span className="dcfc-k"><i className="dcfc-sw-e" />Valor explícito · 10 años proyectados</span>
        <span className="dcfc-k"><i className="dcfc-sw-t" />Valor terminal · a perpetuidad</span>
      </div>
      <div className="dcfc-note">
        El <b>{term.toFixed(0)}%</b> del valor justo depende del <b>valor terminal</b> — la parte más
        sensible a los supuestos de largo plazo (WACC y crecimiento perpetuo).
      </div>
    </div>
  );
}

function ParamRow({ label, value, hint, tooltip }: { label: string; value: string; hint: string; tooltip?: React.ReactNode }) {
  const isNA = value === "N/A";
  return (
    <div className="flex items-center justify-between py-3 border-b border-white/[0.04] last:border-0">
      <div>
        <span className="text-sm text-zinc-300 inline-flex items-center gap-1.5">
          {label}
          {tooltip}
        </span>
        <span className="text-xs text-zinc-600 ml-2">{hint}</span>
      </div>
      <span className={`text-sm font-semibold tabular-nums ${isNA ? "text-zinc-600" : "text-white"}`}>
        {value}
      </span>
    </div>
  );
}

function SensitivityTable({ sensitivity, price }: { sensitivity: NonNullable<StockAnalysis["sensitivity"]>; price: number | null }) {
  if (!sensitivity.matrix || !sensitivity.growth_rates || !sensitivity.discount_rates) return null;
  const { matrix, growth_rates, discount_rates, base_growth_idx, base_discount_idx } = sensitivity;

  function cellClass(val: number | null): string {
    if (val == null || !price) return "";
    const diff = ((val - price) / price) * 100;
    if (diff > 30) return "cell-strong-buy";
    if (diff > 10) return "cell-buy";
    if (diff > -10) return "cell-fair";
    if (diff > -30) return "cell-sell";
    return "cell-strong-sell";
  }

  return (
    <div>
      <div className="flex items-center gap-2 mb-1">
        <h4 className="text-xs text-zinc-500 uppercase tracking-widest font-medium">
          Análisis de sensibilidad
        </h4>
        <InfoTooltip content={INTRINSIC.sensitivity} />
      </div>
      <p className="text-xs text-zinc-600 mb-4">
        Valor justo estimado bajo diferentes escenarios de crecimiento y tasa de descuento.
        {price && <> Precio actual: <strong className="text-zinc-400">${price.toFixed(2)}</strong></>}
      </p>

      <div className="rounded-xl border border-white/[0.06] overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-white/[0.06]">
              <th className="p-3 text-left text-zinc-500 font-medium text-xs">Crec. ↓ / WACC →</th>
              {discount_rates.map((dr, i) => (
                <th key={i} className={`p-3 text-center font-medium text-xs ${
                  i === base_discount_idx ? "text-[#0cc06c]" : "text-zinc-500"
                }`}>
                  {(dr * 100).toFixed(1)}%
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {matrix.map((row, gi) => (
              <tr key={gi} className="border-b border-white/[0.04] last:border-0">
                <td className={`p-3 font-medium text-xs ${
                  gi === base_growth_idx ? "text-[#0cc06c]" : "text-zinc-500"
                }`}>
                  {(growth_rates[gi] * 100).toFixed(1)}%
                </td>
                {row.map((val, di) => (
                  <td key={di} className={`p-3 text-center font-medium text-xs ${cellClass(val)} ${
                    gi === base_growth_idx && di === base_discount_idx ? "ring-1 ring-[#0cc06c]/40 rounded" : ""
                  }`}>
                    {val == null ? "—" : `$${val.toFixed(0)}`}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex flex-wrap gap-4 mt-3 text-[10px] text-zinc-500">
        <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-sm cell-strong-buy" /> Muy subvalorada</span>
        <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-sm cell-buy" /> Subvalorada</span>
        <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-sm cell-fair" /> Precio justo</span>
        <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-sm cell-sell" /> Sobrevalorada</span>
      </div>
    </div>
  );
}
