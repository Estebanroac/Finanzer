"use client";
import { useEffect, useState } from "react";
import type { SegmentsResponse } from "@/lib/api";
import { fetchSegments } from "@/v2/lib/companyData";
import { isAbort } from "@/v2/lib/http";
import { chapterHref } from "@/v2/lib/routes";
import { Missing } from "@/v2/components/depth/Section";

/** V7 · P2: concentración de los ingresos, como hechos del informe anual (segments.summary del backend): el mayor
 *  segmento con su peso y los que bajaron en el último ejercicio. Sin interpretación; enlazado a la página Negocio. */
export default function Concentration({ symbol }: { symbol: string }) {
  const [seg, setSeg] = useState<SegmentsResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    const ac = new AbortController();
    fetchSegments(symbol, ac.signal).then(setSeg).catch((e: Error) => { if (!isAbort(e)) setErr(e.message); });
    return () => ac.abort();
  }, [symbol]);
  if (err) return <Missing title="Concentración" reason={err} />;
  if (!seg) return <p className="missing" aria-busy="true">Cargando los ingresos por segmento de la SEC…</p>;
  const s = seg.summary;
  if (!s || !s.top) return <Missing title="Concentración" reason={seg.reason ?? "el informe anual no desglosa los ingresos"} />;
  const more = <a href={chapterHref(symbol, "negocio", "segmentos")} data-nav>Ver los ingresos por segmento →</a>;
  return (
    <div className="card surface" data-testid="concentration">
      <dl className="kv">
        <dt>Mayor segmento ({s.top.axis_label}, FY{s.fy})</dt>
        <dd><span data-testid="concentration-top">{s.top.label}: {s.top.share_txt} de los {s.concept_label?.toLowerCase() ?? "ingresos"}</span></dd>
        {/* V6b (E8): el rango solo con el ejercicio anterior (sin él, «FY → FY2024») */}
        <dt>Bajan en el último ejercicio{s.prev_fy ? ` (FY${s.prev_fy} → FY${s.fy})` : ""}</dt>
        <dd data-testid="concentration-falling">{s.falling.length
          ? s.falling.map((f) => `${f.label} ${f.change_txt}${f.axis_label ? ` (${f.axis_label})` : ""}`).join(" · ")
          : "ninguno"}</dd>
      </dl>
      {s.coverage_note && <p className="missing"><strong>Cobertura:</strong> {s.coverage_note}</p>}
      <p className="small muted">Fuente: {s.source ? `${s.source.form} presentado el ${s.source.filed} en la SEC` : "informe anual en la SEC"}. {more}</p>
    </div>
  );
}
