# V2 · tablas: V2_cierre_v4 (generado por backend/tools/real_sources_report.py)

Recorrido de la API: 2026-10-30T19:18:55, 9 tickers, 87 s. Semilla del universo: 20261018.

## Endpoints

| Endpoint | n | Éxito | 4xx esperado | Fallos | p50 (s) | p95 (s) |
|---|---|---|---|---|---|---|
| analysis | 9 | 9 (100 %) | 0 | — | 2.37 | 4.348 |
| html_v2 | 9 | 9 (100 %) | 0 | — | 0.001 | 0.113 |
| prices | 9 | 9 (100 %) | 0 | — | 0.497 | 1.215 |
| segments | 9 | 9 (100 %) | 0 | — | 0.001 | 0.101 |
| peers | 9 | 9 (100 %) | 0 | — | 20.06 | 36.041 |
| scenario_base | 9 | 9 (100 %) | 0 | — | 0.002 | 0.039 |
| scenario_extreme | 9 | 9 (100 %) | 0 | — | 0.001 | 0.024 |
| scenario_years_422 | 4 | 4 (100 %) | 0 | — | 0.001 | 0.01 |
| scenario_nan_422 | 4 | 4 (100 %) | 0 | — | 0.001 | 0.011 |
| pdf_v2 | 9 | 9 (100 %) | 0 | — | 0.293 | 0.879 |

## Páginas (historia y 9 páginas por ticker, escritorio)

90 páginas de 9 tickers: 90 sin errores de consola, sin 5xx y sin «undefined/NaN» en el texto; 0 con incidencias. Carga hasta red en reposo: p50 1.37 s, p95 1.64 s.


## Cada `sin_dato` con su motivo

| Bloque | Motivo | Tickers |
|---|---|---|
| company_profile | el emisor no presenta en la SEC | MC.PA |
| extended.company_profile | el emisor no presenta en la SEC | MC.PA |
| extended.history_10y | el emisor no presenta en la SEC | MC.PA |
| extended.next_earnings | Sin fecha anunciada | MC.PA |
| history_10y | el emisor no presenta en la SEC | MC.PA |
| scenario_inputs | No aplica a bancos y aseguradoras | NU, ITUB, JPM |
| scenario_inputs | No aplica a REIT | PLD |
| scenario_inputs | FCF − SBC base −$22.28B (≤ 0) | AMZN |
| segments | el informe anual (20-F) no desglosa los ingresos por segmento en un formato que se pueda l | NU, ITUB |
| segments | no presenta estados en la SEC | MC.PA |
| segments | el informe anual (10-K) no desglosa los ingresos por segmento en un formato que se pueda l | NFLX |
