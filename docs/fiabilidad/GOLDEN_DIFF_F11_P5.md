# F11 · Paso 5 (T6 + T5): causalidad sostenida y beta contrastada (4-nov-2026)

Rama `fiabilidad/f11-medir`, sobre el paso 4 (349d6284). Visto bueno del usuario: «Sí, paso 5». Es el último paso de
F11. Al final va el balance de F11 entero frente a la medida inicial.

## Qué cambia

| Hallazgo | Arreglo en origen (regla general) | Archivos |
|---|---|---|
| T6 · «propio de la empresa» frente a un ETF de EE. UU. (43 emisores extranjeros) | Una empresa con sede fuera de EE. UU. se compara además con el ETF de su país (`market.country_etfs`, iShares MSCI en USD, 31 países). El movimiento es «propio de la empresa» solo si lo es frente al sector **y** frente al país; si no, «se mueve con su país» o «con su sector». Sin ETF para su país (Bermudas, Uruguay, Luxemburgo) o si cotiza en otra moneda (MC.PA, en EUR), lo dice y no concluye | `lib/market_context.py`, `config/market.toml`, `config/schema.toml` |
| T6 · «sobrerreacción» con reacción negativa a sus resultados (22) | La lectura de De Bondt y Thaler solo se cita si los últimos resultados **no** tuvieron una reacción negativa (`pead.reaction ≥ 0`). Si la tuvieron, o no se sabe, la lectura es una pregunta abierta («el precio puede estar descontando algo que este informe no mide…») y dice que no es una señal de compra | `lib/market_context.py` |
| T5 · beta sustituta sin contrastar con la propia (57) | Si la regresión propia explica algo (R² ≥ `contrast_min_r2`, 0,10) y la beta usada queda fuera de la propia ± `contrast_k_se` (2) errores estándar, se declara (`beta.contrast`) y baja la calidad de fuente a «media», con el motivo traducido. **La beta no cambia.** Ponderar la propia y la de la industria es del modelo general (Vasicek) | `lib/beta.py`, `lib/valuation_confidence.py`, `lib/plain_language.py`, `main.py`, `config/market.toml` |

**Fixtures:** el replay de los tests no tenía las series de los ETF de país, y la suite se colgaba más de 30 minutos
(cada descarga fallaba con `FixtureMiss` y reintentaba). Se grabaron las de EWU, EWN, EWQ, EWJ, EWT y EDEN con el mismo
rango que el resto del juego del historial (`tests/f11_country_etf_fixtures.py`, declarado en la metadata). No se salta
la descarga en los tests.

## Golden

Regenerados tras revisar el diff. Suite: **6562 passed, 26 skipped, 0 failed**, más los 5 tests nuevos de
`tests/test_f11_t5_t6.py`.

| Empresa | Cambio | Causa |
|---|---|---|
| TSM, ASML, NVO, HSBC, UL, SHEL | La fuerza relativa añade el ETF de su país (EWT, EWN, EDEN, EWU). Mantienen su lectura | T6 |
| BCS | «se mueve con su sector» → **«se mueve con su país»** (+14,8 % frente al +17,5 % del Reino Unido) | T6 |
| MC.PA | Sin lectura de país: «cotiza en EUR: los ETF de país de referencia son de EE. UU., en USD» | T6 |
| NFLX, NVO | «sobrerreacción» → «caída sin explicar» (NFLX: reacción de −4,9 % a sus resultados; NVO: sin dato de reacción) | T6 |
| BRK-B, FCX, MU, PLTR, TM | Calidad de fuente «media»: la beta de su industria queda fuera de la propia ± 2 EE (TM: 1,46 frente a 0,73 ± 0,17, R² 0,15) | T5 |
| Todas | `beta.contrast` en el JSON (null si no aplica) | T5 |

Ningún nivel de confianza ni ningún veredicto del panel cambia.

## Efecto en el universo

Escaneo de las 543 (caché `2026-11-04-f11-p5`, 0 errores) frente al del paso 4:

| Regla | Paso 4 | Paso 5 |
|---|---:|---:|
| `beta_contrastada` (T5) | 57 | **0** (57 declaradas) |
| `causalidad_sostenida` (T6) | 64 | **4** |
| `forward_creible` (F3) | 14 | 15 (PTC: el consenso de Finnhub cambió entre las dos corridas; P/E forward 21,9 → 19,8) |

**Los 4 que quedan en `causalidad_sostenida`** son ACGL y EG (Bermudas), MELI (Uruguay) y SPOT (Luxemburgo). No hay ETF
de esos países. El análisis lo dice y no concluye, que es lo correcto. La regla los sigue contando porque no hay lectura
de país.

**Sobrerreacción, medida con la reacción.** El escaneo salta las sorpresas de Finnhub para no gastar la cuota gratuita
(`finnhub_skip_paths`), así que en él ninguna empresa tiene reacción y las 23 «sobrerreacciones» del paso 4 salen como
«caída sin explicar». Para medirlo de verdad, reescaneé esas 24 empresas con las sorpresas activas (caché
`2026-11-04-f11-p5d`), como en producción:
- **9 siguen siendo «sobrerreacción»**, con reacción no negativa a sus resultados: BX, CMCSA, CMG, ERIE, GLW, KLAC, ROL,
  TMUS y TSCO.
- **13 pasan a «caída sin explicar»**, porque el mercado castigó sus resultados: ADBE, BRO, CPRT, DECK, FICO (−14,8 %),
  INTU, LII, LULU (−16,9 %), MKC, NFLX (−7,8 %), PODD (−16,2 %), TPL y ZTS.
- **2 no tienen dato de reacción** (INFY y NVO no presentan 8-K de resultados) y también quedan como pregunta abierta.

**Notas y veredictos.** Cambia la confianza de 14 empresas, todas por T5 (la beta sustituta fuera de la propia): J,
SMCI, AWK, BE, CSX, ECL, IRM, LITE, P, PLTR, PYPL, SHOP, SYK y VMC. Con ella cambia su nota de precio, por la
contracción hacia 50. Cambian 4 veredictos, todos de un escalón y en el precio: AWK, P y VMC pasan de «muy exigente» a
«exigente», y SMCI de «atractivo» a «razonable».

- **AWK, verificado aparte:** su beta propia es **−0,46** (R² 0,12, 103 semanas). La recalculé con Yahoo y da
  −0,456, R² 0,117 y EE 0,125. Es real: en estos dos años el agua se movió contra el mercado. La de la industria (0,40)
  queda fuera de su intervalo, y se dice.
- **FE** (calidad 41 → 55, «débil» → «media») **no es del código.** En esta corrida se agotó el presupuesto de EDGAR
  (3 s) y no leyó su último 10-Q. En el paso 4 le pasó a AEP. Es ruido de red, uno por corrida.

## Balance de F11

Misma regla que la medida inicial (`F11_MEDIDA_2026-11-04.md`): empresas con al menos un fallo que mueve la nota, el
voto de un método o la confianza.

| | Medida inicial | Tras el paso 5 |
|---|---:|---:|
| Empresas con ≥ 1 fallo que puntúa | **255 de 543 (47 %)** | **30 de 543 (5,5 %)** |
| Con dos o más | 61 | 3 |

| Regla | Inicial | Final | Qué queda |
|---|---:|---:|---|
| `metodo_citado_aplicable` (T7) | 542 | 0 | — |
| `caida_avisada` (T3) | 213 | 0 | — |
| `forward_creible` (F3) | 83 | 15 | Las respaldan a la vez el BPA a 3 años y el del último ejercicio. **Decisión del usuario:** listón del 25 % para las maduras (recomendado: no) |
| `cota_aplicada` (T4) | 79 | 64 | Solo el rótulo «3 años» en otra ventana (texto). Ninguna supera ya su cota |
| `referencia_representativa` (T1) | 67 | 0 | — |
| `causalidad_sostenida` (T6) | 63 | 4 | Países sin ETF |
| `beta_contrastada` (T5) | 57 | 0 | Declaradas; ponderar la beta es del modelo general |
| `una_definicion_ttm_fy` (N2) | 35 | 0 | — |
| `voto_estable` (F1) | 32 | 0 | — |
| `inverso_tasa_base` (F2) | 28 | 0 | — |
| `calidad_sin_saturar` (F4) | 18 | 18 | Del modelo general (Q1), sin tocar en F11 |
| `riesgo_critico_medido` (T3) | 12 | 0 | — |
| `implicito_mismo_modelo` (N1) | 9 | 0 | — |
| `convergencia_independiente` (T2) | 1 | 0 | — |

Lo que queda (F4, F3 de fondo, N3, N4, la beta Vasicek y el P/B de banco ajustado por ROE) es cambio de método, no
cables sueltos. Va al modelo general, como se acordó al medir.
