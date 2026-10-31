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
 *  arrastra 1:1. Al tocar, parado; al soltar tras arrastrar, sigue la inercia del dedo hasta la tarjeta más cercana al
 *  punto proyectado (muelle sin rebote, el imán solo ahí) y arranca TOUCH_RESUME_MS después, desde donde esté. Sin
 *  imán mientras avanza solo.
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
/** Pantallas táctiles: tras soltar (y llegar a su tarjeta), arranca pasado este tiempo; el arrastre empieza al pasar
 *  TOUCH_DRAG_PX (antes, un toque es un toque). */
export const TOUCH_RESUME_MS = 2500;
const TOUCH_DRAG_PX = 10;
/** Muelle hacia la tarjeta (Apple, «mover / reubicar»: amortiguamiento 1, respuesta 0,4 s) y deceleración con la que se
 *  proyecta dónde acabaría el gesto (la del desplazamiento normal); se da por llegado a menos de SETTLE_PX y SETTLE_PX_S. */
const SPRING_RESPONSE_S = 0.4;
const DECELERATION = 0.998;
const SETTLE_PX = 0.5;
const SETTLE_PX_S = 5;
const SPRING_STEP_MS = 4;
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
    sampleX: 0, sampleT: 0, suppressClick: false, pointerId: -1, spring: null as null | { target: number; v: number } });

  // Lista o periodo nuevos: al principio.
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    s.current.pos = 0;
    s.current.velocity = 0;
    s.current.spring = null;
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
    /** El principio de cada tarjeta en la pista (la posición que la deja en el margen); las de la copia, por el bucle. */
    const starts = () => {
      const left = track?.getBoundingClientRect().left ?? 0;
      return [...el.querySelectorAll<HTMLElement>(".run:first-child .tk-cell")].map((c) => c.getBoundingClientRect().left - left);
    };
    /** Tras soltar: hacia la tarjeta más cercana a donde llevaría la inercia, con la velocidad del dedo (px/ms). */
    const settle = (velocity: number) => {
      const vs = velocity * MS_PER_S;
      const projected = st.pos + (vs / MS_PER_S) * DECELERATION / (1 - DECELERATION);
      const w = runWidth();
      let target = projected, best = Infinity;
      for (const x of starts()) {
        const near = loop && w > 0 ? x + w * Math.round((projected - x) / w) : x;   // la vuelta más cercana del bucle
        if (Math.abs(near - projected) < best) { best = Math.abs(near - projected); target = near; }
      }
      st.spring = { target, v: vs };
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
    const onTouchStart = () => { st.touching = true; st.velocity = 0; st.spring = null; };   // el dedo manda
    const onTouchEnd = () => { st.touching = false; after(SCROLL_QUIET_MS); };

    // Arrastre con el ratón: la captura del puntero empieza al pasar DRAG_PX (antes, un clic es un clic).
    // Con el dedo (pantallas táctiles), igual: arrastre 1:1 desde donde se cogió.
    const onDown = (e: PointerEvent) => {
      if (e.pointerType === "mouse" ? e.button !== 0 : !tx) return;
      Object.assign(st, { down: true, dragged: false, startX: e.clientX, startPos: st.pos, sampleX: e.clientX,
        sampleT: now(), velocity: 0, pointerId: e.pointerId, spring: null });
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
      if (tx && e.pointerType !== "mouse") {     // el dedo: a su tarjeta y, pasado TOUCH_RESUME_MS, en marcha
        if (st.dragged) {
          st.suppressClick = true;
          if (el.hasPointerCapture(e.pointerId)) el.releasePointerCapture(e.pointerId);
          settle(now() - st.sampleT > STILL_MS ? 0 : st.velocity);
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
      if (st.spring && !st.down) {                             // el dedo soltó: muelle hasta su tarjeta
        const sp = st.spring;
        const w0 = 2 * Math.PI / SPRING_RESPONSE_S;            // amortiguamiento 1: sin rebote
        let x = st.pos;
        const n = Math.max(1, Math.ceil(dt / SPRING_STEP_MS)), h = dt / MS_PER_S / n;
        for (let i = 0; i < n; i++) { sp.v += (-w0 * w0 * (x - sp.target) - 2 * w0 * sp.v) * h; x += sp.v * h; }
        sp.target += set(x);
        if (Math.abs(st.pos - sp.target) < SETTLE_PX && Math.abs(sp.v) < SETTLE_PX_S) {
          set(sp.target);
          st.spring = null;
          after(TOUCH_RESUME_MS);
        }
      }
      const moving = !reduced && itemCount > 0 && !held && !st.down && !st.touching && st.velocity === 0 && !st.spring
        && t >= st.resumeAt;
      if (moving && loop) {                                    // avance automático, desde donde esté
        const w = runWidth();
        if (w > 0) set(st.pos + (w / (itemCount * secondsPerItem * MS_PER_S)) * dt);
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
