"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import type { TrendingData, TrendingItem, TrendingResponse } from "@/lib/api";
import { fetchTrending } from "@/v2/lib/companyData";
import { backoffMs, isAbort } from "@/v2/lib/http";
import { rememberName } from "@/lib/stockNames";
import { stockHref } from "@/v2/lib/search";
import { fetchSparklines, SPARK_PERIODS, staleToRefresh, type SparkItem, type SparkPeriod } from "@/v2/lib/sparklines";
import Sparkline from "./Sparkline";
import { useCarousel } from "./useCarousel";
import { reducedMotion } from "@/v2/lib/motion";
import SegmentInk from "@/v2/components/SegmentInk";
import { CACHED_PERIOD, cachedLabel, loadHome, saveHome, type CachedHome } from "./homeCache";
import { priceText, shouldPoll } from "./trendingModel";
import {
  changeLabel, contextLine, DAY_LISTS, engineLine, hasSelection, mergeTrending, sectorChips, selectedItems, sentence, shownChange,
  type SectorChip, type Selection,
} from "./tickerModel";

/** Si el servidor no responde, se reintenta con la pausa del cálculo (backend [trending] poll_s) y, si sigue fallando,
 *  con espera creciente (revisión V6, F16) hasta FAIL_CAP_S. */
const FAIL_CAP_S = 60;
const FALLBACK_POLL_S = 4;   // por debajo del keep-alive del servidor (5 s), como el sondeo (backend [trending] poll_s)
const MS = 1000;
/** Segundos de animación por valor: el cintillo avanza a la misma velocidad con 12 o con 30 valores. */
const SECONDS_PER_ITEM = 4;
const SKELETON_ITEMS = 6;
/** Anchos de los chips de sector mientras se calcula: una fila como la de verdad (valores CSS: son de dibujo, no
 *  cortes de banda; npm run check no admite listas de números en estos componentes). */
const SKELETON_SECTORS = ["6.5rem", "8rem", "10rem", "7rem", "9rem"];

function useMedia(query: string): boolean {
  const [on, setOn] = useState(false);
  useEffect(() => {
    const m = window.matchMedia(query);
    const sync = () => setOn(m.matches);
    sync();
    m.addEventListener("change", sync);
    return () => m.removeEventListener("change", sync);
  }, [query]);
  return on;
}

/** Una tarjeta del cintillo: toda ella enlaza a /v2/{T}. A la izquierda, ticker, precio, variación y nombre; a la
 *  derecha, la mini-gráfica; abajo, la calidad y el precio del motor si ya están en caché. */
function TickerItem({ item, spark, period, copy }: {
  item: TrendingItem; spark: SparkItem | undefined; period: SparkPeriod; copy: boolean;
}) {
  const ch = shownChange(item);
  const c = changeLabel(ch.value);
  const tone = ch.value === null || ch.value === 0 ? "neutral" : ch.value > 0 ? "good" : "bad";
  const eng = engineLine(item);
  const per = SPARK_PERIODS.find((x) => x.key === period)!.label;
  const name = item.name ?? item.symbol;
  const label = `${item.symbol}, ${name}: ${priceText(item.price)}, ${c.sr} en ${per}` +
    (eng ? `; calidad ${eng.quality}, precio ${eng.price}` : "");
  return (
    <li className="tk-cell">
      <a className="tk-item" href={stockHref(item.symbol)} aria-label={label} tabIndex={copy ? -1 : undefined}
        data-testid={copy ? undefined : "ticker-item"} data-symbol={item.symbol}
        onClick={() => rememberName(item.symbol, item.name)}>
        <span className="tk-sym">{item.symbol}</span>
        <span className="tk-px num">{priceText(item.price)}</span>
        <span className={`tk-chg num tone-${tone}`} title={ch.reason ?? undefined}>
          {c.arrow && <span aria-hidden="true">{c.arrow} </span>}{c.text}
        </span>
        <Sparkline item={spark} />
        <span className="tk-name">{name}</span>
        {/* Sin análisis en caché, la misma línea invita a abrirlo: todas las tarjetas tienen la misma estructura. */}
        {eng ? <span className="tk-eng">Calidad <b>{eng.quality}</b> · Precio <b>{eng.price}</b></span>
          : <span className="tk-eng tk-go">Ver análisis →</span>}
      </a>
    </li>
  );
}

/** P8: portada con cintillo. Filtros centrados (listas, sectores y periodo), el cintillo que rota solo (P8b:
 *  contenedor desplazable, useCarousel: trackpad, dedo, flechas y arrastre con el ratón; se detiene con el ratón, el
 *  foco o cualquier interacción y se reanuda solo, sin botón: WCAG 2.2.2; quieto con «reducir movimiento») y una línea
 *  de contexto. Las mini-gráficas llegan después del primer
 *  pintado y no bloquean el buscador. */
export default function TickerStrip() {
  const [resp, setResp] = useState<TrendingResponse | null>(null);
  const [lastGood, setLastGood] = useState<TrendingData | null>(null);
  const [failed, setFailed] = useState<string | null>(null);
  const [sel, setSel] = useState<Selection>({ kind: "list", key: "most_traded" });
  const [period, setPeriod] = useState<SparkPeriod>("1D");
  const [sparks, setSparks] = useState<Record<string, Record<string, SparkItem>>>({});
  const [sparkErr, setSparkErr] = useState<string | null>(null);
  const [moreOpen, setMoreOpen] = useState(false);
  const reduced = useMedia("(prefers-reduced-motion: reduce)");
  const tape = useRef<HTMLDivElement | null>(null);
  const refreshed = useRef<Set<string>>(new Set());
  // Portada rápida: la última portada buena de este navegador, al momento y con su hora, hasta que llega la del servidor.
  const [cached, setCached] = useState<CachedHome | null>(null);
  useEffect(() => { setCached(loadHome()); }, []);
  const moreBtn = useRef<HTMLButtonElement | null>(null);
  const menu = useRef<HTMLUListElement | null>(null);

  // Revisión V6 (F16), traída del antiguo Trending.tsx en la fusión de E4: el sondeo se para con la pestaña oculta
  // (document.hidden) y sigue al volver; los fallos seguidos esperan cada vez más; al desmontar se cancela la petición.
  useEffect(() => {
    let timer: ReturnType<typeof setTimeout> | undefined;
    const ac = new AbortController();
    let failures = 0;
    let pending = false;          // tocaba preguntar con la pestaña oculta: se pregunta al volver
    const later = (ms: number) => { timer = setTimeout(() => (document.hidden ? (pending = true) : load()), ms); };
    const load = () => {
      pending = false;
      fetchTrending(period, ac.signal).then((r) => {
        failures = 0;
        setResp(r);
        setFailed(null);
        if (r.data) { const d = r.data; setLastGood((prev) => mergeTrending(prev, d)); }
        if (shouldPoll(r)) later(r.poll_s * MS);
      }).catch((e: Error) => {
        if (isAbort(e)) return;
        setFailed(e.message);
        later(backoffMs(failures++, FALLBACK_POLL_S * MS, FAIL_CAP_S * MS));
      });
    };
    const onVisible = () => { if (!document.hidden && pending) load(); };
    document.addEventListener("visibilitychange", onVisible);
    load();
    return () => { ac.abort(); clearTimeout(timer); document.removeEventListener("visibilitychange", onVisible); };
  }, [period]);

  // lo que ya se tenía (también de otros periodos) junto con lo último que llegó; sin nada del servidor, la guardada
  const live = lastGood ?? resp?.data ?? null;
  const fromCache = !live && cached !== null;
  const data = live ?? cached?.data ?? null;
  const fresh = useMemo(() => selectedItems(data, sel, period), [data, sel, period]);
  // v4.1 (movimiento): mientras llega el periodo o la lista nuevos, el cintillo conserva sus tarjetas (antes se vaciaba y
  // la página subía y bajaba: CLS) y las cambia con un fundido cuando llegan
  const arrived = hasSelection(data, sel, period);
  const [kept, setKept] = useState<{ items: TrendingItem[]; period: SparkPeriod }>({ items: fresh, period });
  if (arrived && (kept.items !== fresh || kept.period !== period)) setKept({ items: fresh, period });
  const { items, period: shownPeriod } = arrived ? { items: fresh, period } : kept;
  const symbolsKey = items.map((x) => x.symbol).join(",");
  // al cambiar las tarjetas, entran con un fundido breve (no de golpe); con «reducir movimiento», sin él
  const swapKey = `${symbolsKey}|${shownPeriod}`;
  const lastSwap = useRef(swapKey);
  useEffect(() => {
    if (lastSwap.current === swapKey) return;
    const first = !lastSwap.current.split("|")[0];       // la primera vez que llegan, sin fundido: ya entran solas
    lastSwap.current = swapKey;
    if (first) return;
    const run = tape.current?.querySelector<HTMLElement>(".run");
    if (!run || reducedMotion()) return;
    run.animate([{ opacity: 0.25 }, { opacity: 1 }], { duration: 220, easing: "cubic-bezier(0.23, 1, 0.32, 1)" });
  }, [swapKey]);

  // Mini-gráficas del periodo, después del primer pintado (no compiten con el buscador). Las que ya están no se piden.
  useEffect(() => {
    if (!symbolsKey) return;
    const have = sparks[shownPeriod] ?? {};
    const missing = symbolsKey.split(",").filter((s) => !have[s]);
    if (!missing.length) return;
    const ctl = new AbortController();
    const t = setTimeout(() => {
      fetchSparklines(missing, shownPeriod, ctl.signal).then((r) => {
        setSparkErr(null);
        // V6b: un símbolo pedido que no vuelve queda «sin dato» (no se vuelve a pedir en bucle)
        const none = Object.fromEntries(missing.filter((s) => !r.items[s])
          .map((s) => [s, { status: "sin_dato" as const, reason: "el servidor no devolvió la gráfica de este valor" }]));
        setSparks((prev) => ({ ...prev, [shownPeriod]: { ...(prev[shownPeriod] ?? {}), ...none, ...r.items } }));
      }).catch((e: Error) => { if (e.name !== "AbortError") setSparkErr(e.message); });
    }, 0);
    return () => { clearTimeout(t); ctl.abort(); };
  }, [symbolsKey, shownPeriod, sparks]);

  // Portada rápida: la vista inicial que llegó del servidor (listas de 1D y mini-gráficas de «Más negociadas») se guarda
  // en este navegador; saveHome no la cambia por una más antigua.
  const initialSparks = sparks[CACHED_PERIOD];
  useEffect(() => {
    if (!live?.lists?.[CACHED_PERIOD]) return;
    const first = new Set(live.lists[CACHED_PERIOD].most_traded.map((x) => x.symbol));
    saveHome(live, Object.fromEntries(Object.entries(initialSparks ?? {}).filter(([s]) => first.has(s))));
  }, [live, initialSparks]);

  // Portada rápida: las que llegaron caducadas (el servidor las sirve al momento y las refresca) se piden otra vez
  // pasada la pausa del sondeo, una sola vez por valor y periodo.
  const staleKey = staleToRefresh(sparks[period] ?? {}, refreshed.current, period).join(",");
  useEffect(() => {
    if (!staleKey) return;
    const stale = staleKey.split(",");
    const ctl = new AbortController();
    const t = setTimeout(() => {
      fetchSparklines(stale, period, ctl.signal).then((r) => {
        stale.forEach((s) => refreshed.current.add(`${period}:${s}`));
        setSparks((prev) => ({ ...prev, [period]: { ...(prev[period] ?? {}), ...r.items } }));
      }).catch(() => { /* se quedan las de antes */ });
    }, (resp?.poll_s ?? FALLBACK_POLL_S) * MS);
    return () => { clearTimeout(t); ctl.abort(); };
  }, [staleKey, period, resp?.poll_s]);

  // P8b: contenedor desplazable que avanza solo (lista o periodo nuevos: vuelve al principio)
  const { mode, dragging } = useCarousel(tape, { reduced, secondsPerItem: SECONDS_PER_ITEM, itemCount: items.length,
    resetKey: `${sel.kind}:${sel.key}:${shownPeriod}` });
  const loop = !reduced;                              // la copia que cierra el bucle
  // v4 cintillo: en pantallas táctiles avanza con transform (useCarousel decide con la misma consulta)
  const touchDrive = useMedia("not all and (hover: hover) and (pointer: fine)") && !reduced;

  // Flechas con el foco en una tarjeta: la anterior o la siguiente (queda a la vista; el cintillo no avanza con el foco).
  const onTapeKey = (e: React.KeyboardEvent) => {
    if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
    const cards = Array.from(tape.current?.querySelectorAll<HTMLAnchorElement>("[data-testid=ticker-item]") ?? []);
    const i = cards.indexOf(document.activeElement as HTMLAnchorElement);
    if (i < 0) return;
    e.preventDefault();
    const next = cards[(i + (e.key === "ArrowRight" ? 1 : -1) + cards.length) % cards.length];
    next.focus();
    next.scrollIntoView({ block: "nearest", inline: "nearest" });
  };

  const choose = (s: Selection) => { setSel(s); setMoreOpen(false); };
  const choosePeriod = (p: SparkPeriod) => setPeriod(p);
  const isOn = (s: Selection) => s.kind === sel.kind && s.key === sel.key;
  const { primary, more } = sectorChips(data, period);
  const moreActive = sel.kind === "sector" ? more.find((x) => x.key === sel.key) : undefined;

  // Menú «Más ▾»: Escape lo cierra y devuelve el foco; flechas entre opciones; clic fuera lo cierra.
  useEffect(() => {
    if (!moreOpen) return;
    const first = menu.current?.querySelector<HTMLButtonElement>("button:not([aria-disabled=true])");
    first?.focus();
    const close = (e: MouseEvent) => {
      if (!menu.current?.contains(e.target as Node) && !moreBtn.current?.contains(e.target as Node)) setMoreOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [moreOpen]);
  const onMenuKey = (e: React.KeyboardEvent) => {
    const opts = Array.from(menu.current?.querySelectorAll<HTMLButtonElement>("button") ?? []);
    const i = opts.indexOf(document.activeElement as HTMLButtonElement);
    if (e.key === "Escape") { e.preventDefault(); setMoreOpen(false); moreBtn.current?.focus(); }
    else if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      opts[(i + (e.key === "ArrowDown" ? 1 : -1) + opts.length) % opts.length]?.focus();
    } else if (e.key === "Tab") setMoreOpen(false);
  };

  const sectorButton = (c: SectorChip, role?: "menuitemradio") => (
    <button key={c.key} type="button" role={role} className={`chip${isOn({ kind: "sector", key: c.key }) ? " on" : ""}`}
      aria-pressed={role ? undefined : isOn({ kind: "sector", key: c.key })}
      aria-checked={role ? isOn({ kind: "sector", key: c.key }) : undefined}
      aria-disabled={!c.available || undefined} title={c.available ? undefined : `${c.label}: ${c.reason}`}
      data-testid={`sector-${c.key}`}
      onClick={() => { if (c.available) choose({ kind: "sector", key: c.key }); }}>{c.label}</button>
  );

  const calculating = !data && (resp === null || resp.status === "calculando");
  const noData = !data && resp?.status === "sin_dato";
  const cards = (copy: boolean) => items.map((x) => (
    <TickerItem key={x.symbol} item={x} period={shownPeriod} copy={copy}
      spark={sparks[shownPeriod]?.[x.symbol] ?? (fromCache && shownPeriod === CACHED_PERIOD ? cached?.sparks[x.symbol] : undefined)} />
  ));

  return (
    <section className="ticker" aria-labelledby="ticker-title">
      <h2 id="ticker-title" className="sr-only">Valores de la sesión</h2>
      <div className="wrap filters">
        <div className="frow frow-top">
          <div className="fgroup fgroup-day" role="group" aria-label="Listas">
            <span className="glabel" aria-hidden="true">Listas</span>
            <div className="fchips">
            {DAY_LISTS.map((l) => (
              <button key={l.key} type="button" className={`chip${isOn({ kind: "list", key: l.key }) ? " on" : ""}`}
                aria-pressed={isOn({ kind: "list", key: l.key })} data-testid={`list-${l.key}`}
                onClick={() => choose({ kind: "list", key: l.key })}>
                {l.arrow && <span className={`chip-arrow tone-${l.arrow === "up" ? "good" : "bad"}`} aria-hidden="true">
                  {l.arrow === "up" ? "▲" : "▼"} </span>}{l.label}
              </button>
            ))}
            </div>
          </div>
          <span className="fsep" aria-hidden="true" />
          {/* P8b: el periodo es el de las listas y el de las gráficas (uno solo) */}
          <div className="fgroup fgroup-period" role="group" aria-label="Periodo de las listas y las gráficas">
            <span className="glabel" aria-hidden="true">Periodo</span>
            <div className="per">
              <SegmentInk active={period} />
              {SPARK_PERIODS.map((p) => (
                <button key={p.key} type="button" className={period === p.key ? "on" : ""} aria-pressed={period === p.key}
                  data-testid={`period-${p.key}`} onClick={() => choosePeriod(p.key)}>{p.label}</button>
              ))}
            </div>
          </div>
        </div>
        {primary.length > 0 && (
          <div className="frow">
            <div className="fgroup fgroup-sectors" role="group" aria-label="Sectores">
              <span className="glabel" aria-hidden="true">Sectores</span>
              <div className="fchips">
              {primary.map((c) => sectorButton(c))}
              {more.length > 0 && (
                <span className="more-wrap">
                  <button ref={moreBtn} type="button" className={`chip more${moreActive ? " on" : ""}`}
                    aria-haspopup="menu" aria-expanded={moreOpen} aria-controls="more-sectors" data-testid="sector-more"
                    onClick={() => setMoreOpen((o) => !o)}>
                    {moreActive ? moreActive.label : "Más"} <span aria-hidden="true">▾</span>
                  </button>
                  {moreOpen && (
                    <ul id="more-sectors" ref={menu} className="more-menu surface" role="menu" aria-label="Más sectores"
                      onKeyDown={onMenuKey}>
                      {more.map((c) => <li key={c.key} role="none">{sectorButton(c, "menuitemradio")}</li>)}
                    </ul>
                  )}
                </span>
              )}
              </div>
            </div>
          </div>
        )}
        {/* v4.1: mientras se calcula, la fila de sectores ya ocupa su sitio (al llegar no empuja la página: CLS) */}
        {calculating && (
          <div className="frow" aria-hidden="true">
            <div className="fgroup fgroup-sectors"><div className="fchips">
              {SKELETON_SECTORS.map((w, i) => <span key={i} className="chip skel-chip" style={{ width: w }}>{"\u00a0"}</span>)}
            </div></div>
          </div>
        )}
      </div>

      {calculating && (
        <div className="tape skeleton" aria-busy="true">
          <p className="sr-only" role="status">Calculando los valores de la sesión…</p>
          <ul className="run" aria-hidden="true">
            {Array.from({ length: SKELETON_ITEMS }, (_, i) => (
              // v4.1: la misma retícula y las mismas líneas que una tarjeta (mide lo mismo: al llegar no salta nada)
              <li key={i} className="tk-cell"><div className="tk-item">
                <span className="tk-sym"><span className="skel skel-sym">{"\u00a0"}</span></span>
                <span className="tk-px"><span className="skel skel-value">{"\u00a0"}</span></span>
                <span className="tk-chg"><span className="skel skel-value">{"\u00a0"}</span></span>
                <svg className="spark empty" viewBox="0 0 136 52" />
                <span className="tk-name"><span className="skel skel-name">{"\u00a0"}</span></span>
                <span className="tk-eng"><span className="skel skel-name">{"\u00a0"}</span></span></div></li>
            ))}
          </ul>
        </div>
      )}
      {calculating && <div className="wrap ticker-foot skel-foot" aria-hidden="true"><p className="muted">{"\u00a0"}</p></div>}
      {noData && <p className="state" role="status">No hay valores de la sesión ahora mismo. {sentence(resp?.reason)}</p>}
      {failed && !data && !calculating && <p className="state" role="status">No se pudo consultar el servidor ({failed}).</p>}

      {data && (
        <div ref={tape} className={`tape scroller${loop ? " looping" : ""}${touchDrive ? " tx" : ""}${dragging ? " dragging" : ""}`}
          data-testid="ticker" data-mode={mode} data-pending={arrived ? undefined : ""} aria-busy={arrived ? undefined : true} onKeyDown={onTapeKey}>
          <div className="track">
            <ul className="run" aria-label={`${items.length} valores`}>{cards(false)}</ul>
            {/* V6b: la copia que cierra el bucle queda fuera de los lectores (aria-hidden) y del tabulador (sus enlaces
                con tabIndex −1), pero no es `inert`: con el bucle, media vuelta se ve la copia y sus tarjetas se pulsan. */}
            {loop && <ul className="run" aria-hidden="true" data-copy="">{cards(true)}</ul>}
          </div>
        </div>
      )}

      {data && (
        <div className="wrap ticker-foot">
          {fromCache && cached && (
            <p className="muted" role="status" data-testid="ticker-cached">
              Guardado en este navegador: {cachedLabel(cached.data.as_of, new Date())}. Actualizando…
            </p>
          )}
          <p className="muted" data-testid="ticker-context">{contextLine(data, sel, shownPeriod, items.length)}
            {sparkErr && <> · sin mini-gráficas ahora ({sparkErr})</>}{data.note && <> · aviso: {data.note}</>}</p>
        </div>
      )}
    </section>
  );
}
