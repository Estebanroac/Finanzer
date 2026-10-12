# RECON — Reconocimiento del motor de análisis de Finanzer

**Etapa 1 · solo lectura** · 11-oct-2026 · contra `redesign-spec.md` (versión de 306 líneas, incluye la subsección *ROCE como métrica de contraste*).

> **Convenciones.** Rutas relativas a la raíz del repo `finanzer_next/`. `archivo:línea` o `archivo:inicio-fin`. **[DESCONOCIDO]** = no verificable desde aquí; no se supone. "Local" = ejecución en este Mac (IP residencial, **sin** `FINNHUB_API_KEY`); "prod" = Render (IP de datacenter, con Finnhub activo).
>
> **Nada se modificó.** No se instalaron dependencias (todo ya estaba en el Python del sistema). Las respuestas de las APIs y el PDF de prueba quedaron en el scratchpad de la sesión, fuera del repo.

---

## 0. Antes de empezar: qué código es "la app"

| Hecho | Evidencia |
|---|---|
| Hay **dos codebases que empujan al mismo remoto** `github.com/Estebanroac/Finanzer`. | `git remote -v` en ambos. |
| `finanzer_complete_v3/` es la versión **Dash legacy** (último commit c7c7da9, 17-mar-2026, "Restore original backup version"). No tiene `/api/pdf`; el PDF se descarga con `dcc.send_file` (`app.py:3046`). | grep |
| **`finanzer_next/` es la que genera el informe del spec y la que está en producción**: FastAPI + Next.js con export estático (último commit 66594b2, 8-jul-2026). Expone `GET /api/pdf/{symbol}` (`backend/main.py:882`), la matriz `dcf_sensitivity_analysis` y `terminal_pct`, todo lo que cita el spec. | `backend/main.py`, `backend/lib/*` |
| La descripción "Python/Dash" del brief corresponde a la versión legacy. **Este informe analiza `finanzer_next`.** | — |
| `finanzer_next` tiene un cambio sin commitear en `backend/lib/alert_interpretations.py` (estado anterior a esta recon; no se tocó). | `git status` |
| ⚠️ **Seguridad:** la URL del remoto en `finanzer_complete_v3/.git/config` lleva **un token personal de GitHub en texto plano** (`https://Estebanroac:ghp_…@github.com/…`). Recomendación: revocarlo en github.com/settings/tokens y quitarlo de la URL. No se reproduce aquí. | `git remote -v` |

---

## 1. Mapa del código actual

### 1.1 Estructura y responsabilidad por archivo

```
finanzer_next/
├── build.sh                      Build de Render: pip install + valida que frontend/out/ exista y esté completo. NO reconstruye el frontend.
├── requirements.txt              = backend/requirements.txt (fastapi 0.115, uvicorn 0.30, curl_cffi, reportlab, yfinance, pandas, numpy, requests).
├── README.md                     Arranque local (uvicorn --reload :8000; npm run dev).
├── backend/
│   ├── main.py            (1000) API FastAPI: /api/search, /api/stocks/popular, /api/analysis/{s}, /api/pdf/{s}, /api/health + sirve frontend/out.
│   │                             Contiene _compute_analysis(): EL ORQUESTADOR del análisis (L192-873) y _get_sector_benchmarks() (medianas hardcodeadas).
│   └── lib/
│       ├── yf_adapter.py  (1041) Cliente REAL de Yahoo: curl_cffi → v10/quoteSummary (1 llamada, 9 módulos) + enriquecimiento con yfinance
│       │                         (estados anuales) + defensas ante respuestas degradadas, "último bueno conocido" de 24 h y gancho a Finnhub.
│       ├── finnhub_fallback.py (299) 2.ª fuente: Finnhub /stock/metric (free tier). Solo rellena campos None. Inerte sin FINNHUB_API_KEY.
│       ├── data_fetcher.py (1789) FinancialDataService/YahooFinanceFetcher: arma CompanyProfile + FinancialStatements a partir de get_ticker_info.
│       │                         Mucho código muerto (históricos, comparación sectorial, caché de estados, FMP).
│       ├── financial_ratios.py (4684) MOTOR: ratios, Altman, Piotroski, salud financiera bancaria, WACC, DCF multietapa, sensibilidad,
│       │                         score v2 (5 categorías × 20), umbrales sectoriales (SECTOR_THRESHOLDS). Incluye un motor de alertas legacy muerto.
│       ├── alert_interpretations.py (533) "Cerebro" de señales vigente: fortalezas/advertencias/riesgos con texto adaptativo (20 intérpretes).
│       ├── pdf_report.py  (1533) Informe PDF (reportlab platypus): portada, resumen, 6 secciones, narrativa por bandas (read_*), radar, grid DCF.
│       ├── sector_profiles.py (143) Mapeo nombre de sector de Yahoo → clave canónica (11 sectores) + ETF de referencia. Nada más.
│       ├── config.py       (196) Constantes "centralizadas"; en la práctica solo se consumen 10 (Altman, DCF). El resto es decorativo.
│       └── stock_database.py (791) Diccionario ticker→nombre para búsqueda local y nombres "bonitos".
└── frontend/                     Next.js (export estático en frontend/out/, que se commitea). Solo es relevante porque DUPLICA umbrales:
    └── src/lib/sectorBench.ts (36), metricScale.ts (116); tabs/*.tsx, InfoTooltip.tsx, MetricsGrid.tsx usan bandas propias.
```

**Sin tests en `finanzer_next`** (ver §5). **Código muerto relevante:** `aggregate_alerts` (`financial_ratios.py:2658-3127`, **0 llamadas**) y todo lo que solo él usa: `get_sector_specific_adjustments` (`:2595`), `classify_all_alerts_severity` (`:1739`), `classify_valuation_alert_severity` (`:1638`), `calculate_justified_pe` (`:713`), `valuation_flags…volatility_risk_flags` (`:2211-2580`). También `data_fetcher.py`: `_stmt_cache` (`:86-129`), `get_historical_metrics`/`get_detailed_historical_data`/`get_sector_comparison_data` (0 llamadas) y el bloque CAGR/históricos de `get_complete_analysis_data` (`:1546-1646`, nunca se alimenta). Ojo: el docstring de `sector_profiles.py:9-12` presenta `get_sector_specific_adjustments` como parte de la adaptación sectorial "real", pero **no se ejecuta**.

### 1.2 Flujo de datos de punta a punta — `GET /api/pdf/NFLX`

```
download_pdf(symbol)                                   main.py:883
└─ _compute_analysis("NFLX")                           main.py:192   (valida el ticker → 400)
   ├─ data_service.get_complete_analysis_data()        data_fetcher.py:1342  (ThreadPool con solo 2 tareas, :1421-1424)
   │   ├─ YahooFinanceFetcher.get_company_profile()    data_fetcher.py:362  (caché 30 min)
   │   └─ YahooFinanceFetcher.get_financial_data()     data_fetcher.py:430  (caché 60 min) → FinancialStatements (:272-320)
   │       └─ ambas → yf_adapter.get_ticker_info()     yf_adapter.py:212  (caché 300 s / 60 s si viene degradado; lock por símbolo)
   │           ├─ _do_fetch()                          yf_adapter.py:336  GET query2.finance.yahoo.com/v10/finance/quoteSummary
   │           │    módulos: financialData, defaultKeyStatistics, assetProfile, price, summaryDetail,
   │           │             incomeStatementHistory, balanceSheetHistory, cashflowStatementHistory, earnings   (:342-348)
   │           │    si no hay 200 → refresca el crumb → si falla → _fallback_yfinance() (:886)
   │           │    └─ _enrich_prior_year_data()        yf_adapter.py:708  yfinance .income_stmt/.balance_sheet/.cashflow (anuales)
   │           │         → _prior_year, _piotroski_current, _current_derived
   │           ├─ Defensa 1: hasta 2 reintentos rotando la suplantación (chrome/safari/edge) si la respuesta viene degradada (:246-261)
   │           ├─ Defensa 3: _merge_last_known_good (<24 h) (:266, :284)
   │           └─ Defensa 4: finnhub_fallback.enrich_info() si hay key y faltan beta/forwardPE/revenueGrowth/prior ROA (:271-277)
   ├─ financials_to_dict() → calculate_all_ratios()    main.py:60 / financial_ratios.py:3130
   ├─ fallback_map con ratios precalculados de Yahoo/Finnhub   main.py:252-277 ; PEG de mercado (:285-287)
   ├─ métricas derivadas (FCF yield, P/FCF, ROIC fallback, cobertura, EV/EBITDA, forward P/E…)  main.py:306-448
   ├─ sector: YAHOO_SECTOR_MAPPING → get_sector_profile → _get_sector_benchmarks   main.py:451-467
   ├─ proxy de "CAGR 3Y" = crecimiento YoY de Yahoo (TODO fase C)                  main.py:476-484
   ├─ calculate_wacc(beta) → spread ROIC−WACC, buyback/shareholder yield            main.py:487-516
   ├─ altman_z_score(...)                              main.py:575 → financial_ratios.py:128
   ├─ piotroski_f_score(...)                           main.py:612 → financial_ratios.py:475
   ├─ calculate_score_v2(...)                          main.py:683 → financial_ratios.py:4323 (+ financial_health_score para financieras)
   ├─ graham_number / margin_of_safety                 main.py:738-748
   ├─ dcf_multi_stage_dynamic(...)  (no financieras)   main.py:772 → financial_ratios.py:2044 → dcf_multi_stage :1876
   ├─ dcf_sensitivity_analysis(...)                    main.py:802 → financial_ratios.py:4511
   ├─ build_signals(...)  (alertas)                    main.py:822 → alert_interpretations.py:500
   ├─ price_history = {52w_high, 52w_low, beta}  ← NO hay serie diaria de precios   main.py:836-841
   └─ yearly_financials (módulo earnings, ≤4 años)     main.py:846-858
└─ pdf_report.build_report(buf, analysis, _get_sector_benchmarks(mapped), logo)    main.py:907-913 → pdf_report.py:596
└─ StreamingResponse application/pdf                   main.py:916
```

`GET /api/analysis/{s}` (`main.py:876`) devuelve el mismo dict al frontend. El PDF **no recalcula nada**: solo lee el dict y aplica sus propias lecturas por banda.

### 1.3 Dónde se calcula cada bloque del informe

| Bloque | Cálculo | Render en PDF | Notas verificadas |
|---|---|---|---|
| **Score por categorías** (5×20) | `calculate_score_v2` `financial_ratios.py:4323-4504` → `score_solidez_financiera` :3276 / `…_financial` :3416 · `score_rentabilidad` :3574 · `score_valoracion` :3757 · `score_calidad_ganancias` :4113 · `score_crecimiento` :4217. Normalizado en `main.py:693-714`. | Portada (panel + barras), radar `pdf_report.py:534`. Nivel con `score_band` :260 (80/60/40/20). | Cada categoría parte de 10 y suma ajustes acotados a [0,20]. El nivel del motor usa **80/65/50/35** (:4462-4476) y el PDF **80/60/40/20** → SNOW 43 = "Precaución" en la API y "Neutral" en el PDF. |
| **Piotroski F** | `piotroski_f_score` `financial_ratios.py:475-639`. Entradas en `main.py:597-628`: año fiscal de `_piotroski_current`, año previo de `_prior_year`. | Tarjeta de modelo `pdf_report.py:1387` | Criterio sin dato = `✗` (no puntúa); solo se marca "no concluyente" si faltan ≥4 (:623-627). |
| **Altman Z** | `altman_z_score` `financial_ratios.py:128-269` (Original / Z'' / Z' según el sector; excluye financieras). | `pdf_report.py:1371-1378` | WC y RE ausentes se toman como **0** (:204-205), con aviso. |
| **Salud financiera (bancos)** | `financial_health_score` `:272-472`, llamada dentro de `calculate_score_v2` :4363 | `pdf_report.py:1361-1367` | Ya reescala cuando faltan datos (:440-452): es el patrón correcto para el cambio 2. |
| **DCF** | `dcf_multi_stage_dynamic` `:2044` → `dcf_multi_stage` `:1876` (3 etapas de 5+5 años + Gordon). Upside/MoS en `main.py:786-798`. | Sección 01 "Valor intrínseco" `pdf_report.py:1069-1105` | Reporta `value_composition.terminal_pct`; solo avisa si TV > 75% (:2036). |
| **Grid de sensibilidad** | `dcf_sensitivity_analysis` `:4511-4682`: 5×5, crecimiento base ±5% (paso 2.5%) × WACC base ±2% (paso 1%). | Tabla coloreada `pdf_report.py:1107-1155` | Centrado por construcción en el caso base. Calcula `interpretation` y `statistics` (mín/máx), pero el PDF **no los muestra**. |
| **Graham** | `graham_number` `:1865-1873` (√(22.5·EPS·BVPS)); margen en `main.py:746` | `pdf_report.py:1077-1079` | Se calcula también para bancos. |
| **ROIC / WACC** | ROIC en `calculate_all_ratios` `:3178-3192, 3215` (impuesto 25%, capital invertido = deuda + equity − caja); fallback en `main.py:327-332` (impuesto 21%). WACC `calculate_wacc` `:642-710`, llamado **solo con beta** (`main.py:489, 762`). Spread `main.py:494`. | `read_spread` `pdf_report.py:149`; secciones 02 y resumen | Ver §6.5: el "WACC" es en realidad el coste del equity. |
| **Alertas** | `build_signals` `alert_interpretations.py:500-533` (20 intérpretes, máx. 6 por grupo). | Sección 06 `pdf_report.py:1487-1512` | El motor legacy `aggregate_alerts` está muerto. |
| **Posición en rango 52s** | **Se calcula en el PDF**, no en el motor: `pdf_report.py:617-621` con `price_52w_high/low` (de `fiftyTwoWeekHigh/Low` de Yahoo, `data_fetcher.py:527-528`). | `read_pos52` :248, `zone_bar_52` :338, portada :824-834 | Curva en U: <10 / <25 / ≤70 / <88 / ≥88. El frontend lo calcula aparte. |

### 1.4 Dónde se genera el PDF y cómo se renderiza

- `pdf_report.build_report(buf, analysis, sector_bench, logo_path)` — `pdf_report.py:596`. Usa reportlab **platypus** (`BaseDocTemplate`, `Frame`, `Table`, `Paragraph`), tamaño carta, con decoración de página en `_page_decor` :430. El radar está dibujado a mano con `reportlab.graphics` (:534).
- Estructura (`story`): portada → `PageBreak` → Resumen ejecutivo (:869) → 01 Valoración (:1033) → 02 Rentabilidad (:1159) → 03 Solidez (:1203) → 04 Crecimiento y retorno (:1244) → 05 Evaluación institucional (:1328) → 06 Alertas (:1487).
- Narrativa: los lectores `read_*` (:89-285) devuelven `(etiqueta, tono, frase)` con **umbrales propios**, distintos de los del motor.
- Se transmite como `StreamingResponse` con un nombre de archivo entre comillas (`main.py:916-922`). El logo se busca en `frontend/public/logo.png` o `frontend/out/logo.png`.
- **Verificado localmente:** `build_report` generó el PDF de NFLX (26 KB, ~7 páginas) en el scratchpad.
- **Bug latente:** el recuadro del escenario base exige `sensitivity["base_growth_idx"/"base_discount_idx"]` (`pdf_report.py:1118, 1148`), pero `dcf_sensitivity_analysis` **nunca devuelve esas claves** (verificado en ejecución: claves = `base_case, discount_rates, growth_rates, interpretation, is_valid, matrix, statistics, warnings`). El recuadro no se dibuja nunca, aunque el texto diga "El recuadro verde marca el escenario base" (:1154).

---

## 2. Inventario de valores hardcodeados

Agrupado por bloque. Las funciones `score_*` y `read_*` contienen bandas en línea (más de 300 literales en total); se listan por función y rango de líneas con sus valores, que es la granularidad útil para extraerlas a YAML. **Importante:** casi ningún umbral vive en `config.py`, y varios están **duplicados con valores distintos** en el motor, el PDF, las alertas y el frontend.

### 2.1 Medianas sectoriales ("brecha vs sector") — Fallo 3

| Dónde | Contenido |
|---|---|
| `backend/main.py:89-94` (defaults) | pe 22 · forward_pe 18 · pb 3.5 · ev_ebitda 14 · pfcf 25 · peg 1.5 · roe 0.15 · roa 0.06 · roic 0.10 · net_margin 0.10 · operating_margin 0.15 · gross_margin 0.40 · current_ratio 1.5 · de 0.8 · interest_coverage 8 · fcf_yield 0.04 · revenue_growth 0.08 · earnings_growth 0.10 |
| `backend/main.py:95-107` (11 sectores) | p. ej. **communication: pe 18, roe 0.12, net_margin 0.12** (← los "P/E 18x, ROE 12%, margen 12%" literales del spec; NFLX cae aquí) · technology pe 30/roe .25 · financials pe 13/pb 1.5/roe .12/de 2.5 · real_estate pe 35 · energy pe 10 · materials pe 14… |
| `frontend/src/lib/sectorBench.ts:13-29` | **Copia** de lo anterior ("mirrors frontend", `main.py:88`). Dos fuentes que mantener sincronizadas a mano. |
| Uso | `sector_pe`/`sector_ev_ebitda` alimentan el score de valoración (`main.py:466-467`); todo el diccionario alimenta las tablas "brecha" del PDF (`main.py:911`). |
| Defaults en línea si falta la mediana | P/E 20 (`financial_ratios.py:843, 1080, 3863`), EV/EBITDA 12 (`:3988`), P/E 25 (`:1669`, muerto). |

### 2.2 Umbrales del score por sector

- `ThresholdConfig` (defaults) `financial_ratios.py:1153-1191`: pe_overvalued_mult 1.3 · p_fcf_high 25 / low 10 · fcf_yield 3%/8% · peg 2.0/1.0 · net_debt_ebitda 4/2 · debt_equity_high 1.0 · interest_coverage_low 3 · current 1.0/2.0 · quick 0.7 · roe 20%/8% · roa 12%/3% · op_margin_low 5% · net_margin_low 3% · beta 1.5/0.8.
- `SECTOR_THRESHOLDS` `financial_ratios.py:1195-1302`: overrides para 11 sectores + default (p. ej. financials roe .12/.06, roa 1.2%/0.8%, de 10; real_estate de 2.0, roe .08/.03; technology de 0.80, op_margin_low .15).
- `FINANCIAL_SECTORS` `:57-68` y palabras clave `:125`; `FINANCIAL_BENCHMARKS` (bancos) `:73-103`: ROA 0.5/0.3/0.2% · ROE 12/8/6% · P/B 0.8/1.2/2.0 · D/E 5/10/15x · equity/assets 6/4% · yield 2.5% · payout 60%.

### 2.3 Bandas dentro de las funciones de score (base 10, máx. 20)

| Función (líneas) | Bandas y puntos |
|---|---|
| `score_solidez_financiera` :3276-3413 | Altman SAFE +6 / GREY −2 / DISTRESS −6 · current ≥2.0 +4, ≥1.5 +2, ≥1.0 0, ≥0.8 −2, else −4 · D/E vs umbral sectorial ×0.5 +5, ×1 +2, ×1.3 0, ×1.6 −2, mitigación por cobertura ≥10 → −2, else −5 · cobertura ≥10 +3, ≥5 +1, ≥3 0, ≥1.5 −2, else −3 |
| `score_solidez_financiera_financial` :3416-3571 | 4 + FHS×1.4 · **tope 18/20** sin datos regulatorios (:3452) · D/E bancario <5 +3, <10 +2, <15 0, else −2 · P/B <0.8 +2, ≤1.2 +1, ≤2.0 0, else −1 |
| `score_rentabilidad` :3574-3754 | ROE vs roe_high sectorial ×1.25 +6 / ×1 +4 / ≥roe_low +2 / ≥5% −2 / ≥0 −4 / <0 −6 · ROA análogo ±4 · margen operativo ≥30 +5, ≥20 +3, ≥10 +1, ≥5 −1, ≥0 −3, <0 −5 (**no sectorial**) · margen neto ≥20 +3, ≥10 +2, ≥5 0, ≥0 −2, <0 −3 · spread ROIC−WACC ≥10% +3, ≥3% +2, ≥0 +1, ≥−3% −1, else −3 |
| `score_valoracion` :3757-4110 | REIT P/FFO ≤12 +4, ≤16 +2, ≤20 0, ≤25 −2, >25 −4 · P/E vs sector ×0.7/0.9/1.1/1.3 (+5/+3/0/−2/−4); growth ×0.7/1.0/1.5/2.0 (+5/+3/0/−2/−3) · compresión del forward P/E ≥25% +3, ≥12% +2, ≥5% +1 · P/FCF 12/18/25/35 (growth 15/25/40/60) · EV/EBITDA vs sector ×0.7/1/1.2/1.5 (growth ×0.7/1.2/1.8/2.5) · PEG 0.8/1.2/1.8/2.5 · bono GARP +3 (calidad ≥70) / growth +2 (≥75) · "rescate" de penalizaciones: tope −4 (growth de calidad) / −6 (:4076-4095) |
| `score_calidad_ganancias` :4113-4214 | F-Score ≥8 +7, ≥6 +4, ≥4 0, ≥2 −4, else −7 · OCF >0 +3 / ≤0 −4 · FCF >0 +3 / ≤0 −4 · FCF/NI ≥1.0 +3, ≥0.7 +1, ≥0.3 0, else −2. **Sin rama financiera.** |
| `score_crecimiento` :4217-4320 | ingresos 3Y ≥20 +5, ≥10 +3, ≥3 +1, ≥0 −1, <0 −4 · EPS 3Y ≥25/12/5/0 · FCF 3Y ≥15/5/−5 · bono growth company +2 |
| `calculate_score_v2` :4323-4504 | is_growth = revenue_cagr_3y > 15% (:4352) · is_reit = sector_key == "real_estate" (:4438) · niveles 80/65/50/35 (:4462-4476) |
| `calculate_growth_quality_score` :927-1053 | base 50; ingresos 25/15/8/0; EPS vs ingresos ×1.2/×1/×0.5; FCF 15/5/0; ROE|ROIC 25/15/8; margen operativo 25/15/5; niveles 80/65/50/35 |
| `classify_company_type` :778-924 | crecimiento 25/15/5%; EPS 20/10%; P/E/sector 0.6/0.85/1.15/1.5; ROE 25/15/8%; yield 4/2%; FCF yield 8/5%; confianza <0.25 → "blend" |
| `adjust_valuation_for_growth` :1056-1146 | calidad 85/75/65/50 → +5/+4/+3/+2; GARP/growth +2; ROE ≥30 +2, ≥20 +1; topes +2/+1/0 |

### 2.4 Modelos institucionales y valoración

| Constante | Dónde |
|---|---|
| Altman: 2.99/1.81 (`config.py:17-18`) · Z'' 2.60/1.10 (`financial_ratios.py:228`) · Z' 2.90/1.23 (`:220`) · coeficientes (`:218, 226, 235`) · sectores "no manufactura" (`:186-191`) | |
| Piotroski: bandas 8/6/4/2 (`:628-637`), "no concluyente" si ≥4 sin dato (`:626`) · **segundas bandas 7/5/4** en `main.py:629` · `config.PIOTROSKI_*` 7/4/3 (**sin uso**) | |
| CAPM: Rf **4.5%**, MRP **5.5%**, g terminal **2.5%** (`config.py:49-51`) · beta por defecto 1.0 (`financial_ratios.py:678`, `main.py:488, 761`) · impuesto 25% (`:647`) · spreads de deuda +1/+2/+3/+5% por D/E 0.3/0.6/1.0 (`:693-700`) | |
| WACC: fallback 10% y clamp **[6%, 20%]** (`:2099-2102`; también `:4549`) · `config.DCF_WACC_MIN/MAX` (sin uso) | |
| DCF: 5+5 años (`config.py:63-64`) · tope de crecimiento 50% (`:1940`, `main.py:778`) · topes por fuente fcf .35 / eps .40 / **rev .30** (`:2117-2121`) · default 8% (`:2131`) y **10% en main.py:763** · decay: exponencial >25%, lineal >15%, si no "step" (`:2139-2144`), factor 0.85 (`:1955`) · aviso de TV >75% (`:2036`) | |
| Grid: ±5% en pasos de 2.5% × ±2% en pasos de 1% (`:4517-4518`) · interpretación 80/60/40/20% de escenarios (`:4671-4680`) | |
| Graham **22.5** (`:1873`) · ROIC fallback impuesto **21%** (`main.py:329`) vs **25%** en ratios (`:3179`) | |
| Guarda de buyback ±25% (`main.py:507`) | |

### 2.5 Alertas y lecturas del PDF (umbrales paralelos a los del score)

- `alert_interpretations.py` (51 comparaciones): P/E desv. >30% o >35x (:92), descuento −20% (:111) · EV/EBITDA >25x, ×1.3 / ×0.7 sector (:124-132) · PEG <1 / >2, descartado >5 (:161-167) · upside DCF ±15/±30% (:179-191) · ROE ≥40% (:213) · spread 10/3/0% (:240-247) · margen bruto >60% (:273) · cobertura <1.5 / >12 (:309, :318) · current >3 (:335) · FCF negativo 2 años (:363) · calidad <0.5 / >1.0 (:383-388) · crecimiento 0/15% (:400-419) · F ≥8 / ≤2 (:432-436) · drawdown −30% (:480) · beta según ThresholdConfig · pesos 28-70 por señal · tope de 6 por grupo (:523).
- `pdf_report.py` `read_*` :89-285: vs sector ±10/±35% · ROE 5/12/20/40% (**universal**) · spread 10/3/0/−3% · current 1/1.5/3 · **D/E 0.5/1/2 "para un negocio no financiero" (universal, también se aplica a bancos)** · cobertura 2/5/10 · DN/EBITDA 0/1/2.5/4 · payout 0/40/60/80/100% · crecimiento 0/3/10/20% · upside ±15/±30 · Graham 0/20% · beta 0.8/1.2/1.6 · 52s 10/25/70/88 · score 80/60/40/20 · buyback ±0.5%/3% · FCF yield 0/3/5/8% · colores del grid ±10/±30% (:1141-1146).
- `frontend/src/lib/metricScale.ts` (116 líneas) y los tabs: bandas propias de color y tooltips ([DESCONOCIDO] si coinciden 1:1 con el backend; no se auditaron línea a línea).

### 2.6 Datos / infraestructura

`data_fetcher.py:25-27` (reintentos 4, base 3 s, máx. 45 s), `:73-77` (timeouts 15/30 s, 4 workers), cachés 30/60 min (`:394, :541`) · `yf_adapter.py:22-24` (TTL 300 s / 60 s degradado), `:35` (perfiles de suplantación), `:38` (último bueno 24 h), `:44-52` (campos de completitud) · `finnhub_fallback.py:41, 46, 51` (timeout 8 s, TTL 300 s, campos que disparan la consulta), guarda de crecimiento 60% / 3×CAGR (`:134`), corrección de EPS si difiere >2% (`:186`) · `config.py:147-156` (caché y rate limit: **sin uso**).

---

## 3. Fuentes de datos

### 3.1 API 1 — Yahoo Finance (no oficial)

| Aspecto | Detalle |
|---|---|
| Cliente | `curl_cffi` con suplantación de navegador (`yf_adapter.py:160-186`), sesión + crumb (`/v1/test/getcrumb`). `yfinance` 1.x como enriquecimiento y fallback. |
| Endpoints | `GET query2.finance.yahoo.com/v10/finance/quoteSummary/{s}?modules=…` (9 módulos, `:342-351`) · `finance.yahoo.com` (cookie) · `/v1/test/getcrumb` · `/v1/finance/search` (autocompletado, `main.py:146`) · vía yfinance: estados anuales (`yf_adapter.py:742-744`) y `fast_info` en el fallback (`:886`). |
| **No pide** | `calendarEvents` (fecha de resultados), `chart` / `history` (precio y volumen diario), estados trimestrales/TTM ni `get_shares_full`. |
| Claves | No requiere. |
| Fragilidad conocida | Desde IPs de datacenter (Render), Yahoo devuelve snapshots degradados (`finnhub_fallback.py:4-7`). Se mitiga con reintentos, último bueno conocido y Finnhub. |

### 3.2 API 2 — Finnhub

| Aspecto | Detalle |
|---|---|
| Cliente | `urllib` de la stdlib, sin SDK (`finnhub_fallback.py:34, 74-89`). |
| Endpoint llamado | **Solo uno:** `GET https://finnhub.io/api/v1/stock/metric?symbol=…&metric=all` (`:98`). Usa `metric` (beta, forwardPE, peTTM, epsTTM, dividendos, payout, crecimiento, current/quick ratio, forwardPEG, coberturas, rotaciones) y `series.annual` (roa, netMargin, currentRatio, grossMargin, longtermDebtTotalAsset) para el año previo de Piotroski. |
| Clave | Variable de entorno `FINNHUB_API_KEY` (`:54-55`), puesta en Render. **No existe en el entorno local** → localmente Finnhub está inerte. Va como query param `token=`. |
| Cuándo se invoca | Solo si Yahoo vino degradado o falta beta/forwardPE/revenueGrowth/ROA previo (`yf_adapter.py:273`, `finnhub_fallback.py:62-71`). Nunca sobrescribe datos de Yahoo, salvo `trailingEps` si difiere >2%. |
| Plan | Parece **free tier**: el código lo dice (`:9`, "rate limit del free tier (60/min)" en `:44`). **[DESCONOCIDO]** el plan real de la cuenta. |
| Noticias / sentimiento | **El código no llama a ningún endpoint de noticias.** Disponibilidad en free tier: **[DESCONOCIDO — no verificado en vivo, falta la clave local]**. La página oficial de precios no lo detalla por endpoint; fuentes de terceros indican `company-news` y `calendar/earnings` **gratis** y `news-sentiment` **premium**. Para verificar (sustituye la clave): `curl "https://finnhub.io/api/v1/company-news?symbol=NFLX&from=2026-10-01&to=2026-10-09&token=$FINNHUB_API_KEY"` y lo mismo con `/news-sentiment?symbol=NFLX`, `/calendar/earnings?symbol=NFLX` y `/stock/candle?symbol=NFLX&resolution=D&from=…&to=…`. |
| FMP | Vestigial: solo se lee `FMP_API_KEY` (`data_fetcher.py:1332`); no hay llamadas. Tampoco está definida localmente. |

### 3.3 Caché, reintentos y límites de tasa

| Mecanismo | Dónde |
|---|---|
| Caché en memoria por proceso (se pierde al reiniciar; Render reinicia en cada deploy) | `yf_adapter._cache` 300 s / 60 s degradado (`:22-24, :219-227`) · `SimpleCache` LRU de 500 entradas, perfil 30 min / financieros 60 min (`data_fetcher.py:161-255, :394, :541`) · Finnhub 300 s (`:45-47`) · último bueno conocido 24 h (`yf_adapter.py:38, :284`). Sin caché persistente ni compartida. |
| Reintentos | Yahoo: refresco de crumb ante no-200 (`:359-370`), 2 reintentos con sesión nueva ante degradación con espera 0.8·n s (`:246-261`) · `data_fetcher`: backoff exponencial ante rate limit (4 intentos, 3→45 s; `:372-427, :450-577`). En la práctica `get_ticker_info` casi nunca lanza excepción (devuelve el fallback), así que ese backoff rara vez se activa. · Finnhub: **sin reintento** (un fallo devuelve None, `:87-89`). |
| Rate limit | No hay un limitador explícito: solo el lock por símbolo (`yf_adapter.py:153`) y la caché. `config.YAHOO_FINANCE_DELAY` / `MAX_PARALLEL_REQUESTS` existen pero no se usan. El presupuesto de Finnhub (60/min) depende solo de la caché de 300 s. |

---

## 4. Disponibilidad real de campos (crítico)

**Método:** llamadas de solo lectura el 11-oct-2026 desde local, con yfinance 1.2.0 (la misma familia de endpoints de Yahoo que usa la app) y ejecutando el motor real (`_compute_analysis`) en proceso. **Finnhub no se pudo consultar** (sin clave local) → sus columnas son [DESCONOCIDO]. Desde Render, Yahoo puede venir degradado: lo que aquí aparece "con dato" puede faltar en prod **[DESCONOCIDO cuánto]**.

Leyenda: ✅ con dato · ⚠️ parcial / con trampa · ❌ ausente · — no aplica.

| Campo | NFLX | JPM | O | FCX | SNOW |
|---|---|---|---|---|---|
| **Partidas no recurrentes** (income stmt) | ⚠️ `Total Unusual Items` **ausente**; `Tax Effect Of Unusual Items` = 0; `Normalized Income` = reportado. La comisión de ~$2.8B aparece como **`Net Non Operating Interest Income Expense` = +$2.59B en el 1T-26** (vs ≈ −$0.14B habitual) y antes de impuestos 6.55B vs operativo 3.96B. **Yahoo no la marca como inusual.** | ✅ desagregado: Total Unusual Items (1.03B FY25; 4.81B TTM), Special Income Charges, Restructuring & M&A, Gain On Sale Of Security, Other Special Charges | ✅ desagregado: Total Unusual Items −339M, Write Off 471M, Impairment, Restructuring, Gain On Sale Of Security 156M | ✅ pequeño (16M FY25; 733M TTM), Gain On Sale Of PPE | ✅ (−60M FY), Write Off, Gain On Sale Of Security |
| ¿Disponible anual / trimestral / TTM? | sí / sí / sí (en los 5) | | | | |
| **Acciones en circulación históricas** | ⚠️ Balance anual 4 años (`Ordinary Shares Number` 4.45→4.22B, **ajustado por el split**). `Share Issued` (incluye autocartera) 4.47→4.57B. `get_shares_full` 5 años **NO ajustado** por el split 10:1 del 17-nov-2025 (443M → 4.16B). | ✅ Ordinary 2.93→2.70B; Share Issued plano 4.10B | ✅ 660→934M (emisión estructural de REIT) | ✅ Ordinary ≈1.43B; Share Issued 1.62B | ✅ 323→344M (4 años) |
| **Sector / industria** (Yahoo, no GICS) | Communication Services / Entertainment | Financial Services / **Banks - Diversified** | Real Estate / **REIT - Retail** | Basic Materials / **Copper** | Technology / Software - Application |
| ¿Se puede identificar banco / REIT? | — | ✅ por `industry` ("Banks - …") | ✅ por `industry` ("REIT - …") | — | — |
| **Historial de ganancias ≥5 años** | ⚠️ Anual: **4 ejercicios** con dato (la 5.ª columna viene NaN en NFLX, O y FCX; SNOW trae 4 columnas). Trimestral: `get_earnings_dates` da 49 trimestres de EPS desde 2014 (EPS "reportado" del calendario, probablemente ajustado/street, **no GAAP** [DESCONOCIDO definición exacta]). Lo que usa hoy la app (`_yearly_financials`): 4 puntos. | ⚠️ ídem; `yearly_financials` = **0 puntos** | ⚠️ 4 años | ⚠️ 4 años (insuficiente para un ciclo del cobre) | ⚠️ 4 años (IPO 2020; 23 trimestres) |
| **FFO / AFFO** | — | — | ⚠️ **No hay FFO ni AFFO en Yahoo** (ninguna fila contiene "FFO"). FFO **aproximable**: NI + D&A (2.52B) + deterioros (`Asset Impairment Charge`) − ganancias por venta. **AFFO no calculable** (sin ajuste de rentas lineales ni capex de mantenimiento; solo `Purchase Of Investment Properties`). La app calcula FFO = NI + (EBITDA − EBIT) y P/FFO 13.6x. Finnhub: [DESCONOCIDO]. | — | — |
| **Métricas de balance bancario** | — | ⚠️ Disponibles: Net Interest Income (95.4B), Interest Income/Expense, Tangible Book Value, gastos no financieros (SG&A, Salaries, Occupancy, Other Non Interest Expense) → **P/B, P/TBV, ROE y ratio de eficiencia aproximado: sí**. **Ausentes:** préstamos, depósitos, reserva y **provisión por pérdidas crediticias**, activos que generan intereses (→ NIM solo como proxy NII/activos), **CET1/CAR**. Operating Income y EBITDA: ausentes. OCF: −147.8B (FY25), −42.0B (FY24). | — | — | — |
| **Próximo reporte de resultados** | ✅ 20-oct-2026 (confirmado; a 11 días del 9-oct, como dice el spec) | ✅ 13-oct-2026 | ✅ 2-nov-2026 | ✅ 27-oct-2026 | ⚠️ 2-dic-2026 **estimado**; `info.earningsTimestamp` devuelve la fecha **pasada** (2-sep): hay que usar `earningsTimestampStart`/`calendar` + `isEarningsDateEstimate` |
| **Precio y volumen diario ≥12 m** | ✅ 251 sesiones/año (OHLCV + Adj Close), 501 en 2 años, en los 5 tickers. **La app no lo descarga hoy.** Desde Render: [DESCONOCIDO] si el endpoint `chart` también viene bloqueado. | | | | |
| **ROCE** (nueva variable del spec) | ✅ calculable: EBIT / (activos − pasivo corriente) FY25 **30.3%** (24.9 / 17.4 / 14.7 los años previos) vs ROIC app 34.5% | ❌ sin EBIT ni pasivo corriente (coherente con excluir FINANCIAL) | calculable (3.3%), pero el spec lo excluye | ✅ **12.9%** (14.6 / 14.0 / 16.3) vs **ROIC app 24.8%** → divergencia de ~12 pp | ✅ −27.7% |

### 4.1 Qué produce HOY el motor con estos datos (ejecución local)

| | NFLX | JPM | O | FCX | SNOW |
|---|---|---|---|---|---|
| Score (nivel motor) | **97** Excelente | 74 Favorable | 82 Excelente | 77 Favorable | 43 Precaución (PDF: "Neutral") |
| Sol/Rent/Val/Cal/Crec | 20/20/20/17/20 | 18/20/14/**2**/20 | 20/17/12/13/20 | 20/20/10/13/14 | 9/0/4/13/17 |
| Piotroski | 6/9 | **2/9** | 5/9 | 5/9 | 4/9 |
| DCF valor razonable / upside | **$129.5 / +84%** | — (financiera) | $29.9 / −45% | $11.6 / −84% | **$142.6 / −61%** |
| Grid mín–máx (¿contiene el precio?) | 88–199 (**no**: todo por encima) | — | 4.5–88 (sí) | 9–20 (**no**: todo por debajo) | 210–431 (sí; base **$318.9 ≠ $142.6** del DCF) |
| % valor terminal | 44% | — | 63% | 41% | 50% |
| WACC usado | 13.37% | (10.1%) | 8.33% | 12.14% | 11.93% |

Notas: localmente el score de NFLX es 97, frente al 99 del spec, y la valoración 20/20 frente a 19/20: los datos difieren de prod. Ver §6 para lo que esto implica.

---

## 5. Calidad y testing

- **Tests: no existen** en `finanzer_next` (ni `test_*.py`, `conftest.py`, `pytest.ini`, jest ni vitest; `package.json` solo tiene `dev/build/start/lint`). pytest 8.4.2 está instalado localmente, sin nada que ejecutar. En `finanzer_complete_v3` solo hay `benchmark_test.py` (un script de benchmark, no una suite). → **Cobertura 0%.** Riesgo alto para un rediseño: no hay red de regresión. Hace falta una línea base (golden files por ticker y fecha) antes de tocar el motor.
- **Ejecutar la app localmente** (no se lanzó ningún servidor en esta etapa):
  ```bash
  cd finanzer_next/backend && python3 -m uvicorn main:app --port 8000
  ```
  El backend sirve el frontend precompilado de `frontend/out/` en `/`. Para desarrollar el frontend: `cd frontend && npm install && npm run dev` (CORS permite `localhost:3000`, `main.py:36`). Para que Finnhub participe hace falta exportar `FINNHUB_API_KEY`. Sin `--reload`, los cambios del backend requieren reiniciar. Entorno local: Python 3.9.6 (sistema), fastapi 0.128.8 / uvicorn 0.39 (≠ versiones fijadas 0.115 / 0.30). Versión de Python en Render: [DESCONOCIDO].
- **Generar un PDF para un ticker:**
  ```bash
  curl -o NFLX.pdf http://localhost:8000/api/pdf/NFLX
  ```
  O sin servidor, en proceso: `main._compute_analysis("NFLX")` → `pdf_report.build_report(buf, analysis, main._get_sector_benchmarks(mapped))`. **Verificado: funciona** (26 KB, ~7 páginas).
- **Deploy:** Render auto-despliega `main`; `build.sh` solo instala el backend y valida `frontend/out/`.
- **Calidad observada:** manejo defensivo abundante (`try/except` amplios que **tragan errores** y degradan en silencio a None, p. ej. `main.py:670, 727, 813`); un fallo puede producir un informe incompleto sin aviso. Lógica de dominio repartida entre 4 capas con umbrales propios (motor, alertas, PDF, frontend).

---

## 6. Brechas frente a la especificación

### 6.0 Supuestos del spec que los datos o el código reales contradicen

| # | Supuesto del spec | Realidad verificada |
|---|---|---|
| C1 | **Fallo 4 / cambio 3:** `normalize_earnings` con `income_stmt.get('unusual_items')` habría detectado la comisión de NFLX. | **No.** Yahoo **no** clasifica la comisión de NFLX como inusual: está en *Net Non Operating Interest Income Expense* (+2.59B en el 1T-26) y `Normalized Income` = reportado. Con el diseño del spec, `one_off_pct` de NFLX = **0%**. Hace falta además un detector de **picos de resultado no operativo** (antes de impuestos − operativo, contra su propio historial). |
| C2 | "~$2.8B sobre ~$11B ≈ 25%". | Mezcla el numerador TTM con el beneficio del FY2025. El beneficio TTM es **13.65B**, así que el peso es ≈ **20% antes de impuestos / ~16% después**. Sigue sobre el 15%, pero cerca del umbral: la decisión de usar bruto o neto de impuestos cambia el veredicto. |
| C3 | **Fallo 2:** NFLX quedó en 6/9 por "sin datos históricos de acciones". | Depende del entorno. **Localmente** el criterio 7 falla con *"Emisión de nuevas acciones"*: la app compara **`Share Issued`** (incluye autocartera: 4.53→4.57B) en vez de **`Ordinary Shares Number`** (en circulación: 4.28→4.22B, **recompras**) (`yf_adapter.py:783, 863`). Con el campo correcto, NFLX = **7/9**. En prod el informe dijo "sin datos" (probablemente el enriquecimiento con yfinance bloqueado) [DESCONOCIDO, no reproducible aquí]. **Arreglar solo la ausencia de dato no basta: también hay un bug de campo.** El mismo error infla `buyback_yield` (NFLX 8% mostrado vs ~1.4% real; FCX 11.6% vs ~0.7%; JPM 35% → descartado por la guarda). |
| C4 | **Fallo 5:** "el grid está mal centrado". | El grid **sí está centrado** en el caso base por construcción (WACC ±2%, crecimiento ±5%). El problema está en los **inputs**: (a) el "WACC" es **solo el coste del equity** — `calculate_wacc` se llama solo con beta y devuelve Rf + β·MRP = 4.5% + 1.61×5.5% = **13.36%** sin ponderar la deuda (`financial_ratios.py:684-685`; `main.py:489, 762`); (b) el **FCF de entrada no es fiable** (C5); (c) el crecimiento es el YoY de un solo trimestre. |
| C5 | El diagnóstico del DCF de NFLX (−50%, fair ~$35) es una propiedad del modelo. | **El signo del DCF de NFLX depende del snapshot de datos.** Localmente la app usa `financialData.freeCashflow` = **$25.4B** (FCF *apalancado* de Yahoo, mayor que el OCF de $12.0B; imposible si FCF = OCF − capex) → **+84%**. Con el FCF del estado de flujos ($11.15B) y crecimiento del 16%, el mismo motor da **$40.8 (−42%)**, TV **41.6%** y grid 27.6–63.0, casi lo que reporta el spec (42%, máx. $54). Conclusión: en prod probablemente entró otro FCF/crecimiento [DESCONOCIDO exacto]. **El mismo ticker da veredictos opuestos según la fuente.** Ese FCF inflado también alimenta P/FCF (+4 en valoración), FCF yield ("atractivo 8.7%") y la calidad FCF/NI. |
| C6 | Datos de mercado/ingesta correctos ("el pipeline funciona"). | Precio, rango 52s y beta sí (NFLX 70.30 / 65.08–124.86 / 1.613 → posición 8.7% ✓). Pero hay campos de Yahoo **anómalos que pasan sin control**: FCF > OCF (NFLX), crecimiento de ingresos de JPM **30.4%** (artefacto de definición de "revenue" bancario, que dispara is_growth, GARP +3 y Crecimiento 20/20), crecimiento de NFLX 24.0% vs 13.4% YoY trimestral calculado de los estados. La guarda anti-artefacto existe solo en la ruta de Finnhub (`finnhub_fallback.py:120-138`), no en la de Yahoo. Refuerza el "séptimo cambio" del Apéndice. |
| C7 | La 2.ª API "muy probablemente ya incluye noticias" y `news-sentiment` es gratis. | La 2.ª API es **Finnhub**, pero la app **no usa ningún endpoint de noticias**, y la clave no está disponible localmente para comprobarlo. Fuentes de terceros sitúan `news-sentiment` en **premium**: con coste $0 probablemente solo `company-news` (titulares, sin sentimiento). [DESCONOCIDO hasta probarlo con la clave.] |
| C8 | Capa conductual: "precio, volumen y rango ya disponibles". | En Yahoo están disponibles (251 sesiones/año), pero **la app hoy solo tiene máx./mín. 52s y beta**: no descarga serie diaria ni fecha de resultados. Es una ingesta nueva (llamada extra por ticker, latencia y riesgo de bloqueo en Render [DESCONOCIDO]). |
| C9 | Clasificador: `gics_sector`, `is_bank`, `is_reit`, `rev_growth_3y`, `earnings_volatility`. | Yahoo da **sector/industria propios (no GICS)**: "Financial Services", no "Financials". Banco y REIT se infieren de `industry` ("Banks - …", "REIT - …"). Hoy `is_reit` = **todo** `real_estate` (incluye promotoras y servicios inmobiliarios, `financial_ratios.py:4438`). `rev_growth_3y` **no existe**: se usa el YoY como proxy (`main.py:476-484`), aunque el CAGR real es calculable con 4 años (SNOW ≈31%). `earnings_volatility` con ≥5 años **no sale del anual de Yahoo** (solo 4 ejercicios): hace falta EPS trimestral (`get_earnings_dates`, de definición dudosa) o una fuente más larga [Finnhub `series.annual` / `financials-reported`: DESCONOCIDO]. |
| C10 | FINANCIAL usa NIM, CAR (Basel), coste del riesgo. | **CAR/CET1, provisiones, préstamos y depósitos no existen en Yahoo.** NIM solo como proxy. Disponibles: P/B, P/TBV, ROE, NII, eficiencia aproximada. El propio código lo reconoce (tope 18/20, `financial_ratios.py:3434-3452`). |
| C11 | REIT usa P/AFFO. | **AFFO no está disponible ni es calculable** con Yahoo; FFO solo aproximado. Realistamente: **P/FFO** (ya existe en el score) y "AFFO: sin dato". |
| C12 | "Medianas sobre comparables reales, refrescadas periódicamente" con coste $0. | Ni la app ni las APIs proveen hoy universos de comparables. Hace falta definir un universo por arquetipo y un job que descargue N tickers (con N×llamadas a Yahoo y riesgo de bloqueo). No hay almacenamiento persistente (solo caché en memoria) ni scheduler. |
| C13 | ROCE: "en CYCLICAL se reporta el ROCE promedio a través del ciclo". | Con Yahoo solo hay **4 ejercicios**, menos que un ciclo de commodities (FCX). Además, el ROIC actual ya es dudoso en algunos casos (FCX: ROIC app 24.8% vs ROCE 12.9%; el ROIC usa deuda + equity − caja e impuesto del 25%, mientras que el fallback de `main.py` usa 21%). |

### 6.1 Cambio 1 — Clasificar antes de puntuar (+ ROCE)

- **Archivos:** nuevo `engine/classify.py` (o `lib/classify.py`); `main.py:451-541` (hoy el sector se resuelve ahí y `company_type` sale del score); `financial_ratios.py:4323-4504` (`calculate_score_v2` ramifica solo financiera vs no financiera y REIT por sector); `score_calidad_ganancias` (sin rama financiera: JPM recibe OCF −4 y Piotroski −4 → **Calidad 2/20** y el riesgo "Debilidad financiera — Piotroski 2/9"); `score_valoracion` (P/E sigue siendo métrica de un banco); `alert_interpretations.py` (`_pe` y `_fcf`/`_fcf_yield` sin guarda de financiera/REIT; a O le salta "Prima sobre el sector — P/E 39.3x" y "Sobrevalorada según DCF −45%" aunque el score lo valora por P/FFO); `main.py:758-760` (el DCF se salta solo para financieras: hoy se aplica a REITs y a pre-beneficio); `pdf_report.py` (`is_financial` local :615; `read_de`/`read_roe` universales); `sector_profiles.py` (mapeo); frontend (pestañas que muestran FCF/P/E).
- **ROCE (nueva variable):** función nueva en `financial_ratios.py` (cerca de `roic` :1343); `FinancialStatements` ya trae `total_assets`, `current_liabilities` y `operating_income`, pero el ROCE "a través del ciclo" exige series multianuales (hoy solo hay 2 años de balance vía `_enrich_prior_year_data`). Exponer en `key_metrics` y en la sección 02 del PDF; añadir el umbral de divergencia a `thresholds.yaml`; ocultarlo para FINANCIAL/REIT.
- **Dependencias que faltan:** CAGR real de 3 años (re-habilitar históricos anuales: el código muerto de `data_fetcher.py:1546-1580` ya tenía un `_cagr` corregido); serie para la volatilidad de beneficios (≥5 años) e historial multianual de EBIT y capital empleado para el ROCE cíclico; lista `CYCLICAL_INDUSTRIES` basada en los nombres de industria de **Yahoo** (p. ej. "Copper", "Steel", "Oil & Gas E&P", "Semiconductors"…); regla banco/REIT por `industry`.
- **Riesgos:** sin tests, cambiar el ramaje mueve todos los scores (hace falta una línea base primero). Seguros, gestoras y fintechs dentro de "Financial Services" no son bancos (¿P/B para Visa?). El arquetipo GROWTH_PRE_PROFIT depende de un crecimiento hoy contaminado por artefactos (JPM 30%). Hay que mantener coherencia entre motor, alertas, PDF y frontend (cuatro lugares que hoy deciden "es financiera" por separado).

### 6.2 Cambio 2 — Arreglar datos faltantes

- **Archivos:** `financial_ratios.py:475-639` (Piotroski: devolver criterios evaluados / máximo evaluable; hoy un criterio sin dato = ✗ y "no concluyente" solo con ≥4); `main.py:629, 638-643, 681-682` (bandas 7/5/4 y el parseo `✓/✗` del texto, que no distingue "sin dato"); `financial_ratios.py:204-205` (Altman: WC/RE ausentes → 0); `:4113-4214` (Calidad); el PDF y el frontend para mostrar cobertura ("7/8 evaluados"). Patrón a reutilizar: `financial_health_score` `:435-452`.
- **Corregir también el campo de acciones** (C3): `yf_adapter.py:783, 863` → `Ordinary Shares Number` primero; `yf_adapter.py:512` (si falta el previo usa el actual → aprueba por defecto, el caso inverso); `main.py:499-508` (buyback con definiciones mezcladas). Considerar splits: el balance anual viene ajustado, `get_shares_full` no.
- **Dependencias:** ninguna externa. Hace falta un modelo de datos de "cobertura" (qué inputs había).
- **Riesgos:** reescalar Piotroski cambia la escala que consume `score_calidad_ganancias` (±7). En JPM, quitar los 2 "sin dato" deja 2/7, que sigue siendo bajo por criterios no aplicables a bancos (CFO, current ratio, margen bruto) → **el cambio 2 sin el cambio 1 no arregla a los bancos**.

### 6.3 Cambio 3 — Normalizar ganancias

- **Archivos:** nuevo `normalize.py`; `yf_adapter.py:336-705` / `_enrich_prior_year_data` (hoy **no** se extrae ninguna fila de partidas no recurrentes ni estados trimestrales/TTM); `data_fetcher.FinancialStatements` (`:272-320`, sin campos para ellas; `calculate_all_ratios` lee `gains_on_sale` (:3200), que **nunca se rellena**); `calculate_all_ratios` (P/E y EPS normalizados); `score_valoracion`, `read_pe` y `_pe` (avisar "P/E no fiable").
- **Dependencias:** estados TTM/trimestrales de yfinance (`ttm_income_stmt`, `quarterly_income_stmt`: verificados con dato) con las filas Total Unusual Items, Special Income Charges, Restructuring, Gain On Sale…, Write Off e Impairment, más un **detector de picos no operativos** para casos como NFLX (C1). Cada fuente aporta llamadas extra por ticker.
- **Riesgos:** las filas de Yahoo tienen signos inconsistentes (JPM: `Special Income Charges` = +, `Other Special Charges` = −, que se compensan); doble conteo entre "Total Unusual Items" y sus componentes; impuesto aplicable (`Tax Effect Of Unusual Items` existe y conviene usarlo). Umbral bruto vs neto (C2). REITs: "Gain On Sale" ya se resta en FFO; no aplicarlo dos veces.

### 6.4 Cambio 4 — Separar calidad de precio

- **Archivos:** `calculate_score_v2` (`:4323`; hoy suma 5 categorías, con Valoración como una más); `main.py:709-714` (contrato `score`); `pdf_report.py` (portada `score_band`, radar de 5 ejes, resumen); frontend (`ScoreCard.tsx`, hero; la app ya muestra la *etiqueta* "Calidad fundamental" vs "Precio", pero con un solo número); alertas.
- **Dependencias:** decidir la composición: **Calidad** = Solidez + Rentabilidad + Calidad de ganancias + Crecimiento (+ ROCE/ROIC); **Precio** = Valoración (múltiplos relativos) + DCF + Graham + rango 52s. El vector de factores (Momentum) necesita la serie diaria de precios (ver cambio 6).
- **Riesgos:** cambio de contrato de API que rompe el frontend y el PDF a la vez (el frontend es un export estático commiteado: hay que reconstruirlo y commitear `frontend/out/`). Los usuarios están acostumbrados al 0-100. Bandas de nivel inconsistentes (80/65/50/35 vs 80/60/40/20): unificar en este cambio.

### 6.5 Cambio 5 — DCF que admite su contradicción

- **Archivos:** `main.py:758-812`; `financial_ratios.py:642-710` (`calculate_wacc` necesita D/E, gasto por intereses y deuda; hoy solo recibe beta), `:2044-2195`, `:4511-4682`; `pdf_report.py:1069-1155`; `alert_interpretations._dcf`.
- **Antes de la regla de confianza, corregir los inputs (bugs verificados):**
  1. **FCF:** `data_fetcher.py:478` prefiere `financialData.freeCashflow` (apalancado; NFLX 25.4B > OCF 12.0B) frente a OCF − capex (:486-487). Validar FCF ≤ OCF.
  2. **WACC = coste del equity** (C4). Pasar la estructura de capital o etiquetarlo como Ke.
  3. **Crecimiento distinto entre el DCF y el grid:** el DCF lo topa en 30% (`:2120`), el grid en 50% (`main.py:806`) y `dcf.growth_rate` reporta el valor sin topar. SNOW: DCF **$142.6** vs caso base del grid **$318.9**, en el mismo informe.
  4. **Decay distinto:** el grid llama a `dcf_multi_stage` sin `decay_type` (lineal); el DCF principal usa step/lineal/exponencial según el crecimiento.
  5. **WACC sin clamp en la UI:** `dcf.wacc` (`main.py:792`) es el sin clamp; el DCF usa el valor clampado a [6, 20]%.
  6. **Recuadro del caso base nunca dibujado** (§1.4).
  7. `dcf_multi_stage_dynamic` calcula también su propio mini-análisis de sensibilidad (`:2168-2193`), que nadie usa → duplicado.
- **Lo que ya existe para el criterio de aceptación:** `statistics.min/max` + precio permiten saber si "el grid contiene el precio"; `interpretation` ya cuenta escenarios; `terminal_pct` ya se reporta. Falta mostrarlos y la métrica de divergencia DCF vs múltiplos vs Graham.
- **Riesgos:** con los inputs corregidos, muchos veredictos cambiarán de signo (NFLX: de +84% a −42% localmente). Sin línea base y tests, es difícil distinguir mejora de regresión. Que el DCF siga aplicándose a REIT/pre-beneficio/cíclicas depende del cambio 1 (FCX: crecimiento de 1.6% → grid entero por debajo del precio, el mismo patrón que el Fallo 5 pero por otra causa).

### 6.6 Cambio 6 — Capa conductual + noticias

- **Archivos:** nuevo `context.py`; `yf_adapter.py` (nueva llamada a `chart`/`history` 1-2 años y a `calendarEvents`, que podría añadirse como módulo a la llamada existente de quoteSummary, `:342-348`); `finnhub_fallback.py` o un cliente Finnhub separado para `company-news` (hoy solo existe `/stock/metric`); `main.py` (nuevo bloque `context`); el PDF (panel separado); el frontend.
- **Dependencias:** precio/volumen diario (✅ en Yahoo; **no se descarga hoy**); fecha de resultados (✅, con la trampa de SNOW: usar `earningsTimestampStart` + flag de estimado); noticias de 7 días (Finnhub `company-news`: [DESCONOCIDO] plan); sentimiento (probablemente **premium** → fuera del presupuesto $0); ajuste por splits en las series de precio (NFLX 10:1).
- **Ya existe parcialmente:** posición en rango (calculada en el PDF y el frontend, no en el motor); `_drawdown` en `alert_interpretations.py:478` lee `max_drawdown_1y`, que **nunca se rellena** (intérprete muerto); idem `fcf_trend_negative_years` (:362).
- **Riesgos:** latencia (+1-2 llamadas por ticker sobre un análisis hoy de 1 llamada); bloqueos de Yahoo desde Render; rate limit de Finnhub (60/min) con caché solo en memoria; sobreajuste (Apéndice 2); no mezclar con el score (criterio del spec).

### 6.7 Fuera de los seis, pero necesario (refuerza el "séptimo" del Apéndice)

1. **Capa de validación de entrada:** imposibles (FCF > OCF), artefactos (crecimiento de bancos), consistencia de definiciones (Share Issued vs Outstanding), splits, y valores negativos absurdos expuestos tal cual (SNOW: `pe` −116, `ev_ebitda` −126, `p_ffo` −108 en `key_metrics`; "Cobertura de intereses crítica −8.4x" junto a "Caja neta").
2. **Reproducibilidad entre entornos:** el mismo ticker da resultados distintos local vs prod (Yahoo degradado + Finnhub). Registrar en la salida qué fuente aportó cada campo.
3. **Red de seguridad:** suite mínima de tests y golden files de los 5 tickers de esta recon antes del paso 1 del "orden de trabajo".
4. **Fuentes únicas de umbrales:** hoy hay 4 copias (motor, alertas, PDF, frontend `sectorBench.ts`/`metricScale.ts`). El paso "extraer a `/config/*.yaml`" debe cubrir también el frontend (o servirle la config vía API), si no la divergencia persiste.
5. **Limpieza de código muerto** (`aggregate_alerts` y su árbol, históricos de `data_fetcher`, FMP, `config.py` decorativo), para no extraer a YAML umbrales que nadie ejecuta.

---

*Fin de la etapa 1. No se inició ninguna otra etapa.*

---

## 7. Hallazgos de producción

*Añadido en la etapa 2.1 (11-oct-2026). Fuente: `GET /api/_capture/{symbol}` en `finanzer.app` (Render, commit
`e0be7d4`), ~23:50 UTC. Las 6 capturas las sirvió un mismo proceso (`hostname:pid` idéntico en captura y
`/api/analysis`) y ninguna quedó contaminada. **Con el código de prod, el replay desde `backend/tests/fixtures/prod/`
reproduce exactamente el `/api/analysis` de producción en los 6 tickers**, así que todo lo de esta sección está
verificado, no inferido. Comparación detallada: `python3 backend/tests/diff_golden.py --local-vs-prod`.*

> **Corrección a §0–§6.** Todo RECON se hizo desde local, donde Yahoo responde completo. **En producción el pipeline
> recorre otro camino de datos** (7.1), así que varias conclusiones de §4 y §6 solo valen para local. La clasificación
> por entorno está en 7.4.

### 7.1 Yahoo responde 401 → el plan B es permanente en prod

- `v10/finance/quoteSummary` devuelve **HTTP 401 a todas las llamadas** desde Render: 6 de 6 por ticker (llamada,
  reintento tras refrescar el crumb y 2 reintentos más con sesión y perfil nuevos, `yf_adapter.py:246-261, 359-370`).
  Con eso `_do_fetch` cae **siempre** en `_fallback_yfinance` (`yf_adapter.py:886`).
- El plan B arma el dict con `fast_info`, `info` (solo para la beta) y los estados **anuales** de yfinance. Después
  **Finnhub** rellena los huecos: 18–29 campos por ticker. Consecuencias verificadas:
  - **El enriquecimiento con los estados del año previo no se ejecuta** (`_enrich_prior_year_data` solo corre en el
    camino v10, `yf_adapter.py:695`). En `_prior_year` solo queda lo que aporta Finnhub (ROA, current ratio, margen
    bruto, rotación, LTD/activos), **sin acciones**. Por eso Piotroski marca *"Sin datos de acciones históricas" → ✗*
    en los **6** tickers (el Fallo 2 del spec) y `buyback_yield`/`shareholder_yield` salen **null** siempre.
  - **El sector sale de `KNOWN_SECTORS`** (lista fija de unos 68 tickers, `yf_adapter.py:82-150, 922-924`). **O y
    FCX quedan como sector "Unknown"**: O no se valora como REIT (no hay P/FFO) y ambos usan umbrales y medianas por
    defecto. JPM y SNOW toman la industria con guion largo (`Banks—Diversified`) porque viene de la lista.
    *(Corrección, etapa 3: una versión anterior decía que `info["sector"]` llegaba y se ignoraba. **Es falso**: en
    prod `ticker.info` devuelve solo `{'trailingPegRatio': …}` porque el quoteSummary interno de yfinance también
    recibe 401. Ver 7.5.)*
  - **FCF = "Free Cash Flow" del estado de flujos anual** (no el FCF apalancado de `financialData`). EPS = Diluted EPS
    anual, corregido por el `epsTTM` de Finnhub si difiere más de un 2%. **`yearly_financials` sale vacío** (sin
    módulo `earnings`): la gráfica histórica no tiene datos en prod.
  - El snapshot final **no se marca como degradado** (`degraded: false`) porque Finnhub completa los campos de
    completitud. El 401 queda oculto para cualquier monitorización basada en ese flag.

### 7.2 Versiones en producción

| | Prod (Render) | Local (este Mac) |
|---|---|---|
| Python | **3.13.4** (el valor por defecto del servicio cuando se creó; hoy Render usa 3.14.3 para servicios nuevos) | 3.9.6 |
| yfinance | **1.7.0** | 1.2.0 |
| pandas | **3.0.6** | 2.3.3 |
| curl_cffi | **0.16.3** | 0.13.0 |
| Resto (numpy, pydantic, reportlab, requests…) | [DESCONOCIDO: no los registró la captura; están en el log de build de Render] | — |

`requirements.txt` usa `>=` (salvo fastapi y uvicorn), así que **cada deploy instala la última versión disponible**: la
línea base de prod solo es estable si se fijan versiones. A pesar de las diferencias de versión, el replay local
(Python 3.9 / pandas 2) reproduce prod exactamente: el motor es aritmética pura sobre los inputs congelados.

### 7.3 Las 5 diferencias más grandes local → prod y su causa

| # | Ticker | Diferencia | Causa (input crudo · procedencia en prod) |
|---|---|---|---|
| 1 | **O** | DCF **−45% → +72%**; score **82 → 63**; Altman 4.11 → 0.96; Solidez 20 → 4 | Sector **"Unknown"** en prod (KNOWN_SECTORS) → umbrales y medianas por defecto, sin rama REIT; FCF 1.58B → 3.99B (FCF apalancado de Yahoo v10 vs estado de flujos · fallback); crecimiento 20.3% → 10.9% (Finnhub); `totalAssets` 53.7B → 72.8B y `retainedEarnings` null → −10.5B (en local el v10 trae un balance incompleto y Altman toma RE = 0) |
| 2 | **NFLX** | DCF **+84% → −50%** (prod = informe del spec); grid 88–199 → 24–54, ninguno contiene $70; Altman 6.7 → 14.9 | FCF **25.39B → 9.46B** (FCF apalancado v10 > OCF, bug C5 · estado de flujos en el fallback); crecimiento 24.0% → 16.0% (Finnhub); `retainedEarnings` null → 42.3B |
| 3 | **JPM** | Crecimiento de ingresos **30.4% → 3.4%** → deja de ser "growth"; Crecimiento 20 → 14; score 74 → 68 | `revenueGrowth` de Yahoo (artefacto bancario, C6) → Finnhub con guarda anti-artefacto (CAGR-3Y); FCF null → −147.8B (estado de flujos) |
| 4 | **FCX** | Crecimiento de ingresos **+1.6% → −24.2%**; grid $9–20 → $2–6 frente a $74; Altman 4.85 → 3.33 | `revenueGrowth` de Finnhub (TTM YoY). **A verificar**: los estados anuales dan +1.8%, así que puede ser un artefacto de Finnhub. Sector "Unknown"; balance del fallback frente al v10 |
| 5 | **SNOW** | El grid **deja de contener el precio** ($210–431 ∋ $369 → $76–178 ∌ $369); upside −61% → −74% | Crecimiento 49.9% → 32.0% (Finnhub); FCF 1.74B → 1.12B (apalancado v10 > OCF → estado de flujos) |

También: V pasa de 91 a 87 (crecimiento 23.8% → 14.4%, Finnhub). NFLX de 97 a 99, la cifra del spec.

### 7.4 Reclasificación de los bugs por entorno

| Bug / fallo | Solo local | Solo prod | Ambos | Evidencia (golden local/prod) |
|---|---|---|---|---|
| FCF de `financialData.freeCashflow` (apalancado) > OCF (C5) | ✔ | | | NFLX 25.39B > 11.97B; SNOW 1.74B > 1.25B. En prod FCF ≤ OCF en los 6 |
| Acciones `Share Issued` en vez de `Ordinary Shares Number` (C3) | ✔ | | | Solo existe en `_enrich_prior_year_data`, que no corre en prod |
| `revenueGrowth` bancario artefacto 30.4% (C6) | ✔ | | | En prod lo reemplaza Finnhub (3.4%) |
| Altman con `retainedEarnings` ausente = 0 (§6.2) | ✔ | | | Aviso en NFLX/O/FCX/SNOW locales; en prod RE viene del estado |
| Piotroski "sin dato" = ✗ (Fallo 2) | | | ✔ | Local: JPM 2 criterios; prod: **"acciones" en los 6** (más 3 extra en JPM) |
| Sector "Unknown" fuera de `KNOWN_SECTORS` | | ✔ | | O y FCX en prod (xfail `test_bug_prod_sector_unknown_outside_known_list_o`) |
| Sin acciones previas → `buyback_yield` null; `yearly_financials` vacío | | ✔ | | Los 6 en prod |
| 401 de Yahoo oculto (`degraded: false`) | | ✔ | | Los 6 en prod |
| Crecimiento de ingresos de Finnhub sospechoso (FCX −24.2% vs +1.8% anual) | | ✔ (a verificar) | | FCX prod |
| WACC = solo coste del equity (C4) | | | ✔ | `wacc == Rf + β·MRP` en todos los no financieros de ambos juegos |
| Crecimiento distinto DCF vs grid / decay distinto (§6.5) | | | ✔ | Local: SNOW 124%; prod: O 14%, FCX 43%, SNOW 17% |
| Recuadro del caso base nunca dibujado (§1.4) | | | ✔ | Código del PDF, independiente del entorno |
| Normalización: no detecta la comisión de NFLX (C1) | | | ✔ | Ningún camino extrae partidas no recurrentes |
| Bancos con lectura de FCF/OCF y P/E (cambio 1) | | | ✔ | JPM Calidad 2/20 (local) y 6/20 (prod) por OCF negativo |
| Bandas del score 80/65/50/35 (motor) vs 80/60/40/20 (PDF) | | | ✔ | Código |
| Medianas sectoriales hardcodeadas (Fallo 3) | | | ✔ (en prod peor: "Unknown" → medianas por defecto) | Código |

**Implicación para el plan:** que un bug sea "solo local" no lo hace inofensivo. Si mañana Yahoo vuelve a responder
en Render, prod pasaría al camino v10 y heredaría los bugs de la columna "solo local" (FCF apalancado, Share Issued,
crecimiento bancario). Los arreglos deben validarse contra **los dos** juegos de golden.

### 7.5 Diagnóstico del 401 de Yahoo en prod (etapa 3; solo diagnóstico)

**Evidencia** (fixtures `backend/tests/fixtures/prod/*`, capturados en Render):

1. Las 6 × 6 respuestas a `query2.finance.yahoo.com/v10/finance/quoteSummary` tienen el **mismo cuerpo**:
   `{"finance":{"error":{"code":"Unauthorized","description":"Invalid Crumb"}}}`. No hay 403, 429 ni páginas de
   desafío: Yahoo emite cookie y crumb, pero **rechaza el crumb** al usarlo.
2. **El cliente de yfinance, independiente del nuestro, falla igual.** En prod, `ticker.info` (que usa quoteSummary
   con la gestión de cookies y crumb propia de yfinance, con varias estrategias) devuelve solo `trailingPegRatio`,
   que sale de otro endpoint. Que dos implementaciones distintas fallen igual descarta un bug de nuestro
   `_ensure_session` como causa principal.
3. **Desde el mismo servidor, los endpoints sin crumb funcionan:** `fast_info` (cotización y gráfico), los estados
   anuales (`fundamentals-timeseries`), la búsqueda (`/v1/finance/search`: `/api/search` de prod devuelve resultados
   de Yahoo) y Finnhub.
4. Desde una IP residencial (local), el mismo código y el mismo flujo de crumb obtienen 200.

**Causa probable:** Yahoo invalida (o no vincula a una sesión válida) el crumb para tráfico desde **IPs de datacenter**
(el rango de Render/Cloudflare, 216.24.57.x). Es un bloqueo por reputación de IP limitado a los endpoints protegidos
con crumb, no un error de cookies de nuestro código. Confianza: alta en "es por IP y solo afecta a endpoints con
crumb"; no verificable sin acceso a la lógica de Yahoo.

**Decisión de diseño (etapa 3):** no se implementa ninguna técnica de elusión (proxies, rotación de IPs ni de
huellas). **El plan B (yfinance sin crumb + Finnhub) es el camino permanente de prod**, y el camino quoteSummary
queda como "mejor caso" (local).

**Qué se pierde frente al camino local** (solo lo protegido por crumb):
| Dato (quoteSummary) | Sustituto en el plan B |
|---|---|
| `assetProfile.sector/industry` | **Búsqueda de Yahoo** (sin crumb) → etapa 3, bug (a) |
| `financialData` TTM: OCF, FCF, márgenes, `revenueGrowth`/`earningsGrowth` trimestral YoY | Estados **anuales** (FY, no TTM) + `/stock/metric` de Finnhub (crecimiento TTM con guarda) |
| `defaultKeyStatistics`: beta, forward EPS/PE, PEG, `lastSplitFactor` | Finnhub (beta, forwardPE, PEG); **forward EPS y factor de split: sin fuente** |
| `summaryDetail`: dividendo, forward P/E | Finnhub (dividendo, payout) |
| `earnings`: serie anual ingresos/beneficio (gráfica histórica) | Derivable de los estados anuales (no se hace en la etapa 3: es presentación) |
| `calendarEvents` / `earningsTimestamp*` (no se pedía ni local) | Nada nuevo (fecha de resultados → etapa 10) |

Consecuencia: en prod todo lo de flujo y márgenes es **anual (FY)**, no TTM, y el crecimiento viene de Finnhub. La
capa de validación de la etapa 3 marca esas procedencias en `data_provenance`.

### 7.6 Regla del crecimiento de ingresos (etapa 3, bug e)

`revenueGrowth` pasa por `validate._rule_growth` en **todas** las rutas (quoteSummary, plan B y Finnhub), con los
umbrales de `validate.THRESHOLDS`:

1. **Guarda anti-artefacto (G1)**: la de `finnhub_fallback._growth`, que ahora delega en `validate.growth_guard`
   (test de equivalencia en `test_validation.py`). El YoY se acepta si |YoY| ≤ 60 % o |YoY| ≤ 3 × |CAGR largo|;
   si no, se usa el CAGR-3Y. Fuera de Finnhub, los CAGR se calculan con los ingresos anuales de los estados
   (`_statements_fy`: CAGR-3Y y CAGR de 4 intervalos como "largo"). Flag `crecimiento_artefacto`.
2. **Coherencia con los estados (G2, solo financieras)**: si el crecimiento difiere más de 15 pp del YoY de los
   estados anuales, se sustituye por este, con flag `crecimiento_incoherente_financiera` (RECON C6: el "revenue"
   bancario tiene definición inestable).
3. **No financieras (G3)**: la misma diferencia solo deja un **aviso** (`crecimiento_incoherente`); puede ser
   aceleración real del último trimestre (SNOW local 49.9 % frente al 29.2 % FY; FCX prod −24.2 % frente al +1.8 %).

**Advertencia:** G1 por sí sola **no** corrige JPM (30.4 % < 60 %). Lo que lo corrige es G2 (30.4 % → 7.3 %).

### 7.7 Pendiente para etapas posteriores (detectado en la etapa 3)

- **Fecha de resultados (bug f)**: no se lee en ninguna ruta (`earningsTimestamp*`, `calendarEvents`,
  `isEarningsDateEstimate`). No se añade: etapa 10.
- **FCX −24.2 % (Finnhub)**: G3 solo avisa. Decidir en la etapa de crecimiento/DCF si se usa el YoY de los estados
  para no financieras cuando la diferencia es extrema.
- **Plan B sin `lastSplitFactor`**: si un estado viniera sin ajustar por split, la comparación de acciones se anula
  (no se corrige). Fuente posible sin crumb: `ticker.splits` (chart), por evaluar.
- WACC = Ke (C4), DCF frente a grid (§6.5), recuadro del caso base (§1.4), `yearly_financials` vacío en prod,
  forward EPS sin fuente en prod, normalización de partidas no recurrentes (C1): sin cambios en la etapa 3.

### 7.8 Regresiones conocidas hasta la etapa 6

Cambios de la etapa 3 que mejoran el dato de entrada pero hacen visible un problema de reglas que se resuelve en
etapas posteriores. Se aceptan a sabiendas al regenerar los golden.

- **JPM: Piotroski 2/9 ahora cuenta en Calidad.** Con el año previo disponible en prod (bugs b y c), el F-Score deja
  de ser "no concluyente" y entra en el score: Calidad pasa de 6 a 2 y el score de 68 a 64. Pero Piotroski **no
  aplica a bancos**: el CFO, el current ratio, el margen bruto y la rotación de activos no tienen sentido en un
  balance bancario. Se resuelve con la **rama FINANCIAL**.
- **O: Altman y Piotroski aplicados a un REIT.** Con el sector correcto (bug a), Altman pasa al modelo Z'' (1.55,
  zona gris) y Piotroski marca ✗ en current ratio. Ninguno de los dos es adecuado para un REIT (apalancamiento
  estructural, sin ciclo de circulante). Se resuelve con la **rama REIT**.
- **JPM: crecimiento de ingresos 7.3% en local frente a 3.4% en prod.**
  - Local (7.3%): YoY de los estados anuales de yfinance, FY2025 frente a FY2024 (181.8 frente a 169.4 B). La regla
    G2 sustituye el 30.4% de quoteSummary.
  - Prod (3.4%): Finnhub da un TTM YoY de 109.0%, que la guarda G1 descarta, y se usa su CAGR-3Y (3.36%). G2 no
    actúa porque 3.4% difiere menos de 15 pp del 7.3% de los estados.
  - **El dato más fiable es el 7.3%.** Compara dos ejercicios consecutivos con la misma definición de ingresos y la
    misma fuente que el resto del análisis en prod. El 3.4% no es un crecimiento interanual: es una media de 3 años
    sobre la serie de Finnhub, cuya definición de "revenue" bancario no coincide con la de los estados (el
    CAGR-3Y de los estados es del 12.5% frente al 3.36% de Finnhub, y el TTM YoY del 109% delata el mismo
    artefacto).
  - Pendiente para la rama FINANCIAL: en financieras, preferir siempre el YoY de los estados al de Finnhub, no
    solo cuando difieren más de 15 pp. A medio plazo, medir el crecimiento bancario con el margen de intereses
    neto o los ingresos netos, no con "Total Revenue".

### 7.9 Decisiones de la etapa 4 y pendientes que generan

Unificaciones aplicadas (un commit por concepto): niveles del score 80/60/40/20 en motor, PDF y UI; Piotroski
8/6/4/2 en interpretación, insignia, Calidad y UI; impuesto del ROIC 25% en los dos cálculos; crecimiento por
defecto del DCF 8%; D/E sin lectura en financieras; DCF y grid con el mismo crecimiento (tope 30%), el mismo
decaimiento y el crecimiento usado impreso en el PDF; texto de Altman con el umbral del modelo usado.

Pendientes registrados:
- **Etapa 8 — impuesto:** sustituir el 25% fijo (ROIC) y el escudo fiscal del WACC por la **tasa efectiva por
  empresa** (provisión de impuestos / BAI, acotada a un rango razonable).
- **Etapa 6 — crecimiento muy negativo:** sustituir un crecimiento <= −20% por un valor por defecto positivo (8%)
  es incorrecto (FCX prod: −24.2% pasa a +8%). En cíclicas debe usarse un **crecimiento normalizado de ciclo medio**.
- **Etapa 9 — UI:** el D/E de financieras ya muestra "—" con "No aplica a entidades financieras" en el código del
  frontend (MetricsGrid, HealthTab, ComparativeTab), igual que el PDF; falta **reconstruir frontend/out**. La misma
  reconstrucción publicará la leyenda de Piotroski corregida. Nota: V (Visa) cae en financieras por la palabra
  clave "credit services"; revisar en la etapa 5 (clasificación).
