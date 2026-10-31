"use client";
import { lazyWith } from "@/v2/lib/lazy";
import type { StockAnalysis } from "@/lib/api";
import { chapterHref, type ChapterSlug } from "@/v2/lib/routes";
import { CHAPTER_ORDER, SECTION_LABELS, type ChapterModel } from "@/v2/lib/story";
import KeyFigures from "@/v2/components/KeyFigures";
import { SegmentsLead } from "@/v2/components/SegmentsLead";

export interface PageProps { analysis: StockAnalysis; symbol: string }

// Revisión V6 (F13): el detalle de cada sección es su propio fragmento (abrir Calidad no descarga Rivales ni las
// gráficas de la acción). Mientras llega, el mismo hueco que dice que carga. Cierre de la v4 (Lighthouse, CLS): el hueco
// ocupa la pantalla, así lo que va detrás (el paso a la siguiente sección) no se ve hasta que llega el contenido, que
// ya no lo empuja a la vista.
const loading = () => <div className="wrap depth-body loading"><p className="missing" aria-busy="true">Cargando la sección…</p></div>;
const PAGES: Record<ChapterSlug, React.ComponentType<PageProps>> = {
  empresa: lazyWith(() => import("./Empresa"), loading),
  negocio: lazyWith(() => import("./Negocio"), loading),
  accion: lazyWith(() => import("./Accion"), loading),
  calidad: lazyWith(() => import("./Calidad"), loading),
  valor: lazyWith(() => import("./Valor"), loading),
  rivales: lazyWith(() => import("./Rivales"), loading),
  riesgos: lazyWith(() => import("./Riesgos"), loading),
  actualidad: lazyWith(() => import("./Actualidad"), loading),
  conclusion: lazyWith(() => import("./Conclusion"), loading),
};

export const PAGE_TITLES = SECTION_LABELS;

/** La lectura con la que abre la sección: su número y nombre, el título, el texto y tres cifras clave. El título recibe
 *  el foco al llegar desde otra sección (revisión V6, F7). */
function SectionIntro({ c, symbol }: { c: ChapterModel; symbol: string }) {
  return (
    <header className="wrap section-intro" data-testid="section-intro">
      <div className="eyebrow">{c.eyebrow}</div>
      <h2 tabIndex={-1} data-page-title="">{c.title}</h2>
      {c.leadFrom === "segments" ? <SegmentsLead symbol={symbol} fallback={c.lead} /> : <p className="lead">{c.lead}</p>}
      {c.figures.length > 0 && <KeyFigures figures={c.figures} />}
    </header>
  );
}

/** Una sección del análisis (V4b): su lectura, todo su detalle (cada página trae su índice en píldoras) y el paso a la
 *  siguiente. */
export default function DepthPage({ chapter, analysis, symbol, reading }: PageProps & { chapter: ChapterSlug; reading: ChapterModel }) {
  const Page = PAGES[chapter];
  const next = CHAPTER_ORDER[CHAPTER_ORDER.indexOf(chapter) + 1];
  return (
    <div className="depth" data-chapter={chapter}>
      <SectionIntro c={reading} symbol={symbol} />
      <Page analysis={analysis} symbol={symbol} />
      {next && (
        <nav className="wrap section-next" aria-label="Siguiente sección">
          <a data-nav href={chapterHref(symbol, next)} data-testid="next-section">
            <span className="eyebrow">Siguiente sección →</span> <b>{SECTION_LABELS[next]}</b></a>
        </nav>
      )}
    </div>
  );
}
