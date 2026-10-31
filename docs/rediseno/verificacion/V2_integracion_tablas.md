# V2 · tablas: V2_integracion (generado por backend/tools/real_sources_report.py)

Recorrido de la API: 2026-10-30T13:25:29, 8 tickers, 59 s. Semilla del universo: 20261018.

## Endpoints

| Endpoint | n | Éxito | 4xx esperado | Fallos | p50 (s) | p95 (s) |
|---|---|---|---|---|---|---|
| analysis | 8 | 8 (100 %) | 0 | — | 2.842 | 4.138 |
| html_v2 | 8 | 8 (100 %) | 0 | — | 0.001 | 0.004 |
| prices | 8 | 8 (100 %) | 0 | — | 0.536 | 1.091 |
| segments | 8 | 8 (100 %) | 0 | — | 0.001 | 0.021 |
| peers | 8 | 8 (100 %) | 0 | — | 16.018 | 32.087 |
| scenario_base | 8 | 8 (100 %) | 0 | — | 0.001 | 0.002 |
| scenario_extreme | 8 | 8 (100 %) | 0 | — | 0.001 | 0.005 |
| scenario_years_422 | 3 | 3 (100 %) | 0 | — | 0.001 | 0.003 |
| scenario_nan_422 | 3 | 3 (100 %) | 0 | — | 0.001 | 0.004 |
| pdf_v2 | 8 | 8 (100 %) | 0 | — | 0.295 | 0.996 |

## Páginas (historia y 9 páginas por ticker, escritorio)

80 páginas de 8 tickers: 80 sin errores de consola, sin 5xx y sin «undefined/NaN» en el texto; 0 con incidencias. Carga hasta red en reposo: p50 1.37 s, p95 1.62 s.


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
| segments | el 20-F no desglosa ingresos por segmento en XBRL | NU, ITUB |
| segments | no presenta estados en la SEC | MC.PA |
