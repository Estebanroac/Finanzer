import { useEffect } from "react";

/** Revisión V6 (F7): título de la pestaña. Next pone el de los metadatos («Finanzer») tras hidratar, a veces después de
 *  este efecto: si lo cambia, se vuelve a poner el nuestro (observando el <head>). */
export function useDocumentTitle(title: string): void {
  useEffect(() => {
    document.title = title;
    const mo = new MutationObserver(() => { if (document.title !== title) document.title = title; });
    mo.observe(document.head, { childList: true, characterData: true, subtree: true });
    return () => mo.disconnect();
  }, [title]);
}
