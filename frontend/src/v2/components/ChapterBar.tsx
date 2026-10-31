"use client";
import { useEffect, useLayoutEffect, useRef } from "react";
import { CHAPTER_ORDER, SECTION_LABELS } from "@/v2/lib/story";
import { chapterHref, type ChapterSlug } from "@/v2/lib/routes";
import { scrollBehavior } from "@/v2/lib/motion";

/** Las nueve secciones del análisis como pestañas (V4b): un enlace a la ruta de cada una, la de la URL como activa. */
export default function ChapterBar({ symbol, current }: { symbol: string; current: ChapterSlug }) {
  const row = useRef<HTMLDivElement>(null);
  // Barra deslizable (móvil, tableta): la sección activa siempre a la vista (E4 Task 3). v4 móvil (PM): si no se ve
  // entera, empieza en el margen (scroll-padding de v2.css, el mismo imán que el resto de filas deslizables). Solo se
  // mueve la barra en horizontal, nunca la página.
  useEffect(() => {
    const r = row.current;
    const a = r?.querySelector<HTMLElement>("a[aria-current=page]");
    if (!r || !a || r.scrollWidth <= r.clientWidth) return;
    const pad = parseFloat(getComputedStyle(r).scrollPaddingLeft) || 0;
    const box = r.getBoundingClientRect(), ar = a.getBoundingClientRect();
    if (ar.left >= box.left + pad && ar.right <= box.right - pad) return;
    r.scrollTo({ left: Math.max(0, r.scrollLeft + ar.left - box.left - pad), behavior: scrollBehavior() });
  }, [current]);
  // v4.1 (movimiento): la marca de la pestaña activa es una sola pieza que se desliza a la nueva (transform, v2.css);
  // se coloca sin transición la primera vez y al cambiar el ancho.
  const ink = useRef<HTMLSpanElement>(null);
  useLayoutEffect(() => {
    const r = row.current, i = ink.current;
    if (!r || !i) return;
    const place = (animate: boolean) => {
      const a = r.querySelector<HTMLElement>("a[aria-current=page]");
      if (!a) return;
      i.dataset.still = animate ? "" : "1";
      i.style.transform = `translateX(${a.offsetLeft}px) scaleX(${a.offsetWidth / 100})`;
    };
    place(i.style.transform !== "");
    const ro = new ResizeObserver(() => place(false));
    ro.observe(r);
    return () => ro.disconnect();
  }, [current]);
  return (
    <nav className="chapterbar" aria-label="Secciones del análisis">
      <div className="wrap chapterbar-grid" ref={row}>
        {CHAPTER_ORDER.map((id) => (
          <a key={id} data-nav href={chapterHref(symbol, id)} aria-current={current === id ? "page" : undefined}>{SECTION_LABELS[id]}</a>
        ))}
        <span className="chapter-ink" ref={ink} aria-hidden="true" />
      </div>
    </nav>
  );
}
