"use client";
import { useEffect, useRef, useState } from "react";
import { stuckHeight } from "@/v2/components/Floating";

/** Distancia bajo la cabecera fija a la que un apartado pasa a ser el activo (las dos barras fijas). */
const ACTIVE_OFFSET_REM = 10;     // bajo las barras fijas (≈ 7.5rem, el scroll-margin de .dsec) y algo de holgura

/** Índice interno de la página en píldoras, fijo bajo la barra de capítulos; la activa es la última sección cuyo
 *  inicio ya pasó bajo las barras (o la última, al llegar al final de la página). */
export default function PillIndex({ items }: { items: Array<{ id: string; label: string }> }) {
  const [active, setActive] = useState(items[0]?.id);
  const raf = useRef(0);
  useEffect(() => {
    const update = () => {
      // V4b: más la cabecera fija, que al bajar queda encima de las barras
      const offset = ACTIVE_OFFSET_REM * parseFloat(getComputedStyle(document.documentElement).fontSize) + stuckHeight();
      const atEnd = window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 2;
      let cur = items[0]?.id;
      for (const i of items) {
        const el = document.getElementById(i.id);
        if (el && el.getBoundingClientRect().top <= offset) cur = i.id;
      }
      setActive(atEnd ? items[items.length - 1]?.id : cur);
    };
    const onScroll = () => { cancelAnimationFrame(raf.current); raf.current = requestAnimationFrame(update); };
    update();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    return () => { window.removeEventListener("scroll", onScroll); window.removeEventListener("resize", onScroll); cancelAnimationFrame(raf.current); };
  }, [items]);
  return (
    <nav className="pillindex" aria-label="En esta página">
      <div className="wrap pillindex-row">
        {items.map((i) => (
          <a key={i.id} href={`#${i.id}`} className="pillnav" aria-current={active === i.id ? "location" : undefined}>{i.label}</a>
        ))}
      </div>
    </nav>
  );
}
