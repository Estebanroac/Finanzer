/**
 * Nombres de empresas conocidas para mostrar el nombre EN EL ACTO en el overlay
 * de análisis, sin esperar la respuesta del API (que llega casi al final de la
 * carga). Para el resto (búsqueda), el nombre se guarda en sessionStorage al
 * hacer clic — ver rememberName/recallName abajo — y sobrevive la hard-nav.
 */
export const STOCK_NAMES: Record<string, string> = {
  AAPL: "Apple Inc.", MSFT: "Microsoft Corporation", GOOGL: "Alphabet Inc.",
  GOOG: "Alphabet Inc.", AMZN: "Amazon.com Inc.", NVDA: "NVIDIA Corporation",
  TSLA: "Tesla Inc.", META: "Meta Platforms Inc.", JPM: "JPMorgan Chase & Co.",
  V: "Visa Inc.", MA: "Mastercard Inc.", BRK: "Berkshire Hathaway",
  "BRK-B": "Berkshire Hathaway", JNJ: "Johnson & Johnson", WMT: "Walmart Inc.",
  PG: "Procter & Gamble", KO: "The Coca-Cola Company", PEP: "PepsiCo Inc.",
  COST: "Costco Wholesale", HD: "The Home Depot", MCD: "McDonald's Corporation",
  NKE: "Nike Inc.", SBUX: "Starbucks Corporation", DIS: "The Walt Disney Company",
  NFLX: "Netflix Inc.", ADBE: "Adobe Inc.", CRM: "Salesforce Inc.",
  ORCL: "Oracle Corporation", AMD: "Advanced Micro Devices", INTC: "Intel Corporation",
  CSCO: "Cisco Systems", IBM: "IBM Corporation", QCOM: "Qualcomm Inc.",
  TXN: "Texas Instruments", AVGO: "Broadcom Inc.", TSM: "Taiwan Semiconductor",
  PYPL: "PayPal Holdings", BAC: "Bank of America", WFC: "Wells Fargo & Co.",
  GS: "Goldman Sachs", MS: "Morgan Stanley", C: "Citigroup Inc.",
  XOM: "Exxon Mobil", CVX: "Chevron Corporation", UNH: "UnitedHealth Group",
  PFE: "Pfizer Inc.", MRK: "Merck & Co.", ABBV: "AbbVie Inc.",
  LLY: "Eli Lilly and Company", T: "AT&T Inc.", VZ: "Verizon Communications",
  BA: "Boeing Company", CAT: "Caterpillar Inc.", GE: "General Electric",
  F: "Ford Motor Company", GM: "General Motors", UBER: "Uber Technologies",
  ABNB: "Airbnb Inc.", PLTR: "Palantir Technologies", COIN: "Coinbase Global",
  SHOP: "Shopify Inc.", SQ: "Block Inc.", ARM: "Arm Holdings",
  SMCI: "Super Micro Computer", MU: "Micron Technology",
};

const KEY = (t: string) => `fz:name:${t.toUpperCase()}`;

/** Recuerda el nombre de una empresa para el overlay tras la navegación. */
export function rememberName(ticker: string, name?: string | null) {
  if (typeof window === "undefined" || !name) return;
  try { sessionStorage.setItem(KEY(ticker), name); } catch { /* modo privado */ }
}

/** Nombre conocido al instante: sessionStorage (búsqueda) → mapa → null. */
export function recallName(ticker: string): string | null {
  if (!ticker) return null;
  const t = ticker.toUpperCase();
  if (typeof window !== "undefined") {
    try {
      const stored = sessionStorage.getItem(KEY(t));
      if (stored) return stored;
    } catch { /* ignore */ }
  }
  return STOCK_NAMES[t] ?? null;
}
