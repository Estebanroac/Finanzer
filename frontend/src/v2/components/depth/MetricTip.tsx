"use client";
import { useCallback, useEffect, useId, useRef, useState, type ReactNode } from "react";
import type { MetricBands, Tone } from "@/lib/api";
import { definitionFor } from "@/lib/tooltips";
import { definitionKey } from "@/v2/lib/terms";
import { toVTone } from "@/v2/lib/tone";
import Floating, { isSheet, onPanelOpen } from "../Floating";

/**
 * "?" de una métrica: qué mide, fórmula, rangos de referencia del motor (display.tooltips) con la banda de la empresa
 * resaltada como "Tu valor" y la nota. La banda la marca la lectura del motor (`reading` = etiqueta de la banda): el
 * cliente no compara números. Escritorio: panel junto al botón; móvil: hoja inferior con foco atrapado. La colocación
 * (fuera de la barra fija de capítulos) es la de `Floating` (V7).
 */
export default function MetricTip({ metricKey, label, value, reading, bands }: {
  metricKey: string; label: string; value?: string | null; reading?: string | null; bands?: MetricBands;
}) {
  const [open, setOpen] = useState(false);
  const [sheet, setSheet] = useState(false);
  const btn = useRef<HTMLButtonElement>(null);
  const box = useRef<HTMLDivElement | null>(null);
  const id = useId();
  const def = definitionFor(definitionKey(metricKey, label), label);
  // Cerrado por Floating. Panel (el «?» entró bajo la barra o salió de la pantalla): el foco no se queda en un botón que
  // desaparece sin avisar (el navegador no da blur al quitarlo, y la tarjeta que lo contiene creería tenerlo). Hoja
  // (gesto hacia abajo, V6b E3): el foco vuelve al «?», como al cerrarla de cualquier otra forma.
  const close = useCallback(() => {
    if (sheet) btn.current?.focus({ preventScroll: true });
    else if (box.current?.contains(document.activeElement)) (document.activeElement as HTMLElement).blur();
    setOpen(false);
  }, [sheet]);
  // V6b (E1): un solo «?» abierto a la vez: si se abre otro, este se cierra (el desglose de una tarjeta no cuenta)
  useEffect(() => onPanelOpen((other, isOpen) => {
    if (isOpen && other !== id && document.getElementById(other)?.classList.contains("tip-box")) setOpen(false);
  }), [id]);

  // Revisión V6 (F8): la hoja inferior (móvil) es modal: atrapa Tab, bloquea el desplazamiento del fondo y, al cerrarse
  // tocando fuera, devuelve el foco al «?». El panel de escritorio no atrapa Tab (se sigue tabulando por la página).
  useEffect(() => {
    if (!open) return;
    // V6b (E1): Escape y Tab solo con el foco en el panel o en su «?» (con el foco en otro sitio, no son suyos)
    const mine = () => !!box.current?.contains(document.activeElement) || document.activeElement === btn.current;
    const onKey = (e: KeyboardEvent) => {
      if (!mine()) return;
      if (e.key === "Escape") { e.preventDefault(); setOpen(false); btn.current?.focus(); return; }
      if (e.key !== "Tab" || !box.current || !box.current.contains(document.activeElement)) return;
      const f = box.current.querySelectorAll<HTMLElement>("button, a[href], [tabindex='0']");      // v4: y el cuerpo, si se desplaza
      if (!f.length) return;
      const first = f[0], last = f[f.length - 1];
      const edge = (e.shiftKey && document.activeElement === first) || (!e.shiftKey && document.activeElement === last);
      if (!edge) return;
      e.preventDefault();
      if (sheet) (e.shiftKey ? last : first).focus();                        // hoja: Tab atrapado
      else { setOpen(false); btn.current?.focus(); }                          // panel: se cierra y el foco vuelve al «?»
    };
    // V6b (E1): el panel (no la hoja) se cierra cuando el foco se va a otro sitio que no es él ni su «?»
    const onFocusOut = (e: FocusEvent) => {
      const to = e.relatedTarget as Node | null;
      if (sheet || !to || box.current?.contains(to) || btn.current?.contains(to)) return;
      setOpen(false);
    };
    const onDown = (e: PointerEvent) => {
      if (box.current && !box.current.contains(e.target as Node) && !btn.current?.contains(e.target as Node)) {
        setOpen(false);
        if (sheet) btn.current?.focus({ preventScroll: true });
      }
    };
    const root = document.documentElement, overflow = root.style.overflow;
    if (sheet) root.style.overflow = "hidden";
    // en captura y en window: el «?» de una tarjeta (TipHost) no deja subir las teclas, y el panel va en un portal
    window.addEventListener("keydown", onKey, true);
    document.addEventListener("pointerdown", onDown);
    const panel = box.current, own = btn.current;
    panel?.addEventListener("focusout", onFocusOut);
    own?.addEventListener("focusout", onFocusOut);
    // el foco entra ya (el panel está montado en este mismo render: el portal tiene destino desde el montaje); antes iba en
    // el fotograma siguiente y una tecla Tab pulsada enseguida salía de la hoja
    const first = box.current?.querySelector<HTMLElement>("button");
    if (first) first.focus({ preventScroll: true });
    else requestAnimationFrame(() => box.current?.querySelector<HTMLElement>("button")?.focus({ preventScroll: true }));
    return () => {
      window.removeEventListener("keydown", onKey, true); document.removeEventListener("pointerdown", onDown);
      panel?.removeEventListener("focusout", onFocusOut); own?.removeEventListener("focusout", onFocusOut);
      if (sheet) root.style.overflow = overflow;
    };
  }, [open, sheet]);

  const closeAndFocus = () => { setOpen(false); btn.current?.focus(); };
  return (
    <span className="tip">
      <button ref={btn} type="button" className="tip-btn" data-tip={metricKey} aria-label={`Qué es ${label}`} aria-expanded={open}
              aria-controls={open ? id : undefined} onClick={() => {
                setSheet(isSheet());      // hoja inferior en móvil: se decide al abrir (no en un efecto)
                setOpen((o) => !o);
              }}>?</button>
      <Floating anchor={btn} open={open} onClose={close} id={id} role="dialog" label={def.title} modal={sheet} sheet={sheet}
                className="tip-box surface" boxRef={(el) => { box.current = el; }}
                onBackdropDown={() => { setOpen(false); btn.current?.focus({ preventScroll: true }); }}
                head={<div className="tip-head">
                  <strong>{def.title}</strong>
                  <button type="button" className="btn tip-close" onClick={closeAndFocus}>Cerrar</button>
                </div>}>
        {def.description && <p>{def.description}</p>}
        {def.formula && <p className="formula">{def.formula}</p>}
        {bands?.tables.map((t) => (
          <div key={t.title} className="tip-bands">
            <div className="eyebrow">Rangos de referencia · {t.title}</div>
            <ul>
              {t.bands.map((b) => {
                const mine = !!reading && b.label === reading;
                return (
                  <li key={b.label + b.range} className={mine ? `mine ${toVTone(b.tone as Tone)}` : undefined}>
                    <span className="num">{b.range}</span><span>{b.label}</span>
                    {mine && <span className="pill neutral">Tu valor{value ? ` ${value}` : ""}</span>}
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
        {value && !(reading && bands?.tables.some((t) => t.bands.some((b) => b.label === reading))) && (
          <p className="tip-mine"><span className="pill neutral">Tu valor {value}</span>{reading && reading !== "—" ? ` · ${reading}` : ""}</p>
        )}
        {bands?.note && <p className="muted">{bands.note}</p>}
        {def.tip && <p className="muted">{def.tip}</p>}
      </Floating>
    </span>
  );
}

/** v4 móvil (PM): una etiqueta y su «?» no se separan al partir la línea: la última palabra va pegada al botón. */
export function LabelTip({ text, children }: { text: string; children: ReactNode }) {
  const i = text.lastIndexOf(" ");
  return <>{text.slice(0, i + 1)}<span className="nobr">{text.slice(i + 1)}{children}</span></>;
}
