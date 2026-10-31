# V4b · 2: auditoría de la información que falta

Encargo del PM (V4b, punto 2), en la rama `rediseno/v4b-datos` (desde `rediseno/v4` 6ebf864, con el punto 1 en fcb87a6).
Revisión del 26-oct-2026. Sin push y sin `git stash`.

## Resumen

- **Recuento.** Panel completo (37 tickers, MC.PA y SPY incluidos) × 10 páginas de /v2: la historia y las 9 de
  profundidad, que serán las secciones. Se cuenta contra el replay y con el build actual.
  - Antes: **3610** marcas de ausencia («Sin dato», «—», «n. d.», celdas vacías y bloques con motivo de ausencia).
  - Después: **3274**.
- **Clasificación.**

  | Clase | Antes | Después |
  |---|---:|---:|
  | (a) no lo publica la fuente o no aplica | 2872 | 2914 |
  | (b) se perdía | **223** | **0** |
  | (c) faltaba en los fixtures | **298** | **161** |
  | No es una ausencia (informativo o maquetación) | 217 | 199 |

  - Las 161 de (c) que quedan son los rivales sin fixtures: pendiente de decisión, ver «Decisiones para el PM».
  - (a) sube 42 porque los bloques recapturados que no desglosan (HSBC, NFLX, PGR) y los motivos nuevos son
    ausencias correctas, ahora con su porqué.
- **Motor (`display` y `display.extended` de los 37 golden).**
  - Estados sin dato, no aplica o no significativo **sin motivo: 42 → 0**.
  - `sin_dato`: 16 → 8. Los 8 que quedan llevan su motivo.
- **Veredictos: 0 cambios.**
  - `tools/verdicts_vs_main.py --ref HEAD` da «43 golden × 11 campos frente a HEAD: 0 con cambios».
  - Los cambios de los golden están en `display` y `market_context`; ningún bloque de puntuación, ajuste ni veredicto.
- **Presentación.** La mayor parte de lo que queda en (a) son celdas que la web pinta vacías o con «—» sin decir por
  qué, aunque el motor tiene el motivo. Lista para E3 en «Presentación (para el PM)». No he tocado páginas ni
  componentes de /v2.

## Cómo se ha contado (reproducible)

```
# 1. replay con el build actual (antes: un worktree temporal en HEAD con su replay en 8771 y la misma web compilada)
cd backend && ../.venv313/bin/python tests/replay_server.py --env panel --port 8767
# 2. recuento en la web: cada marca con su fila, columna, clave del motor y sección
cd frontend && BASE=http://localhost:8767 node scripts/auditoria-faltantes.mjs despues.json
# 3. clasificación (reglas explícitas, en orden) y recuento del motor (golden de HEAD frente a los de la rama)
cd backend && ../.venv313/bin/python tools/auditoria_faltantes.py antes.json despues.json --md tablas.md --ref fcb87a6
```

- **Escáner** (`frontend/scripts/auditoria-faltantes.mjs`).
  - Descarta lo que no es un dato: las celdas de maquetación de las gráficas (tablas con lienzo), la celda «Quitar»
    de la propia empresa y los bloques que afirman cero («no detecta hoy ningún patrón»).
  - Lo que el recuento no puede saber por la forma lo decide el clasificador: bloques informativos, el rótulo
    «Sin dato:» seguido del motivo, etc.
- **Clasificador** (`backend/tools/auditoria_faltantes.py`). Ninguna marca queda sin clasificar, ni antes ni después.
- **Recuentos en bruto** de esta revisión: `docs/rediseno/verificacion/V4b_datos_faltantes/antes.json.gz` y
  `despues.json.gz`. Las tablas de abajo salen de
  `tools/auditoria_faltantes.py ../docs/rediseno/verificacion/V4b_datos_faltantes/{antes,despues}.json.gz --ref fcb87a6`
  (fcb87a6: la punta de la rama antes de este trabajo).

## Tablas

#### Por sección y clase

| Sección | a (antes → después) | b (antes → después) | c (antes → después) | no es una ausencia (antes → después) | sin clasificar (antes → después) | Total |
|---|---:|---:|---:|---:|---:|---:|
| historia | 233 → 215 | 0 → 0 | 0 → 0 | 0 → 0 | 0 → 0 | 233 → 215 |
| empresa | 4 → 11 | 7 → 0 | 0 → 0 | 0 → 0 | 0 → 0 | 11 → 11 |
| negocio | 241 → 244 | 0 → 0 | 27 → 0 | 1 → 2 | 0 → 0 | 269 → 246 |
| accion | 2 → 3 | 1 → 0 | 56 → 0 | 0 → 0 | 0 → 0 | 59 → 3 |
| calidad | 1567 → 1612 | 129 → 0 | 0 → 0 | 74 → 74 | 0 → 0 | 1770 → 1686 |
| valor | 812 → 812 | 0 → 0 | 0 → 0 | 79 → 79 | 0 → 0 | 891 → 891 |
| rivales | 1 → 1 | 85 → 0 | 161 → 161 | 36 → 36 | 0 → 0 | 283 → 198 |
| riesgos | 1 → 4 | 0 → 0 | 27 → 0 | 3 → 8 | 0 → 0 | 31 → 12 |
| actualidad | 1 → 2 | 1 → 0 | 27 → 0 | 24 → 0 | 0 → 0 | 53 → 2 |
| conclusion | 10 → 10 | 0 → 0 | 0 → 0 | 0 → 0 | 0 → 0 | 10 → 10 |
| **Total** | **2872 → 2914** | **223 → 0** | **298 → 161** | **217 → 199** | **0 → 0** | **3610 → 3274** |

#### Por regla

| Clase | Regla | Antes | Después | Por qué |
|---|---|---:|---:|---|
| a | sin referencia de industria | 2106 | 2088 | Damodaran no publica referencia de industria de esta métrica; la celda no lo dice |
| a | no aplica a este tipo de empresa | 290 | 307 | con el porqué en su sitio |
| a | margen sin CAGR (no se compone) | 130 | 130 | celda vacía sin motivo |
| a | ajuste del score que no aplica | 86 | 86 | la tabla pinta «Sin dato» en el valor de un ajuste n/a |
| a | la fuente no lo publica | 48 | 69 | con el motivo en su sitio |
| a | cifra de relleno de la historia | 45 | 45 | la fila de cifras del capítulo se completa con una caja «— / Sin dato» cuando hay menos cifras |
| a | no significativo | 27 | 27 | con el porqué en su sitio |
| a | múltiplo que no aplica (sin cifra por decisión) | 26 | 24 | la fila dice «No aplica a …» |
| a | EDGAR sin el concepto estándar (ficha del ejercicio) | 24 | 24 | el motor da el porqué en display.extended.history_10y.rows[].reasons (V4b); la ficha no lo pinta |
| a | sin referencia de industria | 21 | 19 | referencia de industria sin dato para esta industria (Damodaran) o fila sin lectura; la celda no lo dice |
| a | sensibilidad: columna de WACC recortada | 18 | 18 | sensitivity.trimmed.note lo explica («WACC recortado en [6%, 20%]»); la tabla pinta la columna con «—» |
| a | tarjeta ROCE que no aplica | 18 | 18 | charts.profitability.roce.text tiene el porqué |
| a | CAGR con base ≤ 0 | 12 | 12 | «—» sin motivo |
| a | tarjeta de la conclusión que no aplica | 10 | 10 | display.summary.cards: state no_aplica y el motivo en «bench»; la tarjeta pinta «Sin dato» |
| a | el emisor no presenta en la SEC | 4 | 4 | sin 10-K/20-F |
| a | sin rivales propuestos (sin industria de referencia) | 3 | 3 | V: referencia del mercado por política (benchmark.reason); el resumen de rivales pinta «—» |
| a | cotiza desde hace menos del periodo | 2 | 2 | RIVN salió a bolsa el 10-nov-2021: sin 5 años |
| a | Finnhub gratuito no cubre la bolsa | 1 | 1 | 403 de Finnhub para MC.PA |
| a | criterio de Piotroski sin deuda previa | 1 | 1 | el detalle lo dice |
| a | tarjeta ROIC − WACC que no aplica | 0 | 26 | charts.profitability.spread.text tiene el porqué (V4b); la tarjeta pinta «Sin dato» |
| b | rivales: motivo perdido en el resumen | 85 | 0 | no aplica / no significativo se veía como «Sin dato» (analysis_queue.summary) |
| b | referencia de industria de D/E y cobertura sin cablear | 82 | 0 | Damodaran la publica y el análisis la tiene (benchmark.values) |
| b | motivo perdido: tarjeta ROIC − WACC | 26 | 0 | no aplica al arquetipo (classify) |
| b | motivo perdido: «No aplica» sin porqué | 13 | 0 | classify lo tenía (display._na_why) |
| b | motivo perdido: crecimiento sin tasa | 8 | 0 | base ≤ 0 en la cobertura del score |
| b | nombres internos de Yahoo en el aviso | 7 | 0 | capitalLeaseObligations, commercialPaper |
| b | motivo perdido: serie del sector | 2 | 0 | market_context sabía el porqué (cotiza en EUR) |
| c | rivales sin fixtures en el replay | 161 | 161 | el backend real analiza el rival en vivo |
| c | serie de 5 años sin fixture | 56 | 0 | gráfica y rentabilidad por periodo |
| c | segmentos sin fixture | 54 | 0 | EDGAR (índice del 10-K/20-F) |
| c | titulares y calendario sin fixture | 27 | 0 | Finnhub /company-news |
| no es una ausencia | bloque informativo | 76 | 82 | explica una cifra que está |
| no es una ausencia | rótulo «Sin dato:» de un motivo | 47 | 47 | el motivo va a continuación |
| no es una ausencia | rivales: celda «Quitar» de la propia empresa | 36 | 36 | sin botón: no es un dato |
| no es una ausencia | bloque informativo | 32 | 32 | lectura de un múltiplo de la rama |
| no es una ausencia | bloque informativo | 26 | 2 | afirma que no hay (cero señales) o avisa |

#### Ejemplos (antes)

- **a · sin referencia de industria**: AAPL /historia: Forward P/E · Industria «—»; AAPL /historia: Forward P/E · Lectura «celda vacía»; AAPL /historia: PEG · Industria «—»
- **a · margen sin CAGR (no se compone)**: AAPL /negocio: Margen bruto · CAGR «celda vacía»; AAPL /negocio: Margen operativo · CAGR «celda vacía»; AAPL /negocio: Margen neto · CAGR «celda vacía»
- **a · la fuente no lo publica**: AAPL /calidad: ? «Sin dato: el proveedor no lo da»; AMT /calidad: Retorno total por acción «BPA: No aplica a REIT.»; AMT /calidad: Piotroski F-Score · n/a «Criterios de Piotroski: sin dos ejercicios comparables»
- **a · cifra de relleno de la historia**: AMT /historia: Qué puede salir mal «—»; AMT /historia: Qué puede salir mal «Sin dato»; BAC /historia: Frente a sus rivales «—»
- **a · no aplica a este tipo de empresa**: AMT /negocio: Margen EBITDA «Margen bruto: No aplica a REIT.»; AMT /negocio: Margen EBITDA «Margen operativo: No aplica a REIT.»; AMT /negocio: Margen EBITDA «Margen neto: No aplica a REIT.»
- **a · tarjeta ROCE que no aplica**: AMT /calidad: ? «Sin dato»; AMT /calidad: ? «Sin dato»; BAC /calidad: ? «Sin dato»
- **a · ajuste del score que no aplica**: AMT /calidad: No aplica · Valor «Sin dato»; AMT /calidad: No aplica · Valor «Sin dato»; AMT /calidad: No aplica · Valor «Sin dato»
- **a · múltiplo que no aplica (sin cifra por decisión)**: AMT /valor: P/E (TTM) · Empresa «—»; ASML /valor: P/E (TTM) · Empresa «—»; BAC /valor: EV/EBITDA · Empresa «—»
- **a · tarjeta de la conclusión que no aplica**: AMT /conclusion: Margen neto ? «Sin dato»; AMT /conclusion: ROE ? «Sin dato»; O /conclusion: Margen neto ? «Sin dato»
- **a · CAGR con base ≤ 0**: AMZN /negocio: Beneficio neto · CAGR «—»; AMZN /negocio: Flujo de caja libre · CAGR «—»; BRK-B /negocio: Beneficio neto · CAGR «—»
- **a · no significativo**: AMZN /calidad: Deuda / Equity · Brecha «No significativo · con caja neta, el D/E (0.30x) no mide apalancamiento.»; AMZN /valor: Mueve los supuestos y mira el valor «Escenarios: FCF − SBC base −$22.28B (≤ 0): no hay flujo positivo que descontar, así que el»; AMZN /valor: DCF y sensibilidad «DCF: DCF no significativo: FCF − SBC base −$22.28B (≤ 0): no hay flujo positivo que descon»
- **a · EDGAR sin el concepto estándar (ficha del ejercicio)**: BAC /negocio: Capex «—»; BAC /negocio: Flujo de caja libre «—»; BAC /negocio: Margen operativo «—»
- **a · sensibilidad: columna de WACC recortada**: DOW /valor: −10.0% · 9.1% «—»; DOW /valor: −10.0% · 10.1% «—»; DOW /valor: −7.5% · 10.1% «—»
- **a · el emisor no presenta en la SEC**: MC.PA /empresa: Ficha «Ficha de la SEC: el emisor no presenta en la SEC: sin ficha oficial»; MC.PA /negocio: Ingresos por segmento «Ingresos por segmento: no presenta estados en la SEC»; MC.PA /negocio: Historia de 10 años «Historia de 10 años: el emisor no presenta en la SEC»
- **a · Finnhub gratuito no cubre la bolsa**: MC.PA /actualidad: Noticias de la última semana «Noticias: sin titulares de Finnhub (no disponibles o sin respuesta)»
- **a · criterio de Piotroski sin deuda previa**: PLTR /calidad: Sin dato «Sin dato»
- **a · cotiza desde hace menos del periodo**: RIVN /accion: 5A · RIVN · precio «Sin dato»; RIVN /accion: 5A · RIVN · con dividendos «Sin dato»
- **a · sin rivales propuestos (sin industria de referencia)**: V /historia: Frente a sus rivales · Calidad «—»; V /historia: Frente a sus rivales · Calidad «—»; V /historia: Frente a sus rivales · Calidad «—»
- **b · referencia de industria de D/E y cobertura sin cablear**: AAPL /calidad: Deuda / Equity · Industria «—»; AAPL /calidad: Deuda / Equity · Brecha «—»; AMT /calidad: Deuda / Equity · Industria «—»
- **b · motivo perdido: tarjeta ROIC − WACC**: AMT /calidad: ? «Sin dato»; AMT /calidad: ? «Sin dato»; BAC /calidad: ? «Sin dato»
- **b · motivo perdido: «No aplica» sin porqué**: AMT /calidad: Current ratio · Empresa «No aplica»; BAC /calidad: Current ratio · Empresa «No aplica»; BCS /calidad: Current ratio · Empresa «No aplica»
- **b · rivales: motivo perdido en el resumen**: AMT /rivales: AMT · P/E «Sin dato»; AMT /rivales: AMT · ROIC «Sin dato»; AMT /rivales: AMT · Margen neto «Sin dato»
- **b · motivo perdido: crecimiento sin tasa**: AMZN /calidad: Ingresos «BPA: Sin dato»; AMZN /calidad: Ingresos «FCF: Sin dato»; BRK-B /calidad: Ingresos «BPA: Sin dato»
- **b · nombres internos de Yahoo en el aviso**: CAT /empresa: Datos del análisis «Sin dato del corte, descartados por ser de otro periodo: capitalLeaseObligations, commerci»; KO /empresa: Datos del análisis «Sin dato del corte, descartados por ser de otro periodo: commercialPaper.»; NVO /empresa: Datos del análisis «Sin dato del corte, descartados por ser de otro periodo: capitalLeaseObligations, commerci»
- **b · motivo perdido: serie del sector**: MC.PA /accion: Señales de mercado «Señales parciales: la serie del sector es sin dato.»; MC.PA /actualidad: Señales de mercado «Señales parciales: la serie del sector es sin dato.»
- **c · rivales sin fixtures en el replay**: AAPL /rivales: DELL · Calidad «Sin análisis · DELL: sin fixtures en el replay»; AAPL /rivales: SNDK · Calidad «Sin análisis · SNDK: sin fixtures en el replay»; AAPL /rivales: STX · Calidad «Sin análisis · STX: sin fixtures en el replay»
- **c · segmentos sin fixture**: AMT /negocio: Ingresos por segmento «Ingresos por segmento: no presenta estados en la SEC»; AMT /riesgos: Concentración de los ingresos «Concentración: no presenta estados en la SEC»; AMZN /negocio: Ingresos por segmento «Ingresos por segmento: no presenta estados en la SEC»
- **c · serie de 5 años sin fixture**: AMT /accion: Precio en el tiempo «Gráfica de precio: Yahoo no respondió (2 intentos)»; AMT /accion: Rentabilidad por periodo «Rentabilidad por periodo: Yahoo no respondió (2 intentos)»; AMZN /accion: Precio en el tiempo «Gráfica de precio: Yahoo no respondió (2 intentos)»
- **c · titulares y calendario sin fixture**: AMT /actualidad: Noticias de la última semana «Noticias: sin titulares de Finnhub (no disponibles o sin respuesta)»; AMZN /actualidad: Noticias de la última semana «Noticias: sin titulares de Finnhub (no disponibles o sin respuesta)»; ASML /actualidad: Noticias de la última semana «Noticias: sin titulares de Finnhub (no disponibles o sin respuesta)»
- **no es una ausencia · rótulo «Sin dato:» de un motivo**: AAPL /calidad: ? «Sin dato:»; AMT /calidad: ? «Sin dato:»; AMZN /calidad: ? «Sin dato:»
- **no es una ausencia · bloque informativo**: AAPL /calidad: Crecimiento anual compuesto (3 años) «BPA frente a ingresos: BPA +6.9% frente a ingresos +1.8% (los crecimientos que puntúa Crec»; AAPL /valor: Múltiplos frente a la referencia «Bloque de múltiplos -3 · media de las lecturas de 5 múltiplos en una escala de −1 a +1 (P/»; AMT /valor: Múltiplos frente a la referencia «Bloque de múltiplos +1 · media de las lecturas de 1 múltiplo en una escala de −1 a +1 (EV/»
- **no es una ausencia · rivales: celda «Quitar» de la propia empresa**: AAPL /rivales: AAPL · Quitar «celda vacía»; AMT /rivales: AMT · Quitar «celda vacía»; AMZN /rivales: AMZN · Quitar «celda vacía»

#### Presentación (después): el motor tiene el motivo y la página no lo pinta

| Página | Regla | Marcas | Detalle |
|---|---|---:|---|
| calidad | sin referencia de industria | 1296 | Damodaran no publica referencia de industria de esta métrica; la celda no lo dice |
| valor | sin referencia de industria | 625 | Damodaran no publica referencia de industria de esta métrica; la celda no lo dice |
| historia | sin referencia de industria | 167 | Damodaran no publica referencia de industria de esta métrica; la celda no lo dice |
| negocio | margen sin CAGR (no se compone) | 130 | celda vacía sin motivo |
| calidad | ajuste del score que no aplica | 66 | la tabla pinta «Sin dato» en el valor de un ajuste n/a |
| historia | cifra de relleno de la historia | 45 | la fila de cifras del capítulo se completa con una caja «— / Sin dato» cuando hay menos cifras |
| calidad | tarjeta ROIC − WACC que no aplica | 26 | charts.profitability.spread.text tiene el porqué (V4b); la tarjeta pinta «Sin dato» |
| negocio | EDGAR sin el concepto estándar (ficha del ejercicio) | 24 | el motor da el porqué en display.extended.history_10y.rows[].reasons (V4b); la ficha no lo pinta |
| valor | ajuste del score que no aplica | 20 | la tabla pinta «Sin dato» en el valor de un ajuste n/a |
| calidad | tarjeta ROCE que no aplica | 18 | charts.profitability.roce.text tiene el porqué |
| valor | sensibilidad: columna de WACC recortada | 18 | sensitivity.trimmed.note lo explica («WACC recortado en [6%, 20%]»); la tabla pinta la columna con «—» |
| calidad | sin referencia de industria | 16 | referencia de industria sin dato para esta industria (Damodaran) o fila sin lectura; la celda no lo dice |
| negocio | CAGR con base ≤ 0 | 12 | «—» sin motivo |
| conclusion | tarjeta de la conclusión que no aplica | 10 | display.summary.cards: state no_aplica y el motivo en «bench»; la tarjeta pinta «Sin dato» |
| historia | sin rivales propuestos (sin industria de referencia) | 3 | V: referencia del mercado por política (benchmark.reason); el resumen de rivales pinta «—» |
| valor | sin referencia de industria | 3 | referencia de industria sin dato para esta industria (Damodaran) o fila sin lectura; la celda no lo dice |

#### Motor: display y display.extended de los 37 golden del panel (fcb87a6 → rama)

| Bloque | sin_dato | sin_dato sin motivo | no_aplica | no_aplica sin motivo | no_significativo | no_significativo sin motivo | null |
|---|---:|---:|---:|---:|---:|---:|---:|
| display.charts.growth | 8 → 2 | 8 → 0 | 20 | 0 | 0 → 6 | 0 | 0 |
| display.charts.historical | 0 | 0 | 8 | 0 | 0 | 0 | 0 |
| display.charts.institutional | 0 | 0 | 13 | 0 | 0 | 0 | 0 |
| display.charts.profitability | 2 → 0 | 2 → 0 | 93 | 11 → 0 | 2 → 4 | 0 | 0 |
| display.charts.results_flow | 0 | 0 | 20 | 0 | 0 | 0 | 0 |
| display.charts.solvency | 2 | 2 → 0 | 31 | 0 | 14 | 0 | 0 |
| display.charts.valuation | 2 | 2 → 0 | 88 | 0 | 3 | 0 | 0 |
| display.cover.kpis | 0 | 0 | 0 | 0 | 2 | 2 → 0 | 0 |
| display.extended.company_profile | 0 | 0 | 0 | 0 | 0 | 0 | 35 |
| display.extended.history_10y | 0 | 0 | 0 | 0 | 0 | 0 | 30 |
| display.extended.news | 0 | 0 | 0 | 0 | 0 | 0 | 44 → 188 |
| display.extended.next_earnings | 0 | 0 | 0 | 0 | 0 | 0 | 50 → 38 |
| display.extended.piotroski_values | 0 | 0 | 0 | 0 | 0 | 0 | 91 |
| display.sections.institutional | 0 | 0 | 97 | 0 | 0 | 0 | 0 |
| display.sections.profitability | 0 | 0 | 53 | 0 | 2 | 0 | 0 |
| display.sections.solvency | 0 | 0 | 23 | 15 → 0 | 14 | 0 | 0 |
| display.sections.valuation | 2 | 0 | 100 | 0 | 3 | 0 | 0 |
| display.summary.cards | 0 | 0 | 10 | 0 | 0 | 0 | 0 |
| **Total** | **16 → 8** | **14 → 0** | **556 → 556** | **26 → 0** | **40 → 48** | **2 → 0** | **250 → 382** |

## Arreglos

Todos con test (`backend/tests/test_v4b_datos.py`, `test_peers.py`, `test_market_context.py`, `test_history_10y.py`).

### (b) El dato o su motivo existía y se perdía (motor)

| Qué se perdía | Dónde estaba | Arreglo | Marcas |
|---|---|---|---:|
| La referencia de industria de **D/E y cobertura de intereses** en Solidez | Damodaran la publica; el análisis la tiene en `benchmark.values` | `display`: la fila lleva referencia y brecha; la lectura sigue siendo la de los umbrales del sector. Los PDF pintan esta tabla con tres columnas y no cambian | 82 |
| Rivales: «Sin dato» donde el análisis decía **no aplica** o **no significativo** (P/E de una cíclica, D/E con caja neta, EV/EBITDA y ROIC de un banco, crecimiento de un REIT) | La fila de la página | `analysis_queue.summary` rellena las columnas de `[peers] summary_columns` con la cifra de la página o con «No aplica» / «n. s.» y el porqué en `note`. La tabla ya pinta `note` (title y lectores de pantalla) | 85 |
| El **porqué de «No aplica»** en las filas de múltiplos, rentabilidad, current ratio, D/E y ROCE | `classify.not_applicable` | `display._na_why`. Antes las filas pedían `a.not_applicable`, que solo guarda dcf, graham, altman, piotroski y roce. Los gráficos juntan cabecera y porqué («No aplica a REIT: …»). Incluye el EV/EBITDA con EBITDA ≤ 0 | 13 visibles + 26 del motor |
| La tarjeta **ROIC − WACC** de bancos, REIT y pre-beneficio, y la de CRWD y PLTR (ROIC no significativo) | `classify` y `key_metrics.roic_reason` | `display_charts`: el spread lleva el porqué; con el ROIC n. s., el spread es n. s. | 26 |
| **Crecimiento sin tasa** (BPA y FCF con año base ≤ 0: AMZN, BRK-B…) | `score_coverage.crecimiento.not_significant` | La barra pasa a `no_significativo` con el porqué | 8 |
| Aviso de **datos descartados** con nombres internos de Yahoo (`capitalLeaseObligations`, `commercialPaper`) | `_FIELD_NAMES` | Nombres en español | 7 |
| «La serie del sector es sin dato» (MC.PA) | `market_context` sabía que cotiza en EUR y los ETF de referencia son de EE. UU. | `series_reasons` y el aviso dice el porqué | 2 |
| Cobertura de intereses de AAPL y NVO sin motivo | `data_validation`: los gastos financieros y la cobertura de Finnhub eran de otro periodo | La tarjeta lo dice | motor |
| P/E adelantado y PEG de MC.PA sin motivo | `data_provenance.fields.forwardEps`: la fuente no lo devolvió | La fila lo dice | motor |
| Deuda neta/EBITDA n. s. en la portada de RIVN y SNOW sin motivo | La lectura del análisis | `cover.kpis[].text` (opcional; tipo `Kpi.text` en `lib/api.ts`) | motor |
| **BRK-B sin titulares** | Finnhub escribe las acciones de clase con punto (`BRK.B`: 250 titulares; `BRK-B`: 0) | `finnhub_fallback.provider_symbol`, solo para titulares, que no puntúan. Separador en `[finnhub] class_share_separator` | 1 |

Además, dos correcciones en la misma zona:

- **Ejercicios de 52/53 semanas.** Con cierre a primeros de enero son del año anterior (`[history] fy_year_shift_days`).
  JNJ mostraba «2017» y «2023» dos veces en la historia de 10 años.
- **Crecimiento en Rivales.** El `value` de la columna era la CAGR agregada a 3 años y el texto, la cifra que puntúa.
  Ahora las dos son la de la fila. FCX daba +4,4 % con el texto −7,39 %; había 13 tickers así.

Tres más que destaparon los fixtures completos:

- **Titulares de terceros y el guardián.** El guardián de redacción ya declaraba los titulares como texto «externo»
  (`lib/prose.py`), pero su lista negra los revisaba igual: «Premium» o «Grid» en un titular en inglés fallaban. Los
  8 titulares de antes pasaban por suerte.
  - Ahora `tests/guardian.py` quita los textos «externo» de `display` y del PDF antes de la lista negra y de la regla
    de nombres en inglés.
  - Lo que el motor escribe sigue igual de vigilado: los tests de detección pasan.
- **Mojibake en un resumen de Finnhub** (DOW: «2027â\x80\x9328»). Los controles C1 no tienen glifo en el PDF.
  `market_context.clean_external` lo recompone («2027–28») y, si no puede, los quita.
- **PDF v2, rango de 52 semanas.** Con la serie de 5 años completa, en CAT y JNJ la barra quedaba sola arriba de una
  página, con la cifra del precio sin su rótulo. El subtítulo, el contexto y la barra van ahora en un bloque que no se
  parte (`pdf_v2.doc.Unit`).

Motivos nuevos que el motor da y la web aún no pinta:

- **`display.extended.history_10y.rows[].reasons`.** Por qué falta el margen operativo, el BPA diluido, el capex o
  el FCF de un ejercicio: EDGAR no trae el concepto XBRL estándar del emisor. Afecta a JNJ, DOW, V, SHEL, BRK-B,
  NEE, TM y a los bancos.
  - Mientras la ficha no lo pinte, sigue el «—» (clase a, presentación).
  - Completar esos años con Yahoo mezclaría fuentes en una misma serie, y cambiar los conceptos de EDGAR movería la
    historia que puntúa (ciclicidad, persistencia, DCF inverso). Ver «Decisiones para el PM».

### (c) Faltaba en los fixtures del replay (recaptura)

Los 28 tickers del panel fuera de los 8 de verificación no tenían en el replay segmentos, gráfica de 5 años,
titulares ni calendario. El backend real los trae.

| Fuente | Qué se ha capturado | Notas |
|---|---|---|
| EDGAR | Segmentos de 27 tickers (`tests/capture_segments.py`) | 24 con desglose. HSBC, NFLX y PGR no desglosan en XBRL: clase (a), con su motivo. El replay da lo mismo que la descarga en vivo. Todos los informes anuales usados son anteriores a la captura de su ticker (el más justo, MU: 10-K del 9-oct, captura del 14-oct) |
| Yahoo | Serie de 5 años de 28 tickers y de los ETF que faltaban (XLV, XLP, XLI, XLB, XLC) | `capture_history.py --since 2021-10-01`, opción nueva. Bajada «a 5 años» 12 días después, la serie cortada en la captura no cubría 5 años y la rentabilidad a 5 años salía «Sin dato». Sin splits posteriores a ninguna fecha de corte. RIVN cotiza desde el 10-nov-2021 (clase a) |
| Finnhub | Titulares y calendario de 36 tickers | La ventana de titulares acaba al día siguiente de la captura (antes, en el día de hoy). Finnhub devuelve solo los más recientes de la ventana: en las grandes, todos eran posteriores a la captura y el corte los quitaba todos (MSFT, NVDA, AMZN, MU, NFLX: 0; TSM: 2; AAPL: 63 → 160). Se recapturaron también los 8 originales con el mismo criterio. El calendario guarda fechas y estimaciones pero **no las cifras reales publicadas después de la captura** (`calendar_until_capture`), para que el replay no vea resultados que el análisis de ese día no tenía. MC.PA: 403, Finnhub gratuito no cubre París (clase a). Sin `token=` en ningún fixture (comprobado) |

- El doble de Finnhub del replay (`fixture_backend`) traduce `BRK.B` al ticker en análisis.
- Tests de invariantes: segmentos y gráfica de 5 años para todo el panel, y titulares y calendario cortados en la
  captura.
- Lo que el replay no puede fijar: las **fechas anunciadas de próximos resultados** son las que publicaba el calendario
  el 26-oct (24 tickers pasan de «estimada» a «anunciada»). Es lo mismo que ya pasaba con los 8 originales, capturados
  el 18-oct.

## Rivales del replay (decisión del PM: opción B)

- **Criterio.** Cada ticker del panel con rivales propuestos tiene **al menos 3 analizados** en el replay; se
  priorizan los más citados.
  - Subconjunto mínimo: **68 empresas**.
  - SPY (ETF) y V (referencia del mercado) no tienen rivales propuestos.
- **Captura.** `tests/fixtures/peers/<T>/*.json.gz`, con el mismo método que el panel: `capture_fixtures.py --env panel
  --render-sim --gzip`, Finnhub activo y verificación de que el replay reproduce byte a byte la corrida en vivo.
  - Su EDGAR va en `tests/fixtures/peers/f2b`: lista de emisores, filings, calendario y hechos XBRL, con los `.json`
    comprimidos. 67 de 68 tienen CIK; AEF.V no presenta en la SEC.
  - El juego del panel no cambia: los rivales no tienen golden ni entran en las pruebas del panel, y el diff de los
    golden sale «sin diferencias».
  - **Tamaño en el repo: 10 MB** (7,2 MB de juegos y 2,8 MB de EDGAR).
- **Lectura.**
  - `fixture_backend.FixtureStore` lee `.json.gz` y busca en carpetas de respaldo.
  - `f2b_fixtures` hace lo mismo: fusiona la lista de emisores sin pisar la del panel.
  - El replay arranca con `extra_dirs=(tests/fixtures/peers,)`.
- **Los demás rivales no parecen un fallo.** En la cola de fondo del replay (rivales y tarjetas de la portada), una
  empresa sin datos grabados lleva el motivo «No incluido en la demo con datos grabados; con datos reales se analiza
  al momento». Es clase (c) propia del replay.
  - La tarjeta de la portada dice «No incluido en la demo».
  - El 404 del análisis de una página sigue con su texto: la pantalla de carga lo prueba.
- **Comprobado en el replay.** Los 35 tickers con rivales tienen 3 o más analizados. Los 63 huecos restantes
  llevan el motivo de lector.
- **Tests.** `tests/test_v4b_rivales.py`: 3 rivales grabados por ticker, sin red; lectura comprimida; un rival grabado
  se analiza y uno sin datos da el motivo. Backend: 5609 pasan. E2E de portada, carga y API: 104 pasan.
- **Portada.** El e2e del cintillo usaba TSLA como «valor sin análisis en caché». TSLA es ahora un rival grabado, así
  que el test usa META.

## Decisiones para el PM

1. **Rivales sin fixtures en el replay (161 marcas, 117 rivales distintos).** *Resuelto: opción B con 3 rivales por
   ticker; ver «Rivales del replay».*
   - (A) No capturar ninguno.
   - (B) Mi recomendación: un subconjunto de 15–20, los más citados, para que cada ticker tenga al menos 2 rivales
     analizados.
   - (C) Los 117: unos 45 MB y 2–3 h.
   - En producción se analizan en vivo: es (c) solo del replay.
2. **Referencia de industria para más métricas.** Damodaran publica P/S y EV/Ventas (`psdata`), rentabilidad y payout
   del dividendo (`divfund`) y crecimiento histórico (`fundgr`). No los importamos, y por eso hay 2088 celdas de
   Industria y Brecha sin referencia. Importarlos daría lectura a filas que hoy no la tienen y movería la puntuación
   de Valoración. Necesita tu aprobación y un GOLDEN_DIFF de veredictos.
3. **Rivales de V.** V se compara con el mercado por decisión del motor (Madura dentro de financials), así que no tiene
   industria con la que proponer rivales. Damodaran sí la clasifica por símbolo (`Financial Svcs. (Non-bank &
   Insurance)`, igual que MA y AXP). Usarla solo para proponer rivales no cambia ningún veredicto.
4. **Símbolo de Finnhub para BRK-B** también en métricas, calendario y sorpresas de resultados. Hoy solo los titulares
   usan `BRK.B`; en lo demás cambiaría cifras del análisis de BRK-B.
5. **Historia de 10 años con otros conceptos de EDGAR o con Yahoo** (BPA de V, SHEL, BRK-B; margen operativo de JNJ,
   DOW, SHEL; capex de NEE y TM). Toca la historia que usan la ciclicidad, la persistencia y el DCF inverso.

## Presentación (para el PM, para E3)

El motor ya tiene el motivo; la página pinta un hueco, «—» o «Sin dato». Por orden de marcas:

| Dónde | Qué pinta hoy | Qué tiene el motor | Marcas |
|---|---|---|---:|
| Calidad · Solidez y Crecimiento | Columnas Industria y Brecha vacías en todas las filas | `sections.solvency.columns` y `sections.growth.columns` son de tres columnas (MÉTRICA, VALOR, LECTURA); solo D/E y cobertura traen referencia | 1.099 |
| Valor, Calidad · Rentabilidad, historia · «Lo que exige el precio» | «—» en Industria y Brecha y Lectura vacía en las métricas sin referencia (P/E adelantado, PEG, P/FCF, FCF yield, dividendo, ROA, ROCE…) | `display.benchmark` y `benchmark.sources`: Damodaran solo publica P/E, EV/EBITDA, P/B, ROE, ROIC, márgenes, cobertura y D/E. Basta un «sin referencia publicada» por tabla o por fila | 1.008 |
| Negocio · Estados anuales | Celda CAGR vacía en los márgenes | Un margen no se compone: «—» con nota o la variación en puntos | 130 |
| Calidad y Valor · desglose de la puntuación | «Sin dato» en el valor de un ajuste «No aplica» | El ajuste trae `reason`; el valor no aplica | 86 |
| Historia · capítulos Rivales y Riesgos | Caja de relleno «— / Sin dato» cuando hay menos cifras | Nada que pintar: la fila debería ser más corta | 45 |
| Calidad · tarjeta ROIC − WACC | «Sin dato» | `charts.profitability.spread.text` (V4b) | 26 |
| Negocio · ficha del ejercicio | «—» en margen operativo, BPA, capex y FCF | `display.extended.history_10y.rows[].reasons` (V4b) | 24 |
| Calidad · tarjeta ROCE | «Sin dato» | `charts.profitability.roce.text` | 18 |
| Valor · sensibilidad | Columnas de WACC con «—» | `sensitivity.trimmed.note` («WACC recortado en [6 %, 20 %]: se omiten 4,0 % y 5,0 %»); la tabla no debería pintar esas columnas | 18 |
| Negocio · CAGR del beneficio y del FCF | «—» | Base ≤ 0: CAGR no definido | 12 |
| Conclusión · tarjetas | «Sin dato» en margen neto y ROE de REIT y pre-beneficio | `summary.cards[]`: `state: no_aplica`, `pill: "No aplica"` y el motivo en `bench` | 10 |
| Historia · rivales de V | «—» en Calidad | `peers.note`: sin industria de referencia | 3 |

Más, sin marca en el recuento:

- La cobertura de intereses de AAPL y NVO en Calidad dice «Sin dato: el proveedor no lo da», que es un texto de la
  web. El motor da ahora el porqué en `charts.solvency.gauges[].text`.
- `cover.kpis[].text` es nuevo (opcional) para las cifras de la portada no significativas.

## Pruebas

- **Backend:** 5571 pasan (suite completa). Vitest: 146. `npm run check` y `tsc`, limpios.
- **E2E completa contra el build:** 1109 pasan, 540 omitidos por proyecto y 3 fallan. Ninguno de los 3 es de esta
  rama.
  - `e2e/v1/panel.spec.ts` · PLD (claro y oscuro): «historia · simetría: negocio: hueco de 77px en la columna de
    texto». Lo destapan los datos: PLD ya tiene segmentos y el visual del capítulo Negocio es más alto que su texto.
    Contra la base (fcb87a6) pasa. Es maquetación de la historia (E3), del mismo tipo que el de SHEL.
  - `e2e/v2/v6b.spec.ts:91` · E7 (sondeo de rivales con reloj simulado): inestable, falla 2 de 3 también contra la
    base. Para E3.

## Cambios de los golden (GOLDEN_DIFF)

- `tests/diff_golden.py` (panel y local), `pdf_v2_golden.py` y `contract_forced.py`, regenerados.
- Bloques que cambian: solo «[otros]» y «[pdf]», nunca score, Piotroski, Altman, DCF, grid, alertas ni métricas.
  - Titulares y próximos resultados (recaptura).
  - Referencia y brecha de D/E y cobertura.
  - Porqués de «No aplica» y «no significativo».
  - `market_context.series_reasons`.
  - `history_10y` (`reasons` y años fiscales de JNJ).
  - Avisos con nombres en español.
  - En el texto de los PDF: titulares y avisos.
- `tools/verdicts_vs_main.py --ref HEAD`: **0 cambios** en los 11 campos de veredicto de los 43 golden.
