"use client";
import { useLayoutEffect, useRef } from "react";

/** v4.1 (movimiento): el fondo de la opción activa de un control segmentado (el periodo de la portada) es una sola
 *  pieza que se desliza a la nueva, como en iOS: una capa del ancho del control recortada a la forma del botón activo
 *  (clip-path con sus esquinas redondas; escalarla deformaría la píldora). Se coloca bajo el botón con `.on` de su
 *  padre; la primera vez y al cambiar el ancho, sin transición. `active` solo dispara el cambio. */
export default function SegmentInk({ active }: { active: string }) {
  const ink = useRef<HTMLSpanElement>(null);
  useLayoutEffect(() => {
    const i = ink.current, row = i?.parentElement;
    if (!i || !row) return;
    const place = (animate: boolean) => {
      const b = row.querySelector<HTMLElement>(":scope > button.on");
      if (!b) { i.style.opacity = "0"; return; }
      i.dataset.still = animate ? "" : "1";
      i.style.opacity = "";
      const r = row.clientWidth - b.offsetLeft - b.offsetWidth, btm = row.clientHeight - b.offsetTop - b.offsetHeight;
      i.style.clipPath = `inset(${b.offsetTop}px ${r}px ${btm}px ${b.offsetLeft}px round 999px)`;
    };
    place(i.style.clipPath !== "");
    const ro = new ResizeObserver(() => place(false));
    ro.observe(row);
    return () => ro.disconnect();
  }, [active]);
  return <span className="seg-ink" ref={ink} aria-hidden="true" />;
}
