# Diff de los golden · referencias por industria y región (Damodaran)

*Operador, 17-oct-2026. Commits `e2529d6`, `645c5c1`, `3b32491`, `6ddc780`, `a16bd93`, `c3e86d1`, `e07227e`.
Permiso del usuario: "Sí, tienes permiso para descargar los datos de Damodaran (medianas por sector y prima de riesgo
histórica) y continuar con esa tarea."*

Los golden del panel (37) y local (6), y las 4 muestras forzadas del contrato, **están sin regenerar**: esperan tu
aprobación. Este documento explica cada cambio por su causa. Los niveles se compararon en tres puntos:

- los golden actuales;
- `645c5c1` (referencias por industria y país, sin la clasificación por empresa);
- HEAD.

## 1. Causas

| # | Commit | Causa | Qué cambia en la salida |
|---|---|---|---|
| C1 | `e2529d6` | El nombre de industria de Yahoo partía el guion interno: "Beverages—Non-Alcoholic" (KO) no casaba con el mapa de Damodaran | KO usa la beta del sector (la suya tiene R² 0.01). Antes era la media de Consumer Defensive (0.80); ahora es la de Beverage (Soft), 0.64. Ke pasa de 8.66% a 7.98%, con su efecto en el WACC, el DCF y el DCF inverso de KO. Su industria de referencia es la misma función |
| C2 | `645c5c1` | Referencias por industria y región de Damodaran (agregados de enero de 2026) en lugar de la tabla por sector fijada a mano. País del emisor desde EDGAR (dirección comercial) o el sufijo del ticker | `profile.country` deja de ser "Unknown"; `benchmark` con `industry`, `sources`, `ref` y `short`; las cifras de referencia; las métricas sin fuente salen sin referencia; la puntuación de Valoración y lo que depende de ella (precio, confianza, alertas); los rótulos "de su industria", la columna INDUSTRIA y la nota de la referencia |
| C3 | `6ddc780` | "La referencia" en lugar de "la mediana", y "vs industria" en las tarjetas | Solo texto |
| C4 | `a16bd93` | La industria según la clasificación de la propia empresa en Damodaran (indname.xls), por símbolo o, para un ADR, por nombre legal y país | La industria de AAPL (Computers/Peripherals, no Electronics (Consumer & Office)), BRK-B (Diversified, no Insurance (General)), CAT (Construction Supplies) y SNOW (Software (Internet)); el resto coincide con el mapa de Yahoo |

Las demás piezas (`3b32491` frontend, `c3e86d1` gzip determinista, `e07227e` revisión de parámetros) no cambian
la salida del motor.

## 2. Por ticker

Precio: puntuación y nivel antes → en `645c5c1` → en HEAD. "Valoración (pts)": la categoría del score, de 0 a 20.
La calidad no cambia en ningún caso: sus umbrales siguen por sector, PROVISIONALES.

## panel

| Ticker | País | Referencia (HEAD) | P/E ref antes → 645 → HEAD | EV/EBITDA ref | Precio antes → 645 → HEAD | Calidad | Confianza | Valoración (pts) |
|---|---|---|---|---|---|---|---|---|
| AAPL | United States | Computers/Peripherals (us) | 30 → 20.3 → 34.3 | 20 → 20.0 | 10 muy exigente → 5 muy exigente → 15 muy exigente | 75→75 | alta→alta | 2→3 |
| AMT | United States | R.E.I.T. (us) | 35 → 28.1 → 28.1 | 20 → 19.9 | 61 razonable → 61 razonable → 61 razonable | 75→75 | media→media | 13→13 |
| AMZN | United States | Retail (General) (us) | 20 → 33.5 → 33.5 | 13 → 12.1 | 20 muy exigente → 35 exigente → 35 exigente | 60→60 | alta→alta | 4→7 |
| ASML | Netherlands | Semiconductor Equip (europe) | 30 → 38.2 → 38.2 | 20 → 20.2 | 20 muy exigente → 20 muy exigente → 20 muy exigente | 90→90 | media→media | 2→2 |
| BAC | United States | Bank (Money Center) (us) | 13 → 14.2 → 14.2 | 14 → 14.0 | 46 razonable → 54 razonable → 54 razonable | 74→74 | media→media | 9→11 |
| BCS | United Kingdom | Bank (Money Center) (europe) | 13 → 10.9 → 10.9 | 14 → 9.4 | 65 atractivo → 61 razonable → 61 razonable | 75→75 | media→media | 14→13 |
| BRK-B | United States | Diversified (us) | 13 → 27.3 → 16.8 | 14 → 11.1 | 35 exigente → 46 razonable → 35 exigente | 71→71 | media→media | 6→6 |
| CAT | United States | Construction Supplies (us) | 20 → 26.6 → 25.8 | 13 → 14.9 | 20 muy exigente → 20 muy exigente → 20 muy exigente | 84→84 | media→media | 2→2 |
| CRWD | United States | Software (System & Application) (us) | 30 → 37.5 → 37.5 | 20 → 18.0 | 5 muy exigente → 5 muy exigente → 5 muy exigente | 55→55 | alta→alta | 1→1 |
| DOW | United States | Chemical (Basic) (us) | 14 → 18.4 → 18.4 | 8 → 7.8 | 50 razonable → 50 razonable → 50 razonable | 18→18 | baja→baja | 10→10 |
| DUK | United States | Power (us) | 18 → 21.0 → 21.0 | 12 → 12.3 | 46 razonable → 46 razonable → 46 razonable | 74→74 | media→media | 9→9 |
| FCX | United States | Metals & Mining (us) | 14 → 29.4 → 29.4 | 8 → 11.3 | 28 muy exigente → 31 exigente → 31 exigente | 72→72 | media→media | 4→5 |
| HSBC | United Kingdom | Bank (Money Center) (europe) | 13 → 10.9 → 10.9 | 14 → 9.4 | 46 razonable → 40 exigente → 40 exigente | 74→74 | media→alta | 9→8 |
| JNJ | United States | Drugs (Pharmaceutical) (us) | 25 → 24.9 → 24.9 | 16 → 10.0 | 39 exigente → 30 exigente → 30 exigente | 86→86 | media→alta | 7→6 |
| JPM | United States | Bank (Money Center) (us) | 13 → 14.2 → 14.2 | 14 → 14.0 | 40 exigente → 45 razonable → 45 razonable | 91→91 | alta→alta | 8→9 |
| KO | United States | Beverage (Soft) (us) | 23 → 26.3 → 26.3 | 16 → 16.6 | 25 muy exigente → 15 muy exigente → 15 muy exigente | 81→81 | alta→alta | 5→3 |
| MC.PA | France | Apparel (europe) | 20 → 30.6 → 30.6 | 13 → 15.0 | 58 razonable → 62 razonable → 62 razonable | 80→80 | baja→baja | 13→15 |
| MSFT | United States | Software (System & Application) (us) | 30 → 37.5 → 37.5 | 20 → 18.0 | 35 exigente → 35 exigente → 35 exigente | 95→95 | media→media | 6→6 |
| MU | United States | Semiconductor (us) | 30 → 48.8 → 48.8 | 20 → 25.9 | 20 muy exigente → 20 muy exigente → 20 muy exigente | 90→90 | media→media | 2→2 |
| NEE | United States | Power (us) | 18 → 21.0 → 21.0 | 12 → 12.3 | 42 exigente → 46 razonable → 46 razonable | 69→69 | media→media | 8→9 |
| NFLX | United States | Entertainment (us) | 18 → 32.5 → 32.5 | 10 → 16.5 | 55 razonable → 61 razonable → 61 razonable | 93→93 | alta→media | 11→13 |
| NVDA | United States | Semiconductor (us) | 30 → 48.8 → 48.8 | 20 → 25.9 | 55 razonable → 58 razonable → 58 razonable | 93→93 | alta→media | 11→12 |
| NVO | Denmark | Drugs (Pharmaceutical) (europe) | 25 → 20.6 → 20.6 | 16 → 7.7 | 80 atractivo → 75 atractivo → 75 atractivo | 85→85 | alta→alta | 16→15 |
| O | United States | Retail (REITs) (us) | 35 → 31.1 → 31.1 | 20 → 16.7 | 61 razonable → 61 razonable → 61 razonable | 59→59 | media→media | 13→13 |
| PG | United States | Household Products (us) | 23 → 19.7 → 19.7 | 16 → 12.1 | 39 exigente → 30 exigente → 30 exigente | 85→85 | media→alta | 7→6 |
| PGR | United States | Insurance (Prop/Cas.) (us) | 13 → 11.8 → 11.8 | 14 → 8.4 | 61 razonable → 58 razonable → 58 razonable | 83→83 | media→media | 13→12 |
| PLD | United States | R.E.I.T. (us) | 35 → 28.1 → 28.1 | 20 → 19.9 | 50 razonable → 50 razonable → 50 razonable | 79→79 | alta→alta | 10→10 |
| PLTR | United States | Software (System & Application) (us) | 30 → 37.5 → 37.5 | 20 → 18.0 | 10 muy exigente → 10 muy exigente → 10 muy exigente | 95→95 | alta→alta | 2→2 |
| RIVN | United States | Auto & Truck (global, industria_global) | 20 → 23.7 → 23.7 | 13 → 11.3 | 50 razonable → 50 razonable → 50 razonable | 32→32 | media→media | 10→10 |
| SHEL | United Kingdom | Oil/Gas (Integrated) (europe) | 10 → 15.2 → 15.2 | 6 → 5.9 | 69 atractivo → 69 atractivo → 69 atractivo | 76→76 | media→media | 15→15 |
| SNOW | United States | Software (Internet) (us) | 30 → 37.5 → 34.8 | 20 → 15.7 | 20 muy exigente → 20 muy exigente → 20 muy exigente | 58→58 | alta→alta | 4→4 |
| TM | Japan | Auto & Truck (japan) | 20 → 9.3 → 9.3 | 13 → 7.3 | 54 razonable → 35 exigente → 35 exigente | 70→70 | media→alta | 11→7 |
| TSM | Taiwan | Semiconductor (emerging) | 30 → 26.8 → 26.8 | 20 → 13.7 | 46 razonable → 35 exigente → 35 exigente | 99→99 | media→alta | 9→7 |
| UL | United Kingdom | Household Products (europe) | 23 → 25.8 → 25.8 | 16 → 13.3 | 46 razonable → 42 exigente → 42 exigente | 81→81 | media→media | 9→8 |
| V | United States | mercado (S&P 500 + Damodaran) | 23.0 → 23.0 → 23.0 | 13.2 → 13.2 | 30 exigente → 30 exigente → 30 exigente | 96→96 | alta→alta | 6→6 |
| XOM | United States | Oil/Gas (Integrated) (global, industria_global) | 10 → 15.5 → 15.5 | 6 → 6.1 | 48 razonable → 48 razonable → 48 razonable | 82→82 | baja→baja | 9→9 |

Cambian de nivel de precio: 9 ['AMZN', 'BCS', 'FCX', 'HSBC', 'JPM', 'NEE', 'TM', 'TSM', 'UL']; de calidad: 0 []; de confianza: 7 ['HSBC', 'JNJ', 'NFLX', 'NVDA', 'PG', 'TM', 'TSM']
De esos cambios de precio, los que mueve la clasificación por empresa (645 → HEAD): ['BRK-B']

## local

| Ticker | País | Referencia (HEAD) | P/E ref antes → 645 → HEAD | EV/EBITDA ref | Precio antes → 645 → HEAD | Calidad | Confianza | Valoración (pts) |
|---|---|---|---|---|---|---|---|---|
| FCX | United States | Metals & Mining (us) | 14 → 29.4 → 29.4 | 8 → 11.3 | 24 muy exigente → 31 exigente → 31 exigente | 72→72 | media→media | 3→5 |
| JPM | United States | Bank (Money Center) (us) | 13 → 14.2 → 14.2 | 14 → 14.0 | 40 exigente → 45 razonable → 45 razonable | 91→91 | alta→alta | 8→9 |
| NFLX | United States | Entertainment (us) | 18 → 32.5 → 32.5 | 10 → 16.5 | 55 razonable → 61 razonable → 61 razonable | 93→93 | alta→media | 11→13 |
| O | United States | Retail (REITs) (us) | 35 → 31.1 → 31.1 | 20 → 16.7 | 61 razonable → 61 razonable → 61 razonable | 59→59 | media→media | 13→13 |
| SNOW | United States | Software (Internet) (us) | 30 → 37.5 → 34.8 | 20 → 15.7 | 20 muy exigente → 20 muy exigente → 20 muy exigente | 58→58 | alta→alta | 4→4 |
| V | United States | mercado (S&P 500 + Damodaran) | 23.0 → 23.0 → 23.0 | 13.2 → 13.2 | 25 muy exigente → 25 muy exigente → 25 muy exigente | 96→96 | alta→alta | 5→5 |

Cambian de nivel de precio: 2 ['FCX', 'JPM']; de calidad: 0 []; de confianza: 1 ['NFLX']
De esos cambios de precio, los que mueve la clasificación por empresa (645 → HEAD): []


## 3. Lectura de los cambios de nivel (C2, salvo BRK-B)

- **BCS y HSBC** (atractivo → razonable; razonable → exigente): se miden con la banca europea (P/E 10.9x) y no con la
  de EE. UU. Es lo que pedía la revisión externa de F1 (BCS).
- **TM** (razonable → exigente): fabricantes japoneses, a 9.3x; antes, 20x fijado a mano.
- **TSM** (razonable → exigente): semiconductores de mercados emergentes (26.8x), no 30x.
- **UL** (razonable → exigente): hogar y cuidado personal europeo; EV/EBITDA 13.3x frente a 16x.
- **JPM y NEE** (exigente → razonable), **AMZN y FCX** (muy exigente → exigente): sus industrias de EE. UU. cotizan
  por encima de la cifra que se había fijado a mano (gran banca 14.2x, Power 21.0x, Retail (General) 33.5x,
  Metals & Mining 29.4x).
- **BRK-B** (exigente → razonable → exigente): en `645c5c1` se comparaba con Insurance (General) por el mapa de
  Yahoo (27.3x). Damodaran la clasifica como Diversified (16.8x), lo coherente para un conglomerado. C4 la devuelve
  a "exigente": P/E operativo 27.1x frente a 16.8x.

**Confianza** (7 cambios). Con referencias de su industria, los métodos coinciden más o menos:

- HSBC, JNJ, PG, TM y TSM pasan de media a alta;
- NFLX y NVDA pasan de alta a media (entretenimiento 32.5x y semiconductores 48.8x: los múltiplos dejan de
  contradecir el DCF en un sentido y lo hacen en el otro).

## 4. Límites declarados

- **Agregados, no medianas.** Una industria la pueden dominar sus mayores empresas. Prueba de representatividad: si el
  P/E agregado supera en un 50% la media simple, se usa la industria global. Solo lo cruzan Auto & Truck de EE. UU.
  (Tesla, 119.6x), Chemical (Diversified) de Europa y Diversified de Japón. NVDA y MSFT siguen pesando mucho en
  semiconductores y software de EE. UU.
- **Sin referencia con fuente:** Forward P/E, PEG, P/FCF, FCF yield, ROA y crecimientos. Salen sin referencia; el
  score no los compara con ninguna (el tope del Forward P/E usa el P/E de doce meses de la industria).
- **Los umbrales del score por sector siguen PROVISIONALES.** Damodaran da niveles, no distribuciones.
- **Fecha.** Damodaran actualiza en enero: la revisión de parámetros (`config/review.toml`) avisa a partir del
  5-ene-2027.

## 5. Adenda tras la verificación en producción: C5 (`a024b7b`)

Ya regenerados los golden y desplegado (`d3de317`), la web de AAPL mostraba "ROE de 119.9% frente a −0.2% de su
industria (+70637%)".

Damodaran publica para Computers/Peripherals de EE. UU. un ROE agregado de −0.17% (igual en roe.xls y en pbvdata.xls).
El dato contradice su propia tabla:

- el margen neto agregado es de +17.8%;
- el P/B es de 34x.

Con el mismo numerador y denominadores positivos, el signo no puede diferir. Es un error del dato de origen.

**Regla:** si el ROE y el margen neto agregados tienen distinto signo y el P/B es positivo, el ROE queda sin dato.
Solo cruza la regla esa fila, de las 480.

**Diff:** solo AAPL del panel, y solo en la presentación:

- el ROE deja de tener referencia;
- el gráfico comparativo pasa de 6 a 5 métricas favorables (sale la fila del ROE);
- cambia el texto del PDF.

No cambian el score, las alertas, los niveles ni la confianza. El golden de AAPL (análisis y PDF) espera la
aprobación del usuario.
