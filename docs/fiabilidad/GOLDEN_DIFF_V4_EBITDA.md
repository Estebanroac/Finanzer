# GOLDEN_DIFF_V4_EBITDA: el D&A del EBITDA sin amortizaciones de activos operativos recurrentes

Error de fondo encontrado por el usuario en la escalera de márgenes de NFLX (copia :8790, e36d55ad). Ingresos TTM 49,73
B$, margen bruto 50,7 % y margen EBITDA 67,3 %: un EBITDA por encima del bruto. Rama `rediseno/v4-ebitda`, desde
46a9b78f. Medida en vivo del 30-oct en `docs/fiabilidad/v4_ebitda/MEDIDA.md` (`backend/tools/v4_ebitda_medida.py`).

## Causa (confirmada con los datos)

El EBITDA del corte era EBIT + `info["depreciation"]`, el D&A TTM de Yahoo: la fila «Depreciation And Amortization» del
flujo de caja, que es la misma que «Reconciled Depreciation». En NFLX son 17,92 B$:

- 0,39 de «Depreciation»;
- 17,53 de «Amortization Of Intangibles», que en Netflix es la amortización del contenido. Es un coste operativo
  recurrente: va en el coste de ventas y se paga cada año.

EDGAR presenta 0,33 B$ de `DepreciationDepletionAndAmortization` en FY2025; el contenido va con una etiqueta propia del
emisor. El EBITDA salía inflado unas 2x y el EV/EBITDA, barato.

## La regla descartada: el D&A de EDGAR manda

Escaneo de las 543 empresas y sondeo de los conceptos de D&A de EDGAR (`backend/tools/v4_ebitda_da_probe.py`) en las 70
cuyo D&A difería más de un 20 % y en 32 más. Los conceptos de EDGAR no sirven como total:

- **36 emisores etiquetan solo `Depreciation`** (inmovilizado): faltaría la amortización de intangibles adquiridos. ABBV
  pasaría de 7,87 a 0,78; AVGO de 8,76 a 0,63; MRK, GILD…
- **Los paraguas se usan para partidas parciales.** MCD tiene 0,47 en `DepreciationDepletionAndAmortization` y 2,27 en
  `DepreciationAndAmortization`. Pasa lo mismo en URI (3,27 → 0,45), VLO (3,08 → 0,05), PCAR y UPS.

En cambio, el desglose de Yahoo cuadra con EDGAR en casi todos: su «Depreciation» es `Depreciation` y su «Amortization Of
Intangibles» es `AmortizationOfIntangibleAssets` (ABBV 7,09 = 7,09, DHR, IBM, TMO, SYK…). El error es una sola cosa: una
amortización de intangibles de Yahoo sin respaldo en EDGAR. NFLX tiene 17,53 frente a 0 (contenido); TTWO, 1,17 frente a
0,04 (software capitalizado).

## Regla (decisión del PM, 30-oct)

`lib/edgar_primary._da_reconcile`, en el corte:

- **Respaldo de EDGAR** de la amortización de intangibles de la fuente (`sec_edgar.da_split_ttm`): el mayor de
  `AmortizationOfIntangibleAssets` y el paraguas − la depreciación. Es la opción conservadora: un paraguas que es una
  partida parcial no recorta.
- **Lo que no tiene respaldo,** por encima de la materialidad de N1 (`thresholds.normalization.
  nonoperating_tolerance_revenue`, el 2 % de los ingresos, el mismo parámetro), sale del D&A y del EBITDA. Se nombra
  «amortización de activos operativos recurrentes (contenido, software capitalizado…) sin respaldo como intangibles
  adquiridos», en `data_provenance.edgar.primary.da` y en el origen del D&A y del EBITDA.
- **Por debajo de esa materialidad, o sin etiquetas en EDGAR,** no se toca y se declara «no verificable» en la
  procedencia, porque puede ser etiquetado parcial de EDGAR.
- **Las financieras quedan fuera:** el EBITDA no les aplica. El escaneo lo cazó en MTB, un banco con un 4,9 %.
- **El desglose de Yahoo** sale de los mismos 4 trimestres del corte (`ttm.DA_SPLIT_ROWS`). Con el corte en un ejercicio,
  sale de la fila anual.

**Invariante** `ebitda_sin_amortizacion_operativa` (`lib/model_invariants.py`): hay violación si queda en el EBITDA una
amortización sin respaldo, medida contra EDGAR, por encima de la materialidad. Los dos candidatos con umbral dan muchos
falsos positivos con el D&A de la fuente en las 543:

| Candidato | Marca | Falsos positivos |
|---|---|---|
| Margen EBITDA > margen bruto | 37 | 33 (petroleras, ferrocarriles, mineras, REIT); no detecta TTWO |
| D&A / ingresos > 15 %, salvo REIT, telecos y eléctricas | 18 | 14 |

## Medida en vivo (543 empresas)

Estado de la amortización de intangibles de la fuente:

| Estado | Empresas |
|---|---|
| Sin desglose de Yahoo | 422 |
| Respaldada por EDGAR | 92 |
| No verificable | 26 (12 con respaldo medido, todas ≤ 1,2 % de los ingresos) |
| Quitada del EBITDA | 3 |

Las tres a las que se les quita:

| Empresa | Quitada | % de los ingresos | Margen EBITDA | EV/EBITDA | Precio |
|---|---|---|---|---|---|
| NFLX | 17,53 B$ | 35,2 % | 67,3 % → 32,1 % | 7,9x → 16,6x | atractivo 69 → razonable 58 |
| TTWO | 1,13 B$ | 17,0 % | 17,5 % → 0,5 % | 31x → 1036x (EBIT casi cero) | exigente 30, igual |
| KDP | 0,48 B$ | 2,4 % | 22,5 % → 20,2 % | 17,3x → 19,3x | razonable 52, igual |

- En KDP, la amortización de Yahoo (0,71) triplica la de EDGAR (0,23).
- Las 20 de control no cambian.
- NFLX es la única que cambia de nivel.
- El invariante da 0 violaciones en el universo.

## Filas anuales (decisión del PM: una sola verdad en el TTM y en la historia)

La misma regla en cada ejercicio de los estados (`lib/edgar_primary._da_reconcile_fy`):

- se usa el desglose de la fila anual de Yahoo y el respaldo de EDGAR de ese ejercicio;
- la materialidad es la misma, sobre los ingresos del ejercicio;
- se quita del D&A y del EBITDA de la fila, que es la que usan el EV/EBITDA normalizado de las cíclicas y el FFO de los
  REIT;
- sin EDGAR del ejercicio, «no verificable» y declarado;
- todo queda en `data_provenance.edgar.primary.da_fy`.

En el universo, 5 empresas con algún ejercicio quitado:

| Empresa | Ejercicios (importe quitado) | Nota |
|---|---|---|
| NFLX | FY2022–FY2025: 14,03 / 14,20 / 15,30 / 16,42 B$ | El TTM y la historia, con la misma definición |
| TTWO | FY2023–FY2026: 0,18 / 0,21 / 0,27 / 0,39 B$ | La amortización anual de Yahoo es menor que la suma de sus trimestres (1,13 en el TTM) |
| HAS | FY2022 0,56 y FY2023 0,45 B$ | Cíclica: la amortización del contenido de eOne. Su EV/EBITDA normalizado pasa de 54x a 190x; los puntos no cambian (ya era −4) y se muestra «> 100x» |
| LITE | FY2024 0,03 B$ | Por encima del 2 % de los ingresos de ese ejercicio |
| VRSK | FY2022 0,07 B$ | Por encima del 2 % de los ingresos de ese ejercicio |

## EV/EBITDA con un denominador casi nulo: solo cómo se muestra

Sin una regla previa para múltiplos con un denominador casi nulo, se usa el criterio del margen de seguridad. Un
EV/EBITDA por encima de `thresholds.multiples_display.ev_ebitda_shown_max` (100x) se muestra «> 100x», y la cifra exacta
va en el detalle con su motivo.

`numfmt.ev_ebitda` y `ev_ebitda_detail` se aplican en todos los sitios: la fila y su lectura, la tarjeta, la comparación,
el motivo de la puntuación y la alerta. La puntuación no cambia.

El motivo tiene que ser verdad:

| Motivo | Cuándo | Ejemplos |
|---|---|---|
| «EBITDA casi nulo (x % de los ingresos)» | El margen EBITDA no llega a la materialidad de N1 | TTWO, 0,5 % |
| «múltiplo extremo» | El margen la pasa | PLTR (177,8x con un margen del 43 %); CRWD (1256,9x, 3,7 %) |
| Solo la cifra | El múltiplo es el normalizado de una cíclica, y el margen del TTM no es el de su denominador | HAS |

El margen llega por `numfmt.set_ebitda_margin`, fijado por `main` y por `build_display`. En el universo se muestran
acotadas 12: ARM, AXON, CARR, CRWD, DDOG, GILD, P, PANW, PLTR, SHOP, TSLA y TTWO.

## Golden

| Empresa | Cambio | Causa |
|---|---|---|
| NFLX (panel y local) | En el panel: margen EBITDA 66,2 % → 30,4 %, EV/EBITDA 9,3x → 20,3x, precio 55 → 46 y calidad 85 → 91. En local: precio crudo 65 → 50 (atractivo → razonable) | La amortización del contenido (17,30 B$ en el replay, el 35,8 % de los ingresos) sale del EBITDA. Con la confianza más alta, la calidad se contrae menos |
| CRWD | `data_provenance.edgar.primary.da` y `da_fy`: respaldado. EV/EBITDA «> 100x» (cifra exacta 1256,9x: múltiplo extremo) en la fila, la lectura, la comparación, la puntuación y la alerta | Presentación del múltiplo; los puntos no cambian |
| PLTR | EV/EBITDA «> 100x» (cifra exacta 177,8x: múltiplo extremo) en los mismos sitios | Presentación |
| TSM | `da` y `da_fy`: no verificable | 20-F, sin etiqueta de amortización en EDGAR |
| NVDA, NVO | Solo `da_fy`: sus ejercicios respaldados (NVO FY2022, no verificable) | — |

Fixtures: los companyfacts del juego f2b se amplían con los conceptos de `sec_edgar.DA_SPLIT`, con
`tests/f10_extend_charges_fixtures.py`. Son 3179 hechos, solo de filings que el juego ya tiene. Así el replay da lo mismo
que en vivo: CRWD sale «respaldado».

