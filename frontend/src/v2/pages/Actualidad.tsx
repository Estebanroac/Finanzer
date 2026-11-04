"use client";
import type { PageProps } from "./DepthPage";
import { toVTone } from "@/v2/lib/tone";
import PillIndex from "@/v2/components/depth/PillIndex";
import Section, { Missing } from "@/v2/components/depth/Section";
import Methodology from "@/v2/components/depth/Methodology";
import NewsCard from "@/v2/components/NewsCard";
import { analysisLogo } from "@/v2/lib/logo";
import SignalsTable from "@/v2/components/SignalsTable";

const PILLS = [{ id: "noticias", label: "Noticias" }, { id: "resultados", label: "Próximos resultados" },
  { id: "senales", label: "Señales" }, { id: "conductual", label: "Lectura conductual" }, { id: "metodologia", label: "Metodología" }];

/** Task 10 · Actualidad: noticias, próximos resultados y PEAD, señales de mercado y lectura conductual (contexto). */
export default function Actualidad({ analysis: a, symbol }: PageProps) {
  const d = a.display, m = d.sections.market ?? null, news = d.extended?.news_featured ?? d.extended?.news ?? m?.news ?? [], ne = d.extended?.next_earnings ?? null;
  const pead = m?.rows.find((r) => r.key === "pead");
  return (<>
    <PillIndex items={PILLS} />
    <div className="wrap depth-body">
      <Section id="noticias" eyebrow="Actualidad" title="Noticias de la última semana">
        {news.length > 0 ? (<>
          <div className="news three" data-sym-row>{news.map((n, i) => <NewsCard key={n.url ?? i} n={n} symbol={symbol}
            name={a.profile.name} logo={analysisLogo(a)} />)}</div>
          {m?.news_note && <p className="muted small">{m.news_note}</p>}
        </>) : <Missing title="Noticias" reason={m?.news_note ?? "sin titulares recientes"} />}
      </Section>

      <Section id="resultados" eyebrow="Actualidad" title="Próximos resultados">
        {/* Tres filas compartidas (título · cifra y lectura · fuente) */}
        <div className="dgrid sub" style={{ "--rows": 3 } as React.CSSProperties} data-sym-row>
          <div className="card surface" data-testid="next-earnings">
            <h4>Fecha {ne?.kind && <span className="pill neutral">{ne.kind}</span>}</h4>
            {ne?.status === "ok" && ne.date_txt ? <p className="tile-value">{ne.date_txt}</p> : <p>{ne?.reason ?? "Sin fecha"}</p>}
            <p className="muted small">{ne?.status === "ok" ? (ne.basis ?? "") : ""}</p>
          </div>
          <div className="card surface"><h4>Deriva tras los resultados (PEAD)</h4>
            {pead ? <p><span className={`tile-value num tone-${toVTone(pead.tone)}`}>{pead.value}</span> {pead.text}</p> : <p>Sin lectura de la deriva.</p>}
            <p className="muted small">{m?.pead_note ?? "Sin serie de mercado para leerla."}</p>
          </div>
        </div>
      </Section>

      <Section id="senales" eyebrow="Actualidad" title="Señales de mercado">
        {m ? (<>
          <p className="segs-head"><span className="pill neutral">Contexto: no puntúa</span> {m.note}</p>
          {m.status_note && <p className="missing">{m.status_note}</p>}
          <SignalsTable market={m} />
        </>) : <Missing title="Señales de mercado" reason="sin serie de precios para calcularlas" />}
      </Section>

      <Section id="conductual" eyebrow="Actualidad" title={m?.behavioral_title ?? "Lectura conductual del mercado"}>
        {m && m.behavioral.length > 0
          ? <div className="card surface"><ul className="stack">{m.behavioral.map((t) => <li key={t}>{t}</li>)}</ul></div>
          : <Missing title="Lectura conductual" reason="el análisis no detecta hoy ningún patrón conductual en el precio" />}
      </Section>

      <Methodology items={[
        { label: "Noticias", text: m?.news_note },
        { label: "Serie de mercado", text: m?.source },
        { label: "Señales", text: m?.note },
      ]} />
    </div>
  </>);
}
