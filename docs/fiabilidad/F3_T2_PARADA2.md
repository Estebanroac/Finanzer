# F3 · Punto de parada 2 (T2): clasificador por la historia real (D4)

> Fase 3 del plan de fiabilidad. Rama `fiabilidad/f3-metodo` (worktree `../finanzer_next-f3`). **Nada subido.**
> Medidas del 2026-10-17 en replay (fixtures del panel, sin red). La línea base es el commit `3966a43` (T1b cerrada).

## 0. Resumen

| | Antes (T1b) | Ahora |
|---|---|---|
| Ciclicidad | por la industria de Yahoo (listas de config) y una ventana de 4 ejercicios | por **8+ ejercicios de EDGAR**. Sin esa historia, la industria con confianza baja, y se dice |
| GROWTH_PROFITABLE | no existía | MSFT, NVDA, TSM, NVO y PLTR |
| Subtipos de FINANCIAL | no | banco (JPM, BAC, HSBC, BCS), aseguradora (PGR), conglomerado (BRK-B) |
| Frontera (un umbral movido ±20% cambia el arquetipo) | no | **5:** MSFT, KO, DOW, TM y NFLX, con confianza de clasificación baja y el motivo en el informe |
| Cambios de arquetipo en el panel | — | **8:** CAT y KO → CYCLICAL; TM → MATURE; MSFT, NVDA, NVO, PLTR y TSM → GROWTH_PROFITABLE |
| Suite sin golden | — | 3553 passed; **1 falla:** las muestras forzadas del contrato, que se regeneran con los golden |
| Golden | — | **70 cambian** (los dos juegos): pendientes de tu aprobación (§7) |

**Lo que te pido:**

1. **reabrir las medidas de ciclicidad del diseño** (§2): las de F3_DISENO §1.2 marcan cíclicas a KO, PG, JNJ, V,
   NVDA, PLTR, NFLX y AMZN. Propongo episodios repetidos de caída de ingresos y desplomes del BPA con caída de ventas;
2. **KO** (§3): sale cíclica, en la frontera. Hay que decidir qué hacer;
3. **aprobar los arquetipos línea a línea** (§5). Sin esa aprobación no sigo con la T3;
4. aprobar el diff de los golden, causa por causa (§7).

Siguen pendientes de la parada 1b: `SEC_EDGAR_USER_AGENT` en Render y el "ok, pushea".

## 1. Qué se hizo (un commit por causa, tests antes)

| Commit | Qué | Tipo |
|---|---|---|
| `dc62a83` | **Historia de EDGAR con dos campos nuevos:** operaciones discontinuadas (para cortar los cambios de perímetro) e ingresos de contratos con clientes. Estos últimos sirven para el subtipo financiero: ASC 606 y NIIF 15 excluyen los contratos de seguro. Fixtures ampliados | de fondo |
| `b07983c` | **Historia por acción ajustada por splits.** AAPL tenía una "caída" del 89% porque companyfacts guarda cada ejercicio con la cifra de su informe. El factor del split se lee en las reexpresiones de las **acciones**, no del BPA: AAPL reexpresó su BPA en 2009 por un cambio contable, con un cociente cercano a 3:2. **Errores de escala:** un salto de más de 100 veces se descarta y se declara (NVDA FY2008, acciones en miles) | de fondo |
| `9ea8193` | **Clasificador por la historia** (`lib/cyclicality.py`, `lib/classify.py`). Incluye ciclicidad, GROWTH_PROFITABLE, subtipos de FINANCIAL, frontera y la regla de industria con confianza baja cuando no hay historia | de fondo |
| `0ca5937` | **Nota de crecimiento estructural** (§1.1, paso 6): una cíclica que también crece con beneficio sigue siendo CYCLICAL, con la nota (MU, ASML) | de fondo |
| `ddd7796` | **Motivo concreto de la confianza baja.** Antes decía siempre "el tipo de empresa no está claro"; ahora dice "frontera" o "ciclicidad sin medir (N ejercicios en la SEC; hacen falta 8)" | de fondo |
| `4516eae` | **Rupturas del capital.** Si las acciones crecen ≥ 50% en un ejercicio (salida a bolsa con conversión de preferentes, o fusión pagada en acciones), la serie por acción se corta ahí, como un cambio de perímetro. Ver §4 | de fondo |
| `0f121bc` | **Alerta de posible cíclica medida con la historia** en FINANCIAL, REIT y UTILITY. Si la historia no muestra ciclo, la alerta desaparece (NEE, PLD); si lo muestra, la alerta dice dónde (HSBC). El arquetipo no cambia | de fondo |
| `9e76d50` | **Split entre taxonomías** en el BPA (TM, §8) | de fondo |
| `d2333b3` | Herramienta `tests/f3_t2_measures.py`: medidas y sensibilidad del panel | herramienta |

**Provisional, declarado.** GROWTH_PROFITABLE usa las herramientas de MATURE hasta la T3 (DCF inverso) y la T6:

- Rule of 40;
- FCF − SBC;
- PEG a 3 años.

Hasta entonces, sus calidad, precio y score son los de MATURE (comprobado: solo cambian la etiqueta y la confianza).

## 2. Reapertura: las medidas de ciclicidad del diseño (§1.2) fallan en el panel

**Regla del diseño.** Cíclica si se cumple cualquiera de estas, salvo que lo explique un cambio de perímetro:

- caída máxima de ingresos ≥ 20%;
- amplitud del margen operativo ≥ 1.0× su media;
- ≥ 2 años con caída del BPA > 50%.

Medida sobre la historia de EDGAR del panel:

| Ticker | Lo que dispara la regla del diseño | Por qué no es ciclo |
|---|---|---|
| KO | caída 31% | refranquicia de embotelladoras 2016–2018: menos ingresos, mismo negocio |
| PG | amplitud 1.60 | cargos puntuales (Gillette 2019) en un margen estable |
| JNJ | 2 desplomes del BPA (2017, 2024) | cargo fiscal de 2017; en 2024 el BPA vuelve a lo normal tras la plusvalía de Kenvue de 2023. Las ventas no cayeron |
| V | amplitud 2.05 | margen que se expande al crecer |
| NVDA | amplitud 2.62 y 2 desplomes del BPA (2010, 2023) | margen que se expande; los dos desplomes vienen de ajustes de inventario, sin caída anual de ventas ≥ 10% |
| PLTR, CRWD, SNOW | amplitud 4.0–4.2 | pasan de pérdidas a beneficio: la "amplitud" es la mejora del margen |
| NFLX, AMZN | amplitud 2.2–2.6 y 2–3 desplomes del BPA | margen en expansión e inversión deliberada (AMZN 2014, 2022) |

Con la regla del diseño, **KO, PG y JNJ saldrían cíclicas**, en contra de los casos esperados. Además, PLTR y CRWD
nunca podrían ser GROWTH_PROFITABLE. La amplitud del margen mide expansión, no ciclo. Un desplome del BPA sin caída de
ventas es un cargo puntual.

**Propuesta.** Un ciclo se repite y se ve en las ventas. Es cíclica, con ≥ 8 ejercicios, si se cumple cualquiera de
estas:

- **≥ 2 episodios de caída de ingresos ≥ 10%** (los ejercicios seguidos cuentan como un episodio);
- **≥ 2 desplomes del BPA** (> 50% o a negativo) **el mismo año en que caen los ingresos**.

La serie se corta en los cambios de perímetro: discontinuadas ≥ 10% del beneficio, y rupturas del capital (§4). Por
acción si las acciones crecieron. Las tres medidas del diseño se siguen calculando y se informan en
`classification.inputs.cyclicality.design_measures`, sin decidir.

**Calibración** (umbrales sobre los 24 tickers no financieros, REIT ni utility, con 8+ ejercicios; "C" = cíclica):

| Ticker | Base (10%, 2 episodios) | 8% | 12% | 15% | 3 episodios | 2 episodios + 1 desplome | 3 episodios o 2 desplomes |
|---|---|---|---|---|---|---|---|
| KO | C | C | · | · | · | C | · |
| DOW | C | C | · | · | · | C | · |
| ASML | C | C | C | C | · | C | · |
| SHEL | C | C | C | C | C | · | C |
| TM | · | C | · | · | · | · | · |
| XOM, FCX, CAT, MU | C | C | C | C | C | C | C |

Ninguna variante saca a KO sin sacar también a DOW (y, en dos de ellas, a ASML), que el diseño espera cíclicas. El
prompt prohíbe elegir umbrales para que salga un ticker, así que **me quedo con la base**. El 10% es el umbral
habitual de "caída fuerte". KO y DOW quedan en la frontera, con la confianza baja.

## 3. KO: la decisión que no tomo yo

KO tiene dos episodios de caída: 2017 (−13.6%, refranquicia) y 2020 (−11.5%, pandemia). Además, en 2017 el BPA se
desploma por el cargo de la reforma fiscal. La refranquicia es un cambio de perímetro, pero no se presentó como
operaciones discontinuadas, así que el corte actual no la ve.

| Opción | Qué | Efecto |
|---|---|---|
| **a. (recomendada)** | **Detectar también las desinversiones como cambio de perímetro.** Se usarían los cobros por venta de negocios de EDGAR (`ProceedsFromDivestitureOfBusinesses…`) frente a los ingresos, con un umbral que se calibra y se declara. Es el arreglo en origen: la serie de KO no es comparable entre 2016 y 2018 | Hay que añadir el concepto a la historia y medirlo en todo el panel antes de saber el efecto (puede tocar PG, JNJ o DOW). Si lo apruebas, lo hago y te enseño el resultado antes de cerrar la T2 |
| b. | Aceptar KO como CYCLICAL de frontera (confianza baja, dicho en el informe) | Su análisis usa las herramientas de ciclo medio: precio "exigente" en vez de "muy exigente" |
| c. | Subir el umbral a 12% | **Descartada:** saca también a DOW y es elegir el umbral por un ticker |

## 4. Rupturas del capital (destapado en PLTR)

Antes de su salida a bolsa (septiembre de 2020), las acciones diluidas medias de PLTR excluyen las preferentes
convertibles. Pasan de 577 M (2019) a 979 M (2020) y a 1,924 M (2021). Por eso los ingresos por acción "caían" en
2020–21, aunque los ingresos crecieron un 47% y un 41%. Así, el CAGR a 5 años era 9% y PLTR no llegaba al 10%.

**Arreglo.** Si las acciones crecen ≥ 50% en un ejercicio, hay una ruptura del capital (umbral
`share_break = 0.50`). La serie por acción se corta ahí y el crecimiento por acción se mide desde la última ruptura.

En el panel:

- salidas a bolsa: PLTR (2020–21), SNOW y RIVN;
- fusiones pagadas en acciones: BAC 2009 (Merrill) y PLD 2011 (AMB).

CRWD (+47% en 2021) queda justo por debajo; no le cambia nada, porque falla por margen (§5). Es una definición de dato,
no un umbral para un ticker: aplica a cualquier salida a bolsa reciente.

## 5. Tabla de arquetipos del panel — para aprobar línea a línea

Esperado = F3_DISENO §1.2–§1.4 cuando lo nombra; en el resto, el de la regla anterior.

Medidas (por acción salvo que se diga):

- episodios = caídas de ingresos ≥ 10%;
- desplomes = BPA con caída de ventas;
- CAGR = ingresos por acción a 3 / 5 años;
- margen = margen operativo TTM.

| # | Ticker | Obtenido | Esperado | Medidas que deciden | Justificación de analista | Confianza |
|---|---|---|---|---|---|---|
| 1 | AAPL | MATURE | MATURE | 19 ej.; sin episodios; CAGR 5%/12% | crece a un dígito alto, sin ciclo en 19 años | normal |
| 2 | MSFT | **GROWTH_PROFITABLE** | MATURE (antes) | sin episodios; CAGR 16%/15%; margen 47% | crece al 15–16% con un 47% de margen: es crecimiento rentable, aunque grande | **baja, frontera** (umbral 3 años 15%→18%) |
| 3 | KO | **CYCLICAL** | no cíclica | episodios 2017 y 2020; desplome 2017 | ver §3: refranquicia + pandemia, no ciclo | **baja, frontera** (10%→12%) |
| 4 | PG | MATURE | no cíclica | sin episodios; 5 ejercicios de perímetro cortados | consumo básico estable | normal |
| 5 | JNJ | MATURE | no cíclica | sin episodios; perímetro 2022–23 (Kenvue) | farmacia y dispositivos estables; los cargos no son ciclo | normal |
| 6 | JPM | FINANCIAL · banco | FINANCIAL | industria | banco universal | normal |
| 7 | BAC | FINANCIAL · banco | FINANCIAL | industria; episodio 2010–12 tras la ruptura de 2009 | banco; la caída de 2010–12 es la resaca de la crisis | normal |
| 8 | PGR | FINANCIAL · aseguradora | FINANCIAL | contratos con clientes sin dato → aseguradora | aseguradora de automóvil pura | normal |
| 9 | V | MATURE (red de pagos) | MATURE | activos/ingresos bajo el límite | red de pagos sin cartera de préstamos | normal |
| 10 | BRK-B | FINANCIAL · **conglomerado** | conglomerado (§1.4) | contratos con clientes = 67% de los ingresos | dos tercios de sus ingresos no son seguros (BNSF, BHE, manufacturas) | normal |
| 11 | O | REIT | REIT | industria | REIT de locales netos | normal |
| 12 | PLD | REIT | REIT | industria; la historia no muestra ciclo (sin alerta, antes sí) | REIT logístico | normal |
| 13 | AMT | REIT | REIT | industria | REIT de torres | normal |
| 14 | NEE | UTILITY | UTILITY | industria; la historia no muestra ciclo (sin alerta, antes sí) | utility regulada + renovables | normal |
| 15 | DUK | UTILITY | UTILITY | industria | utility regulada | normal |
| 16 | XOM | CYCLICAL | cíclica | episodios 2015–16, 2020, 2023; desplomes 2016, 2020 | petróleo integrado: el ciclo del crudo | normal |
| 17 | FCX | CYCLICAL | cíclica | episodios 2012, 2015–16, 2019; desplome 2019 | cobre: ciclo de materias primas | normal |
| 18 | CAT | **CYCLICAL** | cíclica (§1.2) | episodios 2009, 2013, 2015–16, 2020; desplomes 2009, 2016 | maquinaria pesada: ciclo de inversión y de minería | normal |
| 19 | MU | CYCLICAL + crecimiento estructural | cíclica | episodios 2016, 2019, 2023; 3 desplomes; CAGR 102% a 3 años | memoria: el ciclo de manual; crece mucho en la parte alta | normal |
| 20 | DOW | CYCLICAL | cíclica | 9 ej. (tras la escisión de 2019); episodios 2020, 2023; desplome 2023 | química básica | **baja, frontera** (10%→12%; 8→10 ejercicios) |
| 21 | PLTR | **GROWTH_PROFITABLE** | GROWTH_PROFITABLE | sin episodios (tras la ruptura); CAGR 24% desde 2021; margen 43% | crece >20% con beneficio y margen alto | normal |
| 22 | NVDA | **GROWTH_PROFITABLE** | a medir; GP solo si §1.2 no la marca | 19 ej.; un episodio (2009); ningún desplome con caída de ventas; CAGR 102%/68%; margen 65% | sus caídas de BPA de 2010 y 2023 fueron ajustes de inventario sin caída anual de ventas ≥ 10%: crecimiento rentable | normal |
| 23 | CRWD | MATURE | GROWTH_PROFITABLE | CAGR 26%/37%; margen operativo −2%; FCF − SBC 5% | **no cumple:** el margen FCF − SBC (5%) no llega al 10% que pide §1.3 (el diseño pedía valorarlo y documentarlo: documentado). BPA TTM sin dato en el fixture | normal |
| 24 | RIVN | GROWTH_PRE_PROFIT | GROWTH_PRE_PROFIT | 7 ej. (corta); pérdidas | pre-beneficio | baja (sin historia) |
| 25 | SNOW | GROWTH_PRE_PROFIT | GROWTH_PRE_PROFIT | pérdidas; CAGR 29% | pre-beneficio | normal |
| 26 | TSM | **GROWTH_PROFITABLE** | a medir | 11 ej.; sin episodios; CAGR 22%/24%; margen 56% | fundición dominante: crece >20% sin caídas anuales ≥ 10% en 11 años | normal |
| 27 | ASML | CYCLICAL + crecimiento estructural | a medir | episodios 2008–09, 2012; desplome 2009; CAGR 16%/20% | equipos de semiconductores: ciclo de inversión de las fábricas; crece con beneficio | normal |
| 28 | NVO | **GROWTH_PROFITABLE** | MATURE (antes) | 7 ej. (corta): CAGR 21%/21%; margen 43% | GLP-1: crecimiento rentable; la ciclicidad no se pudo medir | **baja, sin historia** |
| 29 | NFLX | MATURE | MATURE (antes) | CAGR 14%/14%; margen 30% | crecimiento de dígito alto | **baja, frontera** (15%→12%) |
| 30 | AMZN | MATURE | MATURE (antes) | CAGR 9%/12% | crece a un dígito alto por acción | normal |
| 31 | BCS | FINANCIAL · banco | FINANCIAL | industria | banco | normal |
| 32 | HSBC | FINANCIAL · banco | FINANCIAL | industria; **alerta nueva:** episodios 2016, 2020 | banco con ciclo de crédito y tipos | baja (alerta) |
| 33 | SHEL | CYCLICAL | cíclica (antes) | episodios 2016, 2019–20, 2023–24 | petróleo integrado | normal |
| 34 | UL | MATURE | MATURE | un episodio (2023), perímetro 2025 (helados) | consumo básico estable | normal |
| 35 | TM | **MATURE** | CYCLICAL (antes, por industria) | 19 ej.: un episodio (2009, −22%) y su desplome; 2021 cayó −8.9% | **frontera** (10%→8%). Un analista la llamaría cíclica (automóvil); su historia en yenes solo muestra una caída fuerte | **baja, frontera** |
| 36 | MC.PA | MATURE | MATURE | sin CIK: sin historia | lujo; ciclicidad sin medir | baja (sin historia; D7) |

SPY: ETF, rechazado (422).

**Para tu decisión, además de KO:**

- **TM** (fila 35) está en la frontera por el lado contrario. Lo dejo con la regla, como manda el prompt;
- **CRWD** (fila 23) no cumple GROWTH_PROFITABLE con la regla aprobada: el margen FCF − SBC es del 5%.

## 6. Cambios en el panel frente a T1b (`panel_run --compare`), cada uno por su campo

| Ticker | Cambio | Causa |
|---|---|---|
| CAT | MATURE → CYCLICAL; confianza media → baja | historia cíclica; estabilidad baja por ser cíclica |
| KO | MATURE → CYCLICAL; precio muy exigente → exigente; confianza alta → media | historia (§3); herramientas de ciclo medio; estabilidad baja y DCF no evaluable como cíclica |
| TM | CYCLICAL → MATURE; calidad media → sólida; precio atractivo → razonable; confianza media → baja | la historia no muestra ciclo; con las herramientas de MATURE pierde la base de crecimiento de ciclo (cobertura baja) y su DCF no es evaluable. Lo revisa la T3 |
| MSFT, NVDA, NVO, PLTR, TSM | → GROWTH_PROFITABLE | §1.3. Calidad, precio y score iguales: herramientas de MATURE (provisional) |
| NFLX, NVO | confianza alta → media | frontera (NFLX), sin historia (NVO) |

Confianza sin cambio de nivel:

- **sube:** NEE, PLD, NVDA, PLTR y TSM (la historia sustituye a la alerta de posible cíclica);
- **baja:** MSFT (frontera), HSBC (alerta nueva) y MC.PA (sin historia).

## 7. Golden: 70 cambian. Diff por causa

| Causa | Tickers | Qué cambia |
|---|---|---|
| 1. Campos nuevos de la clasificación | todos | `subtype`, `subtype_label`, `frontier`, `low_confidence`, `structural_growth`, `inputs.cyclicality`, `inputs.growth_profitable` |
| 2. Resumen de la historia de EDGAR | todos los que tienen CIK | `data_provenance`: los dos campos nuevos de la historia y los descartes de escala |
| 3. Texto del motivo | MATURE y CYCLICAL por historia | "ni cíclica, ni de crecimiento rentable" o "cíclica por su historia: …" (portada y anexo, una línea) |
| 4. Cambio de arquetipo con cambio de herramientas | CAT, KO, TM | el análisis completo: score, secciones, gráficos, DCF, sensibilidad (§6) |
| 5. Cambio de arquetipo sin cambio de herramientas | MSFT, NVDA, NVO, PLTR, TSM | etiqueta, motivo y confianza |
| 6. Confianza de la clasificación | MC.PA, NFLX, NVO, MSFT, KO, DOW, TM, HSBC (baja); NEE, PLD, NVDA, PLTR, TSM (sube) | dimensión de estabilidad, su texto y la nota de la portada |
| 7. Muestras forzadas del contrato | — | se regeneran con `contract_forced.py --write` |

Comandos:

- ver el diff: `tests/diff_golden.py --env panel` y `--env local` (`--full` para todo);
- regenerar, solo con tu aprobación: `--regenerate --yes` y `contract_forced.py --write`.

## 8. Notas latentes (no bloquean)

- **CRWD:** BPA TTM sin dato en el fixture. La regla de GROWTH_PROFITABLE exige BPA > 0; sin dato no se cumple. Su
  margen neto es positivo (1.1%). No cambia el resultado, porque falla por margen.
- **SHEL:** sin BPA en la historia de EDGAR (concepto IFRS distinto). Es cíclica por los episodios de ventas.
- **TM, defecto de dato destapado y arreglado** (commit propio, sin efecto en el arquetipo): el split 5:1 de 2021 no
  se ajustaba en el BPA anterior al FY2020. TM pasó a NIIF ese año y sus acciones en NIIF solo cubren 3 ejercicios,
  así que aparecía un falso desplome del BPA en 2020 (¥645 → ¥144). El ejercicio que presentan las dos taxonomías da
  el factor (FY2020: 720.3 en US GAAP frente a 144.05 en NIIF, cociente 5.0).
- **Rendimiento:** la sensibilidad repite la medida unas 12 veces por análisis (milisegundos, funciones puras).
