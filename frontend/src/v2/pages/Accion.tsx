"use client";
import { useEffect, useState } from "react";
import type { PageProps } from "./DepthPage";
import type { Tone } from "@/lib/api";
import { fetchPrices, type PricesPayload } from "@/v2/lib/prices";
import { returnOf } from "@/v2/lib/returns";
import { isAbort } from "@/v2/lib/http";
import { toVTone } from "@/v2/lib/tone";
import PillIndex from "@/v2/components/depth/PillIndex";
import Section, { Missing } from "@/v2/components/depth/Section";
import SignalsTable from "@/v2/components/SignalsTable";
import Methodology from "@/v2/components/depth/Methodology";
import MetricTip from "@/v2/components/depth/MetricTip";
import { lazyWith } from "@/v2/lib/lazy";
import { PriceChartFullSkeleton } from "@/v2/components/PriceChartParts";

// Revisión V6 (F13): la gráfica completa (Lightweight Charts) en su propio fragmento.
// v4.1: mientras llega, su esqueleto del mismo alto (antes una línea de texto: la gráfica, de 26 rem, empujaba la página)
const PriceChartFull = lazyWith(() => import("@/v2/components/PriceChartFull"), () => <PriceChartFullSkeleton />);

const PILLS = [{ id: "grafica", label: "Gráfica" }, { id: "rentabilidad", label: "Rentabilidad por periodo" },
  { id: "rango", label: "Rango de 52 semanas" }, { id: "senales", label: "Señales" }];

/** Task 5 · La acción: gráfica completa, rentabilidad por periodo, rango de 52 semanas y señales (contexto). */
export default function Accion({ analysis: a, symbol }: PageProps) {
  const s = a.display.sections, r52 = s.growth.range52, market = s.market;
  const [prices, setPrices] = useState<PricesPayload | null>(null);
  const [err, setErr] = useState<string | null>(null);
  // Revisión V6 (F12): la serie se pide una vez (caché del módulo); al desmontar se cancela.
  useEffect(() => {
    const ac = new AbortController();
    fetchPrices(symbol, a.profile.sector || null, ac.signal).then(setPrices).catch((e: Error) => { if (!isAbort(e)) setErr(e.message); });
    return () => ac.abort();
  }, [symbol, a.profile.sector]);
  const ok = prices?.company.status === "ok";
  // sin la serie de la empresa, la gráfica se dibuja con el mercado de referencia si lo hay
  const drawable = ok || prices?.market.status === "ok";
  return (<>
    <PillIndex items={PILLS} />
    <div className="wrap depth-body">
      <Section id="grafica" eyebrow="La acción" title="Precio en el tiempo">
        {err ? <Missing title="Gráfica de precio" reason={err} />
          : !prices ? <p className="missing" aria-busy="true">Cargando la serie de precios…</p>
          : drawable ? <PriceChartFull data={prices} symbol={symbol} currency={a.profile.currency} />
          : <Missing title="Gráfica de precio" reason={prices.company.reason} />}
      </Section>

      <Section id="rentabilidad" eyebrow="La acción" title="Rentabilidad por periodo">
        {prices && ok ? (
          <div className="techtable-wrap surface" tabIndex={0} role="region" aria-label="Rentabilidad por periodo" data-scroll-ok>
            {/* v4 móvil (PM): tabla numérica (.numtable); en el móvil, cabeceras cortas (el ticker va en la leyenda) */}
            <table className="techtable numtable" data-testid="returns-by-period">
              <caption className="numtable-caption">{symbol}, el S&P 500 y el ETF de su sector</caption>
              <thead><tr>
                <th scope="col">Periodo</th>
                <th scope="col" className="num"><span className="long">{symbol} · precio</span><span className="short">Precio</span></th>
                <th scope="col" className="num"><span className="long">{symbol} · con dividendos</span><span className="short">Con div.</span></th><th scope="col" className="num">S&P 500</th>
                <th scope="col" className="num">{prices.sector.status === "ok" ? prices.sector.symbol : "ETF del sector"}
                  {/* V7 · P3: qué es XLK (o el ETF que toque) */}
                  {prices.sector.status === "ok" && <MetricTip metricKey="sector_etf" label={`${prices.sector.symbol} (ETF del sector)`} />}</th>
              </tr></thead>
              <tbody>
                {/* Revisión V6 (F1): cifras, textos y tonos del backend (lib/price_returns: las mismas que el PDF) */}
                {(prices.ranges ?? []).map((rg) => {
                  const co = returnOf(prices, "company", rg.key), mk = returnOf(prices, "market", rg.key), se = returnOf(prices, "sector", rg.key);
                  const txt = (t: string) => (t === "—" ? "Sin dato" : t);
                  return (
                    <tr key={rg.key}>
                      <th scope="row">{rg.label}</th>
                      <td data-label={`${symbol} · precio`} className={`num tone-${toVTone(co.price_tone as Tone)}`}>{txt(co.price_txt)}</td>
                      <td data-label={`${symbol} · con dividendos`} className={`num tone-${toVTone(co.tone as Tone)}`}>{txt(co.total_txt)}</td>
                      <td data-label="S&P 500" className="num">{txt(mk.total_txt)}</td>
                      <td data-label={prices.sector.status === "ok" ? (prices.sector.symbol ?? "ETF del sector") : "ETF del sector"} className="num">{txt(se.total_txt)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            <p className="muted small table-foot">S&P 500 con dividendos: {prices.market.total_note ?? "sin la serie con dividendos"}. El ETF del sector, con dividendos (cierre ajustado). Un periodo que la serie no cubre queda sin dato. Las mismas cifras que el informe PDF.</p>
          </div>
        ) : <Missing title="Rentabilidad por periodo" reason={err ?? prices?.company.reason ?? "cargando la serie"} />}
      </Section>

      <Section id="rango" eyebrow="La acción" title="Rango de 52 semanas">
        {r52 ? (
          <div className="card surface" data-testid="range52">
            <div className="r52" aria-hidden="true">
              {r52.zones.map((z) => <span key={z.from} className="r52-zone" style={{ left: `${z.from}%`, width: `${z.to - z.from}%` }} />)}
              <span className="r52-mark" style={{ left: `${r52.pos}%` }} />
            </div>
            <div className="r52-ends num"><span>Mínimo {r52.low}</span><span>Máximo {r52.high}</span></div>
            {a.display.charts.price_card.from_high_txt && <p className="num">{a.display.charts.price_card.from_high_txt} desde el máximo de 52 semanas
              <MetricTip metricKey="pos52" label="Posición en el rango de 52 semanas" reading={r52.reading?.label} bands={a.display.tooltips.pos52} /></p>}
            <p>{r52.caption}{r52.reading && <> <span className={`pill ${toVTone(r52.reading.tone)}`}>{r52.reading.label}</span> {r52.reading.text}</>}</p>
            <p className="muted small">{r52.axis} {r52.zones_note}</p>
          </div>
        ) : <Missing title="Rango de 52 semanas" reason="el proveedor no da el rango" />}
      </Section>

      <Section id="senales" eyebrow="La acción" title="Señales de mercado">
        {market ? (<>
          <p className="segs-head"><span className="pill neutral">Contexto: no puntúa</span> {market.note}</p>
          {market.status_note && <p className="missing">{market.status_note}</p>}
          <SignalsTable market={market} />
        </>) : <Missing title="Señales de mercado" reason="sin serie de precios para calcularlas" />}
      </Section>

      <Methodology items={[
        { label: "Serie de la gráfica y las rentabilidades", text: prices?.source ?? null },
        { label: "Serie de las señales", text: market?.source ?? null },
        { label: "Rentabilidades", text: "De precio: cierre sin ajustar por dividendos; con dividendos: cierre ajustado. Del cierre de la primera sesión del periodo (días naturales hacia atrás desde la última sesión, o el 1 de enero) al de la última; calculadas en el servidor, las mismas que el informe PDF." },
        { label: "Señales", text: market?.note ?? null },
      ]} />
    </div>
  </>);
}
