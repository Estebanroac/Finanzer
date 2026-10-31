"use client";
import { useEffect, useRef, useState } from "react";
import type { SearchHit } from "@/lib/api";
import { enterTarget, moveActive, searchV2, SEARCH_DEBOUNCE_MS, stockHref } from "@/v2/lib/search";
import { isAbort } from "@/v2/lib/http";
import { rememberName } from "@/lib/stockNames";
import "./SearchBox.css";

const NONE = -1;
/** El mismo corte de móvil que v2.css. */
const NARROW = "(max-width: 47.9375em)";

/** Si la pantalla es estrecha (solo se escucha si hace falta). */
function useNarrow(enabled: boolean): boolean {
  const [on, setOn] = useState(false);
  useEffect(() => {
    if (!enabled || typeof window.matchMedia !== "function") return;
    const m = window.matchMedia(NARROW);
    const sync = () => setOn(m.matches);
    sync();
    m.addEventListener("change", sync);
    return () => m.removeEventListener("change", sync);
  }, [enabled]);
  return on;
}

/** Buscador de /v2 (combobox de ARIA 1.2): resultados con nombre, ticker y bolsa; ↑ ↓ para elegir, Enter para abrir
 *  y Escape para cerrar. `hero`: el grande de la portada; si no, el de la barra general. */
export default function SearchBox({ hero = false, placeholder = "Buscar empresa o ticker…", shortPlaceholder }: {
  hero?: boolean; placeholder?: string;
  /** P8: el texto de ayuda en pantallas estrechas, donde el largo se corta («(Apple, AAP»). */
  shortPlaceholder?: string;
}) {
  const narrow = useNarrow(!!shortPlaceholder);
  const [q, setQ] = useState("");
  const [results, setResults] = useState<SearchHit[]>([]);
  const [searched, setSearched] = useState("");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(NONE);
  const seq = useRef(0);
  const input = useRef<HTMLInputElement>(null);
  // Ids fijos (uno por buscador: en cada página hay uno solo). useId daba ids distintos en el HTML prerenderizado y en
  // el cliente (la página se carga con next/dynamic) y React avisaba de un fallo de hidratación.
  const id = hero ? "search-home" : "search-bar";
  const listId = `${id}-list`;

  // Lo escrito antes de que React hidrate la página (el HTML ya es usable) no se pierde: el campo no está controlado
  // por React y, al montarse, el estado recoge su contenido.
  useEffect(() => {
    const typed = input.current?.value ?? "";
    // eslint-disable-next-line react-hooks/set-state-in-effect -- sincroniza una sola vez con el DOM previo a React
    if (typed) { setQ(typed); setOpen(document.activeElement === input.current); }
  }, []);

  useEffect(() => {
    const text = q.trim();
    const n = ++seq.current;
    if (!text) return;                              // sin texto no se pinta la lista (showList)
    const ac = new AbortController();               // al escribir otra cosa, la búsqueda anterior se cancela
    const t = setTimeout(() => {
      searchV2(text, ac.signal).then((r) => {
        if (n !== seq.current) return;              // llegó tarde: ya se escribió otra cosa
        setResults(r);
        setSearched(text);
        setActive(NONE);
      }).catch((e) => { if (!isAbort(e) && n === seq.current) { setResults([]); setSearched(text); } });
    }, SEARCH_DEBOUNCE_MS);
    return () => { clearTimeout(t); ac.abort(); };
  }, [q]);

  // Revisión V6 (F11): los resultados valen solo para lo que está escrito ahora (`searched` = q): Enter no abre un
  // resultado de una búsqueda anterior (oculto), y al escribir no queda marcada una opción vieja.
  const current = searched === q.trim();
  const shown = current ? results : [];

  // V4: el nombre viaja a la pantalla de carga de la empresa (recallName), que lo enseña antes de que llegue el análisis
  const go = (ticker: string) => {
    rememberName(ticker, results.find((r) => r.ticker.toUpperCase() === ticker.toUpperCase())?.name);
    window.location.assign(stockHref(ticker));
  };

  const onKey = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      setOpen(true);
      setActive((a) => moveActive(a, shown.length, e.key === "ArrowDown" ? 1 : -1));
    } else if (e.key === "Enter") {
      const t = enterTarget(q, shown, current ? active : NONE);
      if (t) {
        e.preventDefault();
        go(t);
      }
    } else if (e.key === "Escape") {
      setOpen(false);
      setActive(NONE);
    }
  };

  const showList = open && q.trim() !== "" && current;
  const listed = showList && results.length > 0;
  const status = !showList ? "" : results.length === 0 ? `Sin resultados para «${searched}»`
    : `${results.length} ${results.length === 1 ? "resultado" : "resultados"}`;

  return (
    <div className={`searchbox${hero ? " hero" : ""}`}>
      <input
        className="search" type="search" role="combobox" placeholder={narrow && shortPlaceholder ? shortPlaceholder : placeholder} aria-label="Buscar empresa o ticker"
        aria-expanded={listed} aria-controls={listed ? listId : undefined} aria-autocomplete="list"
        aria-activedescendant={showList && active !== NONE ? `${id}-o${active}` : undefined}
        ref={input} autoComplete="off" spellCheck={false}
        onChange={(e) => { setQ(e.target.value); setOpen(true); setActive(NONE); }}
        onKeyDown={onKey} onFocus={() => setOpen(true)} onBlur={() => setOpen(false)}
      />
      {/* Revisión V6 (F22): sin opciones no hay listbox (antes quedaba uno vacío y oculto) */}
      {listed && <ul id={listId} role="listbox" aria-label="Resultados de la búsqueda" className="results surface">
        {results.map((r, i) => (
          <li key={r.ticker} id={`${id}-o${i}`} role="option" aria-selected={i === active}
            className={i === active ? "on" : undefined}
            onMouseDown={(e) => { e.preventDefault(); go(r.ticker); }} onMouseEnter={() => setActive(i)}>
            <span className="r-name">{r.name}</span>
            <span className="r-meta num">{r.ticker}{r.exchange && <span className="muted"> · {r.exchange}</span>}</span>
          </li>
        ))}
      </ul>}
      {showList && results.length === 0 && <p className="no-results muted">{status}</p>}
      <span className="sr-only" role="status" aria-live="polite">{status}</span>
    </div>
  );
}
