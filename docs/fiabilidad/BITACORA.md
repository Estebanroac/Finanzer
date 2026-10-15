# Bitácora del plan de fiabilidad

> **Lee esto primero en cada chat nuevo.** Es el estado vivo del trabajo. El plan (qué, cómo y por qué) está en
> [`../PLAN_FIABILIDAD.md`](../PLAN_FIABILIDAD.md). El historial técnico detallado está en [`../RECON.md`](../RECON.md) §7.
> Los prompts de cada fase están en [`prompts/`](prompts/).

## Cómo se usa este archivo

- **Al empezar una sesión:** lee "Estado actual", la fila de la fase en curso y las últimas 3 entradas del registro.
- **Al terminar una sesión** (aunque se quede a medias), **añade una entrada al registro** con la plantilla del
  final y actualiza "Estado actual" y la tabla de fases. Una sesión que no deja entrada no ocurrió.
- **Nunca borres entradas.** Si algo resultó falso, añade una entrada nueva que lo corrija y enlace a la anterior.
- Dos tipos de chat: **planificación** (no toca código; decide fases y revisa) y **operador** (escribe código de
  una fase). El operador no salta de fase ni toma decisiones D# por su cuenta: las propone y se detiene.

## Estado actual

| Campo | Valor |
|---|---|
| Fase en curso | **Fase 2a 🛑 detenida en el punto de parada 1** (T0 y T2 hechas; T1 pendiente del cierre de Nueva York). Registro #17 |
| Rama de trabajo | `fiabilidad/f2a-medir` (desde `main` = `8ed57a0`), sin push |
| Producción | `8ed57a0` (fase 1 + documentación). Rollback de código: `9e78f3b` |
| `main` local | = `origin/main` (`8ed57a0`) |
| Último cierre de sesión | 2026-10-15 · operador F2a (ver registro #17) |
| Bloqueos | Ninguno; T1 (captura de HSBC, SHEL, UL y TM) espera al cierre de Nueva York |

## Fases

| Fase | Estado | Rama | Commits | Aprobada por el usuario | Deploy |
|---|---|---|---|---|---|
| 0 Congelar y medir | ✅ cerrada (2026-10-14) | `fiabilidad/f0-panel` → `main` local | `0a8ac66`..`0ae214a` (9 commits) + cierre (registro #6) | sí, 2026-10-14 (registro #6) | no aplica (se sube con el deploy de la fase 1) |
| 1 Lo visible hoy | ✅ cerrada | `fiabilidad/f1-visible` | `d676b22` (D8), `21c3f5f`, `0ebba81` (guardián), `d63de70`…`d7393fd` (T3, 8 commits), `7f32070`, `e3161d2`, `c369575` (T4) | — | — |
| 2 Verdad de datos (EDGAR) | 🛑 2a: parada 1 (T2) | `fiabilidad/f2a-medir` | `8d3a5cc` (planificador), `356f49c` (T0), `0b82c13`, `aa42104` (T2) | — | — (T0 se despliega en la parada 2 si se aprueba) |
| 3 Método por arquetipo | 🔒 espera F2 | — | — | — | — |
| 4 Escalas y confianza | 🔒 espera F3 | — | — | — | — |
| 5 Técnica y conductual | 🔒 espera F4 | — | — | — | — |
| 6 Infraestructura | 🔒 diagnóstico en F2 | — | — | — | — |
| 7 Vigilancia / calibración | 🔒 vigilancia tras F0 | — | — | — | — |

Leyenda: ⏳ pendiente · 🔧 en curso · 🛑 detenida esperando al usuario · ✅ cerrada · 🔒 bloqueada por puerta

## Decisiones (D1–D7 del plan, §6)

| # | Tema | Estado | Decidido | Fecha |
|---|---|---|---|---|
| D1 | Códigos internos en el PDF | **decidida** | Anexo técnico: los códigos salen de las páginas de lectura y se reúnen en un anexo final del PDF rotulado "Detalle técnico para auditoría"; la web no los muestra (usuario, chat de planificación). Se aplica en la fase 1 (`prompts/F1_lo_visible_hoy.md`) | 2026-10-14 |
| D2 | Papel de SEC EDGAR | **decidida (fase de medida)** | Verificar y luego decidir: en la 2a EDGAR no alimenta el motor; con el informe de discrepancias (`F2_DISCREPANCIAS.md`) el usuario decide si pasa a fuente principal de los estados (usuario, chat de planificación). Reforzada al cerrar F0: Render ≠ local en 7/30 | 2026-10-15 |
| D3 | Precio con un solo método (RECON §7.17) | abierta · **prioridad alta en la fase 3** (18/30 del panel con un solo método evaluable; registro #6) | — | — |
| D4 | Arquetipo "crecimiento rentable" | abierta · debe resolver también **qué pesa más cuando una empresa es cíclica y de alto crecimiento a la vez** (NVDA; registro #6) | — | — |
| D5 | Capa técnica en el score | abierta | — | — |
| D6 | Infraestructura | abierta | — | — |
| D7 | Universo de empresas | **decidida** | Emisores registrados en la SEC (10-K y 20-F con CIK en EDGAR). Los demás se analizan con aviso visible ("sin fuente oficial para verificar") y confianza limitada a "baja"; no se rechazan (interpretación del planificador, modificable por el usuario). Diseño en la 2a, implementación en la 2b | 2026-10-15 |
| D8 | `golden/prod` ya no representa producción (base anual frente a TTM; registro #2) | **decidida** | Se retiran los juegos `prod` y `muestra` (fixtures y golden); se queda `local`. Se hace al principio de la fase 1, en un commit propio (registro #6) | 2026-10-14 |

Decisiones nuevas que surjan en una sesión: se añaden aquí como D8, D9… con estado "abierta" y el operador se detiene.

**D8 — contexto para decidir (operador F0, 2026-10-14).** Los fixtures `prod` (capturados en Render el 11-oct con
`/api/_capture`) no traen estados trimestrales, así que con el código actual su replay se calcula en base **anual**,
mientras que prod calcula hoy en **TTM** (`data_provenance.ttm.basis` anual → ttm en JPM y NFLX). `golden/prod`
describe un camino que producción ya no recorre. Opciones (sin decidir): (a) congelarlo como histórico y sacarlo de
la regresión; (b) mantenerlo en la regresión como caso "plan B sin trimestrales" (sigue siendo una ruta posible si
Yahoo deja de servir los trimestrales), renombrado para que no se lea como "producción"; (c) sustituirlo por el
juego `panel` (que ya contiene los 6 tickers) y borrarlo. La fase 0 no lo toca: la regla prohíbe regenerarlo.

## Mapa de pendientes → fase

Siembra inicial (2026-10-14). **La fase 0 completa este mapa** recorriendo todos los pendientes abiertos de RECON
§7.x y asignando cada uno a una fase, o marcándolo como descartado con su motivo.

| Pendiente | Origen | Fase |
|---|---|---|
| ✅ Hecho (F1, `7f32070` + `e3161d2` + `c369575`): maquetación de la página 2 del PDF (panel "Composición" recortado/solapado); comprobación geométrica en verde en 30 + 6 | corrida 2026-10-14 | 1 |
| ✅ Hecho (F1, `d63de70`): PLTR "EBIT negativo" con EBIT +$2.63B → estado `sin_carga` (rating AAA; nivel de precio sin cambio) | corrida 2026-10-14 | 1 |
| ✅ Hecho (F1, `87c147d` + `51e8f96`): "STRONG" en JPM; "MATURE"/"por_defecto" en el PDF → castellano y anexo técnico (D1) | corrida 2026-10-14 | 1 (D1) |
| Piotroski FY frente a TTM (AAPL) / bases mezcladas plan B (AMZN) | corrida + memoria 11b | 2 |
| JNJ sin Altman (utilidades retenidas) | corrida 2026-10-14 | 2 |
| TSM forward P/E 18.9 frente a TTM 31.7 (¿ADR/ordinaria?) | corrida 2026-10-14 | 2 |
| Beta de Finnhub en ADR (NVO 1.64 frente a 0.59) | memoria 11b | 2 |
| Yahoo 401 en Render, fuente nunca "alta" | RECON §7.1 | 2 / 6 |
| PLTR, NVDA, CRWD sin arquetipo propio | corrida 2026-10-14 | 3 (D4) |
| CAT, DOW como "Madura"; TSM `ciclica_condicional_estable` | corrida 2026-10-14 | 3 |
| Crecimiento del DCF (CAGR 3a frente a interanual, AAPL) | corrida 2026-10-14 | 3 |
| Precio con un solo método evaluable | RECON §7.17 | 3 (D3) |
| **Nuevo (panel):** 18/30 con un solo método de precio evaluable → **D3 con prioridad alta en la fase 3** | F0 (registros #5, #6) | 3 (D3) |
| Cobertura de intereses en utilities | memoria 11b | 3 |
| BRK-B posible cíclica / conglomerado | RECON §7.16 | 3 |
| AMZN sin categoría Crecimiento (base ≤ 0) | corrida 2026-10-14 | 3 |
| Calidad saturada en 100 (PLTR, TSM, NFLX, V) | corrida + RECON 7.14 | 4 |
| Producción atiende en serie; PDF de 20–60 s; JPM 46.1 s en frío (14-oct, 14:28) | corrida 2026-10-14 + F0 | 6 (D6) |
| Etapa 10 del spec: capa conductual + noticias | redesign-spec §5 | 5 |
| Rf y prima de riesgo con revisión mensual | RECON §7.13 | 7 |
| Fecha de resultados no se lee en ninguna ruta (bug f): necesaria para PEAD | RECON §7.7 | 5 |
| Crecimiento de Finnhub sospechoso (FCX −24.2% frente a +1.8% en estados): desde 9b ya no puntúa (el DCF y Crecimiento usan el CAGR de los estados), pero se muestra como dato "(interanual)" | RECON §7.7 / §7.15 | 2 |
| Plan B sin `lastSplitFactor` (un estado sin ajustar por split anularía la comparación de acciones) | RECON §7.7 | 2 |
| Forward EPS sin fuente en prod (Finnhub da forward P/E, no BPA) | RECON §7.7 / §7.5 | 2 |
| Crecimiento bancario con "Total Revenue": medirlo con margen de intereses neto o ingresos netos | RECON §7.8 | 3 |
| Bandas paralelas: alinear las de las alertas (cobertura, DCF, beta, DN/EBITDA) con las del score; "cuatro copias de umbrales" | RECON §7.9 / §7.14 / PLAN §1 | 4 |
| Benchmarks y medianas sectoriales PROVISIONALES sin fuente (market P/E 23x, ROE 20%/8%, D/E 1.0x…; forward market 18.9x) | RECON §7.14 / §7.16 | 4 |
| Bandas de REIT (DN/EBITDA ≤5.0x…) y de utilities (cobertura ≥3.5x…) PROVISIONALES, sin muestra | RECON §7.14 / 61212c1 | 4 |
| MATURE de dividendo alto (≥ 4%): Crecimiento como retorno total, propuesto sin aplicar (faltaba fixture; el panel trae KO, PG, JNJ, DOW) | RECON §7.11 / §7.14 | 3 |
| SBC en MATURE (> 5% de ingresos): propuesto sin aplicar (faltaba fixture; el panel trae PLTR, CRWD, SNOW, NVDA) | RECON §7.14 | 3 |
| Techo de la calidad cuando la lectura tiene señales en contra (NFLX 100 con P/E no fiable y DCF por debajo) | RECON §7.12 / §7.13 (a) | 4 |
| Confianza "alta" con convergencia solo "media" (V local 0.80) | RECON §7.13 (c) | 4 |
| Número de Graham calculado en REIT con BPA deprimido por la depreciación (se muestra, no vota) | RECON §7.13 (b) | 3 |
| Descartado — **verificado en la web** (F1 T6, registro #13): la barra de 52 semanas de la web (`Range52Bar`, "contexto, sin juicio") muestra solo la posición, sin tono de curva en U; coincide con el PDF | RECON §7.14 | — |
| Mejoras aprobadas: P/FFO visible en la web (no es un defecto; decisión del planificador en el prompt F1) | memoria (backlog) | mejoras, después de la fase 4 |
| Mejoras aprobadas: DuPont del ROE, margen FCF con tendencia, Rule of 40 (crecimiento rentable) | memoria (backlog) | 3 (D4) |
| ✅ Hecho (F1, `d676b22`): `golden/prod` en base anual mientras prod calcula en TTM → D8: `prod` y `muestra` retirados | F0 (registros #2, #6, #7) | 1 (inicio) |
| **Nuevo (panel):** Yahoo devuelve a Render datos distintos que a una IP residencial en 7/30 (acciones de fast_info en PG y NEE; balance trimestral de DUK al 31-mar en Render frente al 30-jun en local; acciones diluidas trimestrales ausentes en CAT y DUK; balance en el Altman de NVDA; acciones en MSFT; trimestres con resultado operativo en PLD). Local es estable. Efecto en el veredicto: DUK calidad 71 → 74, sin cambio de nivel. **Refuerza D2** | F0 (registros #5, #6) | 2 (D2) |
| **Nuevo (panel):** el crecimiento de ciclo medio está en su cota en 5 cíclicas (XOM y DOW −5.0% en ingresos y BPA; FCX BPA −5.0%; MU y ASML +10.0%). **Texto** ✅ hecho (F1, `eac35b3`: "acotado al mínimo/máximo que admite el modelo"); **método** del tope −5%/+10% → fase 3 | F0 (registros #5, #6) | 1 (texto) / 3 (método) |
| ✅ Hecho (F1, `83e0f70`): invariante `growth_texts_cite_the_scored_figure` acepta el signo expresado con el verbo; 0 xfail | F0 (registros #5, #6) | 1 |
| **Nuevo (panel):** efecto frontera: NVO cambia de nivel de precio con 10 pb de Rf (config 5.29% → ^TNX 5.19%: 58 "razonable" → 70 "atractivo", confianza media → alta). Banda de tolerancia o aviso de proximidad al umbral | F0 (registros #5, #6) | 4 |
| **Nuevo (panel):** BRK-B en base anual (faltan capex y D&A en algún trimestre) | F0 (registro #5) | 2 |
| ✅ Hecho (F1, `eac35b3`): "(3 años)" en la comparación de cíclicas cuya cifra es de ciclo medio → "(ciclo medio)" | F1 T2 (registro #9) | 1 (texto) |
| ✅ Hecho (F1, `90ab32a`): V (benchmark de mercado) decía "múltiplos frente al sector" en la confianza | F1 T2 (registro #9) | 1 |
| **Nuevo (guardián):** BRK-B "P/E (TTM)" con base anual (faltan trimestres). **Texto** ✅ hecho (F1, `f6f0b36`: "P/E (último ejercicio)"); dato (trimestres que faltan) → fase 2 | F1 T2 (registro #9) | 1 (texto) / 2 (dato) |
| ✅ Hecho (F1, `d7393fd`): AMT atribuía la caída del FFO por acción a la emisión de acciones con las acciones planas en 3 años (+0.05%) | F1 T2 (registro #9) | 1 |
| ✅ Hecho (F1, `87c147d`): "N/A" como valor en las tablas → "—" | F1 T2 (registro #9) | 1 |
| ✅ Hecho (F1, `51e8f96`; falta recompilar `frontend/out` en T6): la web mostraba códigos en el desplegable "Detalle técnico", contra D1 | F1 T2 (registro #9) | 1 (web) |
| **Nuevo (panel):** con la tabla validada (registro #6): CAT y TSM deberían ser CYCLICAL y salen "Madura"; PLTR y CRWD salen "Madura" (falta el arquetipo, D4); NVDA a decidir en D4 | F0 (registros #5, #6) | 3 (D4) |
| **Nuevo (F1 T3.1):** NFLX trae en 2026-03 un trimestre con +2.85 B de ingresos financieros (los demás, 40–50 M); el TTM del resultado financiero sale +2.14 B con el anual en −604 M. Sin efecto hoy (cobertura positiva; "sin carga" exige el signo en cada trimestre). Revisar la fuente | F1 (registro #10) | 2 |
| ✅ Hecho (F1, `ff6c591`): XOM "cotiza en el 101% del rango de 52 semanas" → el rango incluye la cotización actual (max/min con el precio, con traza en `data_provenance`); el guardián exige posición 0–100 | F1 (registro #11) | 1 |
| ✅ Hecho (F1, `7c5f044`): tarjetas "No aplica" con cifra (AMT, SNOW, O, PLD, RIVN) → "—" y el motivo; regla #10 del guardián implementada (`no_aplica_con_cifra`) | F1 (registro #11) | 1 |
| ✅ Hecho (F1, `b4935d7`): KPI de portada "Deuda neta/EBITDA" negativo (PLTR, TSM, MSFT, MU, NVDA, CRWD, ASML) → "Caja neta" y su importe; guardián `ratio_negativo_en_tarjeta` | F1 (registro #11) | 1 |
| ✅ Hecho (F1, `d676b22`): `muestra` retirada con D8; sus 17 tests corren sobre el panel (`test_panel_cases.py`) | F0 (registros #2, #6, #7) | 1 (inicio) |
| Descartado — resuelto, **verificado en el panel**: `yearly_financials` con datos en 30/30 (AAPL: 4 ejercicios) | RECON §7.7 | — |
| Descartado — resuelto, **verificado en el panel**: normalización de partidas no recurrentes (C1): `earnings_normalization.items` en 12+ tickers (MSFT, KO, JNJ, JPM, V, O…); NFLX `differs` = true | RECON §7.7 | — |
| Descartado — resuelto, **verificado en el panel**: financieras con el YoY de los estados: `data_validation` = `crecimiento_financiera_estados` en JPM, BAC, PGR y BRK-B | RECON §7.8 | — |
| Descartado — resuelto en la etapa 8, **verificado en el panel**: impuesto efectivo (`tax_rate.source` = efectiva en 26/30; legal 21% en RIVN, AMZN, DOW, SNOW sin beneficio; ninguno en el 25% fijo); WACC mostrado = usado (`key_metrics.wacc` = `dcf.wacc` = `wacc.value` en 19/19 con DCF); sin suelo terminal (AAPL `dcf.growth_rate` 1.8% < terminal 2.5%). Celdas del grid recortadas: **sin verificar** (ningún caso del panel llega al tope) | RECON §7.9 | — |
| Descartado — resuelto, **verificado en el panel**: crecimiento muy negativo en cíclicas ya no pasa a +8% (XOM, DOW: ciclo medio −5.0%). Ver la fila nueva de la cota del ciclo medio | RECON §7.9 | — |
| Descartado — resuelto, **verificado en el panel**: V = MATURE (`classification.rule` = red_de_pagos); JPM fila D/E "No aplica a entidades financieras". La UI no se verifica con el panel (**sin verificar** en la web) | RECON §7.9 | — |
| Descartado — resuelto en las etapas 6–8, **verificado en el panel**: ramas (JPM `piotroski_f.applicable` = false; O `key_metrics.p_ffo` 13.7; SNOW y RIVN GROWTH_PRE_PROFIT; FCX DCF con FCF de mantenimiento 3.65 B). Base anómala de NFLX: **sin verificar** (no se aisló en el panel) | RECON §7.10 | — |
| Descartado — resuelto, **verificado en el panel**: crecimiento por acción (`growth_basis.basis` = por_accion en O, PLD, AMT, PLTR, CRWD, RIVN, SNOW) y DCF de mantenimiento en cíclicas (FCX) | RECON §7.11 | — |
| Descartado — resuelto en F0, **verificado en el panel**: TTM en prod (`data_provenance.ttm.basis` = ttm en 29/30; BRK-B cae al anual porque faltan capex y D&A en algún trimestre, con aviso: ver fila nueva) | RECON §7.12 / §7.13 | — |
| Descartado — resuelto, **verificado en el panel**: motivos de la confianza en lenguaje llano (invariante `confidence_reasons_translated` pasa en 30/30) | RECON §7.14 | — |
| Descartado — obsoleto (no requiere verificación): PDF de revisión desde los fixtures de prod; lo sustituye `panel_run` | RECON §7.14 | — |
| Descartado — resuelto, verificado en git (no en el panel): golden de la 9b regenerados en 18a6a0c | RECON §7.15 | — |
| Descartado — resuelto en la 11b, **verificado en el panel**: BRK-B P/E 17.0 y BPA 31.0 (clase B); ASML `operating_cash_flow` 12.2 B (alias IFRS); plan B sin reintentos (`yahoo.http_statuses` = [401, 401, 200, 200] en los 31: un solo plan B) | RECON §7.16 | — |
| Descartado — resuelto en la 11b, **verificado en el panel**: TSM convertida de TWD (`data_provenance.currency.converted` = true, factor ADR 5.0, P/E 31.3); BRK-B P/E 17.0; SPY 422; NEE `dcf_status` = no_aplica (utility); "CYCLICAL" y "$-8" fuera de la prosa (invariante `no_archetype_codes_nor_sign_after_symbol` pasa en 30/30; los códigos siguen en la línea del detalle técnico del PDF: fila D1) | memoria (deploy 9b) | — |
| Descartado — sin efecto material, **sin verificar** (era una diferencia entre juegos local/prod, no aplica al panel): SNOW con deuda neta en local y caja neta en prod | RECON §7.13 | — |
| **Nuevo (BCS, informe de prod del 15-oct revisado por el usuario con un analista externo):** dividend yield **50.46%** imposible (≈ $11.50 por ADR sobre $22.79). Hipótesis del planificador: `dividendRate` en **peniques leído como libras** (×100) y **sin factor ADR** (÷4), ≈ 25×; real probablemente ~2% (verificar contra el dividendo declarado). Arrastra el shareholder yield (54.32%) y "Dividendo sostenible (50.46%)" en la salud financiera (que además cita el yield donde debería evaluar el payout). **Fase 1 (antes del push):** guardián de identidades datos↔datos (dividend yield ≈ payout × E/P y ≈ dividendos pagados / capitalización; shareholder yield = dividendo + recompras) → si no cuadra, "sin dato" + aviso; "dividendo sostenible" evalúa el payout. **Fase 1 ✅ hecha** (`bfc38e9` identidad y sin dato; `8c860be` dividendo sostenible por payout). **Diagnóstico confirmado (registro #13):** el yield viene de Finnhub `/stock/metric`, que para BCS da la línea de Londres de la acción ordinaria **en peniques** (`dividendIndicatedAnnual` 11.5); el motor lo divide por el precio del ADR en dólares: peniques (×100), sin factor ADR (÷4.154) y **sin conversión GBP→USD** (÷1.342) → ≈ 18×; real ≈ 2.8%. **Fase 2:** arreglar la unidad, el factor y la moneda en origen | usuario, 2026-10-15 | 1 (guardián) / 2 (origen) |
| **Nuevo (F1, identidad del dividendo):** el mismo defecto de origen que BCS en **TSM** (6.05%: 26 TWD por acción ordinaria sobre $430 del ADR; real ≈ 0.95%), **NVO** (30.69%: 11.7 DKK sobre $38; real ≈ 4.8%) y **NVDA** (0.45%: `dividendIndicatedAnnual` = 1 de Finnhub; el dividendo es $0.04, ≈ 0.02%). Desde `bfc38e9` salen "sin dato" con aviso. Arreglar en origen: `dividendIndicatedAnnual` de Finnhub en moneda y acción de la línea local | F1 (registro #13) | 2 |
| **Nuevo (F1, producción 15-oct):** UL (fuera del panel) habría mostrado un dividend yield del **251.70%** (mismo defecto de origen de Finnhub, línea local en otra moneda); la identidad lo deja "sin dato". Entra en el arreglo de origen | F1 (registro #15) | 2 |
| **Nuevo (F1, producción 15-oct):** JNJ: Finnhub **impone** su `epsTTM` (6.5886) sobre el BPA TTM derivado de Yahoo (8.62) por diferir >2%, con los trimestres de Yahoo aún en junio (probablemente Finnhub ya incluye el trimestre nuevo): bases mezcladas, P/E 30.1x → 39.4x y nivel de precio razonable → exigente. Regla de imposición de Finnhub a revisar | F1 (registro #15) | 2 |
| **Decidido (usuario, 2026-10-15, registro #14):** las **filas de tabla** con "No aplica" pasan a la misma regla que las tarjetas: "—" y el motivo, sin cifra (también la tabla de valoración: el FCF yield de BCS del 29.31% no debe verse). **Cambia la regla de la etapa 9b** (que mostraba la cifra con "No aplica") por decisión del usuario; su test se ajusta | F1 (registros #13, #14) | 1 |
| **Nuevo (usuario, 2026-10-15):** decidir qué métricas aplican de verdad a FINANCIAL. El P/E y el dividend yield son métricas legítimas de un banco; hoy salen como "no aplica" | usuario, registro #14 | 3 |
| **Nuevo (usuario, 2026-10-15):** el control de identidad del dividendo solo detecta rentabilidades **infladas**; falta el sentido contrario (unidad 100 veces menor), resolviendo el caso de los dividendos extraordinarios como PGR (yield indicado 0.19% frente a 6.6% pagado) | usuario, registro #14 | 2 |
| **Nuevo (F2a, T3; corrección de la 2b):** **NVDA es un falso positivo del control de identidad del dividendo de la fase 1, en producción.** El dato de Finnhub (`dividendIndicatedAnnual` = 1.00) es **correcto**: NVDA subió el trimestral de 0.01 a 0.25 en el 2T de su año fiscal 2027 (10-Q del 2026-07-26), y 0.25 × 4 = 1.00. El control compara el indicado con lo pagado en los últimos 12 meses (ventanas distintas) y lo deja en "sin dato". Diseño en F2_PRECEDENCIA §2.2: comparar magnitudes equivalentes (DPA declarado de EDGAR frente al pagado, en la misma ventana) y no anular un aumento verificado (último declarado × frecuencia = indicado). Corrige la fila de TSM/NVO/NVDA: NVDA no tiene el dato roto en origen | F2a (T3, registro #17) | 2 (2b) |
| **Nuevo (F2a, T4; para la 2b):** deuda total de **DUK** +1.1% (970 millones de USD) sobre EDGAR. Hipótesis: Yahoo suma el arrendamiento operativo no corriente (≈ 1,000 millones; 1,033 a 2025-12-31), el patrón de MSFT y NVDA; DUK solo etiqueta los arrendamientos en el 10-K. Con la regla de F2_PRECEDENCIA §2.3 sobra ese operativo y faltan 576 millones de arrendamiento financiero. En la 2b: usar el arrendamiento del último FY con aviso de fecha cuando no hay etiqueta trimestral | F2a (T4, registro #17) | 2 (2b) |
| **Nuevo (F2a, T4; para la 2b):** deuda total de **O** +6.2% (1,930 millones de USD; EDGAR 29,252 = notas + préstamos + papel comercial). Hipótesis: (1) hipotecas o línea de crédito con conceptos propios de O; (2) intangibles de arrendamientos por debajo de mercado (1,457) + pasivos por arrendamiento (528) = 1,985. En la 2b: leer el balance del 10-Q del 2T para decidirlo | F2a (T4, registro #17) | 2 (2b) |
| **Nuevo (BCS):** factor ADR **4.154** frente a **4** oficial: se infiere de acciones del balance (31-dic) / acciones de hoy, y las recompras entre ambas fechas (~3.9%) se cuelan en el factor. Desvía ~3.9% todas las cifras por acción. Usar el ratio oficial del depositario (o ajustar al entero cercano dentro de tolerancia, declarándolo) | usuario, 2026-10-15 | 2 |
| **Nuevo (BCS):** bancos europeos con **AT1** (instrumentos híbridos contabilizados como patrimonio): el ROE/ROTE contable (10.0%) frente al RoTE reportado (12.2%); los cupones AT1 deben restarse del beneficio y los AT1 del patrimonio tangible; el payout de "dividendos pagados" puede incluir cupones AT1 | usuario, 2026-10-15 | 2 (datos) / 3 (método) |
| **Nuevo (BCS):** "ROTE implícito en el precio" para bancos: con P/TBV 0.81, Ke 11%, g 2.5% → ROTE ≈ 9.4% descontado, frente al reportado y al objetivo de la gerencia (sensibilidad). Equivalente bancario del reverse DCF | usuario, 2026-10-15 | 3 |
| **Nuevo (BCS):** beta **1.64** idéntica a la de NVO (Finnhub en ADR, ya sospechosa): verificar contra una beta calculada sobre la serie de precios | usuario, 2026-10-15 | 2 |
| ✅ Hecho (F1, `48a0242`): etiqueta "P/B frente a ROE 0.95× justificado" → "95% del P/B justificado (0.73x frente a 0.76x)", ídem P/TBV | usuario, 2026-10-15 | 1 |
| **Nuevo (proceso):** el panel no tiene emisores que reporten en peniques ni bancos europeos. Ampliarlo al inicio de la fase 2 con BCS, HSBC, SHEL, UL y TM (GBp/EUR/JPY, distintos factores ADR, AT1). En la fase 1 basta con capturar BCS para probar el guardián de identidades (✅ `3f2138b`, grupo "Revisión externa") | planificador, 2026-10-15 | 1 (BCS) / 2 (resto) |
| **Nuevo (ROCE, usuario 2026-10-15):** el ROCE se calcula (AAPL 68.72%; promedio de ciclo en cíclicas) pero en la web es la **última fila de "Tabla de rentabilidad y eficiencia", plegada por defecto** (desde la 9b); solo se ve la nota de divergencia ROCE–ROIC. La fila no tiene referencia, brecha ni lectura ("Antes de impuestos"). En FINANCIAL/REIT "No aplica" (correcto). **Fase 1 (T6):** subirlo al bloque visible de Rentabilidad junto a ROIC − WACC (con el promedio de ciclo en CYCLICAL) y al resumen del PDF, sin cambiar cálculos. **Fase 4:** referencia por sector, bandas de lectura y ROCE promedio como prueba de persistencia de la calidad | usuario + planificador, 2026-10-15 | 1 (visible) / 4 (bandas) |
| **Nuevo (infra):** Render **apaga el servicio sin tráfico** ("Service waking up" al abrir finanzer.app el 15-oct): explica buena parte de los 46–52 s en frío, además de la atención en serie | planificador, 2026-10-15 | 6 (D6) |
| **Revisión externa F1 (UL, planificador 2026-10-15):** "Los ingresos se contraen un 3.4% anual" → DCF con g −3.4% → alerta "Sobrevalorada según DCF −40%". Probable **cambio de perímetro** (escisión de helados/Magnum a finales de 2025; verificar en los estados): los años comparados no son homogéneos. El motor no detecta escisiones/desinversiones (operaciones discontinuadas, salto de ingresos) | planificador, 2026-10-15 | 2 (detectar) / 3 (crecimiento sin el perímetro) |
| **Revisión externa F1 (TXRH):** referencias por **sector amplio** (consumer_cyclical) para un restaurante: "Margen bruto 15.7% vs 35% muy inferior". Hace falta referencia por **industria** | planificador, 2026-10-15 | 4 |
| **Revisión externa F1 (TXRH):** lecturas ciegas al modelo de negocio: current ratio < 1 "Tensión" (normal en restauración/comercio con capital circulante negativo); Altman Z'' y Piotroski castigados por pasivos por arrendamiento (ASC 842) | planificador, 2026-10-15 | 3 |
| **Revisión externa F1 (TXRH):** DCF con g = CAGR histórico 13.5% sin convergencia al largo plazo y fiabilidad "alta" (el CAGR incluye inflación de precios) | planificador, 2026-10-15 | 3 |
| **Revisión externa F1 (BCS):** P/B 0.73x frente a 1.50x "del sector" (bancos de EE. UU.): "descuento profundo −51%". Hace falta referencia por **geografía** (los bancos europeos cotizan estructuralmente más bajo por menor ROE) | planificador, 2026-10-15 | 4 |
| **Revisión externa F1 (UL):** factor ADR 1.012 frente a 1 oficial (mismo defecto que BCS: recompras en el factor) | planificador, 2026-10-15 | 2 |
| **Prioridad (JNJ):** las reglas de **precedencia de fuentes** (qué fuente manda y con qué periodo) son el núcleo de la fase 2: Finnhub sustituyó el BPA por uno con el trimestre nuevo mientras los estados siguen en junio (periodos mezclados → cambio de nivel en producción) | planificador, 2026-10-15 | 2 (alta) |
| **Nuevo (proceso):** revisión externa al cierre de cada fase: 2–3 tickers **fuera del panel**, contrastados con un analista independiente (como hizo el usuario con BCS). Se añade al protocolo de PLAN_FIABILIDAD §5 | planificador, 2026-10-15 | todas |

## Registro de sesiones

<!-- Plantilla (copiar al final, numerar en orden):

### #N · AAAA-MM-DD · <planificación | operador> · Fase X
- **Objetivo de la sesión:**
- **Hecho:** (con hashes de commit)
- **Verificación:** (comandos ejecutados y resultado: suite, golden, panel, PDF)
- **Decisiones tomadas por el usuario:** (cita literal de la aprobación)
- **Abierto / siguiente paso:**
- **Archivos tocados:**
- **Avisos para el siguiente chat:** (gotchas, cosas a no repetir)
-->

### #1 · 2026-10-14 · planificación · antes de la fase 0
- **Objetivo de la sesión:** evaluar el motor en producción y definir el plan de fiabilidad.
- **Hecho:** corrida de 12 tickers (AAPL, JPM, O, XOM, KO, JNJ, NEE, CAT, PLTR, AMZN, TSM, RIVN) contra
  finanzer.app: los 12 en 200. Salida en `~/Downloads/finanzer_corrida_2026-10-14/` (PDF, JSON de análisis, texto
  extraído, PNG por página). Redactados `docs/PLAN_FIABILIDAD.md`, esta bitácora y `prompts/F0_congelar_y_medir.md`.
  Sin cambios de código. Sin commit.
- **Verificación:** resultados resumidos en PLAN_FIABILIDAD §1.
- **Decisiones tomadas por el usuario:** "un solo plan" — PLAN_FIABILIDAD sustituye al plan anterior y absorbe lo
  que quedaba (la etapa 10 pasa a ser la fase 5). RECON sigue siendo el historial. El código se hace en otro chat.
- **Abierto / siguiente paso:** abrir un chat de operador con `prompts/F0_congelar_y_medir.md`.
- **Archivos tocados:** `docs/PLAN_FIABILIDAD.md`, `docs/fiabilidad/BITACORA.md`,
  `docs/fiabilidad/prompts/F0_congelar_y_medir.md` (los tres sin commitear).
- **Avisos para el siguiente chat:** `main` local tiene `f9d6c30` sin push: no pushear sin orden (redespliega).
  Producción atiende en serie: no lanzar más de 12 peticiones paralelas contra finanzer.app.

### #2 · 2026-10-14 · operador · Fase 0 (T1–T2, detenida en el punto de parada 1)
- **Objetivo de la sesión:** T1 (rama y suite) y T2 (método de captura fiel a producción), hasta el punto de parada 1.
- **Hecho:**
  - T1: rama `fiabilidad/f0-panel` creada desde `main` local (`f9d6c30`). Sin commits.
  - T2, diagnóstico: la "simulación de Render" de la etapa 11b **no quedó como herramienta**; solo existe el test
    unitario `test_plan_b_is_not_retried_and_quote_summary_block_is_remembered` (monkeypatch de un 401). El juego
    `muestra` se capturó en local **por quoteSummary (200), sin plan B y sin Finnhub**: no representa producción.
  - T2, prototipo (fuera de `backend/`, sin commitear): `docs/fiabilidad/f0_t2_prototipo/render_sim_proto.py`
    (captura con Render simulado) y `compare.py` (diff de dos análisis con la procedencia de Finnhub). Evidencia en
    `f0_t2_prototipo/evidencia/` (análisis de prod en vivo de JPM y NFLX del 14-oct y los simulados).
  - T2, propuesta (pendiente de aprobación):
    - **Opción A (recomendada): captura local con Render simulado.** Sobre `fb.record` se añaden dos ganchos en
      `tests/`: S1, `quoteSummary` responde 401 con el cuerpo de prod ("Invalid Crumb"), y S2, `yfinance.Ticker.info`
      devuelve `{}` (en prod solo trae `trailingPegRatio`; el plan B solo lee `beta`). Todo lo demás (fast_info,
      estados anuales y trimestrales, sonda de moneda, tipos de cambio, búsqueda y Finnhub) va a la red real, con
      `.venv313` (mismas versiones que prod) y la clave de Finnhub exportada solo en la pestaña de terminal del
      usuario. Pros: no toca producción ni despliega, repetible, graba todo lo que consume el código actual.
      Riesgos: la IP residencial podría recibir algo distinto que la de Render en los endpoints sin crumb (no
      observado en JPM), y si Yahoo cambia en Render la simulación no se entera. Mitigación: `panel_run --mode live`
      compara cada vez contra finanzer.app (T4/T5).
    - **Opción B: reabrir `/api/_capture` en producción con token.** Datos reales de Render, pero exige desplegar
      (pushear `main` redespliega y arrastra `f9d6c30`), gestionar `CAPTURE_TOKEN` en Render, reescribir el endpoint
      (el de `e0be7d4` no graba trimestrales, moneda, tipos de cambio ni búsqueda), cargar un servidor que atiende en
      serie y volver a retirarlo. Descartada salvo orden expresa.
    - Opción C (solo corridas en vivo, sin fixtures): no reproducible; no sirve de vara.
- **Verificación:**
  - Suite antes de empezar: `cd backend && ../.venv313/bin/python -m pytest tests -q` → **597 passed, 1 skipped,
    0 xfail** (19.5 s).
  - Prototipo sin Finnhub: `.venv313/bin/python render_sim_proto.py <out> JPM NFLX` → los dos por
    `plan_b_yfinance`, quoteSummary `[401, 401]` como en prod, replay **idéntico byte a byte**, 0 accesos no grabados.
  - Contra `https://finanzer.app/api/analysis/{JPM,NFLX}` del mismo día (2 peticiones, 200 en 4.6 s y 3.8 s): en JPM
    **todas** las diferencias (51 de 649 campos) se explican por Finnhub ausente en local (beta, forward P/E, PEG,
    dividendo, crecimiento) y por la tasa libre de riesgo (prod usa ^TNX en vivo; los fixtures congelan la de config
    por diseño). Estados, precio, arquetipo, calidad y nivel de precio coinciden. En NFLX el nivel de precio cambia
    (exigente 42 → razonable 46), atribuible a los 11 campos de Finnhub; **sin verificar hasta repetir con Finnhub**.
- **Decisiones tomadas por el usuario:** ninguna todavía.
- **Abierto / siguiente paso:**
  1. El usuario, en su pestaña de terminal con `FINNHUB_API_KEY` exportada, corre el prototipo con Finnhub sobre JPM
     y NFLX; el operador compara con prod en vivo del mismo día (debe quedar solo la diferencia de Rf).
  2. Aprobación del método (A o B). Con A: llevar S1/S2 a `tests/` (p. ej. `capture_fixtures.py --env panel
     --render-sim`) y seguir con T3.
- **Archivos tocados:** `docs/fiabilidad/BITACORA.md` (esta entrada), `docs/fiabilidad/f0_t2_prototipo/` (nuevo).
  Nada en `backend/`. Sin commits.
- **Avisos para el siguiente chat:**
  - **`golden/prod` ya no representa producción:** prod calcula hoy en base **TTM** (lee los trimestrales), pero los
    fixtures `prod` del 11-oct no tienen trimestrales y su golden sale en base **anual** (`data_provenance.ttm.basis`
    anual → ttm en JPM y NFLX). Por eso la validación de T2 se hizo contra prod en vivo y no contra `golden/prod`.
    No se regenera (lo prohíbe la fase); lo sustituye el juego `panel`.
  - `backend/tests/README.md` lista 6 tests xfail de bugs conocidos, pero hoy hay 0 xfail: tabla desactualizada.
  - Los fixtures siempre usan la Rf de config; el modo `live` siempre diferirá en Rf frente al `replay` (F5).
  - La sesión se abrió en `finanzer_complete_v3`; el repo de trabajo es `~/Downloads/finanzer_next` (rutas absolutas).

### #3 · 2026-10-14 · operador · Fase 0 (T2 aprobada con condiciones; validación con Finnhub pendiente)
- **Objetivo de la sesión:** aplicar la aprobación de la opción A y validarla con Finnhub antes de capturar el panel.
- **Decisiones tomadas por el usuario:** "Apruebo la opción A, con estas condiciones: 1. Primero valida la captura
  con Finnhub de JPM y NFLX contra producción en vivo. Si queda alguna diferencia que no sea la Rf (en especial el
  nivel de precio de NFLX), detente y explícala antes de capturar el panel. 2. Lleva S1 y S2 a backend/tests/ como
  modo de capture_fixtures.py (p. ej. --render-sim). Saca los scripts del prototipo de docs/ (la evidencia puede
  quedarse). 3. Metadatos de cada fixture: render simulado (S1, S2), si Finnhub participó y Rf congelada. 4. En
  panel_run --mode live, separa en su propia sección las diferencias que vienen solo de la Rf. 5. Respeta el límite
  de Finnhub (60 peticiones por minuto) al capturar los 31 tickers. 6. Registra en la bitácora la decisión D8
  (abierta): qué hacer con golden/prod, que ya no representa producción. Corrige la tabla de xfail del README de
  tests."
- **Hecho (sin commits todavía):**
  - Condición 2: `fixture_backend.render_sim()` (S1, S2 y Finnhub a ≤ 1 petición cada 1.1 s ≈ 55/min, condición 5),
    constantes `PANEL_ENV`, `PANEL_GROUPS`, `PANEL_TICKERS`; `capture_fixtures.py --render-sim [--dir]` y
    `--env panel` (exige `--render-sim` y `FINNHUB_API_KEY`). Prototipo borrado de `docs/`; queda `evidencia/`.
  - Condición 3: metadatos nuevos `render_simulation` (S1, S2), `risk_free.frozen`, `yahoo.http_statuses`
    (además de `finnhub.participated`).
  - Condición 6: D8 ya la había añadido el chat de planificación; se quitó la fila duplicada que añadí y se dejó
    el párrafo de contexto con las opciones. README de tests: tabla de bugs conocidos corregida (0 xfail, 8 tests
    ya corregidos y en qué etapa) y sección "Captura con Render simulado".
- **Verificación:** `capture_fixtures.py --render-sim --dir <scratch> JPM` → `http=[401, 401, 200, 200]`,
  `path=plan_b_yfinance`, replay idéntico; `--env panel` sin `--render-sim` o sin clave → error explícito. Suite:
  `597 passed, 1 skipped` (17.3 s).
- **Abierto / siguiente paso:** el usuario corre en su pestaña (con la clave exportada)
  `cd ~/Downloads/finanzer_next/backend && ../.venv313/bin/python tests/capture_fixtures.py --render-sim --dir ../docs/fiabilidad/f0_t2_prototipo/captura_fh JPM NFLX`;
  el operador compara contra finanzer.app del mismo día separando las diferencias que solo vienen de la Rf
  (condición 1). Si queda algo más, se detiene y lo explica. Después: T3.
- **Archivos tocados:** `backend/tests/fixture_backend.py`, `backend/tests/capture_fixtures.py`,
  `backend/tests/README.md`, `docs/fiabilidad/BITACORA.md`, `docs/fiabilidad/f0_t2_prototipo/` (scripts fuera).
- **Avisos para el siguiente chat:** la bitácora la editan dos chats a la vez (planificación y operador): releerla
  justo antes de escribir y no duplicar filas.

### #4 · 2026-10-14 · operador · Fase 0 (T2: validación con Finnhub superada)
- **Objetivo de la sesión:** condición 1 de la aprobación: validar la captura con Finnhub de JPM y NFLX contra
  producción en vivo antes de capturar el panel.
- **Hecho:**
  - La clave de Finnhub vive en Render, no en el Mac; los comandos con `!` del chat abren un shell sin variables
    exportadas (cuatro capturas salieron sin Finnhub y se borraron). Solución: la clave se guardó en el **Llavero de
    macOS** (servicio `finanzer-finnhub`) con un diálogo de macOS en el que la pegó el usuario; las capturas la leen
    con `FINNHUB_API_KEY=$(security find-generic-password -s finanzer-finnhub -w)`, sin imprimirla ni escribirla.
  - `capture_fixtures.py --render-sim` ahora **se niega** a capturar sin clave (salvo `--sin-finnhub`).
  - Captura de validación en `docs/fiabilidad/f0_t2_prototipo/evidencia/captura_render_sim_finnhub/` (JPM, NFLX):
    `http=[401, 401, 200, 200]`, `path=plan_b_yfinance`, `degraded=False`, `finnhub=True` (12 y 11 campos), replay
    idéntico, sin secretos (`grep -rlE "token=|apikey"` vacío).
- **Verificación** (prod en vivo a las 14:28 del 14-oct, guardada en `evidencia/prod_live_*_1428.json`):
  - Arquetipo, calidad, nivel y puntuación de precio, confianza y veredicto **idénticos** en los dos. NFLX:
    "razonable 46" en ambos: la diferencia de la sesión #2 (exigente 42) venía solo de Finnhub.
  - Diferencias restantes: JPM 42 campos (7 solo por la Rf: config 5.29% frente a ^TNX 5.194%), NFLX 75 (27 solo
    por la Rf). El resto viene **del precio intradía** (JPM 333.66 → 333.77; NFLX 70.295 → 70.25) y su arrastre
    (capitalización, múltiplos, pesos del WACC).
  - Prueba: replay con el precio y la Rf de prod → **0 diferencias** en JPM y en NFLX (tolerancia relativa 1e-6).
  - Latencia de prod: JPM 46.1 s en frío (servidor en serie), NFLX 3.3 s.
- **Decisiones tomadas por el usuario:** no rotar la clave de Finnhub (quedó visible en una captura de pantalla del
  chat): "no lo quiero cambiar. deja esa api."
- **Abierto / siguiente paso:** visto bueno a la validación (además de la Rf queda el precio intradía, explicado y
  probado) → T3, captura de los 31 con `--env panel --render-sim`. Propuesta para la condición 4: `panel_run --mode
  live` separa dos secciones, "solo Rf" y "solo precio intradía", con el mismo método (replay con la Rf y el precio
  de prod); lo que quede fuera de ambas es diferencia real.
- **Archivos tocados:** `backend/tests/capture_fixtures.py`, `docs/fiabilidad/BITACORA.md`,
  `docs/fiabilidad/f0_t2_prototipo/evidencia/`.
- **Avisos para el siguiente chat:** no pedir al usuario que exporte variables ni que use `!` para secretos; usar
  el Llavero. Responder siempre en español.

### #5 · 2026-10-14 · operador · Fase 0 (T3–T7 hechas; detenida en el punto de parada 2)
- **Objetivo de la sesión:** T3 (panel), T4 (`panel_run`), T5 (línea base, con los dos ajustes del usuario), T6
  (mapa de pendientes) y T7 (cierre) hasta el punto de parada 2.
- **Decisiones tomadas por el usuario (citas literales):**
  - "Aprobado. Acepto tu propuesta para la condición 4: en panel_run --mode live, secciones separadas «solo Rf» y
    «solo precio intradía»; todo lo demás es diferencia real. Para la captura: si el mercado de EE. UU. sigue
    abierto, espera al cierre (16:00 Nueva York) para que los 31 compartan el precio de cierre del mismo día. Si ya
    cerró, captura ahora. Registra en la línea base la latencia de 46 s de JPM en frío (va a la fase 6). Sigue con
    T3 y T4 y detente en el punto de parada 2."
  - Ajustes de T5: "1. En el mapa de pendientes, marca cada descartado «resuelto» como «verificado en el panel» o
    «sin verificar», con la evidencia (ticker y campo). Si alguno no está resuelto, devuélvelo a su fase. 2. Separa
    los tests de invariantes en dos grupos [...] Corre los genéricos sobre los 31 del panel sin tocar el motor. Lo
    que fallen va al inventario de F3, con xfail estricto si hace falta para mantener la suite en verde."
  - "Visto bueno a test_invariants_detectan.py (bdc7690)." · "Espera al cierre de las 16:00 y captura a las 16:15,
    como acordamos."
- **Hecho:**
  - T3: 31 fixtures del panel capturados de 16:15 a 16:17 NY (plan B + Finnhub en los 31; SPY 422), sin secretos;
    31 golden; el panel en la regresión y el determinismo (`REG_ENVS`, no en `conftest.ENVS`).
  - T4: `tests/panel_run.py` (replay/live, `--compare`, solo Rf / solo precio / reales) con 6 tests; pypdfium2 4.30.0.
  - T5: `docs/fiabilidad/F0_LINEA_BASE.md`. Ajuste 2: `tests/invariants.py` (26 genéricos; los tests existentes
    delegan en él), `test_panel_invariants.py` (780 comprobaciones; 2 xfail estrictos: XOM y DOW) y
    `test_invariants_detectan.py` (los 26 detectan su violación). Ajuste 1: 12 descartados verificados en el panel
    con evidencia, 5 "sin verificar" con motivo; ninguno resultó no resuelto.
  - T6: mapa de pendientes completo (filas nuevas del panel marcadas "Nuevo (panel)").
  - T7: RECON §7.18; esta entrada.
  - Commits en `fiabilidad/f0-panel`: `0a8ac66`, `00ebda0`, `27be92e`, `c415ecc`, `79f9d59`, `bdc7690` y los de
    cierre de esta sesión (ver `git log`). Sin push ni merge.
- **Verificación:** suite `../.venv313/bin/python -m pytest tests` → **1538 passed, 1 skipped, 2 xfailed** (51 s).
  `panel_run --mode replay` y `--mode live` en `~/Downloads/finanzer_f0_panel_2026-10-14/`. Recaptura local de 7
  tickers: 6 idénticos (PLD solo precio) → la diferencia con prod viene de Yahoo en Render.
- **Abierto / siguiente paso (punto de parada 2):** el usuario valida la tabla de arquetipos esperados (TSM, ASML a
  decidir; BRK-B dudoso), decide sobre el invariante de crecimientos negativos (xfail XOM/DOW), D8 (`golden/prod`)
  y aprueba el cierre de la fase 0.
- **Archivos tocados:** `backend/tests/` (fixture_backend, capture_fixtures, conftest, diff_golden, test_regression,
  test_determinism, panel_run, test_panel_run, invariants, test_panel_invariants, test_invariants_detectan,
  test_display, test_coverage, test_validation, test_quality_price, test_muestra, test_display_charts, README,
  requirements), `backend/tests/{fixtures,golden}/panel/`, `docs/RECON.md`, `docs/fiabilidad/{BITACORA,F0_LINEA_BASE}.md`.
- **Avisos para el siguiente chat:** la Rf congelada hace que NVO salga "razonable" en replay y "atractivo" en prod;
  Yahoo da a Render datos distintos que a local en 7/30 (vigilar con `panel_run --mode live`); la clave de Finnhub
  está en el Llavero (`finanzer-finnhub`).

### #6 · 2026-10-14 · operador · Fase 0 cerrada
- **Objetivo de la sesión:** registrar la aprobación del cierre, aplicar las decisiones y mergear en `main` local.
- **Decisiones tomadas por el usuario (cita literal):**

  > Apruebo el cierre de la fase 0, con estas decisiones (regístralas en la bitácora con esta cita):
  > 
  >   1. Tabla de arquetipos esperados validada con estos cambios:
  >      - CAT: CYCLICAL (confirmado).
  >      - BRK-B: FINANCIAL válido (el P/B es la métrica de la propia empresa); la volatilidad de sus ingresos sigue en la fase 3.
  >      - TSM y ASML: esperado CYCLICAL.
  >      - NVDA: «a decidir en D4». D4 debe resolver qué pesa más cuando una empresa es cíclica y de alto crecimiento a la vez.
  >   2. Invariante growth_texts_cite_the_scored_figure (XOM, DOW): se ajusta en la fase 1 para aceptar el signo expresado con el verbo. El texto que presenta la cota del ciclo medio como dato medido (XOM, DOW, FCX, MU, ASML) va a la fase 1. El método del tope −5%/+10% va a la fase 3.
  >   3. Nuevos pendientes en el mapa:
  >      - Efecto frontera (NVO cambia de nivel con 10 pb de Rf): fase 4, banda de tolerancia o aviso de proximidad al umbral.
  >      - Render ≠ local en 7/30: refuerza D2, fase 2.
  >      - 18/30 con un solo método: D3 pasa a prioridad alta en la fase 3.
  >   4. D8 decidida: se retiran los juegos prod y muestra (fixtures y golden); se queda local. Se hace al principio de la fase 1, en un commit propio.
  >   5. Haz merge de fiabilidad/f0-panel en main EN LOCAL, sin push. Se subirá junto con el deploy de la fase 1.
  > 
  >   Cierra la fase 0 en la bitácora (estado, fila de la fase y D8) y detente. No empieces la fase 1.

- **Hecho:**
  - Decisión 1: `panel_run.EXPECTED` con la tabla validada (CAT, TSM y ASML CYCLICAL; BRK-B FINANCIAL sin "dudoso";
    NVDA "?" para D4) y su test. Recuento con el replay del panel (`~/Downloads/finanzer_f0_panel_2026-10-14/replay_tabla_validada`):
    **26/31 coinciden**; no coinciden CAT, PLTR, CRWD y TSM; NVDA a decidir. `F0_LINEA_BASE.md` actualizado.
  - Decisiones 2–4: mapa de pendientes (invariante y texto de la cota → fase 1; método del tope → fase 3; efecto
    frontera → fase 4; Render ≠ local → D2, fase 2; 18/30 un solo método → D3 prioridad alta en la fase 3;
    D8 decidida, `prod` y `muestra` se retiran al empezar la fase 1). Tabla de decisiones: D2 reforzada, D3
    prioridad alta, D4 con la pregunta de NVDA, D8 decidida.
  - Decisión 5: merge `--no-ff` de `fiabilidad/f0-panel` en `main` local, sin push (ver `git log`).
  - Estado actual y fila de la fase 0: ✅ cerrada. Fase 1: pendiente, sin empezar.
- **Verificación:** `pytest tests/test_panel_run.py` → 6 passed; suite completa en `main` tras el merge (ver el
  final de esta entrada en el mensaje de cierre del operador).
- **Abierto / siguiente paso:** la fase 1 empieza, cuando el usuario lo ordene, con D8 en un commit propio
  (retirar `prod` y `muestra`, fixtures y golden). El push de `main` va con el deploy de la fase 1.
- **Archivos tocados:** `backend/tests/panel_run.py`, `backend/tests/test_panel_run.py`,
  `docs/fiabilidad/{BITACORA,F0_LINEA_BASE}.md`.
- **Avisos para el siguiente chat:** `main` local va por delante de `origin/main` (f9d6c30 + fase 0): pushear
  redespliega producción. Al retirar `prod` y `muestra`, revisar los tests atados que los usan
  (`test_muestra.py`, ramas de `prod` en `test_cost_of_capital`, `test_normalize`, `test_ingestion`,
  `test_known_bugs`, `test_display_charts`, `test_frontend_contract`).

### #7 · 2026-10-14 · operador · Fase 1 (T0 hecha; detenida en el punto de parada 1)
- **Objetivo de la sesión:** T0 (D8) y T1 (diseño del guardián narrativo) hasta el punto de parada 1.
- **Hecho:**
  - Rama `fiabilidad/f1-visible` desde `main` local `0f798c8`.
  - T0 (`d676b22`, "F1: D8, retira los juegos prod y muestra"): fuera `fixtures/{prod,muestra}`, `golden/prod`,
    `import_prod_capture.py`, `supplement_prod_search.py` y `diff_golden --local-vs-prod`. `test_muestra.py` →
    `test_panel_cases.py` (los 17 tests, sobre el panel; PFE → KO para el grid con celda negativa). Tests atados a
    los 6 tickers: `conftest.BOUND_ENVS = [local, panel]` en lugar de `prod`. Casos que el panel ya no da con el
    mismo ticker: cobertura negativa con caja neta y ROIC no significativo → CRWD; base anual por trimestres
    incompletos → BRK-B; EBITDA < 0 con caja neta → sin caso en ningún juego, lo cubre
    `test_read_nde_net_cash_only_when_cash_exceeds_debt`.
  - T1: diagnóstico verificado y diseño en `docs/fiabilidad/F1_DISENO_GUARDIAN.md` (enfoque b + a enlazados, 19
    predicados, colector sin cambio de salida, prueba de que detecta).
- **Verificación:** suite tras T0 → `1474 passed, 1 skipped, 2 xfailed` (47 s). La bajada desde 1538 son 64 tests:
  los casos `prod` de la regresión y el determinismo (28) y de los 6 tests genéricos de `test_display` (36), cubiertos
  por los golden y los invariantes del panel.
- **Diagnóstico PLTR (verificado):** `interest_coverage_state` decide por el signo del cociente. PLTR no tiene gasto
  financiero en los estados del plan B; la cobertura −1.53 viene de Finnhub (ingreso financiero neto) con EBIT
  +2.63 B. El estado erróneo llega a 4 sitios: `display.read_coverage`, el motivo de `validate.py`, la Solidez y el
  **rating sintético del WACC** (`cost_of_capital.synthetic_rating`: BBB por regla M). CRWD: EBIT GAAP −119 M y
  gasto +26.6 M → su texto es correcto.
- **Decisiones tomadas por el usuario:** ninguna en esta sesión (las de la fase vienen del prompt F1 y de D1/D8).
- **Abierto / siguiente paso:** aprobación del diseño del guardián (y del tratamiento del WACC de PLTR en la misma
  causa que la cobertura). Después, T2 (guardián en rojo).
- **Archivos tocados:** `backend/tests/` (D8), `docs/fiabilidad/F1_DISENO_GUARDIAN.md`, `docs/fiabilidad/BITACORA.md`.
- **Avisos para el siguiente chat:** la bitácora tenía sin commitear el cambio del planificador en D1 (decidida:
  anexo técnico); va en el commit de esta entrada. `invariants.py` todavía nombra `test_muestra` en comentarios.

### #8 · 2026-10-14 · operador · Fase 1 (diseño del guardián aprobado; T2 en curso)
- **Decisiones tomadas por el usuario (cita literal):**

  > Apruebo el diseño del guardián con estos cambios:
  > 
  >   1. Red de seguridad también sobre el PDF: normaliza el texto extraído (espacios, guiones, saltos de línea). Cada palabra de afirmación que aparezca en el PDF debe poder rastrearse hasta una frase de display con afirmaciones declaradas; si no, falla. Lo mismo para cualquier frase propia de pdf_report.py.
  > 
  >   2. Gasto financiero de PLTR: busca primero en los estados del plan B (Interest Income, Net Interest Income, Net Non Operating Interest Income Expense o equivalentes). Solo si no existen, infiere el signo desde la cobertura de Finnhub, y deja en data_provenance que el dato es inferido.
  > 
  >   3. Rating del WACC de PLTR: sí, en el mismo commit que la cobertura de intereses (misma causa). Cuantifica en el diff el cambio de Kd, WACC, valor del DCF y nivel de precio. Con caja neta, el peso de la deuda debería ser casi cero; si el nivel de precio cambia, explícalo antes de seguir.
  > 
  >   4. Añade al catálogo:
  >      - #20 Base temporal: «(3 años)», «interanual», «TTM», «FY…» deben coincidir con la base real del dato (growth_basis, data_provenance.ttm).
  >      - #21 Contracción del precio: «sin ajustar X → ajustado Y por confianza Z» debe cuadrar con price_attractiveness (score_raw, score, factor) y con confidence.level.
  >      - Amplía la #6: si benchmark.profile = market, el texto debe decir «mercado», no «sector».
  > 
  >   Registra esta aprobación en la bitácora y sigue con T2 (guardián en rojo).

- **Hecho:** aprobación registrada; el diseño se amplía con #20, #21, la #6 con «mercado» y la red sobre el PDF
  normalizado (también frases propias de `pdf_report.py`). T2 en curso (ver la entrada siguiente).

### #9 · 2026-10-15 · operador · Fase 1 (T2: guardián narrativo en rojo)
- **Objetivo de la sesión:** implementar el guardián aprobado (registro #8) sin arreglar nada.
- **Hecho (`0ebba81`):**
  - `lib/claims.py`: afirmaciones declaradas junto al texto; colector (`contextvars`) activo solo en tests.
  - Instrumentación sin cambio de salida: lectores de `display.py` (en la llamada, con el campo que respalda cada
    afirmación), `read_vs_sector` por decorador, textos del motor que `display` pasa al informe (desglose, tarjetas
    institucionales, nota del WACC, confianza, filas y etiquetas con base temporal, criterios Piotroski, nota de
    clasificación) y señales de `alert_interpretations.py` por intérprete.
  - `tests/guardian.py`: 16 predicados (catálogo más #20 y #21), red de seguridad en el display y en el PDF
    normalizado (la palabra se rastrea por ventana de caracteres, porque pypdf puede intercalar columnas; las
    etiquetas cortas de celda valen por sí solas), lista negra y reglas #6/#7/#17/#20. Los tooltips (escalas de
    bandas) y las zonas de los gráficos no son afirmaciones sobre la empresa: fuera de la red, dentro de la lista
    negra. Las frases propias de `pdf_report.py` pasan por la misma red del PDF (no apareció ninguna sin respaldo).
  - `test_guardian.py`: (regla × juego × ticker) sobre 30 del panel + 6 de local, 85 xfail estrictos.
    `test_guardian_detecta.py`: los 16 predicados y cada mecanismo detectan su violación (25 tests).
- **Verificación:** `diff_golden.py --env local` y `--env panel` → sin diferencias. Suite → **2244 passed, 1 skipped,
  87 xfailed** (51 s).
- **En rojo (casos conocidos):** PLTR "EBIT negativo" (6 frases: lectura, desglose, motivo de validación…); "STRONG"
  en JPM, BAC, PGR, BRK-B; códigos internos en 30/30; cota del ciclo medio en XOM, DOW, FCX, MU, ASML.
- **Nuevos (al mapa, fase 1):** "(3 años)" en cifras de ciclo medio; V "frente al sector" con benchmark de mercado;
  BRK-B "TTM" con base anual; AMT atribuye la caída del FFO a una dilución inexistente; "N/A" en tablas; la web
  enseña códigos en "Detalle técnico".
- **Decisiones tomadas por el usuario:** ninguna nueva. (El commit `98cc1b2` lleva la entrada #8.)
- **Abierto / siguiente paso:** T3, un commit por causa.
- **Archivos tocados:** `backend/lib/{claims,display,alert_interpretations}.py`, `backend/tests/{guardian,test_guardian,test_guardian_detecta}.py`.
- **Avisos para el siguiente chat:** el guardián tarda ~5 s en los 36 informes.

### #10 · 2026-10-15 · operador · Fase 1 (T3: arreglos, un commit por causa)
- **Objetivo de la sesión:** T3 del prompt F1: convertir en verde los 85 xfail del guardián, una causa por commit.
- **Hecho:**
  - `d63de70` T3.1 cobertura de intereses por el signo del EBIT y del resultado financiero (*Net Non Operating
    Interest Income Expense* de los estados del plan B; sin inferir en ningún ticker). PLTR: `sin_carga`, rating
    BBB → AAA, Kd 6.40% → 5.69%, WACC −0.0003 pp (peso de la deuda 0.04%), DCF 44.22 sin cambio, Solidez ya en
    20/20: **nivel de precio sin cambio**. "Sin carga" exige el signo en el TTM y en cada trimestre (NFLX, ver mapa).
  - `87c147d` T3.2 "STRONG"/"N/A" en castellano en la capa de presentación (también en la web, `api.ts`).
  - `51e8f96` T3.3 D1: `display.annex` → anexo "Detalle técnico para auditoría" al final del PDF; tabla de
    confianza en lenguaje llano; la web deja de recibir y de mostrar el detalle técnico.
  - `eac35b3` T3.4 cota del ciclo medio dicha como cota; "(ciclo medio)" en la comparación de CYCLICAL.
  - `83e0f70` T3.5 invariante del crecimiento: signo con el verbo (y deja de aceptar "5.0%" positivo dentro de
    "se contraen un 5.0%"). 0 xfail en el panel.
  - `90ab32a`, `f6f0b36`, `d7393fd` T3.6: V "frente al mercado"; BRK-B "P/E (último ejercicio)"; AMT sin dilución
    inexistente.
  - `docs/fiabilidad/F1_DIFF_GOLDEN.md`: diff de golden explicado causa por causa (para T5).
- **Verificación:** suite → **72 failed, 2395 passed, 1 skipped, 0 xfailed**; los 72 son la comparación con los
  golden (36 análisis + 36 PDF), sin regenerar a propósito hasta el punto de parada 2. Guardián: 0 fallos, tabla
  de conocidos vacía. Cada cambio de golden, atribuido en `F1_DIFF_GOLDEN.md`; fuera de PLTR ninguna cifra cambia.
- **Decisiones tomadas por el usuario:** ninguna nueva.
- **Abierto / siguiente paso:** T4 (página 2 + comprobación geométrica + PNG); el anexo cambia el número de
  páginas en 14 PDF (revisar en T4). `frontend/out` se recompila en T6 (cambios de `api.ts` y `StockHeader.tsx`).
- **Archivos tocados:** `backend/lib/{financial_ratios,ttm,yf_adapter,data_fetcher,validate,cost_of_capital,alert_interpretations,display,display_charts,pdf_report}.py`, `backend/main.py`, `backend/tests/{guardian,invariants,test_guardian,test_guardian_detecta,test_invariants_detectan,test_panel_invariants,test_interest_coverage,test_presentacion_castellano,test_anexo_tecnico,test_cota_ciclo_medio}.py`, `frontend/src/{lib/api.ts,components/StockHeader.tsx}`.
- **Avisos para el siguiente chat:** la regresión de golden falla a propósito hasta T5; para ver solo lo demás,
  `pytest tests | grep -v matches_golden`.

### #11 · 2026-10-15 · operador · Fase 1 (T4 hecha; T5: detenida en el punto de parada 2)
- **Objetivo de la sesión:** T4 (maquetación del PDF y comprobación geométrica) y T5 (golden y panel) del prompt F1.
- **Hecho:**
  - `7f32070` página 2 en flujo natural y a ancho completo; la lectura en `KeepInFrame(shrink)` con el alto que
    queda (antes: alturas fijas 27/46/27%, composición 24 pt más estrecha, barras 12 pt más anchas que su celda,
    lectura montada sobre la composición en 32 de 36 PDF).
  - `e3161d2` `tests/pdf_geometry.py` (pypdfium2): texto dentro del área útil y sin solapes; prueba de que detecta en
    páginas sintéticas y en el código anterior a T4 (33 de 36). Encontró y se arreglaron en `data_table` dos
    defectos más: "No aplica a …" sobre la brecha (RIVN, SNOW) y el criterio de Piotroski sobre su detalle (24 PDF).
  - `c369575` el anexo técnico no se parte entre páginas (AAPL, SNOW).
  - `19449a1` apartado T4 de `F1_DIFF_GOLDEN.md`.
  - Revisión visual de las páginas 1 y 2 de un ticker por grupo (AAPL, JPM, AMT, NEE, XOM, PLTR, SNOW, TSM, NFLX):
    `~/Downloads/finanzer_f1_panel_2026-10-15/revision_visual/`. Sin defectos de maquetación; tres hallazgos de
    contenido al mapa (a decidir).
- **Verificación:** suite → **72 failed, 2508 passed, 1 skipped, 0 xfailed**: los 72 son la comparación con los
  golden (36 análisis + 36 PDF). Comprobación geométrica y página 2: 72/72 en verde. `panel_run --mode replay
  --compare ~/Downloads/finanzer_f0_panel_2026-10-14/replay_tabla_validada` → **0 cambios** de arquetipo, nivel de
  calidad, nivel de precio o confianza en los 31; solo cambia `paginas_pdf` en 18 (anexo y filas partidas).
- **Decisiones tomadas por el usuario:** ninguna nueva.
- **Abierto / siguiente paso:** **punto de parada 2**: aprobación del diff de golden (`F1_DIFF_GOLDEN.md`) para
  regenerarlos; decidir los tres hallazgos de la revisión visual. Después T6 (web, con `frontend/out` recompilado),
  T7 (merge y deploy con "ok, pushea"), T8 (cierre).
- **Archivos tocados:** `backend/lib/pdf_report.py`, `backend/tests/{pdf_geometry,test_pdf_geometry,test_anexo_tecnico,test_archetype_branches}.py`, `docs/fiabilidad/F1_DIFF_GOLDEN.md`.
- **Avisos para el siguiente chat:** el margen de la página 2 es estrecho (NFLX y SNOW quedan a 3–4 pt); si un texto
  crece, la lectura se contrae un poco en vez de desbordar. `test_page_2_holds_the_whole_summary` lo vigila.

### #12 · 2026-10-15 · operador · Fase 1 (punto de parada 2 aprobado)
- **Decisión del usuario (literal):**
  > Apruebo regenerar los golden de panel y local con el diff de F1_DIFF_GOLDEN.md. Regenéralos ahora, en un commit propio, para que los arreglos siguientes tengan su diff aislado.
  >
  > Después, antes de T6, cuatro cosas más dentro de la fase 1 (un commit por causa, con test que falla antes):
  >
  > 1. Punto ciego del guardián: la afirmación #10 («no aplica» con cifra) no detectó las tarjetas de AMT y SNOW. Explica por qué (¿las tarjetas KPI y metric_card no declaran afirmaciones?), haz que el guardián cubra todas las tarjetas de portada y resumen, y añade el caso a test_guardian_detecta.py. Arregla las tarjetas: si no aplica, valor «—» y el motivo, sin cifra.
  >
  > 2. Rango de 52 semanas: máximo = max(máximo, precio) y mínimo = min(mínimo, precio), para que la posición nunca pase de 0–100% (XOM «101%»). Añade al guardián que la posición citada está entre 0 y 100.
  >
  > 3. Deuda neta/EBITDA negativa en la portada (PLTR, TSM): se muestra «Caja neta» con su importe, igual que en la fila de Solidez. Ningún ratio negativo se presenta como nivel en una tarjeta.
  >
  > 4. Escala mínima del KeepInFrame(shrink) en la portada y en la página 2: la comprobación geométrica falla si la escala baja de 0.85. Reporta la escala mínima actual en el panel.
  >
  > Presenta en el punto de parada 3 el diff de estos cuatro arreglos (qué tickers y campos cambian) junto con la petición de «ok, pushea». No regeneres los golden de estos cuatro sin esa aprobación.
- **Hecho:** `da2b33e` golden de panel y `local` regenerados (72 archivos); suite **2580 passed, 1 skipped**.
- **Abierto / siguiente paso:** los cuatro arreglos (un commit por causa), T6 y punto de parada 3.

### #13 · 2026-10-15 · operador · Fase 1 (arreglos tras la parada 2, T6 y BCS; detenida en el punto de parada 3)
- **Instrucción del usuario (BCS, literal):**
  > Hallazgo nuevo de producción (BCS, informe del 15-oct revisado con un analista externo). Lee las filas «Nuevo (BCS)» del mapa de pendientes de la bitácora: las añadió el planificador.
  >
  > Dentro de la fase 1, antes del punto de parada 3 (un commit por causa, con test que falla antes):
  >
  > 5. Captura BCS en el panel con --render-sim, como caso de prueba. No amplíes más el panel: eso es del inicio de la fase 2.
  >
  > 6. Guardián de identidades (datos frente a datos, no texto): dividend yield ≈ payout × earnings yield, y ≈ dividendos pagados / capitalización, con una tolerancia que justifiques. Shareholder yield = dividend yield + buyback yield. Si una identidad no cuadra, la cifra sale «sin dato» con aviso en data_validation y no puntúa. Debe dispararse en BCS (hoy 50.46%) y en ningún ticker del panel que esté bien. Con prueba de que detecta.
  >
  > 7. «Dividendo sostenible (X%)» en la salud financiera bancaria: evalúa y cita el payout, no el dividend yield.
  >
  > 8. Etiqueta «P/B frente a ROE 0.95× justificado» (y P/TBV): reescríbela para que no parezca el múltiplo justificado, p. ej. «cotiza al 95% del P/B justificado (0.73x frente a 0.76x)».
  >
  > No toques en esta fase el origen del dato (peniques/libras, factor ADR 4.154 frente a 4, AT1, beta de Finnhub): es de la fase 2. Solo diagnostica y anota en el mapa la causa confirmada del 50.46%: verifica si dividendRate viene en peniques y sin factor ADR, que es la hipótesis del planificador.
  >
  > Incluye estos cuatro arreglos en el diff que presentarás en el punto de parada 3.
- **Hecho (un commit por causa; golden sin regenerar):**
  - `7c5f044` tarjetas "No aplica" sin cifra; regla #10 del guardián (no estaba implementada). `ff6c591` rango de 52
    semanas con la cotización actual (XOM 101% → 100%). `b4935d7` caja neta en la portada en lugar de un ratio
    negativo. `c09ee29` escala mínima 0.85 del contenido encogido (mínimas: portada 0.936 TSM, página 2 1.000).
  - T6: `8ca3718` `npm run check` reparado (leía `golden/prod`, retirado en D8); `b3309a8` en la web la
    cobertura "sin carga" se leía "No significativo" (hallazgo de T6); `450a4d4` `frontend/out` recompilado.
    Verificado en el navegador con un servidor local que sirve el mismo análisis que los tests (replay del panel,
    ruta de producción): PLTR "sin carga financiera neta" y "Caja neta $9.20B"; JPM "sólida", sin "STRONG" ni "N/A";
    XOM 100% y "acotado al mínimo"; AMT tarjetas "—"; ningún código ni "Detalle técnico". La barra de 52 semanas de
    la web solo muestra la posición (RECON §7.14: descartado, verificado).
  - BCS: `3f2138b` en el panel (render-sim, 10:11 intradía); `359f06a` "Gran descuento" declarado (guardián);
    `bfc38e9` guardián de identidades y dividend yield sin dato si no cuadra (tolerancia 2.0 por arriba, justificada
    en `F1_DIFF_GOLDEN.md` P3.7); `8c860be` dividendo sostenible por payout; `48a0242` etiqueta del P/B justificado.
  - **Diagnóstico del 50.46%:** confirmado y ampliado (mapa): peniques, sin factor ADR y sin conversión GBP→USD
    (≈ 18×). La identidad destapa el mismo defecto en TSM, NVO y NVDA (mapa, fase 2).
- **Verificación:** suite → **45 failed, 2832 passed, 1 skipped**: los 45 son la regresión de golden de 22 tickers
  (19 del panel, 3 de `local`; BCS sin golden). Guardián, invariantes, geometría y contrato de la web en verde.
  `panel_run --mode replay --compare …/replay` (la corrida aprobada en la parada 2): ningún cambio de arquetipo,
  nivel de calidad, nivel de precio ni confianza en los 31; `validaciones` +1 en TSM, NVO y NVDA; BCS nuevo
  (FINANCIAL, calidad 75 sólida, precio 50 razonable, confianza media).
- **Decisiones tomadas por el usuario:** la de BCS (arriba).
- **Abierto / siguiente paso:** **punto de parada 3**: aprobación de los golden de estos arreglos (y del nuevo de
  BCS) y "ok, pushea". Con ella: regenerar golden (commit propio), merge en `main` local, suite en verde, push,
  verificación en producción (T7) y cierre (T8). A decidir: "No aplica" con cifra en las filas de tabla.
- **Avisos para el siguiente chat:** el servidor de replay para la web está en el scratchpad de la sesión
  (`serve_replay.py`: parchea `main._compute_analysis` con `fb.run_analysis`); recrearlo si hace falta.

### #14 · 2026-10-15 · operador · Fase 1 (parada 3 aprobada con condiciones)
- **Decisión del usuario (literal):**
  > Apruebo regenerar los golden del diff P3.1–P3.9 de F1_DIFF_GOLDEN.md, en su propio commit.
  >
  > Decisión sobre las filas «No aplica» de las tablas: misma regla que las tarjetas, «—» y el motivo, sin cifra (también la tabla de valoración: el FCF yield de BCS del 29.31% no debe verse). Ajusta el test de la 9b que protegía lo contrario y anota en la bitácora que la regla cambia por decisión del usuario.
  >
  > Antes del deploy, dos puntos más (un commit por causa, con test que falla antes):
  > - Punto 9 (ROCE visible): mira la fila «Nuevo (ROCE)» del mapa. ROCE en el bloque visible de Rentabilidad, junto a ROIC − WACC (y el promedio de ciclo en CYCLICAL), y en el resumen del PDF. En FINANCIAL y REIT, «No aplica». Sin cambiar cálculos ni inventar bandas (eso es de la fase 4). Guardián: la cifra citada = key_metrics.roce redondeado.
  > - La regla de las tablas que acabo de decidir.
  >
  > Añade al mapa de pendientes:
  > - Fase 3: decidir qué métricas aplican de verdad a FINANCIAL. El P/E y el dividend yield son métricas legítimas de un banco; hoy salen como «no aplica».
  > - Fase 2: el control de identidad del dividendo solo detecta rentabilidades infladas; falta el sentido contrario (unidad 100 veces menor), resolviendo el caso de dividendos extraordinarios como PGR.
  >
  > Ok, pushea, con esta condición: si el punto 9 y la regla de las tablas solo cambian presentación (en el panel ningún cambio de cifra, arquetipo, nivel de calidad, nivel de precio ni confianza frente a la corrida aprobada), regenera esos golden en su propio commit, haz merge a main con la suite y el guardián en verde, pushea y verifica producción con panel_run --mode live frente a la corrida F0 live. Si cambia cualquier otra cosa, detente y preséntamelo sin pushear.
  >
  > Ten en cuenta que Render apaga el servicio sin tráfico: la primera petición tras el deploy tardará. No lo cuentes como fallo; despiértalo antes de medir.
  >
  > Después del deploy, en T8, deja preparada la revisión externa (punto 11 del protocolo): los PDF de producción de BCS, UL y una empresa mediana de EE. UU. fuera del panel, para que yo los contraste con un analista independiente.
- **Hecho:** `b25e75e` golden de P3.1–P3.9 regenerados y el de BCS creado; suite **2877 passed, 1 skipped**.
- **Regla que cambia por decisión del usuario:** "No aplica" en las filas de tabla, sin cifra (antes, etapa 9b, con
  cifra). Mapa: filas nuevas de fase 3 (métricas de FINANCIAL) y fase 2 (identidad del dividendo a la baja).

### #15 · 2026-10-15 · operador · Fase 1 (punto 9, regla de tablas, deploy y cierre T8; esperando aprobación)
- **Hecho:**
  - `617fd0c` filas "No aplica" de las tablas sin cifra (regla de la 9b cambiada por decisión del usuario; el test
    de la 9b exige ahora "—"). `2f8c652` ROCE visible en Rentabilidad (web) y en "Creación de valor" del resumen del
    PDF, con la comparación con el ROIC como lectura (sin bandas) y guardián del ROCE. `b0f8aee` golden
    regenerados tras verificar la condición del usuario (solo presentación: `panel_run` replay sin cambios en los 32;
    diff sin campos fuera de `display`). `3ef6b24` `frontend/out` recompilado. Verificado en el navegador (XOM:
    ROCE 11.12%, promedio del ciclo 16.89%; JPM: "ROCE · No aplica" con su motivo).
  - Merge `4e90ff6` en main: suite 2915 passed, guardián 1144, contrato 37 salidas. **Push `9e78f3b..4e90ff6`** a
    las 10:41; sello servido a las 10:43. `panel_run --mode live` frente a F0 live: NVO por Rf y precio (frontera),
    JNJ por el dato (Finnhub impone `epsTTM`), BCS nuevo; nada atribuible al código (`DEPLOY_VERIFICATION.md`).
  - T8: RECON §7.19; métricas F3 de cierre (abajo); revisión externa preparada en
    `~/Downloads/finanzer_f1_revision_externa_2026-10-15/` (PDF de producción de BCS, UL y TXRH, con `LEEME.md`).
- **Métricas F3 de cierre frente a la línea base (37 informes: 31 del panel sin SPY + 6 de `local`):**

| Métrica | Línea base (F0 / entrada de F1) | Cierre |
|---|---|---|
| Contradicciones de cifra (guardián) | PLTR "EBIT negativo"; 85 xfail del guardián al entrar | **0** |
| Palabras en inglés fuera del anexo | STRONG en 4 financieras; códigos de arquetipo en 30/30 | **0** |
| Códigos internos fuera del anexo | 30/30 | **0** (anexo presente en 37/37) |
| Defectos de maquetación | página 2 en todos (32/36 con la comprobación geométrica) + 2 tablas | **0** (escala mínima: portada 0.936, página 2 0.968) |
| Fallos del guardián | 85 (T2) | **0** de 1112 comprobaciones |
| xfail de invariantes del panel | 2 (XOM, DOW) | **0** de 808 |
| Identidad del dividendo | — | dispara en 4 (BCS, TSM, NVO, NVDA), todas con el dato roto en origen |

- **Decisiones tomadas por el usuario:** registro #14 (aprobación con condiciones y regla de las tablas).
- **Abierto / siguiente paso:** aprobación del cierre de la fase 1; revisión externa con el analista. Los commits de
  documentación del cierre (este registro, RECON §7.19, `DEPLOY_VERIFICATION.md`) están en `main` local sin
  pushear: subirlos redespliega Render sin cambio de código.

### #16 · 2026-10-15 · operador · Fase 1 cerrada
- **Aprobación del usuario (literal):**
  > Apruebo el cierre de la fase 1. Regístralo en la bitácora con esta cita y pushea el commit de documentación (b143b0f), más los cambios del planificador que haya en BITACORA.md (filas «Revisión externa F1» y «Prioridad (JNJ)» del mapa). No cambies esas filas: inclúyelas tal cual.
  >
  > Revisión externa hecha por el planificador sobre BCS, UL y TXRH: no hay fallos de fase 1. Los hallazgos son de datos y de método y quedan en el mapa (fases 2, 3 y 4). Después del push, verifica que el sello de build cambió y detente. No empieces la fase 2.
- **Hecho:** filas del planificador commiteadas tal cual; push de la documentación del cierre (`b143b0f`, este
  registro y las filas del planificador). Sin cambios de código.
- **Abierto / siguiente paso:** fase 2 (no empezada). Rollback de producción: `9e78f3b`.

### #17 · 2026-10-15 · operador · Fase 2a (T0 y T2 hechas; detenida en el punto de parada 1)
- **Objetivo de la sesión:** fase 2a (medir): T0, T1 y T2 hasta el punto de parada 1.
- **Hecho:**
  - **T0:**
    - `8d3a5cc`: ediciones del planificador sobre D2 y D7, tal cual;
    - `356f49c`: `/api/health` devuelve `commit` desde `RENDER_GIT_COMMIT`, `null` en local, con test.
  - **User-Agent de la SEC:** guardado en el Llavero (`finanzer-sec-ua`) mediante un diálogo del sistema. No aparece
    en el chat ni en ningún archivo.
  - **T2:**
    - `0b82c13`: `tests/edgar.py`, `tests/edgar_diag.py`, `tests/test_edgar_tools.py` y los extractos por ticker en
      `tests/fixtures/edgar/` (7.9 MB; la caché cruda `raw/`, de 127 MB, queda fuera de git);
    - `aa42104`: `F2_EDGAR_DIAGNOSTICO.md`.
  - **Hallazgos de T2:**
    - los 36 tickers tienen CIK (SPY sin estados) → **ningún caso D7 en el panel**;
    - factores ADR confirmados en el 20-F y en el F-6: TSM 5, NVO 1, BCS 4, HSBC 5, SHEL 2, UL 1, TM 10; ASML no es
      ADR;
    - el motor aplica 4.154 en BCS. La hipótesis es un desfase de fechas de las acciones; se mide en T3;
    - **contradicen el prompt:**
      - BCS, HSBC, SHEL y UL publican semestrales con XBRL en 6-K;
      - `companyfacts` no incorpora el 20-F de 2025 de TSM, el de FY2026 de TM ni los 6-K de 2026, aunque llevan
        XBRL; se leen de la instancia del filing;
      - XOM cambió de CIK (2115436; la historia está en 34088);
    - perímetro de UL confirmado: ingresos de 2024 reexpresados de 60,761 a 52,479 millones de EUR.
- **Verificación:**
  - `python3 tests/edgar_diag.py --markdown` → "descarga companyfacts: mediana 0.42s (máx 0.91s), tamaño mediana
    3.6 MB (máx 8.0 MB)";
  - `../.venv313/bin/python -m pytest tests -q` → "2923 passed, 1 skipped in 55.35s";
  - búsqueda del User-Agent y del correo en `backend/tests` y `docs` → 0 archivos.
- **Decisiones tomadas por el usuario:** ninguna en esta sesión (D2 y D7 ya decididas por el planificador).
- **Abierto / siguiente paso:**
  - presentar el punto de parada 1;
  - **T1** después del cierre de Nueva York (16:15), en una sola sesión, con `--render-sim` y Finnhub;
  - luego, T3 (discrepancias) y T4 (precedencia).
- **Archivos tocados:**
  - `backend/main.py` (`/api/health`);
  - `backend/tests/{test_health,edgar,edgar_diag,test_edgar_tools}.py`;
  - `backend/tests/fixtures/edgar/`;
  - `docs/fiabilidad/F2_EDGAR_DIAGNOSTICO.md` y esta bitácora.
- **Avisos para el siguiente chat:**
  - la herramienta lee la caché por defecto (`--refresh` para volver a descargar);
  - no le pongas `print` al User-Agent;
  - para TSM FY2025 y TM FY2026, `companyfacts` no basta: hay que leer `<ticker>-<fecha>_htm.xml` del filing;
  - el resolutor ticker → CIK necesita `PREDECESSORS` (XOM).
