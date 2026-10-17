# F5 · Capa técnica y conductual: verificación y cierre

> Fase 5 del plan de fiabilidad (PLAN_FIABILIDAD §2.2, §2.3 y §4). Rama `fiabilidad/f5-contexto`, que sale de
> `fiabilidad/f4-escalas` (worktree `../finanzer_next-f3`). **Nada subido.**
> Hecha bajo la delegación del usuario (registro #29), sobre la preparación F5prep (módulos aislados con contraste
> independiente, fusionada antes de la fase 2b). D5 vigente: **solo contexto, nunca puntúa**.

## 0. Resumen

| | Resultado |
|---|---|
| Señales en el análisis | Momentum 12-1, tendencia de 200 sesiones, volatilidad de 1 año (con la del S&P 500 al lado), caída máxima (1 año y la serie), fuerza relativa frente al ETF del sector a 12 meses, volumen anómalo |
| Panel con señales | 36 de 36 (SPY se rechaza antes, como debe) |
| Contraste independiente (pandas a mano, sin los módulos) | 7 tickers del panel (AAPL, JPM, XOM, NVO, PLTR, O, NFLX): coincide a 1e-9 en todas las señales |
| Lectura conductual del mercado | Anclaje al máximo de 52 semanas: 7. Sobrerreacción sin deterioro fundamental: 2 (NFLX, NVO). Extrapolación del crecimiento pasado: 4 (AMZN, ASML, NVDA, V) |
| Titulares de 7 días | Finnhub `company-news` es gratuito en el plan actual (comprobado con la clave el 2026-10-17: AAPL, 247 titulares). Se muestran los 5 más recientes de la propia empresa, sin interpretar |
| D5 | El contexto se calcula después del veredicto y nada del motor lo lee (test estructural); 0 cambios de nivel en el panel |
| Tiempo del panel en replay | 8.6 s (8.1 s en F4) |
| Suite | 3902 passed; falla 1, las muestras forzadas del contrato, que van con los golden |

## 1. Qué se hizo

| Commit | Qué |
|---|---|
| `9363163` | Serie del ETF del sector en el análisis (`price_history.sector`, en caché 6 h por proceso y compartida por sector); `peek` lee las series ya descargadas sin volver a pedirlas. Fixtures de los 11 ETF derivados sin red de la captura de F5prep. |
| `309ed32` | `lib/market_context.py`, la sección "Contexto de mercado" (web: pestaña propia; PDF: sección 07), los predicados del guardián (`market_signal` y `behavioral`), los titulares y el contraste independiente. |

Decisiones que F5prep dejó para esta fase, tomadas con criterio de analista:

- **Huecos sueltos:** hasta 5 sesiones sin cotización se toleran y se declaran. No falsean el momentum ni la caída máxima. Un salto de un día (posible split sin ajustar) sigue bloqueando.
- **Calendario:** el del S&P 500 solo vale para lo que cotiza en dólares (acciones y ADR). MC.PA tiene los festivos de París.
- **Escisiones registradas como split (UL):** siguen con su nota en la beta y en las caídas (decisión del usuario en F5prep), sin bloquear.
- **Ventana:** la serie del análisis es de 2 años, así que la caída máxima se da a 1 año y para la serie entera. Pasar a 5 años exigiría recapturar todos los fixtures y otra descarga más larga en producción; no compensa para contexto.

## 2. Revisión de las lecturas conductuales

La revisión que el plan reserva al usuario ("revisa 5 lecturas y comprueba que ninguna suena a recomendación") la hace el operador bajo la delegación:

| Ticker | Lectura | ¿Suena a recomendación? | Juicio de analista |
|---|---|---|---|
| AAPL | Cotiza a un 1.5% de su máximo de 52 semanas; el máximo actúa como ancla (George y Hwang, 2004) | No: describe un sesgo documentado, sin "comprar" ni "vender" | Correcta |
| NFLX | 47.3% bajo su máximo de 2 años sin deterioro de los fundamentales medidos (ingresos +12.6%, BPA +36.5% a 3 años): patrón de sobrerreacción (De Bondt y Thaler, 1985). "No es una previsión." | No: cierra con "No es una previsión" | Correcta; el matiz "medidos" es necesario |
| NVO | 67.8% bajo su máximo sin deterioro de los fundamentales medidos (65.2% antes de la revisión, que medía sobre el cierre ajustado) | No | Correcta en lo que mide. Un analista sabe que la caída descuenta competencia futura (GLP-1) que los datos pasados no recogen: "medidos" lo deja dicho |
| NVDA | El precio exige 21.1% anual 10 años (logró 44.6%); solo menos del 1% de las comparables lo sostuvo: da por hecho que el crecimiento pasado continúa (Lakonishok, Shleifer y Vishny, 1994) | No | Correcta. La primera redacción decía "en línea con el 44.6%", que era falso, y se corrigió |
| V | Exige 12.5% (logró 11.2% en 10 años); solo un 7% de las comparables lo sostuvo | No | Correcta |

Criterios que se endurecieron en la revisión:

- **Sobrerreacción:** exige además que el BPA no caiga. MC.PA (ingresos +0.7%, BPA a la baja) dejó de llamarse "sin deterioro".
- **Cíclicas:** se excluyen de la sobrerreacción. Su caída es el ciclo y su BPA es de ciclo medio.

## 3. Revisión externa (fuera del panel)

| Ticker | Resultado |
|---|---|
| NOW | Tres series correctas. Extrapolación: exige 23.0% (logró 24.1% en 8 años); menos del 1% de las comparables lo sostuvo |
| DE | Señales completas. Ninguna lectura conductual: cíclica, sin anclaje |
| SAN | Señales completas, con XLF como referencia sectorial |

## 4. Web

Pestaña "Contexto de mercado" comprobada en el navegador (NFLX, replay). La compilación de prueba no se versiona.

## 5. Lo que no se hizo y por qué

- **PEAD (deriva tras resultados):** la fecha de resultados ya se lee (2b, T3), pero hace falta la sorpresa del BPA frente al consenso y no hay fuente con fecha para ella. El informe lo dice.
- **Latencia desde Render:** el plan pedía medirla antes de construir. Sin deploy no se puede. La serie de la empresa y la del índice ya se descargaban desde la 2b; lo nuevo es el ETF del sector, cacheado 6 h y compartido por sector, más una llamada a Finnhub para los titulares, cacheada. Se mide en la comprobación de producción de esta fase.
- **Golden, deploy y push:** pendientes del usuario, como en las fases 3 y 4.

## 6. Revisión de código de la fase 5

Revisión independiente del diff de F5. Arreglos en un commit (prefijo F5), verificados con el panel en replay y la suite (3907 passed; falla la de siempre, la de los golden).

| Hallazgo | Arreglo |
|---|---|
| 1. El ETF del sector y los titulares se pedían en serie dentro del análisis, sin límite de espera | Se piden en paralelo, con un máximo de `wait_timeout_s` (4 s). Si no llegan a tiempo, la sección dice por qué y el análisis sigue |
| 2. La sobrerreacción leía el "retorno total" (ingresos más rentabilidad por dividendo) como si fueran ingresos | Lee el CAGR de ingresos a 3 años de los estados (`classification.inputs.revenue_cagr_3y`). El guardián comprueba la misma cifra |
| 3. La fuerza relativa comparaba MC.PA (en euros) con un ETF de EE. UU. en dólares | Solo se calcula para lo que cotiza en USD. El resto dice por qué no hay dato |
| 4. Un volumen muy por debajo de lo habitual (z ≤ −2) se describía como "rango habitual" | Ahora dice "muy por debajo de lo habitual" |
| 5. La distancia al máximo se medía sobre el cierre ajustado, que rebaja los precios pasados por los dividendos | Se mide sobre la cotización sin ajustar, la que ve el lector (NVO: 65.2% → 67.8%). La caída máxima sigue en ajustado, porque es rentabilidad del accionista |
| 6. "Tiende a revertir" y "tiende a infravalorar" anticipaban el precio | Las dos lecturas describen el sesgo estudiado y cierran con "no una previsión" |
| 7. `peek` devolvía series caducadas | Solo devuelve entradas vigentes |
| 8. Un sector sin ETF propio usaba SPY como "sector" | Sin fuerza relativa, y se dice |
| 9. La extrapolación decía "en los últimos 10" sin unidad ni magnitud | "(sus ingresos por acción: 19.2% anual en los últimos 10 años)" |
| 10. Los titulares no se graban en los fixtures | **Limitación declarada:** en replay la sección sale sin titulares ("sin clave"), y el contraste independiente no los cubre. Se prueban con un doble de Finnhub (`test_news_are_the_company_own_most_recent_headlines`) y se verificaron en vivo el 2026-10-17 |

Además, un fallo del ETF del sector queda en caché negativa durante `sector_fail_ttl_s` (600 s). Así un ETF caído no vuelve a costar el tiempo de espera en cada análisis del mismo sector.
