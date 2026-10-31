# Verificación del margen operativo con dos verdades (29-oct-2026)

Las 28 empresas de la regla `margen_operativo_unico` (puerta de la v4, `PUERTA_V4_2026-10-29.md`) que no se explican
por los cargos que ya identifica la normalización. Cada una se comparó con los propios estados en SEC EDGAR
(companyfacts: los 4 trimestres del TTM del análisis, cada uno con su valor de 3 meses, o el Q4 como ejercicio − 9
meses), con los análisis guardados del escaneo de la puerta. Herramienta: `backend/tools/verif_margen_operativo.py`.
Solo lectura: ningún cambio en el motor.

## Corrección previa: qué es cada margen

La regla y la puerta tenían los rótulos al revés:

- **El margen que se enseña y puntúa** (`key_metrics.operating_margin`) es el de **EDGAR**: `OperatingIncomeLoss`,
  ejercicio + acumulado del año − acumulado del año anterior (`data_provenance.fields.operatingIncome`), sobre los
  ingresos TTM de Yahoo. Sin TTM trimestral, es el `operatingIncome` de quoteSummary de Yahoo.
- **La «suma trimestral»** de las piezas de N1/N1b es la de las 4 filas «Operating Income» de los estados
  trimestrales de **Yahoo**. No es EDGAR.

Hay que corregir el texto de la regla `margen_operativo_unico` y el de la puerta.

## Resumen

| Quién acierta (frente al operativo presentado en EDGAR) | Empresas |
|---:|---|
| **Nuestro constructor de EDGAR**: Yahoo trimestral es otra cifra | **20**: ALB, BA, BAX, BEN, CPAY, DIS, ECHO, EL, GPN, NSC, NXPI, ON, SHOP, SJM, SOLV, SPGI, T, TROW; D y V con el último 10-Q leído del filing |
| **Yahoo trimestral**: nuestro constructor falla | **2**: FIX (etiqueta anual en un 10-Q) e IFF (acumulado reexpresado con un ejercicio sin reexpresar) |
| **Ninguna** | **2**: HON (perímetro cambiado por las escisiones) y SKYD (estados de FY2024 de la antecesora) |
| **Sin TTM trimestral**: el enseñado sale de quoteSummary; las piezas (estados) cuadran con EDGAR | **3**: CRL, FDXF, BTI |
| Sin verificar | **1**: DEO (el 20-F de FY2026 no está en companyfacts) |

FIX: el 16,7 % es el bueno (2.095 M$ sobre 12.543 M$). Lo da el ejercicio del 10-K (1.315 M$) y no la etiqueta del
10-Q (209 M$).

## Reglas generales

**Para nuestro constructor de EDGAR** (`sec_edgar.flow_ttm` y quien lo use):

1. **Un periodo de un ejercicio (≥ 350 días) nunca de un informe trimestral** (10-Q, 10-Q/A, 6-K).
   - Un 10-Q no presenta ejercicios: si trae uno, es un error de etiquetado del emisor.
   - Hoy `_current` toma el último presentado por (inicio, fin), y el 10-Q, por ser posterior al 10-K, gana.
   - El frame `CY2025` de la SEC tampoco sirve: es el valor erróneo.
   - Caso: FIX.
   - Corregido tras el escaneo de comprobación del 29-oct: la primera versión decía «solo de un informe anual», y
     eso deja sin ejercicio a VRSN. En companyfacts, su beneficio neto anual solo aparece en el DEF 14A (la tabla de
     «pay versus performance» repite los ejercicios), que por ser posterior al 10-K gana la deduplicación. La regla
     es excluir los trimestrales, no exigir un anual.
2. **Cada pieza del TTM en la misma base que el ejercicio.**
   - El acumulado del año anterior debe ser el que se presentó con su periodo (el 10-Q del año anterior), no el
     comparativo reexpresado de un 10-Q posterior. Si no, una reexpresión (discontinuadas, cargos reclasificados)
     entra a medias.
   - Comprobación: TTM = Σ de los 4 trimestres (3 meses, o Q4 = ejercicio − 9 meses del mismo informe), con ±1 pp
     de los ingresos.
   - Caso: IFF (−291 M$ frente a 754 M$).
3. **Cambio de perímetro: si el comparativo del año anterior no coincide con el original, hay reexpresión.**
   - Si además cambian los ingresos (escisión, discontinuadas: HON, 33,6 B$ en EDGAR frente a 30,7 B$ de TTM), el TTM
     mezcla perímetros.
   - Hay que usar la base del perímetro vigente (la regla de perímetro de F3 · T5) o declararlo. Nunca la cifra
     mezclada.
4. **Sin TTM trimestral, una sola fuente.**
   - El margen operativo debe salir de los mismos estados que el resto (el ejercicio de EDGAR o de los estados
     anuales), con su periodo dicho. Nunca del `operatingIncome` de quoteSummary, que es otra definición o periodo:
     CRL 604 frente a 25 M$, FDXF −508 frente a 540 M$, BTI.
   - Con estados desfasados (SKYD: FY2024 de la antecesora, en octubre de 2026), declarar o descartar. La regla de
     estados desfasados no lo cubre porque no hay EDGAR del corte.
5. **El último trimestre leído del filing** (pendiente en companyfacts: D, V): vale, pero con la comprobación de la
   regla 2.

**Para la fuente de Yahoo:**

6. **El «Operating Income» trimestral de Yahoo no es el operativo presentado.**
   - En 18 de las 20 en que acierta nuestro EDGAR, Yahoo da otra cifra. Lo inferido: saca partidas no recurrentes,
     cargos (Yahoo más alto) y ganancias (más bajo: BA, SOLV). No está verificado partida a partida.
   - Las piezas de N1/N1b se construyen con ella: el techo de la normalización ya parte de un operativo «limpio» según
     Yahoo.
   - Para una sola verdad: el operativo presentado de EDGAR y, aparte, las partidas no recurrentes que quita nuestra
     normalización, dichas (como el margen neto). Yahoo trimestral solo como respaldo sin EDGAR, y declarado.
7. **Ganancias por venta de negocios dentro del operativo** (SOLV, BA: por verificar en sus 10-Q). Hay que
   identificarlas (en EDGAR, `GainLossOnSaleOfBusiness`, `GainLossOnDispositionOfAssets` y las de los grupos
   enajenados) y quitarlas del margen operativo que puntúa, como los cargos.

**Cuándo descartar o declarar:**

- **TTM de EDGAR que no cuadra con la suma de sus trimestres** (>1 pp de los ingresos): usar la suma de los 4
  trimestres si todos están en la misma base; si no, declarar «TTM de EDGAR no homogéneo», no puntuar con la cifra
  mezclada y usar el respaldo declarado.
- **Reexpresión por perímetro:** declarar el perímetro y medir solo sobre el vigente.
- **Emisor con 20-F semestral** (BTI, DEO): el ejercicio, con su periodo dicho.
- **Estados de una antecesora o desfasados** (SKYD): declarar o descartar.

## Tabla

Márgenes sobre los ingresos TTM del análisis. «Correcto»: el operativo presentado en EDGAR para los 4 trimestres del
TTM (o el ejercicio, donde no hay TTM).

| Empresa | Correcto (EDGAR, 4 trimestres o ejercicio) | Nuestro (enseñado, puntúa) | Yahoo trimestral (piezas N1/N1b) | Acierta | Causa |
|---|---:|---:|---:|---|---|
| ALB | 252 M (4,3 %) | 4,3 % | 13,7 % | nuestro EDGAR | El operativo presentado cuadra con sus trimestres; el «Operating Income» trimestral de Yahoo es otro (más alto: inferido, saca cargos; no verificado partida a partida) |
| BA | 4.268 M (4,6 %) | 4,6 % | −5,9 % | nuestro EDGAR | El operativo presentado cuadra con sus trimestres; Yahoo queda en −5,9 % (inferido: saca una ganancia por venta de negocios; por verificar en el 10-Q) |
| BAX | −274 M (−2,4 %) | −2,4 % | 1,8 % | nuestro EDGAR | El operativo presentado cuadra con sus trimestres; el «Operating Income» trimestral de Yahoo es otro (más alto: inferido, saca cargos; no verificado partida a partida) |
| BEN | 906 M (9,7 %) | 9,7 % | 14,0 % | nuestro EDGAR | El operativo presentado cuadra con sus trimestres; el «Operating Income» trimestral de Yahoo es otro (más alto: inferido, saca cargos; no verificado partida a partida) |
| BTI | 9.997 M GBP | 34,9 % | 38,2 % | las piezas (≈ EDGAR en GBP) | Sin TTM (20-F semestral, IFRS): quoteSummary convertido de GBP da 12.060 M; el ejercicio de EDGAR (9.997 M GBP) ≈ las piezas (13.184 M USD) |
| CPAY | 2.196 M (43,7 %) | 43,7 % | 40,5 % | nuestro EDGAR | El operativo presentado cuadra con sus trimestres; el «Operating Income» trimestral de Yahoo es otro (más bajo: inferido, saca ganancias u otros ingresos; no verificado partida a partida) |
| CRL | 25 M (0,6 %) | 15,1 % | 0,6 % | las piezas (estados de yfinance = EDGAR) | Sin TTM trimestral: el margen enseñado sale del operatingIncome de quoteSummary (604 M, sin el deterioro); el ejercicio presentado en EDGAR es 25 M |
| D | (último trimestre fuera de companyfacts) | 21,1 % | 28,1 % | nuestro EDGAR (último 10-Q leído del filing) | El último trimestre aún no está en companyfacts; nuestro constructor lo lee del 10-Q (pendiente). Yahoo reclasifica partidas (utility) |
| DEO | — | 27,0 % | 16,1 % | sin verificar | Sin TTM (20-F, ejercicio a junio): el 20-F de FY2026 no está aún en companyfacts; quoteSummary 5.311 M frente a 3.156 M de los estados |
| DIS | 18.238 M (18,4 %) | 18,4 % | 15,2 % | nuestro EDGAR | El operativo presentado cuadra con sus trimestres; el «Operating Income» trimestral de Yahoo es otro (más bajo: inferido, saca ganancias u otros ingresos; no verificado partida a partida) |
| ECHO | −16.516 M (−112,7 %) | −112,7 % | 7,1 % | nuestro EDGAR | El operativo presentado cuadra con sus trimestres; el «Operating Income» trimestral de Yahoo es otro (más alto: inferido, saca cargos; no verificado partida a partida) |
| EL | 780 M (5,2 %) | 5,2 % | 11,1 % | nuestro EDGAR | El operativo presentado cuadra con sus trimestres; el «Operating Income» trimestral de Yahoo es otro (más alto: inferido, saca cargos; no verificado partida a partida) |
| FDXF | 540 M (6,1 %) | −5,8 % | 6,1 % | las piezas (estados de yfinance = EDGAR) | Sin TTM trimestral: quoteSummary da −508 M; el ejercicio FY2026 presentado en EDGAR es 540 M (escisión reciente) |
| FIX | 2.095 M (16,7 %) | 7,9 % | 16,7 % | Yahoo trimestral | Etiquetado del emisor: su 10-Q del Q1 de 2026 pone el trimestre comparativo de 2025 (209 M) con el periodo del ejercicio entero; por ser posterior al 10-K (1.315 M), nuestro constructor lo toma como ejercicio 2025 (y el frame CY2025 de la SEC también) |
| GPN | 1.269 M (12,4 %) | 12,8 % | 9,7 % | nuestro EDGAR | El operativo presentado cuadra con sus trimestres; el «Operating Income» trimestral de Yahoo es otro (más bajo: inferido, saca ganancias u otros ingresos; no verificado partida a partida) |
| HON | no homogéneo | 27,9 % | 16,2 % | ninguna | Cambio de perímetro (escisiones): los acumulados de 2025 que trae 2026 están reexpresados sin lo escindido y el ejercicio 2025 no; el Q4 derivado sale 5.564 M y los ingresos de EDGAR (33,6 B) no son los del TTM de Yahoo (30,7 B). El TTM mezcla perímetros |
| IFF | 754 M (7,6 %) | −2,9 % | 8,0 % | Yahoo trimestral (≈) | Reexpresión: el 10-Q del Q2 de 2026 reexpresa el primer semestre de 2025 (−705 → +320 M; el cargo del Q1 de 2025 sale del operativo); el ejercicio del 10-K no está reexpresado (−382): FY + acumulado − acumulado reexpresado = −291 M |
| NSC | 4.088 M (31,5 %) | 31,5 % | 35,8 % | nuestro EDGAR | El operativo presentado cuadra con sus trimestres; el «Operating Income» trimestral de Yahoo es otro (más alto: inferido, saca cargos; no verificado partida a partida) |
| NXPI | 4.548 M (33,0 %) | 33,0 % | 28,6 % | nuestro EDGAR | El operativo presentado cuadra con sus trimestres; el «Operating Income» trimestral de Yahoo es otro (más bajo: inferido, saca ganancias u otros ingresos; no verificado partida a partida) |
| ON | 670 M (10,8 %) | 10,8 % | 18,0 % | nuestro EDGAR | El operativo presentado cuadra con sus trimestres; el «Operating Income» trimestral de Yahoo es otro (más alto: inferido, saca cargos; no verificado partida a partida) |
| SHOP | 1.844 M (13,9 %) | 13,9 % | 17,8 % | nuestro EDGAR | El operativo presentado cuadra con sus trimestres; el «Operating Income» trimestral de Yahoo es otro (más alto: inferido, saca cargos; no verificado partida a partida) |
| SJM | 826 M (9,0 %) | 9,0 % | 19,7 % | nuestro EDGAR | El operativo presentado cuadra con sus trimestres; el «Operating Income» trimestral de Yahoo es otro (más alto: inferido, saca cargos; no verificado partida a partida) |
| SKYD | −5.269 M (FY2024) | 9,3 % | −18,1 % | ninguna (periodo desfasado) | Sin TTM: los estados son de FY2024 (antecesora, −5.269 M en EDGAR) y quoteSummary da 2.720 M de otra base; empresa resultante de una fusión de 2025 |
| SOLV | 2.076 M (25,0 %) | 25,0 % | 6,3 % | nuestro EDGAR | Un trimestre de 1.690 M (Q3 de 2025) en el operativo presentado: por su fecha, la ganancia de la venta del negocio de filtración (por verificar en el 10-Q); Yahoo la saca |
| SPGI | 7.772 M (48,8 %) | 47,9 % | 42,7 % | nuestro EDGAR | El operativo presentado cuadra con sus trimestres; el «Operating Income» trimestral de Yahoo es otro (más bajo: inferido, saca ganancias u otros ingresos; no verificado partida a partida) |
| T | 23.579 M (18,3 %) | 18,3 % | 21,4 % | nuestro EDGAR | El operativo presentado cuadra con sus trimestres; el «Operating Income» trimestral de Yahoo es otro (más alto: inferido, saca cargos; no verificado partida a partida) |
| TROW | 2.335 M (30,8 %) | 30,8 % | 34,4 % | nuestro EDGAR | El operativo presentado cuadra con sus trimestres; el «Operating Income» trimestral de Yahoo es otro (más alto: inferido, saca cargos; no verificado partida a partida) |
| V | (ídem) | 60,7 % | 65,6 % | nuestro EDGAR (último 10-Q leído del filing) | Igual que D; Yahoo, más alto (inferido: saca la provisión por litigios; no verificado) |
