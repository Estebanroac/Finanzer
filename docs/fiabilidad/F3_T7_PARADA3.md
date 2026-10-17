# F3 · Punto de parada 3 (T7): verificación de la fase 3

> Fase 3 del plan de fiabilidad. Rama `fiabilidad/f3-metodo` (worktree `../finanzer_next-f3`). **Nada subido.**
> Trabajo hecho bajo la delegación del usuario (registro #29): las decisiones que el prompt reservaba al usuario las
> tomó el operador con criterio de analista y quedan declaradas aquí y en la bitácora. Replay del panel (sin red),
> 2026-10-17. T0 = commit `3d52202` (inicio de la fase 3).

## 0. Resumen

| | T0 | Ahora |
|---|---|---|
| Arquetipos | 6 (sin crecimiento rentable; ciclicidad por industria) | 7: CYCLICAL por 10+ ejercicios de EDGAR, GROWTH_PROFITABLE, subtipos de FINANCIAL |
| Precio con un solo método evaluable | **18/37** | **2/37** (RIVN y SNOW, pre-beneficio) |
| Precio: muy exigente / exigente / razonable / atractivo | 3 / 14 / 15 / 4 | 10 / 7 / 16 / 3 (no extremo) |
| Confianza: alta / media / baja | 5 / 28 / 3 | 10 / 23 / 3 |
| Niveles que cambian solo por la opción 3 de §7.17 | — | 3 al aplicarla en T3 (DUK, NEE, SNOW); al cierre solo SNOW (media → alta): las utilities ganaron un segundo método en T7 |
| Precio con DCF de fiabilidad baja sin el inverso mostrado | — | **0** |
| F1 (`edgar_verify --whatif`) | 91.4% | **94.9%** (1339/1411); 93.5% sin las definiciones aprobadas en T1 |
| Contraste independiente del inverso (5 tickers) | — | Δ = 0.000000 pp (tolerancia ±0.1 pp) |
| Tiempo del panel en replay (37) | 7.7 s | 7.9 s |
| Suite sin golden | — | 3659 passed; falla 1 (las muestras forzadas del contrato, que van con los golden) |
| Golden | — | **sin regenerar**: el clasificador de permisos de la sesión bloqueó `diff_golden.py --regenerate --yes` |

**Lo que queda del usuario:**

1. permitir la regeneración de los golden: `diff_golden.py --regenerate --yes` en los dos juegos y
   `contract_forced.py --write`;
2. `SEC_EDGAR_USER_AGENT` en Render, el requisito de cualquier deploy de la fase 3;
3. el "ok, pushea";
4. tras el deploy: `/api/health` y comprobación en producción (concurrencia ≤ 3) de un ticker por arquetipo, más
   PLTR, NVDA, CAT, MU, BCS, BRK-B, UL y AMZN; y la web recompilada con `npm run build` en el checkout principal.

## 1. Qué se hizo después de la parada 2 (un commit por causa)

| Tarea | Commits | Qué |
|---|---|---|
| T2 cierre | `0fe8ef0` | La ciclicidad exige apalancamiento operativo: KO pasa a MATURE |
| T3 | `f8e5750` | Una sola estructura de DCF |
| T3 | `fa9a156`, `817eda4` | FCF − SBC |
| T3 | `19def27` | DCF inverso con tasas base |
| T3 | `d71f0a2` | Opción 3 |
| T3 | `b120c33` | Web, PDF y guardián |
| T3 | `787317a` | Contraste independiente |
| T4 | `e2b4c3b` | ROTE ajustado por AT1; ROTE y ROE implícitos con sensibilidad |
| T4 | `afae76a` | Su texto |
| T4 | `1c3dbad` | P/E en financieras (registro #14) |
| T4, T7 | `6912ded` | Subtipo visible |
| T5 | `c12ad29` | Retorno total con dividendo ≥ 4% |
| T5 | `381c863` | Perímetro homogéneo (UL) |
| T5 | `e353392` | Ciclo medio de pico a pico |
| T5 | `57e8d46` | Base ≤ 0 (AMZN) |
| T5 | `afdd1d8`, `26aa866` | Mezcla del interanual y del CAGR a 3 años |
| T6 | `ceac134` | Circulante estructural, Altman referencial y avisos del Piotroski |
| T6 | `4ae7705` | Cautiva fuera de la deuda industrial (CAT) |
| T6 | `51201e2` | DuPont, margen FCF con tendencia, regla de 40, SBC y cobertura de intereses ampliada (petición del usuario) |
| T6 | `d2a6adc` | PEG a 3 años |
| T7 | `3f4be83` | Método intrínseco para FCF − SBC ≤ 0 (flujo de mantenimiento) y para utilities (P/B frente al ROE regulado) |
| T7 | `c8ab2fe` | CAGR por años de calendario (destapado en NOW) |
| T7 | `52403a2` | Fixtures externos |
| T7 | `8a58618` | Cautiva sin desglose (DE) |

GROWTH_PROFITABLE deja de ser provisional. Ya tiene herramientas propias:

- DCF inverso como método intrínseco;
- FCF − SBC;
- regla de 40;
- PEG a 3 años.

## 2. Panel final frente a T0 (arquetipo · calidad · precio · confianza)

Cada cambio de nivel tiene su regla y su commit en §1. Los cambios de arquetipo se explican en F3_T2_PARADA2.

| Ticker | Arquetipo | Calidad | Precio | Confianza |
|---|---|---|---|---|
| AAPL | MATURE → MATURE | sólida → sólida | exigente → muy exigente | media → alta |
| AMT | REIT → REIT | sólida → sólida | razonable → razonable | media → media |
| AMZN | MATURE → MATURE | sólida → media | exigente → muy exigente | media → alta |
| ASML | CYCLICAL → CYCLICAL | excelente → excelente | exigente → muy exigente | baja → media |
| BAC | FINANCIAL → FINANCIAL | sólida → sólida | razonable → razonable | media → media |
| BCS | FINANCIAL → FINANCIAL | sólida → sólida | razonable → atractivo | media → media |
| BRK-B | FINANCIAL → FINANCIAL | excelente → sólida | exigente → exigente | media → media |
| CAT | MATURE → CYCLICAL | excelente → excelente | exigente → muy exigente | media → media |
| CRWD | MATURE → MATURE | media → media | exigente → muy exigente | media → alta |
| DOW | CYCLICAL → CYCLICAL | débil → débil | razonable → razonable | baja → baja |
| DUK | UTILITY → UTILITY | sólida → sólida | razonable → razonable | media → media |
| FCX | CYCLICAL → CYCLICAL | sólida → sólida | exigente → muy exigente | media → media |
| HSBC | FINANCIAL → FINANCIAL | sólida → sólida | exigente → razonable | media → media |
| JNJ | MATURE → MATURE | excelente → excelente | exigente → exigente | media → media |
| JPM | FINANCIAL → FINANCIAL | excelente → excelente | exigente → exigente | alta → alta |
| KO | MATURE → MATURE | excelente → excelente | muy exigente → muy exigente | alta → alta |
| MC.PA | MATURE → MATURE | excelente → excelente | razonable → razonable | baja → baja |
| MSFT | MATURE → GROWTH_PROFITABLE | excelente → excelente | razonable → exigente | media → media |
| MU | CYCLICAL → CYCLICAL | excelente → excelente | exigente → muy exigente | media → media |
| NEE | UTILITY → UTILITY | sólida → sólida | razonable → exigente | media → media |
| NFLX | MATURE → MATURE | excelente → excelente | razonable → razonable | alta → media |
| NVDA | MATURE → GROWTH_PROFITABLE | excelente → excelente | razonable → razonable | media → alta |
| NVO | MATURE → GROWTH_PROFITABLE | excelente → excelente | atractivo → atractivo | alta → media |
| O | REIT → REIT | sólida → sólida | razonable → razonable | media → media |
| PG | MATURE → MATURE | excelente → excelente | exigente → exigente | media → media |
| PGR | FINANCIAL → FINANCIAL | excelente → excelente | atractivo → razonable | media → media |
| PLD | REIT → REIT | excelente → excelente | razonable → razonable | media → alta |
| PLTR | MATURE → GROWTH_PROFITABLE | excelente → excelente | exigente → muy exigente | media → alta |
| RIVN | GROWTH_PRE_PROFIT → GROWTH_PRE_PROFIT | débil → débil | razonable → razonable | media → media |
| SHEL | CYCLICAL → CYCLICAL | media → sólida | atractivo → atractivo | media → media |
| SNOW | GROWTH_PRE_PROFIT → GROWTH_PRE_PROFIT | media → media | muy exigente → muy exigente | media → alta |
| SPY | None → None | None → None | None → None | None → None |
| TM | CYCLICAL → MATURE | media → sólida | atractivo → razonable | media → media |
| TSM | MATURE → GROWTH_PROFITABLE | excelente → excelente | razonable → razonable | media → media |
| UL | MATURE → MATURE | sólida → excelente | razonable → razonable | media → media |
| V | MATURE → MATURE | excelente → excelente | muy exigente → exigente | alta → alta |
| XOM | CYCLICAL → CYCLICAL | sólida → excelente | exigente → razonable | media → baja |

Lectura por causa de los 16 cambios de nivel de precio (comparando con la corrida al cierre de T2, `0fe8ef0`, para
separar la reclasificación de los métodos):

- **El inverso de tasas base sustituye a un DCF directo que no concilia** (T3, `19def27`):
  - AAPL, ASML, CAT, CRWD, FCX, MU, PLTR y AMZN pasan de exigente a muy exigente. El precio exige crecimientos que
    menos del 10% de las comparables de su tamaño sostuvo 10 años.
  - MSFT pasa de razonable a exigente: el DCF directo, que antes no votaba, cede su voto al inverso (−4).
- **P/E aplicable a bancos** (`1c3dbad`):
  - BCS pasa de razonable a atractivo (P/E 8.5x frente a 13.0x del sector);
  - HSBC, de exigente a razonable (forward P/E con compresión de 15x a 11x).
  - En BCS, el ROTE sin preferentes resta en la otra dirección: el P/TBV pasa de atractivo a en línea.
- **ROE medio del ciclo de suscripción en aseguradoras** (`e2b4c3b`): PGR pasa de atractivo a razonable. Su P/B
  justificado baja de 7.24x a 4.38x al dejar de usar el ROE de un solo año.
- **P/B frente al ROE regulado en utilities** (`3f4be83`): NEE pasa de razonable a exigente. Descuenta un ROE del
  16.9% frente al 13.1% medio.
- **FCF − SBC** (`fa9a156`): V pasa de muy exigente a exigente. El DCF pierde fiabilidad (alta → media) y su voto
  baja de −2 a −1.
- **Ciclo medio de pico a pico** (`e353392`): XOM pasa de exigente a razonable, con confianza baja. El crecimiento
  del DCF pasa del −5% (valle a valle) al +0.6%; el DCF dice barata y los múltiplos, cara, y la confianza lo refleja.
- **Reclasificación de T2**: TM pasa de atractivo a razonable, como CYCLICAL → MATURE; explicado en F3_T2_PARADA2.

## 3. Fichas de analista (un ticker por arquetipo)

| Tipo | Ticker | Cómo lo analizaría un analista | Qué hace el motor |
|---|---|---|---|
| Madura | KO | Calidad alta y estable; precio por múltiplos y por el crecimiento que descuenta, frente a su crecimiento real (1% en ingresos por acción en 10 años, por la refranquicia) | Calidad excelente (82). Precio muy exigente: el inverso exige un 8.9% anual 10 años frente al 1.0% logrado (exigente) y múltiplos sobre el sector (−3) |
| Crecimiento rentable | MSFT | DCF inverso: qué crecimiento descuenta un P/E ~30 con un 47% de margen; tasas base de las más grandes | Exige un 23.6% anual 10 años, que solo sostuvo un 0.05% de las de más de 100 mil millones de dólares (236 casos): muy exigente; DCF directo de fiabilidad baja sustituido por el inverso; PEG a 3 años 1.3 |
| Cíclica | CAT | Ciclo medio, no el pico; deuda industrial sin Cat Financial | Ciclo medio de pico a pico (2008–2019, +0.4%), flujo de mantenimiento, deuda sin los 34.5 mil millones de la cautiva; el inverso exige un 14.4% anual: muy exigente |
| Banco | JPM | P/TBV frente a ROTE: ¿qué ROTE descuenta 3.2× el tangible? | Descuenta un ROTE del 25.7% frente al 20.0% obtenido: muy exigente; sensibilidad a ±2 pp; P/E frente al sector como segundo bloque |
| Aseguradora | PGR | P/B frente al ROE medio del ciclo de suscripción, no el de un año | ROE implícito 22.1% frente al 23.6% medio: en precio; ratio combinado sin dato (sin fuente estructurada) |
| Conglomerado | BRK-B | Valor contable (la referencia que usa la propia empresa) y suma de partes | Subtipo conglomerado (67% de ingresos no aseguradores); P/B frente al ROE medio (8.8% frente a 10.8% implícito: en precio, en el límite); suma de partes no calculada, dicho |
| REIT | O | P/FFO y lo que descuenta en FFO por acción | El inverso sobre FFO al coste del capital propio: el precio se justifica aunque el FFO por acción caiga un 1.4% anual (en precio); P/FFO +2 |
| Utility | NEE | P/B frente al ROE regulado; su FCF es negativo por diseño | ROE implícito 16.9% frente al 13.1% medio obtenido: exigente |
| Pre-beneficio | SNOW | EV/Ventas, regla de 40, FCF − SBC | FCF − SBC ≤ 0: sin método intrínseco (dicho; sin contraer la confianza por ello); EV/Ventas −2, regla de 40 −2 |

## 4. Revisión externa (fuera del panel; fixtures en `tests/fixtures/f3_externa`)

| Ticker | Por qué estresa | Resultado | Hallazgo y arreglo |
|---|---|---|---|
| NOW | Software de crecimiento rentable | GROWTH_PROFITABLE (21.2% a 3 años, 23.2% a 5; margen 11%); inverso muy exigente; calidad sólida | **Error de fondo:** el CAGR de la historia contaba puntos como años (acciones sin dato en 2014–2016) y daba 39.7% en 9 años. Arreglado (`c8ab2fe`) |
| DE | Cíclica industrial con financiera cautiva | CYCLICAL por su historia (2009, 2015, 2024–25) | Deere no etiqueta la deuda de John Deere Financial por segmento en XBRL (10-Q ni 10-K): no se separa, se dice (`8a58618`) |
| SAN | Banco europeo (ADR, IFRS) | Banco; ROTE implícito 16.3% frente al 16.5% obtenido: en precio | Sin hallazgos |

## 5. Web

Comprobado en el navegador con la app en replay (`tests/replay_server.py`), con MSFT:

- etiqueta "Crecimiento rentable", frontera y motivo;
- bloque "Crecimiento que exige el precio" con la banda "Muy exigente";
- PEG (BPA a 3 años);
- lecturas de calidad en Rentabilidad.

Por la API, un ticker de cada tipo: KO, CAT, JPM, BRK-B, O, NEE, SNOW y PLTR.

La compilación de prueba (webpack) no se versiona. El `frontend/out` del deploy se compila con `npm run build`
(Turbopack) en el checkout principal.

## 6. Mapa: filas de la fase 3

Todas hechas, salvo cuatro:

- **Movidas a la fase 6, con su motivo:**
  - BRK-B en base anual;
  - P/E (TTM) de BRK-B.

  Las dos necesitan construir el corte con los 10-Q de EDGAR (LTM = ejercicio + acumulado del año − acumulado del
  año anterior). La decisión de método que las bloqueaba ya está tomada: ingresos de EDGAR sin ganancias de
  inversión.
- **Descartadas, con su motivo:**
  - compromisos fuera de balance: XBRL solo trae el plazo, no el importe;
  - inflación de precios de TXRH: sin fuente estructurada de precios por producto.

Detalle en la bitácora.
