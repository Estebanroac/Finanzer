"use client";
import { useEffect, useRef, useState } from "react";
import { stuckHeight } from "@/v2/components/Floating";
import { scrollBehavior } from "@/v2/lib/motion";

/** Distancia bajo la cabecera fija a la que un apartado pasa a ser el activo (las dos barras fijas). */
const ACTIVE_OFFSET_REM = 10;     // bajo las barras fijas (≈ 7.5rem, el scroll-margin de .dsec) y algo de holgura

/** Índice interno de la página en píldoras, fijo bajo la barra de capítulos; la activa es la última sección cuyo
 *  inicio ya pasó bajo las barras (o la última, al llegar al final de la página). */
export default function PillIndex({ items }: { items: Array<{ id: string; label: string }> }) {
  const [active, setActive] = useState(items[0]?.id);
  const raf = useRef(0);
  // v4.1 (movimiento): al tocar una píldora la página se desliza al apartado (suave; con «reducir movimiento», salto) y
  // la píldora queda activa desde el toque: mientras dura el desplazamiento no se recalcula (no parpadean las de en medio)
  const lock = useRef<ReturnType<typeof setTimeout> | null>(null);
  const jump = (e: React.MouseEvent<HTMLAnchorElement>, id: string) => {
    const el = document.getElementById(id);
    if (!el || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    e.preventDefault();
    window.history.replaceState(window.history.state, "", `#${id}`);
    setActive(id);
    if (lock.current) clearTimeout(lock.current);
    lock.current = setTimeout(() => { lock.current = null; }, 900);
    el.scrollIntoView({ behavior: scrollBehavior(), block: "start" });
  };
  useEffect(() => {
    const update = () => {
      if (lock.current) return;
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
          <a key={i.id} href={`#${i.id}`} className="pillnav" aria-current={active === i.id ? "location" : undefined}
             onClick={(e) => jump(e, i.id)}>{i.label}</a>
        ))}
      </div>
    </nav>
  );
}
