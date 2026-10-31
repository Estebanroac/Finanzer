# Diff de los golden de F8, causa por causa

> Plan: `docs/superpowers/plans/2026-10-26-fiabilidad-auditoria-externa.md` (Fase A). Auditoría:
> `docs/fiabilidad/auditoria-externa-2026-10-26.txt`. Rama `fiabilidad/f8-auditoria`, desde `a0e824f`
> (punta de `rediseno/v4b-datos`).
>
> Un commit por error. Para cada uno: los golden del replay (37 del panel y 6 locales, con
> `backend/tools/verdicts_vs_main.py --ref <commit anterior>`) y, aparte, las 26 empresas de la auditoría con datos
> reales (`backend/tools/f8_evidencia.py`; detalle en `F8_AUDITORIA_REGISTRO.md`).
>
> El replay no tiene ^TNX: ya usaba el Rf de config (5,29 %), así que en los golden no se ve el cambio del Rf. Con
> datos reales sí se ve (4,99 % → 5,29 %).

## E1 · Ke y beta con controles de cordura

**Causa común.** Cinco reglas nuevas, todas en config:

1. La beta propia solo entra si pasa tres filtros: R² ≥ 0,20, error estándar ≤ 0,25 y beta entre 0,4 y 2,5.
2. Si no los pasa, entra la beta de abajo hacia arriba: la βU de la industria de Damodaran (corregida por caja),
   reapalancada con la D/E de mercado de la empresa. Hay dos excepciones:
   - las financieras usan la beta media de su industria;
   - si la D/E de la empresa supera 3 veces la de su industria, también se usa la beta media de la industria.
3. El Ke tiene dos pisos: Rf + 0,5 × ERP y, si hay deuda, Kd + 1 pp.
4. El Rf y la ERP son del mismo día: el par de Damodaran del 1-oct-2026.
5. Prueba de sensibilidad: si el nivel de precio cambia con Ke ± 1 pp, el veredicto es «dependiente de Ke» y la
   confianza baja un escalón.

**Golden: 15 de 43 cambian** en los 11 campos de veredicto. Solo uno cambia de nivel de precio: NFLX local.

| Juego | Ticker | Cambio | Causa | Justificación financiera |
|---|---|---|---|---|
| local | NFLX | precio razonable → **atractivo** (61 → 69; crudo 65 → 75) | Se descarta su beta propia (0,96 ajustada, R² 0,15). Entra la de abajo hacia arriba, 0,79 (Entertainment, βU 0,76, D/E 0,05). El Ke baja del 9,31 % al 8,61 % y el DCF pasa de −2 % a +10 %. | Con R² 0,15, la regresión explica el 15 % del título. La beta de su industria, con su estructura de capital, es una estimación más estable. Con Ke − 1 pp sigue atractivo y con Ke + 1 pp vuelve a razonable: queda declarado. |
| panel | TM | precio exigente (35 → 31; crudo 35 → 25); confianza alta → media | Se descarta su beta propia (0,81 ajustada, R² 0,15). Su D/E de mercado, 1,20, es 6,1 veces la de Auto & Truck (0,20) porque incluye la deuda de Toyota Financial Services. Por eso no se reapalanca: entra la beta media de la industria, 1,46. El Ke sube del 8,69 % al 11,42 %. Además es dependiente de Ke. | Reapalancar con la deuda de la cautiva daba β 2,56 y un Ke del 16 %, que no es creíble. **Límite conocido:** la tabla de EE. UU. de Auto & Truck pesa mucho a Tesla, así que 1,46 es alta para Toyota. La tabla regional de Damodaran (gratuita) es una mejora posible, propuesta como seguimiento. |
| panel | XOM | crudo 45 → 40 (mostrado 48 → 45); calidad 82 → 81 | Ke del 6,55 % al 7,39 % por el piso Rf + 0,5 × ERP. El DCF pasa de +16 % a −4 %. La confianza ya era baja. | Es el caso de la auditoría: un Ke de Rf + 1,3 pp es casi el de un bono, con β sectorial 0,30. El piso de medio mercado lo corrige. El −1 de calidad viene del spread ROIC − WACC con el WACC más alto. |
| panel | NEE | confianza media → baja | El Ke sube del 7,31 % al 7,67 % por el piso Kd + 1 pp (Kd 6,67 %). Además es dependiente de Ke: pasa de razonable a exigente con + 1 pp. | El accionista es residual: su Ke no puede quedar por debajo del coste de su deuda. |
| panel | DUK | confianza media → baja | Beta de abajo hacia arriba 0,57 (Power, βU 0,31, D/E 0,98) en lugar de la media de la industria, 0,48. Dependiente de Ke: pasa de razonable a exigente con + 1 pp. | Reapalancar con su D/E real añade el riesgo financiero de una utility muy endeudada. |
| panel | NFLX | confianza media → baja | La misma beta que en NFLX local. Dependiente de Ke: pasa de razonable a atractivo con − 1 pp. | — |
| panel | BRK-B | confianza media → baja | Se descarta su beta propia (bruta 0,40, R² 0,14): entra la de abajo hacia arriba, 0,67. Dependiente de Ke: pasa de exigente a muy exigente con + 1 pp. | — |
| panel | NVO | confianza alta → media | Beta de abajo hacia arriba 1,01 (antes, la media de la industria, 0,98). Dependiente de Ke: pasa de atractivo a razonable con + 1 pp. | — |
| panel | BCS, NVDA | confianza media → baja | Sin cambio de beta ni de Ke. Dependientes de Ke: pasan de razonable a atractivo con − 1 pp. | La prueba de sensibilidad hace lo que pide la auditoría: un veredicto que cambia con 1 pp de Ke no merece la misma confianza. |
| panel | HSBC, TSM, V, JPM; local JPM | confianza alta → media | Sin cambio de Ke (beta propia que pasa los filtros). Dependientes de Ke. | Igual. |

Puntuaciones mostradas que cambian solo por la confianza nueva (el crudo no cambia): BCS 61 → 58, BRK-B 35 → 40,
DUK 46 → 48, HSBC 40 → 42, JPM 45 → 46, NEE 46 → 48, NFLX (panel) 61 → 58, NVDA 58 → 55, NVO 75 → 69, TSM 35 → 39,
V 30 → 35. Con menos confianza, la puntuación se contrae más hacia el neutro (50).

**Las 26 de la auditoría con datos reales (26-oct, después del cierre).** Cuatro cambian de nivel de precio:

| Ticker | Antes → E1 | Causa |
|---|---|---|
| AWK | exigente → **muy exigente** | Su beta propia era −0,44 (R² 0,11): ahora se descarta. El Ke sube del 5,14 % (por debajo del Kd, 5,88 %) al 7,39 %. El P/B justificado pasa de verla barata a verla cara. La auditoría: «pasa de barata a cara». |
| NEE | razonable → **exigente** | Piso Kd + 1 pp: Ke del 7,00 % al 9,04 % (Kd 8,04 %, rating sintético por su cobertura). |
| KMI | exigente → **muy exigente** | El Rf del par sube el Ke 0,12 pp y KMI estaba en la frontera. Con datos reales, también es dependiente de Ke. |
| MCD | exigente → **razonable** | El Ke sube 0,33 pp y el DCF la ve más cara (−35,7 % frente a −30,6 %). Pero la fiabilidad del DCF baja de alta a media porque la regla actual mira la distancia al precio, y eso le quita peso en Valoración. **Lo corrige E8**: fiabilidad del DCF sin mirar el precio. Hasta entonces es el comportamiento heredado. |

La confianza baja un escalón por dependencia de Ke en 9 empresas: NVDA, LLY, UNH, JPM, CB, CAT, KO, KMI y AWK. XOM
también es dependiente, pero su confianza ya era baja.

CB y XOM no cambian de nivel (razonable), pero ahora quedan como dependientes de Ke, con confianza baja. La auditoría
estimaba para CB un Ke del 9 %. Con las reglas, la beta media de su industria (Insurance Prop/Cas., 0,48) da un CAPM
del 7,31 %, y el piso lo sube al 7,39 %. Un 9 % exigiría una beta de 0,9, que no sostienen ni su regresión (R² 0,01)
ni su industria. La prueba de sensibilidad declara esa dependencia en lugar de fijar una beta a mano.

## E4 + E5 · Etiquetas e incoherencias de VZ; portada con la métrica normalizada

**Causas.** Cinco reglas, en el motor y en config:

1. **Titular de crecimiento.** En una madura de dividendo alto, Crecimiento puntúa el retorno total (dividendo +
   ingresos por acción). Los textos de «ingresos» citaban esa suma. Ahora citan el crecimiento de los ingresos (el del
   DCF), y el retorno total va en su propia fila, rotulado. No cambia ninguna puntuación.
2. **PEG n.s.** El PEG no es significativo (no puntúa, no cuenta como dato ausente y la tabla da el motivo) si:
   - el crecimiento del BPA del informe (CAGR a 3 años) es ≤ 0; o
   - el PEG es el de la fuente y, con el crecimiento del informe, su lectura cambia de tramo (`peg_bounds`).
   Sin crecimiento del informe no hay contraste y el PEG de la fuente se queda.
3. **Convergencia.** «Alta» exige además que ningún múltiplo individual contradiga la dirección común con lectura
   extrema, ±1 (`convergence_extreme_reading`). Si lo hace, la convergencia es media.
4. **Telecom.** FCF de la valoración (P/FCF, FCF yield y DCF) = FCF − media de 5 años de las compras de espectro
   (EDGAR, `PaymentsToAcquireIntangibleAssets`). Sin los 5 ejercicios en EDGAR: sin ajuste, declarado. El PM la pasó
   a 10 años: ver «E4 (ajuste)» más abajo.
5. **E5.** Si el motor marca el P/E reportado como no fiable, la lectura del P/E (portada, resumen y sección) es la del
   normalizado; el reportado pasa a la nota con su etiqueta. No cambia ninguna puntuación.

**Golden: 6 de 43 cambian** en los 11 campos de veredicto. Uno cambia de nivel de precio: UL.

| Juego | Ticker | Cambio | Causa | Justificación financiera |
|---|---|---|---|---|
| panel | UL | precio exigente → **razonable** (crudo 40 → 50; mostrado 42 → 50) | PEG n.s. (regla 2): el BPA del informe cae un 1,7 % anual y el PEG de la fuente (2,74, «muy caro», −3) se calculaba con un crecimiento de consenso del 4,8 %. Sin él, el bloque de múltiplos pasa de 0 a +2. La convergencia pasa de media a baja: los múltiplos la ven barata y el DCF cara. | Con el BPA en contracción, un PEG no mide nada: dividir el P/E por un crecimiento que el informe no muestra es mezclar dos empresas. La convergencia baja ya avisa de que los métodos no coinciden. |
| panel | KO | crudo 15 → 20 (mostrado 15 → 28); confianza alta → media | PEG n.s. (regla 2): el de la fuente, 3,22, supone un crecimiento del BPA del 8,6 %; con el del informe, 11,6 %, sería 2,39 (otro tramo). El bloque pasa de −3 a −2. Con el PEG fuera, el veredicto se vuelve dependiente de Ke (muy exigente con Ke − 1 pp pasa a exigente). | El lector ve un BPA que crece un 11,6 % y un PEG que no sale de ahí. Sigue en «muy exigente». |
| panel | JNJ | mostrado 30 → 35; confianza alta → media | PEG n.s. (regla 2: 2,42 frente a 1,64 con el 17,9 % del informe) y convergencia alta → media (regla 3): el Forward P/E lee +1,00, contrario a «cara». | Un múltiplo en lectura extrema contraria no puede convivir con «los métodos coinciden». |
| panel | AMZN | mostrado 35 → 39; confianza alta → media | Convergencia alta → media (regla 3): Forward P/E en +1,00 contra «cara». | Igual. |
| panel | TSM | mostrado 39 → 42; confianza media → baja | Convergencia alta → media (regla 3): Forward P/E en +1,00. Con la dependencia de Ke de E1, baja a «baja». | Igual. |
| local | V | crudo y mostrado 25 → 20 | PEG n.s. (regla 2): el de la fuente, 1,75, supone un 18,7 % y el del informe es el 13,4 % (2,45: otro tramo). El bloque pasa de −3 a −4. Sigue en «muy exigente». | — |

**Sin cambio en los 11 campos, con cambio visible:**

- NFLX, panel y local: PEG n.s. (0,93 y 1,20 de la fuente frente a 0,61 con el 36,5 % del informe). La puntuación no
  cambia porque el bloque redondea igual.
- GOOGL y AMZN (E5): la lectura del P/E cita el normalizado (31,4x y 39,9x) y el reportado va a la nota.
- VZ no está en el panel. Con datos reales, abajo.

**Las 26 de la auditoría con datos reales** (corrida «e4», 27-oct antes de la apertura, con los mismos precios que
«e1»). Una cambia de nivel de precio:

| Ticker | Antes → E4 | Causa |
|---|---|---|
| VZ | atractivo (alta) → **exigente** (media); crudo 80 → 40 | Las tres reglas de E4 a la vez. (a) Espectro: FCF 20,16 mil millones − media de las compras de espectro de FY2021–FY2025, 11,68 = 8,48. Con él, el P/FCF pasa de 8,9x a 21,1x, el FCF yield del 11,3 % al 4,7 % y el DCF de +65 % a −83 %, con fiabilidad baja: la tabla de sensibilidad no contiene el precio. (b) PEG 0,80 n.s.: el BPA cae un 7,1 % anual. (c) La convergencia ya no es alta: sin DCF evaluable, el DCF inverso y los múltiplos no coinciden. |

Cambia la confianza, sin cambio de nivel:

- LLY: media → baja. Convergencia alta → media (regla 3: Forward P/E +1,00), más la dependencia de Ke.
- UNH: baja → media. PEG n.s. (BPA −14,5 %). Sin él, deja de ser dependiente de Ke.

Cambia el precio crudo, sin cambio de nivel:

- MCD: 45 → 55, sigue «razonable». PEG n.s. (2,63 de la fuente frente a 1,58 con el 12,8 % del informe). La
  convergencia pasa de media a baja: múltiplos barata y DCF cara.
- KO: 15 → 20. PEG n.s.
- SAP: 30 → 35. PEG n.s.

El PEG queda n.s. en 16 de 26 (puntuaba en 7: UNH, MCD, VZ, KO, WMT, LIN y SAP). En las otras 9 no puntuaba, porque su arquetipo no lo usa (FINANCIAL, CYCLICAL,
UTILITY, REIT): ahí solo cambia la tabla.

## E2 · Bandera de pico de beneficio

**Causa.** Una regla nueva (`lib/earnings_peak.py`, `valuation.earnings_peak`). Hay bandera si se cumplen dos
condiciones:

- (a) el beneficio TTM con el que se valora supera en más de un 40 % la mediana de los 3 últimos ejercicios;
- (b) el forward P/E de Yahoo supera en más de un 20 % al P/E TTM.

El forward entra solo si es coherente: el beneficio que implica no puede quedar por debajo de mín(TTM, mediana) / 3.
Un error de escala hacia abajo activaría (b) por error; uno hacia arriba nunca pone la bandera. Si no es coherente, o
no hay forward, la bandera se decide solo con (a) y se declara. La bandera solo se calcula en los arquetipos en los que
el P/E puntúa. No se usa consenso de pago ni consenso estimado.

Con bandera:

- el P/E del score es la media del P/E sobre la mediana de 3 ejercicios y el forward (solo el primero si no hay
  forward fiable);
- la lectura del P/E, el resumen y las alertas citan ese P/E («un beneficio sin su pico»);
- el P/E del TTM (o del último ejercicio, sin 4 trimestres) pasa a la nota con el motivo («beneficio atípico»);
- la compresión del Forward P/E se mide frente al TTM, porque el forward ya entra en el P/E que puntúa.

**Golden: 1 de 43 cambia** en los 11 campos de veredicto, sin cambio de nivel.

| Juego | Ticker | Cambio | Causa | Justificación financiera |
|---|---|---|---|---|
| panel | UL | crudo 50 → 45, mostrado 50 → 46; sigue «razonable» | Bandera de pico con las dos condiciones. El beneficio TTM (normalizado) supera en un 53 % la mediana de FY2023–FY2025, 7,02 mil millones. El forward P/E (16,1x) es un 21 % mayor que el TTM (13,2x). El P/E que puntúa pasa de 13,2x («muy barato», +5) a 18,1x (media de 20,2x y 16,1x; «atractivo», +3). El bloque de múltiplos baja de +2 a +1. | El TTM de Unilever no es el beneficio que el mercado espera repetir: su propio forward es menor. Con 13,2x parecía un 49 % más barata que el sector solo por un beneficio puntual. |

En el resto de golden solo se añade el bloque `earnings_peak` del análisis (vacío donde el P/E no puntúa). En NVDA,
PLTR y TSM del panel se cumple (a) sin (b): el mercado espera más beneficio, no menos, y no hay bandera. Es la
compensación que pedía la auditoría.

**Las 26 de la auditoría con datos reales** (corrida «e2», 27-oct antes de la apertura, mismos precios que «e4»):

| Ticker | Antes → E2 | Causa |
|---|---|---|
| NEE | exigente (media), crudo 35 → **30**; sigue «exigente» | Bandera con las dos condiciones. TTM normalizado de 11,58 mil millones frente a la mediana de 6,95 (+67 %). Forward P/E de 18,7x frente a 14,8x TTM (+27 %). El P/E que puntúa pasa de 14,9x («atractivo», +3, frente a 21x del sector) a 21,8x (media de 24,8x sobre la mediana y 18,7x forward; «en línea», 0). El nivel ya era «exigente» desde E1, por el piso del Ke, así que E2 no lo cambia otra vez. |

Ninguna otra lleva bandera. Cumplen (a) sin (b): NVDA y LLY, en las que el forward implica más beneficio.
GOOGL cumple (b) sin (a), porque la normalización ya le quitó el pico.

## E4 (ajuste) · Espectro de telecom con 10 años

**Causa.** Decisión del PM del 27-oct, desviación razonada de la auditoría:
`valuation.telecom_spectrum.years` pasa de 5 a 10, el ciclo completo de subastas. Con menos años en EDGAR se usan los
que haya, con un mínimo de 5.

**Golden: 0 de 43 cambian.** No hay telecom en el panel ni en el juego local.

**Con datos reales** (corrida «e4_espectro10», mismo precio que «e2»):

| Ticker | E2 → ajuste | Causa |
|---|---|---|
| VZ | exigente (media), crudo 40 → **razonable** (baja), crudo 45 | La media del espectro baja de 11,68 a 6,57 mil millones, porque la banda C de 2021 pesa la mitad que en 5 años. FCF ajustado de 8,48 → 13,59 mil millones; P/FCF de 21,1x → 13,1x; DCF de −83 % (fiabilidad baja) → −18 % (fiabilidad alta). La confianza baja porque es dependiente de Ke: pasa a exigente con Ke + 1 pp. |

Frente al «antes» de la auditoría (atractivo, confianza alta), VZ queda en razonable con confianza baja: E4 corrige el
titular, el PEG y la convergencia, y el FCF resta el espectro de un ciclo completo.

## E8 · Fiabilidad del DCF por los insumos, no por el precio

**Causa.** Una regla nueva en `valuation_confidence.dcf_reliability` (umbrales en `thresholds.dcf_reliability`). La
fiabilidad ya no mira si la tabla de sensibilidad contiene el precio: ese dato solo informa, y la distancia al precio
cuenta en la convergencia entre métodos.

Se parte de «alta» y cada criterio que falla resta un escalón:

1. el valor terminal pesa más del 75 % (más del 85 %: baja directamente, como antes);
2. la dispersión del bloque central de la tabla (g ± 2,5 pp, WACC ± 1 pp) supera 2,5 veces (máximo ÷ mínimo), o algún
   valor es ≤ 0;
3. el margen FCF de los 5 últimos ejercicios (EDGAR) es inestable: coeficiente de variación > 0,33, o media ≤ 0;
4. hay banderas de datos: beta sin verificar, o la bandera de pico de E2.

Se mantienen dos reglas: el FCF de entrada marcado o inferido da baja, y una cíclica no pasa de media.

**Desviación razonada en el criterio 2.** La auditoría pide máximo ÷ mínimo > 2,5 sobre la tabla. La tabla completa
abarca supuestos extremos a propósito (g ± 5 pp, WACC ± 2 pp) y va de 2,2 a 16,8 veces: con 2,5 restaba en 30 de 33
empresas y no discriminaba. El bloque central mide la sensibilidad a errores razonables (el mismo ± 1 pp de la prueba
de Ke de E1). Ahí, 2,5 discrimina: lo superan VZ (3,96), KMI (3,66) y DOW (55).

**Golden: 13 de 43 cambian; 4 de nivel de precio.**

| Juego | Ticker | Cambio | Causa | Justificación financiera |
|---|---|---|---|---|
| panel | JNJ | exigente → **muy exigente** (crudo 30 → 20) | Fiabilidad del DCF de media a alta: el precio quedaba fuera del bloque central, pero los insumos son estables (margen FCF 21–25 %, coeficiente de variación 0,07). El DCF (−41 %) pasa de −2 a −4. | Es la asimetría de la auditoría: un DCF que ve cara la empresa restaba la mitad porque no coincidía con el precio. |
| panel | PG | exigente → **muy exigente** (crudo 30 → 20); confianza alta → media | Igual: fiabilidad de media a alta (margen 17–20 %) y DCF (−37 %) de −2 a −4. Ahora es dependiente de Ke. | Igual. |
| panel | V | exigente → **muy exigente** (crudo 30 → 25); confianza media → alta | Fiabilidad de media a alta (margen 52–61 %) y DCF (−29 %) de −1 a −2. Deja de ser dependiente de Ke. | Igual. |
| panel | KO | muy exigente → **exigente** (crudo 20 → 30); confianza media → alta | Fiabilidad de alta a media: el margen FCF pasa del 29 % al 10 % en 5 ejercicios (coeficiente de variación 0,39), por el depósito fiscal y los pagos de Fairlife. El DCF (−31 %) pasa de −4 a −2. | Un DCF sobre un FCF base inestable merece menos peso, lo vea caro o barato. |
| panel | AAPL | sin cambio en los 11 campos | Fiabilidad de baja a alta: ya no se descarta por estar fuera de la tabla. El DCF directo (−66 %) sustituye al inverso; los dos restaban −4. | — |
| panel | ASML, MU, PLTR; panel y local FCX | crudo +10 (ASML 10 → 20, MU 10 → 20, PLTR 10 → 20, FCX 25 → 35) | Fiabilidad de baja a media: margen FCF inestable (coeficiente de variación de 0,40 a 6,7) y, en las cíclicas, el techo de media. Puntúa el DCF directo con −2 en lugar del inverso con −4. | El directo cuenta, con la mitad del peso por la inestabilidad del flujo. Ninguna cambia de nivel. |
| panel | DOW | crudo 50 → 60; confianza baja → media | Fiabilidad de media a baja: el bloque central va de 0,32 a 17,69 USD (55 veces) y el margen FCF es inestable. El DCF directo deja de puntuar (0) y la convergencia sube a media. | Con un FCF casi nulo, el valor del DCF no es una medida. |
| panel | NVDA | confianza baja → media (mostrado 55 → 58) | Fiabilidad de alta a media: margen FCF del 14 % al 47 % (coeficiente de variación 0,35). El DCF (+2 %) sigue en 0 y deja de ser dependiente de Ke. | — |
| panel | TSM | crudo 35 → 30 | Fiabilidad de media a alta; el DCF (−28 %) pasa de −1 a −2. | Igual que JNJ. |
| local | NFLX | crudo 75 → 70 (sigue «atractivo») | Fiabilidad de alta a media: margen FCF del −0,4 % al 21 % (coeficiente de variación 0,69); el DCF (+10 %) pasa de +2 a +1. | — |

**Las 26 de la auditoría con datos reales.** Corridas «e8_antes» (código de E2 + espectro) y «e8», hechas seguidas el
27-oct después de la apertura. Los precios varían menos de un 0,4 % entre las dos.

| Ticker | Antes → E8 | Causa |
|---|---|---|
| UNH | razonable → **atractivo** (crudo 65 → 75) | Fiabilidad de media a alta: margen FCF del 7 % al 4 %, con coeficiente de variación 0,23, por debajo del umbral. El DCF (+69 %) pasa de +2 a +4. **Efecto conocido hasta E7**: la auditoría señala este DCF como sesgado, porque crece con los ingresos (11 %) mientras el margen cae. E8 hace lo que pide (confiar en los insumos) y deja al descubierto el sesgo del motor de crecimiento, que corrige E7. Como con MCD en E1, queda declarado. |
| KO | muy exigente → **exigente** (crudo 20 → 30); confianza media → alta | Como en el panel: margen FCF inestable (0,39) y fiabilidad de alta a media. |
| KMI | muy exigente → **exigente** (crudo 20 → 30); confianza media → alta | Fiabilidad de alta a media: el bloque central va de 3,66 veces su mínimo a su máximo. El DCF (−38 %) pasa de −4 a −2. |

La fiabilidad cambia sin cambio de nivel en estas: MSFT, GOOGL, LIN, WMT y UNP pasan de baja a alta (el caso de la
auditoría); FCX y ASML, de baja a media; LLY y SAP, de media a alta; NVDA y VZ, de alta a media. En SAP, UNP y LLY baja
el crudo, porque su DCF caro cuenta más; en ASML sube. MCD sigue en «alta» por los insumos (margen 24–31 %, bloque
central de 2,41 veces), y su «razonable» ya no depende de la distancia al precio, como anticipaba E1.

## E9 · La rentabilidad mide el capital invertido

**Causa.** Tres reglas en `score_rentabilidad`, con los parámetros en `thresholds.score.rentabilidad`:

1. **El diferencial ROIC − WACC manda.** Por debajo de 0, Rentabilidad no pasa de 10/20; por debajo de −3 pp, de 6/20
   (`spread_caps`). El desglose lleva la fila «Tope por ROIC − WACC».
2. **Márgenes frente a los de su industria de Damodaran** (`operating_margin_vs_industry` = 1,5 / 1,15 / 0,85 / 0,5 veces;
   `net_margin_vs_industry` = 1,5 / 1,0 / 0,5), no con umbrales absolutos. Sin margen de la industria, las bandas
   absolutas de antes, declaradas.
   - **Desviación razonada.** La auditoría pide «percentil dentro de su industria». Los datos gratuitos de Damodaran
     traen el agregado de cada industria, no la distribución por empresa: no hay percentil sin datos de pago, así que
     se compara con el agregado.
3. **ROE con apalancamiento alto.** Con un D/E por encima del umbral de su sector (`debt_equity_high`), puntúa el ROIC
   en el sitio del ROE, con las mismas bandas («ROIC (en lugar del ROE: apalancamiento alto)»).

**Golden: 11 de 43 cambian; 2 de nivel de calidad.**

| Juego | Ticker | Cambio | Causa | Justificación financiera |
|---|---|---|---|---|
| panel | NEE | calidad sólida → **media** (69 → 56); Rentabilidad 20 → 10 | ROE → ROIC por el D/E (puntúa −4 en lugar de +6); tope de 10/20 por diferencial negativo. | Es el caso de la auditoría: «destruye valor» y «rentabilidad excelente» en la misma página. El ROE del 18,8 % lo sostenía el apalancamiento. |
| panel | AMZN | calidad media → **sólida** (60 → 66); Rentabilidad 15 → 20 | Margen operativo y neto frente a su industria (Retail (General), 6,8 % operativo): de +1 a +5 (11,5 %, 1,7 veces) y de 0 a +3. | Un margen operativo del 11,5 % es bajo en absoluto, pero alto en el comercio minorista. La regla absoluta castigaba a la industria, no a la empresa. |
| panel | DUK | calidad 74 → 66; Rentabilidad 16 → 10 | ROE → ROIC por el D/E y tope de 10/20. | Igual que NEE. |
| panel | TM | calidad 68 → 65; Rentabilidad 8 → 6 | ROE → ROIC (D/E con la financiera cautiva) y tope de 6/20 (diferencial < −3 pp). Sus márgenes suben frente a Auto & Truck. | — |
| panel | BAC, BCS, HSBC, BRK-B | calidad −1 a −4 | Margen neto frente a su industria: el agregado de los bancos ronda el 27–29 %, y el «excelente» absoluto (≥ 20 %) ya no aplica. | El margen neto de un banco solo dice algo frente a otros bancos. |
| panel | SHEL, FCX; local FCX | calidad −2 | Margen operativo frente a su industria: de +1 a −1 (SHEL) y de +3 a +1 (FCX). | — |

**Las 26 de la auditoría con datos reales.** Corridas «e9_antes» y «e9», seguidas; los precios varían menos de un
0,2 %. Rentabilidad y calidad:

| Ticker | Rentabilidad | Calidad | Causa |
|---|---|---|---|
| NEE | 20 → **6** | sólida 66 → **media 49** | Diferencial de −3,8 pp: tope de 6/20. Además, ROE → ROIC por el D/E (1,87). |
| AWK | 19 → **10** | sólida 76 → 65 | Diferencial de −0,9 pp: tope de 10/20. |
| KMI | 16 → **10** | media 54 → 46 | Diferencial de −0,6 pp: tope de 10/20; ROE → ROIC. |
| VZ | 20 → **14** | sólida 65 → **media 58** | ROE (15,2 %) → ROIC por el D/E (1,59); margen neto (11,4 %) frente al de Telecom. Services (14,2 %): de +2 a 0. |
| UNH | 9 → **20** | media 52 → **sólida 66** | Márgenes frente a Healthcare Support Services, cuyo agregado es del 3,0 % operativo y el 1,25 % neto: UNH está en 1,6 y 2,6 veces. Con denominadores tan bajos, la ratio se amplifica; el deterioro de su margen en el tiempo no es materia de E9, sino de E7 (DCF) y E11 (confianza). |
| AMZN | 15 → **20** | media 60 → **sólida 66** | Como en el panel. |
| WMT | 11 → 15 | excelente 81 → 86 | Margen operativo del 4,4 % frente al 6,8 % de Retail (General): de −3 a −1. |
| FCX | 19 → 17 | sólida 72 → 70 | Margen operativo frente a su industria. |
| BA | 0 → 5 | débil 19 → 25 | ROE de −76 % con D/E 7,89 (patrimonio casi nulo): puntúa el ROIC (11,6 %, +2) en lugar del ROE; margen operativo frente a Aerospace/Defense (0,54 veces). |

El resto no cambia. Ningún nivel de precio cambia. Los cuatro casos de la auditoría quedan así: NEE 6/20, AWK 10/20,
KMI 10/20 y VZ 14/20. VZ tiene ahora el diferencial positivo (+1,7 pp con el Ke de E1), así que no lleva tope.

## E8 (ajuste) · Criterio (5) de la fiabilidad del DCF: crecimiento proyectado con el margen en caída

**Causa.** Decisión del PM del 27-oct. La fiabilidad del DCF resta un escalón si se cumplen las tres condiciones:

- el DCF proyecta g ≥ 0;
- el margen operativo TTM (o el neto) está ≥ 20 % por debajo de su mediana de 5 ejercicios de EDGAR;
- el margen baja en al menos 3 de los 4 últimos cambios anuales.

Con una caída ≥ 40 %, la fiabilidad es baja directamente. El texto lo declara: «supuesto no verificado hasta el DCF de
tres impulsores» (E7, Fase B). La calibración, con los 69 casos, está en `F8_AUDITORIA_REGISTRO.md`.

**Golden: 0 de 43 cambian.**

**Con datos reales:** solo UNH.

| Ticker | E8 → ajuste | Causa |
|---|---|---|
| UNH | atractivo (crudo 75) → **razonable** (crudo 65, confianza media) | Margen operativo TTM del 4,8 % frente a una mediana de 8,3 % (FY2021–FY2025): −42 %, 3 bajadas en 4 años, con el DCF creciendo al 11,4 %. La fiabilidad pasa a baja: el DCF (+67 %) deja de puntuar y entra el inverso. Es el caso que la auditoría marca como no utilizable. |

## E9 (ajuste del PM) · Márgenes frente a la industria en puntos porcentuales, no en ratio

**Causa.** Con la ratio empresa ÷ industria, UNH subía de 9 a 20 en Rentabilidad. Su margen operativo, hundido un 42 %,
era 1,6 veces el 3,0 % agregado de Healthcare Support Services. Con denominadores pequeños la ratio se amplifica, y
una empresa de margen bajo en una industria de margen bajo leía mejor que una de margen alto en una de margen alto.

**Regla.** Los márgenes se comparan en puntos porcentuales: margen de la empresa − margen agregado de la industria.
Los tramos están en config por tipo de margen y salen de los cuantiles de 69 casos:

- operativo: +15 / +5 / −2 / −8 pp;
- neto: +12 / +4 / −3 pp.

**Por qué puntos y no una ratio con suelo:** el suelo añade un parámetro arbitrario y por encima de él la ratio se
sigue amplificando. Los puntos porcentuales leen igual una diferencia en cualquier industria. Con la prueba de cordura
del PM (igual diferencia relativa, 1,6 veces), la empresa de margen bajo en una industria de margen bajo saca menos.

**Golden: 11 de 43 cambian frente a E9 con ratio; 4 de nivel de calidad.**

| Juego | Ticker | Cambio | Causa |
|---|---|---|---|
| panel | AMZN | calidad sólida → **media** (66 → 60); Rentabilidad 20 → 15 | Margen operativo del 11,5 % frente al 6,8 % de Retail (General): +4,7 pp, «en línea» (+1) en lugar de 1,7 veces, «excepcional» (+5). Margen neto: de +3 a 0. |
| panel | MC.PA | calidad excelente → **sólida** (80 → 78) | Margen neto frente a su industria en puntos. |
| panel | XOM | calidad excelente → **sólida** (81 → 79) | Margen operativo del 10,7 % frente al 14,3 % de su industria: −3,5 pp («por debajo», −1). |
| panel | TM | calidad sólida → **media** (65 → 62) | Márgenes frente a Auto & Truck en puntos: de +3 a +1 y de +3 a +2. |
| panel | SHEL, BCS, HSBC, JNJ, UL; panel y local JPM | calidad −1 a −3 | Márgenes frente a su industria en puntos. |

**Con datos reales** (corridas «e9b_antes» y «e9b», seguidas; los precios varían menos de un 0,3 %). Los casos que
pidió el PM:

| Ticker | Margen operativo frente a la industria | Margen neto frente a la industria | Rentabilidad | Calidad |
|---|---|---|---|---|
| UNH | 4,8 % frente a 3,0 %: +1,8 pp («en línea», +1) | 3,1 % frente a 1,25 %: +1,9 pp (0) | 20 → **15** | sólida 66 → **media 60** |
| WMT | 4,4 % frente a 6,8 %: −2,4 pp (−1) | 3,0 % frente a 5,6 %: −2,6 pp (0) | 15 → 15 | excelente 86 (sin cambio) |
| MSFT | 46,8 % frente a 33,0 %: +13,8 pp (+3) | 40,3 % frente a 25,5 %: +14,8 pp (+3) | 20 → 20 | excelente 95 |
| NVDA | 65,2 % frente a 35,3 %: +29,9 pp (+5) | 63,7 % frente a 30,4 %: +33,2 pp (+3) | 20 → 20 | excelente 93 |
| KO | 29,6 % frente a 20,5 %: +9,1 pp (+3) | 28,6 % frente a 13,4 %: +15,2 pp (+3) | 20 → 20 | excelente 81 |
| COST | no está en las 26 de la auditoría ni en los golden | — | — | — |

Además:

- AMZN: Rentabilidad 20 → 15; calidad sólida → media (60).
- XOM: Rentabilidad 18 → 16; calidad excelente → sólida (79).
- JPM y CB: Rentabilidad 20 → 18; siguen en excelente.

Ningún nivel de precio cambia.

## E11 · La más baja manda, la calidad se contrae con confianza baja, y «excelente» desde 85

**Causa (auditoría §3 E11).**

- MRNA tenía «cobertura de datos: baja» y confianza «media», aunque la metodología dice «la más baja manda».
- XOM tenía confianza baja y calidad 82, «excelente», sin contraer.
- Había saturación: 14 de 26 informes con calidad de 80 o más, y GOOGL en 100.

**Reglas.**

1. **La más baja manda.** Ninguna dimensión evaluada (convergencia, cobertura, fuente o estabilidad) puede quedar por
   debajo de la confianza final. Es genérico: la cobertura entra, venga de donde venga su bajada, sin leer
   `data_provenance.staleness`. Sustituye a `weak_dimension_cap`, que solo bajaba a «media».
2. **Con confianza baja, la calidad se contrae hacia 50:** mostrada = 50 + (cruda − 50) × 0,85. Con confianza media o
   alta no se contrae, porque la convergencia de métodos es del precio. La comprobación de Ke también aplica la
   contracción cuando baja la confianza a «baja».
3. **«Excelente» desde 85** (`score.quality.bands`), solo por el hallazgo de saturación. Sigue la cautela del PM:
   - El pasaje de la auditoría, en el mismo párrafo: «Saturación: 14 de 26 informes tienen calidad de 80 o más, y
     GOOGL llega a 100». Entre las soluciones propone «subir el umbral de "excelente" en lugar de partir de 10/20 y
     sumar hasta el techo».
   - Comprobado primero si E9 y la contracción bastaban, en los 68 casos con calidad (26 de la auditoría en vivo y
     42 golden; SPY no tiene calidad), con `tools/f8_quality_bands.py e11_antes e11 996cd7be`:

     | Escenario | excelente | sólida | media | débil |
     |---|---|---|---|---|
     | Antes de E11 (umbral 80) | 32 (47 %) | 18 (26 %) | 14 (21 %) | 4 (6 %) |
     | E11 con umbral 80 | 29 (43 %) | 20 (29 %) | 15 (22 %) | 4 (6 %) |
     | **E11 con umbral 85** | **17 (25 %)** | 32 (47 %) | 15 (22 %) | 4 (6 %) |

     E9 y la contracción solo bajan «excelente» del 47 al 43 %: sigue siendo la banda más poblada y no discrimina. La
     contracción solo saca de «excelente» a quien tiene una cruda por debajo de 85 aproximadamente.
   - 85 es el p75 de las calidades con E11 (p50 76, p90 95): «excelente» queda como el cuartil superior.
   - **Quién deja «excelente»:** 15 de los 32 casos. La contracción sola no lo explica.

     | Motivo | Casos |
     |---|---|
     | La contracción sola (queda por debajo de 80) | CAT (en vivo y golden) 84 → 79; MCD (en vivo) 81 → 76 |
     | La contracción y el umbral (contraída a 80–84) | ASML (en vivo y golden) 90 → 84; MU 90 → 84; LLY (en vivo) 89 → 83; CB (en vivo) 87 → 81; NVO 85 → 80 |
     | Solo el umbral 85 (misma puntuación) | JNJ 84; PGR 83; KO (en vivo y golden) 81; LIN (en vivo) 81; UL 80 |

     Siguen en «excelente» 17: en vivo GOOGL, SAP, MSFT, NVDA, JPM y WMT; en los golden V, PLTR, MSFT, NVDA, TSM, JPM,
     NFLX y PG, más JPM, V y NFLX locales.
   - Es una regla general en config; ninguna empresa recupera un nivel anterior.
   - **Solo cambia la etiqueta.** El codo de la persistencia era el umbral de «excelente» y se separa en su clave
     (`quality_persistence.knee = 80`). En el WIP, subir el umbral a 85 aflojaba la persistencia y subía la calidad de
     KO, SAP, LLY, CB, ASML y NVDA de 1 a 2 puntos. Comprobado: la calidad de E11 coincide en los 46 golden y en las
     26 en vivo con la de antes contraída según la confianza nueva. Hay test.

**Golden: 24 de 43 cambian.**

| Causa | Golden | Cambio |
|---|---|---|
| La más baja manda: estabilidad «baja» (cíclica) → confianza baja → calidad y precio se contraen | ASML | calidad 90 → 84, **excelente → sólida**; precio muy exigente → **exigente** |
| | CAT | 84 → 79, **excelente → sólida**; precio muy exigente → **exigente** |
| | MU | 90 → 84, **excelente → sólida**; precio muy exigente → **exigente** |
| | SHEL | 71 → 68; precio atractivo → **razonable** |
| | FCX (panel y local) | 70 → 67 |
| | DOW | 18 → 23; la contracción sube hacia 50 a una débil y sigue débil |
| La más baja manda: convergencia «baja» (P/B frente al sector y P/B justificado en direcciones opuestas) → confianza baja | BAC | 70 → 67 |
| La más baja manda deja la confianza en «media» y la comprobación de Ke la baja a «baja» | HSBC | 70 → 67; precio exigente → **razonable** |
| | NVO | 85 → 80, **excelente → sólida**; precio atractivo → **razonable** |
| | NFLX (local) | 93 → 87; precio atractivo → **razonable** |
| La más baja manda: calidad de fuente «media» (P/E implausible, ítems inferidos) → confianza alta → **media** | CRWD | precio 5 → 16, sigue muy exigente |
| Ya tenían confianza baja: ahora se contrae la calidad | TSM | 99 → 92 |
| | NFLX (panel) | 93 → 87 |
| | XOM | 79 → 75 |
| | MC.PA | 78 → 74 |
| | BCS | 69 → 66 |
| | BRK-B | 70 → 67 |
| | NEE | 56 → 55 |
| | DUK | 66 → 64, **sólida → media** |
| Umbral 85, solo la etiqueta | JNJ (84), KO (81), PGR (83), UL (80) | **excelente → sólida** |

**Con datos reales** (corridas «e11_antes» y «e11», seguidas):

- **Cambios en las 26 de la auditoría:**
  - **MRNA** (el caso de la auditoría): confianza media → **baja** por la más baja manda (cobertura baja); calidad
    33 → 36, débil.
  - **XOM** (el caso de la auditoría): confianza baja; calidad 79 → **75**, contraída.
  - **ASML**: confianza media → baja (estabilidad baja); calidad 90 → 84, **excelente → sólida**; precio muy
    exigente → exigente.
  - **CAT**: confianza media → baja (estabilidad baja); calidad 84 → 79, **excelente → sólida**; precio muy exigente → exigente.
  - **MCD**: confianza media → baja por la más baja manda (convergencia baja); calidad 81 → 76, **excelente → sólida**.
  - **FCX**: confianza media → baja (estabilidad baja); calidad 70 → 67.
  - **LLY**: confianza ya baja; calidad 89 → 83, **excelente → sólida**.
  - **CB**: confianza ya baja; calidad 87 → 81, **excelente → sólida**.
  - **BA**: confianza ya baja; calidad 25 → 29, débil.
  - **KO** (81) y **LIN** (81): **excelente → sólida**, solo por el umbral.
- **Siguen en «excelente»:** GOOGL 100, SAP 96, MSFT 95, NVDA 93, JPM 89 y WMT 86. Antes eran 13 de 26; ahora, 6.
- **Sin cambio de nivel:** AMZN, AWK, KMI, NEE, O, PLD, UNH, UNP y VZ.

**Textos.**

- El resumen ejecutivo y la sección 01 dicen ahora si la confianza contrae la calidad. Antes decían siempre «la calidad
  no se contrae». Ejemplo: «Contrae hacia 50 el atractivo del precio (de X a Y) y la calidad del negocio (de A a B)».
- El tooltip de la confianza pasa a «la calidad del negocio, solo si la confianza es baja».
- La escala de calidad del PDF y de /v2 lee las bandas del motor: «sólida 65–85 · excelente 85+».
- **Marcas de la escala en /v2**, medidas en los 4 proyectos y en las tres escalas (ninguna baja de 12 px):
  - En móvil e iPhone no se enseñan (tarjeta compacta).
  - En escritorio caben centradas: sin solapes, como antes.
  - En tablet (iPad, tarjeta de 229 px) la marca «excelente 85+», centrada en un tramo del 15 %, se salía 6,8 px de la
    tarjeta. Una regla de `v2.css`, solo en ese ancho, la alinea al borde. Ya no se sale, pero solapa 24 px con
    «sólida».
  - En tablet ya había solapes antes de E11: calidad 6,6 px, y el precio 15 a 17 px entre «muy exigente», «exigente» y
    «razonable».
  - Las cuatro marcas no caben a 12 px en 229 px con ninguna colocación: con columnas iguales siguen solapando 4 px.
    Hace falta un diseño propio para tablet (E3).
- Tests ajustados a las reglas nuevas, sin cambiar lo que comprueban:
  - `test_cost_of_capital` (la más baja manda);
  - `test_quality_price` y `test_pdf_v2_parts` (umbral 85);
  - `scale.test.ts`, `confidence.test.ts` y `CompanyHeader.test.tsx`; en este último solo cambia «Excelente desde 85».
- El guardián `quality_persistence` compara la frase «X → Y» con la calidad tras la persistencia (`score_raw`), no con
  la ya contraída.

## E10 (peso en el score) · Altman pasa de [+6, −2, −6] a [+3, −1, −3]

**Causa (auditoría §3 E10).** «Peso en el score: bajar el +6 de Altman, porque su validez predictiva cae fuera de la
muestra original (precisión de alrededor de 0,75 según Altman y otros, 2017)». El +6 era el componente más pesado de
Solidez: los demás son el current ratio ±4, el D/E ±5 y la cobertura de intereses ±3, sobre una base de 10 y un techo
de 20.

**Regla** (aprobada por el PM el 27-oct). El peso se escala por su poder discriminante fuera de muestra:

- El AUC ronda 0,75 (Altman, Iwanicz-Drozdowska, Laitinen y Suvas, 2017, *Financial Distress Prediction in an
  International Context: A Review and Empirical Analysis of Altman's Z-Score Model*, JIFMA 28(2)).
- La información por encima del azar es 2·AUC − 1 = 0,5, así que el peso se reduce a la mitad: [+3, −1, −3], el mismo
  que la cobertura de intereses.
- La neutralidad no cambia: «referencial» puntúa 0, y «no aplica» y «sin dato» quedan fuera de la cobertura y se
  reescalan como antes.
- El runway (GROWTH_PRE_PROFIT) conserva [+6, +2, −2, −6]: la rebaja de Altman es por su validez estadística fuera de
  muestra y el runway es caja medida, no un modelo.
- Ni la variante por SIC ni las exclusiones de E10 se tocan aquí: van en `fiabilidad/f8-independientes`.

**Solidez en los 69 casos** (`tools/f8_solidez_bands.py e10p_antes e10p b86b588d`; tonos de una categoría según
`category_tone_bounds`):

| Peso | 20/20 (techo) | positivo (≥ 12) | aviso (8–11) | negativo (< 8) | sin dato |
|---|---|---|---|---|---|
| Antes [6, −2, −6] | 21 | 34 | 7 | 6 | 1 |
| Después [3, −1, −3] | 16 | 39 | 8 | 5 | 1 |

- **Zonas de Altman en los 69:** 34 en zona segura, 5 en zona gris, 3 en zona de peligro, 4 referenciales (no
  puntúan) y 23 sin Altman (financieras, REIT o sin dato).
- **Zona segura, de +6 a +3:** pierden 3 puntos, o menos si su Solidez sin tope pasaba de 20.
  - Seis dejan el techo o cambian de tono: CAT (en vivo y golden), JNJ y PG pasan de 20 a 18; MRNA (en vivo) de 20
    a 17; UNP (en vivo) de 12 a 9, de positivo a aviso.
  - El resto pierden 3 sin cambiar de tono: V, ASML, TM, KO, NVO, UL, LIN, LLY y SAP.
- **Zona gris, de −2 a −1:** AAPL y CRWD de 10 a 11; SHEL de 11 a 12, de aviso a positivo; UNH (en vivo) de 7 a 8,
  de negativo a aviso; VZ (en vivo) de 2 a 3.
- **Zona de peligro, de −6 a −3:** DOW de 0 a 2.

**Calidad.** «Excelente» (≥ 85) pasa de 17 a 16 de 68 casos. Solo **PG** cambia de nivel: de excelente 85 a
**sólida 82**, por Solidez de 20 a 18.

**Golden: 14 de 43 cambian.** Solo cambia la calidad; el precio y la confianza, no.

| Golden | Calidad |
|---|---|
| V (panel y local) | 96 → 92 |
| ASML, JNJ | 84 → 81 |
| CAT | 79 → 76 |
| KO | 81 → 79 |
| NVO, UL | 80 → 76 |
| TM | 62 → 59 |
| PG | 85 → **82, sólida** |
| AAPL, CRWD, DOW, SHEL | suben 1 (zonas gris y de peligro) |

**Con datos reales** (corridas «e10p_antes» y «e10p», seguidas), ningún cambio de nivel:

- bajan: SAP 96 → 92, ASML 84 → 81, CAT 79 → 76, KO 81 → 79, LIN 81 → 78, LLY 83 → 81, UNP 75 → 71, MRNA 36 → 31;
- suben: UNH 60 → 61, VZ 58 → 59.

**Tests ajustados a los datos nuevos:**

- `CompanyHeader.test.tsx` (E3): la Solidez de AAPL, 10 → 11 (zona gris −1).
- `test_coverage`: mid_full, Solidez 8 → 9.
- `test_pdf_v2_parts`: AAPL 76.
- `test_pdf_v2_report`: la nota de calidad en el resumen pasa de KO a MU, porque KO (79) ya no pasa el codo de la
  persistencia y no lleva nota.

> **Evidencia fuera de `main` (E6, 31-oct):** las capturas (`docs/rediseno/capturas-*`), `docs/fiabilidad/f8_evidencia/` y los volcados JSON de escaneo y medida de `docs/` no están en `main`. Siguen en las ramas locales del rediseño y de la fiabilidad (`rediseno/v4-f8`) y en el archivo `v4_evidencia_8e4f3952.tar.gz` de `/Users/joseestebanroa/Downloads/finanzer_next-archivo`, fuera del repositorio.
