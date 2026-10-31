// GENERADO por backend/tools/gen_frontend_config.py desde backend/.
// NO EDITAR A MANO: cambia el backend y vuelve a ejecutar el generador.
// tests/test_frontend_config_sync.py falla si este archivo se desincroniza.

/** Arquetipos del clasificador único (sectors.toml [archetypes.not_applicable]). */
export type Archetype = "FINANCIAL" | "REIT" | "GROWTH_PRE_PROFIT" | "CYCLICAL" | "UTILITY" | "MATURE" | "GROWTH_PROFITABLE";

/** Rótulo de cada estado de una métrica (lib/display.py STATE_LABELS). */
export const STATE_LABELS = {
  con_dato: "Con dato",
  sin_dato: "Sin dato",
  no_aplica: "No aplica",
  no_significativo: "No significativo",
} as const;

/** Bandas de las dos puntuaciones (thresholds.toml [score.quality] y [score.price]):
 *  `bands` de mayor a menor (≥), `labels` de la mejor a la peor; `confidence.labels`: niveles de
 *  confianza del veredicto del mejor al peor ([score.price] confidence_factor). Rediseño /v2.
 *  V7 (PM, el texto de los desgloses): `scale`, la escala de las dos ([score.total] max); `categories`, cuántas
 *  categorías suma la calidad; `category`, la base y el máximo de cada una ([score.category]); `neutral`, el
 *  punto hacia el que la confianza contrae el precio ([score.price] neutral). */
export const SCORE_BANDS = {
  quality: { bands: [85, 65, 45], labels: ["excelente", "sólida", "media", "débil"], categories: 4 },
  price: { bands: [65, 45, 30], labels: ["atractivo", "razonable", "exigente", "muy exigente"], neutral: 50 },
  category: { base: 10, max: 20 },
  scale: 100,
  confidence: { labels: ["alta", "media", "baja"] },
} as const;

/** La web /v2 (data.toml [web]). `analysisTimeoutMs`: cuánto espera la página al análisis antes de dar el
 *  error «tarda más de lo normal»; `loading`: el ritmo de la pantalla de carga (AnalyzeLoading). */
export const WEB = {
  analysisTimeoutMs: 120000,
  peersPollMaxMs: 600000,
  loading: {
    delayMs: 300, expectedMs: 4810, fastMs: 180, stallFill: 0.95,
    typicalS: [1.77, 4.81], exitHoldMs: 320, exitMs: 620,
    titles: ["Estados financieros de la SEC", "Precios y mercado", "Ratios frente a su industria", "Valoración: DCF y múltiplos", "Puntuaciones y veredicto"],
    labels: ["Estados SEC", "Mercado", "Ratios", "Valoración", "Veredicto"],
    phrases: ["Reuniendo los ingresos, beneficios, caja y deuda de los últimos años, contrastados con los informes oficiales.", "Trayendo la cotización y su historia, y la del mercado, para situar a la empresa.", "Comparando márgenes, rentabilidad y deuda con las empresas de su industria.", "Calculando cuánto vale el negocio por su caja futura y comparándolo con lo que paga el mercado por empresas parecidas.", "Sumando la calidad del negocio y el atractivo del precio, y midiendo cuánto fiarse del resultado."],
    stallTitle: "Últimos ajustes…",
  },
  /** Umbrales de la prueba de rendimiento (e2e/perf, V4b · 3). */
  perf: { cpuThrottle: 4, sectionChangeMs: 150, inpP75Ms: 200, longTaskMs: 100, scrollLongTaskMs: 50 },
} as const;

/** P8 (el cintillo): el nombre corto de la empresa, sin forma jurídica (names.toml [company]; backend/lib/names.py
 *  company). `samples`: lo que devuelve el backend con unos nombres de muestra (src/v2/lib/companyName.test.ts). */
export const COMPANY_NAMES = {
  suffixesCi: ["Inc.", "Inc", "Corp.", "Corp", "Corporation", "Ltd.", "Ltd", "Limited", "plc", "p.l.c."],
  suffixes: ["N.V.", "NV", "S.A.", "AG", "SE", "A S", "A/S"],
  afterComma: ["Co.", "Co", "Company", "Holdings"],
  edgarState: "\\s*/[A-Z]{0,3}/?$",
  exceptions: {"The Coca-Cola Company": "Coca-Cola", "Coca-Cola Company (The)": "Coca-Cola", "Walt Disney Company (The)": "Disney", "Hershey Company (The)": "Hershey", "Estée Lauder Companies (The)": "Estée Lauder", "Cooper Companies (The)": "Cooper Companies", "Ford Motor Company": "Ford", "Alibaba Group Holding Ltd": "Alibaba", "ARM HOLDINGS PLC /UK": "Arm", "ASML HOLDING NV": "ASML", "ASTRAZENECA PLC": "AstraZeneca", "BANCO BILBAO VIZCAYA ARGENTARIA, S.A.": "BBVA", "BARCLAYS PLC": "Barclays", "BROOKFIELD Corp /ON/": "Brookfield", "BP PLC": "BP", "British American Tobacco p.l.c.": "British American Tobacco", "CANADIAN NATURAL RESOURCES Ltd": "Canadian Natural Resources", "DIAGEO PLC": "Diageo", "ENBRIDGE INC": "Enbridge", "HDFC BANK LTD": "HDFC Bank", "HSBC HOLDINGS PLC": "HSBC", "ICICI BANK LTD": "ICICI Bank", "ING GROEP NV": "ING", "MERCADOLIBRE INC": "MercadoLibre", "MITSUBISHI UFJ FINANCIAL GROUP INC": "Mitsubishi UFJ Financial Group", "NOVO NORDISK A S": "Novo Nordisk", "NOVARTIS AG": "Novartis", "RIO TINTO PLC": "Rio Tinto", "ROYAL BANK OF CANADA": "Royal Bank of Canada", "SHOPIFY INC.": "Shopify", "SUMITOMO MITSUI FINANCIAL GROUP, INC.": "Sumitomo Mitsui Financial Group", "TORONTO DOMINION BANK": "Toronto-Dominion Bank", "TOYOTA MOTOR CORP/": "Toyota", "TAIWAN SEMICONDUCTOR MANUFACTURING CO LTD": "TSMC", "UNILEVER PLC": "Unilever"},
  samples: {"ARM HOLDINGS PLC /UK": "Arm", "ASML HOLDING NV": "ASML", "ASTRAZENECA PLC": "AstraZeneca", "Alibaba Group Holding Ltd": "Alibaba", "Alphabet Inc. Class A": "Alphabet", "Apple Inc.": "Apple", "BANCO BILBAO VIZCAYA ARGENTARIA, S.A.": "BBVA", "BARCLAYS PLC": "Barclays", "BP PLC": "BP", "BROOKFIELD Corp /ON/": "Brookfield", "Berkshire Hathaway Inc.": "Berkshire Hathaway", "British American Tobacco p.l.c.": "British American Tobacco", "CANADIAN NATURAL RESOURCES Ltd": "Canadian Natural Resources", "Coca-Cola Company (The)": "Coca-Cola", "Cooper Companies (The)": "Cooper Companies", "DIAGEO PLC": "Diageo", "Deere & Company": "Deere & Company", "ENBRIDGE INC": "Enbridge", "Estée Lauder Companies (The)": "Estée Lauder", "Foo, Holdings": "Foo", "Ford Motor Company": "Ford", "HDFC BANK LTD": "HDFC Bank", "HSBC HOLDINGS PLC": "HSBC", "Hershey Company (The)": "Hershey", "Home Depot (The)": "Home Depot", "ICICI BANK LTD": "ICICI Bank", "ING GROEP NV": "ING", "Inc.": "Inc.", "JPMorgan Chase & Co.": "JPMorgan Chase & Co.", "LVMH Moët Hennessy - Louis Vuitton, Société Européenne": "LVMH Moët Hennessy - Louis Vuitton, Société Européenne", "MERCADOLIBRE INC": "MercadoLibre", "MITSUBISHI UFJ FINANCIAL GROUP INC": "Mitsubishi UFJ Financial Group", "Microsoft Corporation": "Microsoft", "NOVARTIS AG": "Novartis", "NOVO NORDISK A S": "Novo Nordisk", "NVIDIA Corporation": "NVIDIA", "Novo Nordisk A/S": "Novo Nordisk A", "Procter & Gamble Company (The)": "Procter & Gamble Company", "RIO TINTO PLC": "Rio Tinto", "ROYAL BANK OF CANADA": "Royal Bank of Canada", "Realty Income Corporation": "Realty Income", "SAP SE": "SAP", "SHOPIFY INC.": "Shopify", "SUMITOMO MITSUI FINANCIAL GROUP, INC.": "Sumitomo Mitsui Financial Group", "Shell plc": "Shell", "Siemens AG": "Siemens", "TAIWAN SEMICONDUCTOR MANUFACTURING CO LTD": "TSMC", "TORONTO DOMINION BANK": "Toronto-Dominion Bank", "TOYOTA MOTOR CORP/": "Toyota", "Taiwan Semiconductor Manufacturing Company Limited": "Taiwan Semiconductor Manufacturing Company", "Tesla, Inc.": "Tesla", "The Coca-Cola Company": "Coca-Cola", "UNILEVER PLC": "Unilever", "Unilever PLC": "Unilever", "Walt Disney Company (The)": "Disney"},
} as const;
