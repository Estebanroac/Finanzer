"use client";

import { useEffect, useState } from "react";

/**
 * Dispara las animaciones de entrada de las visualizaciones: devuelve false en
 * el primer render y true al siguiente frame, de modo que las barras/áreas
 * transicionen de 0 a su valor al montar el panel. Con prefers-reduced-motion
 * (o en pestañas en segundo plano, vía el fallback por timeout) el estado
 * final queda garantizado.
 */
export function useGrow(): boolean {
  const [on, setOn] = useState(false);
  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setOn(true);
      return;
    }
    const raf = requestAnimationFrame(() => setOn(true));
    const safety = setTimeout(() => setOn(true), 400); // pestaña en background
    return () => {
      cancelAnimationFrame(raf);
      clearTimeout(safety);
    };
  }, []);
  return on;
}
