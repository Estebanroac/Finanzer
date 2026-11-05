# Modelo general de Finanzer: especificación (borrador para después de la v4)

> Borrador del 28-oct-2026 (rama `modelo/general-inventario`). Propuesta, no código: nada de esto cambia el motor hasta
> que el usuario la apruebe. Parte del inventario (`INVENTARIO.md`) y del escaneo del universo (`ESCANEO_2026-10-28.md`,
> 543 empresas, base sin F10). Las cifras «hoy» salen de ahí.

## 1. Por qué

El usuario no quiere seguir corrigiendo informe a informe: cada revisión externa (F8 con 26 empresas, F9 con NU, F10 con
NVIDIA) destapa una excepción, y cada corrección añade otra. El inventario mide el resultado de ese camino:

| Hoy | Cifra |
|---|---:|
| Variables que puntúan | 47 |
| Universales (las 7 clases de empresa) | **1** (el bloque de múltiplos) |
| Específicas de 1–4 clases | 34 |
| Muertas (se registran y nunca aplican) | 2 |
| Ramas `if archetype == …` en el código | 158, en 12 archivos |
| Entradas «no aplica» por clase | 64 |
| Umbrales por sector escritos a mano (PROVISIONALES) | 80, en 11 sectores |
| Ajustes que puntúan fuera de la cobertura (bonos) | 2 (el Forward P/E, en 174 empresas) |

Y el escaneo enseña lo que produce: alertas que contradicen la fila de su cifra (20 empresas), cifras dobles en el mismo
informe (11), vacíos sin motivo (97), la empresa comparada consigo misma (111) y votos que se repiten (ROE y ROIC − WACC,
r = 0,81 en 407 empresas).

**Objetivo:** un modelo cuyas variables apliquen a todas las acciones con la misma fórmula, donde lo que cambia por tipo
de empresa sea solo **la medida contable** que entra en la fórmula (qué es su «beneficio», su «capital» y su «flujo»),
con seis tipos y no más.

## 2. Principios

1. **Una variable, una fórmula, una referencia.** La misma cifra, con la misma referencia, en el score, en la fila, en
   la tarjeta, en la alerta y en el PDF. Si dos bloques no pueden coincidir, uno de los dos sobra.
2. **Lo que cambia por tipo es la base contable, no la variable.** «Rentabilidad sobre el capital menos su coste» vale
   para todos; para un banco el capital es el patrimonio y el coste el Ke, y para una empresa general son el capital
   invertido y el WACC.
3. **La referencia es la industria sin la propia empresa** (Damodaran, región o global; sin ella cuando pesa más del
   umbral, F10 · N2). Se retiran las tablas por sector escritas a mano.
4. **Un voto por idea.** Si dos variables se mueven juntas en el universo (|r| ≥ 0,7 dentro de una categoría), una pasa
   a lectura (se enseña y no vota).
5. **Reglas generales en vez de excepciones**: denominador ≤ 0 ⇒ «no significativo» con su motivo; año base anómalo ⇒
   método robusto; beneficio por encima de su techo operativo ⇒ se normaliza el exceso (F10 · N1); una sola serie anual
   (EDGAR) para todo lo histórico.
6. **Umbrales con origen.** Cada banda sale de una distribución medida (la industria o el universo) y se escribe con su
   fuente; nada se ajusta para rescatar un caso concreto. Lectura continua cuando la variable lo es: su posición en la
   distribución, no tramos fijados a mano.

## 3. Tipos de empresa

| Tipo | Quién (regla de clasificación) | «Beneficio» B | «Capital» K y su coste | «Flujo» F | Hoy (escaneo) |
|---|---|---|---|---|---:|
| **Empresa general** | por defecto | beneficio neto normalizado (sin no operativo ni no recurrente) | capital invertido · WACC | FCF − SBC | MATURE 332 + CYCLICAL 60 + GROWTH_PROFITABLE 42 = 434 |
| **Banco** | industria «Banks…»; prestamistas de Credit Services; financieras ambiguas | beneficio neto | patrimonio tangible · Ke | — (el flujo no aplica) | 26 + 9 «financiera» |
| **Aseguradora** | industria «Insurance…» (con conglomerado como aseguradora) | beneficio operativo (sin resultado de inversiones realizado) | patrimonio · Ke | — | 16 + 1 |
| **REIT** | industria «REIT…» | FFO (Nareit) | activos totales · WACC | AFFO o FFO − capex de mantenimiento | 28 |
| **Utility** | utilities reguladas | beneficio neto | capital invertido · WACC (el retorno lo fija el regulador) | — (negativo por diseño) | 28 |
| **Sin beneficios aún** | BPA ≤ 0 y crecimiento real > 15 % | — (no hay) | caja · años de caja | FCF − SBC | 1 |

**Qué desaparece:** MATURE, GROWTH_PROFITABLE y CYCLICAL dejan de ser tipos. GROWTH_PROFITABLE no tiene ninguna
herramienta propia. Lo de CYCLICAL pasa a una **propiedad medida** de cualquier empresa: `cíclica` según la historia de
EDGAR (la regla `historia_ciclica` actual) activa el ciclo medio en el crecimiento y los múltiplos normalizados. Los
subtipos «conglomerado» y «financiera» se absorben. Las excepciones por industria (redes de pago y gestoras dentro de
Financial Services, circulante negativo, Altman referencial) pasan a lecturas por modelo de negocio o desaparecen con
las variables que las necesitaban (§4).

**Abierto:** la aseguradora necesita su ratio combinado (siniestralidad + gastos / primas) para no ser «un banco con
otro nombre». EDGAR lo permite reconstruir (primas, siniestros, gastos de adquisición); falta verificarlo en las 17 del
universo.

## 4. Variables finales

Doce variables. Diez son universales (la misma fórmula sobre la base de su tipo, §3) y dos dependen de un tipo por
contabilidad. Entre paréntesis, las de hoy que sustituye.

### Solidez (3)

| # | Variable | Fórmula | Tipos | Sustituye a |
|---|---|---|---|---|
| S1 | Apalancamiento frente a su industria | deuda neta / EBITDA (general, REIT, utility); patrimonio tangible / activos (banco, aseguradora) | todos (base del tipo) | D/E por sector, deuda neta/EBITDA con bandas de REIT y de utility, D/E bancario (muerta), salud bancaria |
| S2 | Cobertura de intereses frente a su industria | EBIT / intereses netos | todos menos banco y aseguradora | cobertura con bandas generales y bandas de utility |
| S3 | Años de caja | (caja + inversiones a corto) / quema de FCF; con FCF ≥ 0, «autofinanciada» | **todos** con F < 0 | runway (solo pre-beneficio) |

Pasan a lectura (se enseñan, no votan): **Altman Z** (AUC ≈ 0,75 fuera de muestra, F8 · E10, y vota con ROA, margen neto
y ROE: r ≈ 0,8) y **liquidez corriente** (Damodaran no tiene referencia por industria; con las excepciones de circulante
negativo, hoy no puntúa en 15 industrias).

### Rentabilidad (2)

| # | Variable | Fórmula | Tipos | Sustituye a |
|---|---|---|---|---|
| R1 | Retorno sobre el capital menos su coste | B / K − coste de K (ROIC − WACC; ROE − Ke en banco y aseguradora; FFO / activos − WACC en REIT) | todos menos sin beneficios | ROE, ROA, ROIC − WACC, FFO/activos, y el tope por ROIC − WACC |
| R2 | Margen frente a su industria | margen operativo (general, utility); margen FFO (REIT); ratio combinado (aseguradora); eficiencia (banco); margen operativo y su mejora (sin beneficios) | todos (base del tipo) | margen operativo, margen neto, margen FFO, margen bruto y mejora del margen del pre-beneficio, eficiencia bancaria |

El ROE de hoy pesa más que ninguna otra variable (±3,7 de media en 479 empresas) y se lee contra tablas por sector
escritas a mano; R1 lo hace universal y sin tablas.

### Calidad de ganancias (2)

| # | Variable | Fórmula | Tipos | Sustituye a |
|---|---|---|---|---|
| Q1 | Conversión en caja | F / B (FCF − SBC / beneficio normalizado; AFFO / FFO en REIT); sin beneficio, margen FCF − SBC | todos menos banco, aseguradora y utility | OCF > 0, FCF > 0, FCF / beneficio, FCF − SBC > 0, payout sobre FFO |
| Q2 | Estabilidad del retorno | desviación de R1 en 5–10 ejercicios de EDGAR | todos con historia | estabilidad del ROE (hoy solo en financieras) |

Pasa a lectura: **Piotroski F** (nueve criterios binarios; vota con margen y ROA, r ≈ 0,65, y hoy aplica a 5 de 7
clases).

### Crecimiento (2)

| # | Variable | Fórmula | Tipos | Sustituye a |
|---|---|---|---|---|
| G1 | Crecimiento por acción, robusto | CAGR de los ingresos por acción (valor en libros tangible por acción en banco y aseguradora; FFO por acción en REIT), con regresión log-lineal si la base es anómala y ciclo medio si es cíclica | todos | crecimiento de ingresos, del BPA y del FCF, crecimiento del valor en libros |
| G2 | Retorno total para el accionista | rentabilidad por dividendo + G1, frente al Ke | todos | retorno total (hoy en REIT y en MATURE con dividendo ≥ 4 %) |

El BPA y el FCF quedan como lecturas: su CAGR a 3 años es el que más se rompe por un año valle (43 empresas en el
escaneo) y vota con el de los ingresos (r = 0,79).

### Valoración (3)

| # | Variable | Fórmula | Tipos | Sustituye a |
|---|---|---|---|---|
| V1 | Precio frente al beneficio del tipo | P / B normalizado frente a su industria sin la empresa (P/E; P/FFO en REIT; EV/Ventas en sin beneficios) | todos | P/E, Forward P/E (bono), PEG, P/FFO, EV/Ventas (F10 · N4: un voto) |
| V2 | Precio frente al capital o al flujo | EV/EBITDA frente a su industria (general, REIT, utility); P/B y P/TBV frente a su justificado (banco, aseguradora) | todos | EV/EBITDA, P/FCF, P/B y P/TBV, P/B frente al ROE regulado |
| V3 | Valor intrínseco | DCF directo con su fiabilidad o, si no es significativo, el inverso con las tasas base | todos menos banco y aseguradora | DCF, DCF inverso (sus cuatro variantes de nombre) |

La rentabilidad por dividendo de la utility deja de votar en Valoración: entra en G2.

**Requisito de V1 (decisión del usuario, 5-nov-2026, F12 · D2).** Fundir el forward en un único voto del beneficio
reduce su peso, pero no corrige su validación. Dentro de V1, el beneficio previsto solo entra con las dos comprobaciones
de F12 (`historical_metrics.backing_base` y `thresholds.score.valoracion.forward_basis_gap`):
1. El crecimiento histórico que lo respalda no puede salir de un año base deprimido frente a la historia larga (5–10
   ejercicios, la misma razón de base anómala). Si sale, el respaldo es la ventana que empieza después o la tasa larga,
   la menor.
2. El forward y el beneficio normalizado comparten base: si el crecimiento que implica frente al normalizado y frente
   al reportado difiere más de 15 pp, la parte prevista no puntúa.

### Resumen

| | Hoy | Propuesta |
|---|---:|---:|
| Variables que puntúan | 47 | 12 |
| Universales (con la base de su tipo) | 1 | 10 |
| Tipos de empresa (y subtipos) | 7 (+4) | 6 |
| Tablas de umbrales por sector | 12 | 0 |
| Juegos de bandas propios de un tipo (`thresholds.score`) | 22 | 0 (las bandas son de la industria) |

## 5. Bandas

Cada variable se lee por su **distancia a la industria** (en puntos porcentuales para los márgenes y los retornos, como
ya hace el margen con F8 · E9; en múltiplos de la industria para los múltiplos y el apalancamiento), y la puntuación es
una función continua de esa distancia, acotada, en lugar de tramos. La escala de cada variable se calibra con la
distribución del universo (543 empresas del escaneo más el panel), con sus cuantiles publicados en la config junto a
su fuente. Sin referencia de industria, la del mercado amplio de su región, declarada. Nada se ajusta para que una
empresa concreta salga distinta.

## 6. Cómo se valida que no empeora

Cada paso de la migración (§7) se acepta solo si cumple todo esto:

1. **Reglas de cordura en el universo** (`tools/universe_scan.py`, las 15 de `lib/model_invariants.py`): ninguna regla
   sube; las de la puerta de la v4 (vacíos sin motivo, cifras dobles, alertas frente a filas, peso en la referencia,
   techo del margen, base anómala) en 0 o con cada caso explicado.
2. **Votos independientes**: en el escaneo, ningún par de variables de una misma categoría con |r| ≥ 0,7
   (`tools/model_inventory.py --scan`, §6.1).
3. **Estabilidad del veredicto**: matriz de transiciones de las etiquetas de calidad (hoy: excelente 93, sólida 270,
   media 147, débil 33) y de precio (atractivo 62, razonable 220, exigente 156, muy exigente 101, sin dato 4). Cada
   empresa que salte dos niveles o más, con su causa en el registro del paso. Un salto sin causa bloquea el paso.
4. **Los casos de las revisiones externas**: las 26 de la auditoría F8 (`tools/f8_evidencia.py`: MSFT, NVDA, LLY, UNH,
   JPM, CB, AMZN, MCD, GOOGL, VZ, CAT, UNP, KO, WMT, XOM, KMI, NEE, AWK, PLD, O, LIN, FCX, ASML, SAP, MRNA, BA), más NU
   (F9). Cada hallazgo de esas tres revisiones es un test que debe seguir en verde; además, `f8_compare.py` frente a la
   corrida anterior.
5. **Golden**: diferencias revisadas y explicadas, como en cada fase (`GOLDEN_DIFF_<paso>.md`).
6. **Cobertura**: la proporción de variables con dato no baja (hoy, por categoría, en `score_coverage`).
7. **Pre-beneficio fuera del S&P 500**: el universo tiene una sola empresa sin beneficios, así que este tipo se valida
   además con las del panel (RIVN, SNOW) y otras 10 de fuera del índice, elegidas antes de ver el resultado.

## 7. Orden de migración

Primero lo que reduce errores sin cambiar el modelo; después las referencias; al final las variables y las bandas.
Cada paso, una rama, el escaneo y los 27 casos de §6.

| Paso | Qué | Por qué en este orden | Efecto esperado (escaneo) |
|---|---|---|---|
| M0 | Puerta de la v4: F10 (N1–N4) y B1 (vacíos), B2 (cifras dobles), B3 (alertas con la referencia de su fila) | Ya repartido; es la v4 | peso 111 → ~0, techo 67 → ~0, base anómala 43 → 0, vacíos 97 → 0, alertas 20 → 0, cifras 11 → 0 |
| M1 | Reglas generales: denominador ≤ 0 ⇒ n.s. en `CategoryCoverage`; una serie anual de EDGAR para historia, gráfico y crecimiento | Quitan excepciones sin cambiar qué se mide | menos código por métrica; las reglas de M0 se quedan en 0 por construcción |
| M2 | Una referencia: ROE, ROA, D/E y P/FCF dejan las tablas por sector por la industria sin la empresa | Antes de fundir variables, que todas midan contra lo mismo | 80 umbrales PROVISIONALES fuera; cambian las lecturas de ROE y D/E |
| M3 | Tipos: general (con la propiedad «cíclica»), banco, aseguradora, REIT, utility, sin beneficios | Con las referencias ya únicas, un tipo solo cambia la base contable | 158 ramas → las de 6 tipos; fuera las 2 variables muertas |
| M4 | Valoración: V1 (un voto de beneficio), V2, V3 | Ya repartido en parte (F10 · N4) | Forward P/E deja de ser bono; el bloque deja de repetir el mismo BPA |
| M5 | Rentabilidad y calidad: R1, R2, Q1, Q2; Altman y Piotroski pasan a lecturas | Son los votos más correlacionados | Rentabilidad y Calidad con 2 variables cada una |
| M6 | Crecimiento y solidez: G1, G2, S1–S3 | Dependen del método robusto (N3) y de las referencias (M2) | retorno total para todos; runway para toda empresa que quema caja |
| M7 | Bandas continuas calibradas con el universo | Al final, con las variables ya estables | sin tramos fijados a mano |

## 8. Riesgos y preguntas para el usuario

- **El veredicto cambiará** en muchas empresas en M2, M5 y M7. No es un error, pero hay que enseñarlo: §6.3 da la matriz de
  transiciones de cada paso, con sus causas.
- **Datos que faltan**: el ratio combinado de la aseguradora; la distribución por industria (Damodaran publica agregados,
  no cuantiles: las escalas de §5 se calibran con el universo, que es de grandes empresas).
- **Altman y Piotroski** son conocidos por los usuarios. Pasan a lecturas visibles con su motivo, sin desaparecer. ¿De
  acuerdo?
- **Liquidez corriente**: se propone sacarla del score; es la única que no tiene una referencia por industria gratuita.
- **Alcance**: ¿el objetivo de «casi todas universales» admite las dos variables que dependen de la contabilidad (S2 y
  Q1 no aplican a banco ni aseguradora; V3 tampoco)?

## 9. Puntos abiertos que deja F10

**a) M2 medido y NO aplicado en la v4** (rama `medida/f10-m2`, `docs/fiabilidad/f10_m2/M2_MEDIDA.md`). Es el paso M2 de
§7: el ROE, el ROA y el D/E se leen frente a la industria sin la empresa, en lugar de las tablas por sector. En el
universo (543 empresas, variante A) cambia el nivel de **calidad del 14 %** (77: 63 bajan y 14 suben) y el de
**precio de ninguna**. Antes de aplicarlo quedan tres decisiones:
1. **La referencia del ROE agregado.** El ROE de la industria hereda sus distorsiones: CB baja contra «Seguros de daños»
   de Europa sin Chubb (las 18 aseguradoras pequeñas que N2b ya quitó del P/B en dos etapas) y AMZN contra un «Retail
   (General)» con un ROE del 61 %, inflado por su apalancamiento. ¿Se usa para el ROE la misma convergencia global sin
   la empresa que N2b usa en el P/B? ¿O se mide en puntos porcentuales, como los márgenes desde E9?
2. **Si el ROA vota.** No hay referencia gratuita por industria: Damodaran no publica activos totales. Con las bandas por
   defecto castiga a todo banco y aseguradora (JPM, SYF). Sin voto, la rentabilidad pierde una variable, que es justo
   la propuesta R1 de §4 (de 5 votos a 2).
3. **La regla del cambio ROE → ROIC.** Frente a la industria salta con un D/E solo un 10 % por encima (SYK, +15 %); con
   la tabla había que superar el umbral del sector. Y el ROIC se compara con el de la industria, alto en las de capital
   ligero (Software 34 %). Hace falta un margen en la regla y que no sea un umbral fijado a mano: por ejemplo, el
   percentil del D/E dentro de su industria.

**b) Beneficio agregado de Damodaran: ¿antes o después de los dividendos preferentes?** Es el caso de BAC: según cuál
sea, el P/E y el ROE de la referencia de los bancos cambian lo bastante para cruzar un umbral. Falta confirmarlo con la
definición de las hojas de Damodaran (`pedata`, `roe`) y con los totales en dólares que ya importa N2: beneficio neto
frente a beneficio disponible para el accionista común. Si es antes de preferentes, la referencia de los bancos con
preferentes grandes (BAC, JPM, WFC, C) debe ajustarse, o compararse con el beneficio de la empresa en la misma base.

**c) Post-v4 · La beta propia con un filtro continuo, no con un corte en R² 0,20.**
- **Qué pasa hoy:** la beta propia se usa si pasa tres filtros (`market.beta_choice`: R² ≥ 0,20, error estándar ≤
  0,25 y beta en [0,4; 2,5]). Si no los pasa, entra la de su industria, desapalancada y reapalancada.
- **El caso:** MSCI, en dos pasadas del mismo día, tuvo R² 0,202 y 0,199. Con el corte, la beta salta de 0,87
  (propia) a 0,49 (sector), el WACC de 8,8 % a 7,4 %, y el precio de 10 «muy exigente» a 40 «exigente». Es un salto
  grande por una diferencia que no significa nada.
- **Arreglado en la v4** (`fiabilidad/f10-beta-semanas`): la regresión usa solo semanas completas, así que la beta es
  la misma en todo el día.
- **Queda post-v4:** el corte binario. La propuesta es una media ponderada de la propia y la de la industria, con un
  peso que crezca con la precisión de la propia (por ejemplo, la ponderación bayesiana de Vasicek: el peso de la
  propia es la varianza de las betas de la industria entre esa varianza más el error estándar² de la propia). Así no
  hay ningún umbral fijado a mano y la beta varía de forma continua. Hay que medir cuántas empresas cambian de nivel
  frente a hoy.

**d) Post-v4 · Nombrar los ingresos recurrentes sin nombre en N1b; el escudo fiscal de las pérdidas.** Detalle en
`EXCESOS_SIN_NOMBRE_2026-10-29.md`.
- **Pensiones no operativas (NOC) y AFUDC de capital de las utilities (SO, FE):** nombrarlos con su etiqueta estándar
  de EDGAR, sin recortarlos (son recurrentes), para que no queden como «sin nombre».
- **Ford (F):** la causa es el escudo fiscal de unas pérdidas. El techo de N1b solo aplica el tipo a un resultado
  positivo; es un arreglo del techo, no un nombre.

> **Evidencia fuera de `main` (E6, 31-oct):** las capturas (`docs/rediseno/capturas-*`), `docs/fiabilidad/f8_evidencia/` y los volcados JSON de escaneo y medida de `docs/` no están en `main`. Siguen en las ramas locales del rediseño y de la fiabilidad (`rediseno/v4-f8`) y en el archivo `v4_evidencia_8e4f3952.tar.gz` de `/Users/joseestebanroa/Downloads/finanzer_next-archivo`, fuera del repositorio.
