"use client";

import { useState, useRef, useEffect } from "react";

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
}

export default function InfoTooltip({ content, size = "sm" }: Props) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const btnRef = useRef<HTMLButtonElement>(null);

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  // Close on Escape
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [open]);

  const sz = size === "sm" ? "w-3.5 h-3.5 text-[9px]" : "w-4 h-4 text-[10px]";

  return (
    <div ref={ref} className="relative inline-flex">
      <button
        ref={btnRef}
        onClick={(e) => { e.stopPropagation(); setOpen(!open); }}
        className={`${sz} rounded-full bg-white/[0.06] hover:bg-white/[0.12] text-zinc-500 hover:text-zinc-300 flex items-center justify-center transition-all duration-200 shrink-0`}
        aria-label={`Info: ${content.title}`}
      >
        ?
      </button>

      {open && (
        <>
          {/* Backdrop for mobile */}
          <div className="fixed inset-0 z-[998] sm:hidden" onClick={() => setOpen(false)} />

          {/* Tooltip card */}
          <div className="absolute z-[999] bottom-full left-1/2 -translate-x-1/2 mb-2 w-72 sm:w-80 animate-in fade-in slide-in-from-bottom-1 duration-200">
            <div className="bg-[#18181b] border border-white/[0.08] rounded-xl shadow-2xl shadow-black/60 overflow-hidden">
              {/* Header */}
              <div className="px-4 py-3 border-b border-white/[0.06] flex items-center justify-between">
                <h4 className="text-white text-sm font-semibold">{content.title}</h4>
                <button
                  onClick={() => setOpen(false)}
                  className="text-zinc-500 hover:text-zinc-300 text-xs transition-colors"
                >
                  ✕
                </button>
              </div>

              {/* Body */}
              <div className="px-4 py-3 space-y-3 max-h-64 overflow-y-auto scrollbar-thin">
                {/* Description */}
                <p className="text-zinc-400 text-xs leading-relaxed">
                  {content.description}
                </p>

                {/* Formula */}
                {content.formula && (
                  <div className="bg-white/[0.03] rounded-lg px-3 py-2">
                    <span className="text-zinc-600 text-[10px] uppercase tracking-wider font-medium">Formula</span>
                    <p className="text-zinc-300 text-xs font-mono mt-1">{content.formula}</p>
                  </div>
                )}

                {/* Thresholds */}
                {content.thresholds && content.thresholds.length > 0 && (
                  <div>
                    <span className="text-zinc-600 text-[10px] uppercase tracking-wider font-medium">Umbrales</span>
                    <div className="mt-1.5 space-y-1">
                      {content.thresholds.map((t, i) => (
                        <div key={i} className="flex items-center gap-2">
                          <span className={`w-1.5 h-1.5 rounded-full shrink-0`} style={{ backgroundColor: t.color }} />
                          <span className="text-zinc-300 text-xs font-mono">{t.value}</span>
                          <span className="text-zinc-500 text-xs">{t.label}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Good / Bad */}
                {(content.good || content.bad) && (
                  <div className="grid grid-cols-2 gap-2">
                    {content.good && (
                      <div className="bg-emerald-500/[0.06] border border-emerald-500/10 rounded-lg px-2.5 py-2">
                        <span className="text-emerald-400 text-[10px] font-medium uppercase tracking-wider">Bueno</span>
                        <p className="text-zinc-300 text-xs mt-1 leading-relaxed">{content.good}</p>
                      </div>
                    )}
                    {content.bad && (
                      <div className="bg-red-500/[0.06] border border-red-500/10 rounded-lg px-2.5 py-2">
                        <span className="text-red-400 text-[10px] font-medium uppercase tracking-wider">Malo</span>
                        <p className="text-zinc-300 text-xs mt-1 leading-relaxed">{content.bad}</p>
                      </div>
                    )}
                  </div>
                )}

                {/* Tip */}
                {content.tip && (
                  <div className="flex gap-2 items-start bg-blue-500/[0.06] border border-blue-500/10 rounded-lg px-2.5 py-2">
                    <span className="text-blue-400 text-xs">💡</span>
                    <p className="text-zinc-300 text-xs leading-relaxed">{content.tip}</p>
                  </div>
                )}
              </div>
            </div>

            {/* Arrow */}
            <div className="absolute left-1/2 -translate-x-1/2 -bottom-1 w-2 h-2 bg-[#18181b] border-r border-b border-white/[0.08] rotate-45" />
          </div>
        </>
      )}
    </div>
  );
}
