import type { Viewport } from "next";
import "./v2.css";

// Spec §5 (revisada): el zoom con los dedos nunca se bloquea. Viewport declarado sin maximumScale ni userScalable.
// v4 móvil: viewport-fit=cover para que env(safe-area-inset-*) tenga valor (márgenes y final de página, v2.css).
export const viewport: Viewport = { width: "device-width", initialScale: 1, viewportFit: "cover" };

// Sin parpadeo (E4 Task 4): antes de pintar, el script pone en <html> el tema guardado o, la primera vez, el del
// sistema (data-v2theme; <html> lleva suppressHydrationWarning en el layout raíz). Con él, el fondo de html y body
// y los tokens de .fz2 (v2.css) salen ya en su tema desde el primer byte, antes de que llegue el análisis.
const PAPER = `html,body{background:#F7F6F2}html[data-v2theme="dark"],html[data-v2theme="dark"] body{background:#16181B}`;
const THEME = `try{var t=localStorage.getItem("finanzer.v2.theme");if(t!=="dark"&&t!=="light")t=window.matchMedia&&matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light";document.documentElement.dataset.v2theme=t}catch(e){}`;

export default function V2Layout({ children }: { children: React.ReactNode }) {
  return (<>
    <style dangerouslySetInnerHTML={{ __html: PAPER }} />
    <script dangerouslySetInnerHTML={{ __html: THEME }} />
    {children}
  </>);
}
