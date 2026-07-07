"use client";

import { useLayoutEffect, useRef, useState } from "react";
import type { StockAnalysis } from "@/lib/api";
import ValuationTab from "./tabs/ValuationTab";
import ProfitabilityTab from "./tabs/ProfitabilityTab";
import HealthTab from "./tabs/HealthTab";
import IntrinsicTab from "./tabs/IntrinsicTab";
import EvaluationTab from "./tabs/EvaluationTab";
import ComparativeTab from "./tabs/ComparativeTab";
import HistoricalTab from "./tabs/HistoricalTab";

const TABS = [
  { id: "valuation", label: "Valoración" },
  { id: "profitability", label: "Rentabilidad" },
  { id: "health", label: "Solidez" },
  { id: "historical", label: "Histórico" },
  { id: "comparative", label: "Comparativa" },
  { id: "intrinsic", label: "Valor Intrínseco" },
  { id: "evaluation", label: "Evaluación" },
];

interface TabsSectionProps {
  data: StockAnalysis;
}

export default function TabsSection({ data }: TabsSectionProps) {
  const [activeIdx, setActiveIdx] = useState(0);
  const [dir, setDir] = useState("14px"); // sentido del slide del panel
  const btnRefs = useRef<(HTMLButtonElement | null)[]>([]);
  const [underline, setUnderline] = useState({ left: 0, width: 0 });

  // Magic underline: se mide desde la tab activa y se desliza con transición.
  useLayoutEffect(() => {
    const measure = () => {
      const btn = btnRefs.current[activeIdx];
      if (btn) setUnderline({ left: btn.offsetLeft, width: btn.offsetWidth });
    };
    measure();
    // re-medir al cargar fuentes y al redimensionar (los anchos cambian)
    window.addEventListener("resize", measure);
    document.fonts?.ready.then(measure).catch(() => {});
    return () => window.removeEventListener("resize", measure);
  }, [activeIdx]);

  const select = (i: number) => {
    if (i === activeIdx) return;
    setDir(i > activeIdx ? "16px" : "-16px");
    setActiveIdx(i);
    btnRefs.current[i]?.scrollIntoView({ inline: "center", block: "nearest", behavior: "smooth" });
  };

  const activeTab = TABS[activeIdx].id;

  return (
    <div>
      {/* Tab bar — sticky bajo el nav (h-14), frosted, con underline deslizante */}
      <div className="sticky top-14 z-40 -mx-4 px-4 sm:-mx-6 sm:px-6 mb-8
        backdrop-blur-xl bg-[#050507]/75 border-b border-white/[0.06]">
        <div className="relative flex gap-1 overflow-x-auto tab-scroll">
          {TABS.map((tab, i) => (
            <button
              key={tab.id}
              ref={el => { btnRefs.current[i] = el; }}
              onClick={() => select(i)}
              className={`press relative flex-shrink-0 px-4 py-3.5 text-sm font-medium transition-colors whitespace-nowrap ${
                i === activeIdx ? "text-white" : "text-zinc-500 hover:text-zinc-300"
              }`}
            >
              {tab.label}
            </button>
          ))}
          <span
            className="absolute bottom-0 h-0.5 bg-[#0cc06c] rounded-full pointer-events-none
              shadow-[0_0_8px_rgba(12,192,108,0.6)]"
            style={{
              left: underline.left,
              width: underline.width,
              transition: "left 0.35s cubic-bezier(0.16,1,0.3,1), width 0.35s cubic-bezier(0.16,1,0.3,1)",
            }}
          />
        </div>
      </div>

      {/* Contenido — remonta por tab con slide direccional */}
      <div key={activeTab} className="tab-panel-in" style={{ "--dir": dir } as React.CSSProperties}>
        {activeTab === "valuation" && <ValuationTab data={data} />}
        {activeTab === "profitability" && <ProfitabilityTab data={data} />}
        {activeTab === "health" && <HealthTab data={data} />}
        {activeTab === "historical" && <HistoricalTab data={data} />}
        {activeTab === "comparative" && <ComparativeTab data={data} />}
        {activeTab === "intrinsic" && <IntrinsicTab data={data} />}
        {activeTab === "evaluation" && <EvaluationTab data={data} />}
      </div>
    </div>
  );
}
