import { flushSync } from "react-dom";

/** v4.1 (movimiento; el usuario: «suave, sutil, sensación de iPhone; que no todo sea de golpe»). Un solo lenguaje de
 *  movimiento: los tiempos y curvas viven como tokens en v2.css (:root, --ease-*, --dur-*); aquí, lo que necesita JS. */

const REDUCED = "(prefers-reduced-motion: reduce)";
export const reducedMotion = () => typeof window !== "undefined" && typeof window.matchMedia === "function" && window.matchMedia(REDUCED).matches;
/** Comportamiento de un desplazamiento programado: suave salvo con «reducir movimiento». */
export const scrollBehavior = (): ScrollBehavior => (reducedMotion() ? "auto" : "smooth");

type VT = { finished: Promise<void>; skipTransition: () => void };
type VTDoc = Document & { startViewTransition?: (cb: () => void) => VT };
/** La transición en curso: si llega otro cambio (tocar otra pestaña enseguida), la anterior se da por terminada. */
let current: VT | null = null;
function run(update: () => void, mark: (on: boolean) => void) {
  current?.skipTransition();
  mark(true);
  const vt = (document as VTDoc).startViewTransition!(() => flushSync(update));
  current = vt;
  vt.finished.finally(() => { if (current === vt) { current = null; mark(false); } });
}
/** ¿Hay transiciones de vista (y se quieren)? Sin ellas, los cambios son inmediatos o los hace el CSS. */
export const canTransition = () => !reducedMotion() && typeof (document as VTDoc).startViewTransition === "function";

/** Cambio de pestaña, como en iOS: la vista nunca salta a la vista. v4.1 (el usuario, en su iPhone: «me salta un
 *  latigazo… todo como que se tira de golpe»): la sección nueva entraba a la vez que la página saltaba cientos de px al
 *  principio de la sección (o a donde se leía). Ahora:
 *   1. lo que se va a mover se funde (OUT_MS): solo la sección si la barra ya está pegada arriba (no se moverá); toda la
 *      página bajo la barra superior si aún no lo está (la barra va a subir);
 *   2. con eso invisible, el contenido cambia (`update`) y la vista se coloca sin animar (`place`, que dice cuándo ha
 *      terminado: una vuelta a donde se leía puede esperar a que crezca la sección), con el alto del contenedor fijado
 *      para que el documento no encoja por el camino;
 *   3. vuelve a verse: la sección entra con un fundido y unos px desde el lado del cambio (`dir`).
 *  Nunca queda oculta más de MAX_HIDDEN_MS: nada retrasa la lectura. `now`: el contenido ya cambió (atrás/adelante del
 *  navegador): se oculta sin fundido y se sigue igual. Con «reducir movimiento», cambio y colocación inmediatos. */
const OUT_MS = 100;
const MAX_HIDDEN_MS = 400;
let endPage: (() => void) | undefined;
/** Un cambio aún oculto, sin aplicar: si llega otro toque antes, se descarta y manda el último. */
let pendingSwap: ReturnType<typeof setTimeout> | undefined;
/** Si la sección tarda en montarse (su fragmento aún llega), la marca de entrada espera a que entre; como mucho, esto. */
const PAGE_MARK_MAX_MS = 1_000;
export function switchSection(update: () => void, place: () => Promise<void>, dir: 1 | -1 = 1, now = false) {
  if (reducedMotion()) { update(); requestAnimationFrame(() => { void place(); }); return; }
  const root = document.documentElement;
  const main = document.querySelector<HTMLElement>(".fz2 main");
  clearTimeout(pendingSwap);
  endPage?.();
  root.dataset.leave = document.querySelector(".fz2[data-stuck]") ? "depth" : "main";
  if (now) root.dataset.leaveNow = "";
  let gone = false;
  const show = () => {
    if (gone) return;
    gone = true;
    delete root.dataset.leaveNow;
    root.dataset.pageDir = dir > 0 ? "fwd" : "back";
    delete root.dataset.leave;                     // vuelve a verse: fundido (main) y entrada de la sección (.depth)
    const done = (e?: AnimationEvent) => { if (!e || e.animationName === "fz2-page-in") endPage?.(); };
    const timer = setTimeout(done, PAGE_MARK_MAX_MS);
    endPage = () => {
      delete root.dataset.pageDir; delete root.dataset.leave; delete root.dataset.leaveNow;
      if (main) main.style.minHeight = "";
      clearTimeout(timer); clearTimeout(cap); document.removeEventListener("animationend", done); endPage = undefined;
    };
    document.addEventListener("animationend", done);
  };
  const cap = setTimeout(show, (now ? 0 : OUT_MS) + MAX_HIDDEN_MS);
  endPage = () => { clearTimeout(cap); gone = true; endPage = undefined; };   // otro toque antes de volver a verse: manda ese
  const swap = () => {
    if (main) main.style.minHeight = `${main.offsetHeight}px`;   // el documento no encoge mientras cambia
    update();
    requestAnimationFrame(() => { place().finally(() => requestAnimationFrame(show)); });   // con la sección ya pintada
  };
  if (now) swap(); else pendingSwap = setTimeout(swap, OUT_MS);
}

/** Fundido cruzado de toda la vista: la pantalla de carga que da paso a la página (lo nuevo sube unos px) o el cambio
 *  de modo claro/oscuro (`theme`: solo color, sin desplazamiento; v2.css html[data-vt="theme"]). Sin pasar por un
 *  fondo vacío; con «reducir movimiento» o sin la API, el cambio es inmediato. */
export function crossfade(update: () => void, kind: "page" | "theme" = "page") {
  if (!canTransition()) { update(); return; }
  run(update, (on) => { if (on) document.documentElement.dataset.vt = kind; else delete document.documentElement.dataset.vt; });
}
