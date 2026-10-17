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
- **Sin parches (principio del usuario, 2026-10-15):** "no quiero un modelo con parches. quiero algo real y
  funcional".
  - Todo arreglo se declara como **de fondo** (corrige el dato o el método en origen) o como **protección
    provisional** (tapa un síntoma). Una protección provisional lleva siempre la fase que la sustituye, y esa fase no
    se cierra mientras siga en pie.
  - Lo financiero se justifica con práctica estándar citable y se mide contra la fuente oficial (SEC EDGAR); no se
    añaden reglas para callar una inquietud.

## Estado actual

| Campo | Valor |
|---|---|
| Fase en curso | **Fases 3 a 6 ✅ cerradas en código; fase 7: estudio de calibración ✅ y revisión de parámetros ✅** (bajo la delegación del usuario, registros #31–#35); vigilancia semanal continua. Pendientes del usuario: `SEC_EDGAR_USER_AGENT` en Render, el "ok, pushea", el deploy y el permiso para descargar los datos sectoriales de Damodaran (F4_PARADA §5) |
| Rama de trabajo | `fiabilidad/f7-calibracion` (sale de `fiabilidad/f6-infra` ← `fiabilidad/f5-contexto` ← `fiabilidad/f4-escalas` ← `fiabilidad/f3-metodo`; worktree `../finanzer_next-f3`), sin subir |
| Producción | `01336e2` (código `103c76f`). Rollback de código: `60f8a69` |
| `main` local | `b2f1972` (borrador del prompt de la fase 3), un commit por delante de `origin/main`; sin subir |
| Último cierre de sesión | 2026-10-17 · operador F3–F7 (ver registro #35) |
| Bloqueos | `SEC_EDGAR_USER_AGENT` en Render (la pone el usuario): sin ella no hay deploy de la fase 3. Golden de la fase 3 sin regenerar (permiso del usuario) |

## Fases

| Fase | Estado | Rama | Commits | Aprobada por el usuario | Deploy |
|---|---|---|---|---|---|
| 0 Congelar y medir | ✅ cerrada (2026-10-14) | `fiabilidad/f0-panel` → `main` local | `0a8ac66`..`0ae214a` (9 commits) + cierre (registro #6) | sí, 2026-10-14 (registro #6) | no aplica (se sube con el deploy de la fase 1) |
| 1 Lo visible hoy | ✅ cerrada | `fiabilidad/f1-visible` | `d676b22` (D8), `21c3f5f`, `0ebba81` (guardián), `d63de70`…`d7393fd` (T3, 8 commits), `7f32070`, `e3161d2`, `c369575` (T4) | — | — |
| 2 Verdad de datos (EDGAR) | ✅ cerrada: 2a (2026-10-15) y 2b (2026-10-16, registros #21–#23). F1 91.4% (objetivo 95% no alcanzado; lo que falta, en la fase 3 o por diseño: RECON §7.21) | `fiabilidad/f2a-medir` y `fiabilidad/f2b-corregir` → `main` | 2a: `8d3a5cc`…`aed575a`; 2b: `b25aed6`…`103c76f` (T1–T8) + cierre (RECON §7.21, registro #23) | 2a: sí; 2b: paradas 1 y 2 sí, "ok, pushea" (2026-10-16) | 2a `25b9d8a`; 2b `103c76f` |
| 3 Método por arquetipo | ✅ cerrada en código (2026-10-17, registros #24–#31; RECON §7.22) · preparación F3prep fusionada (`fiabilidad/f3-prep`) | `fiabilidad/f3-metodo` | T1: `3d52202`…`20c2a2e`; T1b: `d34c858`…`3966a43`; T2: `dc62a83`…`0fe8ef0`; T3–T8: `f8e5750`…`784b7eb` | paradas 1 y 1b sí (registros #25, #27); parada 2 y 3 bajo delegación (#29, #31) | — (falta `SEC_EDGAR_USER_AGENT`, golden y "ok, pushea") |
| 4 Escalas y confianza | ✅ cerrada en código (2026-10-17, registro #32; F4_PARADA, RECON §7.23); referencias por industria y geografía en espera del permiso de descarga | `fiabilidad/f4-escalas` | `1f12e33`…`f99859a` | bajo delegación (#29, #32) | — (con la fase 3) |
| 5 Técnica y conductual | ✅ cerrada en código (2026-10-17, registro #33; F5_PARADA, RECON §7.24); latencia desde Render, en la comprobación de producción | `fiabilidad/f5-contexto` | `e99e958`..`8e2bf07` (prep) + `9363163`, `309ed32` | §5 de la muestra aceptado (#20); lecturas conductuales revisadas bajo delegación (#33) | — (con las fases 3 y 4) |
| 6 Infraestructura | ✅ cerrada en código (2026-10-17, registro #34; F6_PARADA, RECON §7.25); arranque en frío fuera (D6); medida en Render con el deploy | `fiabilidad/f6-infra` | diagnóstico `697eb83`..`583e685`; `94ce758`, `6fb46c3`, `1b8f5ca`…`9b7bbc4`, revisión `2006379`…`ead7808` | bajo delegación (#29, #34) | — (con las fases 3 a 5) |
| 7 Vigilancia / calibración | 🔧 continua: vigilancia semanal activa (tarea `finanzer-vigilancia-semanal`, sábados 09:00); revisión mensual de parámetros ✅ (`7bbfc6e`); estudio de calibración ✅ (F7_CALIBRACION v2 tras revisión, registro #35): ninguna escala anticipa la cotización de forma robusta; decisiones del usuario abiertas | `fiabilidad/f7-calibracion` | `697eb83`..`583e685`; `7bbfc6e`, `3ef8c8f`… | tarea programada aprobada (registro F67prep); estudio bajo delegación (#35) | — |

Leyenda: ⏳ pendiente · 🔧 en curso · 🛑 detenida esperando al usuario · ✅ cerrada · 🔒 bloqueada por puerta

## Decisiones (D1–D7 del plan, §6)

| # | Tema | Estado | Decidido | Fecha |
|---|---|---|---|---|
| D1 | Códigos internos en el PDF | **decidida** | Anexo técnico: los códigos salen de las páginas de lectura y se reúnen en un anexo final del PDF rotulado "Detalle técnico para auditoría"; la web no los muestra (usuario, chat de planificación). Se aplica en la fase 1 (`prompts/F1_lo_visible_hoy.md`) | 2026-10-14 |
| D2 | Papel de SEC EDGAR | **decidida** | Usuario, literal: "acepto tus recomendaciones". La recomendación aceptada, la del operador en F2_PRECEDENCIA §3 (escenario B + respaldo; A, campo a campo más adelante), dice: "D2 = EDGAR como verificación por ahora, y como respaldo para lo que Yahoo no da (utilidades retenidas de JNJ, D&A de BCS). La 2b arregla en origen los errores de dato: dividendo de Finnhub, factor ADR oficial, corte coherente y el falso positivo de NVDA. EDGAR pasará a fuente principal campo a campo cuando la fase 3 cierre las definiciones (deuda, capex, EBIT bancario)." Antes (fase de medida): verificar y luego decidir | 2026-10-15 |
| D3 | Precio con un solo método (RECON §7.17) | **decidida** | DCF inverso: "el precio exige crecer X% anual 10 años" frente al crecimiento logrado y las tasas base, como segundo método cuando el DCF directo no concilia; y la confianza no se contrae por la mera ausencia del segundo método (opción 3 de §7.17). Diseño en `F3_DISENO_METODO.md` §2 (usuario, chat de planificación) | 2026-10-15 |
| D4 | Arquetipo "crecimiento rentable" | **decidida** | Se crea GROWTH_PROFITABLE; la ciclicidad se mide con la historia real (10+ ejercicios de EDGAR, caídas de ingresos y márgenes) y va antes que el crecimiento: una cíclica que crece sigue siendo CYCLICAL con nota de crecimiento estructural (resuelve NVDA/TSM). Diseño en `F3_DISENO_METODO.md` §1 (usuario, chat de planificación) | 2026-10-15 |
| D5 | Capa técnica en el score | **decidida** | **Solo contexto:** las señales técnicas y la lectura conductual se muestran en un panel aparte y nunca suman ni restan a la calidad, al precio ni al score; la capa conductual puede informar la confianza solo como contexto explicado. Se revisa cuando la fase 7 (calibración) aporte evidencia. Usuario, literal: "sigue con d5 con lo que recomiendas, esta bien" (recomendación del plan §6: "(a) hasta que la fase 7 la valide") | 2026-10-15 |
| D6 | Infraestructura | **revisada: sin plan de pago** | El usuario **no contrata** el plan siempre encendido de Render: "no voy a contratar el plan de render. no hay presupuesto para eso. y eso no es un problema por ahora". Se acepta el arranque en frío (42.7 s medido en F6_DIAGNOSTICO, rama `fiabilidad/f67-prep`). La fase 6 trabaja solo con código: sacar el código bloqueante del bucle de eventos (cola en serie) y caché persistente de estados (tras D2). Sustituye a la decisión anterior (servicio siempre encendido, 2026-10-15) | 2026-10-15 |
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
| Piotroski FY frente a TTM (AAPL) / bases mezcladas plan B (AMZN) **2a: no medida.** T3 compara los datos de origen, y la base del Piotroski es un cálculo del motor. Va a la 2b con el corte coherente (F2_PRECEDENCIA §1). **2b: ✅ hecha** (`0c8d211` corte coherente: todos los datos de los estados en un solo corte; `4c102ee` base temporal declarada en los criterios del Piotroski, FY frente a FY). | corrida + memoria 11b | 2 |
| JNJ sin Altman (utilidades retenidas) **2a: medida en F2_DISCREPANCIAS §4, confirmada.** Falta en el pipeline y EDGAR la tiene (169 mil millones de USD). EDGAR la cubre como respaldo (D2). **2b: ✅ hecha** (`3ef20e7`: respaldo de EDGAR del mismo corte; JNJ vuelve a tener Altman, Z'' 4.41, con las utilidades retenidas de `us-gaap:RetainedEarningsAccumulatedDeficit`). | corrida 2026-10-14 | 2 |
| TSM forward P/E 18.9 frente a TTM 31.7 (¿ADR/ordinaria?) **2a: no medida**, porque las estimaciones no están en EDGAR. Hoy el forward P/E de Finnhub es 18.88 y el P/E TTM, 31.3: la razón (1.66) no es el factor ADR 5. **2b: ✅ hecha** (`8f461cf`): el P/E forward de Finnhub es una estimación de consenso de horizonte no documentado y la procedencia lo declara; contrastado en vivo con Yahoo (TSM 18.9 frente a 17.9). La razón con el TTM no es el factor ADR: el P/E no depende de la moneda ni del factor. | corrida 2026-10-14 | 2 |
| Beta de Finnhub en ADR (NVO 1.64 frente a 0.59) **2a: medida en F2_DISCREPANCIAS §5, confirmada.** 6 de 8 ADR difieren más de 0.3 (NVO 1.96 frente a 1.11). Beta propia en la 2b. **2b: ✅ hecha** (`01324a3`: beta propia de 2 años semanales frente al S&P 500, o la del sector si R² < 0.1; la de Finnhub solo como contraste, con aviso si difiere más de 0.5). | memoria 11b | 2 |
| Yahoo 401 en Render, fuente nunca "alta" **2a: no medida.** Es infraestructura y queda fuera de T3. Sigue en la fase 6. **2b: ➡️ movida a la fase 6** (infraestructura: qué devuelve Yahoo a Render; la 2b no la toca). **F6: ✅ resuelta por diseño** (registro #34): el plan B es la ruta de producción, y la fuente ya no resta por los 401 (F4, `8834e60`). Que la confianza salga "alta" en el panel (12 de 36) lo demuestra. | RECON §7.1 | 6 |
| PLTR, NVDA, CRWD sin arquetipo propio **F3: ✅ hecha** (T2, `dc62a83`…`9e76d50`): PLTR y NVDA son GROWTH_PROFITABLE; CRWD sigue MATURE por la regla aprobada (margen FCF − SBC 5% < 10%; F3_T2_PARADA2 fila 23). | corrida 2026-10-14 | 3 (D4) |
| CAT, DOW como "Madura"; TSM `ciclica_condicional_estable` **F3: ✅ hecha** (T2): CAT y DOW CYCLICAL por su historia de EDGAR (`historia_ciclica`); TSM GROWTH_PROFITABLE (11 ejercicios sin caídas ≥ 10%). La regla `ciclica_condicional_estable` desaparece. | corrida 2026-10-14 | 3 |
| Crecimiento del DCF (CAGR 3a frente a interanual, AAPL) **F3: ✅ hecha** (T5, `afdd1d8` + `26aa866`): con más de 10 pp entre el interanual y el CAGR a 3 años, el DCF usa una mezcla declarada de los dos; AAPL pasa al DCF inverso (T3). | corrida 2026-10-14 | 3 |
| Precio con un solo método evaluable **F3: ✅ hecha** (T3, `19def27` + `d71f0a2`): DCF inverso contra tasas base y opción 3 de §7.17. Un solo método evaluable: 18 → 2 de 37 (RIVN y SNOW, pre-beneficio). | RECON §7.17 | 3 (D3) |
| **Nuevo (panel):** 18/30 con un solo método de precio evaluable → **D3 con prioridad alta en la fase 3** **F3: ✅ hecha** (D3 aplicada): 18/37 → 2/37 en el panel final (F3_T7_PARADA3 §0). | F0 (registros #5, #6) | 3 (D3) |
| Cobertura de intereses en utilities **F3: ✅ hecha** (T7, `3f4be83` y T6, `51201e2`): la utility se valora con P/B frente al ROE regulado; la cobertura se lee con EBIT, EBITDA y su tendencia. | memoria 11b | 3 |
| **Nuevo (usuario, 2026-10-17):** cobertura de intereses: (1) empresas que no publican el gasto por intereses (AAPL desde 2023): intereses pagados del estado de flujos (`InterestPaidNet`), declarado "intereses pagados (caja)"; (2) cobertura con EBITDA (y con FFO en REIT) como segunda medida; (3) tendencia con la historia larga. Usuario: "lo cubrimos cuando requiera" **F3: ✅ hecha** (T6, `51201e2`): las tres partes: intereses pagados como respaldo declarado, EBITDA como segunda medida y tendencia por ejercicio. En REIT, además, (FFO + intereses) / intereses (`784b7eb`; O 4.3x, PLD 7.8x, AMT 4.9x). | usuario, registro #27 | 3 (T6) |
| BRK-B posible cíclica / conglomerado **F3: ✅ hecha** (T2 + T4): BRK-B es FINANCIAL con subtipo conglomerado (67% de ingresos no aseguradores), P/B frente al ROE medio; no cíclica (sin episodios confirmados). La suma de partes no se calcula, y se dice. | RECON §7.16 | 3 |
| AMZN sin categoría Crecimiento (base ≤ 0) **F3: ✅ hecha** (T5, `57e8d46`): base ≤ 0 → "no significativo" declarado en vez de un crecimiento sin sentido. | corrida 2026-10-14 | 3 |
| Calidad saturada en 100 (PLTR, TSM, NFLX, V) **F4: ✅ hecha** (`1f12e33`, `92a279e`): por encima de 80 la calidad exige persistencia en 5 ejercicios; > 95 pasa de 4 a 2 (TSM 99, V 96), ninguna en 100 (F4_PARADA §2). | corrida + RECON 7.14 | 4 |
| Producción atiende en serie; PDF de 20–60 s; JPM 46.1 s en frío (14-oct, 14:28) **F6: ✅ cola en serie quitada** (`6fb46c3` y revisión `2006379`…`ead7808`): 12 análisis en frío a la vez, de 26 s a 7.5 s en total, con `/api/health` libre (F6_PARADA §3). El arranque en frío (≈ 43 s) sigue: D6. | corrida 2026-10-14 + F0 | 6 (D6) |
| Etapa 10 del spec: capa conductual + noticias **F5: ✅ hecha** (`9363163`, `309ed32`): contexto de mercado (momentum, tendencia, volatilidad, caídas, fuerza relativa, volumen), lectura conductual (anclaje, sobrerreacción, extrapolación) y titulares de 7 días de Finnhub, aparte y sin puntuar (D5); F5_PARADA. | redesign-spec §5 | 5 |
| Rf y prima de riesgo con revisión mensual | RECON §7.13 | 7 |
| Fecha de resultados no se lee en ninguna ruta (bug f): necesaria para PEAD **F5: hecha en parte**: la fecha se lee desde la 2b (T3, aviso de resultados); el PEAD no se lee porque falta la sorpresa del BPA frente al consenso con fuente y fecha, y el informe lo dice. | RECON §7.7 | 5 |
| Crecimiento de Finnhub sospechoso (FCX −24.2% frente a +1.8% en estados): desde 9b ya no puntúa (el DCF y Crecimiento usan el CAGR de los estados), pero se muestra como dato "(interanual)" **2a: no medida.** T3 no compara el crecimiento de Finnhub. **2b: ✅ hecha** (`f762e03`): el interanual sale siempre de los estados (FY0 frente a FY1) y se rotula "(último ejercicio)"; el de la fuente no entra (periodo_incoherente, aviso). FCX: +1.8%. | RECON §7.7 / §7.15 | 2 |
| Plan B sin `lastSplitFactor` (un estado sin ajustar por split anularía la comparación de acciones) **2a: no reproducida en el panel.** Yahoo ya aplica los splits posteriores al filing (CRWD 4:1, UL 8 por 9; F2_DISCREPANCIAS §3, periodo). El plan B no se probó. **2b: ✅ hecha** (`20fc859`): el plan B toma el factor del último evento de split de la serie de precios (CRWD 4:1, NFLX 10:1, UL 0.888 de la escisión). Sin efecto hoy en el panel: Yahoo ya ajusta los estados. | RECON §7.7 | 2 |
| Forward EPS sin fuente en prod (Finnhub da forward P/E, no BPA) **2a: no medida**, porque las estimaciones no están en EDGAR. **2b: ✅ hecha** (`8f461cf`): el BPA forward no tiene fuente y queda "sin dato" declarado; no se usa ni se muestra. | RECON §7.7 / §7.5 | 2 |
| Crecimiento bancario con "Total Revenue": medirlo con margen de intereses neto o ingresos netos **F3: ✅ hecha** (T4, `e2b4c3b` + `9155044`): Crecimiento puntúa los ingresos netos del banco (su "Total Revenue" ya es margen de intereses + comisiones, con los ingresos de los estados); el margen de intereses se calcula y se muestra aparte, informativo (JPM +12.7% anual en 3 años, 52% de los ingresos netos). | RECON §7.8 | 3 |
| Bandas paralelas: alinear las de las alertas (cobertura, DCF, beta, DN/EBITDA) con las del score; "cuatro copias de umbrales" **F4: ✅ hecha** (`ea2926b`, `71b5184`): DCF, cobertura, deuda neta/EBITDA y beta con una sola fuente de umbrales (alertas, lectura, gráfico, tooltip y pre-mortem). | RECON §7.9 / §7.14 / PLAN §1 | 4 |
| Benchmarks y medianas sectoriales PROVISIONALES sin fuente (market P/E 23x, ROE 20%/8%, D/E 1.0x…; forward market 18.9x) **F4: ⏸️ espera el permiso del usuario para descargar los conjuntos de datos de Damodaran** (F4_PARADA §5); sin ellos no hay fuente con fecha para sustituirlas. | RECON §7.14 / §7.16 | 4 |
| Bandas de REIT (DN/EBITDA ≤5.0x…) y de utilities (cobertura ≥3.5x…) PROVISIONALES, sin muestra **F4: ➡️ movida a la fase 7** (calibración con la historia de EDGAR de una muestra amplia de REIT y utilities; sin muestra no hay umbral con fuente). | RECON §7.14 / 61212c1 | 7 |
| MATURE de dividendo alto (≥ 4%): Crecimiento como retorno total, propuesto sin aplicar (faltaba fixture; el panel trae KO, PG, JNJ, DOW) **F3: ✅ hecha** (T5, `c12ad29`): MATURE con dividendo ≥ 4%: Crecimiento como retorno total (crecimiento + rentabilidad por dividendo), declarado. | RECON §7.11 / §7.14 | 3 |
| SBC en MATURE (> 5% de ingresos): propuesto sin aplicar (faltaba fixture; el panel trae PLTR, CRWD, SNOW, NVDA) **F3: ✅ hecha** (T3, `fa9a156` + `817eda4`; T6, `51201e2`): el DCF descuenta FCF − SBC en todos los arquetipos; con SBC material, lectura "SBC como coste real". | RECON §7.14 | 3 |
| Techo de la calidad cuando la lectura tiene señales en contra (NFLX 100 con P/E no fiable y DCF por debajo) **F4: ✅ hecha** en lo que toca a la calidad (`1f12e33`): NFLX 100 → 93 por persistencia (margen y conversión en caja recientes). Las señales de precio (P/E, DCF) no limitan la calidad por diseño (dos puntuaciones, etapa 9a): van al precio y a la confianza. | RECON §7.12 / §7.13 (a) | 4 |
| Confianza "alta" con convergencia solo "media" (V local 0.80) **F4: ✅ hecha** (etapa 9a, verificado en el panel de F4: ninguna alta con convergencia media) y ampliado (`122cbb4`): alta exige además que ninguna dimensión sea baja. | RECON §7.13 (c) | 4 |
| Número de Graham calculado en REIT con BPA deprimido por la depreciación (se muestra, no vota) **F3: descartada, ya resuelta** (etapa 9a, `1ca1588`; verificado en el panel de T7): en REIT el Graham no se calcula (`graham_number` vacío en O) y la tarjeta dice "No aplica a REIT: el beneficio contable está distorsionado por la depreciación inmobiliaria". El método intrínseco del REIT es el DCF inverso sobre FFO (T3). | RECON §7.13 (b) | — |
| Descartado — **verificado en la web** (F1 T6, registro #13): la barra de 52 semanas de la web (`Range52Bar`, "contexto, sin juicio") muestra solo la posición, sin tono de curva en U; coincide con el PDF | RECON §7.14 | — |
| Mejoras aprobadas: P/FFO visible en la web (no es un defecto; decisión del planificador en el prompt F1) | memoria (backlog) | mejoras, después de la fase 4 |
| Mejoras aprobadas: DuPont del ROE, margen FCF con tendencia, Rule of 40 (crecimiento rentable) **F3: ✅ hecha** (T6, `51201e2`): DuPont, margen FCF con tendencia y regla de 40 (GROWTH_PROFITABLE), en la web y el PDF; informan, no puntúan. | memoria (backlog) | 3 (D4) |
| ✅ Hecho (F1, `d676b22`): `golden/prod` en base anual mientras prod calcula en TTM → D8: `prod` y `muestra` retirados | F0 (registros #2, #6, #7) | 1 (inicio) |
| **Nuevo (panel):** Yahoo devuelve a Render datos distintos que a una IP residencial en 7/30 (acciones de fast_info en PG y NEE; balance trimestral de DUK al 31-mar en Render frente al 30-jun en local; acciones diluidas trimestrales ausentes en CAT y DUK; balance en el Altman de NVDA; acciones en MSFT; trimestres con resultado operativo en PLD). Local es estable. Efecto en el veredicto: DUK calidad 71 → 74, sin cambio de nivel. **Refuerza D2** **2a: medida en F2_DISCREPANCIAS §4.1.** **F6: ⏸ sin medir:** hace falta el deploy. Lo acotan el corte coherente y el respaldo de EDGAR (2b), y desde la F6 el corte de doce meses de EDGAR cuando Yahoo no trae los trimestres (registro #34). Render tenía razón en 3; en 2, los dos datos son reales pero de cortes distintos (periodo); 2 no se pueden verificar. **2b: ➡️ movida a la fase 6** (infraestructura). En la 2b, el corte coherente (`0c8d211`) y el respaldo de EDGAR (`3ef20e7`) acotan su efecto: un dato de otro periodo no entra y lo que falta del corte lo da EDGAR. | F0 (registros #5, #6) | 6 |
| **Nuevo (panel):** el crecimiento de ciclo medio está en su cota en 5 cíclicas (XOM y DOW −5.0% en ingresos y BPA; FCX BPA −5.0%; MU y ASML +10.0%). **Texto** ✅ hecho (F1, `eac35b3`: "acotado al mínimo/máximo que admite el modelo"); **método** del tope −5%/+10% → fase 3 **F3: ✅ hecha** (T5, `e353392`): crecimiento de ciclo medio de pico a pico (XOM +0.6%, CAT +0.4%, FCX −7.4%, MU +10.3%, SHEL +5.3%); la cota −5%/+10% queda solo cuando la historia no tiene dos picos (DOW tras la escisión de 2019; ASML), dicho como "acotado: historia corta". | F0 (registros #5, #6) | 1 (texto) / 3 (método) |
| ✅ Hecho (F1, `83e0f70`): invariante `growth_texts_cite_the_scored_figure` acepta el signo expresado con el verbo; 0 xfail | F0 (registros #5, #6) | 1 |
| **Nuevo (panel):** efecto frontera: NVO cambia de nivel de precio con 10 pb de Rf (config 5.29% → ^TNX 5.19%: 58 "razonable" → 70 "atractivo", confianza media → alta). Banda de tolerancia o aviso de proximidad al umbral **F4: ✅ hecha** (`a0aa922`): aviso de frontera a ≤ 2 puntos de un umbral, en calidad y en precio (11 en el panel). | F0 (registros #5, #6) | 4 |
| **Nuevo (panel):** BRK-B en base anual (faltan capex y D&A en algún trimestre) **2a: reproducida.** El fixture sigue en base anual. La D&A del FY falta en el pipeline y EDGAR la tiene (13,476 millones de USD); no se comprobó si EDGAR trae los trimestres. EDGAR como respaldo en la 2b. **2b: ➡️ movida a la fase 3** (definición): Yahoo no trae el 3T-2025 de BRK-B (resultados, flujos ni balance; confirmado en vivo el 2026-10-16) y completar el corte con EDGAR mezclaría dos definiciones de ingresos: Yahoo suma las ganancias y pérdidas de inversión (FY2025 410.5 frente a 371.4 mil millones de `us-gaap:Revenues`; 2T-26 117.9 frente a 101.8). Beneficio neto, D&A, capex e intereses sí casan. La D&A del FY la cubre ya el respaldo (`3ef20e7`). Corte trimestral de BRK-B con EDGAR cuando la fase 3 decida qué ingresos usa. **F3: ➡️ movida a la fase 6**: la decisión de definición está tomada (ingresos de EDGAR `us-gaap:Revenues`, sin ganancias de inversión); falta construir el corte LTM con los 10-Q de EDGAR (ejercicio + acumulado del año − acumulado del año anterior), que es infraestructura de datos. **F6: ✅ hecha** (`9b7bbc4`): sin 4 trimestres de Yahoo, el corte pasa al último 10-Q de EDGAR. BRK-B, al 30-jun-2026: P/E 16.96 → 13.24 (TTM), con el balance de Yahoo de esa fecha. Solo si no pierde campos: UL se queda en el ejercicio (F6_PARADA §2). | F0 (registro #5) | 6 |
| ✅ Hecho (F1, `eac35b3`): "(3 años)" en la comparación de cíclicas cuya cifra es de ciclo medio → "(ciclo medio)" | F1 T2 (registro #9) | 1 (texto) |
| ✅ Hecho (F1, `90ab32a`): V (benchmark de mercado) decía "múltiplos frente al sector" en la confianza | F1 T2 (registro #9) | 1 |
| **Nuevo (guardián):** BRK-B "P/E (TTM)" con base anual (faltan trimestres). **Texto** ✅ hecho (F1, `f6f0b36`: "P/E (último ejercicio)"); dato (trimestres que faltan) → fase 2 **2a:** el dato, como en la fila "BRK-B en base anual". **2b: ➡️ movida a la fase 3**: el dato, como en la fila "BRK-B en base anual". **F3: ➡️ movida a la fase 6** (el dato), con la fila "BRK-B en base anual". **F6: ✅ hecha** con esa fila (`9b7bbc4`): "P/E (TTM)" con base de doce meses de EDGAR. | F1 T2 (registro #9) | 6 |
| ✅ Hecho (F1, `d7393fd`): AMT atribuía la caída del FFO por acción a la emisión de acciones con las acciones planas en 3 años (+0.05%) | F1 T2 (registro #9) | 1 |
| ✅ Hecho (F1, `87c147d`): "N/A" como valor en las tablas → "—" | F1 T2 (registro #9) | 1 |
| ✅ Hecho (F1, `51e8f96`; falta recompilar `frontend/out` en T6): la web mostraba códigos en el desplegable "Detalle técnico", contra D1 | F1 T2 (registro #9) | 1 (web) |
| **Nuevo (panel):** con la tabla validada (registro #6): CAT y TSM deberían ser CYCLICAL y salen "Madura"; PLTR y CRWD salen "Madura" (falta el arquetipo, D4); NVDA a decidir en D4 **F3: ✅ hecha** (T2): CAT CYCLICAL, TSM GROWTH_PROFITABLE, PLTR y NVDA GROWTH_PROFITABLE; CRWD MATURE con su motivo (fila de arriba). | F0 (registros #5, #6) | 3 (D4) |
| **Nuevo (F1 T3.1):** NFLX trae en 2026-03 un trimestre con +2.85 B de ingresos financieros (los demás, 40–50 M); el TTM del resultado financiero sale +2.14 B con el anual en −604 M. Sin efecto hoy (cobertura positiva; "sin carga" exige el signo en cada trimestre). Revisar la fuente **2a: no reproducida en lo medido.** El gasto financiero TTM cuadra con EDGAR (847 millones); los ingresos financieros no se compararon. **2b: ✅ hecha** (`a2bb87a`): el dato es real. 10-Q del 1T-2026 de NFLX: "Interest and other income (expense)" de 2,852 millones, con la comisión de ruptura de 2.8 mil millones de la fusión con WBD. El motor ya la aísla como pico no operativo y la cobertura usa el EBIT (16.9x); un test lo fija. | F1 (registro #10) | 2 |
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
| **Nuevo (BCS, informe de prod del 15-oct revisado por el usuario con un analista externo):** dividend yield **50.46%** imposible (≈ $11.50 por ADR sobre $22.79). Hipótesis del planificador: `dividendRate` en **peniques leído como libras** (×100) y **sin factor ADR** (÷4), ≈ 25×; real probablemente ~2% (verificar contra el dividendo declarado). Arrastra el shareholder yield (54.32%) y "Dividendo sostenible (50.46%)" en la salud financiera (que además cita el yield donde debería evaluar el payout). **Fase 1 (antes del push):** guardián de identidades datos↔datos (dividend yield ≈ payout × E/P y ≈ dividendos pagados / capitalización; shareholder yield = dividendo + recompras) → si no cuadra, "sin dato" + aviso; "dividendo sostenible" evalúa el payout. **Fase 1 ✅ hecha** (`bfc38e9` identidad y sin dato; `8c860be` dividendo sostenible por payout). **Diagnóstico confirmado (registro #13):** el yield viene de Finnhub `/stock/metric`, que para BCS da la línea de Londres de la acción ordinaria **en peniques** (`dividendIndicatedAnnual` 11.5); el motor lo divide por el precio del ADR en dólares: peniques (×100), sin factor ADR (÷4.154) y **sin conversión GBP→USD** (÷1.342) → ≈ 18×; real ≈ 2.8%. **Fase 2:** arreglar la unidad, el factor y la moneda en origen **2a: medida en F2_DISCREPANCIAS §4, confirmada:** unidad + factor ADR, 18.6×. **2b: ✅ hecha** (`c9b661d` dividendo indicado en la moneda y la clase del precio, con los pagos del propio ADR: BCS 2.71%; `b25aed6` factor ADR oficial). | usuario, 2026-10-15 | 1 (guardián) / 2 (origen) |
| **Nuevo (F1, identidad del dividendo):** el mismo defecto de origen que BCS en **TSM** (6.05%: 26 TWD por acción ordinaria sobre $430 del ADR; real ≈ 0.95%), **NVO** (30.69%: 11.7 DKK sobre $38; real ≈ 4.8%) y **NVDA** (0.45%: `dividendIndicatedAnnual` = 1 de Finnhub; el dividendo es $0.04, ≈ 0.02%). Desde `bfc38e9` salen "sin dato" con aviso. Arreglar en origen: `dividendIndicatedAnnual` de Finnhub en moneda y acción de la línea local **2a: medida en F2_DISCREPANCIAS §4.** TSM (6.2×) y NVO (6.4×) confirmados (unidad). NVDA descartado: es un falso positivo (fila del F2a, T3). **2b: ✅ hecha** (`c9b661d`): TSM 0.90%, NVO 4.86%; NVDA 0.45% es correcto (subida verificada). | F1 (registro #13) | 2 |
| **Nuevo (F1, producción 15-oct):** UL (fuera del panel) habría mostrado un dividend yield del **251.70%** (mismo defecto de origen de Finnhub, línea local en otra moneda); la identidad lo deja "sin dato". Entra en el arreglo de origen **2a: medida en F2_DISCREPANCIAS §4, confirmada:** unidad + factor ADR (255.2% en el fixture). El mismo defecto aparece en HSBC, SHEL y TM. **2b: ✅ hecha** (`c9b661d`): UL 3.44%, HSBC 3.97%, SHEL 2.92%, TM 3.30%. | F1 (registro #15) | 2 |
| **Nuevo (F1, producción 15-oct):** JNJ: Finnhub **impone** su `epsTTM` (6.5886) sobre el BPA TTM derivado de Yahoo (8.62) por diferir >2%, con los trimestres de Yahoo aún en junio (probablemente Finnhub ya incluye el trimestre nuevo): bases mezcladas, P/E 30.1x → 39.4x y nivel de precio razonable → exigente. Regla de imposición de Finnhub a revisar **2a: medida en F2_DISCREPANCIAS §4, confirmada en vivo** (periodo: 6.5886 = TTM de junio − 3T-2025 + 3T-2026). No se reproduce en los fixtures del 14-oct. Regla del corte coherente en F2_PRECEDENCIA §1. **2b: ✅ hecha** (`0c8d211` y `d984181`: Finnhub solo entra si casa con el corte; `e6364b2`: BPA TTM = suma de los BPA diluidos de los 4 trimestres del corte). | F1 (registro #15) | 2 |
| **Decidido (usuario, 2026-10-15, registro #14):** las **filas de tabla** con "No aplica" pasan a la misma regla que las tarjetas: "—" y el motivo, sin cifra (también la tabla de valoración: el FCF yield de BCS del 29.31% no debe verse). **Cambia la regla de la etapa 9b** (que mostraba la cifra con "No aplica") por decisión del usuario; su test se ajusta | F1 (registros #13, #14) | 1 |
| **Nuevo (usuario, 2026-10-15):** decidir qué métricas aplican de verdad a FINANCIAL. El P/E y el dividend yield son métricas legítimas de un banco; hoy salen como "no aplica" **F3: ✅ hecha** (T4, `1c3dbad`): el P/E aplica a bancos y aseguradoras (segundo bloque de precio); el dividend yield ya se mostraba. Resumen del banco con P/B primero. | usuario, registro #14 | 3 |
| **Nuevo (usuario, 2026-10-15):** el control de identidad del dividendo solo detecta rentabilidades **infladas**; falta el sentido contrario (unidad 100 veces menor), resolviendo el caso de los dividendos extraordinarios como PGR (yield indicado 0.19% frente a 6.6% pagado) **2a: medida en PGR** (definición: indicado ordinario 0.40 frente a 13.9 pagado con el extraordinario). Diseño en F2_PRECEDENCIA §2.2. **2b: ✅ hecha** (`c9b661d`): control en los dos sentidos con magnitudes equivalentes; PGR muestra el ordinario (0.19%) con la nota del extraordinario. | usuario, registro #14 | 2 |
| **Nuevo (F2a, T3; corrección de la 2b):** **NVDA es un falso positivo del control de identidad del dividendo de la fase 1, en producción.** El dato de Finnhub (`dividendIndicatedAnnual` = 1.00) es **correcto**: NVDA subió el trimestral de 0.01 a 0.25 en el 2T de su año fiscal 2027 (10-Q del 2026-07-26), y 0.25 × 4 = 1.00. El control compara el indicado con lo pagado en los últimos 12 meses (ventanas distintas) y lo deja en "sin dato". Diseño en F2_PRECEDENCIA §2.2: comparar magnitudes equivalentes (DPA declarado de EDGAR frente al pagado, en la misma ventana) y no anular un aumento verificado (último declarado × frecuencia = indicado). Corrige la fila de TSM/NVO/NVDA: NVDA no tiene el dato roto en origen **2a: medida en F2_DISCREPANCIAS §4**, descartada como dato roto. **2b: ✅ hecha** (`c9b661d`): la subida verificada ya no se anula. | F2a (T3, registro #17) | 2 (2b) |
| **Nuevo (F2a, T4; para la 2b):** deuda total de **DUK** +1.1% (970 millones de USD) sobre EDGAR. Hipótesis: Yahoo suma el arrendamiento operativo no corriente (≈ 1,000 millones; 1,033 a 2025-12-31), el patrón de MSFT y NVDA; DUK solo etiqueta los arrendamientos en el 10-K. Con la regla de F2_PRECEDENCIA §2.3 sobra ese operativo y faltan 576 millones de arrendamiento financiero. En la 2b: usar el arrendamiento del último FY con aviso de fecha cuando no hay etiqueta trimestral **2a: medida en F2_DISCREPANCIAS** (fuente errónea; la hipótesis está por verificar). **2b: ✅ hecha** (`4f01557` y `4fca871`): regla de la deuda coherente con el EBITDA; el arrendamiento financiero de DUK, del último 10-K con aviso de fecha. | F2a (T4, registro #17) | 2 (2b) |
| **Nuevo (F2a, T4; para la 2b):** deuda total de **O** +6.2% (1,930 millones de USD; EDGAR 29,252 = notas + préstamos + papel comercial). Hipótesis: (1) hipotecas o línea de crédito con conceptos propios de O; (2) intangibles de arrendamientos por debajo de mercado (1,457) + pasivos por arrendamiento (528) = 1,985. En la 2b: leer el balance del 10-Q del 2T para decidirlo **2a: medida en F2_DISCREPANCIAS** (fuente errónea; la hipótesis está por verificar). **2b: ✅ hecha** (`4fca871`): hipótesis 1 verificada en el 10-Q del 2T-2026: notas 25,092 + préstamos 2,760 + línea de crédito y papel comercial 2,763 + hipotecas 37 = 30,652 = Yahoo. La deuda de Yahoo es la correcta. | F2a (T4, registro #17) | 2 (2b) |
| **Nuevo (BCS):** factor ADR **4.154** frente a **4** oficial: se infiere de acciones del balance (31-dic) / acciones de hoy, y las recompras entre ambas fechas (~3.9%) se cuelan en el factor. Desvía ~3.9% todas las cifras por acción. Usar el ratio oficial del depositario (o ajustar al entero cercano dentro de tolerancia, declarándolo) **2a: medida en F2_DISCREPANCIAS §4, confirmada:** desfase de fechas (recompras de 2026). Las acciones de FY0 y FY1 quedan un 3.85% por debajo; el BPA cuadra con el factor 4. **2b: ✅ hecha** (`b25aed6`: factor ADR oficial del depositario, 4). | usuario, 2026-10-15 | 2 |
| **Nuevo (BCS):** bancos europeos con **AT1** (instrumentos híbridos contabilizados como patrimonio): el ROE/ROTE contable (10.0%) frente al RoTE reportado (12.2%); los cupones AT1 deben restarse del beneficio y los AT1 del patrimonio tangible; el payout de "dividendos pagados" puede incluir cupones AT1 **2a: medida en F2_DISCREPANCIAS §4, confirmada** (definición): 997 millones de GBP de cupones en los dividendos y BPA +19.8%; ROE 10.0% frente a 10.4% del ordinario. En HSBC es al revés. **2b: ✅ hecha** en datos (`7b610a7`): beneficio y patrimonio del ordinario separados (BCS: cupones AT1 997, AT1 12,725 = EDGAR); el ROE y el P/B los usan; el BPA y el payout ya eran por acción ordinaria. El ROTE ajustado por AT1, en la fase 3, con las filas anuales que quedan en los datos. **F3: ✅ hecha** (T4, `e2b4c3b`): ROTE ordinario: cupones AT1 fuera del beneficio y AT1 fuera del patrimonio tangible (BCS, HSBC, SAN). | usuario, 2026-10-15 | 2 (datos ✅) / 3 (método) |
| **Nuevo (BCS):** "ROTE implícito en el precio" para bancos: con P/TBV 0.81, Ke 11%, g 2.5% → ROTE ≈ 9.4% descontado, frente al reportado y al objetivo de la gerencia (sensibilidad). Equivalente bancario del reverse DCF **F3: ✅ hecha** (T4, `e2b4c3b` + `afae76a`): ROTE implícito en el precio = P/TBV × (Ke − g) + g, con sensibilidad ±2 pp; ROE implícito en aseguradoras, conglomerados y utilities. | usuario, 2026-10-15 | 3 |
| **Nuevo (BCS):** beta **1.64** idéntica a la de NVO (Finnhub en ADR, ya sospechosa): verificar contra una beta calculada sobre la serie de precios **2a: medida en F2_DISCREPANCIAS §5, confirmada:** BCS 1.64 frente a 1.24 de referencia. **2b: ✅ hecha** (`01324a3`): beta propia de BCS. | usuario, 2026-10-15 | 2 |
| ✅ Hecho (F1, `48a0242`): etiqueta "P/B frente a ROE 0.95× justificado" → "95% del P/B justificado (0.73x frente a 0.76x)", ídem P/TBV | usuario, 2026-10-15 | 1 |
| **Nuevo (proceso):** el panel no tiene emisores que reporten en peniques ni bancos europeos. Ampliarlo al inicio de la fase 2 con BCS, HSBC, SHEL, UL y TM (GBp/EUR/JPY, distintos factores ADR, AT1). En la fase 1 basta con capturar BCS para probar el guardián de identidades (✅ `3f2138b`, grupo "Revisión externa") **2a: ✅ hecho** (T1, `4051a5e`: HSBC, SHEL, UL y TM). **2b:** sin trabajo pendiente (hecha en la 2a). | planificador, 2026-10-15 | 1 (BCS) / 2 (resto) |
| **Nuevo (ROCE, usuario 2026-10-15):** el ROCE se calcula (AAPL 68.72%; promedio de ciclo en cíclicas) pero en la web es la **última fila de "Tabla de rentabilidad y eficiencia", plegada por defecto** (desde la 9b); solo se ve la nota de divergencia ROCE–ROIC. La fila no tiene referencia, brecha ni lectura ("Antes de impuestos"). En FINANCIAL/REIT "No aplica" (correcto). **Fase 1 (T6):** subirlo al bloque visible de Rentabilidad junto a ROIC − WACC (con el promedio de ciclo en CYCLICAL) y al resumen del PDF, sin cambiar cálculos. **Fase 4:** referencia por sector, bandas de lectura y ROCE promedio como prueba de persistencia de la calidad | usuario + planificador, 2026-10-15 | 1 (visible) / 4 (bandas) |
| **Nuevo (infra):** Render **apaga el servicio sin tráfico** ("Service waking up" al abrir finanzer.app el 15-oct): explica buena parte de los 46–52 s en frío, además de la atención en serie **F6: ⏸ fuera por D6** (sin plan de pago): no se quita con código. La parte de la cola sí se quitó (registro #34). | planificador, 2026-10-15 | 6 (D6) |
| **Revisión externa F1 (UL, planificador 2026-10-15):** "Los ingresos se contraen un 3.4% anual" → DCF con g −3.4% → alerta "Sobrevalorada según DCF −40%". Probable **cambio de perímetro** (escisión de helados/Magnum a finales de 2025; verificar en los estados): los años comparados no son homogéneos. El motor no detecta escisiones/desinversiones (operaciones discontinuadas, salto de ingresos) **2a: medida en F2_DISCREPANCIAS §4, confirmada** (perímetro: los ingresos de 2024 se reexpresan de 60,761 a 52,479 millones de EUR). Yahoo ya trae 2024 y 2025 con el perímetro nuevo. No se verificó si los años anteriores del CAGR también lo traen. **2b: ✅ hecha** la detección (`a435698`): data_provenance.perimeter declara los ejercicios reexpresados (UL 2023 y 2024), las discontinuadas y la base de cada ejercicio de Yahoo; en UL, 2022 está en el perímetro anterior y el CAGR a 3 años mezcla las dos bases. El crecimiento sin el perímetro, en la fase 3. **F3: ✅ hecha** (T5, `381c863`): perímetro homogéneo: los ejercicios con operaciones discontinuadas materiales se excluyen del CAGR (UL), declarado. | planificador, 2026-10-15 | 2 (detectar ✅) / 3 (crecimiento sin el perímetro) |
| **Revisión externa F1 (TXRH):** referencias por **sector amplio** (consumer_cyclical) para un restaurante: "Margen bruto 15.7% vs 35% muy inferior". Hace falta referencia por **industria** **F4: ⏸️ espera el permiso del usuario para descargar los conjuntos de datos de Damodaran** (F4_PARADA §5); sin ellos no hay fuente con fecha para sustituirlas. | planificador, 2026-10-15 | 4 |
| **Revisión externa F1 (TXRH):** lecturas ciegas al modelo de negocio: current ratio < 1 "Tensión" (normal en restauración/comercio con capital circulante negativo); Altman Z'' y Piotroski castigados por pasivos por arrendamiento (ASC 842) **F3: ✅ hecha** (T6, `ceac134`): capital circulante negativo estructural (no puntúa ni alerta salvo empeoramiento > 15%), Altman referencial y aviso del Piotroski por industria. | planificador, 2026-10-15 | 3 |
| **Revisión externa F1 (TXRH):** DCF con g = CAGR histórico 13.5% sin convergencia al largo plazo y fiabilidad "alta" (el CAGR incluye inflación de precios) **F3: ✅ hecha en parte** (T3, `f8e5750`): el DCF converge linealmente al crecimiento terminal en los años 6–10 y la fiabilidad la mide la conciliación con el precio. La parte de la inflación de precios se descarta: no hay fuente estructurada de precios por producto para separarla. | planificador, 2026-10-15 | 3 |
| **Revisión externa F1 (BCS):** P/B 0.73x frente a 1.50x "del sector" (bancos de EE. UU.): "descuento profundo −51%". Hace falta referencia por **geografía** (los bancos europeos cotizan estructuralmente más bajo por menor ROE) **F4: ⏸️ espera el permiso del usuario para descargar los conjuntos de datos de Damodaran** (F4_PARADA §5); sin ellos no hay fuente con fecha para sustituirlas. | planificador, 2026-10-15 | 4 |
| **Revisión externa F1 (UL):** factor ADR 1.012 frente a 1 oficial (mismo defecto que BCS: recompras en el factor) **2a: medida en F2_DISCREPANCIAS §4, confirmada, sin efecto:** está dentro de la tolerancia del motor y no se aplica. **2b: ✅ hecha** (`b25aed6`: factor ADR oficial, 1). | planificador, 2026-10-15 | 2 |
| **Prioridad (JNJ):** las reglas de **precedencia de fuentes** (qué fuente manda y con qué periodo) son el núcleo de la fase 2: Finnhub sustituyó el BPA por uno con el trimestre nuevo mientras los estados siguen en junio (periodos mezclados → cambio de nivel en producción) **2a: medida** (JNJ, F2_DISCREPANCIAS §4). Reglas en F2_PRECEDENCIA §1; D2 decidida. **2b: ✅ hecha** (`0c8d211`, `d984181`, `3ef20e7`): precedencia y corte coherente de F2_PRECEDENCIA aplicados. | planificador, 2026-10-15 | 2 (alta) |
| **Principio "sin parches" (usuario, 2026-10-15): la 2b no se cierra mientras sigan en pie las dos protecciones provisionales de la fase 1.** (1) **Dividend yield "sin dato" por la identidad** (`bfc38e9`): tapa el dividendo de Finnhub en moneda local por acción ordinaria (BCS, TSM, NVO, UL y los ADR nuevos) y da un falso positivo en NVDA. Sustituirla por la corrección en origen (moneda, acción ordinaria, factor ADR oficial; F2_PRECEDENCIA §2.2). La identidad queda solo como verificación, con magnitudes equivalentes. (2) **Rango de 52 semanas ampliado con el precio** (`range52_widened`): tapa un rango de la fuente desfasado del precio. Sustituirlo por el rango correcto desde la serie de precios (`lib/price_series.py`, F5prep) o desde la fuente, de la misma sesión que el precio **2b: ✅ hecha**: la protección 1, retirada en `c9b661d`; la 2, en `c8ae863`. Las dos sustituidas por el arreglo en origen. | usuario, 2026-10-15 (registro #20) | 2 (2b, alta) |
| **Mejora (planificador, F2a):** compromisos relevantes **fuera de balance** como contexto de solidez, sin entrar en las ratios. Caso: MSFT con 329.1 mil millones de arrendamientos firmados y aún no iniciados (centros de datos), ≈ 5× su deuda en balance; AMZN 137.2 mil millones. En XBRL solo aparece el plazo, sin importe: necesita lectura del texto de la nota o fuente alternativa **F3: descartada**: en XBRL solo aparece el plazo de los compromisos, sin importe; mostrarlos exigiría leer el texto de las notas. Se reabre si una fuente estructurada trae el importe. | planificador, 2026-10-15 | — |
| **Nuevo (F3prep, CAT):** deuda de **financieras cautivas** (Cat Financial; también Deere, Ford, GM) dentro de la deuda neta industrial: CAT carga 83.61 $/acción y su DCF directo da −73%. Práctica de analista: excluir la deuda de la financiera (respaldada por su cartera de préstamos) de la deuda industrial. Separar datos (2b) y usarlos (3) **2b: ✅ hecha** en datos (`4f01557`): la deuda de Cat Financial (34,456 millones) se separa y se declara en data_provenance.debt; su uso, en la fase 3. **F3: ✅ hecha** (T6, `4ae7705`; T7, `8a58618`): la deuda de la cautiva sale de la deuda industrial cuando EDGAR la desglosa con la misma fecha (CAT: 34.5 mil millones); DE no la desglosa en XBRL y se dice. | planificador, 2026-10-15 | 2 (datos ✅) / 3 (uso) |
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

### F3prep · 2026-10-15 · operador en paralelo (worktree) · Preparación de la fase 3 — llevado por el planificador
- **Registro completo:** `docs/fiabilidad/F3PREP_REGISTRO.md` en la rama `fiabilidad/f3-prep` (worktree `../finanzer_next-f3prep`, desde `8ed57a0`, commits `0f6f21b`..`da34592`, **sin push ni merge**). El operador no editó esta bitácora para no chocar con el de la 2a.
- **Hecho:** `lib/reverse_dcf.py` (DCF inverso, bisección, estados `ok`/`no_aplica`/`fuera_de_rango`/`sin_convergencia`) y `lib/bank_implied.py` (ROTE/ROE implícitos y sensibilidad), **aislados, sin conectar**. Parámetros en `valuation.toml` + `schema.toml`. Muestra en `F3PREP_MUESTRA.md`.
- **Verificación:** suite 3023 passed, 4 skipped (3 por falta de `node_modules` en el worktree), 0 golden cambiados; ida y vuelta con el DCF directo en KO, JNJ, XOM, AAPL y PG (error < 1e-8); contraste independiente en 3 casos (< 1e-8); ROTE BCS 9.385% (ejemplo de F3_DISENO §3); ida y vuelta exacta del ROTE en JPM, BAC y BCS.
- **Revisión del planificador:** el contraste con el CAGR de FCF a 3 años da lecturas erróneas (PLTR, NVDA, NFLX "baratas"; KO, NVO "exigentes"). Recomendaciones registradas en `F3_DISENO_METODO.md` §8: **decididas** el 2026-10-15 (el usuario delegó en el planificador la opción recomendada: "las dos cosas mías las puedes hacer tú, tomando la decisión más recomendada"). **No fusionar** `fiabilidad/f3-prep` hasta el inicio de la fase 3 (toca `valuation.toml`/`schema.toml`, como la 2b).

### F67prep · 2026-10-15 · operador en paralelo (worktree) · Vigilancia semanal (fase 7) y diagnóstico de infraestructura (fase 6) — 🛑 punto de parada
- **Objetivo de la sesión:** `prompts/F67prep_vigilancia_y_diagnostico_infra.md` (T0–T6), solo medir y vigilar; sin tocar el motor ni la app.
- **Hecho** (rama `fiabilidad/f67-prep`, worktree `../finanzer_next-f67prep`, desde `8ed57a0`, **sin push ni merge**):
  - `697eb83` `tests/vigilancia.py` + `test_vigilancia.py`; `6f0e1f1` timeout → HTTP 599 (no 200); `19e135f` `tests/perfil_local.py`, `tests/medir_concurrencia.py` + `test_f6_herramientas.py`; `935ba45` `F6_DIAGNOSTICO.md` y `F7_VIGILANCIA.md`.
  - **Semana 0** corrida a las 14:03–14:05 NY en `~/Downloads/finanzer_vigilancia/2026-10-15/` (32 tickers, SPY 422, 31 PDF, 0 alertas); validada contra F0 y F1 (`~/Downloads/finanzer_f7_validacion_2026-10-15/`): con commits declarados atribuye F0→hoy a "commit distinto" y F1→hoy a "mismo código" (JNJ por precio −2.1%); sin commit degrada a aviso. Inyección de un cambio de nivel con todo igual → 1 alerta, salida 1.
  - **Diagnóstico F6** (medidas en `~/Downloads/finanzer_f6_medida_2026-10-15/`): CPU local despreciable (análisis 5–11 ms, PDF ~50 ms); un análisis en frío hace 15 peticiones HTTP casi en serie (8 de estados); en producción frío 3.1–4.3 s, caliente 0.38–0.72 s, PDF caliente ≈ 2 s (CPU de reportlab, ≈ 34× este Mac). **Serie confirmada**: `async def` con código bloqueante (`main.py:1521-1534`) y un solo proceso; a concurrencia 3 el total no mejora (33 s frente a 38–39 s) y `/api/health` tarda 2.5 s de mediana con un análisis en curso. Arranque en frío medido: **42.7 s**. "Caliente" dura 300 s (`yf_adapter.cache_ttl_s`). Estimación de 12 simultáneas (no ejecutada): hoy máx ≈ 41 s; 2 workers ≈ 21 s; fuera del bucle ≈ 4–7 s (sin medir).
- **Verificación:** `cd backend && ../.venv313/bin/python -m pytest tests -q` → "2932 passed, 4 skipped in 59.99s" (3 skips por falta de `node_modules` en el worktree); 0 golden ni fixtures tocados (`git diff --stat main..HEAD`: solo los 7 archivos nuevos).
- **Decisiones tomadas por el usuario:** ninguna en esta sesión.
- **Abierto / siguiente paso (punto de parada):** (1) permiso del usuario para crear la **tarea programada semanal** (sábados 09:00, diseño y texto en `F7_VIGILANCIA.md`); no está creada. (2) "ok, pushea" si se quiere subir la rama (solo herramientas de test y documentos; el push redespliega). (3) El planificador decide qué opción de F6 entra en la fase 6 (recomendación del operador: D6 + sacar el código bloqueante del bucle de eventos; la caché persistente espera a D2).
- **Archivos tocados:** los 7 de la rama; esta entrada al final de la bitácora (nada más de la bitácora).
- **Avisos para el siguiente chat:** hasta que se despliegue `356f49c` (2a), `/api/health` no da el commit y la vigilancia no puede alertar por rotura (solo avisar); usar `--commit-anterior/--commit-actual` para corridas viejas. Peticiones a producción de esta sesión: 32 + 32 (semana 0) y 2 × 36 (medidas de concurrencia), todas antes de las 14:15 NY y a concurrencia ≤ 3 (más una sonda de `/api/health`).
- **Actualización (misma sesión):** el usuario aprobó la tarea programada ("Sí, crea la tarea programada semanal de vigilancia (sábados 09:00) con el texto de F7_VIGILANCIA.md."). Creada como `finanzer-vigilancia-semanal` (cron `0 9 * * 6`, guardada en modo Auto; el archivo está en `~/.claude/scheduled-tasks/finanzer-vigilancia-semanal/SKILL.md`). Corre desde el worktree `../finanzer_next-f67prep`: si se borra o se fusiona la rama, hay que actualizar la ruta de la tarea.
- **Cierre (decisión del usuario, literal):** "No pushees ni fusiones a main por ahora. Deja la rama fiabilidad/f67-prep local y el worktree ../finanzer_next-f67prep en su sitio (la tarea programada corre desde ahí). La incorporamos a main cuando cierre la fase 2a, en orden. Cierra la sesión con tu entrada en la bitácora." Estado final: rama local `fiabilidad/f67-prep` (`697eb83`..`583e685`, 5 commits), sin push ni merge; worktree en su sitio; tarea programada activa. **Siguiente paso:** fusionar en `main` después del cierre de la 2a, en orden, y entonces cambiar la ruta de la tarea programada.

### #18 · 2026-10-15 · operador · Fase 2a (T1, T3 y T4 hechas; detenida en el punto de parada 2)
- **Objetivo de la sesión:** continuar la 2a tras el punto de parada 1 (aprobado: "Apruebo el punto de parada 1. Sigue con T1 después del cierre de Nueva York y luego con T3"), con los criterios del usuario para T4.
- **Hecho:**
  - **T4:** `F2_PRECEDENCIA.md` con los 4 criterios del usuario (`01aec9d`, `36652af`):
    - deuda coherente con el EBITDA;
    - identidad del dividendo con magnitudes equivalentes;
    - aviso de resultados publicados y no incorporados;
    - filings que companyfacts aún no trae;
    - beta propia recomendada;
    - verificación de que los arrendamientos financieros de MSFT, AMZN y MU son solo pasivos en balance (MSFT: 329.1 mil millones no iniciados, excluidos).
  - **Mapa:** NVDA (falso positivo, 2b), O y DUK (2b).
  - **T1** (`385e441`, `4051a5e`):
    - HSBC, SHEL, UL y TM capturados el 15-oct a las 16:15 de Nueva York, en una sola sesión, con `--render-sim` y Finnhub; los cuatro con el arquetipo esperado;
    - golden nuevos;
    - el guardián daba un falso positivo en UL (base anual: "sin TTM" contaba como TTM): corregido con un test que fallaba primero.
  - **Herramienta de T3** (`f8f13df`…`06a6ec0`): `tests/edgar_verify.py` y `tests/beta_ref.py`, con extractos que incluyen los 12 filings que companyfacts no trae.
  - **T3** (`6946a64`): `F2_DISCREPANCIAS.md`. Las cifras de T4 y T2 se pusieron al día con los 36 (`8d7c1fb`).
- **Resultados:**
  - **Línea base F1: 90.0%** de los campos comparables dentro de tolerancia (1,262/1,403): EE. UU. 91.6%, extranjeros 82.9%.
  - **Causas de lo que queda fuera:** definición 78, fuente errónea 41 (la mitad, el beneficio operativo construido por Yahoo), periodo 14, unidad + factor ADR 4, factor ADR 4.
  - **What-if B** (solo errores de dato): 0 cambios de nivel. **What-if A:** 1 (NFLX). **Beta propia:** 3 (BRK-B, NVO, NFLX).
  - **Casos conocidos:**
    - confirmados: BCS (peniques, factor 4.154 por recompras, AT1 997 millones de GBP), UL (perímetro y factor 1.012 sin efecto), JNJ (BPA de Finnhub 6.5886 en vivo; utilidades retenidas 169 mil millones), TSM, NVO y el dividendo de HSBC, SHEL, UL y TM (moneda de la línea local);
    - descartado: NVDA;
    - **nuevo: TM**, con el factor 11.07 por una capitalización de Yahoo un 9.6% corta.
- **Verificación:**
  - `pytest tests -q` → "3195 passed, 1 skipped";
  - `npm run check` → "StockAnalysis encaja con 41 salidas del backend";
  - captura: "[HSBC] OK … [TM] OK", con la clave en 0 fixtures;
  - `edgar_verify.py --whatif` → 2065 filas;
  - búsqueda de secretos → 0 archivos.
- **Decisiones tomadas por el usuario:** criterios de T4 (deuda, dividendo, aviso de resultados, retraso de companyfacts, beta propia); arrendamientos solo en balance; O y DUK a la 2b. D2 sigue pendiente de decisión con T3 y T4.
- **Abierto / siguiente paso:**
  - **punto de parada 2:** decisión D2 y "ok, pushea" para T0 (`/api/health`) y el panel ampliado;
  - después, T5 (RECON §7.20, mapa de fase 2 marcado "medida en F2_DISCREPANCIAS").
- **Archivos tocados:**
  - `backend/tests/{guardian,test_guardian_detecta,fixture_backend,panel_run,edgar,edgar_diag,edgar_verify,beta_ref,test_edgar_verify}.py` y `backend/tests/README.md`;
  - fixtures y golden de HSBC, SHEL, UL y TM;
  - `docs/fiabilidad/F2_{DISCREPANCIAS,PRECEDENCIA,EDGAR_DIAGNOSTICO}.md` y esta bitácora.
- **Avisos para el siguiente chat:**
  - las ediciones del planificador en esta bitácora (D3, D4 y la fila "compromisos fuera de balance") siguen **sin commitear** en la copia de trabajo: no son del operador;
  - las clasificaciones "probable" de T3 no se han leído en la nota del filing;
  - el panel de 36 ya está en los golden: la suite tarda unos 80 s.
- **Actualización (misma sesión): deploy de T0 y del panel ampliado.**
  - **Aprobación del usuario (literal):** "Ok, pushea: merge de fiabilidad/f2a-medir a main con la suite en verde, push y verifica que /api/health devuelve el commit desplegado. D2 lo decido aparte."
  - **Hecho:**
    - fast-forward de `main` 8ed57a0 → 25b9d8a (19 commits, sin cambiar de rama: la carpeta la comparten otros operadores);
    - el único cambio de código de producción es `/api/health` en `backend/main.py`.
  - **Verificación:**
    - `pytest tests -q` → "3195 passed, 1 skipped in 73.15s";
    - `git push origin <sha>:refs/heads/main` → "8ed57a0..25b9d8a";
    - `curl https://finanzer.app/api/health` → `{"status":"ok"}` a las 16:34:27 (código anterior) y `{"status":"ok","commit":"25b9d8a39bdeb41a12e119605bdaadf4dad19a69"}` a las 16:34:57;
    - `/api/analysis/AAPL` → 200 en 4.8 s, MATURE, "Calidad sólida · precio exigente" (igual que su golden).
  - **Siguiente:** decisión D2 del usuario y, con ella, T5 (RECON §7.20 y mapa de la fase 2). Este registro va en un commit local, sin push: pushear redespliega.

### #19 · 2026-10-15 · operador · Fase 2a cerrada (T5)
- **Objetivo de la sesión:** T5 tras la decisión D2: RECON §7.20, bitácora y mapa de la fase 2.
- **Decisión del usuario sobre D2 (literal):** "acepto tus recomendaciones". La recomendación que aceptó, tal como se la presentó el operador principal: "D2 = EDGAR como verificación por ahora, y como respaldo para lo que Yahoo no da (utilidades retenidas de JNJ, D&A de BCS). La 2b arregla en origen los errores de dato: dividendo de Finnhub, factor ADR oficial, corte coherente y el falso positivo de NVDA. EDGAR pasará a fuente principal campo a campo cuando la fase 3 cierre las definiciones (deuda, capex, EBIT bancario)."
  Es la recomendación de F2_PRECEDENCIA §3: escenario B con EDGAR de respaldo; el A, campo a campo, más adelante.
- **Hecho:**
  - `aed575a`: RECON §7.20 (la fase 2a, la línea base de F1 en 90.0% y D2);
  - esta bitácora:
    - fila D2 con las dos citas literales;
    - estado y fila de la fase 2 ("2a cerrada");
    - las 27 filas de la fase 2 del mapa, marcadas "**2a:** medida en F2_DISCREPANCIAS" con su causa, "no reproducida" o "no medida" (T3 no las cubre: estimaciones, método o infraestructura).
- **Verificación:** la suite, en el mensaje del commit de cierre.
- **Abierto / siguiente paso:**
  - el prompt de la 2b lo escribe el planificador;
  - los commits `65eefb4`, `aed575a` y el de T5 están en local, sin push. Pushear a `main` redespliega: hace falta un "ok, pushea".
- **Archivos tocados:** `docs/RECON.md` y esta bitácora.
- **Avisos para el siguiente chat:**
  - por indicación del usuario ("si exacto significa eso"), el commit de cierre incluye, tal cual, los cambios de otras sesiones que estaban sin commitear en esta bitácora:
    - D3–D6, del planificador y del operador principal;
    - las filas del mapa "Mejora (planificador, F2a)" y "Nuevo (F3prep, CAT)";
    - las entradas F3prep y F67prep;
  - la fila de CAT (F3prep) no lleva marca de la 2a: llegó después de T3 y no se midió.

### #20 · 2026-10-15 · operador principal · Cierre del día: todo fusionado y desplegado
- **Petición del usuario (literal):** "porfavor cerremos todo lo que este abierto hasta ahora. y commiteemos y despleguemos. todo lo pendiente. vigila los demas chats dependientes a este y asegurate que todo este cerrado".
- **Decisiones del usuario registradas antes del cierre:**
  - D5, solo contexto, y D6, sin plan de pago (filas de decisiones).
  - D2 (registro #19).
  - F5prep §5 aceptado: "acepto tus recomendaciones". Es decir: umbral de salto 0.8; series con huecos, a decidir en la fase 5; escisiones como split (UL) con nota y sin bloquear (`1493641`); `config/market.toml`.
- **Hecho:**
  - `7a94020`: los documentos de planificación que estaban sin commitear (`F3_DISENO_METODO.md` y los prompts de F2a, F3prep, F5prep y F67prep). Sin secretos (comprobado contra el Llavero).
  - Fusiones `--no-ff` en `main`:
    - `9b11795` (`fiabilidad/f67-prep`);
    - `f93f5c1` (`fiabilidad/f3-prep`; el planificador había dicho "no fusionar hasta el inicio de la fase 3", y la petición del usuario de cerrar y desplegar todo lo pendiente lo supera);
    - `a2572e0` (`fiabilidad/f5-prep`). Un conflicto, el previsto: `tests/test_config_literals.py`, donde las dos ramas añadían sus módulos a la misma lista. Se conservan las dos entradas.
  - Push `74cd267..a2572e0` a `origin/main` (redespliega Render).
- **Verificación:**
  - `../.venv313/bin/python -m pytest tests -q` sobre la fusión → "3481 passed, 1 skipped in 67.71s".
  - Ningún golden, nada del frontend ni `backend/main.py` cambia (`git diff --name-only 74cd267` → 0). Del motor solo cambia `lib/settings.py` (carga `market.toml`); los módulos nuevos (`reverse_dcf`, `bank_implied`, `price_series`, `market_signals`) no están conectados.
  - `npm run check` → "StockAnalysis encaja con 41 salidas del backend".
  - Producción: `/api/health` → `{"status":"ok","commit":"a2572e0f5ca2accbc123a5140b6929ca80d33952"}` desde las 17:08:29 de Nueva York (push a las 17:06:51). `/api/analysis/AAPL` → 200 en 4 s, MATURE, "Calidad sólida · precio exigente" (igual que su golden); `/api/pdf/AAPL` → 200 en 5 s (133 KB).
- **Sesiones:** F2a, F3prep, F5prep y F67prep cerradas, con sus ramas fusionadas.
  - Los worktrees `../finanzer_next-f3prep`, `-f5prep` y `-f67prep` siguen en disco. El de f67 no se debe borrar mientras la tarea programada corra desde él; si se borra, hay que cambiar la ruta de la tarea a la carpeta principal.
- **Siguiente paso:** el planificador escribe el prompt de la 2b (correcciones de datos de F2_PRECEDENCIA y mapa de la fase 2).

### #21 · 2026-10-16 · operador · Fase 2b (T0–T3 hechas; detenida en el punto de parada 1)
- **Objetivo de la sesión:** prompt `prompts/F2b_verdad_de_datos_corregir.md` hasta el punto de parada 1 (T0–T3).
- **Hecho** (rama `fiabilidad/f2b-corregir`, worktree `../finanzer_next-f2b`; informe completo en
  [`F2b_PARADA1.md`](F2b_PARADA1.md)):
  - **T0:** línea base reproducida, **90.0%** (1,262/1,403); análisis en frío desde este Mac 3.4–4.35 s.
  - **T1** (`b25aed6`): `config/adr.toml` con el factor oficial (depositario, 20-F, F-6, fecha); el implícito, solo
    comprobación ("recompras/emisiones desde el cierre"). BCS 4.154 → 4; TM 11.07 → 10. **Corrige a la 2a:** el 9.6%
    de TM no es un error de Yahoo; es la recompra y amortización de ~1,200 millones de acciones (6-K del 2026-08-04).
  - **T2** (`c9b661d`, `5570d8b`): dividendo indicado en la moneda y la clase del precio con los pagos del propio
    título (`lib/price_history.py`, `lib/dividends.py`); identidad con magnitudes equivalentes en los dos sentidos
    (NVDA subida, PGR extraordinario); **protección 1 retirada** (`main.py`, `display.py`); guardián adaptado. BCS
    2.71%, UL 3.44%, NVDA 0.45%, ASML 0.47% → 0.55% (otro caso del mismo defecto).
  - **T3** (`0c8d211`, `c0b0414`, `4c102ee`, `e6364b2`, `d984181`, `0fd5bd3`): corte coherente (`ttm.find_cut`,
    `data_provenance.as_of`, regla `periodo_incoherente`); Finnhub solo si casa con el corte (BPA y ratios TTM); BPA
    TTM = suma de los BPA diluidos trimestrales; aviso de resultados publicados (`lib/sec_edgar.py`, calendario de
    Finnhub para los 20-F); base del Piotroski declarada.
- **Verificación:**
  - `edgar_verify.py --whatif` → "1264/1391 (90.9%)"; filas "factor ADR" 4 → 0;
  - `pytest tests -q` → "82 failed, 3439 passed, 1 skipped" (los 82, golden: 41 análisis + 41 PDF; regenerarlos
    espera la aprobación);
  - `panel_run --mode replay --compare` → 2 cambios: AMZN precio razonable → exigente; ASML confianza media → baja;
  - `npm run check` → falla solo porque los golden no tienen aún `as_of_note` ni `data_notices`;
  - A/B del análisis en frío (6 tickers, red local) → mediana ≈ 4.2 s sin los hilos nuevos y ≈ 3.6 s con ellos.
- **Decisiones tomadas por el usuario:** ninguna en esta sesión (las pide el punto de parada 1).
- **Abierto / siguiente paso:**
  - el usuario: aprobar los golden (F2b_PARADA1 §4), elegir la regla del factor fuera de la tabla (§1.2; recomiendo B,
    el factor del 20-F vía EDGAR, en T4) y la fuente del dividendo (§2.1; recomiendo b), y poner
    `SEC_EDGAR_USER_AGENT` en Render;
  - el operador, con eso: regenerar los golden, T4–T9.
- **Archivos tocados:** `backend/config/{adr,data,market,schema,validation}.toml`;
  `backend/lib/{currency,display,dividends,finnhub_fallback,numfmt,pdf_report,price_history,sec_edgar,settings,ttm,
  validate,valuation_confidence,yf_adapter}.py`; `backend/main.py`; tests nuevos (`test_adr_factor`, `test_dividends`,
  `test_corte`) y adaptados; fixtures nuevas `tests/fixtures/{history,f2b}` y sus herramientas (`capture_history.py`,
  `history_fixtures.py`, `capture_f2b_sources.py`, `f2b_fixtures.py`); `frontend/src/{lib/api.ts,
  components/StockHeader.tsx}`; `docs/fiabilidad/F2b_PARADA1.md` y esta bitácora.
- **Avisos para el siguiente chat:**
  - `tests/edgar.py` (herramienta de la 2a) y el módulo de producción se llaman distinto a propósito
    (`lib/sec_edgar.py`): con el mismo nombre, `tests/` tapaba a `lib/`;
  - las series de precios y las listas de EDGAR del replay están en juegos aparte y se cortan en la fecha de captura
    de cada ticker; una recaptura del panel las llevará dentro;
  - en el worktree, `.venv313` y `frontend/node_modules` son enlaces a la carpeta principal (ignorados por git).

### #22 · 2026-10-16 · operador · Fase 2b (parada 1 aprobada; golden regenerados; T4 en curso)
- **Objetivo de la sesión:** con la parada 1 aprobada, regenerar los golden y seguir con T4.
- **Decisiones tomadas por el usuario (cita literal):**
  > "Apruebo el punto de parada 1: regenera los golden con el diff causa por causa de F2b_PARADA1 §4, regla del factor
  > B (20-F vía EDGAR en T4) y dividendo (b), pagos del ADR. Sigue con T4."
  - golden: aprobados con el diff causa por causa de F2b_PARADA1 §4;
  - factor ADR fuera de la tabla (§1.2): **regla B**, el factor del 20-F vía EDGAR, en T4 (A queda de respaldo);
  - fuente del dividendo (§2.1): **(b)**, los pagos del propio ADR.
- **Hecho:**
  - golden regenerados (`diff_golden.py --env panel --regenerate --yes` y `--regenerate --yes`); después, los dos
    `diff_golden.py` → "Resultado: sin diferencias"; `pytest -q` → "3521 passed, 1 skipped"; `npm run check` →
    "check-contract: StockAnalysis encaja con 41 salidas del backend".
  - **T4 hecha** (`5857741`, `104df65`, `1362d7a`, `3ef20e7`, `aa89c6c`, `08c97a1`):
    - cliente de EDGAR (`lib/sec_edgar.py`): companyfacts reducido en caché diaria, las instancias de los filings
      que companyfacts aún no trae (iterparse; hasta 3 por análisis), portada del 20-F, sucesión de XOM en config;
      dos etapas en un hilo dentro del presupuesto de 3 s;
    - **regla B** del factor ADR (portada del 20-F; A de respaldo). En vivo sobre 21 portadas: coincide con la tabla
      en los 5 ADR del panel que lo dicen; TSM, TM, BP, GSK, RIO, DEO, SONY, AZN y TTE no lo dicen (regla A);
    - **respaldo del mismo corte** (`lib/edgar_backup.py`): JNJ utilidades retenidas → Altman 4.41; BCS gastos
      financieros, D&A, OCF y dividendos (6-K semestral pendiente leído); BRK-B D&A e inventario; HSBC OCF, capex y
      dividendos; DUK y V dividendos; UL D&A; NVDA pasivo total FY → Altman 12.85. No respalda EBIT bancario ni capex
      de REIT (fase 3, D2), ni deuda (T5), ni salta de concepto (HSBC: la D&A del 6-K incluye deterioros);
    - **D7**: `data_provenance.official_source`, aviso literal (portada y web), insignia "Sin fuente oficial",
      anexo técnico, techo "baja" (dimensión `fuente_oficial`); sin User-Agent o EDGAR caído: nota, sin techo.
      Fixture nuevo del panel **MC.PA** (LVMH), grupo "Sin CIK (fase 2b)";
    - de paso, dos defectos de origen: TM tomaba como FY1 una columna anual de Yahoo sin cifras (calidad 51 → 59,
      Piotroski 5 → 6) y la alerta de BPA en descenso suponía una dilución sin dato (guardián, MC.PA).
- **Verificación T4:**
  - `pytest tests/test_edgar_t4.py` → "36 passed"; `pytest -q` → "85 failed, 3538 passed, 1 skipped" (los 85 son
    golden: 42 análisis + 42 PDF + el de MC.PA, que no existe aún); `npm run check` → contrato roto solo por
    `official_source_badge` ausente en los golden;
  - `edgar_verify.py --whatif` → "1276/1412 (90.4%)" (antes 1264/1391, 90.9%): +12 dentro y +12 fuera. "Sin dato en
    el pipeline" 41 → 16. Las 12 filas nuevas "fuera" son de **periodo**: la herramienta compara el TTM del corte
    (junio de 2026, ahora con el dato de EDGAR) con el FY2025 de EDGAR y las etiqueta "fuente errónea"/"definición";
    no reclasifico la herramienta (regla de la fase); va a la medida final (T8);
  - A/B en vivo, 8 tickers en frío intercalados (con UA / sin UA): mediana 3.64 s frente a 3.83 s (ruido de red);
    EDGAR terminó sus dos etapas dentro del presupuesto en los 8;
  - golden de T4 (sin regenerar): ningún cambio de nivel (calidad, precio, confianza) en 41 análisis; puntuaciones:
    JNJ calidad 84 → 86 y Altman sin dato → 4.41; BCS calidad 72 → 75; TM 51 → 59; NVDA Altman 11.33 → 12.85. En
    todos, `data_provenance.official_source`, `edgar` (hechos, pendientes, respaldo), la dimensión
    `fuente_oficial`, `official_source_badge` y la fila "Fuente oficial" del anexo.
- **Abierto / siguiente paso:** aprobación de los golden de T4 (o junto con los de T5–T7 en la parada de T8);
  T5 (deuda coherente con el EBITDA), T6, T7, T8, T9. El arquetipo esperado de MC.PA queda "?" para el usuario.
- **Comprobaciones pedidas con la aprobación de la parada 1** (llegaron por el coordinador, cita del usuario: "Sí,
  envíale la respuesta recomendada a la sesión de la 2b."; los golden ya estaban regenerados con la aprobación
  directa de este chat, `67f784b`):
  - (i) AAPL, cobertura de intereses sin dato: se trata como **dato ausente**, no como criterio suspendido
    (`score_coverage.solidez.missing = ["Cobertura de intereses"]`, `not_applicable` vacío; solidez reescalada sobre
    3 de 4 componentes). No hay nada que corregir;
  - (ii) ASML, los 3 campos descartados (gastos financieros, dividendos pagados, beneficios retenidos): **no se pueden
    recuperar del mismo corte**. Sus 6-K trimestrales no llevan XBRL (`isXBRL = 0` desde 2025-10) y EDGAR solo los
    tiene al 2025-12-31, con el corte en 2026-03-31. El respaldo de T4 los deja sin dato con ese motivo y la confianza
    baja se mantiene (convergencia no evaluable, estabilidad cíclica y calidad de fuente baja).
  - **T5 hecha** (`4f01557`, `4fca871`, `61a964c`, `4960463`): deuda coherente con el EBITDA (`lib/debt.py`).
    - En US GAAP, la fila "Capital Lease Obligations" de Yahoo resultó ser el **arrendamiento operativo** (a veces con
      el financiero): sale lo operativo y entra el financiero de EDGAR si no está ya (XOM lo presenta dentro de
      `LongTermDebtAndCapitalLeaseObligations`: sin doble cuenta). IFRS 16: la de Yahoo ya es la de la regla.
    - MSFT 56.8 → 106.9 (= what-if de la 2a); AMZN 209.9 → 132.4 (2a: 136.1; la diferencia es la parte corriente de
      su deuda a largo plazo, que AMZN presenta en gastos devengados y Yahoo no recoge; D2: no se sustituye);
      PLTR 0.21 → 0 (era arrendamiento operativo; WACC = Ke); SNOW pasa a caja neta.
    - **O resuelto** (hipótesis 1 del mapa): su 10-Q del 2T da notas 25,092 + préstamos 2,760 + línea de crédito y
      papel comercial 2,763 (`RevolvingCreditFacilityAndCommercialPaper`) + hipotecas 37 = 30,652 = los préstamos de
      Yahoo; la 2a no sumaba la línea de crédito. **DUK:** financiero del 10-K (576) con aviso de fecha.
    - **Bancos:** D/E, deuda / activos, deuda neta y EV fuera ("No aplica": se mide con capital, fase 3);
      subordinada declarada (BCS 14.7, HSBC 27.9 mil millones). **CAT:** cautiva declarada, 34.46 de 45.15 (Cat
      Financial, con dimensión en el 10-Q). **Altman X4** US GAAP sin el arrendamiento operativo.
- **Verificación T5:** `pytest tests/test_debt_t5.py` → "11 passed"; `pytest -q` → "85 failed, 3549 passed,
  1 skipped" (los 85, golden); niveles frente a los golden aprobados → 0 cambios en 42 análisis (calidad MSFT +1,
  DUK +3, RIVN +3, como preveía la 2a; SNOW +10 por la caja neta); `edgar_verify --whatif` → "1282/1411 (90.9%)".
- **Pendiente de confirmar por el usuario en este chat:** el coordinador transmitió que el usuario aprobó regenerar
  ya los golden de T4 (y el arquetipo esperado de MC.PA = el del motor, a revisar en la fase 3, y corregir en T8
  el emparejamiento de periodos de `edgar_verify`), lo que contradice su instrucción directa aquí (aprobarlos en
  T8). No se ha regenerado nada hasta su confirmación aquí.
- **Decisión del usuario (cita literal, en este chat):** "Confirmo lo que pasó el coordinador: regenera ya los golden
  (T4 y T5, sin cambios de nivel), MC.PA con el arquetipo que asigna hoy el motor, y en T8 corrige el emparejamiento
  de periodos de edgar_verify. Sigue con T6." → golden regenerados (`65dde21`), MC.PA esperado = MATURE; las
  muestras forzadas del contrato también en `npm run check` (`6f7a9e7`).
  - **T6 hecha** (`01324a3`, `c8ae863`): beta propia (2 años semanales frente al S&P 500, Blume) o, con R² < 0.1, la
    del sector (`config/betas.toml`: Damodaran, "Betas by Sector (US)", enero de 2026; entra sin Blume); sin serie, la
    de la fuente con aviso; `beta_discrepante` (> 0.5) como aviso. Rango de 52 semanas de la serie (365 días: el
    mínimo de Yahoo en 35 de 35). **Protección 2 retirada** (`c8ae863`): con la 1 (`5570d8b`, registro #21), la 2b
    ya no tiene protecciones provisionales en pie.
  - Desviación justificada del prompt: no se conecta `lib/price_series.py`; la serie del título y del índice ya
    entra por `lib/price_history.py` (T2) y una segunda descarga sería redundante ("descarga lo mínimo").
  - Verificado con Render simulado en vivo (MSFT, DUK, BCS): serie y ^GSPC se descargan; 3.4–4.7 s.
- **Verificación T6:** `pytest -q` → "84 failed, 3564 passed" (los 84, golden de T6); `npm run check` → 46 salidas;
  F1 "1282/1411 (90.9%)". Niveles frente a los golden aprobados: **BRK-B, NVO, NFLX** (previstos por la 2a), **JNJ**
  (precio razonable → exigente, confianza alta → media: R² 0.00 → beta del sector farma 0.98, antes 0.46) y **TM**
  (precio razonable → atractivo: beta propia 0.81, antes 0.92).
  - **Observación para el usuario:** la beta de farma de Damodaran es la media de 228 empresas, muchas pequeñas; para
    un gigante defensivo como JNJ resulta alta. Es la regla aprobada (F2_PRECEDENCIA §5); si se quiere otra (p. ej.
    ponderada por capitalización), es una decisión nueva (D#).

- **Decisión del usuario (cita literal, en este chat):** "Acepto la regla tal cual (JNJ con la beta del sector). Los
  golden de T6 los apruebo en la parada de T8. Sigue con T7." → los golden de T6 y T7 esperan a la parada de T8.
  - **T7 hecha:** las 29 filas de fase 2 del mapa tienen destino (hecha con su commit, o movida con su motivo).
    - Crecimiento interanual (`f762e03`): siempre de los estados, FY0 frente a FY1, rotulado "(último ejercicio)";
      el de la fuente queda como periodo_incoherente (aviso). Sustituye a la guarda anti-artefacto y al aviso a
      15 pp de validate.
    - forwardPE de Finnhub (`8f461cf`): la procedencia declara que es consenso de horizonte no documentado.
    - Factor de split del plan B (`20fc859`): del último evento de la serie de precios.
    - NFLX (`a2bb87a`): el +2.85 B es real (comisión de ruptura de WBD, 10-Q del 1T-2026) y el motor ya lo aísla.
    - Beneficio y patrimonio del ordinario (`7b610a7`, `lib/ordinary.py`): sin cupones AT1 ni dividendos
      preferentes; el ROE y el P/B los usan; el D/E y el Altman siguen con el total.
    - Cambio de perímetro declarado (`a435698`, `lib/perimeter.py`): UL 2023–2024 reexpresados, 2022 en el
      perímetro anterior, el CAGR mezcla bases (su corrección, fase 3).
    - **Movidas:** BRK-B base anual → fase 3 (Yahoo no trae el 3T-2025, confirmado en vivo; completar el corte con
      EDGAR mezclaría dos definiciones de ingresos: Yahoo suma las ganancias de inversión); Yahoo 401 y Yahoo
      distinto en Render → fase 6 (infraestructura).
- **Verificación T7:** `pytest -q` → "84 failed, 3577 passed, 1 skipped" (los 84, golden de T6 sin regenerar).
  Niveles, HEAD frente a cada causa en los 43 análisis (veredicto, calidad, precio, confianza): solo el crecimiento
  mueve algo, sin cambiar ningún veredicto. **MU:** confianza baja → media, porque se van las dos incidencias del
  crecimiento de Finnhub que ya no entra; precio 40 → 35. **NVO:** el PEG trailing usa el crecimiento del BPA del
  último ejercicio, 6.2% frente al 4.9% de Finnhub: 1.89 → 1.50; convergencia y confianza media → alta; precio
  65 → 70. Las demás causas: 0 cambios.
- **Decisión del usuario (cita literal, en este chat):** "Sigue con T8 hasta la parada 2."
  - **T8 hecha hasta el punto de parada 2** (informe `docs/fiabilidad/F2b_PARADA2.md`; muestreo manual en
    `docs/fiabilidad/F2b_MUESTREO_MANUAL.md`).
    - **F1:** 1284/1411 (**91.0%**) con el arreglo de la herramienta (`db4db68`: empareja por data_provenance.as_of,
      TTM frente a TTM), 1276/1411 (90.4%) sin él. Objetivo ≥ 95%: **no alcanzado** (faltan 57 filas).
      - 31 filas fuera son definiciones que cierra la fase 3 por D2 (capex 20, ingresos de bancos 6, caja de bancos y
        aseguradoras 5).
      - 6 son el beneficio del ordinario (T7) frente a la referencia de los propietarios de la herramienta: decisión
        abierta para el usuario.
      - 21 son el EBIT que construye Yahoo: la marca "estimado" de F2_PRECEDENCIA no estaba en el prompt; se propone
        para la fase 3.
    - **Golden de T6–T7 sin regenerar:** diff causa por causa en el informe, §3. Cambios de nivel solo en T6 (BRK-B,
      JNJ, NVO, TM, NFLX); T7 no cambia ningún veredicto.
    - **Tiempo** en frío: mediana ≈ 3.2 s (T0 ≈ 4.2 s).
    - **Web recompilada** (`7805de9`, con webpack: el `node_modules` del worktree es un enlace).
- **Verificación T8:** `edgar_verify.py --whatif` → "1284/1411 (91.0%)"; `--sin-as-of` → "1276/1411 (90.4%)";
  `pytest -q` → "84 failed, 3577 passed, 1 skipped" (los 84, golden de T6–T7); `npm run check` → 46 salidas;
  `perfil_local.py --red-local` → 3.09–3.44 s en frío. Navegador (replay del panel): MC.PA con la insignia y el aviso
  de D7, la tabla de Crecimiento con "(último ejercicio)", sin errores en la consola.
- **Punto de parada 2:** esperando del usuario la aprobación de los golden de T6–T7, la decisión sobre la referencia
  del beneficio neto en F1, el alcance del EBIT "estimado" y el "ok, pushea". Falta `SEC_EDGAR_USER_AGENT` en Render.
- **Decisión del usuario (cita literal, en este chat):** "si. aprueba y genera. con F1 haz lo que mejor
  financieramente podemos hacer. y con todo lo demas haces lo que debe hacer una app de analisis financiero. y si, ya
  puedes pushear".
  - EBIT de la fuente marcado "estimado por la fuente" si difiere > 2% del de EDGAR (`4310fc8`; F2_PRECEDENCIA
    §2.1, escenario B): KO, PLD, NEE, DUK, FCX, CRWD, UL, V. Sin cambios de nivel.
  - F1 con la referencia del accionista ordinario (`a3b4c7a`): campos **1290/1411 (91.4%)**, ratios 193/216 (89.4%).
    Objetivo del 95% no alcanzado: lo que queda fuera se cierra en la fase 3 (definiciones de D2, EBIT) o es
    definición por diseño (dividendo indicado, deuda de la regla).
  - Golden regenerados (`dcdda74`). `pytest -q` → "3662 passed, 1 skipped"; `npm run check` → 46 salidas.
- **Push y deploy (2026-10-16):** rama `fiabilidad/f2b-corregir` subida y `main` adelantado (fast-forward desde
  `60f8a69`).
  - El primer deploy (`bdc474d`) no pasaba las guardas de `build.sh`: la web compilada con webpack no traía
    `build-stamp.json` y referenciaba el chunk de `/stock/[[...symbol]]` codificado. Se recompiló con Turbopack en el
    checkout principal (`fafee5d`) y se comprobó con las dos guardas en local.
  - **Comprobación en producción** (`/api/health` = `fafee5d`; 20:53 de Nueva York; concurrencia 3): BCS, TSM, NVO,
    UL, NVDA, PGR, JNJ, MSFT, AMZN, XOM y MC.PA responden en 4.6–12.2 s.
    - Dividendos correctos: BCS 2.72%, TSM 0.93%, NVO 4.77%, UL 3.36%, NVDA 0.47%, PGR 0.18% (ordinario).
    - Beta propia o del sector; corte coherente; aviso de resultados pendientes en TSM, PGR y JNJ.
  - **Fallo encontrado y corregido en origen** (`103c76f`): XOM con el rango "sin dato". Yahoo da la barra del día
    con el cierre vacío y la serie la descartaba, así que la cotización de hoy quedaba fuera del rango. Tras el
    redeploy (`/api/health` = `103c76f`): XOM 111.18–179.16, "En máximos de 52 semanas"; la web, sin errores en la
    consola.
  - **Pendiente del usuario:** `SEC_EDGAR_USER_AGENT` en Render. Sin él, producción va sin EDGAR ("verificación
    oficial no disponible"). Queda sin la deuda de la regla (MSFT 56.8 y AMZN 209.9 son los de la fuente), sin el
    respaldo (Altman de JNJ sin dato), sin la marca del EBIT estimado y sin el aviso D7 de MC.PA. Con la variable
    puesta, repetir la comprobación.
  - **Siguiente:** T9 (RECON §7.21 y cierre de la 2b en la bitácora).

### #23 · 2026-10-16 · operador · Fase 2b cerrada (T9)
- **Objetivo de la sesión:** T9: RECON §7.21 y cierre de la 2b en la bitácora.
- **Decisiones tomadas por el usuario (cita literal):** "Sigue con T9 y cierra la 2b."
- **Hecho:**
  - RECON §7.21: resumen de T1–T8 con los commits, la medida final, la producción y lo que pasa a la fase 3.
  - Estado actual y fila de la fase 2 en "cerrada".
  - El mapa ya estaba al día desde T7: las 29 filas de fase 2 tienen destino. La fila "sin parches" está marcada como
    hecha: protección 1 retirada en `c9b661d`, protección 2 en `c8ae863`.
- **Definición de terminado de la 2b (prompt §5):**
  - ✅ factor ADR oficial;
  - ✅ dividendo y protección 1;
  - ✅ corte coherente;
  - ✅ cliente de EDGAR y D7;
  - ✅ deuda coherente con el EBITDA (O y DUK resueltos);
  - ✅ beta y rango, con la protección 2 retirada;
  - ✅ mapa;
  - ⚠️ F1 91.4%, por debajo del 95%: el número real, con lo que falta y su fase, en RECON §7.21. Muestreo de 5
    tickers preparado, golden aprobados y tiempo medido;
  - ✅ desplegado con "ok, pushea" y verificado en producción (`103c76f`). RECON y bitácora al día.
- **Verificación:**
  - `curl https://finanzer.app/api/health` → `{"status":"ok","commit":"103c76f…"}`;
  - comprobación de producción de los 11 casos (registro #22);
  - `pytest -q` → "3663 passed, 1 skipped" (en `103c76f`).
- **Abierto / siguiente paso:**
  - El usuario pone `SEC_EDGAR_USER_AGENT` en Render y se repite la comprobación de producción: deuda de MSFT y AMZN,
    Altman de JNJ, EBIT estimado y D7 en MC.PA.
  - El planificador escribe el prompt de la fase 3. Este operador se detiene aquí.
- **Archivos tocados:** `docs/RECON.md` (§7.21) y `docs/fiabilidad/BITACORA.md`.
- **Avisos para el siguiente chat:**
  - `frontend/out` se compila con `npm run build` (Turbopack + postbuild) en el checkout principal; en un worktree el
    `node_modules` es un enlace y Turbopack falla, y con webpack `build.sh` de Render rechaza el deploy.
  - Para medir niveles por causa: exportar cada commit con `git archive` y enlazar `tests/fixtures/edgar/raw`
    (ignorado por git).
  - F1: `edgar_verify.py --sin-as-of --ni-propietarios` reproduce la medida de la 2a.

### #24 · 2026-10-16 · operador · Fase 3 (T0–T1 hechas; detenida en el punto de parada 1)
- **Objetivo de la sesión:** arrancar la fase 3 con el prompt revisado por el planificador: línea base (T0) y
  propuesta de definiciones de D2, historia larga, moneda del crecimiento y tasas base (T1).
- **Decisiones tomadas por el usuario (cita literal):** "Eres el operador de la fase 3 del plan de fiabilidad de
  Finanzer. Lee y sigue al pie de la letra docs/fiabilidad/prompts/F3_metodo_por_tipo_de_negocio.md (versión revisada
  por el planificador, sin commitear en main: commitéala en tu rama como primer commit, "F3: prompt revisado por el
  planificador")."
- **Hecho:**
  - rama `fiabilidad/f3-metodo` en el worktree `../finanzer_next-f3`, desde `main` = `b2f1972` (local, sin subir);
    primer commit `3d52202` con el prompt revisado. La copia sin commitear del prompt en el checkout principal se
    descartó tras comprobar que era idéntica a la commiteada (`cmp`);
  - T0 (línea base): suite, F1, panel de 37 y estado de EDGAR en producción (abajo);
  - T1: `3c331dd` (herramientas `tests/f3_t1_whatif.py`, `f3_t1_depth.py`, `f3_t1_mem.py`) y `20c2a2e`
    (`docs/fiabilidad/F3_T1_PARADA1.md`): definición propuesta de capex, EBIT, EBIT bancario, ingresos de bancos, de
    BRK-B, de utilities y de XOM, caja y deuda, con la causa medida de cada diferencia de Yahoo (CAT suma el equipo
    arrendado de Cat Financial; KO excluye otros cargos operativos; BRK-B suma las ganancias de inversión; NEE, DUK y
    XOM: concepto equivocado de la herramienta); EDGAR principal recomendado en EBIT, ingresos de BRK-B y de bancos de
    EE. UU. y capex con cautiva; historia larga ya disponible en la descarga de la 2b (19 ejercicios en EE. UU.; NVO 7,
    TM 6 en IFRS); coste en frío 0.45–0.75 s y pico de memoria +80–116 MB por lectura (propuesta: LRU de 64 y semáforo
    de 1); crecimiento en la moneda de los estados; tasas base: fuente oficial localizada (Mauboussin y Callahan,
    Morgan Stanley, "Bayes and Base Rates", 10-feb-2026), pendiente de permiso de descarga.
- **Verificación:**
  - `pytest tests -q` → "3660 passed, 4 skipped" (T0, sin `node_modules` enlazado) y "3663 passed, 1 skipped" (tras
    enlazar `frontend/node_modules` y añadir las herramientas);
  - `edgar_verify.py --whatif` → "1290/1411 (91.4%)" (igual que el cierre de la 2b);
  - `panel_run.py --mode replay` → 37 tickers, 18 con un solo método de precio, arquetipo distinto del esperado en
    CAT, PLTR, NVDA, CRWD y TSM; precio: 15 razonable, 14 exigente, 4 atractivo, 3 muy exigente; confianza: 28
    media, 5 alta, 3 baja;
  - `curl https://finanzer.app/api/analysis/JNJ` → `data_provenance.edgar.status = "desactivado"` (`/api/health` =
    `01336e2`): **`SEC_EDGAR_USER_AGENT` sigue sin estar en Render**;
  - `f3_t1_whatif.py` → 1 cambio de nivel en 36 (BRK-B calidad excelente → sólida, 81 → 76); KO 85 → 82, PLD 82 → 85
    y precio 46 → 50, AMT 79 → 75, CAT precio 39 → 42.
- **Abierto / siguiente paso:** decisiones del usuario en F3_T1_PARADA1 §0 (definiciones, EDGAR principal por campo,
  moneda del crecimiento, permiso para descargar el PDF de tasas base) y la variable de Render. Después, T1b.
- **Archivos tocados:** `docs/fiabilidad/prompts/F3_metodo_por_tipo_de_negocio.md` (revisión del planificador),
  `docs/fiabilidad/F3_T1_PARADA1.md`, `backend/tests/f3_t1_*.py` y esta bitácora.
- **Avisos para el siguiente chat:**
  - en el worktree, `tests/fixtures/edgar/raw` y `frontend/node_modules` son enlaces al checkout principal
    (excluidos en `.git/info/exclude`);
  - el PDF de Morgan Stanley no se puede leer sin descargarlo (403 a lecturas automáticas): descargar es una acción
    que el usuario autoriza;
  - `main` local va por delante de `origin/main` con `b2f1972` (borrador del prompt): no se ha subido.

### #25 · 2026-10-16 · operador · Fase 3 (parada 1 aprobada; T1b en curso)
- **Objetivo de la sesión:** con la parada 1 aprobada, implementar T1b (capa de datos).
- **Decisiones tomadas por el usuario (cita literal):** "Apruebo tus recomendaciones de la parada 1: definiciones de
  §1.1, EDGAR principal en EBIT, ingresos de BRK-B y de bancos de EE. UU. y capex con cautiva; crecimiento en la moneda
  de los estados; y te autorizo a descargar el PDF 2.0 de Morgan Stanley."
  - definiciones de F3_T1_PARADA1 §1.1 (capex sin el equipo arrendado de la cautiva; EBIT reportado; EBIT de bancos
    "no aplica"; ingresos netos totales de bancos; ingresos de BRK-B sin ganancias de inversión; caja de no
    financieras con inversiones a corto plazo; caja de financieras fuera de la deuda neta);
  - EDGAR principal (D2) en: EBIT, ingresos de BRK-B y de bancos de EE. UU., capex de emisores con cautiva;
  - crecimiento y CAGR en la moneda de los estados, con el efecto divisa aparte;
  - tasas base: descarga autorizada del PDF 2.0 (13-may-2026).

### #26 · 2026-10-16 · operador · Fase 3 (T1b hecho; detenida en el punto de parada 1b)
- **Objetivo de la sesión:** implementar las decisiones de la parada 1 (capa de datos) y medir.
- **Decisiones tomadas por el usuario:** las del registro #25. Ninguna nueva en esta parte.
- **Hecho** (informe: `docs/fiabilidad/F3_T1B_PARADA1B.md`):
  - EDGAR como fuente principal: EBIT (`d34c858`), ingresos de aseguradoras, conglomerados y bancos de EE. UU.
    (`7685a1b`, `a997ee2`), capex con cautiva (`5043eca`);
  - historia anual larga con caché LRU y semáforo (`84fc641`; juego f2b ampliado desde la caché local de la 2a);
  - dos defectos latentes en producción que la historia destapó: perímetro con reexpresiones antiguas (`0d48d11`) y
    "último informe anual" de la deuda sin límite (`090f38b`);
  - crecimiento en la moneda de los estados (`3b16823`);
  - herramienta F1 con las definiciones aprobadas (`78fa695`, `0f85a69`).
- **Verificación:**
  - `edgar_verify.py --whatif` → "1339/1411 (94.9%)"; `--sin-definiciones-f3` → "1319/1411 (93.5%)" (T0: 91.4%);
  - `panel_run.py --compare <T0>` → un cambio de nivel: BRK-B calidad excelente → sólida;
  - `pytest tests -q --ignore=tests/test_regression.py` → todo en verde salvo `test_forced_samples_are_up_to_date`
    (muestras del contrato, se regeneran con los golden); `test_regression.py` → "66 failed" (golden pendientes).
- **Abierto / siguiente paso:** aprobación de los golden (F3_T1B_PARADA1B §3), decisión del EBITDA (§5, abierta),
  `SEC_EDGAR_USER_AGENT` en Render (sin ella no hay deploy) y "ok, pushea".
- **Archivos tocados:** `lib/edgar_primary.py` (nuevo), `lib/growth_currency.py` (nuevo), `lib/sec_edgar.py`,
  `lib/perimeter.py`, `lib/archetype_metrics.py`, `lib/yf_adapter.py`, `main.py`, `config/data.toml`,
  `config/schema.toml`, `tests/edgar_verify.py`, tests nuevos y el juego `tests/fixtures/f2b/edgar/companyfacts`.
- **Avisos para el siguiente chat:**
  - el juego f2b ya trae la historia larga: se amplía con `tests/f3_extend_history_fixtures.py` desde la caché local
    de la 2a (no captura en vivo; los CIK sin caché local se listan);
  - la regla de industria debe normalizarse con `classify.norm_industry` (Yahoo usa raya: "Insurance—Diversified").

### #27 · 2026-10-16 · operador · Fase 3 (parada 1b: golden aprobados; EBITDA)
- **Decisiones tomadas por el usuario (cita literal):** "Apruebo los golden de T1b (F3_T1B_PARADA1B §3) y el EBITDA =
  EBIT reportado + D&A (opción a). También te autorizo a descargar el PDF "The Impact of Intangibles on Base Rates" de
  Morgan Stanley."
  - golden de T1b: aprobados con el diff de F3_T1B_PARADA1B §3;
  - EBITDA = EBIT que presenta el emisor + D&A (opción a de §5);
  - tasas base: descarga autorizada de "The Impact of Intangibles on Base Rates" (Morgan Stanley, 23-jun-2021).
- **Hecho:** golden regenerados (`diff_golden.py --regenerate --yes` en los dos juegos y `contract_forced.py --write`);
  después, los dos `diff_golden.py` sin diferencias (código de salida 0) y `pytest tests -q` → "3701 passed, 1 skipped".
- **Hecho (continuación de #27):**
  - `76747c8`: EBITDA = EBIT del emisor + D&A, con el FFO anual de los REIT como beneficio + D&A. Ningún cambio de
    nivel; diff en F3_T1B_PARADA1B §6.2, golden **sin regenerar** hasta la aprobación;
  - `97c8c6b`: tasas base en `config/base_rates.toml` (Mauboussin y Callahan, 2021, Exhibit 3, pp. 6–8). Tramos e
    industrias cuadran con el total (test).
- **Abierto:** aprobación del diff del EBITDA, `SEC_EDGAR_USER_AGENT` en Render y "ok, pushea" del primer deploy.
- **Decisión del usuario (cita literal):** "Apruebo el diff del EBITDA (F3_T1B_PARADA1B §6.2): regenera sus golden."
  Golden regenerados (`diff_golden.py --regenerate --yes` en los dos juegos y `contract_forced.py --write`); los dos
  `diff_golden.py` sin diferencias; `pytest tests -q` → "3713 passed, 1 skipped".

### #28 · 2026-10-17 · operador · Fase 3 (T2 hecha; detenida en el punto de parada 2)
- **Decisión del usuario sobre la cobertura de intereses (cita literal):** "okat predecto. lo cubrimos cuando requiera.
  bueno, continua con el plan. sigue ejecutando". Las tres mejoras quedan en el mapa para la T6 (commit `3966a43`).
- **Hecho (T2, un commit por causa, tests antes):**
  - historia: `dc62a83` (discontinuadas e ingresos de contratos con clientes), `b07983c` (splits y errores de escala),
    `9e76d50` (split entre taxonomías, TM);
  - clasificador: `9ea8193` (ciclicidad por la historia, GROWTH_PROFITABLE, subtipos de FINANCIAL, frontera ±20%,
    industria con confianza baja sin historia), `0ca5937` (nota de crecimiento estructural), `ddd7796` (motivo
    concreto de la confianza baja), `4516eae` (rupturas del capital: PLTR), `0f121bc` (alerta medida con la historia
    en FINANCIAL, REIT y UTILITY);
  - herramienta: `d2333b3` (`tests/f3_t2_measures.py`).
- **Reapertura de diseño (no la decido yo):** las medidas de F3_DISENO §1.2 marcan cíclicas a KO, PG, JNJ, V, NVDA,
  PLTR, NFLX y AMZN. Propuesta: episodios repetidos de caída de ingresos y desplomes del BPA con caída de ventas
  (F3_T2_PARADA2 §2).
- **Provisional, declarado:** GROWTH_PROFITABLE usa las herramientas de MATURE hasta la T3/T6.
- **Verificación:** `pytest tests -q` → "71 failed, 3660 passed, 1 skipped". Lo que falla son los golden de los dos
  juegos y las muestras forzadas del contrato, pendientes de aprobación. `panel_run --compare` frente a `3966a43`:
  8 cambios de arquetipo (CAT, KO → CYCLICAL; TM → MATURE; MSFT, NVDA, NVO, PLTR, TSM → GROWTH_PROFITABLE), cada uno
  explicado (F3_T2_PARADA2 §6).
- **Abierto:** aprobación línea a línea de los arquetipos (§5), reapertura de §1.2, KO (§3, recomendada la opción a:
  desinversiones como cambio de perímetro), golden (§7). De la 1b: `SEC_EDGAR_USER_AGENT` en Render y "ok, pushea".
  Sin la aprobación de los arquetipos no empieza la T3.

### #29 · 2026-10-17 · operador · Fase 3 (parada 2 decidida bajo delegación; T3 en curso)
- **Delegación del usuario (cita literal):** "no esperes ningunan dicesision mio, no me esperes para ejecitar el
  siguiente paso. te doy absoluto permiso para que ttrbajaes hasta que termines absolutamente todo el proyecto con
  todas sus fases y tareas. si necesitas una decision, tomala tu desde el mejor punto de vista de un anasista
  financiero de acciones."
- **Decisiones tomadas por el operador con esa delegación** (F3_T2_PARADA2 §9):
  - reapertura de §1.2 aprobada, con la condición de apalancamiento operativo (`0fe8ef0`);
  - KO y TM son MATURE;
  - arquetipos del panel aprobados.
- **No hecho:** regenerar los golden de T2. La acción `diff_golden.py --regenerate --yes` fue denegada por el
  clasificador de permisos de la sesión; queda para el usuario.
- **Límites que la delegación no levanta:**
  - `SEC_EDGAR_USER_AGENT` en Render: es su cuenta, y es requisito de cualquier deploy de la fase 3;
  - ningún push mientras falte esa variable.


### #30 · 2026-10-17 · operador · Fase 3 (T3 hecha, bajo la delegación del registro #29)
- **Hecho (un commit por causa):**
  - `f8e5750`: una sola estructura de DCF (§8.2): 5 años constantes y convergencia lineal en los años 6–10. Se retiran
    los decaimientos lineal y exponencial. `growth_cap` (50%) queda como guarda interna; el tope de entrada (30%) no
    cambia: la plausibilidad la juzga el inverso con las tasas base (§8.3);
  - `fa9a156` + `817eda4`: FCF − SBC siempre que haya SBC del mismo periodo (§8.4). SNOW y AMZN pasan a DCF no
    significativo; V, de fiabilidad alta a media;
  - `19def27`: DCF inverso conectado (§2, §8.1, §8.5, §8.7).
    - Tasas base con lognormal ajustada a mediana y desviación típica. Bandas: < 10% de comparables, muy exigente;
      < 25%, exigente; si no, la historia propia a ±5 pp.
    - Es el método intrínseco cuando el directo tiene fiabilidad baja, y en los REIT (sobre FFO).
  - `d71f0a2`: opción 3 de §7.17. Niveles que cambian solo por ella: 3 (DUK, NEE, SNOW: confianza media → alta);
  - `b120c33`: frase del inverso en la web y en el PDF; guardián con predicado `implied_growth`;
  - `787317a`: contraste independiente en KO, V, NFLX, DOW y PG: Δ = 0.000000 pp.
- **Decisiones del operador (delegación #29), con su porqué:**
  - lognormal: los autores advierten cola a la derecha;
  - fila "All" con < 100 observaciones: 100+ Healthcare tiene 7 observaciones a 10 años;
  - deflactor del IPC-U 2024/2020 = 0.825;
  - industria de Yahoo → Fama y French 5 (tabla en config);
  - puntos del inverso con la escala del DCF de fiabilidad alta.
- **Medido (replay, panel):**
  - precio: muy exigente 3 → 9, exigente 14 → 10, razonable 15 → 14, atractivo 4 → 3 (no extremo);
  - ningún DCF de fiabilidad baja sin el inverso mostrado;
  - `pytest tests -q --ignore=tests/test_regression.py` → "1 failed, 3605 passed, 1 skipped". Lo que falla son las
    muestras forzadas del contrato, que se regeneran con los golden, bloqueados por permisos (#29).

### #31 · 2026-10-17 · operador · Fase 3 (T4–T8 hechas; parada 3 decidida bajo la delegación del registro #29; fase cerrada en código)
- **Hecho (un commit por causa; detalle en F3_T7_PARADA3 §1 y RECON §7.22):**
  - **T4, financieras:**
    - `e2b4c3b` + `afae76a`: ROTE ordinario y ROTE/ROE implícito con banda y sensibilidad;
    - `1c3dbad`: P/E en bancos y aseguradoras (registro #14);
    - `6912ded`: subtipo visible y servidor de replay;
    - `9155044`: margen de intereses aparte.
  - **T5, crecimiento:**
    - `c12ad29`: retorno total con dividendo ≥ 4%;
    - `381c863`: perímetro homogéneo;
    - `e353392`: ciclo medio de pico a pico;
    - `57e8d46`: base ≤ 0;
    - `afdd1d8` + `26aa866`: mezcla del interanual y del CAGR a 3 años.
  - **T6, lecturas por modelo de negocio:**
    - `ceac134`: circulante estructural, Altman referencial y Piotroski;
    - `4ae7705`: cautiva fuera de la deuda industrial;
    - `51201e2` + `784b7eb`: DuPont, margen FCF, regla de 40, SBC y cobertura de intereses con EBITDA, tendencia,
      intereses pagados y FFO;
    - `d2a6adc`: PEG a 3 años.
  - **T7, verificación:**
    - `3f4be83`: método intrínseco por flujo de mantenimiento y para utilities;
    - `c8ab2fe`: CAGR por años de calendario (NOW);
    - `52403a2`: fixtures externos;
    - `8a58618`: cautiva sin desglose (DE);
    - `2e4d6ad`: documento de la parada 3.
- **Decisiones del operador (delegación #29), con su porqué de analista:**
  - **Utilities: P/B frente al ROE regulado como método intrínseco.** Su FCF es negativo por diseño (capex
    regulado), y el regulador remunera la base de activos.
  - **Owner earnings con FCF − SBC ≤ 0:** OCF − D&A − SBC. La D&A aproxima el capex de mantenimiento.
  - **ROE medio en aseguradoras:** el ciclo de suscripción hace engañoso el ROE de un año. Con él, PGR pasa de
    atractivo a razonable.
  - **P/E en financieras:** los analistas de bancos lo usan junto al P/TBV. Con él, BCS pasa a atractivo y HSBC, a
    razonable.
  - **Parada 3 aprobada:** las 9 fichas de analista, una por arquetipo, coinciden con la lectura de un analista
    (F3_T7_PARADA3 §3).
- **Mapa:**
  - cerradas: 25 filas;
  - movidas a la fase 6: BRK-B en base anual y su P/E (TTM), que necesitan el corte LTM con los 10-Q de EDGAR;
  - descartadas, con su motivo: compromisos fuera de balance (sin importe en XBRL) y la inflación de TXRH (sin
    fuente); dentro de la fila 170, hecha en parte;
  - la fila del Graham en REIT ya estaba resuelta desde la etapa 9a.
- **Medido (replay, panel):**
  - un solo método evaluable: 18 → 2;
  - precio: muy exigente 3 → 10, exigente 14 → 7, razonable 15 → 16, atractivo 4 → 3;
  - confianza: alta 5 → 10, media 28 → 23, baja 3 → 3;
  - F1: 94.9% (sin cambio desde T1b);
  - tiempo del panel: 7.7 → 7.9 s;
  - `pytest tests -q --ignore=tests/test_regression.py` → "1 failed, 3659 passed, 1 skipped". Lo que falla son las
    muestras forzadas del contrato, que van con los golden.
- **No hecho, del usuario:**
  - regenerar los golden de T2–T7: el clasificador de permisos de la sesión bloqueó la acción, y no se rodeó;
  - `SEC_EDGAR_USER_AGENT` en Render;
  - "ok, pushea";
  - deploy y comprobación en producción;
  - `npm run build` en el checkout principal.
- **Siguiente:** fase 4 (escalas y confianza) según PLAN_FIABILIDAD §4, en la rama `fiabilidad/f4-escalas`, que sale de
  `fiabilidad/f3-metodo`, bajo la misma delegación.


### #32 · 2026-10-17 · operador · Fase 4 (cerrada en código bajo la delegación del registro #29) y revisión de código de la fase 3
- **Sin prompt del planificador:** con la delegación, el operador leyó PLAN_FIABILIDAD §4 y lo ejecutó. Rama
  `fiabilidad/f4-escalas`, que sale de `fiabilidad/f3-metodo`.
- **Hecho (un commit por causa; detalle en F4_PARADA §1):**
  - `1f12e33`, `92a279e`: persistencia de la calidad por encima de 80;
  - `122cbb4`, `e5baf6e`: confianza por causas reales;
  - `a0aa922`: aviso de frontera;
  - `bc4fa89`, `f99859a`: pre-mortem;
  - `ea2926b`, `71b5184`: bandas paralelas.
- **Revisión de código independiente de la fase 3** (protocolo §5.7). De los 8 hallazgos, 6 confirmados y 2
  plausibles, todos arreglados con prefijo F3:
  - `6578a63`: el ciclo medio se dividía dos veces por las acciones;
  - `583f112`: los ejercicios de 52/53 semanas desplazaban el año (JNJ: 3 años 9.6% → 8.9%);
  - `9fecbf3`: el tramo de tamaño de las tasas base leía otra moneda como USD;
  - `c12b3e8`: el rótulo del DCF inverso decía "flujo de mantenimiento" cuando no lo era;
  - `dea16bf`: el retorno total de la madura de dividendo alto se calcula por acción;
  - `d8b59a1`: el perímetro se casa por fecha;
  - `8c53940`: las lecturas de calidad cruzan estados por ejercicio.
  - El hallazgo 3 (interanual de la fuente en la mezcla del DCF) no se reproduce: la 2b (`f762e03`) ya lo sustituye
    por el de los estados.
- **Decisiones del operador (delegación #29), con su porqué de analista:**
  - **Persistencia en el total y no por categoría.** Por categoría rebajaba también lo que solo es "excelente" (KO
    82 → 79); el plan pide que el 100 sea raro, no mover el umbral de excelente.
  - **Anclas:** el margen frente al actual (¿es un pico?), ingresos sin retrocesos y conversión en caja. Es la
    persistencia del rendimiento (Mauboussin). Un año sin dato no prueba nada.
  - **"Alta" exige ninguna dimensión baja:** una cíclica o datos rechazados son una debilidad clara.
  - **Finnhub deja de restar en la fuente:** desde la 2b solo entra si casa con el corte.
  - **Pre-mortem en el sentido del nivel:** con precio exigente, la lectura falla si la empresa sí sostiene el
    crecimiento exigido; con precio razonable o atractivo, si crece menos de lo que ya descuenta.
- **Medido (replay, panel):**
  - calidad > 95: 4 → 2 (TSM 99, V 96), ninguna en 100;
  - confianza alta: 10 → 12;
  - frontera: 11;
  - pre-mortem: 34 de 36 (el mensaje de `bc4fa89` dice 33 por error; son 34);
  - niveles de calidad y de precio: 0 cambios;
  - tiempo: 8.1 s;
  - `pytest tests -q --ignore=tests/test_regression.py` → "1 failed, 3803 passed, 1 skipped". Lo que falla son las
    muestras forzadas del contrato, que van con los golden.
- **Revisión externa:**
  - NOW: sin hallazgos;
  - DE: la deuda del pre-mortem incluye la cautiva, y ahora se dice;
  - SAN: la ventana se anclaba en los ingresos IFRS de EDGAR, que acaban en 2017. Error de fondo, arreglado.
- **Web:** comprobada en replay (NFLX: nota de persistencia y pre-mortem).
- **No hecho, del usuario:**
  - permiso para descargar los conjuntos de datos de Damodaran: referencias por industria y geografía, y medianas
    con fuente;
  - golden;
  - `SEC_EDGAR_USER_AGENT`;
  - "ok, pushea";
  - deploy.
- **Movido:** las bandas de REIT y utilities sin muestra, a la fase 7 (calibración con EDGAR).
- **Siguiente:** fase 5 (capa técnica y conductual), PLAN §4; la preparación F5prep ya está fusionada, con los módulos
  aislados.
- **Adenda, revisión de código independiente de la fase 4** (protocolo §5.7). De los 7 hallazgos, todos arreglados y
  sin cambios en el panel:
  - `8834e60`: la fuente excluye por regla, no por acción; antes se perdían los rechazos "sin_dato";
  - `bbcdf67`: estados casados por fecha de cierre, ejercicios de 52/53 semanas;
  - `72ad982`: retorno total por acción en el perímetro homogéneo y con las acciones casadas por fecha;
  - `f27d5c5`: pre-mortem fuera de rango en el sentido del nivel;
  - `4d7b1e2`: persistencia con ventana por fecha, sin regla vacía.


### #33 · 2026-10-17 · operador · Fase 5 (cerrada en código bajo la delegación del registro #29)
- **Hecho:**
  - `9363163`: serie del ETF del sector y sus fixtures;
  - `309ed32`: contexto de mercado y lectura conductual, aparte y sin puntuar, en una pestaña web y en la sección 07
    del PDF, más los titulares de 7 días de Finnhub;
  - `a0a13a3`: fixture de MC.PA con su EUR→USD; destapado al probar un ticker suelto.
- **Comprobado con la clave:** Finnhub `company-news` es gratuito en el plan actual (AAPL, 247 titulares en 7 días).
  La clave no salió del Llavero ni se imprimió.
- **Decisiones del operador (delegación #29):**
  - huecos sueltos tolerados (≤ 5) y declarados;
  - calendario de EE. UU. solo para lo que cotiza en dólares;
  - ventana de 2 años: caída de 1 año y de la serie entera;
  - sobrerreacción con el BPA sin caer y sin cíclicas;
  - PEAD sin leer, por falta de fuente para la sorpresa, y se dice.
- **Revisión de 5 lecturas conductuales** (la del usuario según el plan, hecha bajo la delegación): ninguna suena a
  recomendación. Se corrigió la redacción de la extrapolación de NVDA, que decía "en línea" con un crecimiento
  logrado del doble (F5_PARADA §2).
- **Medido (replay, panel):**
  - señales en 36 de 36;
  - contraste independiente a 1e-9 en 7 tickers;
  - lectura conductual: anclaje 7, sobrerreacción 2, extrapolación 4;
  - 0 cambios de nivel;
  - 8.6 s;
  - `pytest tests -q --ignore=tests/test_regression.py` → "1 failed, 3902 passed, 1 skipped". Lo que falla son las
    muestras forzadas del contrato.
- **Revisión externa:** NOW, DE y SAN, sin hallazgos.
- **Web:** comprobada en replay.
- **Pendiente:** medir la latencia en Render (va con el deploy); golden, `SEC_EDGAR_USER_AGENT`, "ok, pushea" y
  deploy, del usuario.
- **Siguiente:** fase 6 (infraestructura, solo código por D6) y fase 7 (calibración).

### #34 · 2026-10-17 · operador · Fase 6 (cerrada en código bajo la delegación del registro #29) y revisión de código de la fase 5
- **Revisión de código de la fase 5** (`76316bf`, F5_PARADA §6), 10 hallazgos arreglados:
  - ETF del sector y titulares en paralelo, con espera máxima;
  - sobrerreacción con los ingresos de los estados, no con el retorno total;
  - fuerza relativa solo en USD;
  - volumen bajo descrito como tal;
  - distancia al máximo sobre la cotización sin ajustar (NVO: 65.2% → 67.8%);
  - lecturas conductuales sin tono de previsión;
  - limitación de los titulares en replay declarada.
- **Hecho (F6_PARADA):**
  - `94ce758`, `6fb46c3`: análisis, PDF y búsqueda fuera del bucle de eventos, con un semáforo de 4;
  - `1b8f5ca`: caché de los estados de 6 h;
  - `fafdf3b`: trimestrales en paralelo;
  - `b586299`, `a83fe4e`: procedencia por fuente en el anexo;
  - `96a7e8c`: el 8-K de resultados del propio corte no se avisa como pendiente;
  - `9b7bbc4`: **corte de doce meses de EDGAR cuando Yahoo no trae 4 trimestres**. BRK-B al 30-jun-2026: P/E 16.96 → 13.24 y ROE 9.3% → 11.5%, sin cambio de nivel. UL se queda en el ejercicio porque el corte de EDGAR perdería deuda y EBITDA.
- **Medido** (local, en vivo, Render simulado, 12 tickers fuera del panel a la vez):
  - frío: de 25.8–26.5 s a 7.1–7.9 s en total, con EDGAR completo en los 12;
  - `/api/health`: de 13 s de mediana a 0.001 s;
  - con la cotización caducada y los estados en caché: 2.3 s;
  - con la red lenta, dos corridas dieron 19 s. La SEC (≤ 10 peticiones/s) es el límite real de 12 a la vez.
- **Revisión de código de la fase 6:** 9 hallazgos, arreglados en `2006379`, `dd0ca0a`, `0d86c00` y `ead7808`:
  - caché compartida sin lock;
  - presupuesto de EDGAR gastado en cola, con resultados que dependían de la carga;
  - valor en libros del corte;
  - anexo con códigos;
  - carreras de clase y de sesión;
  - PDF fuera del semáforo.
  El 8 (trimestral parcial en caché) se acepta y se declara. La medida A/B posterior no empeora: 7.8 frente a 7.5 s, 12 de 12 con EDGAR.
- **Suite:** "1 failed, 3930 passed, 1 skipped". Lo que falla son las muestras forzadas del contrato, que van con los golden.
- **Mapa:**
  - "producción atiende en serie" y "BRK-B en base anual" y su P/E, ✅;
  - "Yahoo 401 en Render", resuelta por diseño;
  - "apaga sin tráfico" y "Yahoo distinto en Render", ⏸ (D6 y deploy).
- **Límite anotado para la fase 7 o el usuario:** el beneficio GAAP de BRK-B incluye las ganancias no realizadas de su cartera (ASC 321). Definir el beneficio operativo de aseguradoras y conglomerados es una decisión de método.
- **Siguiente:** fase 7. Hecha la revisión mensual de parámetros (`7bbfc6e`); el estudio de calibración, con hipótesis fijadas antes de correrlo (`3ef8c8f`).

### #35 · 2026-10-17 · operador · Fase 7 (revisión de parámetros y estudio de calibración, bajo la delegación del registro #29)
- **Revisión mensual de parámetros** (`7bbfc6e` y revisión):
  - `config/review.toml` con fuente, fecha del dato, consulta y cadencia de cada parámetro de mercado;
  - `tests/revision_parametros.py` con cadencias mensuales de calendario y aviso de dato antiguo;
  - hoy: 7 vigentes, 1 con dato antiguo (EV/EBITDA del S&P 500, 1T-2025) y 2 sin fuente (medianas y umbrales sectoriales, que esperan los datos de Damodaran).
- **Estudio de calibración** (F7_CALIBRACION, versión 2):
  - hipótesis y regla fijadas en `3ef8c8f` antes de correrlo;
  - 965 análisis point-in-time del motor real, en replay (98 empresas fuera del panel, ejercicios 2012–2021, al día siguiente de cada 10-K).

  La **revisión independiente** encontró una fuga de información futura: los precios venían ajustados por splits posteriores (WMT a un tercio, GE ×4.8; 218 observaciones). También encontró ejercicios mal construidos (BMY, CVS, 52/53 semanas). Con ambos corregidos:
  - **H2** (calidad "excelente" → menor caída a 3 años) sigue validada con la regla prerregistrada, +3.8 pp, pero **no es robusta**: con bootstrap empresa × año y neta de sector × año, el IC incluye 0;
  - **H3a** (precio "muy exigente" → −9 pp a 1 año) pasa de validada a **no concluyente**;
  - **H1 y H3b**, no concluyentes.

  Conclusión: ninguna escala anticipa de forma robusta la cotización, y la app no lo afirma (comprobado). No cambia ningún umbral. La versión 1 se conserva junto a los datos.
- **Bandas de REIT y utilities** (F4_PARADA §5):
  - **bien centradas:** las 3 de utilities y el P/FFO de los REIT; "PROVISIONAL" fuera de sus comentarios, sin cambiar valores;
  - **en el límite:** la deuda neta/EBITDA de los REIT, que sigue PROVISIONAL;
  - **satura:** FFO/patrimonio contable (82% en el tramo alto). Es decisión del usuario.
- **Decisiones abiertas para el usuario:**
  - REIT FFO/patrimonio: retirar, sustituir por FFO/activos (recomendado) o dejar;
  - repetir el estudio con una muestra mayor, con empresas desaparecidas y la prima de cada fecha (necesita la descarga de Damodaran);
  - beneficio operativo de aseguradoras (BRK-B, del registro #34).
- **Suite:** "1 failed, 3931 passed, 1 skipped". Lo que falla son las muestras forzadas del contrato, que van con los golden.
- **Decisión del usuario (2026-10-17):** REIT FFO/patrimonio → **FFO/activos totales**, recalibrado con la muestra de la fase 7.
  - Tramos por quintiles: 9 / 7 / 6 / 5%, con los mismos puntos.
  - Panel:
    - O, calidad 70 "sólida" → 59 "media" (FFO/activos 5.0%);
    - PLD, 85 "excelente" → 79 "sólida", en la frontera;
    - AMT, 79 → 75.
  - Golden de los tres pendientes de regenerar (F7_CALIBRACION §6).

### #36 · 2026-10-17 · operador · Decisiones de método bajo la delegación (registro #29): aseguradoras y REIT
- **Beneficio operativo de aseguradoras y conglomerados** (abierto desde el #34). El operador lo decide como analista:
  - se valoran sobre el beneficio **sin las ganancias de su cartera**, realizadas y no realizadas (ASC 321), que es la convención del mercado y la del propio Berkshire;
  - la rentabilidad (ROE, ROA, margen) **no** las excluye: su patrimonio ya incluye la cartera a valor razonable, e invertir el float es parte del negocio.

  Implementación:
  - `sec_edgar.investment_gains` (GainLossOnInvestments, RealizedInvestmentGainsLosses…);
  - `edgar_primary`: las ganancias de doce meses del corte, en aseguradoras y conglomerados; fuera los corredores; en IFRS se declara;
  - `normalize`: ítem "estructural", entero, al tipo efectivo; sin doble conteo con las ganancias de valores de Yahoo, con el total de partidas inusuales ni con los picos inferidos;
  - `operating_pe`: el P/E y el E/P del análisis pasan a ser capitalización / beneficio operativo en todos sus consumidores (tabla "P/E operativo", portada, alertas, score), con el reportado aparte. Con un beneficio operativo ≤ 0 no hay P/E.

  Resultados:
  - **BRK-B:** beneficio operativo de doce meses 43.4 mil millones (Berkshire publica 44–47); P/E 13.2 → 26.8; precio 42 → 35, sigue "exigente"; calidad sin cambio (71);
  - **PGR:** P/E 11.1 → 11.4, sin cambio de nivel.
- **REIT, FFO/activos** (decisión del usuario, `21e8341`): verificado con el estudio de bandas, bien centrada (19 / 25 / 18 / 21 / 17%).
  - FFO/patrimonio se muestra como dato informativo, sin puntuar.
  - La cifra va con dos decimales (O: 4.98%, justo bajo el corte del 5%).
- **Revisión independiente** de los dos cambios: 11 hallazgos, arreglados en el commit siguiente:
  - el P/E con beneficio operativo negativo o con pérdida reportada;
  - el doble conteo con los picos inferidos;
  - el total de partidas inusuales que borraba los deterioros;
  - el P/E mostrado distinto del que puntuaba;
  - textos que llamaban "no recurrente" a la cartera;
  - el alcance (corredores) y el tipo fiscal;
  - el estudio de bandas roto;
  - "(fase 7)" en un texto;
  - FFO/patrimonio, que no se mostraba.

  Queda de diseño: el P/B justificado de las financieras usa el ROE con las ganancias.
- **Panel:** 0 cambios de nivel frente al cierre de la fase 7, salvo los ya registrados de O y PLD.
- **Suite:** "1 failed, 3936 passed, 1 skipped". Lo que falla son las muestras forzadas del contrato, que van con los golden.
- **Bloqueado para el usuario** (reglas suyas vigentes; la delegación no las levanta):
  - regenerar los golden (el clasificador de permisos lo denegó);
  - `SEC_EDGAR_USER_AGENT` en Render;
  - "ok, pushea" y deploy;
  - el permiso para descargar los datos de Damodaran (medianas sectoriales y prima histórica).

### #37 · 2026-10-17 · operador · Golden regenerados con la aprobación del usuario
- **Aprobación del usuario:** "Apruebo regenerar los golden del panel y local y las muestras forzadas del contrato, con el diff explicado causa por causa."
- **Diff causa por causa** en [`GOLDEN_DIFF_F3_F7.md`](GOLDEN_DIFF_F3_F7.md):
  - se pasó el motor por los 85 commits que tocan código desde los golden anteriores (`d0ab47c`), validado con 0 diferencias en el commit base;
  - 51 commits cambian la salida, todos con su causa y decisión registradas;
  - ningún cambio de veredicto queda sin causa.
- **Regenerados:** golden de panel (37) y local (6), y las 4 muestras forzadas del contrato. Coinciden con la salida de `354e7eb`.
- **Suite completa, con regresión:** "4113 passed, 1 skipped", 0 fallos. Es la primera vez desde la fase 3.
- **Pendiente del usuario:**
  - `SEC_EDGAR_USER_AGENT` en Render;
  - "ok, pushea" y deploy;
  - permiso para descargar los datos de Damodaran.

### #38 · 2026-10-17 · operador · Push de F3–F7 a `main` y deploy
- **Aprobación del usuario:** "Ya puse SEC_EDGAR_USER_AGENT en Render. ok, pushea y despliega."
- **Fusión:** fast-forward de `main` hasta `fiabilidad/f7-calibracion` (`134b6b6`, 119 commits).
- **Frontend:** `frontend/out` recompilado con Turbopack (`5216bc6`). Lleva las pestañas de contexto de mercado y las lecturas de calidad; el sello del contrato coincide y no queda ningún archivo sin seguimiento.
- **Suite en `main`:** "4113 passed, 1 skipped".
- **Push:** `01336e2..5216bc6` a las 14:49 de Nueva York.
- **Comprobación del checkout limpio** (`git archive`, sin variables de entorno):
  - pasan todas las comprobaciones de `build.sh` (recursos, contrato);
  - la app arranca y `/api/health` y `/` dan 200.
- **Estado del deploy:** a los 45 minutos producción seguía en `01336e2`. Render no lo había desplegado, o falló sin que se vea desde fuera. Se hace un segundo push (este registro) para reintentar el deploy automático. La causa tiene que mirarse en el panel de Render, que solo puede abrir el usuario.
- **Verificación en producción pendiente** del deploy:
  - BRK-B, AAPL y O con concurrencia ≤ 3;
  - `data_provenance.edgar.status`;
  - P/E operativo de BRK-B;
  - PDF;
  - latencias.
