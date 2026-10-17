/**
 * Definiciones de las métricas (qué es, cómo se calcula, cómo leerla).
 *
 * Etapa 9b: aquí NO hay bandas ni umbrales. Las bandas que muestra cada tooltip
 * llegan en `display.tooltips` (backend/lib/display.py): solo las aplicadas a esta
 * empresa, según su arquetipo y su benchmark, generadas desde la config del score.
 * Los textos tampoco citan cifras de corte: la lectura de una métrica la da el
 * backend, igual en la web y en el PDF.
 *
 * Las claves coinciden con `Row.key` / `Kpi.key` / `MetricCard.key` del contrato.
 */
export interface Definition {
  title: string;
  description: string;
  formula?: string;
  good?: string;
  bad?: string;
  tip?: string;
}

export const DEFINITIONS: Record<string, Definition> = {
  // ── Puntuaciones ──
  quality: {
    title: "Calidad del negocio",
    description:
      "Puntuación de 0 a 100 de la calidad del negocio: solidez financiera, rentabilidad, calidad de ganancias y crecimiento. El atractivo del precio se puntúa aparte.",
    tip: "La calidad y el precio son preguntas distintas: una empresa excelente puede estar cara.",
  },
  price: {
    title: "Atractivo del precio",
    description:
      "Puntuación de 0 a 100 de lo atractivo que es el precio actual: valoración por múltiplos frente a su referencia y DCF. Se contrae hacia 50 cuando la confianza del veredicto no es alta.",
    tip: "Si la confianza no es alta verás «sin ajustar X → ajustado a Y»: X es lo que dicen los métodos e Y la cifra ajustada por la confianza.",
  },
  category: {
    title: "Categorías de la puntuación",
    description:
      "Cada categoría parte de una base neutral de 10/20 y suma o resta según la banda en la que cae cada indicador. Solidez, Rentabilidad, Calidad de ganancias y Crecimiento forman la calidad del negocio; Valoración, el atractivo del precio.",
    tip: "Una categoría «no concluyente» no tiene datos suficientes: se excluye y la puntuación se reescala sobre las demás.",
  },
  confidence: {
    title: "Confianza del veredicto",
    description:
      "Mide cuánto fiarse del veredicto de precio: si los métodos de valoración coinciden, si hay datos suficientes, la calidad de la fuente y la estabilidad del tipo de empresa.",
    tip: "La confianza contrae el atractivo del precio hacia 50; la calidad del negocio no se contrae.",
  },

  // ── Mercado ──
  price_now: {
    title: "Precio",
    description: "Último precio de cotización disponible.",
  },
  market_cap: {
    title: "Capitalización de mercado",
    description: "Valor total de la empresa en bolsa.",
    formula: "Precio × acciones en circulación",
    tip: "Las empresas más grandes tienden a ser más estables, con menos potencial de crecimiento explosivo.",
  },
  beta: {
    title: "Beta bruta (volatilidad)",
    description:
      "Cuánto se mueve la acción cuando se mueve el mercado (S&P 500), tal como la publica la fuente. Una beta igual a la unidad se mueve como el mercado. El coste de capital usa la beta ajustada (Blume), que verás en el desglose del WACC.",
    formula: "Covarianza(acción, mercado) / varianza(mercado)",
    tip: "Mide riesgo de mercado, no riesgo del negocio: una empresa débil puede tener beta baja.",
  },
  pos52: {
    title: "Posición en el rango de 52 semanas",
    description:
      "Dónde cotiza el precio dentro de su rango del último año. Es contexto de mercado: no dice si la acción está cara o barata ni mide la calidad del negocio.",
    formula: "(Precio − mínimo 52s) / (máximo 52s − mínimo 52s)",
    tip: "El atractivo del precio sale de los múltiplos y del DCF, no de la posición en el rango.",
  },

  // ── Valoración ──
  pe: {
    title: "P/E (precio / beneficio, TTM)",
    description: "Cuánto pagan los inversores por cada dólar de beneficio de los últimos doce meses.",
    formula: "Precio / BPA de los últimos 12 meses",
    good: "Un P/E por debajo de su referencia, con beneficios estables, puede indicar oportunidad.",
    bad: "Un P/E muy por encima de su referencia sin crecimiento que lo respalde sugiere sobrevaloración.",
    tip: "Se compara siempre con la mediana de su referencia (sector o mercado), nunca con un número fijo.",
  },
  pe_normalized: {
    title: "P/E normalizado",
    description: "P/E calculado sobre el beneficio sin partidas no recurrentes.",
    tip: "Se muestra cuando las partidas extraordinarias distorsionan el P/E reportado.",
  },
  forward_pe: {
    title: "Forward P/E",
    description: "Precio dividido por el beneficio estimado para los próximos doce meses.",
    formula: "Precio / BPA estimado",
    good: "Por debajo del P/E actual: el mercado espera que el beneficio crezca.",
    bad: "Por encima del P/E actual: el mercado espera una caída del beneficio.",
  },
  pb: {
    title: "P/B (precio / valor en libros)",
    description: "Compara el precio de mercado con el valor contable del patrimonio.",
    formula: "Precio / (patrimonio / acciones)",
    tip: "Más útil en bancos y empresas intensivas en capital que en negocios de intangibles.",
  },
  ptbv: {
    title: "P/TBV (precio / valor en libros tangible)",
    description: "Como el P/B, pero sin fondo de comercio ni intangibles: el patrimonio que respalda de verdad a un banco.",
    formula: "Capitalización / patrimonio tangible",
  },
  ps: {
    title: "P/S (precio / ventas)",
    description: "Capitalización dividida por los ingresos. Útil cuando aún no hay beneficios.",
    formula: "Capitalización / ingresos",
  },
  peg: {
    title: "PEG",
    description: "El P/E ajustado por el crecimiento esperado del beneficio.",
    formula: "P/E / crecimiento del beneficio (%)",
    tip: "Depende de estimaciones: si el crecimiento no llega, el PEG real será mayor.",
  },
  ev_ebitda: {
    title: "EV/EBITDA",
    description: "Valor de la empresa (incluida la deuda neta) frente a su beneficio operativo antes de amortizaciones.",
    formula: "Enterprise value / EBITDA",
    tip: "Neutral a la estructura de capital: compara empresas con distinto endeudamiento.",
  },
  ev_ebitda_normalized: {
    title: "EV/EBITDA normalizado",
    description: "EV/EBITDA sobre el EBITDA medio del ciclo, no sobre el de un año concreto.",
    tip: "En empresas cíclicas el EBITDA de un año puede estar en el pico o en el valle del ciclo.",
  },
  pfcf: {
    title: "P/FCF (precio / flujo de caja libre)",
    description: "Cuánto se paga por cada dólar de caja libre que genera la empresa.",
    formula: "Capitalización / flujo de caja libre",
  },
  p_fcf_normalized: {
    title: "P/FCF normalizado",
    description: "P/FCF sobre el flujo de caja libre de mantenimiento (flujo operativo − amortizaciones), promedio del ciclo.",
  },
  fcf_yield: {
    title: "FCF yield",
    description: "Flujo de caja libre en relación con el valor de mercado: el inverso del P/FCF.",
    formula: "Flujo de caja libre / capitalización",
    tip: "El flujo de caja es más difícil de maquillar que el beneficio contable.",
  },
  earnings_yield: {
    title: "Earnings yield (E/P)",
    description: "Beneficio por cada dólar invertido al precio actual: el inverso del P/E.",
    formula: "BPA / precio",
    tip: "Compáralo con la rentabilidad del bono del Tesoro.",
  },
  dividend_yield: {
    title: "Dividend yield",
    description: "Porcentaje del precio que la empresa devuelve cada año en dividendos.",
    formula: "Dividendo anual por acción / precio",
    bad: "Una rentabilidad anormalmente alta puede anticipar un recorte del dividendo.",
  },
  p_ffo: {
    title: "P/FFO",
    description: "El múltiplo de referencia de los REIT: precio frente a los fondos de operaciones (beneficio + amortización inmobiliaria).",
    formula: "Precio / FFO por acción",
  },
  ev_sales: {
    title: "EV/Ventas",
    description: "Valor de la empresa frente a sus ingresos: el múltiplo de las compañías que aún no tienen beneficios.",
    formula: "Enterprise value / ingresos",
  },
  rule_of_40: {
    title: "Regla de 40",
    description: "Crecimiento de ingresos más margen de flujo de caja libre (descontada la compensación en acciones en pre-beneficio).",
    formula: "Crecimiento de ingresos + margen (FCF − SBC)",
    tip: "Equilibra crecer rápido con generar caja.",
  },
  dcf_upside: {
    title: "Valor justo DCF y potencial",
    description: "El DCF estima el valor de la empresa descontando sus flujos de caja futuros al coste de capital (WACC). El potencial es la distancia entre ese valor y el precio.",
    formula: "Σ FCF_t / (1 + WACC)^t + valor terminal descontado",
    tip: "Muy sensible al crecimiento y a la tasa de descuento: revisa la tabla de sensibilidad y la fiabilidad del DCF.",
  },
  dcf_fair_value: {
    title: "Valor justo DCF",
    description: "Valor por acción que estima el modelo DCF con el escenario base.",
  },
  margin_of_safety: {
    title: "Margen de seguridad",
    description: "Distancia entre el valor intrínseco estimado y el precio, sobre el valor intrínseco. Concepto central de Benjamin Graham.",
    formula: "(Valor intrínseco − precio) / valor intrínseco",
  },
  graham: {
    title: "Número de Graham",
    description: "Referencia del inversor defensivo de Benjamin Graham: el precio máximo que pagaría con un P/E de 15 y un P/B de 1,5.",
    formula: "√(22,5 × BPA × valor en libros por acción)",
    tip: "Es una referencia; no vota en la convergencia entre métodos de valoración.",
  },
  sensitivity: {
    title: "Sensibilidad del valor justo",
    description: "Cómo cambia el valor justo del DCF al variar el crecimiento (filas) y la tasa de descuento (columnas). El recuadro marca el escenario base.",
    tip: "Fíjate en los escenarios conservadores: crecimiento bajo y descuento alto.",
  },
  wacc: {
    title: "WACC (coste de capital)",
    description: "La rentabilidad mínima que la empresa debe generar para no destruir valor: el coste medio ponderado de su patrimonio y su deuda.",
    formula: "%patrimonio × Ke + %deuda × Kd × (1 − t)",
  },
  multiples_block: {
    title: "Bloque de múltiplos",
    description: "P/E, Forward P/E, P/FCF, EV/EBITDA y PEG están correlacionados: puntúan juntos, como un solo bloque. El ajuste individual de cada uno se muestra entre paréntesis.",
  },

  // ── Rentabilidad ──
  roe: {
    title: "ROE (rentabilidad sobre el patrimonio)",
    description: "Cuánto beneficio genera la empresa por cada dólar de los accionistas.",
    formula: "Beneficio neto / patrimonio",
    bad: "Un ROE alto sostenido con mucha deuda es frágil: revisa el apalancamiento.",
  },
  roa: {
    title: "ROA (rentabilidad sobre activos)",
    description: "Eficiencia para generar beneficio con todos los recursos, propios y prestados.",
    formula: "Beneficio neto / activos totales",
    tip: "Más comparable que el ROE entre empresas con distinto endeudamiento.",
  },
  roic: {
    title: "ROIC (rentabilidad sobre el capital invertido)",
    description: "Rentabilidad después de impuestos de todo el capital invertido en el negocio (patrimonio y deuda).",
    formula: "NOPAT / capital invertido",
    tip: "Cuando el capital invertido es muy pequeño, el ROIC deja de ser significativo.",
  },
  roic_wacc_spread: {
    title: "Spread ROIC − WACC (creación de valor)",
    description: "Diferencia entre lo que la empresa gana sobre su capital y lo que le cuesta. Positivo: crea valor; negativo: lo destruye.",
    formula: "ROIC − WACC",
  },
  roce: {
    title: "ROCE (rentabilidad sobre el capital empleado)",
    description: "Beneficio operativo antes de impuestos sobre el capital empleado (activos − pasivos corrientes).",
    formula: "EBIT / capital empleado",
  },
  roce_avg: {
    title: "ROCE promedio",
    description: "ROCE medio de los últimos ejercicios: la rentabilidad a lo largo del ciclo.",
  },
  gross_margin: {
    title: "Margen bruto",
    description: "Lo que queda de cada dólar de ventas tras el coste directo de lo vendido: el poder de precios básico.",
    formula: "(Ingresos − coste de ventas) / ingresos",
  },
  operating_margin: {
    title: "Margen operativo",
    description: "Lo que queda de cada dólar de ventas tras todos los gastos de operación.",
    formula: "Beneficio operativo / ingresos",
  },
  net_margin: {
    title: "Margen neto",
    description: "Lo que queda de cada dólar de ventas después de todos los gastos, intereses e impuestos.",
    formula: "Beneficio neto / ingresos",
  },

  // ── Solidez ──
  runway: {
    title: "Runway",
    description: "Años que la caja cubre la quema de flujo de caja libre. Sustituye al Altman en las empresas pre-beneficio.",
    formula: "(Caja + inversiones a corto plazo) / quema anual de FCF",
  },
  current_ratio: {
    title: "Current ratio",
    description: "Capacidad de pagar las deudas a corto plazo con los activos corrientes.",
    formula: "Activos corrientes / pasivos corrientes",
  },
  quick_ratio: {
    title: "Quick ratio (prueba ácida)",
    description: "Como el current ratio, pero sin inventarios, que pueden tardar en convertirse en caja.",
    formula: "(Activos corrientes − inventarios) / pasivos corrientes",
  },
  cash_ratio: {
    title: "Cash ratio",
    description: "La prueba de liquidez más estricta: solo caja frente a los pasivos corrientes.",
    formula: "Caja y equivalentes / pasivos corrientes",
  },
  de: {
    title: "Deuda / patrimonio (D/E)",
    description: "Dólares de deuda por cada dólar de patrimonio.",
    formula: "Deuda total / patrimonio",
    tip: "No mide lo mismo en todos los negocios: en bancos los depósitos son pasivo y en REIT el apalancamiento se mide por la deuda neta/EBITDA.",
  },
  debt_to_assets: {
    title: "Deuda / activos",
    description: "Porcentaje de los activos financiado con deuda.",
    formula: "Deuda total / activos totales",
  },
  net_cash: {
    title: "Caja neta",
    description: "La caja supera a la deuda total: la empresa no tiene deuda neta. Importe = caja − deuda total.",
    formula: "Caja − deuda total",
  },
  net_debt_to_ebitda: {
    title: "Deuda neta / EBITDA",
    description: "Años de EBITDA que harían falta para pagar la deuda neta (deuda menos caja).",
    formula: "(Deuda total − caja) / EBITDA",
    tip: "Con EBITDA negativo la ratio no es significativa.",
  },
  interest_coverage: {
    title: "Cobertura de intereses",
    description: "Cuántas veces el beneficio operativo cubre el gasto por intereses.",
    formula: "EBIT / gasto por intereses",
    tip: "Con EBIT negativo y caja neta no es significativa: los intereses se pagan con caja.",
  },
  payout_ratio: {
    title: "Payout",
    description: "Porcentaje del beneficio (en REIT, del FFO) que se reparte como dividendo.",
    formula: "Dividendos / beneficio neto (o FFO)",
    bad: "Un payout por encima del beneficio no es sostenible en el tiempo.",
  },

  // ── Crecimiento y retorno ──
  revenue_growth: {
    title: "Crecimiento de ingresos",
    description: "Tasa anual compuesta de los ingresos en los últimos 3 años (en cíclicas, el promedio del ciclo; con dilución o recompras relevantes, por acción). Es la cifra que puntúa Crecimiento.",
  },
  revenue_growth_yoy: {
    title: "Crecimiento de ingresos (último ejercicio)",
    description: "Variación de los ingresos del último ejercicio anual frente al anterior, de los estados financieros. Es informativa: no puntúa.",
  },
  net_interest_income_growth: {
    title: "Margen de intereses (CAGR 3 años)",
    description: "En un banco, lo que cobra por sus préstamos menos lo que paga por sus depósitos y su deuda: tasa anual compuesta de los últimos 3 años y su peso en los ingresos netos. Es informativo: Crecimiento puntúa los ingresos netos (margen de intereses más comisiones).",
  },
  earnings_growth: {
    title: "Crecimiento del beneficio por acción (BPA)",
    description: "Tasa anual compuesta del BPA en los últimos 3 años (en cíclicas, el promedio del ciclo). Es la cifra que puntúa Crecimiento.",
  },
  earnings_growth_yoy: {
    title: "Crecimiento del BPA (último ejercicio)",
    description: "Variación del BPA diluido del último ejercicio anual frente al anterior, de los estados financieros. Es informativa: no puntúa.",
  },
  total_return: {
    title: "Retorno total por acción (REIT)",
    description: "Rentabilidad por dividendo más el crecimiento anual del FFO por acción en los últimos 3 años: el crecimiento que puntúa en un REIT.",
  },
  eps_vs_revenue: {
    title: "BPA frente a ingresos",
    description: "Diferencia entre el crecimiento del BPA y el de los ingresos: expansión o compresión de márgenes (o efecto de recompras). Es informativo: no puntúa.",
  },
  buyback_yield: {
    title: "Buyback yield (recompras netas)",
    description: "Porcentaje de acciones retirado (o emitido) en el último año.",
    formula: "(Acciones año previo − acciones actuales) / acciones año previo",
    bad: "Negativo: la empresa emite acciones y diluye a los accionistas.",
  },
  shareholder_yield: {
    title: "Shareholder yield",
    description: "Todo lo que la empresa devuelve al accionista: dividendos más recompras netas.",
    formula: "Dividend yield + buyback yield",
  },

  // ── Evaluación institucional ──
  financial_health: {
    title: "Salud financiera (sector financiero)",
    description: "Puntuación de 0 a 10 de solidez para bancos y aseguradoras, donde el Altman no aplica: capitalización, liquidez, calidad de activos y rentabilidad.",
  },
  altman: {
    title: "Altman Z-Score",
    description: "Modelo de Edward Altman que estima el riesgo de insolvencia a dos años. Finanzer elige la variante (Z, Z' o Z'') según el sector exacto.",
    tip: "No se calcula con ceros: si falta un componente, queda «sin dato». No aplica a bancos ni a REIT.",
  },
  piotroski: {
    title: "Piotroski F-Score",
    description: "Nueve señales contables de mejora en rentabilidad, estructura de capital y eficiencia operativa (Joseph Piotroski, 2000).",
    tip: "Los criterios sin dato no cuentan como incumplidos: el resultado se escala sobre los evaluados.",
  },
  breakdown: {
    title: "Desglose por categoría",
    description: "Cada indicador suma o resta puntos a su categoría según la banda en la que cae; la columna de ajuste muestra cuánto.",
  },
  alerts: {
    title: "Alertas y señales",
    description: "Riesgos, advertencias y fortalezas que detecta el motor a partir de las métricas.",
    tip: "Un riesgo pesa más que varias fortalezas.",
  },

  // ── Histórico (dato bruto) ──
  yearly: {
    title: "Histórico anual",
    description: "Cifras de los estados anuales, los mismos con los que se calculan los crecimientos a 3 años. Es dato bruto: sin lecturas ni colores.",
  },
  free_cash_flow: {
    title: "Flujo de caja libre",
    description: "Caja que genera el negocio tras invertir en mantenerlo.",
    formula: "Flujo operativo − capex",
  },
  fcf_minus_sbc: {
    title: "FCF − SBC",
    description: "Flujo de caja libre descontada la compensación en acciones, que es un coste real pagado con dilución.",
  },
};

/** Definición de una clave del contrato; las filas de rama sin definición propia usan su etiqueta. */
export function definitionFor(key: string, fallbackTitle: string): Definition {
  return DEFINITIONS[key] ?? { title: fallbackTitle, description: "" };
}
