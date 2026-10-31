import V2Entry from "./V2Entry";

/** Rediseño E4: la portada es /v2 sin símbolo. Next no admite src/app/v2/page.tsx junto a esta ruta opcional
 *  ([[...symbol]] ya cubre /v2), así que se elige aquí. El export genera dos HTML: out/v2/index.html (la portada) y
 *  out/v2/{STORY_SHELL}/index.html (la historia y las páginas de profundidad: leen el símbolo de la URL), que el
 *  backend sirve para /v2/{T} y /v2/{T}/{capítulo}. */
const STORY_SHELL = "_";

export async function generateStaticParams() {
  return [{ symbol: [] }, { symbol: [STORY_SHELL] }];
}

export default async function V2Page({ params }: { params: Promise<{ symbol?: string[] }> }) {
  const { symbol } = await params;
  return <V2Entry home={!symbol || symbol.length === 0} />;
}
