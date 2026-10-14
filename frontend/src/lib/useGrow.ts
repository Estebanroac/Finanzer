"use client";

import { useEffect, useState } from "react";

/** true si el usuario pidió reducir el movimiento (sin animaciones de entrada). */
export function prefersReducedMotion(): boolean {
  return typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

/**
 * Dispara las animaciones de entrada de las visualizaciones: devuelve false en el
 * primer render y true al siguiente frame, de modo que barras, anillos y marcadores
 * transicionen de 0 a su valor al montar el panel. Con prefers-reduced-motion el
 * estado final llega sin animación (y el CSS apaga las transiciones); en pestañas en
 * segundo plano, el timeout de seguridad garantiza el estado final.
 */
export function useGrow(): boolean {
  const [on, setOn] = useState(false);
  useEffect(() => {
    if (prefersReducedMotion()) {
      const id = requestAnimationFrame(() => setOn(true));
      return () => cancelAnimationFrame(id);
    }
    const raf = requestAnimationFrame(() => requestAnimationFrame(() => setOn(true)));
    const safety = setTimeout(() => setOn(true), 400);
    return () => {
      cancelAnimationFrame(raf);
      clearTimeout(safety);
    };
  }, []);
  return on;
}

/** Cuenta de 0 a `target` con easing (número del anillo); inmediato con movimiento reducido. */
export function useCountUp(target: number | null, durationMs = 1200): number | null {
  const [n, setN] = useState<number | null>(target == null ? null : 0);
  useEffect(() => {
    if (target == null) {
      const id = requestAnimationFrame(() => setN(null));
      return () => cancelAnimationFrame(id);
    }
    if (prefersReducedMotion()) {
      const id = requestAnimationFrame(() => setN(target));
      return () => cancelAnimationFrame(id);
    }
    const t0 = performance.now();
    let rid = 0;
    const tick = (now: number) => {
      const elapsed = now - t0;
      const p = Math.min(1, elapsed / durationMs);
      setN(Math.round(target * (1 - Math.pow(1 - p, 3))));
      if (elapsed < durationMs) rid = requestAnimationFrame(tick);
    };
    rid = requestAnimationFrame(tick);
    const safety = setTimeout(() => setN(target), durationMs + 500);
    return () => {
      cancelAnimationFrame(rid);
      clearTimeout(safety);
    };
  }, [target, durationMs]);
  return n;
}
