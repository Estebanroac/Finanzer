# Prueba hacia atrás del motor · pre-registro (6-nov-2026)

La especificación es la del usuario (6-nov-2026, «Especificación cerrada»). Este documento solo fija **cómo se mide**
cada punto, por escrito y en git **antes de correr el motor o de mirar un solo rendimiento**. Nada de lo que sigue se
cambia después de ver resultados; si algo resulta imposible de medir, se declara «sin dato» y no se sustituye.

## 1. Fecha de corte: 5-nov-2025, después del cierre de Nueva York

- Reloj del análisis congelado en 2025-11-05 18:00 (America/New_York). Último precio = cierre del 5-nov-2025.
- **EDGAR**: solo hechos e informes con `filed` / `filingDate` ≤ 2025-11-05 (por fecha de presentación, no de periodo).
- **Yahoo**: series de precios, dividendos, ETF de sector, índice y tipos de cambio cortadas en el 5-nov-2025 y con la
  misma longitud de ventana que pide el motor (se piden de nuevo con fechas explícitas, no se recorta la de hoy).
  Estados de Yahoo: solo las columnas cuyo informe (10-K/10-Q/20-F/40-F/6-K de EDGAR del mismo periodo) se presentó
  ≤ 2025-11-05; si el periodo no casa con ningún informe, la columna sale si su cierre es posterior a corte − 100 días.
  Cotización (`fast_info`): precio, capitalización (precio × acciones de la última portada de EDGAR ≤ corte) y
  máximo/mínimo de 52 semanas recalculados con la serie cortada.
- **Finnhub**: `/stock/metric` sin el bloque actual: solo se conservan las series con periodo presentado ≤ corte;
  los valores «actuales» que no salen de esas series quedan sin dato (incluida su beta: la del motor es la propia,
  2 años semanales). `/stock/earnings`: solo trimestres publicados ≤ corte. `/stock/financials-reported`: solo
  `filedDate` ≤ corte. Calendario de resultados: fechas sí, estimaciones y cifras reales no.
- **Consenso adelantado y noticias: no disponibles** (P/E adelantado, PEG adelantado, estimaciones, titulares → sin
  dato). No se rellenan con datos actuales.
- **Damodaran**: industrias, betas, primas país y lista de empresas de **enero de 2025** (archivo de NYU Stern); prima
  de riesgo y Rf de **noviembre de 2025** (ERPbymonth.xlsx, fila de nov-2025). Ni ^TNX en vivo.
- **Pares del universo** (`config/peer_metrics.tsv`, hoy una foto de Yahoo `Ticker.info` del 28-oct-2026, que no tiene
  historia): se reconstruyen con EDGAR ≤ corte y el cierre del 5-nov-2025, con las mismas definiciones. Es la única
  sustitución de fuente y queda declarada.
- **Universo** (`tests/hacia_atras/universo_2025-11-05.tsv`, 543): el S&P 500 de la revisión 1319995707 de
  Wikipedia (2-nov-2025) con los cambios efectivos el 3 y el 4-nov (entra Q, sale EMN) + los 40 ADR de
  `market.universe.adrs`. Incluye las 29 que después salieron del índice (EA, WBD, K, HOLX, DAY, IPG…). Símbolos de
  esa fecha (BK, FI, MMC); los datos se piden con el símbolo de hoy si cambió (BNY, FISV, MRSH).

## 2. Versiones del motor (mismos datos congelados)

- **A** = `96d781ec` (origin/main, la actual: F13 + F14 + F15).
- **B** = `450cb5fc` (la de producción el 5-nov-2026, antes de F13), corrida con las herramientas del banco de
  `e61a513a` (mismo motor + el módulo de invariantes, que no cambia el análisis).
- Información, no decide: **A14** = `023644f0` (fin de F14, sin F15), para separar F15 de F13+F14.

## 3. Muestra

- Las 110 (`f13_banco110_2026-11-05/tickers110.txt`).
- Control: 300 del universo de 2025 sin las 110, estratificadas por sector GICS con el algoritmo de
  `tests/muestra_control.py` (cuota proporcional, restos al mayor decimal) y su semilla **20261106**.
  Reparto: Com. 10, Cons. disc. 31, Cons. básico 21, Energía 12, Financiero 54, Salud 37, Industria 48, Tecnología 45,
  Materiales 12, Inmobiliario 15, Utilities 15. Lista en `universo_2025-11-05.tsv` (columna `grupo`).
- Se reporta siempre por separado. **Decide el control.**

## 4. Etiquetas que se evalúan

- Precio: `verdict.price_level` (la que ve el usuario). **Barata** = atractivo o muy atractivo; **cara** = exigente o
  muy exigente; razonable aparte; sin veredicto fuera de las medias.
- Puntuación: `price_attractiveness.score` (la contraída, la que se muestra); la cruda, como información.
- Confianza: `verdict.confidence` (alta, media, baja).
- Alerta roja: `alerts.red_flags` no vacía.
- Lecturas conductuales: `market_context.behavioral` (sobrerreacción, caída sin explicar, anclaje, extrapolación) y
  las señales `momentum` y `relative_strength` de `market_context.signals`.

## 5. Líneas base (mismo universo, misma fecha, mismos datos ≤ corte)

- **L1**: P/E de doce meses (cierre del 5-nov-2025 × acciones / beneficio neto atribuible TTM de EDGAR) dividido por la
  mediana del P/E de su sector GICS en el universo de 543. Tercios de ese cociente en el universo: el tercio más bajo =
  barata, el más alto = cara. Beneficio ≤ 0: sin etiqueta L1 (se cuenta cuántas).
- **L2**: rendimiento de caja libre = (flujo operativo − capex) TTM / capitalización. Tercios en el universo: el más
  alto = barata, el más bajo = cara (un FCF negativo cae en cara). Sin flujo o sin capitalización: sin etiqueta.
- Se calculan igual para financieras (son reglas simples a propósito).

## 6. Resultados reales (del 5-nov-2025 al 5-may-2026 y al 5-nov-2026)

- Rendimiento total con el cierre ajustado de Yahoo (dividendos reinvertidos). Relativo = rendimiento de la acción −
  rendimiento del SPDR de su sector GICS (XLK, XLF, XLV, XLY, XLP, XLE, XLI, XLB, XLU, XLRE, XLC; los ADR por su
  sector GICS), en puntos porcentuales. Si el día no es sesión, el último cierre anterior.
- Deslistadas: compra en efectivo → el precio pagado el día del cierre de la operación y 0 % después; compra en
  acciones → las acciones del comprador según la relación de canje. Si no hay precio gratuito y fiable: sin dato, y se
  dice cuántas.
- Caída máxima: la mayor caída de pico a valle del cierre ajustado dentro de cada ventana (el pico puede ser el día 0).
- Fundamentales: BPA diluido, ventas y FCF (flujo operativo − capex) de los 2 primeros trimestres que cierran después
  del último periodo presentado al corte, de EDGAR (el 4.º trimestre = anual − 9 meses).
- Eventos negativos en 12 meses: **recorte de dividendo** = un pago ordinario ≥ 5 % menor que el anterior o su
  suspensión (Yahoo, ajustado por splits; los extraordinarios no cuentan). **Recorte de guía y de calificación: sin
  fuente gratuita y fiable → sin dato** (regla de presupuesto 0); el criterio (c) se mide con caídas y dividendos y se
  dice que la medida de eventos es parcial.

## 7. Métricas y criterios (los de la especificación, con su forma exacta)

- **(a)** Media del relativo a 12 meses por grupo; diferencia D = media(barata) − media(cara). **Éxito**: D(motor A)
  ≥ 5 pp **y** D(motor A) > D(L1) **y** D(motor A) > D(L2), en el control. Información: 6 meses, Spearman entre la
  puntuación y el relativo (6 y 12), intervalos por remuestreo (no cambian el criterio), y lo mismo con B y A14.
- **(b)** Acierto de dirección = barata con relativo 12 m > 0 o cara con relativo 12 m < 0 (razonable y sin veredicto
  fuera). Tasa por confianza. **Éxito**: alta > media > baja (estricto; se da n de cada nivel).
- **(c)** Acierto de una empresa = caída máxima ≥ 25 % en la ventana de 6 o de 12 meses, o recorte de dividendo en 12
  meses. **Éxito**: frecuencia con alerta ≥ 2 × frecuencia sin alerta.
- **(d)** Crecimiento: `dcf.growth_rate` frente al crecimiento interanual de las ventas de los 2 trimestres
  siguientes. Caja: `dcf.fcf_input` (anual, la del motor) × ½ × (1 + g)^½ frente a FCF − SBC real de esos 2
  trimestres. Mediana del error y del error absoluto por arquetipo (`classification.archetype`). «Sería errónea si…»
  (`premortem.items`): se comprueban las de margen y deuda con los trimestres reales; las de precio inverso (10 años)
  son «no evaluables a 12 meses».
- **(e)** Solo precio: empresas con lectura de sobrerreacción o caída sin explicar → relativo medio a 6 y 12 meses y %
  que rebotó (relativo > 0). Momentum 12-1 y fuerza relativa: tercios en la muestra y relativo medio de cada tercio.

## 8. Regla de decisión (de la especificación)

Si el motor A no supera a L1 y a L2 en (a), la valoración se simplifica hacia la regla que haya funcionado y el motor
queda para calidad, alertas y lectura. No se abre otro ciclo de ajustes de precio.

## 9. Entregables

`archivo-historico/evidencias-de-pruebas/hacia_atras_2025-11-05/`: `empresas_410.csv` (una fila por empresa con A,
B, A14, L1, L2 y resultados), `metricas.csv` (a–e × muestra × versión), datos congelados, registro de accesos no
grabados; informe en `informes-pdf/`.
