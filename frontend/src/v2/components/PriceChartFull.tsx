"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import { createChart, createSeriesMarkers, HistogramSeries, LineSeries, type IChartApi, type Time } from "lightweight-charts";
import type { PricesPayload, SeriesRole } from "@/v2/lib/prices";
import { chartPoints, DEFAULT_RANGE, sessionsOf, windowOf, type RangeKey } from "@/v2/lib/returns";
import { EVENT_KINDS, marksOf } from "@/v2/lib/chartEvents";
import { tickLabel, crosshairLabel } from "@/v2/lib/chartTime";
import { AXIS_PX, AXIS_PX_MOBILE, css, fmtDate, MARK_COLOR, MARK_SIZE, MOBILE_QUERY, Marks, RangeButtons, useTheme } from "./PriceChartParts";

import { perShareCur, volume as fmtVol } from "@/v2/lib/format";

const VOLUME_PANE_SHARE = 0.25;      // alto del panel de volumen frente al de precio
const pad2 = (n: number) => String(n).padStart(2, "0");
/** El tiempo del cursor como "AAAA-MM-DD" (la librería lo devuelve como texto o como día hábil {year, month, day}). */
const isoOf = (t: Time | undefined): string =>
  typeof t === "string" ? t : t && typeof t === "object" ? `${t.year}-${pad2(t.month)}-${pad2(t.day)}` : "";

/**
 * La acción a todo el ancho (spec §3.4): la gráfica del capítulo con cursor (fecha, cierre y volumen de la sesión),
 * panel de volumen, marcas de eventos con su leyenda y rangos de 1S a 5A, en base 100 frente al S&P 500 y al ETF del
 * sector (con dividendos). La serie la descarga la página (la comparte con la tabla de rentabilidades).
 * Verificación de la v4 (V3): sin la serie de la empresa pero con la del mercado, dibuja el S&P 500 (y el sector) como
 * referencia y dice en una línea por qué falta la empresa (V4b: lo hacía la gráfica de la página-historia).
 */
export default function PriceChartFull({ data, symbol, currency }: { data: PricesPayload; symbol: string; currency: string | null }) {
  const wrap = useRef<HTMLDivElement>(null);
  const box = useRef<HTMLDivElement>(null);
  const theme = useTheme();
  const [range, setRange] = useState<RangeKey>(DEFAULT_RANGE);
  const pts = data.company.points;
  const last = pts[pts.length - 1];
  const [cursor, setCursor] = useState<{ t: string; c: number; v: number | null } | null>(null);
  const byTime = useMemo(() => new Map(pts.map((p) => [p.t, p])), [pts]);
  const own = data.company.status === "ok";

  useEffect(() => {
    if (!box.current || (!own && data.market.status !== "ok")) return;
    const root = box.current.closest(".fz2") ?? document.body;
    const chart: IChartApi = createChart(box.current, {
      autoSize: true,
      layout: { background: { color: "transparent" }, textColor: css(root, "--text-3"), fontFamily: "inherit",
        fontSize: window.matchMedia(MOBILE_QUERY).matches ? AXIS_PX_MOBILE : AXIS_PX, attributionLogo: false,
        panes: { separatorColor: css(root, "--line") } },
      localization: { locale: "es-ES", timeFormatter: crosshairLabel },
      timeScale: { borderVisible: false, tickMarkFormatter: tickLabel },
      grid: { vertLines: { visible: false }, horzLines: { color: css(root, "--line-soft") } },
      rightPriceScale: { borderVisible: false, entireTextOnly: true, scaleMargins: { top: 0.1, bottom: 0.1 } },
      crosshair: { vertLine: { color: css(root, "--line") }, horzLine: { color: css(root, "--line") } },
      // El zoom con los dedos es de la página (spec §5): el periodo se elige con las pestañas.
      // Táctil (E4 Task 3): arrastrar mueve el cursor y nunca bloquea el desplazamiento vertical de la página
      handleScroll: { mouseWheel: false, pressedMouseMove: false, horzTouchDrag: false, vertTouchDrag: false }, handleScale: false,
    });
    // Revisión V6 (F1): base 100 y marcas del backend; aquí solo se pintan.
    const add = (role: SeriesRole, color: string, width: 1 | 2, dashed: boolean) => {
      const s = chart.addSeries(LineSeries, { color, lineWidth: width, lineStyle: dashed ? 2 : 0, priceLineVisible: false, lastValueVisible: false });
      s.setData(chartPoints(data, role, range));
      return s;
    };
    if (data.market.status === "ok") add("market", css(root, "--text-3"), 1, true);
    if (data.sector.status === "ok") add("sector", css(root, "--warn"), 1, true);
    if (own) {
      const co = add("company", css(root, "--good"), 2, false);
      createSeriesMarkers(co, marksOf(data, range).map((m) => ({
        time: m.t, position: "belowBar" as const, shape: "circle" as const, color: css(root, MARK_COLOR[m.kind]), size: MARK_SIZE })));
      const vol = chart.addSeries(HistogramSeries, { color: css(root, "--scale-neutral"), priceLineVisible: false, lastValueVisible: false,
        priceFormat: { type: "volume" } }, 1);
      const shown = sessionsOf(data, "company", range);
      vol.setData(pts.filter((p) => shown.has(p.t) && p.v != null).map((p) => ({ time: p.t, value: p.v as number })));
      const panes = chart.panes();
      if (panes[1]) panes[1].setStretchFactor(VOLUME_PANE_SHARE);
    }
    chart.timeScale().fitContent();
    chart.subscribeCrosshairMove((param) => {
      const p = byTime.get(isoOf(param.time));
      setCursor(p ? { t: p.t, c: p.c, v: p.v } : null);
    });
    return () => chart.remove();
  }, [data, range, theme, pts, byTime, own]);

  const marks = own ? marksOf(data, range) : [];
  const kinds = EVENT_KINDS.filter((k) => marks.some((m) => m.kind === k.kind));
  const at = cursor ?? (last ? { t: last.t, c: last.c, v: last.v } : null);
  const win = windowOf(data, range);
  return (
    <div ref={wrap} className="pricechart full card surface">
      <div className="ranges">
        <RangeButtons data={data} range={range} onPick={setRange} />
        {own && <Marks kinds={kinds.length ? kinds : EVENT_KINDS} />}
      </div>
      {own ? (
        <p className="cursor-read num" aria-live="polite" data-testid="cursor-readout">
          {at ? <>{cursor ? "" : "Última sesión · "}{fmtDate(at.t)} · cierre {perShareCur(at.c, currency)} · volumen {fmtVol(at.v)}</> : "Sin sesiones"}
          {win && !win.covered && win.start && <span className="muted"> · la serie empieza el {fmtDate(win.start)}</span>}
        </p>
      ) : (
        <p className="note muted" data-testid="price-chart-reference">Sin la serie de {symbol}: {data.company.reason}. Como referencia, el S&P 500{data.sector.status === "ok" ? ` y ${data.sector.symbol}` : ""} en el mismo periodo.</p>
      )}
      <div ref={box} className="chart chart-full" data-testid="price-chart-full" role="group"
           aria-label={own
             ? `Precio de ${symbol} en ${range} frente al S&P 500${data.sector.status === "ok" ? ` y a ${data.sector.symbol}` : ""}, en base 100 y con dividendos, con el volumen debajo`
             : `Sin la serie de la empresa: S&P 500${data.sector.status === "ok" ? ` y ${data.sector.symbol}` : ""} en ${range}, en base 100 y con dividendos`} />
      <p className="legend">
        {own && <span><i className="sw line co" />{symbol}</span>}<span><i className="sw line mk" />S&P 500</span>
        {data.sector.status === "ok" && <span><i className="sw line se" />{data.sector.symbol}</span>}
        {own && <span><i className="sw vol" />Volumen</span>}
        <span className="muted">Base 100 al inicio del periodo, con dividendos</span>
      </p>
      <p className="attribution muted">
        Gráfica: <a href="https://www.tradingview.com/" target="_blank" rel="noreferrer">TradingView Lightweight Charts™</a> · Copyright (с) 2025 TradingView, Inc.
      </p>
    </div>
  );
}
