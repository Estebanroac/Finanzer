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

/** Cambio de pestaña: el contenido nuevo entra con un fundido y un leve desplazamiento desde el lado del cambio (`dir`
 *  1: hacia delante, desde la derecha; -1: hacia atrás). Lo hace el CSS al montarse la sección (v2.css,
 *  html[data-page-dir]); no se usa la View Transitions API aquí: retiene el siguiente fotograma para capturar la vista
 *  y eso sumaba 16–24 ms a la respuesta del toque (INP). Con «reducir movimiento», el cambio es inmediato. */
let endPage: (() => void) | undefined;
/** Si la sección tarda en montarse (su fragmento aún llega), la marca espera a que entre; como mucho, esto. */
const PAGE_MARK_MAX_MS = 1_000;
export function pageTransition(update: () => void, dir: 1 | -1 = 1) {
  if (reducedMotion()) { update(); return; }
  const root = document.documentElement;
  endPage?.();
  root.dataset.pageDir = dir > 0 ? "fwd" : "back";
  const done = (e?: AnimationEvent) => { if (!e || e.animationName === "fz2-page-in") endPage?.(); };
  const timer = setTimeout(done, PAGE_MARK_MAX_MS);
  endPage = () => { delete root.dataset.pageDir; clearTimeout(timer); document.removeEventListener("animationend", done); endPage = undefined; };
  document.addEventListener("animationend", done);
  update();
}

/** Fundido cruzado de toda la vista: la pantalla de carga que da paso a la página (lo nuevo sube unos px) o el cambio
 *  de modo claro/oscuro (`theme`: solo color, sin desplazamiento; v2.css html[data-vt="theme"]). Sin pasar por un
 *  fondo vacío; con «reducir movimiento» o sin la API, el cambio es inmediato. */
export function crossfade(update: () => void, kind: "page" | "theme" = "page") {
  if (!canTransition()) { update(); return; }
  run(update, (on) => { if (on) document.documentElement.dataset.vt = kind; else delete document.documentElement.dataset.vt; });
}
