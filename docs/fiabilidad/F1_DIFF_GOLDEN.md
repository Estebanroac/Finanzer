# Fase 1 — diff de golden explicado causa por causa

Se rellena en T3/T4, un apartado por commit. Los golden **no** se regeneran hasta el punto de parada 2 (T5), con la
aprobación del usuario. Mientras tanto la regresión de golden falla a propósito; el resto de la suite, en verde.

Comandos: `cd backend && ../.venv313/bin/python tests/diff_golden.py --env panel` y `... tests/diff_golden.py`
(juego `local`).

---

## T3.1 — Cobertura de intereses por el signo del EBIT y del resultado financiero

**Causa.** El estado de la cobertura se decidía con el signo del cociente. PLTR cobra más intereses de los que
paga (resultado financiero neto +77.5 M en el último trimestre, +266.4 M TTM; *Net Non Operating Interest Income
Expense* de los estados del plan B), Finnhub da una cobertura de −1.53 y el motor la leía como "EBIT negativo con
caja neta" con un EBIT de +2.63 B.

**Regla nueva** (`financial_ratios.interest_coverage_state`): con EBIT > 0 y cobertura negativa o ausente, el estado
es `sin_carga` si el resultado financiero neto es ≥ 0 **en el TTM y en cada uno de sus 4 trimestres** (un trimestre
atípico no basta: NFLX 2026-03 trae +2.85 B de ingresos financieros y su TTM sale +2.14 B, con los otros tres
trimestres y el anual negativos). Sin esa fila en los estados, se infiere del signo de la cobertura y queda en
`data_provenance` como inferido. No se infirió en ningún ticker del panel ni de `local`.

### Cambios de estado
| Juego | Ticker | Antes | Después |
|---|---|---|---|
| panel | PLTR | `no_significativo` | `sin_carga` |
| resto (29 + 6) | — | sin cambio | sin cambio |

### PLTR (panel): Kd, WACC, DCF y nivel de precio
| Magnitud | Antes | Después | Por qué |
|---|---|---|---|
| Rating sintético | BBB (regla M, tramo de caja neta) | AAA (mejor tramo) | sin carga financiera neta |
| Kd | 6.40% | 5.69% | Rf 5.29% + spread AAA |
| Kd después de impuestos | 5.76% | 5.12% | |
| Peso de la deuda | 0.04% | 0.04% | caja neta: deuda casi nula frente a la capitalización |
| WACC | 11.25181% | 11.25153% | −0.0003 pp: el peso de la deuda es casi cero |
| DCF, valor razonable | 44.22 | 44.22 | sin cambio al céntimo |
| DCF, upside | −78.0% | −78.0% | sin cambio |
| Rejilla de sensibilidad | | ±0.01 en 2 celdas; media 43.8875 → 43.8885 | el WACC base |
| Solidez financiera, fila de cobertura | 0 (no significativa) | +3 (tramo superior) | |
| Solidez financiera, categoría | 20/20 | 20/20 | ya estaba en el tope: la puntuación total no cambia |
| Veredicto / nivel de precio | Calidad excelente · precio exigente | igual | sin cambio |

El nivel de precio **no** cambia.

### Texto (web y PDF de PLTR)
- Resumen, solvencia, lectura y gauge: "con EBIT negativo y caja neta, la cobertura de intereses no es
  significativa: los intereses se pagan con caja" → "sin carga financiera neta: los ingresos financieros cubren los
  gastos financieros y el resultado operativo es positivo".
- Fila de cobertura en solvencia: "—" / "No significativa" → "Sin carga" / "Sin carga financiera".
- Nota del WACC: "Kd 6.40% … BBB … regla M: EBIT < 0 con caja neta" → "Kd 5.69% … AAA … sin carga financiera neta
  (EBIT > 0 e ingresos financieros netos) -> mejor tramo".
- `data_validation` y `data_provenance` de la cobertura: el motivo pasa de "EBIT < 0 con caja neta" a "EBIT > 0 y
  los ingresos financieros superan a los gastos".
- `confidence.dimensions.coverage.coverage` 0.944 → 0.947 y `score_coverage.solidez` 2 → 3 evaluadas: la cobertura
  vuelve a contar como componente evaluado.

### Cambios aditivos en el resto (36 tickers entre panel y `local`)
- `key_metrics.net_interest_income` (nuevo campo; `null` donde falta un trimestre, p. ej. JPM).
- `data_provenance.fields.netInterestIncome` (TTM, suma de 4 trimestres) o
  `data_provenance.ttm.source_fields.netInterestIncome` (por qué no hay TTM).
- `data_provenance.ttm.ttm_fields`: entra `netInterestIncome` y desplaza el orden alfabético de la lista.

Ningún otro campo cambia fuera de PLTR (comprobado filtrando el diff por estos tres campos: salida vacía).

---

## T3.2 — Inglés en la capa de presentación ("STRONG", "N/A")

**Causa.** El display y el PDF pintaban tal cual el código del motor para la salud financiera bancaria
(`STRONG`/`GOOD`/`NEUTRAL`/`WEAK`) y "N/A" para lo que falta. El motor conserva sus códigos; la presentación los
traduce (`display.FIN_HEALTH_LEVEL_ES`, `NO_DATA = "—"`, `_es_value`), igual que las filas "no significativa".
También en los formateadores de la web (`frontend/src/lib/api.ts`; `frontend/out` se recompila en T6).

**Cambios** (solo texto; ninguna cifra, puntuación ni estado):
| Juego | Tickers | Cambio |
|---|---|---|
| panel | JPM, BAC, PGR, BRK-B | subtítulo de la tarjeta "STRONG" → "Sólida"; resumen "(STRONG)" → "(sólida)" |
| panel | JPM, BAC, PGR, BRK-B, DOW, RIVN, SNOW | valores "N/A" → "—" en rentabilidad, valoración, KPI de portada y tarjetas |
| local | JPM | "STRONG" → "Sólida"/"(sólida)"; un "N/A" → "—" |
| local | SNOW | "N/A" → "—" (portada y valoración) |

Lo único que queda en inglés tras T3.2 son los códigos de arquetipo de "Clasificación (detalle técnico)": van al
anexo técnico en T3.3 (D1).

---

## T3.3 — D1: anexo técnico "Detalle técnico para auditoría"

**Causa.** Los códigos internos (arquetipo `MATURE`/`CYCLICAL`…, reglas `por_defecto`/`industria_*`, reglas de
validación `crecimiento_incoherente`…) salían en las páginas de lectura del PDF ("Clasificación (detalle
técnico)…", columna MOTIVO de la tabla de confianza) y en el desplegable "Detalle técnico" de la web.

**Cambio.**
- `display.annex` = {title, items}: la clasificación técnica y los motivos técnicos de cada dimensión de la
  confianza que no es "alta". El PDF lo imprime **al final**, tras el aviso legal; la web no lo pinta.
- Tabla "Confianza del veredicto" (PDF y pestaña de valoración de la web): el motivo pasa a lenguaje llano con la
  misma tabla de `plain_language` que ya usaba la portada. "sin incidencias" → "Sin incidencias.".
- Se retiran del contrato de la web `cover.classification_detail` y `confidence.reasons[].detail`; se quita el
  desplegable "Detalle técnico" de `StockHeader.tsx` (`frontend/out` se recompila en T6).
- Ninguna cifra, puntuación ni estado cambia.

**Cambios en los golden** (todos los tickers de ambos juegos):
| Campo | Cambio |
|---|---|
| `display.annex` | nuevo: título + 1 ítem de clasificación + 1 por dimensión de confianza no "alta" |
| `display.cover.classification_detail` | retirado (va al anexo) |
| `display.confidence.reasons[].detail` | retirado (va al anexo) |
| `display.confidence.dimensions[].text` | técnico → llano (convergencia conserva la lista de métodos y su signo) |
| PDF | la línea "Clasificación (detalle técnico)…" desaparece de la sección 01; el anexo aparece al final |

**Páginas.** El anexo cabe en la última página salvo en 10 del panel, que ganan una (AAPL 9→10, PLD 6→7, AMT 6→7,
CAT 8→9, MU 9→10, PLTR 8→9, NVDA 8→9, SNOW 9→10, TSM 9→10, ASML 9→10) y SNOW de `local` (9→10). Tres pierden una
(NEE 8→7, DUK 8→7, RIVN 9→8): la tabla de confianza en llano es más corta que el texto técnico. A revisar en el
PNG de T4.

---

## T3.4 — Cota del crecimiento de ciclo medio y base "(3 años)" en CYCLICAL

**Causa.** En una CYCLICAL el crecimiento que puntúa es el promedio interanual de ciclo medio, acotado a
[−5%, +10%] (`valuation.archetypes.cyclical_growth_bounds`). En la cota, el texto lo presentaba como dato medido
("los ingresos se contraen un 5.0% anual de ciclo medio"), y el gráfico de comparación rotulaba la cifra
"(3 años)" (catálogo #20).

**Cambio.** `read_growth(cycle=True)` añade "(acotado al mínimo / máximo que admite el modelo)" cuando la cifra
coincide con la cota de config; la comparación con el sector rotula "(ciclo medio)" en CYCLICAL. La web lee el
mismo texto. Ninguna cifra cambia.

| Juego | Ticker | Cota | Textos que cambian |
|---|---|---|---|
| panel | XOM | −5% (ingresos y BPA) | lecturas, intro y filas de crecimiento, resumen ejecutivo; etiqueta de comparación |
| panel | DOW | −5% (ingresos y BPA) | ídem |
| panel | MU | +10% (ingresos y BPA) | ídem |
| panel | ASML | +10% (ingresos y BPA) | ídem |
| panel | FCX | −5% (BPA) | lectura, intro y fila del BPA; etiqueta de comparación |
| local | FCX | −5% (BPA) | ídem |

---

## T3.6 — Resto de hallazgos del guardián (tres causas, tres commits)

### a) V: "múltiplos frente al sector" con referencia de mercado (catálogo #6) — `90ab32a`
La tabla de confianza nombraba el método con el nombre interno del motor. Con `benchmark.profile = market`, la
presentación lo llama "múltiplos frente al mercado". Cambia `display.confidence.dimensions[0].text` en V (panel y
`local`) y su línea del PDF. Solo texto.

### b) BRK-B: "TTM" con base anual (catálogo #20) — `f6f0b36`
Sin cuatro trimestres consecutivos la base es el último ejercicio (`data_provenance.ttm.basis = anual`). La etiqueta
del P/E pasa a "P/E (último ejercicio)" y la metodología del PDF a "ratios del último ejercicio". Campos nuevos en
todos los tickers (aditivos): `display.pe_label` y `display.methodology.ratios_text`; en BRK-B cambian
`sections.valuation.rows[0].label` y `charts.valuation.multiples[0].label`. Solo texto.

### c) AMT: caída del FFO por acción atribuida a la emisión con las acciones planas
El texto decía "la emisión de acciones crece más deprisa que los fondos de operación, y diluye al accionista" con
las acciones a +0.05% anual en 3 años. La emisión solo se cita si las acciones crecen al menos el umbral con el que
el motor pasa a medir por acción (`thresholds.growth.per_share_min_shares_cagr`, 2%); si no, "son los propios
fondos de operación los que caen (las acciones apenas varían: +0.05% anual)". Cambian `alerts.warnings[0].detail`
y su copia en `display.sections.alerts` de AMT. O y PLD sin cambio. Solo texto.

**Estado tras T3:** guardián con 0 fallos y 0 xfail en los 30 del panel y los 6 de `local`; invariantes del panel
sin xfail. Lo único rojo de la suite es la comparación con los golden (pendiente de aprobación en T5).

---

## T4 — Maquetación del PDF (tres commits; solo el texto del PDF, ningún campo del análisis)

### a) Página 2 — `7f32070`
**Causa.** Alturas fijas (27/46/27%) con la composición centrada (hueco encima) y la lectura alineada abajo: cuando
la lectura no cabía en su 27%, crecía hacia arriba y se montaba sobre la composición (32 de 36 PDF). La composición
era 24 pt más estrecha que el resto y su tabla de barras 12 pt más ancha que su celda (cifras sobre el borde).
**Cambio.** Flujo natural a ancho completo; rellenos de cards, composición y lectura ajustados (sin quitar texto ni
cambiar el cuerpo de letra de las cifras); la lectura en `KeepInFrame(shrink)` con el alto que queda, como la
portada. Página 2 completa en 30 + 6 (test).

### b) Comprobación geométrica y celdas largas — `e3161d2`
`tests/pdf_geometry.py` (pypdfium2): texto dentro del área útil y sin solapes. Detecta en páginas sintéticas y en
el código anterior a T4 (33 de 36 PDF). Encontró dos defectos más, arreglados en `data_table`: "No aplica a …" sobre
la columna de brecha (RIVN, SNOW) y el criterio de Piotroski "Calidad del beneficio (flujo operativo frente a
beneficio neto)" sobre su detalle (24 PDF). La celda que no cabe se parte en líneas dentro de su columna. En el texto
extraído del PDF cambian los saltos de línea de esas celdas.

### c) Anexo sin partir — `c369575`
`KeepTogether` del anexo técnico (AAPL y SNOW dejaban el título al pie de una página).

### Páginas (golden → ahora, T3.3 + T4)
15 PDF sin cambio. Cambian: AAPL 9→10, JPM 7→8, BAC 7→8, PGR 7→8, BRK-B 7→8, PLD 6→7, AMT 6→7, NEE 8→7, XOM 8→9,
FCX 8→9, CAT 8→9, MU 9→10, DOW 8→9, PLTR 8→9, NVDA 8→9, SNOW 9→10, TSM 9→10, ASML 9→10 (panel); JPM 7→8, FCX 8→9,
SNOW 9→10 (`local`). Causas: el anexo al final (T3.3) y las filas con lectura partida en dos líneas (T4 b). Ninguna
última página queda con un fragmento suelto del anexo.

---

# Tras la parada 2 (golden regenerados en `da2b33e`): cuatro arreglos para el punto de parada 3

Los golden de estos cuatro arreglos **no** se regeneran sin aprobación.

## P3.1 — Tarjetas "No aplica" sin cifra; regla #10 del guardián

**Por qué no lo detectó el guardián.** La regla #10 ("no aplica" con cifra) estaba en el diseño y en el docstring
del guardián, pero no se implementó en `_structural`; y la red de seguridad no la cubría porque las tarjetas
(`cover.kpis`, `summary.cards`) no declaran afirmaciones y "No aplica" no es una palabra de afirmación.
**Cambio.** Regla `no_aplica_con_cifra` sobre todas las tarjetas de portada y resumen (caso en
`test_guardian_detecta.py`); `_mkcard` con estado `no_aplica` pinta "—", sin unidad, y el motivo en la línea de
referencia ("No aplica a REIT", "No aplica a empresas en crecimiento sin beneficio").

| Juego | Tickers | Campos |
|---|---|---|
| panel | O, PLD, AMT (REIT); RIVN, SNOW (pre-beneficio) | `display.summary.cards[1..2]` (margen neto y ROE): `value` cifra → "—", `unit` "%" → "", `bench` "" → motivo |
| local | O, SNOW | ídem |

Las tarjetas de portada (`cover.kpis`) ya cumplían. Fuera del alcance (anotado para decidir): las **filas de tabla**
con "No aplica" conservan la cifra (p. ej. JPM P/E 14.27x), decisión de la etapa 9b protegida por
`test_bank_pdf_never_reads_pe_or_fcf_as_primary`.

## P3.2 — Rango de 52 semanas con la cotización actual

**Causa.** El máximo de 52 semanas de la fuente (176.41) no incluía la cotización del día de XOM (177.06): "cotiza
en el 101% del rango". **Cambio.** En `main.py`, máximo = max(máximo, precio) y mínimo = min(mínimo, precio) sobre
`financials`, de modo que `key_metrics`, `price_history` y el display leen el mismo rango; si se amplía, queda en
`data_provenance` como derivado. Guardián: la posición (dato y cifra citada) entre 0 y 100.

| Juego | Ticker | Campos |
|---|---|---|
| panel | XOM | `key_metrics.price_52w_high` y `price_history.52w_high` 176.41 → 177.06; `data_provenance.fields.key_metrics.price_52w_high` (nuevo); posición 101% → 100% en la lectura, el rango de la sección 04, el resumen ejecutivo y la tarjeta de precio ("+0.4%" → "0.0%" desde el máximo) |

Ningún otro ticker del panel ni de `local` tenía el precio fuera de su rango.

## P3.3 — Ningún múltiplo negativo como nivel en una tarjeta (caja neta en la portada)

**Causa.** La portada pintaba "Deuda neta/EBITDA −3.45x" (PLTR) como si fuera un nivel: con caja neta el ratio sale
negativo y no se sitúa en la escala. **Cambio.** Con deuda neta < 0, la tarjeta pasa a "Caja neta" con su importe
(|deuda neta|), la misma lectura que la fila de Solidez; con EBITDA negativo y deuda neta, "—". Guardián: regla
`ratio_negativo_en_tarjeta` sobre todas las tarjetas de portada y resumen (con caso en `test_guardian_detecta.py`).
Tooltip `net_cash` en la web.

| Juego | Ticker | `display.cover.kpis[6]` (key · label · value) |
|---|---|---|
| panel | PLTR | `net_debt_to_ebitda` · "Deuda neta/EBITDA" · "−3.45x" → `net_cash` · "Caja neta" · "$9.20B" |
| panel | TSM | "−0.78x" → "$79.47B" |
| panel | CRWD | "−19.67x" → "$4.19B" |
| panel | MSFT | "−0.10x" → "$19.82B" |
| panel | MU, NVDA, ASML | ídem (−0.29x, −0.12x, −0.40x → su caja neta) |

La fila de Solidez (tabla) conserva "−3.45x" con la lectura "Caja neta"; el arreglo pedido es para las tarjetas.

## P3.4 — Escala mínima del contenido encogido (portada y página 2)

**Cambio.** La portada y la página 2 declaran su escala efectiva en las palabras clave del PDF
(`escala_portada=…`, `escala_pagina2=…`; 1.000 si cabe sin encoger) y la comprobación geométrica falla por debajo
de 0.85 (con caso sintético). Sin cambio en el texto de ningún PDF ni en el análisis (los golden de texto no lo ven).

**Escalas actuales** (30 del panel + 6 de `local`):
| Bloque | Mínima | Encogidos |
|---|---|---|
| Portada | **0.936** (TSM) | 9: TSM 0.936, AMZN 0.957, BRK-B 0.964, NVO 0.968, NVDA 0.973, ASML 0.986, MU 0.991, PLTR 0.991, SNOW (`local`) 0.991 |
| Página 2 | **1.000** | ninguno |

## P3.5 — (hallazgo de T6) Web: la cobertura "sin carga" se leía como "No significativo"

**Causa.** En T3.1 la fila y el medidor de la cobertura con estado `sin_carga` quedaron con `state =
no_significativo`; el PDF pinta la lectura, pero la web pinta el estado cuando no es `con_dato`: "Cobertura de
intereses · No significativo" junto a "Sin carga financiera neta". **Cambio.** Fila `con_dato` con valor "Sin carga"
y lectura "Sin carga financiera"; medidor `con_dato` sin escala (`no_burden`), que la web ya pinta como lectura +
texto. El invariante de los medidores reconoce `no_burden`.

| Juego | Ticker | Campos |
|---|---|---|
| panel | PLTR | `display.sections.solvency.rows[6].state` no_significativo → con_dato; `display.charts.solvency.gauges[1]`: state no_significativo → con_dato, + `reading`, `tone`, `value_txt`, `no_burden` |

Sin cambio en el texto del PDF.

## P3.6 — BCS en el panel (caso de prueba) — `3f2138b`, `359f06a`

Capturado con `--env panel --render-sim` el 2026-10-15 a las 10:11 (intradía; 401, 401, plan B; Finnhub activo).
Grupo "Revisión externa". Su golden es **nuevo** y queda pendiente de la aprobación de la parada 3 (hoy la
regresión falla con "falta golden"). Con BCS el guardián marcó "Gran descuento" (pill acortada) sin afirmación
declarada: se declara (`359f06a`, sin cambio de salida).

**Diagnóstico del 50.46% (confirmado, sin tocar el origen: fase 2).** El yield no viene de Yahoo sino de Finnhub
`/stock/metric`, que para BCS devuelve la línea de Londres de la acción **ordinaria en peniques**
(`dividendIndicatedAnnual` = 11.5, `52WeekHigh` = 538.3). `financial_ratios.dividend_yield` divide ese 11.5 entre
el **precio del ADR en dólares** (22.87): 0.503. Tres errores a la vez: peniques frente a libras (×100), sin factor
ADR (÷4.154; oficial 4) y libras frente a dólares (÷1.342). La hipótesis del planificador (peniques y sin factor
ADR) es correcta; además falta la conversión de moneda: el error total es ≈ 18× (no 25×). Corregido, ≈ 2.8%
(11.5 p × 4.154 × 1.342 / $22.87). Lo pagado según los estados (dividendos / capitalización) es 3.9%, que puede
incluir cupones AT1 (mapa, fase 2).

**El mismo defecto en el panel** (lo destapó la identidad): TSM 6.05% (26 TWD por acción ordinaria sobre $430 del
ADR; real ≈ 0.95%), NVO 30.69% (11.7 DKK sobre $38; real ≈ 4.8%, que es lo pagado), NVDA 0.45%
(`dividendIndicatedAnnual` = 1 de Finnhub; el dividendo es $0.04: ≈ 0.02%).

## P3.7 — Guardián de identidades y dividend yield "sin dato" si no cuadra

**Motor** (`main.py`, `validate.dividend_yield_identity`): el yield se compara con lo que la empresa paga
(dividendos pagados del último ejercicio / capitalización; sin ellos, payout × E/P). Si lo supera más de
`dividend_identity_max_ratio` veces, sale **sin dato** con aviso `identidad_dividendo` en `data_validation`, no
puntúa, y el shareholder yield también queda sin dato (antes habría sumado 0 y quedado igual a las recompras).
Las filas de la sección 04 se conservan con "—", "Sin dato" y el motivo.

**Guardián** (`tests/guardian.py: identities`, datos frente a datos): yield frente a payout × E/P (payout / P/FFO
en REIT, cuyo payout es sobre el FFO), por una vía distinta de la del motor; shareholder yield = dividendo +
recompras (y sin dato si el dividendo se invalidó); el yield invalidado no aparece en el score. Casos en
`test_guardian_detecta.py`. En rojo antes del arreglo exactamente en BCS, TSM, NVO y NVDA.

**Tolerancia: 2.0, solo por arriba.** En el panel, los yields correctos están entre 0.82 y 1.20 veces lo pagado
(desfase entre el dividendo indicado y el último ejercicio pagado, subidas, recompras); los erróneos, entre 3.6 y
12.9 veces (unidades ×100, factor ADR ×4–5, moneda local ×6–32). 2.0 deja margen a ambos lados (1.7× sobre el
mayor correcto, 1.8× bajo el menor erróneo); subir el dividendo más del doble en un año es excepcional y, si pasa,
el coste es un "sin dato" con aviso, no una cifra falsa. Solo por arriba porque un dividendo extraordinario deja el
yield indicado por debajo de lo pagado con razón (PGR: 0.19% frente a 6.6%).

| Juego | Ticker | Campos |
|---|---|---|
| panel | TSM, NVO, NVDA | `key_metrics.dividend_yield` y `shareholder_yield` → null; `data_validation` + `identidad_dividendo`; filas "Dividend yield" y "Shareholder yield" de la sección 04: valor "—", "Sin dato", motivo |
| panel | BCS | ídem (golden nuevo) |

Ningún otro ticker de panel ni de `local` cambia.

## P3.8 — "Dividendo sostenible" de la salud bancaria evalúa y cita el payout

**Causa.** El componente se activaba con el dividend yield y lo citaba ("Dividendo sostenible (50.46%)" en BCS),
aunque lo que evalúa es el payout. **Cambio.** Se activa con el payout y lo cita ("Dividendo sostenible (payout
27%)", "Payout alto (payout 70% > 60%)"); sin payout no se evalúa. Mismos puntos en todos los bancos del panel.

| Juego | Ticker | Campos |
|---|---|---|
| panel | JPM, BAC | `financial_health.details[3].detail` y su copia en `score.breakdown.Solidez Financiera`: "(1.97%)" / "(2.49%)" → "(payout 27%)" / "(payout 32%)" |
| panel | PGR | "Payout ratio alto (70% > 60%)" → "Payout alto (payout 70% > 60%)" |
| local | JPM | "(1.98%)" → "(payout 27%)" |
| panel | BCS | (golden nuevo) "Dividendo sostenible (payout 28%)" en lugar de "(50.46%)" |
