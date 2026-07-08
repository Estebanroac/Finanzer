"use client";

import { useState, useEffect } from "react";
import { createPortal } from "react-dom";
import { activeBandIndex } from "@/lib/metricScale";

export interface TooltipContent {
  title: string;
  description: string;
  formula?: string;
  good?: string;
  bad?: string;
  thresholds?: { label: string; value: string; color: string }[];
  tip?: string;
}

interface Props {
  content: TooltipContent;
  size?: "sm" | "md";
  /** Valor numérico crudo del indicador (decimal para %, ratio crudo). */
  value?: number | null;
  /** Valor ya formateado para mostrar (ej. "2.16%", "37.58x"). */
  valueLabel?: string;
}

/**
 * Botón "?" que abre una TARJETA explicativa (no una burbuja anclada).
 *
 * Vía portal a <body> para escapar los `transform` de los paneles animados.
 * Adaptativo: hoja inferior en móvil, tarjeta centrada en escritorio.
 * Si se pasa `value`/`valueLabel`, muestra "Tu valor" coloreado por su banda y
 * resalta la fila correspondiente en la tabla de rangos.
 */
export default function InfoTooltip({ content, size = "sm", value, valueLabel }: Props) {
  const [open, setOpen] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => setMounted(true), []);

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

  const sz = size === "sm" ? "w-3.5 h-3.5 text-[9px]" : "w-4 h-4 text-[10px]";
  const titleId = `tt-${content.title.replace(/\s+/g, "-").toLowerCase()}`;

  const thresholds = content.thresholds;
  const activeIdx = thresholds ? activeBandIndex(thresholds, value) : -1;
  const activeBand = activeIdx >= 0 && thresholds ? thresholds[activeIdx] : null;
  const showValue = valueLabel != null && valueLabel !== "" && valueLabel !== "N/A";

  return (
    <>
      <button
        onClick={(e) => { e.stopPropagation(); setOpen(true); }}
        className={`${sz} rounded-full bg-white/[0.06] hover:bg-white/[0.12] text-zinc-500 hover:text-zinc-300 flex items-center justify-center transition-all duration-200 shrink-0 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#0cc06c]/50`}
        aria-label={`Qué es: ${content.title}`}
      >
        ?
      </button>

      {mounted && open && createPortal(
        <div
          className="fixed inset-0 z-[9999] flex items-end justify-center sm:items-center p-0 sm:p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby={titleId}
          onClick={(e) => { e.stopPropagation(); setOpen(false); }}
        >
          <div className="absolute inset-0 bg-black/60 backdrop-blur-[2px] animate-in fade-in duration-200" />

          <div
            onClick={(e) => e.stopPropagation()}
            className="relative w-full sm:w-[440px] sm:max-w-[92vw] max-h-[86vh] flex flex-col
                       bg-[#161618] border border-white/[0.08]
                       rounded-t-3xl sm:rounded-2xl shadow-2xl shadow-black/70
                       animate-in fade-in slide-in-from-bottom-4 sm:zoom-in-95 sm:slide-in-from-bottom-0 duration-300
                       motion-reduce:animate-none"
          >
            {/* Asa (móvil) */}
            <div className="sm:hidden flex justify-center pt-2.5 pb-1 shrink-0">
              <span className="w-9 h-1 rounded-full bg-white/15" />
            </div>

            {/* Cabecera */}
            <div className="flex items-start justify-between gap-3 px-5 pt-3 sm:pt-4 pb-3 border-b border-white/[0.06] shrink-0">
              <h4 id={titleId} className="text-white text-[15px] font-semibold leading-snug text-balance">
                {content.title}
              </h4>
              <button
                onClick={() => setOpen(false)}
                className="shrink-0 w-7 h-7 -mr-1 -mt-0.5 rounded-full text-zinc-500 hover:text-zinc-200 hover:bg-white/[0.06] flex items-center justify-center transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-[#0cc06c]/50"
                aria-label="Cerrar"
              >
                ✕
              </button>
            </div>

            {/* Cuerpo */}
            <div className="px-5 py-4 space-y-4 overflow-y-auto scrollbar-thin overscroll-contain">
              {/* Tu valor actual (coloreado por su banda) */}
              {showValue && (
                <div
                  className="flex items-center justify-between gap-3 px-3.5 py-2.5 rounded-xl border"
                  style={{
                    borderColor: activeBand ? `${activeBand.color}55` : "rgba(255,255,255,0.08)",
                    background: activeBand ? `${activeBand.color}14` : "rgba(255,255,255,0.03)",
                  }}
                >
                  <span className="text-[10px] uppercase tracking-wider text-zinc-400 font-semibold">Tu valor</span>
                  <span className="flex items-baseline gap-2">
                    <span
                      className="text-lg font-semibold tabular-nums leading-none"
                      style={{ color: activeBand ? activeBand.color : "#fafafa" }}
                    >
                      {valueLabel}
                    </span>
                    {activeBand && (
                      <span className="text-xs text-zinc-400">· {activeBand.label}</span>
                    )}
                  </span>
                </div>
              )}

              {/* Qué es */}
              <p className="text-zinc-300 text-[13px] leading-relaxed">
                {content.description}
              </p>

              {/* Cómo se calcula */}
              {content.formula && (
                <section>
                  <SectionLabel>Cómo se calcula</SectionLabel>
                  <div className="mt-1.5 bg-white/[0.03] border border-white/[0.05] rounded-lg px-3 py-2.5">
                    <p className="text-zinc-200 text-[13px] font-mono leading-relaxed">{content.formula}</p>
                  </div>
                </section>
              )}

              {/* Rangos de referencia — tabla */}
              {thresholds && thresholds.length > 0 && (
                <section>
                  <SectionLabel>Rangos de referencia</SectionLabel>
                  <div className="mt-2 rounded-xl border border-white/[0.07] overflow-hidden">
                    {thresholds.map((t, i) => {
                      const active = i === activeIdx;
                      return (
                        <div
                          key={i}
                          className="flex items-center gap-3 px-3 py-2 border-b border-white/[0.05] last:border-b-0"
                          style={active ? { background: `${t.color}14` } : undefined}
                        >
                          <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: t.color }} />
                          <span
                            className="text-[13px] font-mono tabular-nums min-w-[68px]"
                            style={{ color: active ? t.color : "#e4e4e7", fontWeight: active ? 600 : 400 }}
                          >
                            {t.value}
                          </span>
                          <span className="text-[13px] leading-snug" style={{ color: active ? "#e4e4e7" : "#a1a1aa" }}>
                            {t.label}
                          </span>
                          {active && (
                            <span
                              className="ml-auto shrink-0 text-[9px] font-semibold uppercase tracking-wide px-1.5 py-0.5 rounded"
                              style={{ color: t.color, backgroundColor: `${t.color}22` }}
                            >
                              Tu valor
                            </span>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </section>
              )}

              {/* Bueno / Malo */}
              {(content.good || content.bad) && (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                  {content.good && (
                    <div className="bg-emerald-500/[0.07] border border-emerald-500/15 rounded-lg px-3 py-2.5">
                      <span className="text-emerald-400 text-[10px] font-semibold uppercase tracking-wider">Bueno</span>
                      <p className="text-zinc-300 text-[12.5px] mt-1 leading-relaxed">{content.good}</p>
                    </div>
                  )}
                  {content.bad && (
                    <div className="bg-red-500/[0.07] border border-red-500/15 rounded-lg px-3 py-2.5">
                      <span className="text-red-400 text-[10px] font-semibold uppercase tracking-wider">Malo</span>
                      <p className="text-zinc-300 text-[12.5px] mt-1 leading-relaxed">{content.bad}</p>
                    </div>
                  )}
                </div>
              )}

              {/* Tip */}
              {content.tip && (
                <div className="flex gap-2.5 items-start bg-[#0cc06c]/[0.07] border border-[#0cc06c]/15 rounded-lg px-3 py-2.5">
                  <span className="text-[13px] leading-none mt-0.5">💡</span>
                  <p className="text-zinc-300 text-[12.5px] leading-relaxed">{content.tip}</p>
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

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <span className="text-zinc-500 text-[10px] uppercase tracking-wider font-semibold">
      {children}
    </span>
  );
}
