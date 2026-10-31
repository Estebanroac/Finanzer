/** V7 (puntuación): el motor ya cierra sus frases (backend/lib/prose.py); aquí solo se cierra lo que llega sin cerrar,
 *  para no producir «..». */
export function closeSentence(t: string): string {
  return /[.)»…?!]$/.test(t.trimEnd()) ? t.trimEnd() : `${t.trimEnd()}.`;
}
