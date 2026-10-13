"use client";

import type { Display, ScoreBlock, StockAnalysis } from "@/lib/api";
import { pdfUrl } from "@/lib/api";
import { Collapsible, Help, Pill, StateTag, ToneBar, toneClass } from "./ui";

/**
 * Cabecera = portada del PDF: tipo de empresa y su motivo, las dos puntuaciones, el
 * veredicto verbal con la confianza (motivos en lenguaje llano y detalle técnico
 * desplegable), cobertura parcial, componentes de cada puntuación, métricas clave
 * del arquetipo y fortaleza / a vigilar / contexto. Todo sale de display.cover.
 *
 * Orden pensado para el móvil (390×844): el veredicto va justo debajo de las dos
 * puntuaciones, antes de las barras de componentes, para leerse sin hacer scroll.
 */
export default function StockHeader({ data }: { data: StockAnalysis }) {
  const D = data.display;
  const C = D.cover;
  const tips = D.tooltips;

  return (
    <header className="mb-8 space-y-4">
      {/* Título */}
      <div className="fade-up">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="flex items-center gap-2.5 mb-1 min-w-0">
              <h1 className="text-2xl sm:text-4xl font-bold text-white tracking-tight truncate">{data.profile.name}</h1>
              <span className="shrink-0 px-2 py-0.5 rounded-md text-[11px] font-mono font-semibold text-[#0cc06c] bg-[#0cc06c]/10 border border-[#0cc06c]/20">
                {data.symbol}
              </span>
            </div>
            <p className="text-sm text-zinc-500 truncate">
              {[data.profile.sector, data.profile.industry, data.profile.exchange].filter(Boolean).join(" · ")}
            </p>
          </div>
          <a href={pdfUrl(data.symbol)} target="_blank" rel="noopener noreferrer" className="fz-btn press shrink-0"
            aria-label="Descargar el informe en PDF">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <span className="hidden sm:inline">Descargar PDF</span>
            <span className="sm:hidden">PDF</span>
          </a>
        </div>
        {C.classification_notes.length > 0 && (
          <p className="mt-3 text-[13px] leading-relaxed text-zinc-400">
            <span className="fz-arch">{C.archetype_label}</span>{" "}
            {C.classification_notes.join(" ")}
          </p>
        )}
        {C.currency_note && <p className="mt-1.5 text-[12px] leading-relaxed text-zinc-500">{C.currency_note}</p>}
      </div>

      {/* Puntuaciones · veredicto · componentes */}
      <div className="fz-hero fade-up delay-1">
        <div className="fz-hero-main">
          <div className="fz-hero-scores">
            <ScoreBlockView b={C.quality} helpKey="quality" bands={tips.quality} />
            <ScoreBlockView b={C.price} helpKey="price" bands={tips.price} />
          </div>
          <Verdict display={D} />
        </div>
        <div className="fz-hero-cats">
          {C.categories.map((g, gi) => (
            <div key={g.title} className="mb-3 last:mb-0">
              <div className="fz-kicker mb-2 flex items-center gap-2">
                {g.title}
                {gi === 0 && <Help k="category" title="Categorías" bands={tips.category} />}
              </div>
              {g.items.map((c) => (
                <div key={c.name} className="fz-cat-row">
                  <span className="fz-cat-name">{c.name}</span>
                  {c.conclusive ? (
                    <>
                      <ToneBar pct={c.pct} tone={c.tone} />
                      <span className="fz-cat-score"><b>{c.score}</b><span>/{c.max}</span></span>
                    </>
                  ) : (
                    <>
                      <span className="state-tag state-sin_dato">{c.text}</span>
                      <span className="fz-cat-score"><b>n/c</b></span>
                    </>
                  )}
                </div>
              ))}
            </div>
          ))}
        </div>
      </div>

      {/* Métricas clave del arquetipo */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 fade-up delay-3">
        {C.kpis.map((k) => (
          <div key={k.key + k.label} className="fz-kpi">
            <span className="fz-kpi-v">{k.value}</span>
            <span className="fz-kpi-l">
              {k.label}
              <Help k={k.key === "price" ? "price_now" : k.key} title={k.label} bands={tips[k.key]} value={k.value}
                reading={D.readings[k.key] ? { label: D.readings[k.key]!.label, tone: D.readings[k.key]!.tone } : null} />
            </span>
            <StateTag state={k.state} />
          </div>
        ))}
      </div>

      {/* Lo esencial */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5 fade-up delay-4">
        {C.highlights.map((h) => (
          <div key={h.kind} className={`fz-hl ${toneClass(h.tone)}`}>
            <span className="fz-hl-k fz-tone-fg">{h.kicker}</span>
            <span className="fz-hl-t">{h.text}</span>
          </div>
        ))}
      </div>
    </header>
  );
}

/** Veredicto verbal + confianza (llano) + cobertura parcial + detalle técnico desplegable. */
function Verdict({ display }: { display: Display }) {
  const C = display.cover;
  const conf = display.confidence;
  const tech = (conf?.reasons.length ?? 0) > 0 || C.classification_detail.length > 0;
  return (
    <div className={`fz-verdict ${toneClass(C.quality.tone)}`}>
      <div className="fz-kicker mb-1">Veredicto</div>
      <p className="text-xl sm:text-2xl font-bold text-white leading-snug">{C.verdict.text}</p>
      {C.verdict.confidence_text && (
        <p className={`mt-1 text-[14.5px] ${toneClass(C.verdict.confidence_tone)} fz-tone-fg flex items-center gap-2`}>
          {C.verdict.confidence_text}
          <Help k="confidence" title="Confianza del veredicto" />
        </p>
      )}
      {C.confidence_reasons.length > 0 && (
        <div className="mt-3">
          <div className="fz-kicker mb-1.5">Motivos de la confianza</div>
          <ul className="fz-reasons">
            {C.confidence_reasons.map((r) => <li key={r}>{r}</li>)}
          </ul>
        </div>
      )}
      {C.coverage_notes.length > 0 && (
        <p className="mt-3 text-[13px] tone-warn fz-tone-fg">Cobertura parcial: {C.coverage_notes.join("; ")}</p>
      )}
      {tech && (
        <div className="mt-3">
          <Collapsible summary="Detalle técnico">
            <ul className="fz-tech">
              {conf?.reasons.map((r, i) => (
                <li key={i}>
                  {r.text && <span className="block text-zinc-300">{r.text}</span>}
                  <span className="text-zinc-500">{r.dimension} {r.level.replace("_", " ")}: {r.detail}</span>
                </li>
              ))}
              {C.classification_detail.map((t) => (
                <li key={t}><span className="text-zinc-500">Clasificación: {t}</span></li>
              ))}
            </ul>
          </Collapsible>
        </div>
      )}
    </div>
  );
}

function ScoreBlockView({ b, helpKey, bands }: { b: ScoreBlock; helpKey: string;
  bands?: StockAnalysis["display"]["tooltips"][string] }) {
  return (
    <div className={`fz-score ${toneClass(b.tone)}`}>
      <div className="fz-kicker flex items-center gap-1.5">
        {b.title}
        <Help k={helpKey} title={b.title} bands={bands} value={b.score != null ? `${b.score}/100` : undefined}
          reading={b.level ? { label: b.level, tone: b.tone } : null} />
      </div>
      <div className="text-[11px] text-zinc-500 mb-1">{b.question}</div>
      <div className="flex items-baseline gap-1">
        <span className="fz-score-n fz-tone-fg">{b.score ?? "—"}</span>
        <span className="text-zinc-500 text-sm">/100</span>
      </div>
      <Pill tone={b.tone}>{b.level ?? "sin dato"}</Pill>
      {b.note && <div className="mt-1 text-[11.5px] tone-warn fz-tone-fg leading-snug">{b.note}</div>}
    </div>
  );
}
