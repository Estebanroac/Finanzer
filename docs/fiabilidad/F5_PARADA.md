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
| NVO | 65.2% bajo su máximo sin deterioro de los fundamentales medidos | No | Correcta en lo que mide. Un analista sabe que la caída descuenta competencia futura (GLP-1) que los datos pasados no recogen: "medidos" lo deja dicho |
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
