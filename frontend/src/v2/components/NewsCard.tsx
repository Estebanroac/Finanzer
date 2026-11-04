import { useState } from "react";
import type { CompanyLogoInfo } from "@/lib/api";
import type { NewsItem } from "@/v2/lib/story";
import { newsCard } from "@/v2/lib/news";
import CompanyLogo from "./CompanyLogo";

/** Tarjeta de noticia (capítulo 8). Con o sin imagen mide lo mismo: sin foto propia, el hueco de la imagen es una
 *  portada (el logotipo de la empresa y el medio sobre un degradado sobrio; sin logotipo, su placa con las iniciales),
 *  también si la foto no llega a cargar (CNBC la niega a algunos navegadores); titular y resumen enteros, así las
 *  tarjetas de una fila son iguales. `name` y `logo`: los del análisis (el logotipo versionado, o null si no hay). */
export default function NewsCard({ n, symbol, name, logo }: {
  n: NewsItem; symbol?: string; name?: string | null; logo?: CompanyLogoInfo | null;
}) {
  const c = newsCard(n);
  const [failed, setFailed] = useState(false);
  const body = (<>
    {c.image && !failed
      // eslint-disable-next-line @next/next/no-img-element -- imagen de otro dominio en un export estático: next/image necesitaría un cargador; va con loading="lazy"
      ? <img className="news-img" src={c.image.src} alt={c.image.alt} loading="lazy" referrerPolicy="no-referrer"
          onError={() => setFailed(true)} />
      : <div className="news-img news-img-empty" aria-hidden>
          {symbol && <CompanyLogo symbol={symbol} name={name} logo={logo} size="lg" className="news-ph-logo" testId="news-logo" />}
          {c.source && <span className="news-ph-src">{c.source}</span>}
        </div>}
    <div className="news-body">
      <div className="eyebrow">{c.meta}</div>
      <b className="news-title">{c.headline}{c.url && <span className="sr-only"> (se abre en una pestaña nueva)</span>}</b>
      {c.summary && <p className="news-sum muted">{c.summary}</p>}
      {c.lang && <span className="pill neutral news-lang">{c.lang}</span>}
    </div>
  </>);
  // Revisión V6 (F3, F24): con un enlace http(s), la tarjeta entera lo abre (y lo avisa a los lectores de pantalla);
  // sin enlace válido, un <article> con el mismo aspecto, no un enlace vacío.
  return c.url
    ? <a className="news-card surface" href={c.url} target="_blank" rel="noopener noreferrer">{body}</a>
    : <article className="news-card surface">{body}</article>;
}
