"use client";
import { useEffect, useRef, useState } from "react";
import { WEB } from "@/lib/generated/backendConfig";
import { advance, startPace, stationFill, type PaceConfig, type PaceState } from "@/v2/lib/loadingPace";

/** V4 (PM, maqueta aprobada): la pantalla de carga del análisis. El anillo con el logo y su giro lento; «Analizando»; el
 *  nombre corto de la empresa con su ticker (o solo el ticker); una tarjeta con la estación en curso, qué se hace en
 *  ella, la barra de cinco tramos con sus etiquetas; y un pie con lo que suele tardar. Cinco estaciones iguales
 *  (`loadingPace`); textos y tiempos, de la config (data.toml [web]). */
const L = WEB.loading;
export const LOADING_STEPS = L.titles;
const PACE: PaceConfig = { stations: L.titles.length, expectedMs: L.expectedMs, fastMs: L.fastMs, stallFill: L.stallFill };
const PCT = 100;
const REDUCED = "(prefers-reduced-motion: reduce)";

/** «Suele tardar entre 1 y 5 segundos la primera vez; después, al instante.» (p50 y p95 medidos, hacia fuera). */
export const TYPICAL_TEXT = `Suele tardar entre ${Math.floor(L.typicalS[0])} y ${Math.ceil(L.typicalS[L.typicalS.length - 1])} `
  + "segundos la primera vez; después, al instante.";

export default function AnalyzeLoading({ symbol, name, startedAt, arrivedAt, onFinished }: {
  symbol: string;
  /** Nombre corto (sin forma jurídica), si se conoce antes del análisis. */
  name: string | null;
  /** Cuándo empezó la petición (performance.now()) y cuándo llegó el análisis (ms desde entonces), o null. */
  startedAt: number; arrivedAt: number | null;
  /** Fin de la disolución: quien la pinta la quita. */
  onFinished: () => void;
}) {
  // el ritmo sale del tiempo transcurrido (loadingPace), un fotograma cada vez; no de temporizadores
  const pace = useRef<PaceState>(startPace(PACE));
  const [view, setView] = useState<{ s: PaceState; now: number }>(() => ({ s: startPace(PACE), now: 0 }));
  const [exiting, setExiting] = useState(false);
  const [reduced] = useState(() => typeof window.matchMedia === "function" && window.matchMedia(REDUCED).matches);

  useEffect(() => {
    let raf = 0;
    const tick = () => {
      const t = performance.now() - startedAt;
      const next = advance(pace.current, PACE, t, arrivedAt !== null && arrivedAt <= t ? arrivedAt : null);
      pace.current = next;
      setView({ s: next, now: t });
      if (!next.done) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [startedAt, arrivedAt]);

  const { s, now } = view;
  useEffect(() => {
    if (!s.done) return;
    const t1 = setTimeout(() => setExiting(true), L.exitHoldMs);
    const t2 = setTimeout(onFinished, L.exitHoldMs + L.exitMs);
    return () => { clearTimeout(t1); clearTimeout(t2); };
  }, [s.done, onFinished]);

  const n = PACE.stations;
  const index = Math.min(s.index, n - 1);
  const title = s.stalled ? L.stallTitle : L.titles[index];
  // con «reducir movimiento», salto por estación: el tramo en curso no se llena poco a poco
  const fill = (i: number) => (i < s.index || s.done ? 1 : i > s.index ? 0 : reduced ? 0 : stationFill(s, PACE, now));
  return (
    <div className={`analyze-loading${exiting ? " out" : ""}`} data-testid="analyze-loading" data-station={index}
         style={{ animationDuration: exiting ? `${L.exitMs}ms` : undefined }}>
      <div className="al-inner">
        <div className="al-ring" aria-hidden="true">
          <svg viewBox="0 0 200 200">
            <circle className="trk" cx="100" cy="100" r="88" />
            <circle className="d1" cx="100" cy="100" r="88" />
            <circle className="d2" cx="100" cy="100" r="72" />
          </svg>
          {/* eslint-disable-next-line @next/next/no-img-element -- export estático: sin optimizador de imágenes */}
          <img src="/brand/finanzer-logo.svg" alt="" width={64} height={64} />
        </div>
        <p className="al-eyebrow">Analizando</p>
        <h1 className="al-who">
          {name ? <>{name}<span className="al-sym num">{symbol}</span></> : <span className="num">{symbol}</span>}
        </h1>
        <div className="al-card surface">
          <div className="al-now">
            <b key={`t${index}${s.stalled}`} className="al-fade al-title">{title}</b>
            <small className="num">Paso {index + 1} de {n}</small>
          </div>
          <p key={`p${index}${s.stalled}`} className="al-fade al-phrase">{s.stalled ? L.stallPhrase : L.phrases[index]}</p>
          <div className="al-seg" aria-hidden="true">
            {L.labels.map((l, i) => <i key={l}><span style={{ width: `${fill(i) * PCT}%` }} /></i>)}
          </div>
          <div className="al-labels" aria-hidden="true">
            {L.labels.map((l, i) => <span key={l} className={i < index || s.done ? "done" : i === index ? "cur" : undefined}>{l}</span>)}
          </div>
        </div>
        <p className="al-foot">{TYPICAL_TEXT}</p>
        {/* Para lectores de pantalla, la estación en curso (lo de arriba es visual) */}
        <span className="sr-only" role="status" aria-live="polite">
          {s.done ? `Análisis de ${symbol} listo` : `Analizando ${symbol}: ${title}, paso ${index + 1} de ${n}`}
        </span>
      </div>
    </div>
  );
}
