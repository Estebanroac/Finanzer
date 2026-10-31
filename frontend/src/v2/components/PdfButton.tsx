"use client";
import { useEffect, useRef, useState } from "react";
import { pdfV2Url } from "@/lib/api";
import { WEB } from "@/lib/generated/backendConfig";
import { pdfFilename, pdfStatusText, type PdfState } from "@/v2/lib/pdfDownload";

/** «Descargar PDF» (PDF rápido). Sigue siendo un enlace al PDF (funciona sin JavaScript y con «abrir en otra pestaña»),
 *  pero al pulsarlo la web lo pide ella: el botón pasa a «Preparando el PDF…», un aviso dice por qué tarda (las
 *  comparables) y el archivo se descarga solo al llegar. La página no se bloquea. Si el PDF llega antes de
 *  `loading.delayMs` (ya estaba todo), el aviso no llega a salir. */
export default function PdfButton({ symbol, testId }: { symbol: string; testId?: string }) {
  const url = pdfV2Url(symbol);
  const [state, setState] = useState<PdfState>({ kind: "idle" });
  const [shown, setShown] = useState(false);
  const busy = useRef(false);
  const alive = useRef(true);
  useEffect(() => () => { alive.current = false; }, []);

  const onClick = async (e: React.MouseEvent<HTMLAnchorElement>) => {
    if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button !== 0) return;   // otra pestaña: el enlace
    e.preventDefault();
    if (busy.current) return;
    busy.current = true;
    setState({ kind: "preparing" });
    const timer = setTimeout(() => setShown(true), WEB.loading.delayMs);
    try {
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const blob = await res.blob();
      const href = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = href;
      a.download = pdfFilename(res.headers.get("content-disposition"), symbol);
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(href), 0);
      if (alive.current) setState({ kind: "idle" });
    } catch (err) {
      if (alive.current) setState({ kind: "error", reason: err instanceof Error ? err.message : "error de red" });
    } finally {
      clearTimeout(timer);
      busy.current = false;
      if (alive.current) setShown(false);
    }
  };

  const preparing = state.kind === "preparing";
  const text = pdfStatusText(symbol, state);
  return (
    <>
      <a className={`btn pdf-btn${preparing ? " preparing" : ""}`} href={url} onClick={onClick}
        aria-busy={preparing || undefined} data-testid={testId} data-state={state.kind}>
        {preparing && <span className="pdf-spin" aria-hidden="true" />}
        {preparing ? "Preparando el PDF…" : "Descargar PDF"}
      </a>
      {/* El aviso: siempre en el DOM (aria-live solo anuncia cambios de una región que ya existe); visible cuando
          tarda o falla. */}
      <span className={`pdf-status${(preparing && shown) || state.kind === "error" ? " on" : ""}`} role="status"
        aria-live="polite" data-testid={`${testId ?? "pdf-top"}-status`}>{text}</span>
    </>
  );
}
