"use client";

import { useState } from "react";
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
  const [activeTab, setActiveTab] = useState("valuation");

  return (
    <div>
      {/* Tab bar — underline style */}
      <div className="flex gap-1 border-b border-white/[0.06] mb-8 overflow-x-auto tab-scroll">
        {TABS.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`relative flex-shrink-0 px-4 py-3 text-sm font-medium transition-colors whitespace-nowrap ${
              activeTab === tab.id
                ? "text-white"
                : "text-zinc-500 hover:text-zinc-300"
            }`}
          >
            {tab.label}
            {activeTab === tab.id && (
              <span className="absolute bottom-0 left-2 right-2 h-0.5 bg-[#00d632] rounded-full" />
            )}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="fade-in" key={activeTab}>
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
