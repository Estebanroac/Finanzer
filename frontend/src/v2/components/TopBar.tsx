"use client";
import { useEffect, useRef, useState } from "react";
import { flushSync } from "react-dom";
import Link from "next/link";
import PdfButton from "@/v2/components/PdfButton";
import type { Theme } from "@/v2/lib/theme";
import SearchBox from "@/v2/components/SearchBox";

/** El aviso de navegación propia entre secciones (StoryPageClient: pushState + este evento). */
const NAV = "finanzer:v2-nav";
/** Lo que puede subir la barra con la fila abierta antes de plegarla (px). */
const SCROLL_SLACK_PX = 8;

export default function TopBar({ symbol, theme, onToggleTheme, search = true }: {
  /** Símbolo de un análisis válido ya cargado: solo con él sale «Descargar PDF» (revisión V6, prueba V2: con un ETF,
   *  un ticker inexistente o una empresa deslistada el PDF respondería 422/404). */
  symbol: string | null; theme: Theme; onToggleTheme: () => void;
  /** La portada lleva su propio buscador grande: la barra deja el hueco vacío. */
  search?: boolean;
}) {
  // Móvil: el buscador va plegado tras la lupa y se despliega en una fila bajo la barra (en escritorio, siempre a la vista)
  const [open, setOpen] = useState(false);
  const header = useRef<HTMLElement>(null);
  const row = useRef<HTMLDivElement>(null);
  const lupa = useRef<HTMLButtonElement>(null);

  // El foco, en el mismo toque: iOS solo saca el teclado si focus() llega dentro del gesto (por eso flushSync)
  const toggle = () => {
    if (open) { setOpen(false); return; }
    flushSync(() => setOpen(true));
    row.current?.querySelector<HTMLInputElement>("input")?.focus();
  };
  const close = () => { setOpen(false); lupa.current?.focus(); };

  // Se cierra al cambiar de página (secciones, atrás/adelante, la página que vuelve de la caché del navegador) y cuando
  // la barra ha subido unos px bajo la franja de la barra de estado (abierta, la barra va por encima de la página y no
  // debe pintarse sobre la franja; el margen tolera el ajuste que hace iOS al sacar el teclado)
  useEffect(() => {
    if (!open) return;
    const shut = () => setOpen(false);
    const back = (e: PageTransitionEvent) => { if (e.persisted) shut(); };   // no al terminar de cargar: solo al volver
    const edge = document.querySelector(".status-edge")?.getBoundingClientRect().height ?? 0;
    const io = new IntersectionObserver(([e]) => { if (e.intersectionRatio !== 1) shut(); },
      { threshold: 1, rootMargin: `${SCROLL_SLACK_PX - Math.round(edge)}px 0px 0px 0px` });
    const bar = header.current?.querySelector(".wrap");
    if (bar) io.observe(bar);
    window.addEventListener("popstate", shut);
    window.addEventListener(NAV, shut);
    window.addEventListener("pageshow", back);
    return () => {
      io.disconnect();
      window.removeEventListener("popstate", shut);
      window.removeEventListener(NAV, shut);
      window.removeEventListener("pageshow", back);
    };
  }, [open]);

  return (<>
    {/* La franja de la barra de estado del iPhone: ver .status-edge en v2.css */}
    <div className="status-edge" aria-hidden="true" />
    <header className="topbar" ref={header}>
      <div className="wrap">
        {/* Marca: el logo en su placa nocturna (la misma forma en los dos temas, en los iconos y en el PDF) y «Finanzer»
            en Manrope 700; el nombre es texto, así que el enlace se llama «Finanzer» para los lectores de pantalla */}
        <Link className="brand" href="/v2">
          {/* eslint-disable-next-line @next/next/no-img-element -- export estático: sin optimizador de imágenes */}
          <img className="brand-logo" src="/brand/finanzer-logo.svg" alt="" width={36} height={36} />
          <span className="brand-word">Finanzer</span>
        </Link>
        {search ? (
          <div className="search-row" id="search-row" ref={row} data-open={open || undefined}
            onKeyDown={(e) => { if (e.key === "Escape" && open) close(); }}>
            <SearchBox onPick={() => setOpen(false)} />
            <button type="button" className="btn search-close" onClick={close}>Cerrar</button>
          </div>
        ) : <span className="search-slot" />}
        <div className="actions">
          {search && (
            <button type="button" className="btn icon-btn search-toggle" ref={lupa} onClick={toggle}
              aria-label="Buscar empresa o ticker" aria-expanded={open} aria-controls="search-row">
              <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <circle cx="10.5" cy="10.5" r="6.5" /><path d="M15.5 15.5 20 20" />
              </svg>
            </button>
          )}
          <button className="btn theme-btn" onClick={onToggleTheme} aria-pressed={theme === "dark"}>
            {/* Revisión V6 (F25): las dos etiquetas en el HTML y el CSS enseña la del tema que el script del layout puso en
                <html> antes de pintar: sin parpadeo al hidratar (antes salía «Modo oscuro» y cambiaba en oscuro). En el
                móvil, el sol o la luna (los mismos dos estados) y la etiqueta queda solo para los lectores de pantalla. */}
            <svg className="theme-ico theme-to-light" viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <circle cx="12" cy="12" r="4" /><path d="M12 2.5v2M12 19.5v2M2.5 12h2M19.5 12h2M5.3 5.3l1.4 1.4M17.3 17.3l1.4 1.4M5.3 18.7l1.4-1.4M17.3 6.7l1.4-1.4" />
            </svg>
            <svg className="theme-ico theme-to-dark" viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2" strokeLinejoin="round">
              <path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5Z" />
            </svg>
            <span className="theme-label theme-to-light">Modo claro</span><span className="theme-label theme-to-dark">Modo oscuro</span>
          </button>
          {symbol && <PdfButton symbol={symbol} />}
        </div>
      </div>
    </header>
  </>);
}
