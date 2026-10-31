/**
 * Las tres tarjetas de confianza de la portada (maqueta 5). Textos tomados de la metodología del motor, no inventados:
 *  · Datos oficiales: backend/lib/sec_edgar.py («SEC EDGAR en el camino del análisis: verificación y respaldo») y
 *    lib/edgar_backup.py (respalda con EDGAR lo que Yahoo no da del mismo corte).
 *  · Método por tipo de empresa: backend/lib/display.py, methodology.models (bancos: P/B y P/TBV justificados por el
 *    retorno; REIT: P/FFO; eléctricas: P/E frente al sector).
 *  · Honestidad con la incertidumbre: la confianza de cada veredicto (alta, media o baja) y el atractivo del precio
 *    contraído hacia 50 según esa confianza (metodología de la web actual, StockPageClient).
 */
export interface TrustCard { title: string; text: string }

export const TRUST_CARDS: TrustCard[] = [
  {
    title: "Datos oficiales de la SEC",
    text: "Las cifras de los estados financieros se verifican con los informes que la empresa presenta a la SEC (EDGAR), " +
      "que también cubren lo que falta en los datos de mercado.",
  },
  {
    title: "Método por tipo de empresa",
    text: "Un banco no se valora como Apple: se usan P/B y P/TBV justificados por su retorno; un REIT, el P/FFO; " +
      "una eléctrica, su P/E frente al sector.",
  },
  {
    title: "Honesto con la incertidumbre",
    text: "Cada veredicto lleva su confianza (alta, media o baja) y, cuanto menor es, más se acerca a 50 la puntuación " +
      "del precio.",
  },
];
