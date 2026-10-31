"use client";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState, useSyncExternalStore } from "react";
import type { StockAnalysis } from "@/lib/api";
import { fetchAnalysisV2 } from "@/v2/lib/analysis";
import { readTheme, useTheme, writeTheme } from "@/v2/lib/theme";
import TopBar from "@/v2/components/TopBar";
import CompanyHeader from "@/v2/components/CompanyHeader";
import ChapterBar from "@/v2/components/ChapterBar";
import LoadError from "@/v2/components/LoadError";
import AnalyzeLoading from "@/v2/components/AnalyzeLoading";
import { recallName } from "@/lib/stockNames";
import { companyShort } from "@/v2/lib/companyName";
import { WEB } from "@/lib/generated/backendConfig";
import DepthPage, { PAGE_TITLES } from "@/v2/pages/DepthPage";
import { buildReadings } from "@/v2/lib/story";
import { chapterHref, parseV2Path, type ChapterSlug, type V2Route } from "@/v2/lib/routes";
import { readCached, writeCached } from "@/v2/lib/analysisCache";
import { isAbort } from "@/v2/lib/http";
import { useDocumentTitle } from "@/v2/lib/useDocumentTitle";
import { preloadLazy } from "@/v2/lib/lazy";
import { CHAPTER_ORDER } from "@/v2/lib/story";
import { crossfade, pageTransition } from "@/v2/lib/motion";

/** La sección que abre /v2/{T} (V4b: no hay una página con todo; la empresa es la primera). */
const FIRST_SECTION: ChapterSlug = "empresa";

/** Lleva la vista al ancla de la URL; sin ancla, en la primera carga arriba y al cambiar de sección al principio de la
 *  nueva, bajo la cabecera fija (V4b, PM: nunca hay que recorrer la cabecera para llegar al contenido). Tras pintar, para
 *  que exista el destino. */
function scrollToTarget(fromNav = false) {
  requestAnimationFrame(() => placeView(fromNav));
}
/** v4.1 (movimiento): dónde se quedó el lector en cada sección (por empresa y sección, durante la visita). Volver a una
 *  pestaña ya leída la abre donde estaba; una nueva, al principio de la sección. */
const readAt = new Map<string, number>();
/** Mientras se coloca la vista tras un cambio de sección, los desplazamientos son del navegador o nuestros (al cambiar
 *  el alto de la página), no del lector: no se anotan como «dónde se leía». */
let placing = false;
const pageKey = () => window.location.pathname.replace(/\/$/, "");
function placeView(fromNav: boolean) {
  const id = decodeURIComponent(window.location.hash.slice(1));
  const section = document.querySelector<HTMLElement>(".depth");
  const kept = readAt.get(pageKey());
  if (id) whenPresent(id, (el) => el.scrollIntoView());
  else if (!fromNav) window.scrollTo(0, 0);
  else if (kept !== undefined && section && kept > section.offsetTop) { restoreTo(kept); return; }
  else section?.scrollIntoView();
  requestAnimationFrame(() => { placing = false; });
}
/** Vuelve a `y`. Si la sección aún no ha crecido hasta ahí (su detalle llega en su propio fragmento), lo reintenta
 *  cada vez que la página crece, hasta llegar, hasta que el lector se mueva o como mucho RESTORE_WAIT_MS. */
const RESTORE_WAIT_MS = 1_500;
/** Medio píxel arriba o abajo (redondeos del navegador): ya está donde se leía. */
const RESTORE_EDGE_PX = 1;
function restoreTo(y: number) {
  const there = () => Math.abs(window.scrollY - y) <= RESTORE_EDGE_PX;
  window.scrollTo(0, y);
  if (there()) { requestAnimationFrame(() => { placing = false; }); return; }
  const ro = new ResizeObserver(() => { window.scrollTo(0, y); if (there()) stop(); });
  const stop = () => { placing = false; ro.disconnect(); clearTimeout(timer); window.removeEventListener("wheel", stop); window.removeEventListener("touchstart", stop); window.removeEventListener("keydown", stop); };
  const timer = setTimeout(stop, RESTORE_WAIT_MS);
  ro.observe(document.body);
  window.addEventListener("wheel", stop, { passive: true });
  window.addEventListener("touchstart", stop, { passive: true });
  window.addEventListener("keydown", stop);
}
const chapterIndex = (path: string) => CHAPTER_ORDER.indexOf(parseV2Path(path).chapter ?? FIRST_SECTION);

/** Cuánto se espera a que aparezca el destino de un ancla (el detalle de la sección llega en su propio fragmento). */
const ANCHOR_WAIT_MS = 5_000;
/** `fn` con el elemento `id` en cuanto exista (ya, o cuando se monte el detalle de la sección). */
function whenPresent(id: string, fn: (el: HTMLElement) => void) {
  const now = document.getElementById(id);
  if (now) { fn(now); return; }
  const mo = new MutationObserver(() => {
    const el = document.getElementById(id);
    if (!el) return;
    stop();
    requestAnimationFrame(() => fn(el));
  });
  const timer = setTimeout(() => stop(), ANCHOR_WAIT_MS);
  const stop = () => { mo.disconnect(); clearTimeout(timer); };
  mo.observe(document.body, { childList: true, subtree: true });
}

/** La cabecera fija (V4b): cuando la completa queda bajo la compacta, aparece la compacta y la barra de secciones baja bajo
 *  ella. Sin estado de React (un atributo y una variable CSS en la raíz): bajar por la página no vuelve a pintarla. Se
 *  decide con lo que se ve (una medida por fotograma al desplazar): un IntersectionObserver mide frente al visor de la
 *  ventana, que en WebKit (iOS) empieza unos px por encima del visible al desplazar, y la cabecera ya tapada no contaba
 *  como fuera (e2e en iPhone). */
function useStuckHeader(root: React.RefObject<HTMLElement | null>, full: React.RefObject<HTMLElement | null>,
                        head: React.RefObject<HTMLElement | null>, on: boolean) {
  useEffect(() => {
    const r = root.current, f = full.current, h = head.current;
    if (!on || !r || !f || !h) return;
    let height = 0, raf = 0;
    const check = () => {
      raf = 0;
      // fija en cuanto la compacta taparía la completa (+1 px: la que toca el borde ya no se lee)
      r.toggleAttribute("data-stuck", f.getBoundingClientRect().bottom < height + 1);
    };
    const schedule = () => { if (!raf) raf = requestAnimationFrame(check); };
    const measure = () => {
      height = Math.round(h.getBoundingClientRect().height);
      r.style.setProperty("--stuck-h", `${height}px`);
      schedule();
    };
    const ro = new ResizeObserver(measure);
    ro.observe(h);
    measure();
    window.addEventListener("scroll", schedule, { passive: true });
    window.addEventListener("resize", schedule);
    return () => {
      ro.disconnect(); cancelAnimationFrame(raf);
      window.removeEventListener("scroll", schedule); window.removeEventListener("resize", schedule);
      r.removeAttribute("data-stuck");
    };
  }, [root, full, head, on]);
}

const NAV = "finanzer:v2-nav";
/** Sin requestIdleCallback (Safari): cuándo empezar a descargar las demás secciones tras pintar la primera. */
const PRELOAD_FALLBACK_MS = 500;
/** V4 (PM): si el análisis llega antes (de la caché), no hay pantalla de carga: entra directo, sin parpadeo. */
const LOADING_DELAY_MS = WEB.loading.delayMs;
/** La ruta como almacén externo (la URL): cambia con la navegación propia (pushState + evento) y con atrás/adelante. */
function subscribeRoute(cb: () => void): () => void {
  window.addEventListener("popstate", cb);
  window.addEventListener(NAV, cb);
  return () => { window.removeEventListener("popstate", cb); window.removeEventListener(NAV, cb); };
}
const NO_ROUTE: V2Route = { symbol: null, chapter: null, invalid: false };

/** Título de la pestaña (revisión V6, F7): sección y empresa. */
export function pageTitle(route: V2Route, name: string | null): string {
  if (route.invalid) return "Ticker no válido · Finanzer";
  if (!route.symbol) return "Finanzer";
  const who = name ? `${name} (${route.symbol})` : route.symbol;
  return `${PAGE_TITLES[route.chapter ?? FIRST_SECTION]} · ${who} · Finanzer`;
}

export default function StoryPageClient() {
  const theme = useTheme();
  const path = useSyncExternalStore(subscribeRoute, () => window.location.pathname, () => null);
  const route = useMemo<V2Route>(() => (path ? parseV2Path(path) : NO_ROUTE), [path]);
  // `at`: cuándo llegó el análisis, en ms desde la petición (el ritmo de la pantalla de carga)
  const [loaded, setLoaded] = useState<{ symbol: string; data: StockAnalysis | null; error: string | null; at?: number } | null>(null);
  // cuándo empezó la petición del símbolo en curso (performance.now()), para la pantalla de carga
  const [startedAt, setStartedAt] = useState(0);
  const [attempt, setAttempt] = useState(0);
  // La pantalla de carga (V4): de qué símbolo está en pantalla; sigue tras llegar el análisis hasta que se disuelve
  const [loading, setLoading] = useState<string | null>(null);
  const loadingUp = useRef(false);
  // Lo cargado vale solo para el símbolo de la ruta (al cambiar de empresa no se pinta la anterior).
  const data = loaded?.symbol === route.symbol ? loaded.data : null;
  const error = loaded?.symbol === route.symbol ? loaded.error : null;

  // El análisis, una vez por símbolo: de la caché de la sesión o del backend (navegar entre páginas no lo repite).
  // Revisión V6 (F2): fetchAnalysisV2 (motivo del backend en español) y cancelación al desmontar o reintentar.
  useEffect(() => {
    const s = route.symbol;
    if (!s) return;
    const ac = new AbortController();
    const cached = readCached(s);
    const load = cached ? Promise.resolve(cached) : fetchAnalysisV2(s, ac.signal).then((d) => { writeCached(s, d); return d; });
    let settled = false;
    const t0 = performance.now();
    const show = setTimeout(() => { if (!settled) { loadingUp.current = true; setStartedAt(t0); setLoading(s); } }, LOADING_DELAY_MS);
    load.then((d) => {
      settled = true;
      if (ac.signal.aborted) return;
      setLoaded({ symbol: s, data: d, error: null, at: performance.now() - t0 });
      if (!loadingUp.current) scrollToTarget();       // con la pantalla de carga, al disolverse (finishLoading)
    }).catch((e: Error) => {
      settled = true;
      if (isAbort(e) || ac.signal.aborted) return;
      // el error sale ya, sin esperar al mínimo en pantalla de la carga
      loadingUp.current = false; setLoading(null);
      setLoaded({ symbol: s, data: null, error: e.message });
    });
    return () => { clearTimeout(show); ac.abort(); };
  }, [route.symbol, attempt]);
  const finishLoading = useCallback(() => { loadingUp.current = false; crossfade(() => setLoading(null)); scrollToTarget(); }, []);
  const retry = () => { setLoaded(null); setAttempt((n) => n + 1); };

  // Revisión V6 (F7): título de la pestaña por empresa y sección, y el foco al título de la sección al cambiar de
  // sección dentro de la web (no en la primera carga: ahí el foco es del navegador).
  useDocumentTitle(pageTitle(route, data?.profile.name ?? null));
  const lastPage = useRef<string | null>(null);
  useEffect(() => {
    if (!data || !route.symbol) return;
    const here = `${route.symbol}/${route.chapter ?? FIRST_SECTION}`;
    if (lastPage.current !== null && lastPage.current !== here) {
      requestAnimationFrame(() => document.querySelector<HTMLElement>("[data-page-title]")?.focus({ preventScroll: true }));
    }
    lastPage.current = here;
  }, [data, route.symbol, route.chapter]);

  // Navegación entre las secciones del mismo símbolo sin recargar (una sola petición del análisis).
  // v4.1: el cambio de sección es una transición de página (fundido y un leve desplazamiento hacia el lado del cambio)
  // y conserva dónde se leía cada sección.
  const go = useCallback((href: string) => {
    const from = window.location.pathname, to = new URL(href, window.location.href).pathname;
    readAt.set(pageKey(), window.scrollY);
    placing = true;
    pageTransition(() => {
      window.history.pushState(null, "", href);
      window.dispatchEvent(new Event(NAV));
      requestAnimationFrame(() => placeView(true));      // con la sección nueva ya pintada
    }, chapterIndex(to) >= chapterIndex(from) ? 1 : -1);
  }, []);
  useEffect(() => {
    if ("scrollRestoration" in window.history) window.history.scrollRestoration = "manual";   // la posición la pone placeView
    let shown = window.location.pathname;
    const back = () => {
      const to = window.location.pathname;
      const dir = chapterIndex(to) >= chapterIndex(shown) ? 1 : -1;
      shown = to;
      placing = true;
      // la marca de dirección ya (la sección nueva entra al montarse); la vista, cuando React la haya pintado
      pageTransition(() => requestAnimationFrame(() => placeView(true)), dir);
    };
    const remember = () => { if (!placing) { shown = window.location.pathname; readAt.set(pageKey(), window.scrollY); } };
    window.addEventListener("popstate", back);
    window.addEventListener("scroll", remember, { passive: true });
    return () => { window.removeEventListener("popstate", back); window.removeEventListener("scroll", remember); };
  }, []);
  // V4b: los enlaces de la antigua página-historia (/v2/{T}#calidad) llevan a la sección (/v2/{T}/calidad).
  useEffect(() => {
    if (!route.symbol || route.chapter) return;
    const old = parseV2Path(`/v2/${route.symbol}/${window.location.hash.slice(1)}`).chapter;
    if (!old) return;
    window.history.replaceState(null, "", chapterHref(route.symbol, old));
    window.dispatchEvent(new Event(NAV));
  }, [route.symbol, route.chapter]);
  const onClick = (e: React.MouseEvent) => {
    const a = (e.target as Element).closest<HTMLAnchorElement>("a[data-nav]");
    if (!a || e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    const next = parseV2Path(new URL(a.href).pathname);
    if (next.symbol !== route.symbol) return;          // otra empresa: navegación normal
    e.preventDefault();
    go(a.getAttribute("href")!);
  };

  const readings = useMemo(() => (data ? buildReadings(data) : null), [data]);
  const { symbol } = route;
  const section = route.chapter ?? FIRST_SECTION;
  // La página se monta cuando la pantalla de carga termina de disolverse (o enseguida si no hubo pantalla): nunca hay dos
  // capas a la vez (lectores de pantalla, foco, capturas y comprobaciones ven solo una).
  const ready = !!data && loading !== symbol;
  const rootRef = useRef<HTMLDivElement>(null), fullRef = useRef<HTMLDivElement>(null), stuckRef = useRef<HTMLDivElement>(null);
  useStuckHeader(rootRef, fullRef, stuckRef, ready);
  // V4b · 3: con la primera sección pintada, las demás (y sus gráficas) se descargan en segundo plano, en un momento
  // libre: cambiar de pestaña no espera a la red ni a Suspense (≈ 330 ms medidos antes, en los tres navegadores)
  useEffect(() => {
    if (!ready) return;
    const w = window as Window & { requestIdleCallback?: (cb: () => void) => number; cancelIdleCallback?: (id: number) => void };
    let idle = 0, timer = 0;
    const later = () => {
      if (w.requestIdleCallback) idle = w.requestIdleCallback(() => { void preloadLazy(); });
      else timer = window.setTimeout(() => { void preloadLazy(); }, PRELOAD_FALLBACK_MS);
    };
    // después de pintar el detalle de la sección abierta (su fragmento va primero, sin competir con los demás)
    const shown = () => !!document.querySelector(".depth .depth-body .dsec");
    const mo = shown() ? null : new MutationObserver(() => { if (shown()) { mo?.disconnect(); later(); } });
    if (mo) mo.observe(document.body, { childList: true, subtree: true }); else later();
    return () => { mo?.disconnect(); if (idle) w.cancelIdleCallback?.(idle); clearTimeout(timer); };
  }, [ready]);

  // v4.1 (movimiento): el cambio de modo, con un fundido cruzado breve (no de golpe)
  const toggle = () => crossfade(() => writeTheme((theme ?? readTheme()) === "dark" ? "light" : "dark"), "theme");

  return (
    <div className="fz2" ref={rootRef} data-theme={theme ?? undefined} onClick={onClick}>
      {/* El PDF solo con un análisis válido cargado (no mientras carga ni con su error: ETF, inexistente, deslistada) */}
      <TopBar symbol={ready ? symbol : null} theme={theme ?? "light"} onToggleTheme={toggle} />
      <main aria-busy={!ready && !error}>
        <div className="wrap">
          {route.invalid && (
            <div className="load-error" role="alert" data-testid="invalid-ticker">
              <h1>Ticker no válido</h1>
              <p>La dirección no lleva un ticker reconocible (por ejemplo, AAPL, BRK-B o MC.PA). Búscalo arriba o vuelve a la portada.</p>
              <p><Link className="btn" href="/v2">Volver a la portada</Link></p>
            </div>
          )}
          {error && symbol && <LoadError symbol={symbol} reason={error} onRetry={retry} />}
          {!route.invalid && !error && symbol && loading === symbol && (
            <AnalyzeLoading symbol={symbol} name={companyShort(recallName(symbol))} startedAt={startedAt}
                            arrivedAt={data ? (loaded?.at ?? 0) : null} onFinished={finishLoading} />
          )}
          {ready && data && (<>
            <h1 data-testid="company-name" className="sr-only" tabIndex={-1}>{data.profile.name}</h1>
            <div ref={fullRef}><CompanyHeader analysis={data} /></div>
          </>)}
        </div>
        {ready && readings && data && symbol && (<>
          {/* Fija arriba al bajar: la cabecera compacta (solo visual) y, debajo, la barra de secciones a ancho completo. */}
          <div className="stuck-head" ref={stuckRef}><div className="wrap"><CompanyHeader analysis={data} compact /></div></div>
          <ChapterBar symbol={symbol} current={section} />
          <DepthPage key={section} chapter={section} analysis={data} symbol={symbol}
                     reading={readings.find((c) => c.id === section)!} />
        </>)}
      </main>
    </div>
  );
}
