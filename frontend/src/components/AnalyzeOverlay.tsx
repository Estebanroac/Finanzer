"use client";

import { useEffect, useRef, useState } from "react";

const STEPS = [
  "Recopilando estados financieros",
  "Calculando ratios y múltiplos",
  "Altman Z-Score · Piotroski F-Score",
  "Modelo de valoración DCF",
  "Puntuación Finanzer",
];

// Ritmo de los primeros pasos (ms desde el montaje). El último paso queda en
// "activo" (spinner) hasta que el backend responda: la animación cubre la
// carga real y se disuelve exactamente cuando los datos están listos.
const STEP_SCHEDULE = [420, 900, 1380, 1860];
const MIN_SHOWTIME = 2250; // mínimo en pantalla para que la secuencia se lea
const EXIT_HOLD = 320;     // pausa con todo completado antes de disolver
const EXIT_ANIM = 620;     // duración de la disolución (aoOut)

export default function AnalyzeOverlay({
  symbol,
  companyName,
  done,
  onFinished,
}: {
  symbol: string;
  companyName?: string | null;
  done: boolean;
  onFinished: () => void;
}) {
  const [completed, setCompleted] = useState(0); // pasos completados (0..5)
  const [exiting, setExiting] = useState(false);
  const [barTarget, setBarTarget] = useState(0); // 0 -> 88 (espera) -> 100 (done)
  const [minElapsed, setMinElapsed] = useState(false);
  const finishedRef = useRef(false);

  // Avance de los primeros 4 pasos con ritmo fijo
  useEffect(() => {
    const timers = STEP_SCHEDULE.map((ms, i) =>
      setTimeout(() => setCompleted(c => Math.max(c, i + 1)), ms)
    );
    const minT = setTimeout(() => setMinElapsed(true), MIN_SHOWTIME);
    // La barra arranca hacia 88% (asintótica vía transición CSS larga);
    // el 12% restante se completa cuando el backend responde.
    const raf = requestAnimationFrame(() => setBarTarget(88));
    return () => {
      timers.forEach(clearTimeout);
      clearTimeout(minT);
      cancelAnimationFrame(raf);
    };
  }, []);

  // Cierre: datos listos + tiempo mínimo cumplido -> completar todo y disolver
  useEffect(() => {
    if (!done || !minElapsed || finishedRef.current) return;
    finishedRef.current = true;
    setCompleted(STEPS.length);
    setBarTarget(100);
    const t1 = setTimeout(() => setExiting(true), EXIT_HOLD);
    const t2 = setTimeout(() => onFinished(), EXIT_HOLD + EXIT_ANIM);
    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
    };
  }, [done, minElapsed, onFinished]);

  return (
    <div className={`ao-overlay${exiting ? " ao-out" : ""}`} aria-hidden="true">
      <div className="ao-bg" />
      <div className="ao-glow" />
      <div className="ao-grid" />
      <div className="ao-inner">
        <div className="ao-ticker">{symbol || "—"}</div>
        <div className="ao-company">{companyName || " "}</div>
        <div className="ao-scanner">
          <svg className="ao-ring" viewBox="0 0 200 200">
            <circle className="trk" cx="100" cy="100" r="88" />
            <circle className="d1" cx="100" cy="100" r="88" />
            <circle className="d2" cx="100" cy="100" r="72" />
          </svg>
          <div className="ao-sweep" />
          <div className="ao-orbit"><span className="p" /></div>
          <div className="ao-orbit o2"><span className="p" /></div>
          <img className="ao-logo" src="/logo.png" alt="" />
        </div>
        <div className="ao-label">
          Analizando <b>{symbol}</b> · fundamentales
        </div>
        <ul className="ao-steps">
          {STEPS.map((label, i) => (
            <li
              key={label}
              className={i < completed ? "done" : i === completed ? "active" : ""}
            >
              <span className="ao-dot" />
              {label}
            </li>
          ))}
        </ul>
        <div className="ao-bar">
          <div
            className="ao-bar-fill"
            style={{
              width: `${barTarget}%`,
              transition:
                barTarget >= 100
                  ? "width 0.35s cubic-bezier(0.45,0,0.15,1)"
                  : "width 5.5s cubic-bezier(0.3,0.6,0.35,1)",
            }}
          />
        </div>
      </div>
    </div>
  );
}
