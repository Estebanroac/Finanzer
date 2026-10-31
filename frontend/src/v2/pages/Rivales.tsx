"use client";
import type { Row } from "@/lib/api";
import type { PageProps } from "./DepthPage";
import PillIndex from "@/v2/components/depth/PillIndex";
import Section from "@/v2/components/depth/Section";
import Methodology from "@/v2/components/depth/Methodology";
import TechTable from "@/v2/components/depth/TechTable";
import PeersTable from "@/v2/components/PeersTable";

const PILLS = [{ id: "comparador", label: "Comparador" }, { id: "referencia", label: "Frente a la referencia" },
  { id: "metodologia", label: "Metodología" }];
const cap = (t: string) => t.charAt(0).toUpperCase() + t.slice(1);

/** Task 8 · Rivales: el comparador con rivales analizados por el motor y la comparativa completa con la referencia. */
export default function Rivales({ analysis: a, symbol }: PageProps) {
  const d = a.display, cmp = d.charts.comparison;
  const asRows = (items: typeof cmp.groups[number]["items"]): Row[] => items.map((i) => ({
    key: i.key, label: i.label, value: i.value_txt, bench: i.bench_txt, gap: i.gap_txt, reading: i.reading,
    tone: i.tone, state: "con_dato", text: i.text,
  }));
  return (<>
    <PillIndex items={PILLS} />
    <div className="wrap depth-body">
      <Section id="comparador" eyebrow="Rivales" title="Frente a empresas parecidas">
        <PeersTable symbol={symbol} />
      </Section>
      <Section id="referencia" eyebrow="Rivales" title={`Frente a la referencia: mejor en ${cmp.better} de ${cmp.total}`}>
        {cmp.groups.map((g) => (
          <TechTable key={g.title} caption={g.title} rows={asRows(g.items)} refLabel={cap(d.benchmark.short)} tooltips={d.tooltips} withText />
        ))}
        {cmp.market_note && <p className="segs-head">{cmp.market_note}</p>}
      </Section>
      <Methodology items={[
        { label: "Referencia", text: cmp.note },
        { label: "Rivales", text: "Los rivales propuestos salen de la misma industria de referencia (Damodaran) que resolvió el análisis de la empresa, ordenados por tamaño (capitalización) y, dentro de una banda de tamaño parecido, primero los de su región. Cada rival tiene su análisis completo de Finanzer: sus cifras son las de su propia página." },
      ]} />
    </div>
  </>);
}
