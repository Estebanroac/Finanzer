/** PDF rápido: la descarga del informe desde la web. El primer PDF de una empresa espera a sus comparables (el servidor
 *  las calcula al servir el análisis, F10 · N5): mientras tanto el botón dice que se está preparando y por qué, y la
 *  descarga sale sola al terminar. Aquí, la parte pura (nombre del archivo y textos). */

export type PdfState = { kind: "idle" } | { kind: "preparing" } | { kind: "error"; reason: string };

/** El nombre que da el servidor (Content-Disposition) o, sin él, «Informe Finanzer HD.pdf». */
export function pdfFilename(disposition: string | null, symbol: string): string {
  const m = /filename\*?=(?:UTF-8'')?"?([^";]+)"?/i.exec(disposition ?? "");
  if (m) {
    try {
      return decodeURIComponent(m[1]);
    } catch {
      return m[1];
    }
  }
  return `Informe Finanzer ${symbol}.pdf`;
}

/** Lo que dice el estado, visible y para lectores de pantalla. */
export function pdfStatusText(symbol: string, s: PdfState): string {
  if (s.kind === "preparing") {
    return `Preparando el PDF de ${symbol}: espera a que estén las comparables de su industria. Se descargará solo.`;
  }
  if (s.kind === "error") return `No se pudo preparar el PDF de ${symbol} (${s.reason}). Vuelve a intentarlo.`;
  return "";
}
