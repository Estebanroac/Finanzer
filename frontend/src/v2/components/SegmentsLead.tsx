"use client";
import { useEffect, useState } from "react";
import type { SegmentsResponse } from "@/lib/api";
import { fetchSegments } from "@/v2/lib/companyData";
import { isAbort } from "@/v2/lib/http";

/** V7 · P4: la lectura de «Cómo gana dinero» desde los segmentos (frase del backend); sin ellos, la de reserva. La
 *  petición es la misma que la del detalle de la sección (fetchSegments la guarda por símbolo). */
export function SegmentsLead({ symbol, fallback }: { symbol: string; fallback: string }) {
  const [seg, setSeg] = useState<SegmentsResponse | null>(null);
  useEffect(() => {
    const ac = new AbortController();
    fetchSegments(symbol, ac.signal).then(setSeg).catch((e: Error) => { if (!isAbort(e)) setSeg(null); });
    return () => ac.abort();
  }, [symbol]);
  const s = seg?.summary;
  return <p className="lead" data-testid="segments-lead">{s?.text ? `${s.text}${s.second_text ? ` ${s.second_text}` : ""}` : fallback}</p>;
}
