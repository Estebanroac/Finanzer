# V2 · tablas: V2_oficial (generado por backend/tools/real_sources_report.py)

Recorrido de la API: 2026-10-27T21:46:09, 7 tickers, 380 s. Semilla del universo: 20261018.

## Endpoints

| Endpoint | n | Éxito | 4xx esperado | Fallos | p50 (s) | p95 (s) |
|---|---|---|---|---|---|---|
| analysis | 7 | 7 (100 %) | 0 | — | 6.693 | 10.5 |
| html_v2 | 7 | 7 (100 %) | 0 | — | 0.002 | 0.003 |
| prices | 7 | 7 (100 %) | 0 | — | 0.701 | 1.422 |
| segments | 7 | 7 (100 %) | 0 | — | 0.001 | 0.019 |
| peers | 7 | 7 (100 %) | 0 | — | 140.202 | 232.428 |
| scenario_base | 7 | 7 (100 %) | 0 | — | 0.002 | 0.005 |
| scenario_extreme | 7 | 7 (100 %) | 0 | — | 0.002 | 0.003 |
| pdf_v2 | 7 | 7 (100 %) | 0 | — | 0.277 | 2.444 |
| scenario_years_422 | 2 | 2 (100 %) | 0 | — | 0.001 | 0.004 |
| scenario_nan_422 | 2 | 2 (100 %) | 0 | — | 0.001 | 0.001 |

## Páginas (historia y 9 páginas por ticker, escritorio)

70 páginas de 7 tickers: 70 sin errores de consola, sin 5xx y sin «undefined/NaN» en el texto; 0 con incidencias. Carga hasta red en reposo: p50 1.39 s, p95 2.84 s.


## Cada `sin_dato` con su motivo

| Bloque | Motivo | Tickers |
|---|---|---|
| company_profile | el emisor no presenta en la SEC | MC.PA |
| extended.company_profile | el emisor no presenta en la SEC | MC.PA |
| extended.history_10y | EDGAR no respondió a tiempo | NU |
| extended.history_10y | el emisor no presenta en la SEC | MC.PA |
| extended.next_earnings | Sin fecha anunciada | MC.PA |
| history_10y | EDGAR no respondió a tiempo | NU |
| history_10y | el emisor no presenta en la SEC | MC.PA |
| scenario_inputs | No aplica a bancos y aseguradoras | NU, ITUB, JPM |
| scenario_inputs | No aplica a REIT | PLD |
| scenario_inputs | FCF − SBC base −$22.28B (≤ 0) | AMZN |
| segments | el 20-F no desglosa ingresos por segmento en XBRL | NU, ITUB |
| segments | no presenta estados en la SEC | MC.PA |
