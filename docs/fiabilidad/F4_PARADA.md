# F4 · Escalas y confianza honestas: verificación y cierre

> Fase 4 del plan de fiabilidad (PLAN_FIABILIDAD §4). Rama `fiabilidad/f4-escalas`, que sale de `fiabilidad/f3-metodo`
> (worktree `../finanzer_next-f3`). **Nada subido.**
> Hecha bajo la delegación del usuario (registro #29), sin prompt del planificador: el operador leyó el plan, decidió
> con criterio de analista y declara cada decisión aquí y en la bitácora (registro #32).
> Replay del panel (sin red), 2026-10-17.

## 0. Resumen

| | T0 (inicio de F3) | Cierre de F3 | Ahora |
|---|---|---|---|
| Calidad > 95 (objetivo del plan: ≤ 2) | 4 (NFLX 100, PLTR 100, TSM 100, V 96) | 4 (NFLX 100, TSM 100, PLTR 99, V 96) | **2** (TSM 99, V 96) |
| Calidad en 100 | 3 | 2 | **0** |
| Calidad: <45 / 45–64 / 65–79 / 80–89 / 90–95 / >95 | 2 / 4 / 12 / 9 / 5 / 4 | 2 / 3 / 12 / 10 / 5 / 4 | 2 / 3 / 12 / 10 / 7 / 2 |
| Precio: muy exigente / exigente / razonable / atractivo | 3 / 14 / 15 / 4 | 10 / 7 / 16 / 3 | 10 / 7 / 16 / 3 (sin cambios) |
| Confianza: alta / media / baja | 5 / 28 / 3 | 10 / 23 / 3 | 12 / 21 / 3 |
| Aviso de frontera entre niveles | — | — | 11 (4 de calidad, 8 de precio) |
| Pre-mortem con condiciones | — | — | 34 de 36 (RIVN y SNOW: pre-beneficio sin método intrínseco) |
| Cambios de nivel de calidad o de precio por F4 | — | — | **0** |
| Tiempo del panel en replay | 7.7 s | 8.0 s | 8.1 s |
| Suite sin golden | — | 3659 passed | 3803 passed; falla 1, las muestras forzadas del contrato, que van con los golden |

## 1. Qué se hizo (un commit por causa)

| Punto del plan | Commit | Qué y por qué |
|---|---|---|
| §4.1 saturación | `1f12e33`, `92a279e` | **Lo extraordinario exige persistencia.** Fórmula: calidad = 80 + (calidad − 80) × persistencia. La persistencia es la media ponderada, por sus puntos sobre 16/20, de la de cada categoría en los 5 últimos ejercicios. Anclas: (1) margen operativo ≥ 75% del actual (margen neto en financieras); (2) ingresos al alza; (3) flujo operativo ≥ beneficio y FCF > 0 (sin pérdidas en financieras). Solidez no tiene ancla, porque la historia de EDGAR no trae balances, y se dice. "Excelente" (≥ 80) no cambia; lo que está por encima exige historia. Un ejercicio sin dato no prueba nada. La ventana se ancla en el último ejercicio con dato y la historia de EDGAR se completa con los estados. |
| §4.2 confianza | `122cbb4`, `e5baf6e` | **Causas reales.** La fuente cuenta solo lo que afecta al dato usado: datos rechazados o corregidos, beneficio con ítems inferidos, sin TTM. Antes restaban los avisos (beta del proveedor cuando se usa la propia), los datos de otro periodo ya descartados (eso es cobertura) y "N campos de Finnhub", que desde la 2b solo entran si casan con el corte. Con eso la fuente salía media o baja en casi todo el panel y no discriminaba. "Alta" exige que ninguna dimensión sea baja: una cíclica o datos rechazados ponen techo en media. El resumen cita el motivo real del techo. |
| Mapa, efecto frontera (NVO) | `a0aa922` | A 2 puntos o menos de un umbral de nivel, la portada dice con qué nivel linda: un cambio pequeño en los datos o los supuestos lo cambiaría. |
| §4.3 pre-mortem | `bc4fa89`, `f99859a` | "Esta lectura sería errónea si…" (Valoración, web y PDF). Hasta 3 condiciones con la cifra que las mide: (1) el crecimiento que exige el DCF inverso, o el ROTE/ROE implícito, en el sentido del nivel; (2) el margen de hoy > 120% de su mediana de 10 años o de su media de ciclo medio; (3) deuda neta/EBITDA en el tramo elevado del sector (con la cautiva declarada). |
| Mapa, bandas paralelas | `ea2926b`, `71b5184` | Una sola fuente de umbrales para las alertas, la lectura, el gráfico, el tooltip y el pre-mortem. DCF ±10% y ±30% (la alerta usaba ±15%). Cobertura 10x (la alerta pedía 12x). Deuda neta/EBITDA y beta con los umbrales del sector (la lectura usaba 1 / 2.5 / 4x y 1.6). |

Además, se arreglaron los 6 defectos confirmados y los 2 plausibles de la revisión de código de la fase 3 (`6578a63`…`8c53940`, prefijo F3; detalle en el registro #32). El hallazgo 3 no se reproduce: la 2b ya sustituye el interanual de la fuente por el de los estados en todas las rutas.

## 2. Calidad por encima de 80, antes y después

| Ticker | Antes | Ahora | Qué no persiste (5 últimos ejercicios) |
|---|---|---|---|
| TSM | 100 | 99 | Ingresos: 4 de 5 (cayeron en 2023) |
| NFLX | 100 | 93 | Margen operativo en su nivel actual (29.5%): 2 de 5; flujo operativo ≥ beneficio: 1 de 5 (inversión en contenidos) |
| PLTR | 99 | 95 | Margen operativo: 1 de 5 (beneficio GAAP solo desde 2023) |
| MU | 95 | 90 | Margen: 1 de 5 (cíclica en pico) |
| NVDA | 95 | 93 | Margen: 3 de 5 |
| V | 96 | 96 | Persistente en todo |
| MSFT | 95 | 95 | Persistente en todo |

Lectura de analista: V y MSFT son los dos negocios de rentabilidad sostenida por excelencia del panel y siguen arriba. NFLX, PLTR y MU llegaban a 100 o cerca con márgenes recientes, o de pico, que no tienen historia.

## 3. Revisión externa (fuera del panel)

| Ticker | Resultado | Hallazgo y arreglo |
|---|---|---|
| NOW | Calidad sólida (72); precio muy exigente; pre-mortem: crecer ≥ 23.0% anual 10 años (lo logrado: 24.1% en 8), margen 11.4% frente a una mediana de 4.4% | Sin hallazgos |
| DE | Cíclica, confianza media con techo por estabilidad baja; pre-mortem de deuda 5.1x | La deuda incluye la de John Deere Financial, que no se separa: la condición lo dice ahora (`f99859a`) |
| SAN | Calidad 86 → 85 por persistencia | **Error de fondo:** la ventana de persistencia se anclaba en la serie de ingresos de EDGAR, que en un banco IFRS acaba en 2017. Arreglado (`92a279e`) |

## 4. Web

Comprobado en el navegador, con la app en replay y NFLX:

- en la portada, la nota "Por encima de 80, la calidad exige persistencia: 100 → 93…";
- en Valoración, el bloque "Esta lectura sería errónea si…" con sus dos condiciones.

La compilación de prueba (webpack) no se versiona.

## 5. Lo que no se hizo y por qué

- **Referencias por industria y por geografía** (mapa: TXRH en restauración, BCS en bancos europeos) y **medianas sectoriales con fuente** (las de hoy están "PROVISIONAL, fijadas a mano"). La fuente estándar son los conjuntos de datos de Damodaran (NYU Stern), por industria y por región. Contienen P/E, EV/EBITDA, márgenes, ROE y beta, y se actualizan cada enero. Usarlos exige descargar archivos, y la regla vigente pide el permiso explícito del usuario para cualquier descarga. Lo que hace falta:
  - permiso para descargar desde pages.stern.nyu.edu/~adamodar los ficheros de múltiplos y márgenes de EE. UU., Europa y Japón (unos 6 Excel de 100–300 KB cada uno);
  - con ese permiso, una sesión carga las medianas en `config/sectors.toml` con fuente y fecha, y sustituye el mapeo de sector amplio por el de industria.

  Mitigado entretanto: en bancos manda el P/B frente al ROE propio (método intrínseco, independiente de la geografía).
- **Bandas de REIT y utilities sin muestra:** siguen PROVISIONALES. Se calibran en la fase 7 con la historia de EDGAR de una muestra amplia.
- **Golden:** sin regenerar, igual que en la fase 3 (permiso del usuario).
