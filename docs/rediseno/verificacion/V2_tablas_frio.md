# V2 · tablas: V2_api_frio (generado por backend/tools/real_sources_report.py)

Recorrido de la API: 2026-10-18T05:24:06, 51 tickers, 1330 s. Semilla del universo: 20261018.

## Endpoints

| Endpoint | n | Éxito | 4xx esperado | Fallos | p50 (s) | p95 (s) |
|---|---|---|---|---|---|---|
| analysis | 51 | 47 (92 %) | 3 | BF.B (404) | 2.435 | 8.496 |
| html_v2 | 51 | 51 (100 %) | 0 | — | 0.002 | 0.01 |
| prices | 51 | 51 (100 %) | 0 | — | 0.557 | 2.452 |
| segments | 51 | 51 (100 %) | 0 | — | 0.617 | 1.058 |
| peers | 51 | 51 (100 %) | 0 | — | 76.073 | 128.277 |
| scenario_base | 47 | 47 (100 %) | 0 | — | 0.001 | 0.024 |
| scenario_extreme | 47 | 47 (100 %) | 0 | — | 0.001 | 0.002 |
| scenario_years_422 | 28 | 28 (100 %) | 0 | — | 0.001 | 0.001 |
| scenario_nan_422 | 28 | 28 (100 %) | 0 | — | 0.001 | 0.001 |
| pdf_v2 | 51 | 47 (92 %) | 3 | BF.B (404) | 0.241 | 4.637 |

## Cada `sin_dato` con su motivo

| Bloque | Motivo | Tickers |
|---|---|---|
| company_profile | el emisor no presenta en la SEC | MC.PA |
| extended.company_profile | el emisor no presenta en la SEC | MC.PA |
| extended.history_10y | el emisor no presenta en la SEC | MC.PA |
| extended.next_earnings | Sin fecha anunciada | BBVA, MC.PA |
| history_10y | el emisor no presenta en la SEC | MC.PA |
| peers | sin industria de referencia para proponer rivales (puedes añadirlos a mano) | TROW, KKR, WTW, BX, AON |
| peers | sin industria de referencia para proponer rivales (puedes añadirlos a mano) (no se pudo an | SPY, ZZZZZ, SIVB |
| peers.rival | CEG: fallo (Error interno del servidor. Inténtalo de nuevo en unos minutos.) | NEE |
| peers.rival | ACLX: fallo (No data found for ACLX) | BIIB |
| prices.company | Yahoo no devolvió la serie de precios (2 intentos) | ZZZZZ, BF.B, SIVB |
| prices.sector | sin ETF de sector | SPY, ZZZZZ, BF.B, SIVB |
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
