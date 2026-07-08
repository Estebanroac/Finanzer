import { TooltipContent } from "@/components/InfoTooltip";

// ─── SCORE GENERAL ──────────────────────────────────────
export const SCORE_TOOLTIP: TooltipContent = {
  title: "Score General",
  description:
    "Puntuacion compuesta de 0 a 100 que evalua la salud financiera global de la empresa. Combina metricas de valoracion, rentabilidad, solidez financiera, crecimiento y calidad de ganancias.",
  thresholds: [
    { label: "Excelente — empresa muy solida", value: "80–100", color: "#0cc06c" },
    { label: "Favorable — buena inversion potencial", value: "60–79", color: "#22c55e" },
    { label: "Neutral — riesgo moderado", value: "40–59", color: "#fbbf24" },
    { label: "Precaucion — debilidades importantes", value: "20–39", color: "#f97316" },
    { label: "Evitar — riesgo alto", value: "0–19", color: "#ff4d4d" },
  ],
  tip: "El score es una guia, no una recomendacion. Siempre analiza los detalles de cada categoria.",
};

// ─── METRICAS CLAVE (MetricsGrid) ───────────────────────
export const METRICS: Record<string, TooltipContent> = {
  sector_benchmark: {
    title: "Comparación vs Sector",
    description: "El punto de color y la flecha comparan el valor de la empresa con la MEDIANA de su sector. Verde = mejor que el sector; rojo = peor; ámbar = en línea (dentro de ±10%).",
    tip: "Un P/E de 30 puede ser caro en un banco pero barato en tecnología — por eso cada métrica se compara contra su sector, no contra un número fijo.",
  },
  market_cap: {
    title: "Capitalizacion de Mercado",
    description: "Valor total de la empresa en bolsa. Se calcula multiplicando el precio actual por el numero de acciones en circulacion.",
    formula: "Precio × Acciones en circulacion",
    thresholds: [
      { label: "Mega cap", value: ">200B", color: "#3b82f6" },
      { label: "Large cap", value: "10B–200B", color: "#22c55e" },
      { label: "Mid cap", value: "2B–10B", color: "#fbbf24" },
      { label: "Small cap", value: "<2B", color: "#f97316" },
    ],
    tip: "Empresas mas grandes tienden a ser mas estables pero con menor potencial de crecimiento explosivo.",
  },
  pe_ratio: {
    title: "P/E Ratio (Precio/Beneficio)",
    description: "Indica cuanto pagan los inversores por cada dolar de ganancia. Un P/E alto puede significar expectativas de crecimiento, o que la accion esta cara.",
    formula: "Precio / Ganancia por Accion (EPS)",
    thresholds: [
      { label: "Posiblemente barata", value: "<15", color: "#0cc06c" },
      { label: "Valoracion justa", value: "15–25", color: "#fbbf24" },
      { label: "Cara / alto crecimiento", value: ">25", color: "#f97316" },
    ],
    good: "P/E bajo con ganancias estables puede indicar oportunidad de compra.",
    bad: "P/E muy alto sin crecimiento que lo justifique sugiere sobrevaloracion.",
    tip: "Compara siempre el P/E con el promedio del sector. Un P/E de 30 puede ser barato en tech pero caro en utilities.",
  },
  roe: {
    title: "ROE (Return on Equity)",
    description: "Mide que tan eficientemente la empresa genera ganancias con el dinero de los accionistas. Es uno de los indicadores favoritos de Warren Buffett.",
    formula: "Ingreso Neto / Patrimonio de Accionistas",
    thresholds: [
      { label: "Excelente", value: ">20%", color: "#0cc06c" },
      { label: "Bueno", value: "15–20%", color: "#22c55e" },
      { label: "Aceptable", value: "10–15%", color: "#fbbf24" },
      { label: "Bajo", value: "<10%", color: "#ff4d4d" },
    ],
    good: "ROE alto sostenido indica ventaja competitiva duradera.",
    bad: "ROE alto por exceso de deuda es peligroso — revisa el D/E.",
    tip: "Un ROE alto con deuda baja es la combinacion ideal.",
  },
  de_ratio: {
    title: "D/E (Deuda/Patrimonio)",
    description: "Compara la deuda total con el patrimonio de los accionistas. Indica cuanto depende la empresa de dinero prestado vs dinero propio.",
    formula: "Deuda Total / Patrimonio",
    thresholds: [
      { label: "Conservador", value: "<0.5", color: "#0cc06c" },
      { label: "Moderado", value: "0.5–1.0", color: "#fbbf24" },
      { label: "Apalancado", value: "1.0–2.0", color: "#f97316" },
      { label: "Muy endeudado", value: ">2.0", color: "#ff4d4d" },
    ],
    good: "D/E bajo significa que la empresa se financia mas con recursos propios.",
    bad: "D/E muy alto aumenta el riesgo en recesiones o alzas de tasas de interes.",
    tip: "Los bancos y REITs naturalmente tienen D/E altos — compara dentro del mismo sector.",
  },
  net_margin: {
    title: "Margen Neto",
    description: "Porcentaje de cada dolar de ventas que se convierte en ganancia final despues de TODOS los gastos, impuestos e intereses.",
    formula: "Ingreso Neto / Ingresos Totales × 100",
    thresholds: [
      { label: "Excelente", value: ">20%", color: "#0cc06c" },
      { label: "Bueno", value: "10–20%", color: "#22c55e" },
      { label: "Aceptable", value: "5–10%", color: "#fbbf24" },
      { label: "Bajo", value: "<5%", color: "#ff4d4d" },
    ],
    good: "Margenes altos sugieren poder de precios y eficiencia operativa.",
    bad: "Margenes bajos o negativos indican presion competitiva o problemas de costos.",
  },
  fcf_yield: {
    title: "FCF Yield (Rendimiento de Flujo Libre)",
    description: "Mide cuanto flujo de caja libre genera la empresa en relacion a su valor de mercado. Es como el 'rendimiento real' de la empresa.",
    formula: "Flujo de Caja Libre / Capitalizacion de Mercado × 100",
    thresholds: [
      { label: "Muy atractivo", value: ">8%", color: "#0cc06c" },
      { label: "Atractivo", value: "5–8%", color: "#22c55e" },
      { label: "Moderado", value: "3–5%", color: "#fbbf24" },
      { label: "Bajo", value: "<3%", color: "#f97316" },
    ],
    good: "FCF Yield alto indica que la empresa genera mucho efectivo real para su tamano.",
    bad: "FCF Yield bajo puede significar que la accion esta cara o que la empresa reinvierte todo.",
    tip: "Muchos inversores de valor prefieren FCF Yield sobre P/E porque el flujo de caja es mas dificil de manipular que las ganancias.",
  },
  ev_ebitda: {
    title: "EV/EBITDA",
    description: "Compara el valor total de la empresa (incluyendo deuda) con sus ganancias operativas antes de intereses, impuestos, depreciacion y amortizacion. Es mas completo que el P/E.",
    formula: "Enterprise Value / EBITDA",
    thresholds: [
      { label: "Posiblemente barata", value: "<10", color: "#0cc06c" },
      { label: "Valoracion justa", value: "10–15", color: "#fbbf24" },
      { label: "Cara", value: "15–20", color: "#f97316" },
      { label: "Muy cara", value: ">20", color: "#ff4d4d" },
    ],
    good: "EV/EBITDA bajo con negocio estable puede ser oportunidad de compra.",
    bad: "EV/EBITDA muy alto sin crecimiento rapido sugiere sobrevaloracion.",
    tip: "EV/EBITDA es preferido por analistas profesionales porque incluye la deuda y ignora diferencias contables entre paises.",
  },
  beta: {
    title: "Beta (Volatilidad)",
    description: "Mide la volatilidad de la accion comparada con el mercado (S&P 500 = 1.0). Indica cuanto se mueve la accion cuando el mercado sube o baja.",
    formula: "Covarianza(Accion, Mercado) / Varianza(Mercado)",
    thresholds: [
      { label: "Muy estable (defensiva)", value: "<0.8", color: "#3b82f6" },
      { label: "Similar al mercado", value: "0.8–1.2", color: "#22c55e" },
      { label: "Mas volatil", value: "1.2–1.5", color: "#fbbf24" },
      { label: "Muy volatil", value: ">1.5", color: "#ff4d4d" },
    ],
    good: "Beta bajo = menos volatilidad, ideal para inversores conservadores.",
    bad: "Beta alto = la accion puede caer mucho mas que el mercado en correcciones.",
    tip: "Beta mide riesgo de mercado, no riesgo de la empresa. Una empresa mala puede tener beta bajo si no se mueve.",
  },
};

// ─── VALORACION (ValuationTab) ──────────────────────────
export const VALUATION: Record<string, TooltipContent> = {
  earnings_yield: {
    title: "Earnings Yield (Rendimiento de Ganancias)",
    description: "Cuánto genera la empresa en beneficios por cada dólar invertido al precio actual. Es el inverso del P/E, expresado como porcentaje.",
    formula: "Ganancia por Acción / Precio × 100  (= 1 / P/E)",
    thresholds: [
      { label: "Atractivo", value: ">6%", color: "#0cc06c" },
      { label: "Razonable", value: "4–6%", color: "#22c55e" },
      { label: "Moderado", value: "2–4%", color: "#fbbf24" },
      { label: "Bajo", value: "<2%", color: "#f97316" },
    ],
    tip: "Compáralo con el rendimiento de un bono del tesoro: si el earnings yield es menor, el activo 'sin riesgo' paga más y la acción luce cara.",
  },
  buyback_yield: {
    title: "Buyback Yield (Recompra de Acciones)",
    description: "Porcentaje de acciones que la empresa recompró en el último año. Recomprar reduce el número de acciones y aumenta tu participación en las ganancias.",
    formula: "(Acciones año previo − Acciones actuales) / Acciones año previo × 100",
    thresholds: [
      { label: "Recompra fuerte", value: ">3%", color: "#0cc06c" },
      { label: "Recompra moderada", value: "0.5–3%", color: "#22c55e" },
      { label: "Neutral", value: "0–0.5%", color: "#9ca3af" },
      { label: "Dilución (emite acciones)", value: "<0%", color: "#ff4d4d" },
    ],
    good: "Recompras sostenidas con la acción barata crean valor para el accionista.",
    bad: "Buyback negativo = la empresa emite más acciones y diluye tu participación.",
    tip: "Cuidado con recompras a precios altos: destruyen valor aunque suban el EPS.",
  },
  shareholder_yield: {
    title: "Shareholder Yield (Retorno Total al Accionista)",
    description: "Todo el efectivo que la empresa te devuelve: dividendos más recompras netas de acciones. Es la visión completa del retorno de capital.",
    formula: "Dividend Yield + Buyback Yield",
    thresholds: [
      { label: "Alto retorno", value: ">5%", color: "#0cc06c" },
      { label: "Bueno", value: "2–5%", color: "#22c55e" },
      { label: "Bajo", value: "0–2%", color: "#fbbf24" },
      { label: "Dilución neta", value: "<0%", color: "#ff4d4d" },
    ],
    tip: "Combina lo mejor de dividendos y recompras: mide el retorno de capital total, no solo el dividendo.",
  },
  pe_trailing: {
    title: "P/E Trailing (TTM)",
    description: "Precio actual dividido por las ganancias de los ultimos 12 meses. Refleja lo que ya paso.",
    formula: "Precio / EPS (ultimos 12 meses)",
    thresholds: [
      { label: "Posible oportunidad", value: "<15", color: "#0cc06c" },
      { label: "Valoracion justa", value: "15–25", color: "#fbbf24" },
      { label: "Premium", value: ">25", color: "#f97316" },
    ],
    tip: "Util para empresas maduras con ganancias estables. Menos util para empresas de alto crecimiento.",
  },
  pe_forward: {
    title: "P/E Forward",
    description: "Precio actual dividido por las ganancias ESTIMADAS para los proximos 12 meses. Refleja expectativas del mercado.",
    formula: "Precio / EPS estimado (proximo ano)",
    good: "Si el Forward P/E es menor que el Trailing P/E, el mercado espera crecimiento.",
    bad: "Si es mayor que el Trailing, el mercado espera caida de ganancias.",
    tip: "Compara Forward vs Trailing para ver si los analistas esperan mejora o deterioro.",
  },
  pb: {
    title: "P/B (Precio/Valor en Libros)",
    description: "Compara el precio de mercado con el valor contable de la empresa. Un P/B de 1 significa que pagas exactamente lo que vale en libros.",
    formula: "Precio / (Patrimonio / Acciones)",
    thresholds: [
      { label: "Descuento vs libros", value: "<1", color: "#0cc06c" },
      { label: "Cerca de valor en libros", value: "1–3", color: "#fbbf24" },
      { label: "Prima significativa", value: ">3", color: "#f97316" },
    ],
    tip: "Mas util para bancos y empresas intensivas en capital. Menos util para tech (muchos intangibles).",
  },
  ps: {
    title: "P/S (Precio/Ventas)",
    description: "Precio de mercado dividido por los ingresos por accion. Util para empresas sin ganancias que aun generan ventas.",
    formula: "Capitalizacion / Ingresos Totales",
    thresholds: [
      { label: "Atractivo", value: "<2", color: "#0cc06c" },
      { label: "Razonable", value: "2–5", color: "#fbbf24" },
      { label: "Caro", value: ">5", color: "#f97316" },
    ],
    tip: "Muy usado para evaluar startups y empresas tech que reinvierten todo y aun no dan ganancias.",
  },
  peg: {
    title: "PEG Ratio",
    description: "Ajusta el P/E por la tasa de crecimiento de ganancias. Un PEG de 1 significa que pagas un precio justo por el crecimiento.",
    formula: "P/E / Tasa de Crecimiento de Ganancias (%)",
    thresholds: [
      { label: "Subvalorada para su crecimiento", value: "<1", color: "#0cc06c" },
      { label: "Valoracion justa", value: "1–1.5", color: "#fbbf24" },
      { label: "Cara para su crecimiento", value: ">1.5", color: "#f97316" },
    ],
    good: "PEG < 1 es la senal clasica de Peter Lynch para encontrar oportunidades.",
    bad: "PEG > 2 sugiere que estas pagando demasiado por el crecimiento esperado.",
    tip: "El PEG depende de estimaciones futuras — si el crecimiento no se materializa, el PEG real sera mayor.",
  },
  ev_ebitda: {
    title: "EV/EBITDA",
    description: "Enterprise Value dividido por EBITDA. Mide cuantos anos de ganancias operativas necesitas para pagar toda la empresa (incluyendo deuda).",
    formula: "Enterprise Value / EBITDA",
    thresholds: [
      { label: "Posiblemente barata", value: "<10", color: "#0cc06c" },
      { label: "Valoracion justa", value: "10–15", color: "#fbbf24" },
      { label: "Cara", value: ">15", color: "#f97316" },
    ],
    tip: "Preferido sobre P/E por analistas institucionales porque es neutral a la estructura de capital.",
  },
  pfcf: {
    title: "P/FCF (Precio/Flujo de Caja Libre)",
    description: "Precio dividido por el flujo de caja libre por accion. Mide cuanto pagas por cada dolar de efectivo real que genera la empresa.",
    formula: "Capitalizacion / Flujo de Caja Libre",
    thresholds: [
      { label: "Atractivo", value: "<15", color: "#0cc06c" },
      { label: "Razonable", value: "15–25", color: "#fbbf24" },
      { label: "Caro", value: ">25", color: "#f97316" },
    ],
    tip: "El FCF es el dinero real que queda despues de operar y mantener el negocio — mas confiable que las ganancias contables.",
  },
  fcf_yield_val: {
    title: "FCF Yield",
    description: "Rendimiento del flujo de caja libre. Es el inverso del P/FCF expresado como porcentaje.",
    formula: "FCF / Capitalizacion × 100",
    thresholds: [
      { label: "Muy atractivo", value: ">8%", color: "#0cc06c" },
      { label: "Atractivo", value: "5–8%", color: "#22c55e" },
      { label: "Moderado", value: "3–5%", color: "#fbbf24" },
      { label: "Bajo", value: "<3%", color: "#f97316" },
    ],
    tip: "Piensalo como el 'interes' que te paga la empresa con su generacion de caja.",
  },
  dividend_yield: {
    title: "Dividend Yield",
    description: "Porcentaje del precio que la empresa te devuelve anualmente en dividendos.",
    formula: "Dividendo Anual por Accion / Precio × 100",
    thresholds: [
      { label: "Alto rendimiento", value: ">4%", color: "#0cc06c" },
      { label: "Moderado", value: "2–4%", color: "#22c55e" },
      { label: "Bajo", value: "1–2%", color: "#fbbf24" },
      { label: "Minimo o sin dividendo", value: "<1%", color: "#9ca3af" },
    ],
    good: "Dividendos estables y crecientes indican empresa madura y confiable.",
    bad: "Dividend Yield extremadamente alto (>8%) puede ser trampa — la empresa puede recortarlo.",
    tip: "Empresas tech de crecimiento como NVDA y AMZN rara vez pagan dividendos significativos — reinvierten en el negocio.",
  },
};

// ─── RENTABILIDAD (ProfitabilityTab) ────────────────────
export const PROFITABILITY: Record<string, TooltipContent> = {
  roic_wacc_spread: {
    title: "ROIC − WACC (Creación de Valor)",
    description: "La diferencia entre lo que la empresa GANA sobre su capital (ROIC) y lo que le CUESTA ese capital (WACC). Si es positivo, crea valor; si es negativo, lo destruye.",
    formula: "ROIC − WACC  (en puntos porcentuales)",
    thresholds: [
      { label: "Crea mucho valor", value: ">5%", color: "#0cc06c" },
      { label: "Crea valor", value: "0–5%", color: "#22c55e" },
      { label: "Marginal", value: "−5–0%", color: "#fbbf24" },
      { label: "Destruye valor", value: "<−5%", color: "#ff4d4d" },
    ],
    good: "Un spread positivo y creciente es la firma de un negocio con ventaja competitiva duradera.",
    bad: "Spread negativo: la empresa ganaría más repartiendo el dinero que reinvirtiéndolo.",
    tip: "Para muchos inversores es el indicador DEFINITIVO de calidad: ganar más que el costo de capital crea riqueza real.",
  },
  wacc: {
    title: "WACC (Costo de Capital)",
    description: "El costo promedio ponderado del capital: la rentabilidad mínima que la empresa debe generar para no destruir valor. Es la 'valla' que sus retornos deben superar.",
    formula: "Costo de deuda × %deuda + Costo del patrimonio × %patrimonio",
    tip: "Suele estar entre 7% y 11%. Sirve como tasa de descuento en el DCF y como referencia para el ROIC.",
  },
  roe: {
    title: "ROE (Return on Equity)",
    description: "Retorno sobre el patrimonio. Mide cuantos centavos de ganancia genera la empresa por cada dolar que los accionistas han invertido.",
    formula: "Ingreso Neto / Patrimonio × 100",
    thresholds: [
      { label: "Excelente", value: ">20%", color: "#0cc06c" },
      { label: "Bueno", value: "15–20%", color: "#22c55e" },
      { label: "Aceptable", value: "10–15%", color: "#fbbf24" },
      { label: "Bajo", value: "<10%", color: "#ff4d4d" },
    ],
    tip: "Warren Buffett busca ROE consistentemente >15% durante 10+ anos.",
  },
  roa: {
    title: "ROA (Return on Assets)",
    description: "Retorno sobre activos. Mide la eficiencia de la empresa para generar ganancias con todos sus recursos (propios y prestados).",
    formula: "Ingreso Neto / Activos Totales × 100",
    thresholds: [
      { label: "Excelente", value: ">15%", color: "#0cc06c" },
      { label: "Bueno", value: "8–15%", color: "#22c55e" },
      { label: "Aceptable", value: "5–8%", color: "#fbbf24" },
      { label: "Bajo", value: "<5%", color: "#ff4d4d" },
    ],
    tip: "ROA es mas confiable que ROE para comparar empresas con diferente nivel de deuda.",
  },
  roic: {
    title: "ROIC (Return on Invested Capital)",
    description: "Retorno sobre el capital invertido. Mide que tan bien la empresa usa TODO el capital (propio + deuda) para generar ganancias despues de impuestos.",
    formula: "NOPAT / (Patrimonio + Deuda a Largo Plazo)",
    thresholds: [
      { label: "Crea valor (supera costo de capital)", value: ">12%", color: "#0cc06c" },
      { label: "Aceptable", value: "8–12%", color: "#fbbf24" },
      { label: "Destruye valor", value: "<8%", color: "#ff4d4d" },
    ],
    good: "ROIC > WACC (tipicamente 8-10%) significa que la empresa crea valor para accionistas.",
    bad: "ROIC < costo de capital destruye valor — seria mejor repartir el dinero.",
    tip: "ROIC es considerado por muchos como el indicador MAS importante de calidad empresarial.",
  },
  eps: {
    title: "EPS (Ganancia por Accion)",
    description: "Cuanto gana la empresa por cada accion en circulacion. Es la base para calcular el P/E.",
    formula: "Ingreso Neto / Acciones en Circulacion",
    good: "EPS creciente de forma consistente indica negocio saludable.",
    bad: "EPS decreciente o negativo indica problemas de rentabilidad.",
    tip: "Busca empresas con EPS creciendo al menos 10% anual durante 5+ anos.",
  },
  gross_margin: {
    title: "Margen Bruto",
    description: "Porcentaje de ventas que queda despues de pagar el costo directo de los productos/servicios. Mide el poder de precios basico.",
    formula: "(Ingresos - Costo de Ventas) / Ingresos × 100",
    thresholds: [
      { label: "Excelente (software/tech)", value: ">70%", color: "#0cc06c" },
      { label: "Bueno", value: "40–70%", color: "#22c55e" },
      { label: "Moderado (manufactura)", value: "20–40%", color: "#fbbf24" },
      { label: "Bajo (retail/commodities)", value: "<20%", color: "#f97316" },
    ],
    tip: "Margenes brutos altos y estables sugieren ventaja competitiva (marca, patentes, efecto red).",
  },
  operating_margin: {
    title: "Margen Operativo",
    description: "Porcentaje de ventas que queda despues de todos los gastos operativos (incluyendo salarios, investigacion, marketing, etc.).",
    formula: "Ingreso Operativo / Ingresos × 100",
    thresholds: [
      { label: "Excelente", value: ">25%", color: "#0cc06c" },
      { label: "Bueno", value: "15–25%", color: "#22c55e" },
      { label: "Aceptable", value: "10–15%", color: "#fbbf24" },
      { label: "Bajo", value: "<10%", color: "#ff4d4d" },
    ],
    tip: "La diferencia entre margen bruto y operativo revela cuanto gasta la empresa en operar.",
  },
  net_margin: {
    title: "Margen Neto",
    description: "Porcentaje final de cada dolar de ventas que se convierte en ganancia neta despues de TODOS los gastos.",
    formula: "Ingreso Neto / Ingresos × 100",
    thresholds: [
      { label: "Excelente", value: ">20%", color: "#0cc06c" },
      { label: "Bueno", value: "10–20%", color: "#22c55e" },
      { label: "Aceptable", value: "5–10%", color: "#fbbf24" },
      { label: "Bajo", value: "<5%", color: "#ff4d4d" },
    ],
    tip: "El margen neto es el 'bottom line' — lo que realmente queda para los accionistas.",
  },
  ebitda_margin: {
    title: "Margen EBITDA",
    description: "Rentabilidad operativa antes de intereses, impuestos, depreciacion y amortizacion. Elimina diferencias contables entre empresas.",
    formula: "EBITDA / Ingresos × 100",
    thresholds: [
      { label: "Excelente", value: ">30%", color: "#0cc06c" },
      { label: "Bueno", value: "20–30%", color: "#22c55e" },
      { label: "Aceptable", value: "10–20%", color: "#fbbf24" },
      { label: "Bajo", value: "<10%", color: "#ff4d4d" },
    ],
    tip: "Muy usado en M&A porque permite comparar empresas de diferentes paises con distintas leyes fiscales.",
  },
};

// ─── SOLIDEZ FINANCIERA (HealthTab) ─────────────────────
export const HEALTH: Record<string, TooltipContent> = {
  cash_ratio: {
    title: "Cash Ratio (Razón de Efectivo)",
    description: "La prueba de liquidez más estricta: mide si la empresa puede pagar sus deudas de corto plazo solo con efectivo, sin vender inventario ni cobrar cuentas.",
    formula: "Efectivo y Equivalentes / Pasivos Corrientes",
    thresholds: [
      { label: "Muy líquida", value: ">0.5", color: "#0cc06c" },
      { label: "Saludable", value: "0.2–0.5", color: "#22c55e" },
      { label: "Ajustado", value: "0.1–0.2", color: "#fbbf24" },
      { label: "Justo", value: "<0.1", color: "#f97316" },
    ],
    tip: "Un cash ratio muy alto es súper seguro, pero puede indicar efectivo ocioso sin invertir en crecimiento.",
  },
  net_debt_to_ebitda: {
    title: "Deuda Neta / EBITDA",
    description: "Cuántos años de EBITDA necesitaría la empresa para pagar toda su deuda neta (deuda menos caja). Es la medida de apalancamiento favorita de los bancos.",
    formula: "(Deuda Total − Efectivo) / EBITDA",
    thresholds: [
      { label: "Caja neta (más caja que deuda)", value: "<0", color: "#0cc06c" },
      { label: "Conservador", value: "0–1.5x", color: "#22c55e" },
      { label: "Moderado", value: "1.5–3x", color: "#fbbf24" },
      { label: "Muy apalancado", value: ">3x", color: "#ff4d4d" },
    ],
    good: "Por debajo de 3x la deuda suele ser manejable incluso en una recesión.",
    bad: "Por encima de 4x, una caída de ganancias puede complicar el pago de la deuda.",
    tip: "Es más fiable que Deuda/Patrimonio porque resta la caja y se mide contra la generación real de efectivo.",
  },
  equity_to_assets: {
    title: "Patrimonio / Activos",
    description: "Qué porcentaje de los activos pertenece realmente a los accionistas y no está financiado con deuda. Es el complemento de Deuda/Activos.",
    formula: "Patrimonio / Activos Totales × 100",
    thresholds: [
      { label: "Muy sólido", value: ">70%", color: "#0cc06c" },
      { label: "Saludable", value: "50–70%", color: "#22c55e" },
      { label: "Moderado", value: "30–50%", color: "#fbbf24" },
      { label: "Muy apalancado", value: "<30%", color: "#ff4d4d" },
    ],
    tip: "Cuanto mayor el porcentaje, menos depende la empresa de dinero prestado.",
  },
  current_ratio: {
    title: "Current Ratio (Razon Corriente)",
    description: "Mide la capacidad de la empresa para pagar sus deudas a corto plazo. Compara activos liquidos contra obligaciones inmediatas.",
    formula: "Activos Corrientes / Pasivos Corrientes",
    thresholds: [
      { label: "Muy solida", value: ">2.0", color: "#0cc06c" },
      { label: "Saludable", value: "1.5–2.0", color: "#22c55e" },
      { label: "Aceptable", value: "1.0–1.5", color: "#fbbf24" },
      { label: "Riesgo de liquidez", value: "<1.0", color: "#ff4d4d" },
    ],
    good: "Current Ratio > 1.5 indica buena capacidad de pago a corto plazo.",
    bad: "Current Ratio < 1 significa que debe mas de lo que puede pagar pronto.",
  },
  quick_ratio: {
    title: "Quick Ratio (Prueba Acida)",
    description: "Igual que el Current Ratio pero excluye inventarios, que pueden ser dificiles de vender rapidamente. Es una prueba mas estricta.",
    formula: "(Activos Corrientes - Inventarios) / Pasivos Corrientes",
    thresholds: [
      { label: "Muy liquida", value: ">1.5", color: "#0cc06c" },
      { label: "Saludable", value: "1.0–1.5", color: "#22c55e" },
      { label: "Ajustado", value: "0.5–1.0", color: "#fbbf24" },
      { label: "Problematico", value: "<0.5", color: "#ff4d4d" },
    ],
    tip: "Si el Quick Ratio es mucho menor que el Current Ratio, la empresa depende mucho de vender inventario.",
  },
  cash: {
    title: "Efectivo y Equivalentes",
    description: "Dinero en caja e inversiones a corto plazo que la empresa puede usar inmediatamente. Es el 'colchon de seguridad'.",
    good: "Mucha caja permite invertir en oportunidades y sobrevivir crisis.",
    bad: "Exceso de caja sin uso puede indicar falta de oportunidades de crecimiento.",
    tip: "Compara la caja con la deuda total para ver la 'deuda neta' real.",
  },
  fcf: {
    title: "Flujo de Caja Libre (FCF)",
    description: "Efectivo que genera la empresa despues de operar y mantener sus activos. Es el dinero disponible para dividendos, recompras, o reduccion de deuda.",
    formula: "Flujo Operativo - Gastos de Capital (CapEx)",
    good: "FCF positivo y creciente indica negocio sano que genera caja real.",
    bad: "FCF negativo persistente indica que la empresa quema caja — necesita financiamiento.",
    tip: "El FCF es mas dificil de manipular que las ganancias contables. Muchos inversores lo prefieren sobre el ingreso neto.",
  },
  de_ratio: {
    title: "D/E (Deuda/Patrimonio)",
    description: "Cuantos dolares de deuda tiene la empresa por cada dolar de patrimonio de accionistas.",
    formula: "Deuda Total / Patrimonio",
    thresholds: [
      { label: "Conservador", value: "<0.5", color: "#0cc06c" },
      { label: "Moderado", value: "0.5–1.0", color: "#fbbf24" },
      { label: "Apalancado", value: "1.0–2.0", color: "#f97316" },
      { label: "Alto riesgo", value: ">2.0", color: "#ff4d4d" },
    ],
    tip: "Sectores como utilities y real estate suelen operar con D/E mas altos que tech.",
  },
  debt_to_assets: {
    title: "Deuda/Activos",
    description: "Que porcentaje de los activos totales esta financiado con deuda. Mide la dependencia de financiamiento externo.",
    formula: "Deuda Total / Activos Totales",
    thresholds: [
      { label: "Conservador", value: "<30%", color: "#0cc06c" },
      { label: "Moderado", value: "30–50%", color: "#fbbf24" },
      { label: "Alto", value: ">50%", color: "#ff4d4d" },
    ],
  },
  interest_coverage: {
    title: "Cobertura de Intereses",
    description: "Cuantas veces las ganancias operativas cubren los pagos de intereses de deuda. Mide la capacidad de servir la deuda.",
    formula: "EBIT / Gastos por Intereses",
    thresholds: [
      { label: "Muy seguro", value: ">10x", color: "#0cc06c" },
      { label: "Comodo", value: "5–10x", color: "#22c55e" },
      { label: "Ajustado", value: "2–5x", color: "#fbbf24" },
      { label: "Peligroso", value: "<2x", color: "#ff4d4d" },
    ],
    good: "Cobertura >5x significa que la empresa puede pagar intereses comodamente.",
    bad: "Cobertura <2x indica riesgo — cualquier caida en ganancias puede impedir pagos.",
  },
  payout_ratio: {
    title: "Payout Ratio",
    description: "Porcentaje de las ganancias que la empresa distribuye como dividendos. El resto se reinvierte.",
    formula: "Dividendos / Ingreso Neto × 100",
    thresholds: [
      { label: "Reinvierte mucho (crecimiento)", value: "<30%", color: "#3b82f6" },
      { label: "Equilibrado", value: "30–60%", color: "#22c55e" },
      { label: "Alto — distribuye mucho", value: "60–80%", color: "#fbbf24" },
      { label: "Insostenible", value: ">80%", color: "#ff4d4d" },
    ],
    tip: "Payout > 100% significa que paga mas dividendos de lo que gana — insostenible a largo plazo.",
  },
};

// ─── HISTORICO (HistoricalTab) ──────────────────────────
export const HISTORICAL: Record<string, TooltipContent> = {
  price_range: {
    title: "Posición en el rango de 52 semanas",
    description: "Dónde está el precio hoy dentro de su rango del último año. Los DOS extremos son alerta: en mínimos puede ser una oportunidad o un negocio deteriorándose; en máximos, fortaleza o estar caro/sobreextendido. La zona media es la más cómoda.",
    formula: "(Precio − Mínimo 52s) / (Máximo 52s − Mínimo 52s) × 100",
    thresholds: [
      { label: "En mínimos — alerta (¿oportunidad o problema?)", value: "0–10%", color: "#ff453a" },
      { label: "Cerca del mínimo — barata, con cautela", value: "10–25%", color: "#fbbf24" },
      { label: "Zona saludable — rango cómodo", value: "25–70%", color: "#0cc06c" },
      { label: "Cerca del máximo — cara, con cautela", value: "70–88%", color: "#fbbf24" },
      { label: "En máximos — cara / sobreextendida", value: "88–100%", color: "#ff453a" },
    ],
    tip: "Es una señal POSICIONAL (dónde está el precio), no de valoración fundamental — úsala junto al score. Una acción en mínimos puede seguir cara por su P/E.",
  },
  beta_hist: {
    title: "Beta",
    description: "Mide cuanto se mueve la accion cuando el mercado sube o baja. Beta 1.0 = se mueve igual que el S&P 500.",
    thresholds: [
      { label: "Defensiva", value: "<0.8", color: "#3b82f6" },
      { label: "Normal", value: "0.8–1.2", color: "#22c55e" },
      { label: "Agresiva", value: ">1.2", color: "#f97316" },
    ],
  },
  waterfall: {
    title: "Cascada de Ingresos",
    description: "Muestra como fluye el dinero desde los ingresos totales hasta el flujo de caja libre, pasando por cada nivel de gastos. Cada barra muestra cuanto queda despues de cada deduccion.",
    tip: "Idealmente cada barra debe ser un porcentaje razonable de la anterior. Si hay caidas abruptas, revisa donde se va el dinero.",
  },
  revenue_growth: {
    title: "Crecimiento de Ingresos",
    description: "Cambio porcentual de los ingresos respecto al ano anterior.",
    thresholds: [
      { label: "Alto crecimiento", value: ">20%", color: "#0cc06c" },
      { label: "Crecimiento sano", value: "5–20%", color: "#22c55e" },
      { label: "Estancado", value: "0–5%", color: "#fbbf24" },
      { label: "Cayendo", value: "<0%", color: "#ff4d4d" },
    ],
  },
  earnings_growth: {
    title: "Crecimiento de Ganancias",
    description: "Cambio porcentual de las ganancias netas respecto al ano anterior. Es mas importante que el crecimiento de ingresos.",
    thresholds: [
      { label: "Excelente", value: ">25%", color: "#0cc06c" },
      { label: "Bueno", value: "10–25%", color: "#22c55e" },
      { label: "Moderado", value: "0–10%", color: "#fbbf24" },
      { label: "Negativo", value: "<0%", color: "#ff4d4d" },
    ],
    tip: "Las ganancias deben crecer mas rapido o al mismo ritmo que los ingresos — si no, los margenes se estan comprimiendo.",
  },
  yearly_chart: {
    title: "Evolucion Anual",
    description: "Grafico de barras que muestra los ingresos y ganancias de los ultimos 4 anos. Permite ver la tendencia de crecimiento a simple vista.",
    tip: "Busca tendencia ascendente en ambas barras. Si ingresos crecen pero ganancias no, puede haber problemas de eficiencia.",
  },
  balance_sheet: {
    title: "Composicion del Balance",
    description: "Muestra como se compone la estructura financiera: patrimonio propio (equity), deuda, y efectivo disponible.",
    tip: "Una empresa saludable tiene mas equity que deuda, y suficiente caja para cubrir emergencias.",
  },
  per_share: {
    title: "Datos por Accion",
    description: "Metricas normalizadas por accion para comparar empresas de diferente tamano: precio, ganancias, valor en libros, y flujo de caja.",
    tip: "El valor en libros por accion vs precio te dice si estas pagando mas o menos que el valor contable de la empresa.",
  },
};

// ─── EVALUACION (EvaluationTab) ─────────────────────────
export const EVALUATION: Record<string, TooltipContent> = {
  financial_health: {
    title: "Salud Financiera",
    description: "Score compuesto (0–10) de solidez financiera para bancos y aseguradoras, donde el Altman Z-Score no aplica. Combina capitalización, liquidez, calidad de activos y rentabilidad.",
    thresholds: [
      { label: "Excelente", value: ">8", color: "#0cc06c" },
      { label: "Buena", value: "6–8", color: "#22c55e" },
      { label: "Neutral", value: "4–6", color: "#fbbf24" },
      { label: "Débil", value: "<4", color: "#ff4d4d" },
    ],
    tip: "Reemplaza al Altman Z-Score en el sector financiero, cuyo balance no encaja en el modelo tradicional.",
  },
  score_category: {
    title: "Categorías del Score",
    description: "El score de 0–100 se compone de 5 categorías, cada una sobre 20 puntos: Valoración, Rentabilidad, Solidez Financiera, Crecimiento y Calidad de Ganancias.",
    tip: "Un score alto con una categoría muy baja merece revisión: abre el desglose para ver de dónde viene la puntuación.",
  },
  altman_z: {
    title: "Altman Z-Score (Adaptativo)",
    description: "Modelo de Edward Altman que predice probabilidad de quiebra. Finanzer selecciona automaticamente la variante correcta segun el tipo de empresa: Z original (manufactura), Z'' (tech/servicios) o Z' (privadas).",
    formula: "Manufactura: 1.2×X1+1.4×X2+3.3×X3+0.6×X4+1.0×X5 | No-Mfg: 6.56×X1+3.26×X2+6.72×X3+1.05×X4",
    thresholds: [
      { label: "Zona segura (umbral segun modelo)", value: ">2.60–2.99", color: "#0cc06c" },
      { label: "Zona gris — monitorear de cerca", value: "1.10–2.60", color: "#fbbf24" },
      { label: "Zona de riesgo — probabilidad alta", value: "<1.10–1.81", color: "#ff4d4d" },
    ],
    tip: "Para tech/servicios se usa Z'' que elimina asset turnover (X5), evitando sesgo en empresas asset-light. Los umbrales se ajustan automaticamente al modelo seleccionado.",
  },
  piotroski: {
    title: "Piotroski F-Score",
    description: "Sistema de puntuacion de 0 a 9 creado por el profesor Joseph Piotroski de Stanford. Evalua 9 criterios binarios (pasa/no pasa) de rentabilidad, apalancamiento y eficiencia operativa.",
    thresholds: [
      { label: "Excelente — empresa muy saludable", value: "8–9", color: "#0cc06c" },
      { label: "Fuerte", value: "6–7", color: "#22c55e" },
      { label: "Neutral", value: "4–5", color: "#fbbf24" },
      { label: "Debil", value: "2–3", color: "#f97316" },
      { label: "Muy debil — senales de deterioro", value: "0–1", color: "#ff4d4d" },
    ],
    good: "Score 7+ indica empresa en buena forma operativa y financiera.",
    bad: "Score 3 o menos indica deterioro en multiples areas — alta probabilidad de bajo rendimiento.",
    tip: "Piotroski demostro que comprar acciones con F-Score alto y vender las de F-Score bajo genera retornos superiores al mercado.",
  },
  score_breakdown: {
    title: "Desglose del Score",
    description: "Muestra como se compone la puntuacion total. Cada categoria (Valoracion, Rentabilidad, Solidez, Crecimiento, Calidad) contribuye un porcentaje al score final.",
    tip: "Una empresa puede tener un score medio pero brillar en categorias especificas. Revisa que las categorias importantes para tu estrategia esten bien.",
  },
  alerts: {
    title: "Alertas y Senales",
    description: "Sistema automatico de deteccion de problemas (banderas rojas), advertencias (precaucion), y fortalezas. Analiza decenas de metricas para encontrar senales relevantes.",
    tip: "Las banderas rojas son mas importantes que las fortalezas. Una sola bandera roja puede invalidar muchas fortalezas.",
  },
};

// ─── VALOR INTRINSECO (IntrinsicTab) ────────────────────
export const INTRINSIC: Record<string, TooltipContent> = {
  graham: {
    title: "Valor Graham",
    description: "Formula de Benjamin Graham (el padre del value investing y mentor de Buffett) para estimar el valor intrinseco de una accion basado en ganancias y crecimiento.",
    formula: "V = EPS × (8.5 + 2g) × 4.4 / Y\ndonde g = tasa de crecimiento, Y = tasa del bono corporativo AAA",
    good: "Si el precio es menor al valor Graham, la accion puede estar subvalorada.",
    bad: "Si el precio supera al valor Graham por mucho, puede estar sobrevaluada.",
    tip: "Graham disenó esta formula para inversores conservadores. Tiende a ser mas restrictiva que el DCF.",
  },
  dcf: {
    title: "Valor DCF (Flujo de Caja Descontado)",
    description: "Modelo que estima el valor de una empresa sumando todos sus flujos de caja futuros, descontados al presente. Es el metodo mas usado por analistas profesionales.",
    formula: "V = Σ FCF_t / (1+r)^t + Terminal Value / (1+r)^n",
    good: "Si el DCF > precio actual, el mercado puede estar subvalorando la empresa.",
    bad: "DCF < precio sugiere que el mercado tiene expectativas muy optimistas.",
    tip: "El DCF es muy sensible a las estimaciones de crecimiento y tasa de descuento. Siempre revisa la tabla de sensibilidad.",
  },
  sensitivity: {
    title: "Tabla de Sensibilidad",
    description: "Muestra como cambia el valor intrinseco al variar la tasa de crecimiento y la tasa de descuento. Cada celda es un escenario diferente.",
    good: "Si la mayoria de celdas muestran valores > precio actual, hay margen de seguridad.",
    bad: "Si casi todas las celdas muestran valores < precio, la accion esta cara en casi cualquier escenario.",
    tip: "Enfocate en los escenarios conservadores (crecimiento bajo, descuento alto). Si aun asi el valor > precio, es buena senal.",
  },
  margin_safety: {
    title: "Margen de Seguridad",
    description: "Diferencia porcentual entre el valor intrinseco estimado y el precio de mercado. Concepto central de Benjamin Graham.",
    formula: "(Valor Intrinseco - Precio) / Valor Intrinseco × 100",
    thresholds: [
      { label: "Gran margen — oportunidad potencial", value: ">30%", color: "#0cc06c" },
      { label: "Margen moderado", value: "10–30%", color: "#22c55e" },
      { label: "Precio justo", value: "0–10%", color: "#fbbf24" },
      { label: "Sobrevaluada", value: "<0%", color: "#ff4d4d" },
    ],
    tip: "Graham recomendaba un margen de seguridad de al menos 30% antes de comprar.",
  },
};

// ─── COMPARATIVA (ComparativeTab) ───────────────────────
export const COMPARATIVE: Record<string, TooltipContent> = {
  sector_comparison: {
    title: "Comparacion vs Sector",
    description: "Compara los indicadores de la empresa contra los promedios de su sector industrial. Permite saber si la empresa es mejor o peor que sus competidores tipicos.",
    tip: "Una empresa puede parecer 'cara' en general pero ser 'barata' comparada con su sector. El contexto sectorial es clave.",
  },
  relative_indicator: {
    title: "Indicador Relativo (%)",
    description: "Muestra la diferencia porcentual entre el valor de la empresa y el promedio del sector. Verde = mejor que el sector, Rojo = peor.",
    good: "La empresa supera al sector en este indicador.",
    bad: "La empresa esta por debajo del promedio de su sector.",
  },
  summary: {
    title: "Resumen Comparativo",
    description: "Cuenta cuantos indicadores de la empresa superan al promedio de su sector. Mas indicadores verdes = empresa mas competitiva dentro de su industria.",
    thresholds: [
      { label: "Superior al sector", value: ">70%", color: "#0cc06c" },
      { label: "En linea con el sector", value: "40–70%", color: "#fbbf24" },
      { label: "Por debajo del sector", value: "<40%", color: "#ff4d4d" },
    ],
  },
};
