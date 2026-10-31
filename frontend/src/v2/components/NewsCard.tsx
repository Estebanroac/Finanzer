import type { NewsItem } from "@/v2/lib/story";
import { newsCard } from "@/v2/lib/news";

/** Tarjeta de noticia (capítulo 8). Con o sin imagen mide lo mismo: sin imagen, el hueco de la imagen lleva el medio
 *  sobre el fondo neutro; titular y resumen con un número fijo de líneas, así las tarjetas de una fila son iguales. */
export default function NewsCard({ n }: { n: NewsItem }) {
  const c = newsCard(n);
  const body = (<>
    {c.image
      // eslint-disable-next-line @next/next/no-img-element -- imagen de otro dominio en un export estático: next/image necesitaría un cargador; va con loading="lazy"
      ? <img className="news-img" src={c.image.src} alt={c.image.alt} loading="lazy" referrerPolicy="no-referrer" />
      : <div className="news-img news-img-empty" aria-hidden><span>{n.source ?? ""}</span></div>}
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
