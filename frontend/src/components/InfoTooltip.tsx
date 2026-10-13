"use client";

import { useEffect, useId, useState, useSyncExternalStore } from "react";
import { createPortal } from "react-dom";
import type { MetricBands, Tone } from "@/lib/api";
import type { Definition } from "@/lib/tooltips";

interface Props {
  def: Definition;
  /** Bandas aplicadas a esta empresa (display.tooltips[clave]); sin bandas propias en el frontend. */
  bands?: MetricBands;
  /** Valor ya formateado por el backend. */
  value?: string;
  /** Lectura del backend para este valor (etiqueta + tono). */
  reading?: { label: string; tone: Tone | null } | null;
  /** Etiquetas de banda activas (la lectura de la fila y, si existe, la del score). */
  activeLabels?: Array<string | null | undefined>;
  /** Frase de la lectura (la misma que el PDF usa en el texto de la sección). */
  text?: string | null;
}

const noop = () => () => {};

/**
 * Botón "?" que abre una tarjeta explicativa: qué es la métrica, cómo se calcula,
 * la lectura que le da el backend y las bandas aplicadas a esta empresa. La banda
 * resaltada es la que coincide con la lectura del backend (por etiqueta): el
 * frontend no compara números contra umbrales.
 * Portal a <body> para escapar los transform de los paneles; hoja inferior en móvil.
 */
export default function InfoTooltip({ def, bands, value, reading, activeLabels = [], text }: Props) {
  const [open, setOpen] = useState(false);
  const isClient = useSyncExternalStore(noop, () => true, () => false);
  const titleId = useId();

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [open]);

  const active = new Set(activeLabels.filter((l): l is string => !!l));
  const showValue = value != null && value !== "" && value !== "N/A" && value !== "—";

  return (
    <>
      <button
        type="button"
        onClick={(e) => { e.stopPropagation(); setOpen(true); }}
        className="fz-help"
        aria-label={`Qué es: ${def.title}`}
      >
        ?
      </button>

      {isClient && open && createPortal(
        <div className="fz-modal" role="dialog" aria-modal="true" aria-labelledby={titleId}
          onClick={(e) => { e.stopPropagation(); setOpen(false); }}>
          <div className="fz-modal-veil" />
          <div className="fz-modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="sm:hidden flex justify-center pt-2.5 pb-1 shrink-0">
              <span className="w-9 h-1 rounded-full bg-white/15" />
            </div>
            <div className="flex items-start justify-between gap-3 px-5 pt-3 sm:pt-4 pb-3 border-b border-white/[0.06] shrink-0">
              <h4 id={titleId} className="text-white text-[15px] font-semibold leading-snug text-balance">{def.title}</h4>
              <button type="button" onClick={() => setOpen(false)} className="fz-modal-x" aria-label="Cerrar">✕</button>
            </div>

            <div className="px-5 py-4 space-y-4 overflow-y-auto overscroll-contain">
              {showValue && (
                <div className={`fz-yourval tone-${reading?.tone ?? "none"}`}>
                  <span className="text-[10px] uppercase tracking-wider text-zinc-400 font-semibold">Valor de la empresa</span>
                  <span className="flex items-baseline gap-2">
                    <span className="text-lg font-semibold tabular-nums leading-none fz-tone-fg">{value}</span>
                    {reading && <span className="text-xs text-zinc-400">· {reading.label}</span>}
                  </span>
                </div>
              )}
              {text && (
                <section>
                  <SectionLabel>Lectura</SectionLabel>
                  <p className="mt-1 text-zinc-200 text-[13px] leading-relaxed">{capitalize(text)}</p>
                </section>
              )}
              {def.description && <p className="text-zinc-300 text-[13px] leading-relaxed">{def.description}</p>}
              {def.formula && (
                <section>
                  <SectionLabel>Cómo se calcula</SectionLabel>
                  <div className="mt-1.5 bg-white/[0.03] border border-white/[0.05] rounded-lg px-3 py-2.5">
                    <p className="text-zinc-200 text-[13px] font-mono leading-relaxed">{def.formula}</p>
                  </div>
                </section>
              )}
              {bands?.note && <p className="text-[12.5px] text-zinc-400 leading-relaxed">{bands.note}</p>}
              {bands?.tables.map((t, ti) => (
                <section key={ti}>
                  <SectionLabel>{t.title || "Bandas aplicadas"}</SectionLabel>
                  <div className="mt-2 rounded-xl border border-white/[0.07] overflow-hidden">
                    {t.bands.map((b, i) => {
                      const on = active.has(b.label);
                      return (
                        <div key={i} className={`fz-band tone-${b.tone} ${on ? "is-on" : ""}`}>
                          <span className="fz-band-dot" />
                          <span className="fz-band-range">{b.range}</span>
                          <span className="fz-band-label">{b.label}</span>
                          {on && <span className="fz-band-you">Esta empresa</span>}
                        </div>
                      );
                    })}
                  </div>
                </section>
              ))}
              {(def.good || def.bad) && (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                  {def.good && (
                    <div className="bg-emerald-500/[0.07] border border-emerald-500/15 rounded-lg px-3 py-2.5">
                      <span className="text-emerald-400 text-[10px] font-semibold uppercase tracking-wider">A favor</span>
                      <p className="text-zinc-300 text-[12.5px] mt-1 leading-relaxed">{def.good}</p>
                    </div>
                  )}
                  {def.bad && (
                    <div className="bg-red-500/[0.07] border border-red-500/15 rounded-lg px-3 py-2.5">
                      <span className="text-red-400 text-[10px] font-semibold uppercase tracking-wider">En contra</span>
                      <p className="text-zinc-300 text-[12.5px] mt-1 leading-relaxed">{def.bad}</p>
                    </div>
                  )}
                </div>
              )}
              {def.tip && (
                <div className="bg-[#0cc06c]/[0.07] border border-[#0cc06c]/15 rounded-lg px-3 py-2.5">
                  <p className="text-zinc-300 text-[12.5px] leading-relaxed">{def.tip}</p>
                </div>
              )}
            </div>
          </div>
        </div>,
        document.body
      )}
    </>
  );
}

function capitalize(t: string): string {
  const s = t.trim();
  return s ? s[0].toUpperCase() + s.slice(1) : s;
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return <span className="text-zinc-500 text-[10px] uppercase tracking-wider font-semibold">{children}</span>;
}
