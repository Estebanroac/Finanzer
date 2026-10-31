"use client";
import { useEffect, useRef, useState, type CSSProperties, type ReactNode, type RefObject } from "react";
import { createPortal } from "react-dom";
import { autoUpdate, flip, offset, shift, size, useFloating, type Padding } from "@floating-ui/react-dom";

/**
 * V7 (PM): un solo componente para los paneles que abren los «?», el desglose de las puntuaciones y su «Qué es cada
 * fila». Regla: el panel **nunca ocupa la zona de la barra fija de capítulos**, ni por delante ni por detrás.
 *  - Escritorio y tablet: anclado a su elemento, abajo o arriba según quepa y desplazado en horizontal si hace falta
 *    (floating-ui: flip, shift, size). El área válida es el viewport menos la barra (medida en vivo) y 8 px; si no cabe
 *    entero, toma el alto disponible y se desplaza por dentro. Si el ancla entra bajo la barra (o sale de la pantalla),
 *    se cierra; si sigue visible, se recoloca.
 *  - Móvil (< 768 px): hoja inferior con fondo atenuado, que se cierra también con un gesto hacia abajo; la barra de
 *    arriba sigue visible y despejada (ni la hoja ni el fondo la cubren; si la barra está aún en su sitio y tan abajo
 *    que la hoja quedaría corta, la página se desplaza antes hasta que la barra queda pegada arriba).
 * El panel va en un portal dentro de la raíz de /v2 (`.fz2`, de la que toma estilos y tema).
 * v4 (PM): la cabecera (`head`, con «Cerrar») queda fija y el cuerpo se desplaza por dentro, con la rueda, el dedo o el
 * teclado (si no cabe, el cuerpo es enfocable y tiene nombre); su desplazamiento no mueve la página ni recoloca el panel.
 */
export const SHEET_QUERY = "(max-width: 47.9375em)";
export const GAP = 8;
const OFFSET = 6;
const SWIPE_CLOSE_PX = 80;
/** Medio píxel arriba o abajo (redondeos del navegador): la barra «pegada arriba» está a 1 px o menos del borde, y un
 *  ancla está por encima o por debajo de la barra con ese margen. */
const EDGE_PX = 1;
/** Por debajo de este alto disponible el panel no se enseña (aplastado, sería solo su relleno): se oculta hasta que
 *  vuelva a haber sitio, o se cierra si el ancla deja de verse. */
const MIN_USABLE_PX = 48;
/** La hoja va bajo la barra; si con la barra donde está le quedaría menos de esta fracción de la pantalla, la página
 *  se desplaza antes hasta que la barra queda pegada arriba. */
const SHEET_MIN_FRACTION = 0.6;

export const isSheet = () => typeof window !== "undefined" && typeof window.matchMedia === "function" && window.matchMedia(SHEET_QUERY).matches;

/** Alto de la cabecera fija (V4b): al bajar, queda encima de la barra de secciones, que se pega bajo ella. */
export function stuckHeight(): number {
  const root = document.querySelector<HTMLElement>(".fz2");
  return root ? parseFloat(root.style.getPropertyValue("--stuck-h")) || 0 : 0;
}

/** La barra fija de secciones, si está en pantalla. */
export function barRect(): DOMRect | null {
  const el = document.querySelector<HTMLElement>("nav.chapterbar");
  if (!el) return null;
  const r = el.getBoundingClientRect();
  return r.height > 0 && r.bottom > 0 && r.top < window.innerHeight ? r : null;
}

/** En WebKit (iOS), al desplazar la página el visor visual empieza unos px por debajo del de la ventana, y la hoja (fija,
 *  con su alto en dvh) se coloca en el de la ventana: sin sumar ese desfase subía bajo la barra pegada (V4b, e2e en
 *  iPhone). Como floating-ui, solo en WebKit. */
function webkitVisualTop(): number {
  const webkit = typeof CSS !== "undefined" && CSS.supports?.("-webkit-backdrop-filter", "none");
  return webkit ? (window.visualViewport?.offsetTop ?? 0) : 0;
}

/** Lo que el panel deja libre arriba y abajo para `anchor`: 8 px, más la barra si queda por encima (pegada arriba) o
 *  por debajo del ancla (aún en su sitio, bajo la cabecera). */
export function avoidPadding(anchor: Pick<DOMRect, "top" | "bottom">): { top: number; bottom: number; left: number; right: number } {
  const b = barRect();
  const vh = document.documentElement.clientHeight;
  let top = GAP, bottom = GAP;
  if (b) {
    if (b.bottom <= anchor.top + EDGE_PX) top = b.bottom + GAP;
    else if (b.top >= anchor.bottom - EDGE_PX) bottom = vh - b.top + GAP;
  }
  return { top, bottom, left: GAP, right: GAP };
}

/** ¿El ancla ya no se ve? (bajo la barra pegada arriba, o fuera de la pantalla). */
export function anchorHidden(anchor: Pick<DOMRect, "top" | "bottom">): boolean {
  if (anchor.top === 0 && anchor.bottom === 0) return false;     // sin caja (sin maquetar): no se puede medir
  const b = barRect();
  const vh = document.documentElement.clientHeight;
  const topLimit = b && b.top <= stuckHeight() + EDGE_PX ? b.bottom : 0;
  return anchor.bottom <= topLimit || anchor.top >= vh;
}

type Listener = (id: string, open: boolean) => void;
const listeners = new Set<Listener>();
/** Avisa cuando se abre o se cierra un panel (el desglose de una tarjeta se aparta mientras está abierto un «?» de
 *  dentro). */
export function onPanelOpen(fn: Listener): () => void {
  listeners.add(fn);
  return () => { listeners.delete(fn); };
}

export default function Floating({ anchor, open, onClose, id, className, role, label, modal,
  boxRef, onBackdropDown, sheet: sheetProp, head, children }: {
  anchor: RefObject<HTMLElement | null>; open: boolean; onClose: () => void; id?: string; className: string;
  role: "dialog" | "tooltip"; label?: string; modal?: boolean;
  /** V6b (E4): hoja o panel, decidido por quien lo abre (que bloquea el fondo y atrapa el Tab en la hoja). Sin él, la
   *  media query en cada render: al girar una tableta con el panel abierto, los dos no coincidían. */
  sheet?: boolean;
  boxRef?: (el: HTMLDivElement | null) => void;
  onBackdropDown?: () => void;
  /** Cabecera fija (título y «Cerrar»): siempre a la vista, por largo que sea el cuerpo. */
  head?: ReactNode;
  children: ReactNode;
}) {
  const [target, setTarget] = useState<HTMLElement | null>(null);
  // hoja o panel: al abrir, en el propio render (si se decidiera en un efecto, en el primer render ya abierto sería un
  // panel, y su escucha del scroll lo cerraría al desplazar la página para la hoja)
  const sheet = open && (sheetProp ?? isSheet());
  const [topLimit, setTopLimit] = useState(0);
  const pad = (): Padding => avoidPadding(anchor.current?.getBoundingClientRect() ?? { top: 0, bottom: 0 });
  const body = useRef<HTMLDivElement>(null);
  // el desplazamiento del cuerpo antes de medir el panel entero (sin su alto recortado), para devolverlo después
  const keep = useRef<number | null>(null);
  // ¿el cuerpo no cabe? Entonces es enfocable (se lee y se desplaza con el teclado)
  const [scrolls, setScrolls] = useState(false);
  const { refs, floatingStyles, update } = useFloating({
    open,
    strategy: "fixed",
    placement: "bottom-start",
    middleware: [
      offset(OFFSET),
      flip(() => ({ padding: pad(), fallbackStrategy: "bestFit" })),
      shift(() => ({ padding: pad() })),
      size(() => ({
        padding: pad(),
        apply({ availableHeight, availableWidth, elements }) {
          if (elements.floating.classList.contains("sheet")) return;     // la hoja tiene su propio alto (CSS)
          // sin sitio para la cabecera y algo de cuerpo, no se enseña (un panel sin «Cerrar» a la vista no vale)
          const headH = elements.floating.querySelector<HTMLElement>(".float-head")?.offsetHeight ?? 0;
          Object.assign(elements.floating.style, {
            visibility: availableHeight < headH + MIN_USABLE_PX ? "hidden" : "",
            // si no cabe entero en ningún lado, el alto disponible (y se desplaza por dentro): nunca sobre la barra
            maxHeight: `${Math.max(0, Math.floor(availableHeight))}px`,
            maxWidth: `${Math.floor(availableWidth)}px`,
          });
          if (keep.current !== null && body.current) { body.current.scrollTop = keep.current; keep.current = null; }
        },
      })),
    ],
  });

  // Con scroll (de la página o de cualquier contenedor) o al cambiar el tamaño: si el ancla entra bajo la barra (o sale
  // de la pantalla), se cierra; si no, se recoloca. También cuando cambia el tamaño del ancla o del panel.
  useEffect(() => {
    if (!open || sheet) return;
    const el = anchor.current;
    const tick = (e?: Event) => {
      if (!el) return;
      // v4 (PM): el desplazamiento del propio panel no mueve el ancla; antes lo recolocaba y lo devolvía arriba
      const fl = refs.floating.current;
      if (e?.target instanceof Node && fl?.contains(e.target)) return;
      if (anchorHidden(el.getBoundingClientRect())) { onClose(); return; }
      // sin el alto recortado del cálculo anterior: flip mide el panel entero y elige el lado con sitio (el cuerpo
      // recupera después su desplazamiento)
      if (fl) {
        if (keep.current === null) keep.current = body.current?.scrollTop ?? 0;
        fl.style.maxHeight = "";
      }
      update();
    };
    window.addEventListener("scroll", tick, { capture: true, passive: true });
    window.addEventListener("resize", tick);
    const stop = el && refs.floating.current ? autoUpdate(el, refs.floating.current, () => tick(), { ancestorScroll: false }) : undefined;
    // V4b: la cabecera fija entra o sale un fotograma después del scroll y mueve la barra: se vuelve a colocar
    const root = el?.closest(".fz2");
    const stuck = root ? new MutationObserver(() => tick()) : null;
    if (root) stuck?.observe(root, { attributes: true, attributeFilter: ["data-stuck"] });
    return () => {
      window.removeEventListener("scroll", tick, { capture: true });
      window.removeEventListener("resize", tick);
      stop?.();
      stuck?.disconnect();
    };
  }, [open, sheet, anchor, onClose, update, refs.floating]);

  // portal en la raíz de /v2, desde el montaje: al abrir, el panel sale en el mismo render (quien lo abre puede llevarle
  // el foco en el siguiente fotograma; si el destino se fijara al abrir, el panel llegaría un render después)
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- el destino del portal depende del DOM
    setTarget(anchor.current?.closest<HTMLElement>(".fz2") ?? document.body);
  }, [anchor]);
  // límite superior de la hoja, al abrir
  useEffect(() => {
    if (!open) return;
    const s = sheet;
    let b = barRect();
    const vh = document.documentElement.clientHeight;
    const stuck = stuckHeight();
    let pinned = false;
    if (s && b && b.top > stuck + EDGE_PX && vh - b.bottom < SHEET_MIN_FRACTION * vh) {
      window.scrollBy({ top: b.top - stuck, behavior: "instant" });
      b = barRect();
      pinned = true;            // la cabecera fija entra en el siguiente fotograma y la barra queda bajo ella
    }
    // la hoja y su fondo, bajo la barra (pegada arriba o aún en su sitio): la barra sigue visible y despejada
    // eslint-disable-next-line react-hooks/set-state-in-effect -- la posición de la barra es del DOM
    setTopLimit(s && b ? Math.max(0, (pinned ? stuck + b.height : b.bottom) + webkitVisualTop()) : 0);
  }, [open, sheet]);

  useEffect(() => { if (open) refs.setReference(anchor.current); }, [open, anchor, refs]);
  // si el cuerpo no cabe (en el panel o en la hoja, al abrir y al cambiar de tamaño), es enfocable
  useEffect(() => {
    const b = body.current;
    if (!open || !b) return;
    const check = () => setScrolls(b.scrollHeight > b.clientHeight + EDGE_PX);
    check();
    const ro = typeof ResizeObserver === "undefined" ? null : new ResizeObserver(check);
    ro?.observe(b);
    if (b.firstElementChild) ro?.observe(b.firstElementChild);
    return () => ro?.disconnect();
  }, [open, sheet]);
  useEffect(() => {
    if (!open || !id) return;
    listeners.forEach((fn) => fn(id, true));
    return () => listeners.forEach((fn) => fn(id, false));
  }, [open, id]);

  // hoja inferior: gesto hacia abajo para cerrarla. V6b (E2): solo si la hoja está arriba del todo al tocar; con su
  // contenido desplazado, arrastrar hacia abajo es volver arriba, no cerrar.
  const [dragFrom, setDragFrom] = useState<number | null>(null);

  if (!target || !open) return null;
  const setBox = (el: HTMLDivElement | null) => { refs.setFloating(el); boxRef?.(el); };
  const common = {
    id, role, "aria-label": label, "aria-modal": modal && open ? ("true" as const) : undefined, hidden: !open,
  };
  const inner = (<>
    {head && <div className="float-head">{head}</div>}
    <div ref={body} className="float-body" tabIndex={scrolls ? 0 : undefined} role={scrolls ? "region" : undefined}
         aria-label={scrolls ? `Texto de la ayuda${label ? `: ${label}` : ""}` : undefined}>
      <div className="float-content">{children}</div>
    </div>
  </>);
  if (open && sheet) {
    const style: CSSProperties = { maxHeight: `calc(100dvh - ${topLimit + GAP}px)` };
    return createPortal(<>
      <div className="tip-backdrop" aria-hidden="true" style={{ top: topLimit }}
           onPointerDown={(e) => { e.stopPropagation(); (onBackdropDown ?? onClose)(); }} />
      <div ref={setBox} {...common} className={`${className} sheet`} style={style}
           onTouchStart={(e) => setDragFrom((body.current?.scrollTop ?? 0) <= 0 ? e.touches[0].clientY : null)}
           onTouchMove={(e) => { if (dragFrom !== null && e.touches[0].clientY - dragFrom > SWIPE_CLOSE_PX) { setDragFrom(null); onClose(); } }}
           onTouchEnd={() => setDragFrom(null)}>
        {inner}
      </div>
    </>, target);
  }
  return createPortal(
    <div ref={setBox} {...common} className={`${className} floating`} style={open ? floatingStyles : undefined}>{inner}</div>,
    target);
}
