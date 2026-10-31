"use client";
import { lazy, Suspense, useState, type ComponentType, type ReactNode } from "react";

/** Cargas de todos los fragmentos registrados (para descargarlos en segundo plano: `preloadLazy`). */
const registry: Array<() => Promise<unknown>> = [];

/** Revisión V6 (F13): un componente en su propio fragmento (import() dinámico) con su esqueleto mientras llega.
 *  React.lazy y no next/dynamic: anidado dentro de otro next/dynamic (V2Entry → StoryPageClient), next/dynamic hace
 *  que `next dev` (Turbopack) precargue en el HTML un fragmento que nunca genera (404 en la consola). Las páginas y
 *  las gráficas no se pintan al prerenderizar (no hay datos), así que no hace falta el SSR de next/dynamic.
 *  V4b · 3 (sin lag, medido): un fragmento ya descargado se pinta directo, sin Suspense. Con Suspense, React 19 retiene
 *  el contenido ~300 ms tras enseñar el esqueleto (su «throttle» de fallbacks): cada sección tardaba ~330 ms en llegar la
 *  primera vez aunque su fragmento llegara en 1 ms. */
export function lazyWith<P extends object>(load: () => Promise<{ default: ComponentType<P> }>, fallback: () => ReactNode): ComponentType<P> {
  let loaded: ComponentType<P> | null = null;
  const preload = () => load().then((m) => { loaded = m.default; return m; });
  registry.push(preload);
  const L = lazy(preload);
  function Lazy(props: P) {
    // Lo que había al montar (no cambia luego: pasar de Suspense a directo remontaría el componente y perdería su estado)
    const [Direct] = useState<ComponentType<P> | null>(() => loaded);
    if (Direct) return <Direct {...props} />;
    return <Suspense fallback={fallback()}><L {...props} /></Suspense>;
  }
  return Lazy;
}

/** Descarga en segundo plano todos los fragmentos registrados, también los que registran los que llegan (las gráficas
 *  de una sección), para que cambiar de sección no espere a la red ni a Suspense. */
export async function preloadLazy(): Promise<void> {
  let done = 0;
  while (done < registry.length) {
    const batch = registry.slice(done);
    done = registry.length;
    await Promise.allSettled(batch.map((p) => p()));
  }
}
