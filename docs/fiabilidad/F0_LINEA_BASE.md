# Fase 0 · Línea base de fiabilidad (F1–F5)

*Operador F0, 14-oct-2026. Es la vara contra la que se mide cada fase siguiente. Plan:
[`../PLAN_FIABILIDAD.md`](../PLAN_FIABILIDAD.md) §0 (propiedades) y §3 (panel). Bitácora: [`BITACORA.md`](BITACORA.md),
registros #2–#5.*

## Cómo se obtuvo

| | |
|---|---|
| Panel | 31 tickers en 9 grupos (`fixture_backend.PANEL_GROUPS`); SPY debe rechazarse con 422 |
| Captura | 14-oct-2026, **16:15–16:17 Nueva York** (tras el cierre: los 31 con el precio de cierre del día), local, `capture_fixtures.py --env panel --render-sim` |
| Método | Render simulado (S1: quoteSummary 401; S2: `ticker.info` vacío) → plan B + Finnhub, como en producción. Validado contra finanzer.app en JPM y NFLX: con la Rf y el precio de prod, **0 diferencias** (registro #4) |
| Entorno | `.venv313` (Python 3.13.4, yfinance 1.7.0, pandas 3.0.6, curl_cffi 0.16.3), commit `f9d6c30` (motor de producción `9e78f3b` + documentación) |
| Finnhub | Participó en los 31 (6–16 campos por ticker), a ≤ 1 petición cada 1.1 s |
| Rf | Congelada a la de config (5.29%) en fixtures y replay; producción usa ^TNX (5.19% hoy) |
| Golden | `tests/golden/panel/` (31), generados con el motor **tal como está**: describen el comportamiento actual, con sus bugs |
| Corridas | `panel_run` replay y live (finanzer.app, concurrencia 3, 16:17–16:21 NY) en `~/Downloads/finanzer_f0_panel_2026-10-14/{replay,live}` (resumen.md/csv, JSON, PDF, texto y PNG por página) |
| Suite | `../.venv313/bin/python -m pytest tests` → **1538 passed, 1 skipped, 2 xfailed** (51 s): el panel entra en la regresión, el determinismo y los 26 invariantes genéricos |

## Resumen de una línea por propiedad

| # | Propiedad | Línea base (14-oct-2026) |
|---|---|---|
| F1 | Dato correcto | No medible aún frente a la fuente oficial (fase 2). Hoy: Finnhub sustituye entre 6 y 16 campos por ticker; 12 de 30 tienen intervenciones de validación; Altman sin dato en JNJ; Yahoo da a Render datos distintos que a local en **7/30** |
| F2 | Método adecuado | **24/31** coinciden con la tabla propuesta (incluido SPY 422); 4 no coinciden (CAT, PLTR, NVDA, CRWD → "Madura"); 1 dudoso (BRK-B); 2 a decidir (TSM → MATURE, ASML → CYCLICAL) |
| F3 | Texto fiel al dato | 1 contradicción de cifra (PLTR "EBIT negativo" con EBIT +2.63 B); "STRONG" en 4 financieras; códigos internos en el detalle técnico del PDF en 30/30; panel "Composición" tapado y recortado en la página 2; 2 invariantes genéricos que fallan (XOM, DOW); cota del ciclo medio presentada como dato en 5 cíclicas |
| F4 | Incertidumbre honesta | Calidad ≥ 95 en 5/30 (100 en 3); un solo método de precio evaluable en **18/30**; DCF de fiabilidad baja en 11/19 con DCF; confianza media en 24/30; NVO cambia de nivel de precio con 10 pb de Rf |
| F5 | Reproducible | Determinismo: byte a byte en los 31 (suite). Live frente a replay: 23/30 solo difieren por Rf o precio; 7/30 con diferencias reales de datos (Render ≠ local), sin cambio de nivel salvo NVO (por la Rf). Latencia /api/analysis: p50 6.7 s · p95 45.9 s · máx 52.5 s; JPM en frío 46.1 s (14:28) y 10.8 s en la corrida del panel |

## F1 · Dato correcto (lo medible hoy)

La verdad frente a la fuente oficial (SEC EDGAR) es la fase 2. Hoy se registra cuánto depende cada informe de la
fuente secundaria, cuánto corrige la validación y qué dato clave falta.

| Ticker | Campos de Finnhub | Intervenciones de validación | Reglas | Campos clave ausentes | Errores de procedencia |
|---|---|---|---|---|---|
| AAPL | 16 | 0 | — | — | 0 |
| MSFT | 16 | 0 | — | — | 0 |
| KO | 16 | 0 | — | — | 0 |
| PG | 16 | 0 | — | — | 0 |
| JNJ | 16 | 0 | — | altman (sin dato) | 0 |
| JPM | 11 | 1 | crecimiento_financiera_estados:revenueGrowth | operating_income | 0 |
| BAC | 12 | 1 | crecimiento_financiera_estados:revenueGrowth | operating_income | 0 |
| PGR | 16 | 1 | crecimiento_financiera_estados:revenueGrowth | operating_income | 0 |
| V | 16 | 0 | — | — | 0 |
| BRK-B | 14 | 1 | crecimiento_financiera_estados:revenueGrowth | operating_income | 0 |
| O | 16 | 0 | — | — | 0 |
| PLD | 15 | 0 | — | — | 0 |
| AMT | 16 | 0 | — | — | 0 |
| NEE | 16 | 0 | — | — | 0 |
| DUK | 16 | 0 | — | — | 0 |
| XOM | 16 | 0 | — | — | 0 |
| FCX | 16 | 1 | crecimiento_incoherente:revenueGrowth | — | 0 |
| CAT | 16 | 0 | — | — | 0 |
| MU | 15 | 2 | crecimiento_artefacto:revenueGrowth, crecimiento_incoherente:revenueGrowth | — | 0 |
| DOW | 14 | 2 | multiplo_no_significativo:key_metrics.pe, multiplo_no_significativo:ratios.pe | pe | 0 |
| PLTR | 12 | 3 | crecimiento_incoherente:revenueGrowth, ratio_no_significativa:key_metrics.interest_coverage, ratio_no_significativa:ratios.interest_coverage | — | 0 |
| NVDA | 16 | 1 | crecimiento_incoherente:revenueGrowth | — | 0 |
| CRWD | 9 | 4 | pe_implausible:trailingEps, pe_implausible:trailingPE, ratio_no_significativa:key_metrics.interest_coverage, ratio_no_significativa:ratios.interest_coverage | — | 0 |
| RIVN | 8 | 8 | multiplo_no_significativo:key_metrics.ev_ebitda, multiplo_no_significativo:key_metrics.p_ffo, multiplo_no_significativo:key_metrics.pe, multiplo_no_significativo:ratios.ev_ebitda, multiplo_no_significativo:ratios.p_ffo, multiplo_no_significativo:ratios.pe, ratio_no_significativa:key_metrics.net_debt_to_ebitda, ratio_no_significativa:ratios.net_debt_to_ebitda | forward_pe, pe | 0 |
| SNOW | 6 | 8 | multiplo_no_significativo:key_metrics.ev_ebitda, multiplo_no_significativo:key_metrics.p_ffo, multiplo_no_significativo:key_metrics.pe, multiplo_no_significativo:ratios.ev_ebitda, multiplo_no_significativo:ratios.p_ffo, multiplo_no_significativo:ratios.pe, ratio_no_significativa:key_metrics.net_debt_to_ebitda, ratio_no_significativa:ratios.net_debt_to_ebitda | pe | 0 |
| TSM | 15 | 0 | — | — | 0 |
| ASML | 15 | 0 | — | — | 0 |
| NVO | 15 | 0 | — | — | 0 |
| NFLX | 11 | 0 | — | — | 0 |
| AMZN | 12 | 0 | — | — | 0 |

Notas:
- `operating_income` ausente en las 4 financieras es esperado (no tienen EBIT bancario); el P/E ausente en DOW,
  RIVN y SNOW es "no significativo" (beneficio ≤ 0), no un hueco de la fuente.
- **JNJ sin Altman** (utilidades retenidas): sigue abierto (fase 2).
- **Render ≠ local en 7/30** (registro #5): con la misma hora y las mismas versiones, Yahoo devuelve a Render otras
  acciones (PG, NEE, MSFT), otro balance trimestral (DUK al 31-mar frente al 30-jun), sin acciones diluidas
  trimestrales (CAT, DUK), otro balance en el Altman de NVDA y otros trimestres con resultado operativo en PLD.
  Recapturar en local da lo mismo (6/7 idénticos; PLD solo cambia de precio), así que la variación es de la fuente
  según el origen, no del método de captura. Efecto en el veredicto: solo DUK (calidad 71 → 74, mismo nivel).

## F2 · Método adecuado: arquetipo obtenido frente al esperado

La tabla de expectativas es la **propuesta del planificador, pendiente de validar por el usuario**; no es la verdad.

| Ticker | Grupo | Obtenido | Regla | Esperado | Coincide |
|---|---|---|---|---|---|
| AAPL | Madura | MATURE | por_defecto | MATURE | sí |
| MSFT | Madura | MATURE | por_defecto | MATURE | sí |
| KO | Madura | MATURE | por_defecto | MATURE | sí |
| PG | Madura | MATURE | por_defecto | MATURE | sí |
| JNJ | Madura | MATURE | por_defecto | MATURE | sí |
| JPM | Financiera | FINANCIAL | industria_banco | FINANCIAL | sí |
| BAC | Financiera | FINANCIAL | industria_banco | FINANCIAL | sí |
| PGR | Financiera | FINANCIAL | industria_aseguradora | FINANCIAL | sí |
| V | Financiera | MATURE | red_de_pagos | MATURE | sí |
| BRK-B | Financiera | FINANCIAL | industria_aseguradora | FINANCIAL | dudoso |
| O | REIT | REIT | industria_reit | REIT | sí |
| PLD | REIT | REIT | industria_reit | REIT | sí |
| AMT | REIT | REIT | industria_reit | REIT | sí |
| NEE | Utility | UTILITY | industria_utility | UTILITY | sí |
| DUK | Utility | UTILITY | industria_utility | UTILITY | sí |
| XOM | Cíclica | CYCLICAL | industria_ciclica | CYCLICAL | sí |
| FCX | Cíclica | CYCLICAL | industria_ciclica | CYCLICAL | sí |
| CAT | Cíclica | MATURE | por_defecto | CYCLICAL | no |
| MU | Cíclica | CYCLICAL | industria_ciclica_condicional | CYCLICAL | sí |
| DOW | Cíclica | CYCLICAL | industria_ciclica | CYCLICAL | sí |
| PLTR | Crecimiento rentable | MATURE | por_defecto | CRECIMIENTO_RENTABLE | no |
| NVDA | Crecimiento rentable | MATURE | ciclica_condicional_estable | CRECIMIENTO_RENTABLE | no |
| CRWD | Crecimiento rentable | MATURE | por_defecto | CRECIMIENTO_RENTABLE | no |
| RIVN | Pre-beneficio | GROWTH_PRE_PROFIT | pre_beneficio_con_crecimiento | GROWTH_PRE_PROFIT | sí |
| SNOW | Pre-beneficio | GROWTH_PRE_PROFIT | pre_beneficio_con_crecimiento | GROWTH_PRE_PROFIT | sí |
| TSM | ADR / IFRS | MATURE | ciclica_condicional_estable | ? | a decidir |
| ASML | ADR / IFRS | CYCLICAL | industria_ciclica | ? | a decidir |
| NVO | ADR / IFRS | MATURE | por_defecto | MATURE | sí |
| NFLX | Casos trampa | MATURE | por_defecto | MATURE | sí |
| AMZN | Casos trampa | MATURE | por_defecto | MATURE | sí |
| SPY | Casos trampa | HTTP 422 | — | 422 | sí |

Resumen: {'sí': 24, 'dudoso': 1, 'no': 4, 'a decidir': 2}

Lectura:
- **No coinciden (4):** CAT (maquinaria) sale "Madura" por defecto; PLTR, NVDA y CRWD salen "Madura" porque no
  existe el arquetipo "crecimiento rentable" (D4). NVDA entra por `ciclica_condicional_estable`.
- **Dudoso (1):** BRK-B como aseguradora (conglomerado; RECON §7.16).
- **A decidir (2):** TSM sale MATURE (`ciclica_condicional_estable`) y ASML CYCLICAL (`industria_ciclica`): la misma
  industria de semiconductores acaba en dos arquetipos distintos.
- DOW sí sale CYCLICAL en el panel (la corrida del 14-oct la vio "Madura"; la bitácora conserva aquella fila).

## F3 · Texto fiel al dato: inventario (no guardián)

### Barrido automático del texto de los 30 PDF

| Hallazgo | Tickers | Detalle |
|---|---|---|
| Cifra contradicha por el texto | PLTR | "con EBIT negativo y caja neta" con `operating_income` = +2.63 B (la cobertura de intereses de Finnhub es negativa: intereses netos de ingresos) |
| Palabra en inglés | JPM, BAC, PGR, BRK-B | "Salud financiera bancaria de 10/10 (STRONG)" |
| Código interno en el PDF | 30/30 | Línea del detalle técnico: `MATURE`, `por_defecto`, `industria_banco`, `crecimiento_incoherente`, `pe_implausible`… (D1) |
| Cota presentada como dato medido | XOM, DOW (ingresos y BPA −5.0%), FCX (BPA −5.0%), MU y ASML (+10.0%) | El crecimiento de ciclo medio está acotado a [−5%, 10%]; el texto dice "se contraen un 5.0% anual de ciclo medio" sin decir que es el tope |
| "En máximos/mínimos" frente a la posición en el rango de 52 semanas | — | Sin contradicciones |

### Invariantes genéricos sobre el panel (26 × 30 = 780 comprobaciones)

| Invariante | Ticker | Valor | Lectura |
|---|---|---|---|
| `growth_texts_cite_the_scored_figure` | XOM | puntúa `raw` = −0.05; la intro dice "se contraen un 5.0% anual de ciclo medio"; el invariante busca "-5.0%" | Probable falso positivo del invariante con crecimientos negativos (el texto es fiel al signo). Decidir si se ajusta el invariante (fase 1). xfail estricto |
| `growth_texts_cite_the_scored_figure` | DOW | ídem (−0.05) | Ídem. xfail estricto |

Las otras 778 pasan. `test_invariants_detectan.py` prueba que los 26 detectan su violación.

### Maquetación (PNG de la página 2)

- **Panel "Composición de las dos puntuaciones"**: más estrecho que la página, con un hueco grande encima;
  "Lectura del análisis" se le monta encima y **tapa filas** (AAPL: no se ven Calidad de Ganancias ni Crecimiento;
  JPM: tapa la nota al pie); las cifras del margen derecho quedan cortadas ("-4", "-2", "/20"). Es la misma
  plantilla en todos los informes (fase 1).

## F4 · Incertidumbre honesta

| Medida | Panel (30 analizados) |
|---|---|
| Calidad ≥ 95 | **5**: V 96, NVDA 95, PLTR 100, TSM 100, NFLX 100 |
| Niveles de calidad | excelente 17 · sólida 9 · media 2 · débil 2 |
| Niveles de precio | muy exigente 3 · exigente 10 · razonable 16 · atractivo 1 |
| Confianza | alta 4 · media 24 · baja 2 |
| Métodos de precio evaluables | 2 métodos en 12 · **un solo método en 18**: AAPL, MSFT, O, PLD, AMT, NEE, DUK, FCX, CAT, MU, PLTR, NVDA, CRWD, RIVN, SNOW, TSM, ASML, AMZN |
| DCF | ok 19 · no aplica 10 · no significativo 1; fiabilidad baja **11** (AAPL, MSFT, FCX, CAT, MU, PLTR, NVDA, CRWD, SNOW, TSM, ASML), alta 6, media 2 |
| Sensibilidad a la Rf | **NVO** pasa de "razonable 58" (Rf 5.29%) a "atractivo 70" (Rf 5.19%) y de confianza media a alta: 10 pb de Rf mueven el nivel |

Con 18/30 en un solo método evaluable, el techo estructural de RECON §7.17 (D3) afecta a más de la mitad del panel.

## F5 · Reproducible y estable

- **Determinismo:** los 31 dan salidas idénticas byte a byte en el mismo proceso y entre procesos con
  `PYTHONHASHSEED` distinto (`test_determinism.py` con el panel). Regresión: 31 golden de análisis y de texto del PDF.
- **Live frente a replay** (`panel_run --mode live`, misma tarde, precio de cierre): cada diferencia se separa
  repitiendo el replay con la Rf y el precio del servidor.

| Ticker | Solo Rf | Solo precio | Reales | Cambia arquetipo/calidad/precio/confianza |
|---|---|---|---|---|
| AAPL | 113 | 0 | 0 | — |
| MSFT | 113 | 0 | 7 | — |
| KO | 121 | 0 | 0 | — |
| PG | 78 | 0 | 107 | — |
| JNJ | 121 | 0 | 0 | — |
| JPM | 29 | 0 | 0 | — |
| BAC | 28 | 0 | 0 | — |
| PGR | 27 | 0 | 0 | — |
| V | 124 | 0 | 0 | — |
| BRK-B | 29 | 0 | 0 | — |
| O | 16 | 0 | 0 | — |
| PLD | 11 | 79 | 7 | — |
| AMT | 16 | 0 | 0 | — |
| NEE | 39 | 0 | 80 | — |
| DUK | 19 | 0 | 382 | — |
| XOM | 83 | 101 | 0 | — |
| FCX | 91 | 94 | 0 | — |
| CAT | 109 | 0 | 55 | — |
| MU | 90 | 0 | 0 | — |
| DOW | 112 | 0 | 0 | — |
| PLTR | 73 | 0 | 0 | — |
| NVDA | 113 | 0 | 10 | — |
| CRWD | 96 | 0 | 0 | — |
| RIVN | 16 | 0 | 0 | — |
| SNOW | 81 | 0 | 0 | — |
| TSM | 114 | 0 | 0 | — |
| ASML | 123 | 0 | 0 | — |
| NVO | 176 | 0 | 0 | precio_nivel, confianza |
| NFLX | 125 | 0 | 0 | — |
| AMZN | 30 | 0 | 0 | — |
| SPY | — | — | — | HTTP 422 |


  - Solo Rf: esperado (los fixtures congelan la Rf de config). Solo precio: XOM, FCX y PLD (el precio de Yahoo
    cambió después del cierre: 130.57 → 130.46 en PLD).
  - Reales en 7/30, todas por datos distintos de Yahoo en Render (F1). Ninguna cambia arquetipo, nivel de calidad,
    nivel de precio ni confianza; NVO sí cambia de nivel, pero solo por la Rf (F4).
- **Latencias del modo live** (finanzer.app, concurrencia 3, 31 peticiones):

  | | p50 | p95 | máximo |
  |---|---|---|---|
  | `/api/analysis` | 6.7 s | 45.9 s | 52.5 s (KO) |
  | `/api/pdf` | 7.9 s | 12.7 s | 13.7 s |

  Las tres primeras peticiones (AAPL 45.9 s, MSFT 49.3 s, KO 52.5 s) esperaron en la cola de un servidor que atiende
  en serie; el resto, 3–14 s. **JPM en frío: 46.1 s** (14:28, petición suelta de la validación) y 10.8 s en la
  corrida del panel. Va a la fase 6 (D6).

## Qué no mide todavía esta línea base

- F1 frente a SEC EDGAR (fase 2). - F3 sin guardián narrativo (fase 1): el barrido es un inventario con reglas
simples. - La tabla de arquetipos esperados no está validada (punto de parada 2). - La web no se mide (solo API y PDF).
