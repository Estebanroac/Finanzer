"use client";
import { useEffect, useRef, useState } from "react";
import type { PeerRival, PeerSummary, SearchHit } from "@/lib/api";
import { usePeers } from "@/v2/lib/usePeers";
import { chapterHref } from "@/v2/lib/routes";
import { SEARCH_DEBOUNCE_MS, searchV2 } from "@/v2/lib/search";

/** Columnas del comparador (spec §3.4): claves de `summary.metrics` (las mismas cifras que la página de cada empresa). */
const COLS: Array<{ key: string; label: string }> = [
  { key: "pe", label: "P/E" }, { key: "ev_ebitda", label: "EV/EBITDA" }, { key: "roic", label: "ROIC" },
  { key: "net_margin", label: "Margen neto" }, { key: "revenue_growth", label: "Crec. ingresos (3 años)" },
  { key: "de", label: "Deuda / Equity" }, { key: "market_cap", label: "Capitalización" },
];
const STATUS: Record<string, string> = { en_cola: "En cola", analizando: "Analizando…" };
const MAX_HITS = 6;

const Score = ({ s }: { s: { score: number | null; level: string | null } }) =>
  s.score == null ? <>Sin dato</> : <>{Math.round(s.score)}/100{s.level && <span className="metric-sub">{s.level}</span>}</>;

function Cells({ s }: { s: PeerSummary }) {
  return (<>
    <td data-label="Calidad" className="num"><Score s={s.quality} /></td>
    <td data-label="Precio" className="num"><Score s={s.price_score} /></td>
    {COLS.map((c) => {
      const m = s.metrics[c.key];
      // V7 · P5: «n. s.» (P/E con beneficio casi nulo) lleva su motivo y la cifra; V4b (nada oculto): a la vista, bajo el
      // valor, no al pasar el ratón
      return <td key={c.key} data-label={c.label} className="num">{m?.value_txt ?? "Sin dato"}
        {m?.note && <span className="metric-sub metric-note">{m.note}</span>}</td>;
    })}
  </>);
}

/**
 * Comparador de rivales: la empresa arriba y sus rivales analizados con el motor completo (`/api/v2/peers`). Mientras
 * haya rivales en cola o analizándose, vuelve a preguntar cada `poll_s` y pinta un esqueleto del mismo alto. Se
 * pueden quitar rivales y añadir otros con el buscador (`?symbols=`, como mucho `max_symbols`).
 */
export default function PeersTable({ symbol }: { symbol: string }) {
  const [chosen, setChosen] = useState<string[] | null>(null);

  const [q, setQ] = useState("");
  // Resultados del buscador con la búsqueda a la que responden: solo se pintan los de lo que está escrito ahora.
  const [found, setFound] = useState<{ term: string; hits: SearchHit[] }>({ term: "", hits: [] });
  const seq = useRef(0);

  // Revisión V6 (F4): el sondeo con reintentos, compartido con el capítulo 6 de la historia (usePeers)
  const { data, error } = usePeers(symbol, chosen);

  // Revisión V6 (F5): el buscador de /v2 (solo acciones), con espera tras la última tecla, la búsqueda anterior
  // cancelada y un contador de secuencia (una respuesta vieja nunca pisa a la nueva); al desmontar no queda nada vivo.
  useEffect(() => {
    const term = q.trim();
    const id = ++seq.current;
    if (!term) return;
    const ac = new AbortController();
    const t = setTimeout(() => {
      searchV2(term, ac.signal).then((hits) => { if (id === seq.current) setFound({ term, hits }); }).catch(() => {});
    }, SEARCH_DEBOUNCE_MS);
    return () => { clearTimeout(t); ac.abort(); };
  }, [q]);
  const hits = found.term === q.trim() ? found.hits : [];

  const current = data?.rivals.map((r) => r.symbol) ?? [];
  const max = data?.max_symbols ?? 0;
  // Revisión V6 (F4): actualización funcional sobre la última lista (dos clics seguidos no se pisan con una vieja).
  const latest = useRef<string[]>([]);
  useEffect(() => { latest.current = current; });
  const remove = (s: string) => setChosen((prev) => {
    const next = (prev ?? latest.current).filter((x) => x !== s);
    return next.length ? next : prev;
  });
  const add = (s: string) => {
    const sym = s.toUpperCase();
    setChosen((prev) => {
      const base = prev ?? latest.current;
      return sym === symbol || base.includes(sym) || base.length >= max ? prev : [...base, sym];
    });
    setQ("");
  };

  if (error && !data) return <p className="missing" data-missing><strong>Rivales</strong> · {error}</p>;
  const ncols = COLS.length + 3;
  return (
    <div className="peers" data-testid="peers">
      <p className="segs-head">
        {data?.source === "elegidos" ? "Rivales elegidos por ti." : "Rivales propuestos por Finanzer: misma industria de referencia y tamaño parecido; cada uno con su análisis de Finanzer."}
        {data?.industry && <> Industria: <strong>{data.industry}</strong>.</>}
        {data?.source === "elegidos" && <> <button type="button" className="btn link" onClick={() => setChosen(null)}>Volver a los propuestos</button></>}
      </p>
      <div className="techtable-wrap surface" tabIndex={0} role="region" aria-label="Comparador de rivales">
        <table className="techtable peerstable stack-md" style={{ "--stack-cols": 3 } as React.CSSProperties}>
          <thead><tr>
            <th scope="col">Empresa</th><th scope="col" className="num">Calidad</th><th scope="col" className="num">Precio</th>
            {COLS.map((c) => <th key={c.key} scope="col" className="num">{c.label}</th>)}
            <th scope="col"><span className="sr-only">Quitar</span></th>
          </tr></thead>
          <tbody>
            <tr className="me" data-testid="peer-company">
              <th scope="row"><span className="metric-name">{symbol}</span>{data?.company?.name && <span className="metric-sub">{data.company.name}</span>}</th>
              {data?.company ? <Cells s={data.company} /> : <td colSpan={ncols - 2} className="wide"><span className="skel" />Analizando…</td>}
              <td className="stack-hide" />
            </tr>
            {(data?.rivals ?? []).map((r: PeerRival) => (
              <tr key={r.symbol} data-status={r.status}>
                <th scope="row">
                  {r.status === "listo"
                    ? <a href={chapterHref(r.symbol)} className="metric-name">{r.symbol}</a>
                    : <span className="metric-name">{r.symbol}</span>}
                  {r.summary?.name && <span className="metric-sub">{r.summary.name}</span>}
                </th>
                {r.status === "listo" && r.summary ? <Cells s={r.summary} />
                  : r.status === "fallo" ? <td colSpan={ncols - 2} className="row-missing wide"><strong>Sin análisis</strong> · {r.reason ?? "Finanzer no pudo analizarla"}</td>
                  : <td colSpan={ncols - 2} className="wide" aria-busy="true"><span className="skel" />{STATUS[r.status]}</td>}
                <td className="wide stack-end"><button type="button" className="btn icon" aria-label={`Quitar ${r.symbol}`} disabled={!current.some((x) => x !== r.symbol)}
                  onClick={() => remove(r.symbol)}>×</button></td>
              </tr>
            ))}
            {!data && Array.from({ length: 3 }, (_, i) => (
              <tr key={i} aria-busy="true"><th scope="row"><span className="skel" /></th><td colSpan={ncols - 1} className="wide"><span className="skel" />Buscando rivales…</td></tr>
            ))}
          </tbody>
        </table>
      </div>
      {data?.note && <p className="missing" data-missing><strong>Rivales</strong> · {data.note}</p>}
      {error && data && <p className="missing" data-missing><strong>Actualización</strong> · {error}</p>}
      <div className="peer-add">
        <label htmlFor="peer-search">Añadir un rival {max > 0 && <span className="muted">({current.length} de {max})</span>}</label>
        <input id="peer-search" type="search" value={q} onChange={(e) => setQ(e.target.value)} autoComplete="off"
               placeholder="Busca por nombre o ticker" disabled={!data || current.length >= max} />
        {q.trim() && hits.length > 0 && (
          <ul className="peer-hits" aria-label="Resultados">
            {hits.slice(0, MAX_HITS).map((h) => (
              <li key={h.ticker}><button type="button" className="btn link" onClick={() => add(h.ticker)}>
                <strong>{h.ticker}</strong> {h.name}</button></li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
