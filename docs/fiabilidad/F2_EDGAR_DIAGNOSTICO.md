# F2a · T2 — Diagnóstico de SEC EDGAR para el panel

> Fase 2a del plan de fiabilidad (medir; no se corrige nada del motor). Fecha de la medida: **2026-10-15**
> (descargas entre las 15:12 y las 15:20 UTC). Herramienta: `backend/tests/edgar.py` (cliente con caché y tabla de
> conceptos) y `backend/tests/edgar_diag.py` (diagnóstico). Ninguna de las dos entra en el camino del análisis.

## 0. Resumen

- **Los 36 tickers del panel ampliado tienen CIK.** Hay 32 del panel actual y HSBC, SHEL, UL y TM, de T1. Solo SPY
  no tiene estados (es un ETF: la API responde 404) y el motor ya lo rechaza.
  **Ningún ticker del panel es un caso D7.**
- **Taxonomía:**
  - 29 presentan en `us-gaap`. Son los 28 de EE. UU. y ASML, que presenta su 20-F en US GAAP y en EUR.
  - 7 presentan en `ifrs-full`: TSM, NVO, BCS, HSBC, SHEL, UL y TM.
  - TM aparece en las dos taxonomías: pasó de US GAAP a IFRS. La herramienta elige la del balance más reciente.
- **Cobertura:** de 40 campos de la tabla, cada emisor con estados tiene concepto vigente para entre 18 (BRK-B) y
  33 (JNJ, UL).
  - **Los campos con los que el motor calcula sus métricas principales salen en los 35:** resultado neto, activo,
    caja, patrimonio, flujo de operaciones, beneficio antes de impuestos e impuesto.
  - Los huecos son de tres tipos (§4):
    - campos que no aplican (bancos sin balance clasificado);
    - etiquetas propias del emisor, que la API no publica;
    - emisores con varias clases de acción (V, BRK-B), cuyo BPA solo existe con dimensión de clase.
- **Latencia:** la descarga de `companyfacts` tarda una mediana de **0.42 s** (máximo 0.91 s, JPM). El JSON pesa
  una mediana de **3.6 MB** (máximo 8.0 MB, JPM). Es una descarga por emisor; con caché diaria, el coste es despreciable.
- **Cuatro hechos contradicen el prompt o el mapa** (§6):
  1. Cuatro emisores 20-F publican **semestrales con XBRL en 6-K**: BCS, HSBC, SHEL y UL.
  2. **La API `companyfacts` no incorpora** el 20-F de 2025 de TSM, el 20-F de FY2026 de TM ni los 6-K semestrales
     de 2026. Esos filings sí tienen XBRL, y los hechos se leen de la instancia del filing.
  3. **XOM cambió de CIK** (reorganización en holding, 2026-07-01).
  4. **ASML no es un ADR**: sus acciones ordinarias cotizan directamente, con factor 1.
- **Factores ADR verificados en la SEC** (§5):
  - TSM 5, NVO 1, BCS 4, HSBC 5, SHEL 2, UL 1, TM 10; ASML 1, sin depositario.
  - El motor usa un factor implícito (acciones de los estados / acciones de la cotización) y en **BCS aplica 4.154
    frente a 4**. La causa se mide en T3.

Reproducir (sin red, desde la caché; `--refresh` vuelve a descargar):

```bash
cd finanzer_next/backend
python3 tests/edgar_diag.py --markdown
../.venv313/bin/python -m pytest tests/test_edgar_tools.py -q
```

Salida de la corrida que respalda este informe, líneas resumen:

```
descarga companyfacts: mediana 0.42s (máx 0.91s), tamaño mediana 3.6 MB (máx 8.0 MB)
6 passed in 0.02s
```

### Método

1. **Ticker → CIK:** `https://www.sec.gov/files/company_tickers.json`. Además, el `submissions` de cada CIK da los
   formularios, el cierre fiscal y si cada filing lleva XBRL.
2. **Hechos:** `https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json`.
3. **Sucesiones de emisor:** si existe un CIK predecesor (XOM), se funden sus hechos con los del sucesor.
4. **Taxonomía:** la del `Assets` más reciente. **Moneda:** la unidad de ese `Assets`.
5. **Concepto de cada campo:** entre las alternativas de la tabla (§3), la que llega al ejercicio más reciente; si
   empatan, manda el orden de la tabla.
   - El concepto se marca **"deja de llegar"** cuando existe pero no alcanza el último ejercicio con balance (el
     emisor cambió de etiqueta).
6. **Reexpresión:** un mismo periodo (inicio, fin) aparece en varios filings con valores distintos. El valor
   vigente es el del filing más reciente (`filed`). Se mide el cambio original → vigente de los ejercicios.
7. **Límites:**
   - una petición cada 0.15 s, en serie (≤ 6.7/s; el máximo de la SEC es 10/s);
   - `User-Agent` leído del Llavero (`finanzer-sec-ua`), nunca escrito en disco ni en la salida;
   - caché cruda en `tests/fixtures/edgar/raw/` (fuera de git, 127 MB). Los **extractos** por ticker en
     `tests/fixtures/edgar/<T>.json` sí se versionan: solo los conceptos de la tabla, desde 2020, de
     10-K/10-Q/20-F/40-F; 7.9 MB en total. Son la entrada sin red de la verificación de T3.

## 1. Cobertura por ticker

"Campos (vigentes / con concepto)": de los 40 campos de la tabla, cuántos tienen un concepto que llega al último
ejercicio, y cuántos tienen alguno. "⚠ falta el último" significa que el último 10-K/20-F presentado no está en
`companyfacts` (§6.2). "FY reexpresados" cuenta los campos con algún ejercicio reexpresado.

| Ticker | CIK | Formularios | Tax. | Moneda | Cierre FY | Último FY en XBRL | Último trimestre | Campos (vigentes / con concepto) | FY reexpresados | JSON | Descarga |
|---|---|---|---|---|---|---|---|---|---|---|---|
| AAPL | 320193 | 10-K×11 10-Q×33 | us-gaap | USD | 0926 | 2025-09-27 | 2026-06-27 | 29/32 de 40 | 18 | 3.8 MB | 0.18 s |
| MSFT | 789019 | 10-K×6 10-Q×18 | us-gaap | USD | 0630 | 2026-06-30 | 2026-03-31 | 32/32 de 40 | 13 | 4.9 MB | 0.27 s |
| KO | 21344 | 10-K×8 10-Q×26 | us-gaap | USD | 1231 | 2025-12-31 | 2026-04-03 | 30/34 de 40 | 22 | 5.0 MB | 0.20 s |
| PG | 80424 | 10-K×5 10-Q×12 | us-gaap | USD | 0630 | 2026-06-30 | 2026-03-31 | 31/34 de 40 | 7 | 3.9 MB | 0.42 s |
| JNJ | 200406 | 10-K×8 10-Q×25 | us-gaap | USD | 0103 | 2025-12-28 | 2026-06-28 | 33/36 de 40 | 14 | 4.2 MB | 0.41 s |
| JPM | 19617 | 10-K×1 10-Q×3 | us-gaap | USD | 1231 | 2025-12-31 | 2026-06-30 | 25/28 de 40 | 16 | 8.0 MB | 0.86 s |
| BAC | 70858 | 10-K×1 10-Q×3 | us-gaap | USD | 1231 | 2025-12-31 | 2026-06-30 | 27/28 de 40 | 19 | 6.9 MB | 0.56 s |
| PGR | 80661 | 10-K×4 10-Q×13 | us-gaap | USD | 1231 | 2025-12-31 | 2026-06-30 | 24/30 de 40 | 7 | 5.2 MB | 0.51 s |
| V | 1403161 | 10-K×11 10-Q×35 | us-gaap | USD | 0930 | 2025-09-30 | 2026-03-31 | 26/32 de 40 | 7 | 3.6 MB | 0.45 s |
| BRK-B | 1067983 | 10-K×10 10-Q×29 | us-gaap | USD | 1231 | 2025-12-31 | 2026-06-30 | 18/22 de 40 | 10 | 2.8 MB | 0.58 s |
| O | 726728 | 10-K×11 10-Q×34 | us-gaap | USD | 1231 | 2025-12-31 | 2026-06-30 | 25/30 de 40 | 10 | 3.2 MB | 0.45 s |
| PLD | 1045609 | 10-K×7 10-Q×23 | us-gaap | USD | 1231 | 2025-12-31 | 2026-03-31 | 28/30 de 40 | 12 | 3.6 MB | 0.39 s |
| AMT | 1053507 | 10-K×9 10-Q×28 | us-gaap | USD | 1231 | 2025-12-31 | 2026-06-30 | 31/36 de 40 | 18 | 4.9 MB | 0.53 s |
| NEE | 753308 | 10-K×7 10-Q×23 | us-gaap | USD | 1231 | 2025-12-31 | 2026-03-31 | 27/30 de 40 | 20 | 3.9 MB | 0.50 s |
| DUK | 1326160 | 10-K×7 10-Q×23 | us-gaap | USD | 1231 | 2025-12-31 | 2026-03-31 | 32/36 de 40 | 19 | 5.3 MB | 0.63 s |
| XOM | 2115436 (+ CIK 34088) | 10-Q×1 | us-gaap | USD | 1231 | 2025-12-31 | 2026-06-30 | 25/28 de 40 | 2 | 0.1 MB | 0.19 s |
| FCX | 831259 | 10-K×13 10-Q×40 | us-gaap | USD | 1231 | 2025-12-31 | 2026-06-30 | 29/36 de 40 | 16 | 4.5 MB | 0.91 s |
| CAT | 18230 | 10-K×7 10-Q×23 | us-gaap | USD | 1231 | 2025-12-31 | 2026-06-30 | 30/32 de 40 | 14 | 5.9 MB | 0.76 s |
| MU | 723125 | 10-K×10 10-Q×27 | us-gaap | USD | 0903 | 2026-09-03 | 2026-05-28 | 31/34 de 40 | 12 | 4.2 MB | 0.24 s |
| DOW | 1751788 | 10-K×7 10-Q×23 | us-gaap | USD | 1231 | 2025-12-31 | 2026-03-31 | 29/34 de 40 | 0 | 2.6 MB | 0.45 s |
| PLTR | 1321655 | 10-K×6 10-Q×18 | us-gaap | USD | 1231 | 2025-12-31 | 2026-06-30 | 25/31 de 40 | 0 | 1.2 MB | 0.24 s |
| NVDA | 1045810 | 10-K×6 10-Q×18 | us-gaap | USD | 0131 | 2026-01-25 | 2026-07-26 | 31/32 de 40 | 9 | 4.1 MB | 0.27 s |
| CRWD | 1535527 | 10-K×6 10-Q×17 | us-gaap | USD | 0131 | 2026-01-31 | 2026-07-31 | 28/30 de 40 | 7 | 2.0 MB | 0.16 s |
| RIVN | 1874178 | 10-K×5 10-Q×15 | us-gaap | USD | 1231 | 2025-12-31 | 2026-06-30 | 29/30 de 40 | 0 | 1.0 MB | 0.33 s |
| SNOW | 1640147 | 10-K×4 10-Q×11 | us-gaap | USD | 0131 | 2026-01-31 | 2026-07-31 | 29/30 de 40 | 0 | 1.6 MB | 0.41 s |
| TSM | 1046179 | 20-F×12 6-K×638 | ifrs-full | TWD | 1231 | 2024-12-31 ⚠ falta el último | — (sin 10-Q) | 29/31 de 40 | 0 | 0.9 MB | 0.43 s |
| ASML | 937966 | 20-F×25 6-K×362 | us-gaap | EUR | 1231 | 2025-12-31 | — (sin 10-Q) | 30/33 de 40 | 16 | 1.8 MB | 0.46 s |
| NVO | 353278 | 20-F×10 6-K×895 | ifrs-full | DKK | 1231 | 2025-12-31 | — (sin 10-Q) | 30/32 de 40 | 6 | 0.6 MB | 0.42 s |
| NFLX | 1065280 | 10-K×3 10-Q×10 | us-gaap | USD | 1231 | 2025-12-31 | 2026-06-30 | 27/29 de 40 | 11 | 3.6 MB | 0.71 s |
| AMZN | 1018724 | 10-K×6 10-Q×18 | us-gaap | USD | 1231 | 2025-12-31 | 2026-06-30 | 28/30 de 40 | 9 | 4.5 MB | 0.18 s |
| SPY | 884394 | — | — | — | — | — | — | — | — | — | CIK sin companyfacts (HTTP 404) |
| BCS | 312069 | 20-F×5 6-K×240 | ifrs-full | GBP | 1231 | 2025-12-31 | — (sin 10-Q) | 29/32 de 40 | 12 | 1.4 MB | 0.35 s |
| HSBC | 1089113 | 20-F×3 6-K×853 | ifrs-full | USD | 1231 | 2025-12-31 | — (sin 10-Q) | 29/29 de 40 | 17 | 1.4 MB | 0.34 s |
| SHEL | 1306965 | 20-F×13 6-K×746 | ifrs-full | USD | 1231 | 2025-12-31 | — (sin 10-Q) | 32/33 de 40 | 5 | 1.4 MB | 0.34 s |
| UL | 217410 | 20-F×19 6-K×789 | ifrs-full | EUR | 1231 | 2025-12-31 | — (sin 10-Q) | 33/34 de 40 | 21 | 1.1 MB | 0.34 s |
| TM | 1094517 | 20-F×24 6-K×612 | ifrs-full | JPY | 0331 | 2025-03-31 ⚠ falta el último | — (sin 10-Q) | 30/30 de 40 | 1 | 1.8 MB | 0.50 s |


## 2. Cobertura por campo

Hay 35 emisores con estados (el panel ampliado sin SPY). La columna de la derecha muestra el último ejercicio que
trae el concepto cuando deja de llegar al actual. Ese caso no es un hueco de EDGAR: el emisor pasó a otra etiqueta
que no está en la tabla, o dejó de presentar la partida.

| Campo | Con concepto vigente | Sin concepto | Concepto que deja de llegar al último FY |
|---|---|---|---|
| revenue | 34/35 | HSBC | — |
| gross_profit | 14/35 | PG JPM BAC PGR V BRK-B O PLD AMT NEE DUK XOM FCX BCS HSBC SHEL TM | CAT (2020-12) DOW (2020-12) NFLX (2011-12) AMZN (2009-12) |
| operating_income | 25/35 | JPM BAC PGR O XOM DOW SHEL | JNJ (2014-12) BRK-B (2012-12) BCS (2021-12) |
| pretax_income | 35/35 | — | — |
| tax_provision | 35/35 | — | — |
| net_income | 35/35 | — | — |
| net_income_minorities | 21/35 | AAPL MSFT JPM BAC NVDA ASML NVO NFLX AMZN | JNJ (2014-12) PGR (2021-12) V (2014-09) NEE (2023-12) MU (2022-09) |
| discontinued_ops | 4/35 | AAPL MSFT JPM BAC PGR V BRK-B XOM CAT MU PLTR NVDA CRWD RIVN SNOW TSM ASML NVO NFLX AMZN HSBC SHEL TM | KO (2018-12) PG (2019-06) O (2014-12) PLD (2015-12) NEE (2015-12) FCX (2021-12) DOW (2021-12) BCS (2019-12) |
| interest_expense | 27/35 | NEE CAT | AAPL (2023-09) JPM (2023-12) BAC (2023-12) O (2023-12) FCX (2011-12) PLTR (2023-12) |
| net_interest_income | 6/35 | AAPL MSFT KO PG JNJ PGR BRK-B O PLD NEE XOM CAT MU DOW PLTR NVDA CRWD RIVN TSM ASML NVO NFLX AMZN SHEL UL TM | V (2023-09) AMT (2020-12) SNOW (2024-01) |
| non_interest_expense | 6/35 | AAPL MSFT KO PG JNJ PGR V BRK-B O PLD AMT NEE DUK XOM FCX CAT MU DOW PLTR NVDA CRWD RIVN SNOW TSM ASML NVO NFLX AMZN UL | — |
| depreciation | 35/35 | — | — |
| diluted_eps | 32/35 | V | BRK-B (2013-12) FCX (2021-12) |
| diluted_shares | 32/35 | V BRK-B | XOM (2013-12) |
| total_assets | 35/35 | — | — |
| current_assets | 27/35 | JPM BAC PGR BRK-B O PLD BCS HSBC | — |
| cash | 35/35 | — | — |
| short_term_investments | 14/35 | PG JPM BAC BRK-B PLD NEE FCX BCS HSBC SHEL | KO (2020-12) V (2020-09) O (2020-06) AMT (2018-12) DUK (2013-12) XOM (2010-12) CAT (2014-09) DOW (2023-03) NVDA (2025-01) CRWD (2025-01) NVO (2018-12) |
| inventories | 19/35 | JPM BAC PGR V O PLD AMT PLTR CRWD SNOW NFLX BCS HSBC | DUK (2011-12) XOM (2011-12) FCX (2013-12) |
| total_liabilities | 31/35 | KO DUK DOW AMZN | — |
| liabilities_and_equity | 35/35 | — | — |
| current_liabilities | 27/35 | JPM BAC PGR BRK-B O PLD BCS HSBC | — |
| long_term_debt | 28/35 | BRK-B SNOW BCS HSBC | PGR (2015-12) O (2016-12) PLTR (2021-12) |
| short_term_debt | 26/35 | BRK-B PLD PLTR CRWD SNOW BCS HSBC | RIVN (2023-12) TSM (2023-12) |
| total_debt_reported | 19/35 | BRK-B NEE XOM CAT CRWD SNOW TSM | KO (2023-12) PG (2015-06) JPM (2013-12) O (2016-12) AMT (2022-12) DOW (2022-12) PLTR (2020-12) ASML (2018-12) NFLX (2020-12) |
| equity_parent | 35/35 | — | — |
| minority_interest | 22/35 | AAPL MSFT JPM BAC NVDA ASML NVO NFLX AMZN | JNJ (2010-01) PGR (2015-12) V (2010-09) MU (2020-09) |
| at1_equity | 10/35 | AAPL MSFT KO BAC PGR BRK-B O NEE XOM CAT MU DOW NVDA TSM NVO SHEL UL | PG (2026-03) JPM (2009-06) V (2019-06) AMT (2014-12) DUK (2019-06) FCX (2009-03) PLTR (2021-12) ASML (2009-12) |
| at1_coupons | 6/35 | AAPL MSFT KO PG JNJ JPM V BRK-B NEE XOM CAT MU PLTR NVDA CRWD RIVN SNOW TSM ASML NVO NFLX AMZN BCS SHEL UL TM | AMT (2020-12) FCX (2015-12) DOW (2018-12) |
| retained_earnings | 33/35 | O | UL (2019-12) |
| goodwill | 24/35 | XOM RIVN TSM NFLX HSBC TM | AAPL (2017-09) PGR (2024-12) PLD (2011-09) FCX (2014-12) PLTR (2022-12) |
| intangibles | 24/35 | BRK-B XOM RIVN TSM HSBC TM | AAPL (2017-09) KO (2023-12) PGR (2022-12) MU (2025-08) PLTR (2024-12) |
| goodwill_and_intangibles | 5/35 | AAPL MSFT KO PG JNJ JPM BAC PGR V BRK-B O PLD AMT NEE DUK XOM FCX CAT MU DOW PLTR NVDA CRWD RIVN SNOW ASML NVO NFLX AMZN | SHEL (2021-12) |
| shares_outstanding | 33/35 | — | V (2009-11) BRK-B (2011-02) |
| operating_cash_flow | 35/35 | — | — |
| capex | 31/35 | JPM BAC NEE TM | — |
| dividends_paid | 28/35 | BRK-B PLTR CRWD RIVN SNOW NFLX AMZN | — |
| dividend_per_share | 22/35 | BRK-B PLTR CRWD RIVN SNOW NFLX AMZN UL TM | TSM (2018-12) ASML (2020-12) NVO (2020-12) BCS (2025-06) |
| buybacks | 24/35 | PLD RIVN TSM UL TM | PGR (2016-12) BRK-B (2024-12) NEE (2014-12) DUK (2015-12) CRWD (2021-01) AMZN (2024-12) |
| stock_based_compensation | 32/35 | BRK-B XOM TM | — |


## 3. Tabla de conceptos propuesta

Esta tabla es la que codifica `CONCEPTS` en `tests/edgar.py`.

- **Orden:** las alternativas de cada taxonomía van en orden de preferencia. Entre paréntesis, en cuántos emisores
  del panel es ese el concepto vigente.
- **"FS."** es un campo de `FinancialStatements`. **"ttm"** es una entrada de `lib/ttm.py`. **"FY"** es la serie
  anual `_statements_fy` de `yf_adapter`.
- **Signo:** "XBRL +, Yahoo −" significa que la SEC da el pago en positivo y Yahoo lo da como salida de caja
  (negativo). Al comparar, se compara el valor absoluto.
- **Unidad:**
  - la moneda de los estados es la de `Assets`;
  - lo que va por acción está en esa moneda por **acción ordinaria**, no por ADR;
  - las acciones son acciones ordinarias.

| Campo | Lo usa el motor en | us-gaap (en orden) | ifrs-full (en orden) | Signo | Unidad |
|---|---|---|---|---|---|
| revenue | FS.revenue · ttm totalRevenue · FY revenue | `Revenues` (15)<br>`RevenueFromContractWithCustomerExcludingAssessedTax` (10)<br>`RevenueFromContractWithCustomerIncludingAssessedTax` (3)<br>`SalesRevenueNet`<br>`SalesRevenueGoodsNet`<br>`RevenuesNetOfInterestExpense`<br>`RegulatedAndUnregulatedOperatingRevenue`<br>`OperatingLeasesIncomeStatementLeaseRevenue`<br>`PremiumsEarnedNet` | `Revenue` (5)<br>`RevenueFromContractsWithCustomers` (1) | igual | moneda, periodo |
| gross_profit | FS.gross_profit · ttm grossProfits · FY gross_profit | `GrossProfit` (11) | `GrossProfit` (3) | igual | moneda, periodo |
| operating_income | FS.operating_income · ttm · FY operating_income/ebit | `OperatingIncomeLoss` (20) | `ProfitLossFromOperatingActivities` (5) | igual | moneda, periodo |
| pretax_income | normalize (Pretax Income) · tasa efectiva WACC | `IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest` (23)<br>`IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments` (5)<br>`IncomeLossFromContinuingOperationsBeforeIncomeTaxesDomestic` | `ProfitLossBeforeTax` (7) | igual | moneda, periodo |
| tax_provision | normalize (Tax Provision) · tasa efectiva WACC | `IncomeTaxExpenseBenefit` (28) | `IncomeTaxExpenseContinuingOperations` (7) | igual | moneda, periodo |
| net_income | FS.net_income · ttm netIncome · Piotroski · FY net_income | `NetIncomeLoss` (26)<br>`NetIncomeLossAvailableToCommonStockholdersBasic` (2)<br>`ProfitLoss` | `ProfitLossAttributableToOwnersOfParent` (5)<br>`ProfitLoss` (2) | igual | moneda, periodo |
| net_income_minorities | (definición: ROE del accionista ordinario) | `NetIncomeLossAttributableToNoncontrollingInterest` (15) | `ProfitLossAttributableToNoncontrollingInterests` (6) | igual | moneda, periodo |
| discontinued_ops | (perímetro: escisiones y ventas) | `IncomeLossFromDiscontinuedOperationsNetOfTax` (2)<br>`IncomeLossFromDiscontinuedOperationsNetOfTaxAttributableToReportingEntity` (1) | `ProfitLossFromDiscontinuedOperations` (1) | igual | moneda, periodo |
| interest_expense | FS.interest_expense · cobertura · Kd del WACC | `InterestExpense` (4)<br>`InterestExpenseNonoperating` (14)<br>`InterestExpenseDebt` (2)<br>`InterestAndDebtExpense`<br>`InterestExpenseNet` | `FinanceCosts` (3)<br>`InterestExpense` (4) | igual | moneda, periodo |
| net_interest_income | FS.net_interest_income (estado de la cobertura; bancos) | `InterestIncomeExpenseNet` (3)<br>`InterestIncomeExpenseAfterProvisionForLoanLoss`<br>`InterestIncomeExpenseNonoperatingNet` (1) | `InterestRevenueExpense` (2)<br>`NetInterestIncomeExpense` | igual | moneda, periodo |
| non_interest_expense | FY non_interest_expense (eficiencia bancaria) | `NoninterestExpense` (2) | `OperatingExpense` (4) | igual | moneda, periodo |
| depreciation | FS.depreciation · ttm · capex de mantenimiento (CYCLICAL) | `DepreciationDepletionAndAmortization` (21)<br>`DepreciationAndAmortization` (3)<br>`DepreciationAmortizationAndAccretionNet` (2)<br>`Depreciation` (2)<br>`DepreciationAmortizationAndOther` | `DepreciationAndAmortisationExpense` (4)<br>`AdjustmentsForDepreciationAndAmortisationExpense` (1)<br>`DepreciationPropertyPlantAndEquipmentIncludingRightofuseAssets` (1)<br>`DepreciationExpense` (1)<br>`DepreciationAmortisationAndImpairmentLossReversalOfImpairmentLossRecognisedInProfitOrLoss`<br>`AdjustmentsForDepreciationAmortisationAndImpairmentLossReversalOfImpairmentLossRecognisedInProfitOrLoss`<br>`AdjustmentsForDepreciationAndAmortisationExpenseAndImpairmentLossReversalOfImpairmentLossRecognisedInProfitOrLoss` | igual | moneda, periodo |
| diluted_eps | FS.eps · FY diluted_eps (CAGR del BPA) · P/E | `EarningsPerShareDiluted` (25)<br>`EarningsPerShareBasicAndDiluted`<br>`EarningsPerShareBasic` | `DilutedEarningsLossPerShare` (6)<br>`BasicAndDilutedEarningsLossPerShare`<br>`BasicEarningsLossPerShare`<br>`DilutedEarningsLossPerShareFromContinuingOperations` (1) | igual | moneda/acción |
| diluted_shares | normalize (Diluted Average Shares) | `WeightedAverageNumberOfDilutedSharesOutstanding` (25) | `AdjustedWeightedAverageShares` (7)<br>`WeightedAverageShares` | igual | acciones |
| total_assets | FS.total_assets · ttm · Altman · Piotroski (ROA, rotación) | `Assets` (28) | `Assets` (7) | igual | moneda, saldo |
| current_assets | FS.current_assets · Altman X1 · liquidez | `AssetsCurrent` (22) | `CurrentAssets` (5) | igual | moneda, saldo |
| cash | FS.cash · deuda neta | `CashAndCashEquivalentsAtCarryingValue` (22)<br>`CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents` (5)<br>`Cash` (1)<br>`CashAndDueFromBanks` | `CashAndCashEquivalents` (7)<br>`Cash` | igual | moneda, saldo |
| short_term_investments | FS.cash (fila Yahoo 'Cash … And Short Term Investments') | `ShortTermInvestments` (4)<br>`MarketableSecuritiesCurrent` (4)<br>`AvailableForSaleSecuritiesDebtSecuritiesCurrent` (3) | `CurrentInvestments`<br>`OtherCurrentFinancialAssets` (3) | igual | moneda, saldo |
| inventories | FS.inventories · rotación de inventario · prueba ácida | `InventoryNet` (14)<br>`InventoryFinishedGoodsNetOfReserves` | `Inventories` (5) | igual | moneda, saldo |
| total_liabilities | FS.total_liabilities · Altman X4 | `Liabilities` (24) | `Liabilities` (7) | igual | moneda, saldo |
| liabilities_and_equity | (pasivo total derivado = esto − patrimonio total) | `LiabilitiesAndStockholdersEquity` (28) | `EquityAndLiabilities` (7) | igual | moneda, saldo |
| current_liabilities | FS.current_liabilities · Altman X1 · ROCE · Piotroski | `LiabilitiesCurrent` (22) | `CurrentLiabilities` (5) | igual | moneda, saldo |
| long_term_debt | FS.long_term_debt · Piotroski (apalancamiento) | `LongTermDebtNoncurrent` (15)<br>`LongTermDebtAndCapitalLeaseObligations` (5)<br>`LongTermDebt` (2)<br>`LongTermDebtAndCapitalLeaseObligationsIncludingCurrentMaturities` (1) | `NoncurrentPortionOfNoncurrentBorrowings`<br>`LongtermBorrowings` (4)<br>`NoncurrentFinancialLiabilities` (1) | igual | moneda, saldo |
| short_term_debt | FS.total_debt (componente corto plazo) | `LongTermDebtCurrent` (14)<br>`DebtCurrent` (1)<br>`ShortTermBorrowings` (3)<br>`CommercialPaper` (3)<br>`LongTermDebtAndCapitalLeaseObligationsCurrent` (1) | `CurrentBorrowingsAndCurrentPortionOfNoncurrentBorrowings` (2)<br>`CurrentPortionOfNoncurrentBorrowings`<br>`ShorttermBorrowings` (1)<br>`CurrentFinancialLiabilities` (1) | igual | moneda, saldo |
| total_debt_reported | FS.total_debt (si la empresa lo etiqueta entero) | `DebtInstrumentCarryingAmount` (7)<br>`LongTermDebt` (6)<br>`DebtAndCapitalLeaseObligations` | `Borrowings` (4)<br>`DebtSecuritiesInIssue`<br>`DebtSecurities` (1)<br>`DebtInstrumentsIssuedAtAmortisedCost` (1) | igual | moneda, saldo |
| equity_parent | FS.total_equity · ROE · P/B · Altman Z'' X4 | `StockholdersEquity` (24)<br>`StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest` (4) | `EquityAttributableToOwnersOfParent` (6)<br>`Equity` (1) | igual | moneda, saldo |
| minority_interest | (definición: patrimonio del accionista ordinario) | `MinorityInterest` (16) | `NoncontrollingInterests` (6) | igual | moneda, saldo |
| at1_equity | (definición: ROE/ROTE ordinario de bancos con AT1) | `PreferredStockValue` (7) | `OtherEquityInterest` (3)<br>`OtherEquityInstruments` | igual | moneda, saldo |
| at1_coupons | (definición: beneficio del accionista ordinario) | `PaymentsOfDividendsPreferredStockAndPreferenceStock` (2)<br>`DividendsPreferredStockCash` (1)<br>`PreferredStockDividendsIncomeStatementImpact` (2) | `PaymentsOfOtherEquityInstruments` (1) | XBRL +, Yahoo − | moneda, periodo |
| retained_earnings | FS.retained_earnings · Altman X2 | `RetainedEarningsAccumulatedDeficit` (27) | `RetainedEarnings` (6) | igual | moneda, saldo |
| goodwill | (valor contable tangible: ROTE, P/TBV) | `Goodwill` (20) | `Goodwill` (4) | igual | moneda, saldo |
| intangibles | (valor contable tangible: ROTE, P/TBV) | `IntangibleAssetsNetExcludingGoodwill` (12)<br>`FiniteLivedIntangibleAssetsNet` (8) | `IntangibleAssetsOtherThanGoodwill` (4) | igual | moneda, saldo |
| goodwill_and_intangibles | (valor contable tangible si no se separan) | `IntangibleAssetsNetIncludingGoodwill` | `IntangibleAssetsAndGoodwill` (5) | igual | moneda, saldo |
| shares_outstanding | FS.shares_outstanding · FY ordinary_shares · Piotroski | `CommonStockSharesOutstanding` (6)<br>dei: `EntityCommonStockSharesOutstanding` (26) | `NumberOfSharesOutstanding` (1) | igual | acciones |
| operating_cash_flow | FS.operating_cash_flow · ttm · Piotroski · FCF | `NetCashProvidedByUsedInOperatingActivities` (28)<br>`NetCashProvidedByUsedInOperatingActivitiesContinuingOperations` | `CashFlowsFromUsedInOperatingActivities` (7)<br>`CashFlowsFromUsedInOperations` | igual | moneda, periodo |
| capex | FS.capex · ttm capitalExpenditures · FCF | `PaymentsToAcquirePropertyPlantAndEquipment` (18)<br>`PaymentsToAcquireProductiveAssets` (5)<br>`PaymentsForCapitalImprovements` (1)<br>`PaymentsToAcquireRealEstate` (1) | `PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities` (4)<br>`PurchaseOfPropertyPlantAndEquipmentIntangibleAssetsOtherThanGoodwillInvestmentPropertyAndOtherNoncurrentAssets` (1)<br>`PurchaseOfPropertyPlantAndEquipment`<br>`PurchaseOfOtherLongtermAssetsClassifiedAsInvestingActivities` (1) | XBRL +, Yahoo − | moneda, periodo |
| dividends_paid | FS.dividends_paid · ttm dividendsPaid · payout | `PaymentsOfDividendsCommonStock` (9)<br>`PaymentsOfDividends` (8)<br>`PaymentsOfOrdinaryDividends` (4) | `DividendsPaidClassifiedAsFinancingActivities` (3)<br>`DividendsPaidToEquityHoldersOfParentClassifiedAsFinancingActivities` (3)<br>`DividendsPaid` (1) | XBRL +, Yahoo − | moneda, periodo |
| dividend_per_share | FS.dividend_per_share · rentabilidad por dividendo | `CommonStockDividendsPerShareDeclared` (14)<br>`CommonStockDividendsPerShareCashPaid` (6) | `DividendsRecognisedAsDistributionsToOwnersPerShare`<br>`DividendsPaidOrdinarySharesPerShare` (2) | igual | moneda/acción |
| buybacks | shareholder yield (recompras) | `PaymentsForRepurchaseOfCommonStock` (20) | `PaymentsToAcquireOrRedeemEntitysShares` (4) | XBRL +, Yahoo − | moneda, periodo |
| stock_based_compensation | ttm stockBasedCompensation · FCF − SBC | `ShareBasedCompensation` (21)<br>`AllocatedShareBasedCompensationExpense` (5) | `AdjustmentsForSharebasedPayments` (4)<br>`ExpenseFromSharebasedPaymentTransactionsWithEmployees` (2) | igual | moneda, periodo |

**Campos del motor que no son un concepto XBRL** (se derivan de los de arriba o vienen del mercado):

| Campo | Cómo se obtiene de EDGAR |
|---|---|
| ebitda | operating_income + depreciation (Yahoo da su propia fila 'EBITDA'; XBRL no la etiqueta) |
| ebit | operating_income (o pretax_income + interest_expense) |
| free_cash_flow | operating_cash_flow − capex (lo mismo que recalcula validate.py) |
| total_debt | long_term_debt + short_term_debt (o total_debt_reported si existe) |
| tangible_book_value | equity_parent − goodwill − intangibles |
| book_value_per_share | equity_parent / shares_outstanding (en acciones ordinarias, no ADR) |
| ffo (REIT) | net_income + depreciation inmobiliaria − plusvalías por ventas (NAREIT; sin etiqueta estándar) |

**De mercado, no son de EDGAR:**

| Campo | Fuente |
|---|---|
| price | cotización (Yahoo/Finnhub) |
| 52w high/low | cotización |
| beta | serie de precios (Finnhub/Yahoo) |
| forward_eps | estimación de analistas |
| market_cap | precio × acciones (ADR: × factor) |

Además, `dei:EntityCommonStockSharesOutstanding` da las acciones en circulación **a la fecha de portada** del
filing, que es posterior al cierre. Es el dato que usa hoy el motor como `statement_shares`: en TSM coincide al
dígito, 25,932,524,521.

## 4. Huecos: qué no da EDGAR, y para quién

| Hueco | Quién | Causa | Consecuencia |
|---|---|---|---|
| Activo y pasivo corriente | JPM BAC PGR BRK-B O PLD BCS HSBC | Balance sin clasificar (bancos, aseguradoras, REIT) | No aplica: Altman y la liquidez ya no aplican a esos arquetipos. No es un defecto |
| Margen bruto | PG JPM BAC PGR V BRK-B O PLD AMT NEE DUK XOM FCX BCS HSBC SHEL TM; deja de llegar en CAT, DOW, NFLX y AMZN | No presentan beneficio bruto en la cuenta de resultados (o dejaron de etiquetarlo) | Donde Yahoo da "Gross Profit" para estos emisores, lo **construye** (ingresos − coste); en EDGAR no hay cifra con la que verificarlo. En bancos y REIT no aplica |
| Ingresos | HSBC | HSBC presenta "net operating income" con etiqueta propia; la API solo publica etiquetas estándar | Para HSBC, los ingresos se derivan: margen de intereses (`InterestRevenueExpense`) + comisiones netas (`FeeAndCommissionIncomeExpense`) + resto. Hay que validarlo en T3 |
| Beneficio operativo | JPM BAC PGR O XOM DOW SHEL; deja de llegar en JNJ (2014), BRK-B (2012) y BCS (2021) | No lo presentan, o lo etiquetan como propio | El motor toma "Operating Income" de Yahoo, que lo **construye**. Es una partida que no se puede verificar contra EDGAR para esos emisores |
| BPA diluido y acciones medias | V; BRK-B (sin hecho no dimensional desde 2013) | Varias clases de acción: el BPA solo existe con dimensión de clase, y `companyfacts` omite los hechos dimensionales | Para verificar V y BRK-B hace falta la instancia XBRL (§6.2) o derivar beneficio / acciones por clase |
| Acciones en circulación | V, BRK-B (el `dei` deja de llegar en 2009/2011) | Ídem: `dei` por clase | Ídem |
| Gastos financieros | NEE, CAT; deja de llegar en AAPL, JPM, BAC, O y PLTR (2023) | Etiqueta propia, o cambio a "InterestExpenseNonoperating" y similares | Cobertura de intereses sin verificación para NEE y CAT. En AAPL, JPM, BAC, O y PLTR hay que añadir la etiqueta nueva a la tabla (T3) |
| Capex | JPM BAC (no aplica), NEE y TM (etiqueta propia) | NEE: "capital expenditures of NEE/FPL"; TM: "additions to fixed assets" | FCF sin verificar para NEE y TM |
| D&A | Hay concepto en los 35 | — | En TSM y HSBC solo hay depreciación de inmovilizado y de derechos de uso, sin la amortización de intangibles. Es una diferencia de **definición** |
| Dividendo por acción | UL, TM (sin concepto); TSM, ASML y NVO (dejan de llegar en 2018–2020); BCS (último en 2025-06) | Muchos emisores IFRS no etiquetan el DPA en el 20-F; hay alternativas: `DividendsPaidOrdinarySharesPerShare` (NVO, HSBC, SHEL) | **Justo el campo del defecto de Finnhub.** El DPA de esos emisores se verifica con dividendos pagados / acciones medias, en moneda de los estados |
| Instrumentos AT1 | BCS y HSBC con `OtherEquityInterest`; cupones AT1 en HSBC (`PaymentsOfOtherEquityInstruments`) | BCS no etiqueta los cupones AT1 en flujos | ROE del accionista ordinario: verificable en HSBC; en BCS, solo el saldo de AT1 |
| Utilidades retenidas | O (sin concepto); UL (deja de llegar en 2019) | O no las presenta (REIT: distribuciones acumuladas); UL las etiqueta con otra partida de reservas | Altman X2 sin verificación para O y UL (O es REIT: no aplica) |
| Todos | SPY | ETF, sin estados | El motor ya lo rechaza |

## 5. Factores ADR (fuente y fecha)

Hay dos fuentes oficiales por emisor, ambas en EDGAR:

1. **La portada del último 20-F** ("Title of 12(b) Security", página R1 del filing con XBRL; en TSM y TM, el
   documento principal).
2. **El último F-6 del depositario.** El F-6 es el registro de los ADS que presenta el banco depositario; su tabla
   de tasas describe cuántas acciones representa cada ADS.

En HSBC y TM el F-6 no escribe la cifra en el texto (va en el modelo de recibo, que es un anexo). Ahí manda el 20-F.
No se consultaron las webs de los depositarios: el F-6 es el documento del propio depositario.

| Ticker | Depositario | **Factor oficial** (acciones por ADS) | Fuente 1: 20-F (presentado) | Fuente 2: F-6 (presentado) | Factor que usa hoy el motor | Diferencia |
|---|---|---|---|---|---|---|
| TSM | Citibank | **5** acciones comunes | "each ADS represents five (5) common shares" (2026-04-16) | F-6 POS (2007-11-16): "five (5) shares of common stock" | 5.00003, aplicado | 0.0006% |
| ASML | — (no es ADR) | **1** (acción ordinaria cotizada en NASDAQ) | 12(b): "Ordinary Shares" (2026-02-25) | sin F-6 | 1.0034, no aplicado (por debajo de la tolerancia 1.5) | — |
| NVO | JPMorgan | **1** acción B | "American Depositary Receipts, each representing one B Share" (2026-02-04) | F-6 (2023-08-31): "one (1) B share" | 1.0069, no aplicado | — |
| BCS | JPMorgan | **4** acciones ordinarias de 25p | "each representing four 25p ordinary shares" (2026-02-10) | F-6EF (2025-11-20): "four (4) ordinary shares" | **4.154, aplicado** | **+3.85%** |
| HSBC | BNY Mellon | **5** acciones ordinarias | "each representing 5 Ordinary Shares of nominal value US$0.50" (2026-02-26) | F-6EF (2010-08-17); la cifra va en el anexo | pendiente de T1 | — |
| SHEL | JPMorgan | **2** acciones ordinarias | "representing two ordinary shares" (2026-03-12) | F-6 POS (2023-10-13): "two (2) ordinary shares" | pendiente de T1 | — |
| UL | Deutsche Bank | **1** acción ordinaria | "each representing one ordinary share" (2026-03-12) | F-6EF (2020-11-27): "one deposited ordinary share" | pendiente de T1 | — |
| TM | BNY Mellon | **10** acciones | "Each American Depositary Share representing ten shares" (2026-06-10) | F-6 (2021-09-21, el del cambio de 2 a 10 tras el split 5:1); la cifra va en el anexo | pendiente de T1 | — |
| BRK-B (clase) | — | **1/1500** de acción A (0.000667) | 10-K | — | 0.000672, aplicado | +0.8% |

Los factores de la tabla del planificador (HSBC 5, SHEL 2, UL 1, TM 10) **se confirman**.

**Cómo calcula el motor el factor:**

- `lib/currency.py` usa el factor **implícito**: acciones de los estados (`statement_shares`, el `dei` de portada)
  entre acciones de la cotización (capitalización / precio).
- Si se desvía de 1 más que la tolerancia, BPA y acciones se reexpresan con él.
- En BCS, 13,844,768,457 acciones (portada del 20-F, a 2025-12-31) entre 3,332,849,568 ADS-equivalentes da
  4.154. Pero 3,332,849,568 × 4 = 13,331 millones de acciones, que son las de hoy tras las recompras de 2026.

La hipótesis para T3 es que el +3.85% es un **desfase de fechas entre las dos acciones del cociente**, no un factor
distinto. Se confirma o se descarta allí con las acciones del 6-K semestral. Lo mismo vale para UL (1.012 en la
revisión externa F1), que se medirá cuando T1 capture UL.

## 6. Periodos, reexpresiones y hechos que contradicen el prompt

### 6.1 Periodos disponibles

- **10-K/10-Q (EE. UU.):**
  - la cuenta de resultados trae el trimestre (3 meses) y el acumulado (6M, 9M). El 4.º trimestre no se publica: es
    el FY menos los 9M;
  - **el estado de flujos solo trae el acumulado.** En AAPL, por ejemplo, el flujo de operaciones de 2026 aparece
    como 3M (1T), 6M y 9M; el 2T y el 3T salen por diferencia. El TTM con EDGAR es el FY más el acumulado del año
    menos el mismo acumulado del año anterior; vale para todos los flujos;
  - el balance es a la fecha de cierre de cada trimestre.
- **20-F (extranjeros):** solo el ejercicio anual, con los ejercicios comparativos.
  - **Excepción, que contradice el prompt:** BCS, HSBC, SHEL y UL publican el **semestral (6M) en 6-K con XBRL**
    desde 2024; SHEL también el trimestre. Con eso, el TTM de esos cuatro es posible (FY + 6M actual − 6M anterior).
  - TSM, NVO, TM y ASML no tienen interinos en XBRL. Los 6-K de TSM de 2021 son una excepción aislada.
- La herramienta cuenta, por concepto, los periodos FY, Q, 6M y 9M (`periods` en `diag.json`).

### 6.2 `companyfacts` no incorpora parte de los filings IFRS de 2026

| Filing (con `isXBRL=1` en EDGAR) | ¿Hechos financieros en `companyfacts`? |
|---|---|
| TSM 20-F FY2025 (2026-04-16) | **No**: solo 2 hechos `dei`/`srt`; el último ejercicio con cifras es FY2024 |
| TM 20-F FY2026, cierre 2026-03 (2026-06-10) | **No**: solo 1 hecho `dei`; el último es FY2025 (2025-03) |
| 6-K semestral 2026 de BCS (07-28), HSBC (08-04), SHEL (07-30) y UL (07-28) | **No**; los de 2025 sí están |
| 20-F FY2025 de NVO (02-04), BCS (02-10), HSBC (02-26), UL y SHEL (03-12) | Sí |

- **No es la versión de la taxonomía:** NVO y TSM declaran la misma, `ifrs` 2025-03-27, y NVO sí está.
- **No es la ausencia de XBRL:** el filing de TSM trae su instancia (`tsm-20251231_htm.xml`, 10.8 MB, descargada
  en 0.50 s) con las cifras de FY2025. Por ejemplo, el resultado atribuido a la dominante es 1,697,604 millones de
  TWD.

La causa está del lado de la API de la SEC y no se puede comprobar desde fuera. Lo que importa para la fase 2:
**para los emisores IFRS, `companyfacts` puede ir uno o dos periodos por detrás de lo presentado.** La alternativa
que funciona es leer la instancia XBRL del filing, a partir de la lista de filings de `submissions`. T3 la usa para
TSM y TM, y T4 la cuenta como coste del escenario "EDGAR principal".

### 6.3 Otros

- **XOM cambió de CIK:**
  - `company_tickers.json` da 2115436 (ExxonMobil Holdings Corp, 8-K12B del 2026-07-01), con un solo 10-Q;
  - la historia está en 34088 (Exxon Mobil Corp, 3.1 MB), que sigue presentando 10-Q;
  - la herramienta los funde (`PREDECESSORS`).

  Toda resolución automática ticker → CIK necesita esta regla de sucesión.
- **ASML** presenta en US GAAP y en EUR, y no es ADR. **TM** está en `ifrs-full` (la etiqueta del prompt, "reporta
  en JPY", es correcta; la taxonomía cambió en 2021).
- **Splits en los datos:** NVDA 10:1 (2024), NFLX 10:1, AMZN 20:1, NVO 2:1 (2023) y TM 5:1 (2021) aparecen como
  "reexpresiones" del BPA y de las acciones de los ejercicios anteriores. El valor vigente ya viene ajustado, como
  en Yahoo.

### 6.4 Reexpresiones de ejercicios desde 2021 (≥ 1%) y su causa

| Emisor | Campos y magnitud | Causa (la de UL y JNJ, comprobada con los hechos de discontinuadas; las demás, la conocida públicamente, sin leer la nota del filing) |
|---|---|---|
| **UL** | Ingresos 2024: 60,761 → **52,479** millones de EUR (−13.6%; 20-F de 2025 frente al de 2024), 2023 −13.3%; beneficio bruto −10.6%; D&A −24% a −27%; capex −20.5%; BPA −13% | **Escisión de helados (The Magnum Ice Cream Company):** los ejercicios previos se reexpresan sin el negocio, y el resultado de operaciones discontinuadas es de 3,798 millones de EUR en 2025 y 330 millones en 2024. **Caso de perímetro del mapa: confirmado en EDGAR** |
| **JNJ** | Ingresos 2022/2023 −16%; beneficio bruto −13%; existencias −17.7%; fondo de comercio −20% a −28% | Separación de Kenvue (2023): 21,827 millones de USD de resultado de discontinuadas en 2023 |
| BAC | Impuesto 2023/2024 ×2.4–3.4; beneficio antes de impuestos −14% | Cambio de método contable de las inversiones en créditos fiscales (amortización proporcional) |
| AMT | Ingresos 2022/2023 −10%; impuesto | Venta del negocio de India (ATC TIPL) como operación discontinuada |
| HSBC | Patrimonio 2021/2022 −5%; minoritarios −14%; flujo de operaciones 2022 −27% | Adopción de IFRS 17 (seguros) con reexpresión del comparativo |
| CRWD | Resultado neto FY2024: 89.3 → 72.2 millones de USD; FY2025: −19.3 → −15.2 millones (en el 10-K de 2026) | **Sin identificar** en esta medida; queda para T3 si el pipeline usa esos ejercicios |
| DUK | Impuestos 2021; discontinuadas | Reclasificación del negocio comercial renovable (discontinuado) |
| NVDA, NFLX, AMZN, NVO, TM | Solo BPA y acciones | Splits (§6.3) |

Consecuencia para T3: **la comparación usa siempre el valor vigente** (el filing más recente) y anota cuándo Yahoo
trae el original.

## 7. Qué se lleva T3 de este diagnóstico

1. **Fuente de verdad por emisor:** `companyfacts` (extracto en `tests/fixtures/edgar/<T>.json`), más la instancia
   XBRL del filing para TSM FY2025 y TM FY2026, que la API no trae.
2. **Periodo del pipeline:**
   - el TTM se compara con FY + acumulado − acumulado del mismo periodo del año anterior;
   - el balance, con la fecha del último trimestre;
   - en los 20-F sin interinos (TSM, NVO, TM y ASML), solo el ejercicio. La diferencia de periodo es justo la causa
     "periodo" de la clasificación.
3. **Moneda:** EDGAR da la moneda de los estados (TWD, DKK, GBP, EUR, JPY). La comparación deshace la conversión del
   pipeline con `data_provenance.currency`.
4. **Casos conocidos que este diagnóstico ya toca:**
   - BCS: el factor 4.154 tiene la hipótesis de las fechas de las acciones;
   - BCS: el dividendo pagado de 2025 es 1,254 millones de GBP (incluye 41 millones a minoritarios) y el
     reconocido es 1,213 millones;
   - UL: perímetro confirmado;
   - JNJ: tiene `RetainedEarningsAccumulatedDeficit` vigente, así que EDGAR sí da las utilidades retenidas que
     faltan en el pipeline.
