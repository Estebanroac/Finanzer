"use client";
import { useRef } from "react";
import SearchBox from "./SearchBox";

/** V4 (PM): el análisis no llegó (404, 422, 5xx, sin conexión o fuera del presupuesto de espera). El ticker, el motivo
 *  en lenguaje claro (el del backend si se entiende; `fetchAnalysisV2`) y dos salidas: volver a pedirlo o buscar otra
 *  empresa, con el buscador de aquí mismo enfocado (en el móvil la barra superior no lleva buscador). */
export default function LoadError({ symbol, reason, onRetry }: { symbol: string; reason: string; onRetry: () => void }) {
  const search = useRef<HTMLDivElement>(null);
  return (
    <section className="load-error surface" data-testid="load-error" aria-labelledby="load-error-title">
      <p className="eyebrow">No se pudo cargar el análisis</p>
      <h1 id="load-error-title" className="num">{symbol}</h1>
      <p role="alert">{reason}</p>
      <p className="load-error-actions">
        <button type="button" className="btn" onClick={onRetry}>Volver a intentarlo</button>
        <button type="button" className="btn ghost"
                onClick={() => search.current?.querySelector<HTMLInputElement>("input")?.focus()}>Buscar otra empresa</button>
      </p>
      <div ref={search} className="load-error-search"><SearchBox hero placeholder="Empresa o ticker (Apple, AAPL…)" /></div>
    </section>
  );
}
