"use client";
import { useLayoutEffect, useRef, type ReactNode } from "react";
import { tileRows } from "@/v2/lib/tileRows";

/** Fichas de cifras que se rellenan por filas (.tiles.flow). En el móvil van de dos en dos (v2.css) y la cifra nunca se
 *  parte: se mide el ancho propio de cada cifra (sin partir, con su moneda) frente al de media fila y, si no cabe, la
 *  ficha ocupa la fila entera, como las fichas sin cifra (.full); la que se quedaría sola en su fila, también
 *  (tileRows). Vale para cualquier moneda (EUR, GBp, JPY, CHF…) y cifra, y se vuelve a medir al cambiar el ancho o al
 *  llegar la fuente. En pantallas anchas las fichas fluyen (flex) y la regla no se aplica (v2.css). */
export default function FlowTiles({ children }: { children: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);
  useLayoutEffect(() => {
    const grid = ref.current;
    if (!grid) return;
    const fit = () => {
      const tiles = [...grid.querySelectorAll<HTMLElement>(":scope > .tile")];
      const gap = parseFloat(getComputedStyle(grid).columnGap) || 0;
      const half = (grid.clientWidth - gap) / 2;
      const range = document.createRange();
      const wide = tiles.map((t) => {
        if (t.classList.contains("full")) return true;
        const v = t.querySelector<HTMLElement>(".tile-value");
        if (!v) return false;
        const s = getComputedStyle(t);
        const inner = half - parseFloat(s.paddingLeft) - parseFloat(s.paddingRight) - parseFloat(s.borderLeftWidth) - parseFloat(s.borderRightWidth);
        range.selectNodeContents(v);
        return range.getBoundingClientRect().width > inner + 0.5;
      });
      tileRows(wide).forEach((r, i) => { tiles[i].dataset.row = r; });
    };
    fit();
    const ro = new ResizeObserver(fit);
    ro.observe(grid);
    document.fonts?.ready.then(fit);
    return () => ro.disconnect();
  }, [children]);
  return <div ref={ref} className="tiles flow" data-sym-row>{children}</div>;
}
