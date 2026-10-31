"use client";
import { useEffect, useRef } from "react";
import { CHAPTER_ORDER, SECTION_LABELS } from "@/v2/lib/story";
import { chapterHref, type ChapterSlug } from "@/v2/lib/routes";

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
    r.scrollTo({ left: Math.max(0, r.scrollLeft + ar.left - box.left - pad), behavior: "smooth" });
  }, [current]);
  return (
    <nav className="chapterbar" aria-label="Secciones del análisis">
      <div className="wrap chapterbar-grid" ref={row}>
        {CHAPTER_ORDER.map((id) => (
          <a key={id} data-nav href={chapterHref(symbol, id)} aria-current={current === id ? "page" : undefined}>{SECTION_LABELS[id]}</a>
        ))}
      </div>
    </nav>
  );
}
