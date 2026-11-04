import { useEffect, useRef, useState, type RefObject } from "react";

/** P8b: el cintillo es un contenedor desplazable de verdad (overflow-x: auto, sin barra), así que el trackpad con dos
 *  dedos (deltaX), el dedo en móvil y las flechas del teclado lo mueven de forma nativa, sin secuestrar la rueda
 *  vertical de la página. Su `scrollLeft` avanza solo con requestAnimationFrame y en bucle: el contenido va duplicado
 *  y la posición se mantiene en [0, ancho de una copia].
 *
 *  Cuándo avanza solo (V4b, el usuario: «que arranque apenas quito el mouse»; un solo estado con temporizador,
 *  `resumeAt`, que cada gesto reprograma; nada de flags que puedan quedarse puestos):
 *  - ratón encima: parado (se lee en vivo, `:hover`, solo en dispositivos con ratón); al sacarlo, arranca en el acto
 *    (LEAVE_MS = 0);
 *  - tras arrastrar: arranca al terminar la inercia, sin espera extra;
 *  - tras desplazar con la rueda horizontal, el trackpad o el dedo: arranca al terminar el desplazamiento nativo (su
 *    inercia incluida): `scrollend` donde existe y, si no (Safari), SCROLL_QUIET_MS sin eventos de scroll; con el dedo
 *    apoyado, parado;
 *  - foco de teclado dentro (`:focus-visible`, en vivo): parado; al salir, en el acto. El foco que deja un clic del
 *    ratón en una tarjeta no cuenta;
 *  - con «reducir movimiento»: nunca solo, y sin inercia (y sin copia: el componente no la pinta).
 *  Al reanudar sigue desde donde esté, sin saltos. Arrastre con el ratón (pointer events) con inercia suave; si se
 *  arrastró más de DRAG_PX, el clic se cancela (no abre la tarjeta al soltar).
 *
 *  v4 cintillo (el usuario en el iPhone: «no se mueve solo… se desplaza por secciones, por acción, y no de manera
 *  continua como en la página»): en pantallas táctiles (sin ratón) también avanza en continuo y al mismo ritmo por
 *  tarjeta, pero con `transform` sobre la pista (la GPU, sin tirones en Safari iOS) en vez de `scrollLeft`; el
 *  contenedor no se desplaza de forma nativa (`touch-action: pan-y`: lo vertical sigue moviendo la página) y el dedo lo
 *  arrastra 1:1. Al tocar, parado.
 *
 *  v4.1 (el usuario: «pasa como a un lugar en el que deba estar… quiero algo que se mueva sin restricciones»): al soltar
 *  el dedo no hay imán ni tarjeta destino. Soltado en reposo, se queda exactamente donde quedó; con velocidad, sigue
 *  con inercia libre que decae como el desplazamiento nativo de iOS (DECELERATION por ms, la de UIScrollView normal) y
 *  para donde pare. Arranca TOUCH_RESUME_MS después, desde donde esté. Nunca hay imán.
 *
 *  Pestaña oculta o cintillo fuera de la vista (IntersectionObserver): sin bucle de fotogramas, y al volver sigue
 *  desde donde estaba (sin saltar lo que habría avanzado). */
export type CarouselMode = "animado" | "pausado" | "reducido";

/** V4b: al sacar el ratón o el foco, sin espera. */
export const LEAVE_MS = 0;
/** Fin del desplazamiento nativo sin `scrollend` (Safari): tanto tiempo sin eventos de scroll (la inercia del trackpad
 *  manda uno por fotograma mientras dura). */
export const SCROLL_QUIET_MS = 120;
const DRAG_PX = 5;
const MS_PER_S = 1000;
/** Pantallas táctiles: tras soltar (y acabar su inercia), arranca pasado este tiempo; el arrastre empieza al pasar
 *  TOUCH_DRAG_PX (antes, un toque es un toque). */
export const TOUCH_RESUME_MS = 2500;
const TOUCH_DRAG_PX = 10;
/** Inercia del dedo: fracción de la velocidad que queda cada ms (la de UIScrollView, deceleración normal). */
const DECELERATION = 0.998;
/** v4.1 (movimiento): al reanudar, el avance llega a su velocidad en este tiempo (curva suave), en vez de arrancar de
 *  golpe; al pararse (dedo, ratón, foco) se para al instante: lo que se toca responde ya. */
const RAMP_MS = 400;
/** Inercia: fracción de la velocidad que queda en cada fotograma de ~16 ms, la velocidad (px/ms) a la que se para y
 *  su tope (los eventos muy seguidos darían velocidades absurdas). */
const FRICTION = 0.94;
const FRAME_MS = 16;
const STOP_PX_MS = 0.02;
const MAX_PX_MS = 2.5;
/** La velocidad del arrastre se mide sobre muestras separadas al menos esto (ms); si el gesto se detuvo más de
 *  STILL_MS antes de soltar, no hay inercia. */
const SAMPLE_MS = 12;
const STILL_MS = 64;
/** Diferencia entre el `scrollLeft` puesto y el leído que se sigue tomando por propia (redondeo a píxeles). */
const OWN_SCROLL_PX = 2;

export function useCarousel(ref: RefObject<HTMLDivElement | null>, opts: {
  reduced: boolean; secondsPerItem: number; itemCount: number; resetKey: string;
}): { mode: CarouselMode; dragging: boolean } {
  const { reduced, secondsPerItem, itemCount, resetKey } = opts;
  const [mode, setMode] = useState<CarouselMode>(reduced ? "reducido" : "animado");
  const [dragging, setDragging] = useState(false);
  const s = useRef({ pos: 0, lastSet: -1, resumeAt: 0, velocity: 0, down: false, touching: false, dragged: false, startX: 0, startPos: 0,
    sampleX: 0, sampleT: 0, suppressClick: false, pointerId: -1, glide: 0 });

  // Lista o periodo nuevos: al principio.
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    s.current.pos = 0;
    s.current.velocity = 0;
    s.current.glide = 0;
    el.scrollLeft = 0;
    s.current.lastSet = el.scrollLeft;
    el.querySelector<HTMLElement>(".track")?.style.removeProperty("transform");
  }, [ref, resetKey]);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const st = s.current;
    const loop = !reduced;
    const now = () => performance.now();
    const mouse = typeof window.matchMedia === "function" && window.matchMedia("(hover: hover) and (pointer: fine)").matches;
    const runWidth = () => (el.querySelector<HTMLElement>(".run")?.offsetWidth ?? 0);
    /** Cada gesto reprograma la reanudación (nunca la adelanta). */
    const after = (ms: number) => { st.resumeAt = Math.max(st.resumeAt, now() + ms); };
    const hovered = () => mouse && el.matches(":hover");
    const keyboardFocus = () => {
      const a = document.activeElement;
      return !!a && el.contains(a) && a.matches(":focus-visible");
    };
    // en pantallas táctiles, transform sobre la pista (GPU) y arrastre propio; con ratón, el scrollLeft nativo
    const tx = !mouse && !reduced;
    const track = el.querySelector<HTMLElement>(".track");
    /** Pone la posición (en bucle) y devuelve cuánto la ha movido el bucle. */
    const set = (pos: number) => {
      const raw = pos;
      const w = runWidth();
      if (loop && w > 0) {   // bucle en [0, w]: w (el principio de la copia) se ve igual que 0 y deja seguir hacia atrás
        while (pos > w) pos -= w;
        while (pos < 0) pos += w;
      }
      st.pos = pos;
      if (tx && track) track.style.transform = `translate3d(${-pos}px, 0, 0)`;
      else {
        el.scrollLeft = pos;
        st.lastSet = el.scrollLeft;
      }
      return pos - raw;
    };

    // Desplazamiento nativo (trackpad, dedo, flechas, rueda horizontal): se adopta como posición y es un gesto.
    const onScroll = () => {
      if (tx) {                                   // solo el foco lo desplaza (scrollIntoView): pasa a la pista
        const d = el.scrollLeft;
        if (d !== 0) { el.scrollLeft = 0; set(st.pos + d); }
        return;
      }
      if (Math.abs(el.scrollLeft - st.lastSet) <= OWN_SCROLL_PX) return;
      after(SCROLL_QUIET_MS);                     // mientras llegan eventos, se aplaza; al parar, arranca
      st.velocity = 0;
      const w = runWidth();
      if (loop && w > 0 && el.scrollLeft <= 0) set(w);           // hacia atrás desde el principio: a la copia
      else if (loop && w > 0 && el.scrollLeft > w) set(el.scrollLeft);
      else { st.pos = el.scrollLeft; st.lastSet = el.scrollLeft; }
    };
    const onWheel = (e: WheelEvent) => { if (Math.abs(e.deltaX) > Math.abs(e.deltaY)) { after(SCROLL_QUIET_MS); st.velocity = 0; } };
    // El fin del desplazamiento nativo: arranca ya (el navegador lo sabe mejor que la espera de respaldo).
    const onScrollEnd = () => { if (!st.touching) st.resumeAt = Math.min(st.resumeAt, now()); };
    const onTouchStart = () => { st.touching = true; st.velocity = 0; st.glide = 0; };   // el dedo manda (y para la inercia)
    const onTouchEnd = () => { st.touching = false; after(SCROLL_QUIET_MS); };

    // Arrastre con el ratón: la captura del puntero empieza al pasar DRAG_PX (antes, un clic es un clic).
    // Con el dedo (pantallas táctiles), igual: arrastre 1:1 desde donde se cogió.
    const onDown = (e: PointerEvent) => {
      if (e.pointerType === "mouse" ? e.button !== 0 : !tx) return;
      Object.assign(st, { down: true, dragged: false, startX: e.clientX, startPos: st.pos, sampleX: e.clientX,
        sampleT: now(), velocity: 0, pointerId: e.pointerId, glide: 0 });
    };
    const onMove = (e: PointerEvent) => {
      if (!st.down || e.pointerId !== st.pointerId) return;
      const dx = e.clientX - st.startX;
      if (!st.dragged && Math.abs(dx) > (e.pointerType === "mouse" ? DRAG_PX : TOUCH_DRAG_PX)) {
        st.dragged = true;
        Object.assign(st, { startX: e.clientX, sampleX: e.clientX, sampleT: now() });   // sin salto: desde aquí
        try { el.setPointerCapture(e.pointerId); } catch { /* puntero ya suelto */ }
        setDragging(true);
        return;
      }
      if (!st.dragged) return;
      const t = now();
      if (t - st.sampleT >= SAMPLE_MS) {
        const v = (st.sampleX - e.clientX) / (t - st.sampleT);
        st.velocity = Math.max(-MAX_PX_MS, Math.min(MAX_PX_MS, v));
        st.sampleX = e.clientX;
        st.sampleT = t;
      }
      set(st.startPos - dx);
    };
    const end = (e: PointerEvent) => {
      if (!st.down || e.pointerId !== st.pointerId) return;
      st.down = false;
      if (tx && e.pointerType !== "mouse") {     // el dedo: donde quede (con su inercia) y, pasado TOUCH_RESUME_MS, en marcha
        if (st.dragged) {
          st.suppressClick = true;
          if (el.hasPointerCapture(e.pointerId)) el.releasePointerCapture(e.pointerId);
          st.glide = now() - st.sampleT > STILL_MS ? 0 : st.velocity;   // soltado en reposo: ni un píxel más
          setDragging(false);
        }
        st.velocity = 0;
        after(TOUCH_RESUME_MS);
        return;
      }
      if (st.dragged) {
        st.suppressClick = true;                 // el clic que llega al soltar no abre la tarjeta
        if (el.hasPointerCapture(e.pointerId)) el.releasePointerCapture(e.pointerId);
        // sin inercia si el gesto se detuvo antes de soltar o con «reducir movimiento»
        if (reduced || now() - st.sampleT > STILL_MS) st.velocity = 0;
        setDragging(false);
      } else st.velocity = 0;
      if (st.velocity === 0) st.resumeAt = now();     // sin inercia: arranca ya (con ella, al terminar)
    };
    const onClick = (e: MouseEvent) => {
      if (!st.suppressClick) return;
      st.suppressClick = false;
      e.preventDefault();
      e.stopPropagation();
    };
    const onDragStart = (e: DragEvent) => e.preventDefault();     // el enlace no se arrastra como enlace

    el.addEventListener("scroll", onScroll, { passive: true });
    el.addEventListener("wheel", onWheel, { passive: true });
    el.addEventListener("scrollend", onScrollEnd);
    el.addEventListener("touchstart", onTouchStart, { passive: true });
    el.addEventListener("touchend", onTouchEnd, { passive: true });
    el.addEventListener("touchcancel", onTouchEnd, { passive: true });
    el.addEventListener("pointerdown", onDown);
    el.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", end);          // también si se suelta fuera del cintillo
    window.addEventListener("pointercancel", end);
    el.addEventListener("click", onClick, true);
    el.addEventListener("dragstart", onDragStart);

    const detach = () => {
      el.removeEventListener("scroll", onScroll);
      el.removeEventListener("wheel", onWheel);
      el.removeEventListener("scrollend", onScrollEnd);
      el.removeEventListener("touchstart", onTouchStart);
      el.removeEventListener("touchend", onTouchEnd);
      el.removeEventListener("touchcancel", onTouchEnd);
      el.removeEventListener("pointerdown", onDown);
      el.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", end);
      window.removeEventListener("pointercancel", end);
      el.removeEventListener("click", onClick, true);
      el.removeEventListener("dragstart", onDragStart);
    };
    if (reduced) return detach;    // V6b: sin avance ni inercia, el bucle de fotogramas no hace falta
    let raf = 0;
    let prev = now();
    let shown: CarouselMode | null = null;
    let wasHeld = false;
    const show = (m: CarouselMode) => { if (m !== shown) { shown = m; setMode(m); } };
    // Fuera de la vista o con la pestaña oculta, sin fotogramas (batería); al volver, desde donde estaba.
    let onScreen = true;
    const active = () => onScreen && !document.hidden;
    const wake = () => { if (active() && !raf) { prev = now(); raf = requestAnimationFrame(frame); } };
    const io = typeof IntersectionObserver === "function"
      ? new IntersectionObserver(([e]) => { onScreen = e.isIntersecting; wake(); }) : null;
    io?.observe(el);
    document.addEventListener("visibilitychange", wake);
    let ramp = 0;
    const frame = () => {
      if (!active()) { raf = 0; show("pausado"); return; }
      const t = now();
      const dt = t - prev;
      prev = t;
      // Estado en vivo: ratón encima o foco de teclado dentro. Al dejar de estarlo, arranca (LEAVE_MS).
      const held = hovered() || keyboardFocus();
      if (wasHeld && !held) after(LEAVE_MS);
      wasHeld = held;
      if (!st.down && st.velocity !== 0) {                    // inercia tras soltar
        set(st.pos + st.velocity * dt);
        st.velocity *= Math.pow(FRICTION, dt / FRAME_MS);
        if (Math.abs(st.velocity) < STOP_PX_MS) st.velocity = 0;        // fin de la inercia: arranca ya
      }
      if (st.glide !== 0 && !st.down) {                        // el dedo soltó con velocidad: inercia libre, sin destino
        const k = Math.pow(DECELERATION, dt);
        set(st.pos + st.glide * (1 - k) / -Math.log(DECELERATION));   // lo que recorre en dt decayendo (exacto)
        st.glide *= k;
        if (Math.abs(st.glide) < STOP_PX_MS) { st.glide = 0; after(TOUCH_RESUME_MS); }
      }
      const moving = !reduced && itemCount > 0 && !held && !st.down && !st.touching && st.velocity === 0 && st.glide === 0
        && t >= st.resumeAt;
      ramp = moving ? Math.min(1, ramp + dt / RAMP_MS) : 0;
      if (moving && loop) {                                    // avance automático, desde donde esté
        const w = runWidth();
        const ease = ramp * ramp * (3 - 2 * ramp);             // arranque suave (smoothstep)
        if (w > 0) set(st.pos + (w / (itemCount * secondsPerItem * MS_PER_S)) * ease * dt);
      }
      show(reduced ? "reducido" : moving ? "animado" : "pausado");
      raf = requestAnimationFrame(frame);
    };
    raf = requestAnimationFrame(frame);
    return () => {
      cancelAnimationFrame(raf);
      io?.disconnect();
      document.removeEventListener("visibilitychange", wake);
      if (track) track.style.removeProperty("transform");
      detach();
    };
  }, [ref, reduced, secondsPerItem, itemCount]);

  return { mode: reduced ? "reducido" : mode, dragging };
}
