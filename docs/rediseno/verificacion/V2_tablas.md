# V2 · tablas: V2_api (generado por backend/tools/real_sources_report.py)

Recorrido de la API: 2026-10-18T05:52:28, 51 tickers, 604 s. Semilla del universo: 20261018.

## Endpoints

| Endpoint | n | Éxito | 4xx esperado | Fallos | p50 (s) | p95 (s) |
|---|---|---|---|---|---|---|
| analysis | 51 | 48 (94 %) | 3 | — | 2.58 | 4.009 |
| html_v2 | 51 | 51 (100 %) | 0 | — | 0.002 | 0.007 |
| prices | 51 | 51 (100 %) | 0 | — | 0.713 | 1.297 |
| segments | 51 | 51 (100 %) | 0 | — | 0.098 | 0.212 |
| peers | 51 | 51 (100 %) | 0 | — | 32.029 | 68.073 |
| scenario_base | 48 | 48 (100 %) | 0 | — | 0.001 | 0.003 |
| scenario_extreme | 48 | 48 (100 %) | 0 | — | 0.001 | 0.002 |
| scenario_years_422 | 29 | 29 (100 %) | 0 | — | 0.001 | 0.002 |
| scenario_nan_422 | 29 | 29 (100 %) | 0 | — | 0.001 | 0.001 |
| pdf_v2 | 51 | 48 (94 %) | 3 | — | 0.254 | 0.732 |

## Páginas (historia y 9 páginas por ticker, escritorio)

520 páginas de 52 tickers: 520 sin errores de consola, sin 5xx y sin «undefined/NaN» en el texto; 0 con incidencias. Carga hasta red en reposo: p50 1.06 s, p95 5.73 s.


## Cada `sin_dato` con su motivo

| Bloque | Motivo | Tickers |
|---|---|---|
| company_profile | el emisor no presenta en la SEC | MC.PA |
| extended.company_profile | el emisor no presenta en la SEC | MC.PA |
| extended.history_10y | el emisor no presenta en la SEC | MC.PA |
| extended.next_earnings | Sin fecha anunciada | BCS, MC.PA |
| history_10y | el emisor no presenta en la SEC | MC.PA |
| peers | sin industria de referencia para proponer rivales (puedes añadirlos a mano) | TROW, KKR, WTW, BX, AON |
| peers | sin industria de referencia para proponer rivales (puedes añadirlos a mano) (no se pudo an | SPY, ZZZZZ, SIVB |
| peers.rival | ACLX: fallo (No data found for ACLX) | BIIB |
| prices.company | Yahoo no devolvió la serie de precios (2 intentos) | ZZZZZ, SIVB |
| prices.sector | sin ETF de sector | SPY, ZZZZZ, SIVB |
| scenario_inputs | No aplica a bancos y aseguradoras | JPM, BCS, MUFG, HBAN, BBVA, WFC, CINF, C, CFG, BRK-B, CB, CRCL |
| scenario_inputs | No aplica a REIT | O, CPT, PLD |
| scenario_inputs | No aplica a empresas en crecimiento sin beneficio con FCF negativo | RIVN, LCID |
| scenario_inputs | No aplica a utilities reguladas | NEE |
| scenario_inputs | FCF − SBC base −$225.00M (≤ 0) | FDXF |
| segments | no presenta estados en la SEC | MC.PA, ZZZZZ, SIVB |
| segments | el 10-K no desglosa ingresos por segmento en XBRL | CPT, CB |
| segments | el 20-F no desglosa ingresos por segmento en XBRL | BBVA |
| segments | el 10-K/A no desglosa ingresos por segmento en XBRL | CRCL |
| segments | sin informe anual (10-K, 20-F o 40-F) con XBRL en la SEC | SPY |
