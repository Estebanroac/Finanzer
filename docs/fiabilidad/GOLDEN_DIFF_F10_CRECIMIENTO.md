# GOLDEN_DIFF_F10_CRECIMIENTO: crecimiento desde una base anómala

Rama `fiabilidad/f10-crecimiento`, que sale de `rediseno/v4-f8` en 8df00bdb. Es el bloqueante del escaneo de control
del 29-oct (`docs/modelo/CONTROL_F10_2026-10-29.md`): 46 empresas puntuaban el «Crecimiento del BPA a 3 años» desde un
año valle. Ejemplos: NVDA +198 %, VRT +282 %, PODD +245 %.

## La regla (`historical_metrics.robust_growth`)

Todo crecimiento a 3 años pasa por `growth_rate`, y cada serie publica `robust` en `growth_basis`.

1. **Sin año base anómalo:** el CAGR de siempre, robusto.
2. **Con año base anómalo:** la regresión log-lineal. Es robusta si tiene ejercicios fuera de la ventana con los que
   diluir el año anómalo (F10 · N3).
3. **Si no lo es, la serie larga de EDGAR.** Necesita al menos `thresholds.growth.long_years` = 6 ejercicios contiguos
   que lleguen al último de la ventana, todos positivos. La regresión log-lineal se hace sobre los 6 últimos
   (`method: "log_lineal_edgar"`), con su fuente, su ventana y su nota.
4. **Si tampoco, no significativo** («no significativo: año base anómalo (…) y sin serie larga robusta: <por qué>»).
   No puntúa, no resta cobertura y su línea lo dice (B1: ningún vacío sin motivo). Nunca se da una cifra que dependa
   del año anómalo.

Dónde se aplica:

| Serie | Serie larga | Puntúa |
|---|---|---|
| Ingresos | `revenue` de EDGAR | Crecimiento |
| Ingresos por acción | — | Crecimiento |
| BPA | `net_income` de EDGAR, solo con las acciones estables (`per_share_basis` = agregado). Si las acciones cambian, el BPA antiguo de EDGAR no es comparable y el crecimiento queda no significativo | Crecimiento y PEG |
| FCF y FCF − SBC | OCF − capex de EDGAR | Crecimiento |
| FCF por acción (REIT) | — | Crecimiento |
| Valor en libros (banco, aseguradora) | — (`strict_cagr`) | Calidad |
| FFO por acción (REIT) | — (`strict_cagr`) | Crecimiento (retorno total) |
| Margen de intereses (banco) | — (`strict_cagr`) | Solo lectura: fila «No significativo» con su motivo |
| Ingresos y por acción para clasificar (`classify.py`, `cyclicality.growth_profitable_measures`) | `revenue` de EDGAR, o la propia historia | El tipo |

Correcciones al informe anterior:

- `strict_cagr` sí pasaba por `growth_rate` y aplicaba la regresión con base anómala; lo que se perdía era el `robust`.
- La tabla del control decía «ninguna» para el valor en libros, el FFO y el margen de intereses: no es exacto.

### La clasificación: un criterio no significativo no cuenta (PM, 29-oct)

Un crecimiento no significativo es «desconocido», no «sin crecimiento». No cuenta ni a favor ni en contra, y el tipo se
decide con el resto de la evidencia:

- **Pre-beneficio:** decide la falta de beneficio. El motivo lo dice: «el crecimiento de sus ingresos a 3 años no es
  significativo (parte de un año base anómalo) y no cuenta ni a favor ni en contra».
- **Crecimiento rentable:** deciden la tasa a 5 años (si es significativa), el beneficio y el margen.
- **Nota de crecimiento estructural de una cíclica:** sin una tasa a 3 años significativa no se afirma que crezca.
- **Una tasa no significativa de la historia de EDGAR** es un resultado, no un vacío: no se sustituye por la de Yahoo.

### La cota (PM, 29-oct)

Una tasa desde una base anómala baja sobrestima el crecimiento: es una **cota superior** (desde una base anómala alta
sería inferior; el detector solo marca las bajas). `growth_rate` la expone (`bound`: valor y dirección) y
`historical_metrics.bound_decides` dice si decide el tramo. Una puntuación monótona en el crecimiento la usa **solo si
la cota ya decide el tramo**. Entonces puntúa y lo declara («≤ x» y el motivo). Si no lo decide, sigue no significativa.

| Consumidor | ¿Admite la cota? | Qué puede decidir una cota superior del crecimiento |
|---|---|---|
| Regla de 40 (pre-beneficio) | Sí | Cota + margen FCF − SBC en el peor tramo (< 10). RIVN: ≤ −26, −4 |
| Crecimiento de ingresos, BPA y FCF (Crecimiento) | Sí | El peor tramo (crecimiento < 0; FCF < −5 %) |
| PEG (crecimiento rentable) | Sí | La cota del crecimiento da una cota inferior del PEG, que decide el tramo más caro (> 2,5) |
| Compresión del forward | Admitiría la cota, pero no cambia nada | La cota de la compresión también es superior: solo decide «sin compresión» (0), lo mismo que ya da hoy cuando no es significativa |
| Retorno total (REIT, madura de dividendo alto) | No | Suma el dividendo, y la cota del FFO por acción (`strict_cagr`) no se expone |

**Efecto medido** (reescaneo de las 158 con el código final): la cota decide en **0** empresas del universo, sin
ningún nivel que cambie. En el panel decide en una, RIVN: la regla de 40 queda en «≤ −26» y −4, y el precio vuelve de
65 «atractivo» a 50 «razonable», el de la base. Con una base baja, la cota del crecimiento es alta y casi nunca deja una
puntuación en su peor tramo: decide cuando el resto de la fórmula ya es muy malo (RIVN, margen FCF − SBC −73 %).

### Tiempo agotado de EDGAR y referencia de la industria (ENB, PM, 29-oct)

**Qué pasó.** Entre dos pasadas de minutos, la referencia del P/E de ENB pasó de 16,95x (la industria sin la empresa)
a 25,0x (la mediana de 4 pares). No fue un efecto de esta rama:

- En la pasada base, EDGAR no respondió a tiempo para ENB y AOS: presupuesto de 3 s por análisis
  (`data.edgar.budget_s`) y 2,5 s por petición.
- Sin las cifras de la empresa, N2 caía a la mediana de los pares, con el motivo «sin estados en SEC EDGAR», que no
  era el real.
- En la pasada de la rama le tocó a LNT. Es un 1–2 % de las empresas por pasada.

**El mismo fallo cambió un tipo.** En el escaneo completo del universo, RL pasó de cíclica a madura: EDGAR no
respondió a tiempo, y sin su historia no se mide la ciclicidad. Por eso el reintento va en el origen, en todo EDGAR, y
no solo en N2.

**Arreglo en origen.** Si EDGAR no respondió (no si el emisor no tiene estados):

1. `sec_edgar.collect` reintenta con su propio presupuesto (`data.edgar.retry_s` = 6 s) y se queda el mejor de los dos
   intentos (`retried`). Si una descarga del primer intento sigue en curso, la caché hace que se espere su resultado
   en vez de repetirla. Esto cubre la historia (el tipo), N2 y la verificación.
2. Si falla, N2 (`self_exclusion.figures_resilient`) usa las últimas cifras válidas de la caché. Son a una fecha fija,
   así que no caducan hasta que cambia el conjunto de Damodaran.
3. Si no hay ninguna, la referencia queda **degradada** y lo dice:
   - en la fila: «de sus pares del universo (referencia degradada: EDGAR no respondió)»;
   - en la nota de la referencia;
   - en la confianza: una incidencia de la calidad de fuente, que no pasa de «media».

Nunca un respaldo silencioso.

### Consumidores sin cifra inventada

- **DCF.** Con la tasa de la serie larga, la base del crecimiento lo dice: «crecimiento de ingresos por regresión
  log-lineal sobre los 6 últimos ejercicios de EDGAR (…)». Si los ingresos quedan no significativos, usa la misma salida
  que ya tenía sin crecimiento (el valor por defecto) y lo declara: «valor por defecto: el crecimiento de los ingresos
  es no significativo: …».
- **Retorno total de MATURE.** Con dividendo alto, toma los ingresos por acción. Si esa tasa queda no significativa,
  usa la agregada, que también pasa por la regla, y el rótulo lo dice («dividendo + ingresos»). Si las dos quedan no
  significativas, la fila es no significativa.
- **PEG.**
  - Con el BPA de la serie larga, es propio, y su rótulo dice «PEG (BPA, 6 ejercicios)».
  - Con el BPA no significativo, el PEG tampoco lo es, con el mismo motivo.
  - Un PEG de la fuente no se contrasta contra un BPA no significativo: queda no significativo.

## Cambios en los golden (panel y local)

**En todas las empresas:** `growth_basis.eps_cagr` nuevo (método, `robust`, ventana). También son nuevos `robust`,
`not_significant`, `source`, `window` y `years_used` en `revenue_cagr` y `fcf_cagr`, y `peg_basis.own` y
`peg_basis.years` en el PEG propio. Ninguno de estos campos cambia una cifra.

**Cambian cifra o veredicto:** 6 del panel y 1 del local.

| Empresa | Qué cambia | Calidad | Precio |
|---|---|---|---|
| NVDA | Ingresos 101,4 % → **69,0 %** (EDGAR, 6 ejercicios FY2021–FY2026). BPA 198,0 % → **101,7 %** (beneficio neto de EDGAR, con las acciones estables). FCF 186,2 % → **no significativo**: EDGAR solo tiene 5 ejercicios contiguos de FCF. El PEG pasa de no significativo (N3) a **0,27x**, propio, y el bloque de múltiplos de +4 a +5. El DCF dice de dónde sale su crecimiento. La regla de 40 baja de 141 a 108 | sin cambio de nivel | sin cambio de nivel |
| PGR | BPA 149,8 % → **25,6 %** (EDGAR, 6 ejercicios FY2020–FY2025; el FY2022 es el 8 % de la mediana). Sigue en +5 | = | = |
| PLTR | FCF 108,6 % → **no significativo**: la serie de EDGAR tiene FCF ≤ 0. La persistencia pasa de «99 → 95» a «94 → 90» | 95 → 90, excelente | = |
| NFLX (panel y local) | FCF 69,8 % → **no significativo**: base al 23 % y FCF negativos en EDGAR antes de 2020 | 87 → 85, excelente | = |
| AMT | FCF por acción 27,4 % → **no significativo**: base al 49 %, sin serie larga | 71 → 66, sólida | = |
| RIVN | **No cambia de tipo** (sigue en pre-beneficio). Su crecimiento de ingresos (44 %) salía de un FY2022 al 33 % de la mediana, y EDGAR tiene ingresos 0 antes de 2021: ahora es no significativo y no cuenta ni a favor ni en contra, así que decide la falta de beneficio. La fila de crecimiento pasa a no significativa. La regla de 40 puntúa con la cota (ver abajo): ≤ −26, el peor tramo, −4 como antes | 32 → 26, débil | 50 razonable = |

**Tests que cambian con la regla:**

- `test_normalize::test_nflx_fcf_growth_marked_anomalous`: no significativo con su motivo, en lugar de 69,83 %.
- `test_note_short`: PLTR, «94 → 90».
- `test_v4b_datos::test_roic_wacc_card_that_does_not_apply_says_why`: el pre-beneficio entra si el panel tiene alguno
  (genérico, sin nombrar a RIVN).
- `test_f10_n3`: `robust` siempre presente.
- `tests/guardian.py` (regla `roce`): leía «ROCE promedio del ciclo −35,76 %» como 35,76 %. Es un fallo del guardián
  que salió mientras RIVN pasaba por cíclica; ahora la cifra se lee con su signo.

**Muestras forzadas** (`tests/golden/forzados`) y **PDF nuevo** (`tests/golden/panel_pdf_v2`): regeneradas. Cambian los
mismos campos nuevos y los textos de las empresas de arriba.

**P/B justificado (banco y aseguradora).** Si el valor en libros no es significativo, el modelo de dos etapas no se
activa: queda el de una etapa, y `two_stage` lo dice («el crecimiento del valor en libros es no significativo: …: una
sola etapa»). Antes, la tasa desde el año anómalo podía activarlo. Ningún golden cambia por esto.

**Forward P/E.** Este consumidor no estaba en la lista. Su «forward creíble» se acota con el crecimiento del BPA a 3 años
(F9 · R1c). Con el BPA no significativo, la compresión no puntúa y el motivo se cita (la puerta que ya existía para el
BPA sin dato). Con el BPA de la serie larga, la cota usa esa tasa.

## Reescaneo en vivo (29-oct)

Dos pasadas seguidas sobre las mismas 158 empresas, con los mismos límites (EDGAR ≤ 5/s, Finnhub ≤ 30/min, un análisis
a la vez). La primera con la base (8df00bdb, 7,6 min, 353 MB) y la segunda con la rama. Comparación:
`tools/f10_crecimiento_compare.py`.

**Las 158:**

- **112 afectadas:** 46 con el BPA desde una base anómala (la regla del escaneo de control), 13 con los ingresos y
  68 con el FCF; algunas están en más de un grupo.
- **26 más con tipo de crecimiento** (rentable o pre-beneficio), para medir los cambios de tipo.
- **20 de control,** repartidas por tipo.

| Medida | Resultado |
|---|---:|
| Invariante «crecimiento desde un año base anómalo» (BPA y PEG) | **46 → 0** |
| Cambios de tipo | **0** en las 158 y en el panel |
| Cambios de nivel de calidad | **18**, todos a la baja (17 afectadas y VICI, de control) |
| Cambios de nivel de precio | **7** (APP, BSX, COIN, ENB, NOW, SCHW, STE) |
| Calidad que cambia de puntos | 66 (61 bajan, 5 suben) |
| Precio que cambia de puntos | 26: en 24 solo por la regla (Forward P/E, PEG, DCF, P/B justificado). AOS y ENB mezclan la regla con la referencia del sector, que se movió entre las dos pasadas (ENB: P/E de referencia 25,0x → 17,0x) |
| Control con cambios | 1 (VICI: su FFO por acción parte de un año anómalo) |

**Ejemplos:**

| Empresa | BPA a 3 años | Calidad | Precio |
|---|---|---|---|
| NVDA | 198 % → 101,7 % (EDGAR, 6 ejercicios). Ingresos 101 % → 69 %. FCF → n.s. | 93 excelente = | 45 razonable = (PEG 0,27x propio; el DCF declara su crecimiento) |
| VRT | 282 % → **n.s.** (sin serie larga robusta) | 84 → 80, sólida | 48 → 45, razonable |
| PODD | 245 % → 145 % (EDGAR, 6 ejercicios) | 94 excelente = | 50 razonable = |
| APP | Ingresos, BPA y FCF → n.s. (año base anómalo; los ingresos y el BPA, en el perímetro homogéneo tras la venta de sus apps) | 96 → 95, excelente | **69 atractivo → 58 razonable** (sin PEG; DCF con el crecimiento por defecto, declarado) |
| NOW | 61 % → 80 % (EDGAR) | 59 → 58, media | **25 muy exigente → 40 exigente** (PEG 0,99 y Forward P/E con crecimiento respaldado) |
| SCHW | Valor en libros 57 % → n.s. | 84 → 76, sólida | **39 exigente → 45 razonable** (P/B justificado de una etapa) |

## Tipos en todo el universo (543, escaneo con el código de la regla de clasificación)

- **Cambios de tipo frente al control del 29-oct:** 1, RL (cíclica → madura). No viene de la regla: fue un tiempo
  agotado de EDGAR (arriba), y el reintento lo arregla.
- **Empresas con un criterio de clasificación no significativo:** 2, y en ninguna decide.
  - FITB: banco, se clasifica por su industria.
  - TKO: sin BPA, así que no es pre-beneficio ni crecimiento rentable; madura, como en el control.
- **Con el reintento** (reescaneo de las 158), solo ARM queda sin EDGAR, y es estructural: no tiene estados XBRL.
