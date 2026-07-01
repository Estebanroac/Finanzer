"use client";

import { formatPrice, type StockAnalysis } from "@/lib/api";
import InfoTooltip from "@/components/InfoTooltip";
import { INTRINSIC } from "@/lib/tooltips";

export default function IntrinsicTab({ data }: { data: StockAnalysis }) {
  const price = data.price;
  const graham = data.graham_number;
  const dcf = data.dcf;

  // Verdict
  let verdict = "Precio justo";
  let verdictColor = "#fbbf24";
  if (dcf?.fair_value && price) {
    const upside = ((dcf.fair_value - price) / price) * 100;
    if (upside > 15) { verdict = "Subvalorada"; verdictColor = "#00d632"; }
    else if (upside < -15) { verdict = "Sobrevalorada"; verdictColor = "#ff4d4d"; }
  }

  return (
    <div className="space-y-8">
      {/* Verdict banner */}
      <div
        className="rounded-xl border px-6 py-5 flex items-center gap-4"
        style={{ borderColor: `${verdictColor}25`, background: `${verdictColor}08` }}
      >
        <div
          className="w-3 h-3 rounded-full shrink-0"
          style={{ background: verdictColor, boxShadow: `0 0 12px ${verdictColor}60` }}
        />
        <div className="flex-1">
          <span className="text-lg font-bold" style={{ color: verdictColor }}>{verdict}</span>
          <p className="text-sm text-zinc-400 mt-0.5">
            {verdict === "Subvalorada" && "El precio de mercado está por debajo del valor estimado."}
            {verdict === "Sobrevalorada" && "El precio de mercado supera el valor estimado."}
            {verdict === "Precio justo" && "El precio actual está cerca del valor estimado."}
          </p>
        </div>
        <InfoTooltip content={INTRINSIC.margin_safety} size="md" />
      </div>

      {/* Comparison row */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-px rounded-xl overflow-hidden border border-white/[0.06]">
        <ValuationBlock
          title="Precio de Mercado"
          value={formatPrice(price)}
          sub="Precio actual"
          color="#3b82f6"
        />
        <ValuationBlock
          title="Valor Graham"
          value={formatPrice(graham)}
          sub={graham && price ? `${((graham - price) / price * 100).toFixed(1)}% vs precio` : ""}
          color={graham && price && graham > price ? "#00d632" : "#ff4d4d"}
          tooltip="graham"
        />
        <ValuationBlock
          title="Valor DCF"
          value={formatPrice(dcf?.fair_value)}
          sub={dcf?.upside != null ? `${dcf.upside > 0 ? "+" : ""}${dcf.upside.toFixed(1)}% upside` : ""}
          color={dcf?.fair_value && price && dcf.fair_value > price ? "#00d632" : "#ff4d4d"}
          tooltip="dcf"
        />
      </div>

      {/* DCF Details */}
      {dcf && (
        <div>
          <h4 className="text-xs text-zinc-500 uppercase tracking-widest mb-3 font-medium">
            Parámetros DCF
          </h4>
          <div className="rounded-xl border border-white/[0.06] bg-[#0a0a0d]/85 px-5">
            <ParamRow label="WACC" value={dcf.wacc != null ? `${(dcf.wacc * 100).toFixed(1)}%` : "N/A"} hint="Tasa de descuento" />
            <ParamRow label="Growth Rate" value={dcf.growth_rate != null ? `${(dcf.growth_rate * 100).toFixed(1)}%` : "N/A"} hint="Crecimiento estimado" />
            <ParamRow label="Terminal Growth" value={dcf.terminal_growth != null ? `${(dcf.terminal_growth * 100).toFixed(1)}%` : "N/A"} hint="Crecimiento perpetuo" />
            <ParamRow label="Margen de Seguridad" value={dcf.margin_of_safety != null ? formatPrice(dcf.margin_of_safety) : "N/A"} hint="Con 25% descuento" />
          </div>
        </div>
      )}

      {/* Sensitivity table */}
      {data.sensitivity && <SensitivityTable sensitivity={data.sensitivity} price={price} />}
    </div>
  );
}

function ValuationBlock({ title, value, sub, color, tooltip }: { title: string; value: string; sub: string; color: string; tooltip?: string }) {
  return (
    <div className="bg-[#0a0a0d]/85 p-5 text-center">
      <div className="flex items-center justify-center gap-1.5 mb-2">
        <span className="text-xs text-zinc-500">{title}</span>
        {tooltip === "graham" && <InfoTooltip content={INTRINSIC.graham} />}
        {tooltip === "dcf" && <InfoTooltip content={INTRINSIC.dcf} />}
      </div>
      <div className="text-2xl font-bold tabular-nums" style={{ color }}>{value}</div>
      {sub && <div className="text-xs text-zinc-500 mt-1">{sub}</div>}
    </div>
  );
}

function ParamRow({ label, value, hint }: { label: string; value: string; hint: string }) {
  const isNA = value === "N/A";
  return (
    <div className="flex items-center justify-between py-3 border-b border-white/[0.04] last:border-0">
      <div>
        <span className="text-sm text-zinc-300">{label}</span>
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
                <th
                  key={i}
                  className={`p-3 text-center font-medium text-xs ${
                    i === base_discount_idx ? "text-[#00d632]" : "text-zinc-500"
                  }`}
                >
                  {(dr * 100).toFixed(1)}%
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {matrix.map((row, gi) => (
              <tr key={gi} className="border-b border-white/[0.04] last:border-0">
                <td
                  className={`p-3 font-medium text-xs ${
                    gi === base_growth_idx ? "text-[#00d632]" : "text-zinc-500"
                  }`}
                >
                  {(growth_rates[gi] * 100).toFixed(1)}%
                </td>
                {row.map((val, di) => (
                  <td
                    key={di}
                    className={`p-3 text-center font-medium text-xs ${cellClass(val)} ${
                      gi === base_growth_idx && di === base_discount_idx ? "ring-1 ring-[#00d632]/40 rounded" : ""
                    }`}
                  >
                    {val == null ? "—" : `$${val.toFixed(0)}`}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-4 mt-3 text-[10px] text-zinc-500">
        <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-sm cell-strong-buy" /> Muy subvalorada</span>
        <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-sm cell-buy" /> Subvalorada</span>
        <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-sm cell-fair" /> Precio justo</span>
        <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-sm cell-sell" /> Sobrevalorada</span>
      </div>
    </div>
  );
}
