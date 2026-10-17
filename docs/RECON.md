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
- **DCF y grid (hecho en la etapa 4):** el grid parte del crecimiento USADO por el DCF (tope 30% y el mismo suelo
  de la decisión 4) con el mismo decaimiento, y el PDF imprime ese crecimiento. Las celdas del grid siguen
  explorando ±5 pp alrededor del caso base (pueden superar el 30%). El caso base difiere <0.1% del DCF porque el
  grid redondea el WACC a 4 decimales.
- **Etapa 9 — bandas paralelas (principio ya decidido, no aplicado aún):** ROE, current ratio, cobertura, FCF yield,
  beta, DN/EBITDA, PEG, payout y el resumen 75/50 de la UI tienen hoy 3-4 juegos de bandas (score, alertas, lecturas
  del PDF en `thresholds.pdf`, colores de la UI en `thresholds.ui.metric_scale`). Principio: **una sola fuente de
  bandas por métrica**, **lectura del PDF = color de la UI**, y **bandas sectoriales donde el clasificador lo
  permita** (las de `sectors.score_thresholds`).
- **Etapa 8 — WACC mostrado frente a usado:** `dcf.wacc` muestra el coste del equity sin acotar; el DCF lo acota a
  [6%, 20%] y el grid a [8%, 18%] (y lo redondea a 4 decimales). Hoy coinciden en los 6 tickers; debe haber un único
  WACC (junto con el WACC real ponderado por deuda, C4).
- **Etapa 8 — celdas del grid sobre el tope:** el caso base respeta el tope común del 30%, pero las celdas exploran
  ±5 pp y lo superan (SNOW llega al 35%). Evaluar recortar las celdas en el tope o mantener la exploración simétrica.
- **Etapa 8 — suelo en el crecimiento terminal:** el DCF eleva el crecimiento de corto plazo hasta el terminal cuando
  es menor (FCX local: 1.6% → 2.5%), y el grid lo hereda. Es una elección de modelo a revisar.

### 7.10 Regresiones conocidas tras la etapa 5

La etapa 5 deja de inventar datos (Piotroski y Altman sin dato, reescalado por cobertura, categorías no
concluyentes) y conecta el FCF real y su CAGR a 3 años. Varios movimientos de score que resultan son
correctos según los datos, pero aplican reglas genéricas a arquetipos que necesitan otras. No se compensan aquí:

- **O +11 (Realty Income):** FCF/beneficio > 1 es estructural en un REIT (la depreciación hunde el beneficio
  contable), y el bono GARP no aplica a REITs. → **Etapa 6, rama REIT.**
- **SNOW:** la exclusión de Valoración (1/4 componentes: sin P/E, EV/EBITDA ni PEG significativos) sesga el total al
  alza en empresas sin beneficios, porque se quita justo la categoría que más las penalizaría. → **Etapa 6,
  arquetipo GROWTH_PRE_PROFIT con EV/Ventas.**
- **JPM Calidad 0:** Piotroski, OCF y FCF no aplican a bancos (el flujo operativo de un banco refleja la variación
  de depósitos y préstamos, no la calidad del beneficio). → **Etapa 6, rama FINANCIAL.**
- **FCX:** la tendencia negativa del FCF de una cíclica (CAGR −12.6%) la penaliza como si fuera estructural, en
  Crecimiento y, vía la calidad del crecimiento, en Valoración. → **Etapa 6, crecimiento normalizado de ciclo
  medio.**
- **NFLX:** CAGR del FCF +80% medido desde un año base deprimido (2022). → **Etapa 7, efecto base en los CAGR.**

### 7.11 Pendientes registrados en la etapa 6

- **Etapa 7 — crecimiento por acción en cualquier arquetipo:** en la etapa 6 solo el REIT mide su crecimiento
  por acción (CAGR del FFO y del FCF por acción; O: FFO agregado +12.2% anual frente a −0.1% por acción, con las
  acciones +12.3% anual). La regla debe generalizarse: en cualquier arquetipo, si las acciones en circulación
  crecen más de un umbral (en config), el crecimiento (ingresos, BPA, FCF) se evalúa por acción, en base ajustada
  por splits. La dilución estructural no puede leerse como crecimiento.
- **Etapa 8 — DCF de FCX −90% con FCF normalizado:** el FCF normalizado (margen FCF promedio × ingresos actuales,
  1.48 B) incluye el capex de expansión. Para cíclicas, evaluar el **FCF de mantenimiento** (OCF − capex de
  mantenimiento, aproximando el capex de mantenimiento con la D&A). Además, la **regla de confianza** debe marcar
  como de baja fiabilidad un DCF cuya conclusión supere un umbral de distancia al precio (en config).
- **Etapa 9 — retorno total en REIT y empresas de alto dividendo:** para el accionista, el retorno es dividendo +
  crecimiento. En la etapa 6 el REIT mide Crecimiento por acción (O: FFO por acción plano) y la rentabilidad por
  dividendo puntúa aparte, en Valoración. Evaluar si en ese arquetipo (y en MATURE de alto dividendo) Crecimiento
  debe ponderarse junto con la rentabilidad por dividendo, para no castigar como "sin crecimiento" un retorno que
  llega casi todo vía dividendo.

### 7.12 Etapa 7: TTM, normalización y crecimiento por acción

- **TTM en prod sin verificar:** los fixtures de prod son anteriores a la lectura de estados trimestrales, así que
  en replay prod cae al anual con el flag (`data_provenance.ttm.basis = "anual"`, `errors` = trimestrales ausentes).
  La verificación del TTM en prod (y la detección del pico no operativo de NFLX en prod) queda para la
  **recaptura de la etapa 11**. Los fixtures locales se complementaron solo con los tres estados trimestrales
  (`tests/supplement_local_quarterly.py`, marcado en metadata.supplements), sin recapturar el resto.
- **Altman pasa al último FY** (se define sobre ejercicios): en local deja de faltar el dato de utilidades retenidas
  (NFLX, SNOW, FCX tenían Altman "sin dato" por el balance incompleto de quoteSummary; O no aplica por arquetipo).
  Con ello local y prod usan el mismo modelo e inputs (SNOW tenía z 15.46 en ambos antes de pasar a "no aplica").
- **Modelo de Altman solo por arquetipo y sector/industria:** `altman_model` con coincidencia exacta contra
  `valuation.models.altman.manufacturing_sectors` (basic materials, industrials, energy → Z original; el resto →
  Z''). Se elimina el cambio automático a Z' (empresas privadas) cuando falta la capitalización: ahora es "sin
  dato". Antes el modelo dependía del dato disponible y de subcadenas ("financial services" entraba por "services").
- **X4 de Altman según cada variante (corregido):** Z original (1968) = capitalización / pasivo total; Z'' (1995) =
  patrimonio CONTABLE / pasivo total (antes el Z'' usaba la capitalización, que no es su variable: los coeficientes y
  cortes solo valen con las originales). NFLX pasa de 14.94 a 5.29 y V de 14.78 a 3.11, ambos en zona segura (> 2.60).
  Con la capitalización, SNOW daba zona segura (X4 18.05) con utilidades retenidas negativas.
- **GROWTH_PRE_PROFIT — runway en lugar de Altman:** el Altman se calibró con quiebras de empresas maduras endeudadas y
  no aplica. En Solidez lo sustituye el runway, con su mismo peso: FCF TTM >= 0 = autofinanciada (mejor tramo); si es
  negativo, (caja + inversiones a corto plazo) / quema anual de FCF en años, con tramos >= 3 / 2-3 / 1-2 / < 1
  (`thresholds.score.solidez.runway_*`). SNOW queda autofinanciada en ambos entornos (FCF TTM +1.19B local, +1.12B
  prod) y su Solidez no cambia (+6 del runway frente al +6 del Altman en zona segura).
- **REIT — payout sobre FFO:** `key_metrics.payout_ratio` = dividendos / FFO (`payout_basis = "ffo"`); el de beneficio
  neto queda como `payout_ratio_net_income`, solo de referencia. La lectura usa los tramos del score
  (`reit_ffo_payout_bounds`): O 79% "Cubierto" (local) y 90% "Justo" (prod), en lugar de 236-276% "Insostenible".
- **Recurrencia de partidas no recurrentes:** una partida del mismo tipo y signo en 3 o más de los últimos 4
  ejercicios (`thresholds.normalization.recurrence_*`) solo normaliza el exceso sobre su promedio. Resultan
  recurrentes: cargos especiales de O (deterioros, 4 de 4), de V (litigios, 4 de 4) y de SNOW; ganancias por venta de
  valores de O y V (SNOW solo en prod), y el total de partidas de JPM (3 de 4). Las pérdidas en valores de JPM (4 de 4) no entran
  en el total de Yahoo, así que no son un tipo propio (los componentes solo valen como tipos si cuadran con el total
  en cada ejercicio). El pico inferido de NFLX (1T-26, único) se sigue normalizando completo.
- **Etapa 9 — el score debe poder expresar la contradicción:** NFLX local llega a 100/100 con el P/E reportado no
  fiable (16.6% no recurrente) y un DCF negativo (−19.7%). Un techo del score condicionado por la confianza
  (P/E no fiable, DCF por debajo del precio, coberturas bajas) evitaría el "100" en una lectura con señales en
  contra.

### 7.13 Etapa 8: WACC real, DCF coherente y regla de confianza

- **WACC ponderado (C4 corregido):** E/(D+E)·Ke + D/(D+E)·Kd·(1−t) en `lib/cost_of_capital.py`. E = capitalización;
  D = "Total Debt" de Yahoo, que ya incluye los arrendamientos financieros cuando la empresa los informa (FCX, SNOW,
  O); los operativos no aparecen en esa fila (NFLX, V) y no se añaden. Kd = Rf + spread del rating sintético por
  cobertura (Damodaran, ratings.xls de ene-2026, guardado el 2026-01-26 y verificado el 2026-10-12: tramos de
  grandes y pequeñas a 5.000 M$ iguales a los de config; los spreads aproximados se sustituyeron por los vigentes,
  AAA 0.40% … D 19.00%). Regla M: EBIT < 0 con caja neta -> BBB; con deuda neta -> D (marcado). t = provisión / BAI
  del mismo periodo que el beneficio, acotada a [10%, 35%], con el 21% legal como fallback; la misma t en el ROIC.
- **Un solo WACC y un solo rango** ([6%, 20%]): el mismo en DCF, grid, spread ROIC−WACC y lo mostrado. El grid ya no
  desplaza su base a [8%, 18%]: recorta columnas y filas fuera de rango y lo indica (SNOW: sin 32.5% ni 35%).
  FINANCIAL no tiene WACC; REIT tiene WACC (spread) pero no DCF.
- **Rf:** ^TNX con caché de 24 h; si no hay lectura válida, el de config, marcado: 5.29%, el Tesoro a 10 años con
  el que Damodaran calcula la prima implícita (1-oct-2026). En replay (tests y golden) es siempre el de config: los
  golden no dependen del día de captura. **Prima y Rf de config forman un par** y se actualizan juntos.
- **Prima de riesgo = implícita de Damodaran:** 4.20% a 1-oct-2026 (TTM con payout ajustado; antes 5.5% heredada sin
  fuente). Kroll (5.0%) queda como referencia en el comentario de config. Una prima histórica mayor que la implícita
  hace que todo salga sobrevalorado por construcción.
- **Beta ajustada de Blume:** β = 0.67 × β bruta + 0.33 (config) en el Ke del WACC y en el de FINANCIAL; la bruta se
  sigue mostrando (`beta.raw` / `beta.adjusted`, y en el PDF). NFLX 1.61 -> 1.41.
- **Inputs del DCF:** CYCLICAL usa el FCF de mantenimiento (OCF − D&A/DD&A, promedio de los ejercicios): FCX 3.65B
  frente al normalizado 1.48B; DCF −90% -> −61%. El crecimiento de corto plazo ya no se eleva al terminal (FCX con su
  1.6% antiguo: 25.03 -> 23.65 $/acción, converge al 2.5% en la etapa 2). g >= WACC: sin dato con motivo.
- **Fiabilidad del DCF y aporte al score:** baja si el grid no contiene el precio, el valor terminal pesa > 85% o el
  FCF está marcado o inferido; media fuera del caso base ±1, en CYCLICAL o con posible cíclica. Aporte a Valoración:
  ±4 (alta), ±2 (media), 0 (baja, con el texto explícito). El rescate de growth no lo compensa. Con los fixtures, la
  prima implícita, el par Rf 5.29% y Blume: SNOW y FCX en baja (el grid no contiene el precio); NFLX prod −33% media
  (−2, score 99 -> 97); V local +15% alta (+2, 96 -> 98); NFLX local +8% alta (0, en precio).
- **Confianza del veredicto** (`lib/valuation_confidence.py`): convergencia, cobertura, calidad de fuente y
  estabilidad; media ponderada en config. **No limita el score** (techo: etapa 9). Regla de convergencia final:
  · métodos evaluables: DCF (si su fiabilidad no es baja) y múltiplos frente al sector; en FINANCIAL, P/B
    justificado por Gordon (intrínseco) y P/B frente a la mediana del sector (relativo; mediana provisional).
    Graham no vota: se muestra como "referencia del inversor defensivo (P/E 15 × P/B 1.5)";
  · por dirección (en precio = ±10% de upside, la banda del DCF en Valoración): alta si coinciden y la distancia
    entre señales es < 0.6 (30 pp de upside, de "en precio" a "claramente barata/cara"); media si coinciden pero
    la superan, o si uno está en precio y otro tiene dirección; baja si son opuestas;
  · un solo método evaluable: "no evaluable", no pondera y la confianza tiene techo en media.
  Por qué O local salía "alta" antes de este cambio: con un solo método la convergencia valía "media" (0.5 × 0.4 =
  0.2) y las otras tres dimensiones eran "alta" (0.6): 0.80 >= 0.75. Un veredicto sin ningún contraste llegaba a
  "alta" porque la falta de contraste solo restaba 0.2 puntos.
  Distribución con los fixtures: 4 alta (V prod, JPM ×2, V local), 7 media, 1 baja (FCX prod).
- **Etapa 11 — artefacto de los fixtures:** en prod la calidad de fuente nunca llega a "alta" porque los fixtures de
  prod no tienen estados trimestrales (TTM con fallback al anual: una incidencia fija). No se ajusta la regla para
  compensarlo; se verifica con la recaptura de la etapa 11.
- **Mantenimiento mensual — par prima/Rf:** Damodaran publica la prima implícita cada mes (home.htm, "Implied ERP on
  <fecha>", con el Tesoro usado). El par `valuation.capm.market_risk_premium` / `risk_free_rate` debe revisarse cada
  mes y actualizarse junto, con fecha. **Propuesta para la etapa 11:** un test o un aviso en el arranque que compare
  la fecha registrada en config con la de hoy (más de 35 días -> aviso en el log y en `data_provenance`), y un
  script de mantenimiento que lea home.htm, extraiga prima y Tesoro y proponga el cambio de config (sin aplicarlo
  solo: lo revisa una persona).
- **Etapa 9 — pendientes que deja la 8:** (a) techo del score condicionado por la confianza (NFLX prod sigue en 99
  con convergencia baja y un DCF que no concilia); (b) el número de Graham se sigue calculando en REIT con un BPA
  deprimido por la depreciación (no entra en la convergencia, pero se muestra): decidir si pasa a "no aplica";
  (c) con convergencia "media" y las otras tres en "alta", la confianza llega a "alta" (V local: DCF barata +15%,
  múltiplos en precio -> 0.80): revisar si el techo de la etapa 9 debe exigir convergencia alta.
- **Diferencia de entorno:** SNOW local tiene deuda neta en el último trimestre (Kd tramo D por la regla M) y prod caja
  neta en el FY (BBB); con un peso de la deuda del 2% el WACC apenas cambia (12.0% frente a 11.7%).

### 7.14 Etapa 9a: calidad y precio separados (motor, API y PDF)

- **Contrato:** sin score total único. `score` conserva `breakdown`, `excluded_categories` y
  `not_applicable_categories`; desaparecen `total_score`, `max_score`, `level`, `categories_included/total`,
  `partial` y `basis`. Nuevos: `quality` (Solidez + Rentabilidad + Calidad de ganancias + Crecimiento, reescalada a
  100 con cobertura y "no aplica"), `price_attractiveness` (Valoración: `score_raw`, `factor`, `score` contraído hacia
  50 según la confianza, `level`) y `verdict` (`text`, `confidence_text`, `full`). `price` sigue siendo el precio de la
  acción, por eso la puntuación no se llama así.
- **Consumidores del total revisados:** `main.py` (contrato), `financial_ratios.calculate_score_v2` (total y nivel),
  `pdf_report` (portada, radar, resumen, desglose, metodología), tests (`test_coverage`, `test_smoke`,
  `test_archetype_branches`), frontend (`StockPageClient` ScoreCard y resumen rápido, `EvaluationTab` cabeceras,
  `api.ts` tipos y `getScoreColor/Label`, `tooltips.SCORE_TOOLTIP`) y el generador de config (SCORE_LEVEL_BANDS ->
  QUALITY_/PRICE_BANDS). Las alertas no usaban el total.
- **Frontend (mínimo, sin rediseño):** la tarjeta muestra la calidad (0-100) y el veredicto; las cabeceras del desglose
  muestran calidad y precio. `tsc --noEmit` pasa. **`frontend/out` NO se ha reconstruido:** el export estático en
  producción sigue leyendo `score.total_score`. Antes de desplegar el backend de esta rama hay que reconstruir
  `frontend/out` (etapa 9b), o el frontend publicado mostrará la puntuación vacía.
- **Bandas del veredicto (config):** calidad excelente >= 80 / sólida >= 65 / media >= 45 / débil; precio (sobre el
  contraído) atractivo >= 65 / razonable >= 45 / exigente >= 30 / muy exigente. 50 es el neutro de las dos escalas
  (base 10/20 de cada categoría). Factores de contracción 1.0 / 0.75 / 0.5.
- **Confianza "alta" exige convergencia alta:** con convergencia media o no evaluable, techo en "media" (V local deja
  de ser "alta"; sin las bandas growth su convergencia pasa a baja: DCF barata frente a múltiplos cara).
- **REIT — retorno total:** Crecimiento puntúa rentabilidad por dividendo + CAGR del FFO por acción (bandas 10% / 7% /
  4% / 0 frente al Ke de un REIT); la rentabilidad por dividendo sale de Valoración. O: 6.0% + 0% (FFO/acción plano)
  -> Crecimiento 9 -> 11; Valoración 15 -> 14 (prod) y 17 -> 14 (local).
- **MATURE con dividendo alto — umbral propuesto 4% (no aplicado; pendiente de un fixture que lo verifique):** con
  rentabilidad por dividendo >= 4% (unas 3 veces la del S&P 500; utilities, telecos, tabaco), Crecimiento se
  evaluaría como retorno total (dividendo + crecimiento por acción), igual que en REIT, y el dividendo no puntuaría
  en Valoración. No afecta a ningún ticker del juego (NFLX 0%, V 0.7%, JPM es FINANCIAL), así que no hay forma de
  verificarlo con los fixtures actuales: se aplica cuando exista un fixture MATURE de dividendo alto (etapa 11).
- **Bandas, una sola fuente (parcial):** las lecturas del PDF de las métricas que puntúan usan las bandas del score:
  ROE y D/E con las bandas sectoriales (`sectors.score_thresholds`), spread ROIC−WACC, current ratio, cobertura,
  crecimiento (ingresos y BPA) y upside del DCF; sus copias en `thresholds.pdf` se eliminaron. `thresholds.pdf`
  conserva solo métricas que el score no puntúa (DN/EBITDA, payout fuera de REIT, beta, rango 52s, recompras, FCF
  yield, Graham, brecha frente al sector). **Pendiente (9b):** alinear las bandas de las alertas (cobertura, DCF,
  beta, DN/EBITDA) y generar las de la UI desde la misma config.
- **Precio sin calidad (decidido):** salen de Valoración todos los ajustes construidos con métricas de calidad: bono
  "Perfil GARP", bono "Growth Quality", el rescate de penalizaciones para growth de calidad ("Ajuste Growth" /
  "Ajuste Crecimiento") y el ajuste del P/E por calidad del crecimiento (`adjust_valuation_for_growth`, borrada). Se
  mantienen Forward P/E y PEG (múltiplos). `company_type` y `growth_quality_score` siguen en la salida como
  información de perfil, sin efecto en ninguna puntuación.
- **Bandas de múltiplos unificadas por arquetipo:** P/E, P/FCF y EV/EBITDA usan una sola banda dentro de cada
  arquetipo; se eliminan las bandas tolerantes "growth" (`pe_growth_*`, `pfcf_growth_*`, `ev_ebitda_growth_*`). El
  crecimiento entra al precio una sola vez, por PEG y DCF; relajar además las bandas lo contaba dos veces.
  Consecuencia: Valoración pasa a ser monótona en el P/E (antes un P/E mayor podía puntuar mejor al activar el tipo
  growth). Efecto en prod (crudo -> mostrado): NFLX 85->76 atractivo => 50->50 razonable (P/E 0->-2, P/FCF 0->-2,
  sin GARP +3; convergencia baja -> media); V 70->70 atractivo => 0->12 muy exigente (P/E +2->-4, EV/EBITDA -1->-4,
  P/FCF 0->-2, sin GARP; confianza alta -> media); FCX 40->45 razonable => 10->30 exigente (P/FCF normalizado
  -2->-4, EV/EBITDA normalizado 0->-4); SNOW 30->35 exigente => 20->28 muy exigente (sin "Ajuste Crecimiento" +2);
  JPM y O sin cambios.
- **BPA frente a ingresos (cerrado: informativo, no puntúa):** la diferencia entre el crecimiento del BPA y el de
  los ingresos (expansión de márgenes / apalancamiento operativo, o recompras) no puntúa: Crecimiento ya puntúa el
  BPA y los ingresos por separado y puntuar la diferencia contaría el BPA dos veces. Se publica como
  `eps_vs_revenue_growth` (`scored: false`, banda "en línea" ±2 pp en `thresholds.pdf.eps_revenue_gap`) con los
  mismos crecimientos que usa Crecimiento, y el PDF lo muestra en la página de crecimiento como dato informativo.
  No aplica donde no aplica el BPA (REIT, pre-beneficio).
- **Benchmark de múltiplos: perfil "market" cuando el arquetipo contradice al sector:** las medianas de un sector
  suponen un arquetipo (`sectors.benchmarks.sector_archetype`: financials -> FINANCIAL, real_estate -> REIT). Si el
  arquetipo de la empresa es otro (V: red de pagos MATURE dentro de Financial Services; una inmobiliaria no REIT),
  P/E y EV/EBITDA se comparan con las medianas del mercado amplio (`[benchmarks.market]`, PROVISIONALES): P/E 23.0x
  (mediana de los miembros del S&P 500, chartrow.com, 12-oct-2026; método no documentado) y EV/EBITDA 13.2x (mediana
  del S&P 500 a 1T-2025, Ivaluate; no hay mediana pública de constituyentes de 2026; el agregado de Damodaran
  ene-2026 sin financieras es 16.95x y no es una mediana). El resto de referencias del perfil hereda de
  `benchmarks.default` (fijadas a mano, sin fuente). Se registra en `valuation_benchmark` (perfil, motivo,
  fuentes) y en el PDF (columna MERCADO, nota con fuente y motivo, lecturas "frente a la mediana del mercado").
  **Resultado en V:** sin cambio de puntuación. Frente al mercado sigue "muy caro": P/E 31.1x / 23.0x = 1.35x
  (> 1.3x, -4) y EV/EBITDA 28.1x / 13.2x = 2.1x (-4); prod 0 -> 12 y local 20 -> 28, "muy exigente". El
  "muy exigente" de V no era un artefacto del benchmark de bancos. Cambian solo textos: lecturas y alertas
  (prod y local pierden la alerta de P/E: +35% y +37% sobre la mediana ya no son prima fuerte). **Pendiente (9b):** el frontend
  sigue comparando V con el sector (`sectorBench.ts` no exporta el perfil market).
- **Perfil market completo (override de todo lo sectorial):** cuando el arquetipo contradice al sector, no solo
  las medianas de múltiplos sino también los umbrales del score (ROE, ROA, D/E, márgenes, cobertura, liquidez) y
  los textos de alertas y lecturas usan el perfil market (`score_thresholds.overrides.market`, sector_key "market"
  en el score, las alertas y el PDF; `benchmark.thresholds_key` y `benchmark.thresholds` en el JSON; el campo
  `valuation_benchmark` pasa a llamarse `benchmark`). Los umbrales market son los de `score_thresholds.default`
  (ROE 20%/8%, D/E 1.0x…): PROVISIONALES, fijados a mano, sin fuente; no son medianas del S&P 500. V: D/E 0.66x
  frente a 1.0x pasa de +5 ("muy baja" frente a los 10x de un banco) a +2 ("controlada"); ROE 55.9% sigue
  excepcional (20% rango alto). Solidez prod 20 -> 20 (tope), local 20 -> 19; Rentabilidad 20 -> 20.
- **Bloque de múltiplos correlacionados:** P/E, Forward P/E, P/FCF, EV/EBITDA y PEG forman un bloque. Su ajuste es
  el promedio de los ajustes normalizados (positivo / máximo, negativo / |mínimo|) de los miembros con dato y
  aplicables, × `multiples_block_max` = 6, redondeado (mitades lejos de cero). El DCF sigue aparte (±4/±2/0). Los
  miembros siguen en el desglose con su lectura (`in_block`, ajuste entre paréntesis en el PDF) y la línea "Bloque
  de múltiplos" es la que puntúa. Cobertura: los miembros cuentan para la cobertura; se reescala el bloque. Forward
  P/E con dato y sin compresión cuenta 0 en el promedio. La señal de múltiplos de la convergencia usa el promedio
  del bloque como un solo múltiplo. **Efecto lateral a vigilar:** con un solo miembro el bloque amplifica su
  ajuste a ±6 (O: EV/EBITDA +2/4 -> +3; SNOW: P/FCF -4/4 -> -6; FCX: dos miembros a -4 -> -6). EV/Ventas
  (GROWTH_PRE_PROFIT), P/FFO (REIT) y P/B (FINANCIAL) quedan fuera del bloque (no estaban en la lista).
  **Resuelto:** el máximo escala con los miembros (`multiples_block_max_by_members` = ±2 con 1, ±4 con 2, ±6 con
  3+): O +1, SNOW -2, FCX -3. En FINANCIAL, P/B y P/TBV frente a sus justificados forman su propio bloque con las
  mismas reglas (JPM: -2 y -2 -> bloque -2 de ±4, antes -4).
- **Reportado / normalizado:** toda cifra calculada con el beneficio normalizado lo indica: en el desglose el
  nombre ("ROE normalizado", "ROA normalizado", "Margen neto normalizado", "FCF / beneficio neto normalizado",
  "P/E normalizado vs …", y el motivo del Forward P/E) con `normalized: true`; en las alertas el título y el texto
  ("ROE normalizado excepcional — 55.9%"). La portada muestra las cifras reportadas y lo dice ("ROE reportado",
  "P/E reportado (TTM)", "Margen neto reportado") cuando el score usa el normalizado. `normalized_metrics` en el
  contexto lista qué ratios salen del normalizado.
- **Crecimiento a 3 años = CAGR real (antes, interanual):** "Crecimiento Ingresos 3Y" y "Crecimiento EPS 3Y"
  puntuaban el interanual de Yahoo (revenueGrowth / earningsGrowth, trimestre contra el del año anterior) con la
  etiqueta de 3 años. Ahora: CAGR de los 4 ejercicios anuales (`historical_metrics.growth_rate`, con la regla de
  base anómala); ingresos con los extremos positivos, BPA con la fila "Diluted EPS" (respaldo: beneficio neto /
  acciones) y toda la ventana positiva; sin 4 ejercicios o con valores <= 0, sin dato con motivo (nunca el
  interanual). FCF ya era CAGR 3 años. **Excepciones justificadas:** REIT (FFO y FCF por acción, ya CAGR 3 años);
  CYCLICAL en ingresos conserva el crecimiento normalizado de ciclo medio (promedio interanual de todos los
  ejercicios disponibles, RECON §7.9): un CAGR punta a punta de 3 años depende de la fase del ciclo. **Pendiente de
  decisión:** el BPA de CYCLICAL usa ahora el CAGR punta a punta, que tiene el mismo problema de fase: FCX -14.0%
  (2021 fue pico) frente a +53% interanual; Crecimiento FCX 11 -> 7. **Resuelto:** el BPA de CYCLICAL usa el mismo
  crecimiento de ciclo medio que los ingresos (promedio interanual de los ejercicios disponibles, acotado a
  [-5%, 10%]): FCX -5.0% (cota inferior), sigue en "declive" (-4); Crecimiento 7. El dato informativo BPA frente a ingresos y
  las alertas de crecimiento ("anual en tres años (CAGR)") usan los mismos CAGR.
- **Rango de 52 semanas: solo posición, como contexto:** sin "cara"/"barata" en ninguna lectura; etiquetas de
  posición ("En máximos de 52 semanas", "Parte alta del rango"…) en tono neutro, barra en grises, tarjeta de
  portada "CONTEXTO · 52 SEM." y eje "CONTEXTO" en la página de crecimiento. **Pendiente (9b):** el frontend sigue
  mostrando la barra en U con lectura de precio.
- **Pendiente (9b) — motivos de confianza en lenguaje llano:** varios motivos de la confianza son jerga interna:
  campos de Finnhub ("16 campos de Finnhub en lugar de los estados"), "^TNX no disponible", "sin TTM", "valor de
  config", referencias a fixtures. Traducirlos a lenguaje llano para el lector (p. ej. "parte de los datos viene de
  una fuente secundaria", "tipo sin riesgo de referencia, no de mercado") manteniendo el detalle técnico en el
  anexo.
- **CYCLICAL — P/FCF normalizado sobre el FCF de mantenimiento:** el mismo FCF que usa el DCF (flujo operativo −
  capex de mantenimiento aproximado por la D&A, promedio de ciclo), no el margen FCF medio × ingresos actuales.
  FCX: 71.4x -> 29.0x (-4 -> -2).
- **REIT — rentabilidad sobre el FFO:** ROE, ROA, margen neto y ROIC−WACC (sobre el beneficio neto, deprimido por
  la depreciación) y los márgenes bruto y operativo (arrendamiento neto) pasan a "no aplica" (lista del
  arquetipo; también sin alertas: fuera "Margen bruto muy alto" y "Destruye valor"). Rentabilidad = FFO /
  patrimonio (bandas 10% / 8% / 6% / 4%, ±6) y margen FFO = FFO / ingresos (60% / 50% / 40% / 25%, ±5),
  PROVISIONALES. **Apalancamiento:** deuda neta/EBITDA con bandas de REIT ≤5.0x conservador (+4) / ≤6.5x adecuado
  (+2) / ≤7.5x en línea (0) / ≤9.0x elevado (-2) / alto (-4), propuesta PROVISIONAL sin muestra (un REIT con grado
  de inversión opera en 5–6.5x); la alerta usa las mismas bandas (advertencia > 7.5x, riesgo > 9x) y el PDF la
  misma lectura. El D/E queda informativo, sin puntuar ni contar en la cobertura. O: deuda neta/EBITDA 6.0x =
  "adecuado" (+2), sin alerta de riesgo; Solidez 13 -> 10 (pierde el +5 del D/E); Rentabilidad 17 -> 16.
- **GROWTH_PRE_PROFIT — rentabilidad de su fase:** ROE, ROA, margen neto, ROIC−WACC y el nivel del margen
  operativo "no aplican" (negativos por definición). Rentabilidad = margen bruto (75% / 65% / 50% / 35%, ±5),
  mejora interanual del margen operativo (+5 / +2 / 0 / -3 pp, ±4) y margen FCF (20% / 10% / 0 / -10%, ±5),
  PROVISIONALES. Sin bono "Growth Company" en ningún arquetipo (las bandas de crecimiento ya lo puntúan).
  **Efecto a vigilar:** SNOW prod pasa de calidad 59 "media" a 91 "excelente": Rentabilidad 0 -> 20 (bruto 67%
  +3, margen operativo -40.2% -> -30.6% +4, margen FCF 24% +5) y Solidez 11 -> 18 (el D/E -5 deja de puntuar con
  caja neta; la cobertura de intereses "no significativa" cuenta como sin dato y el reescalado da +2).
- **Regla M (todos los arquetipos):** ROIC no significativo si el capital invertido (patrimonio + deuda − caja) es
  menor que el 10% de los activos (`roic_min_invested_capital_share`; SNOW prod 7%: sin ROIC ni spread, motivo
  en `key_metrics.roic_reason`); FCF/beneficio no significativo con beneficio <= 0 (línea "No significativo" en
  el desglose y sin la alerta "Calidad del beneficio baja"); D/E sin puntuar con caja neta.
- **Narrativa sin métricas que no aplican:** ninguna lectura (intro de sección, resumen ejecutivo, tablas,
  alertas, metodología) cita una métrica "no aplica" para el arquetipo: el P/E, el E/P, el FCF yield donde no
  aplica el P/FCF (y en CYCLICAL el TTM, porque se lee el normalizado), el ROE, el spread y el crecimiento del
  BPA se omiten o se marcan "No aplica"; el Número de Graham no se muestra donde el P/E no aplica (FINANCIAL,
  REIT, GROWTH_PRE_PROFIT, CYCLICAL). Sin lectura propia, la intro de Valoración y la de Rentabilidad usan los
  componentes de la rama (P/B justificado, P/FFO, FFO, márgenes de su fase).
- **FINANCIAL — sustitución de política:** el crecimiento de una financiera desde los estados se marca con la
  acción "politica" (procedencia `politica_arquetipo`): queda registrado pero no cuenta como incidencia de
  validación ni baja la calidad de fuente (JPM: 3 -> 2 incidencias).
- **Etiqueta "normalizado" solo si difiere:** si el beneficio normalizado no difiere del reportado más de
  `normalization.label_min_diff` (0.1%), ni el desglose, ni las alertas, ni la portada dicen "normalizado", y la
  línea de normalización del PDF no se muestra (JPM y FCX: normalizado = reportado).
- **Compensación en acciones (SBC) — GROWTH_PRE_PROFIT:** el margen FCF, la regla de 40 y el crecimiento del FCF
  usan FCF − SBC (fila Stock Based Compensation del estado de flujos, en el mismo periodo que el FCF: TTM con los
  4 trimestres si el FCF es TTM; si no, el último ejercicio). Sin SBC del periodo: sin dato con motivo, nunca el
  FCF bruto. El runway sigue en caja pura (FCF sin ajustar): mide liquidez. Se publica `sbc` (SBC, SBC/ingresos,
  margen FCF bruto y ajustado) en todos los arquetipos. SNOW prod (FY2026): SBC 1.60B = 34.1% de los ingresos;
  margen FCF 23.9% -> -10.3%; regla de 40 55 -> 21 (+2 -> -2 en Valoración); FCF − SBC negativo los 4 ejercicios
  (crecimiento: CAGR no definido, sin dato). SNOW local (TTM): SBC 1.64B = 30.2%; margen -8.3%; regla de 40 23.
- **SBC en MATURE (evaluado, no aplicado):** propuesta de umbral SBC/ingresos > 5%: a partir de ahí la SBC mueve
  el margen FCF más de 5 pp y el P/FCF más de un 20% en una empresa con margen FCF del 25%. En el juego, ningún
  MATURE ni otro arquetipo se acerca (NFLX 0.8%, V 2.2%, FCX 0.5%, O 0.5%; JPM sin fila de SBC). Pendiente de
  decisión y de un fixture con SBC alta (etapa 11).
- **GROWTH_PRE_PROFIT — margen operativo de vuelta:** un componente de nivel con bandas del arquetipo (>= 0% / -10%
  / -20% / -30%, ±5, PROVISIONALES) además de la mejora interanual. ROE, ROA, margen neto y ROIC−WACC siguen en
  "no aplica". SNOW prod -30.6% -> -5; Rentabilidad 20 -> 7.
- **"No significativo" = "no aplica" en la cobertura:** la regla M (cobertura de intereses con EBIT < 0 y caja
  neta, ROIC con capital invertido pequeño, FCF/beneficio con beneficio <= 0, D/E con caja neta) no cuenta en el
  denominador ni provoca reescalado (`coverage.not_significant`). SNOW prod: Solidez 18 -> 16 (sin el +2 del
  reescalado).
- **CYCLICAL — narrativa de crecimiento:** la sección 04 y el resumen usan el crecimiento de ciclo medio de
  ingresos y BPA (el del score), no el interanual ("FCX: 53.1%, ritmo propio de compañías growth" desaparece).
- **Regla general — negativo sostenido = señal, no "sin dato" (decidido):** un valor negativo en todos los
  ejercicios de la ventana impide calcular una tasa, pero no es un dato ausente: puntúa en el peor tramo
  (`historical_metrics.growth_rate` lo marca `sustained_negative`; un cambio de signo sigue siendo "sin dato").
  SNOW: FCF − SBC negativo los 4 ejercicios -> crecimiento del FCF en el peor tramo (-3) en lugar del reescalado
  que llevaba los ingresos al máximo; Crecimiento 19 -> 12.
- **GROWTH_PRE_PROFIT — FCF − SBC también en Calidad de ganancias:** el componente FCF usa FCF − SBC (la misma
  definición que el margen, la regla de 40 y el crecimiento). SNOW: +3 -> -3; Calidad de ganancias 16 -> 9.
- **Autofinanciada en caja:** si la SBC supera el FCF, la fortaleza, el runway del desglose y la lectura del PDF
  dicen que es autofinanciada en caja y que la compensación en acciones (SNOW: 34.1% de los ingresos) se paga con
  dilución; no afirman que no dependa de capital.
- **Resultado SNOW:** calidad 91 -> 72 -> **55 "media"** (prod) y 48 "media" (local); los otros cinco no cambian.
- **Presentación:** la portada cabe siempre en una página (si el contenido no entra, se reduce en bloque con
  `KeepInFrame` en lugar de desbordar a la página 2; SNOW desbordaba); concordancia en las lecturas de
  crecimiento ("el BPA se contrae", "los ingresos se contraen").
- **Etapa 9a cerrada** con estos cambios; goldens regenerados en un commit propio.
- **Etapa 11 — saturación de la calidad:** NFLX (100) y V (98) saturan la calidad del negocio. Evaluar con una
  muestra amplia si los componentes correlacionados de Rentabilidad (ROE, ROA y el ROIC del spread) deben
  agruparse en un bloque como los múltiplos, y revisar con esa muestra los tramos superiores de las categorías.
- **Etapa 11 —** el PDF de revisión se genera desde los fixtures de prod (Rf de config, sin TTM).

### 7.15 Etapa 9b: el frontend consume el contrato nuevo

- **Capa de presentación compartida (`lib/display.py`, `result["display"]`):** estado de cada fila (con dato /
  sin dato / no aplica / no significativo), lectura, tono y frase; KPIs de portada por arquetipo; fortaleza / a
  vigilar / contexto; filas de cada sección; tarjetas institucionales; desglose; tooltips. El PDF solo maqueta el
  bloque (los lectores se movieron de `pdf_report` a `display`) y la web solo lo pinta.
- **Decisiones A–D:** Altman `z_score` y Piotroski `score`/`scaled_score` null cuando no aplican; fuera
  `is_growth` y `company_type` (el arquetipo los reemplaza; ningún cálculo los usaba); tooltips con solo las
  bandas aplicadas a la empresa (arquetipo y benchmark), generadas desde la config del score, y test de
  coherencia banda a banda con cada lector; pestaña Histórico desde los estados anuales de los CAGR
  (`archetype_metrics.yearly_financials`; FCF − SBC en GROWTH_PRE_PROFIT), dato bruto, fuera del PDF.
- **Motivos en lenguaje llano (`lib/plain_language.py`):** una tabla para PDF y web. Portada y resumen muestran el
  texto llano (uno por dimensión primero, máximo 3); el técnico queda en el "Detalle técnico" de la web y en la
  sección de confianza del PDF. "^TNX no disponible" y el techo de confianza no se muestran (redundantes).
  Desviación del ejemplo propuesto: `crecimiento_incoherente` es un aviso (el valor se mantiene), así que el
  texto dice "se mantiene, pero conviene tomarlo con cautela", no "se recalculó".
- **Cambios del PDF por el refactor (justificados):** motivos en lenguaje llano; en el resumen ejecutivo, las
  tarjetas de ROE y margen neto de REIT y pre-beneficio dicen "No aplica" (antes se leían frente al sector, contra
  la regla de la 9a); sin la sección "Evolución histórica anual" (solo aparecía en local).
- **Config:** fuera `[ui.metric_scale]` (tercer juego de bandas); `category_tone_bounds` y `exec_category_bounds`
  pasan a config (eran literales del PDF). `backendConfig.ts` solo exporta arquetipos y rótulos de estado.
- **Guardianes:** `frontend/scripts/check-analysis-literals.mjs` (prebuild; sin umbrales literales en los
  componentes de análisis), `check-contract.mjs` + `tests/test_frontend_contract.py` (la web no lee campos que el
  backend no expone) y sello del contrato en `frontend/out/build-stamp.json`, validado por `build.sh`.
- **Pendiente:** los golden (A, B, D y `display`) se regeneran con la aprobación del diff.
- **DCF con el crecimiento de los estados (opción b, decidido):** el crecimiento de entrada del DCF es siempre
  el mismo que puntúa Crecimiento (`fin_dict["revenue_cagr_3y"]`: CAGR de ingresos a 3 años con la regla de base
  anómala, por acción si aplica la regla de dilución, ciclo medio en CYCLICAL). El `revenueGrowth` de la fuente
  queda solo como dato informativo "(interanual)"; un valor marcado `crecimiento_incoherente` ya no entra en el
  score (test de `test_known_bugs`, antes xfail). Efecto: NFLX local (24.0% -> 12.6%: precio 55 -> 46, confianza
  alta -> media), V local (23.8% -> 10.9%: precio 50 -> 30 "exigente", confianza media -> alta) y V prod (14.4% ->
  10.9%: precio 39 -> 25 "muy exigente", confianza media -> alta); NFLX prod y SNOW cambian el valor del DCF sin
  cambiar su aporte; FCX, JPM y O no cambian. La calidad no cambia en ningún caso.

### 7.16 Etapa 11b: muestra amplia en producción (pendientes registrados)

- **BRK-B marcada "posible cíclica" (sin corregir).** Su industria de Yahoo es `Insurance - Diversified`, así que
  el clasificador la trata como aseguradora (FINANCIAL, regla `industria_aseguradora`). La confianza de la
  clasificación sale **baja** por la alerta de posible cíclica: la desviación del crecimiento interanual de
  ingresos es de **52.5 pp** (umbral 15 pp). Causa probable: los "ingresos" de Berkshire incluyen las ganancias y
  pérdidas de su cartera de inversiones (valor razonable de acciones cotizadas), que saltan de un año a otro sin
  que el negocio asegurador ni las filiales operativas sean cíclicos. Pendiente decidir: excluir las ganancias de
  inversión de la serie de ingresos para la regla de volatilidad, o tratar los conglomerados aparte.
- **Clase de acciones en BRK-B:** los estados de yfinance dan el BPA por acción B y las acciones en equivalentes A
  (1.44 M); Finnhub da el BPA de la clase A (59 668). Corregido en la 11b (factor de clase por fila; Finnhub no
  impone BPA cuando los estados se reexpresaron; regla de plausibilidad de P/E y P/B).
- **IFRS:** ASML no tiene la fila `Operating Cash Flow` (usa `Cash Flow From Continuing Operating Activities`);
  NVO y JPM dan `Cash Dividends Paid`; FCX da `Depreciation Amortization Depletion`. Corregido con alias de
  filas (`currency.ROW_ALIASES`) y aviso `fila_clave_ausente` por arquetipo. `Cash Dividends Paid` incluye los
  dividendos preferentes: el payout de JPM sube de 26.6% (Finnhub, TTM) a 29.1% (estados, FY).
- **Plan B siempre "degradado":** en Render `info` y quoteSummary dan 401, el plan B nunca trae beta, forward,
  dividendo ni crecimientos y `_is_degraded` lo daba por degradado: dos reintentos completos más 2.4 s de espera
  (10–12 s por análisis en frío). Corregido: sin reintentos en el plan B, bloqueo de quoteSummary recordado 10 min
  y estados anuales descargados una sola vez (3.2–4.4 s simulando Render).

- **Forward P/E del perfil market:** heredaba el 18x de `default` (sin fuente). Ahora tiene una referencia
  explícita: **18.9x**, el P/E forward del índice S&P 500 al 30-sep-2026 (consenso de 12 meses de Bloomberg, First
  Trust, "Market Minute" de octubre de 2026). Es **provisional**, y es un agregado del índice, no una mediana de
  constituyentes (no hay mediana forward pública). Efecto en V (prod): la compresión del Forward P/E (24.2x) vuelve a
  sumar porque 24.2x < 18.9 × 1.3 = 24.6x. El bloque pasa de −4 a −3, Valoración de 4/20 a 5/20 y el precio de 20 a
  25 (sigue en "muy exigente").

### 7.17 Precio con un solo método evaluable: casi no llega a "muy exigente" (decisión pendiente)

Registrado en la revisión de la 11b; **decisión de diseño para otra ronda, sin cambio de código**.

- **Caso: PLTR** (muestra amplia). P/E 179.9x frente a 30x del sector, P/FCF 149x, EV/EBITDA 185x, PEG 1.81, y
  el precio sigue en **"exigente" (35)**, no en "muy exigente".
- **Por qué.** El DCF tiene fiabilidad baja (el grid no contiene el precio) y no puntúa, así que el bloque de
  múltiplos es el único método evaluable. El bloque promedia los ajustes reescalados a ±1 de sus miembros y se acota
  a ±6 con 3+ miembros. En PLTR la media es −0.70: P/E −1, P/FCF −1, EV/EBITDA −1, PEG −0.5 y el **Forward P/E 0**
  (la compresión no suma en la peor banda, pero el miembro tampoco resta: es una regla de compresión, no de
  nivel). El bloque queda en **−4**, Valoración 6/20, precio sin ajustar 30 y, con la confianza media (factor 0.75),
  50 + (30 − 50) × 0.75 = **35**.
- **El techo es estructural.** Con un solo método, el mínimo es el bloque en −6, es decir Valoración 4/20 y precio
  sin ajustar 20. Para llegar a "muy exigente" (< 30) con confianza media hace falta una media del bloque ≤ −0.92
  (prácticamente todos los miembros en la peor banda, y el Forward P/E nunca aporta −1). Con confianza baja
  (factor 0.5) el suelo es 35 y nunca se llega. Además, un solo método evaluable empuja la confianza hacia media
  o baja, y eso vuelve a contraer el precio hacia 50.
- **Opciones para la próxima ronda** (sin decidir):
  1. que el Forward P/E en la peor banda reste como nivel, no solo como compresión;
  2. que el tope del bloque crezca cuando es el único método evaluable;
  3. que la contracción por confianza no se aplique, o se aplique menos, cuando la confianza baja solo porque falta
     el segundo método y no porque los métodos discrepen.

### 7.18 Fase 0 del plan de fiabilidad: panel de referencia y línea base

*Operador F0, 14-oct-2026. Detalle: [`fiabilidad/F0_LINEA_BASE.md`](fiabilidad/F0_LINEA_BASE.md); bitácora
[`fiabilidad/BITACORA.md`](fiabilidad/BITACORA.md), registros #2–#5.*

- **Qué se capturó:** juego `panel`, 31 tickers en 9 grupos (`fixture_backend.PANEL_GROUPS`), el 14-oct de 16:15 a
  16:17 Nueva York (precio de cierre), con fixtures y golden propios (`tests/{fixtures,golden}/panel`). SPY se graba
  como rechazo 422. No se tocaron los juegos `local`, `prod` ni `muestra`.
- **Cómo:** `capture_fixtures.py --env panel --render-sim`: captura local con Render simulado (S1 quoteSummary 401
  "Invalid Crumb"; S2 `ticker.info` vacío), así el pipeline va por el plan B + Finnhub como en producción. Finnhub a
  ≤ 1 petición cada 1.1 s; la clave se lee del Llavero de macOS y no se graba. Rf congelada a la de config.
  Validado contra finanzer.app (JPM, NFLX): con la Rf y el precio de prod, 0 diferencias. Se descartó reabrir
  `/api/_capture` (exigía desplegar).
- **Vara de medir:** el panel entra en la regresión y el determinismo; `invariants.py` reúne los 26 invariantes
  genéricos (valen para cualquier ticker; los tests atados a los 6 tickers siguen en su archivo) y
  `test_panel_invariants.py` los corre sobre el panel (780 comprobaciones; 2 xfail estrictos);
  `test_invariants_detectan.py` prueba que cada uno detecta su violación. `panel_run.py` corre el panel en replay o
  live, con `--compare` y, en live, las diferencias separadas en solo Rf / solo precio intradía / reales.
- **Línea base:** F2 24/31 coinciden con la tabla propuesta (no: CAT, PLTR, NVDA, CRWD; dudoso: BRK-B; a decidir:
  TSM, ASML). F3: PLTR "EBIT negativo" con EBIT +2.63 B, "STRONG" en 4 financieras, códigos en el detalle técnico,
  panel "Composición" tapado en la página 2, cota del ciclo medio presentada como dato (XOM, DOW, FCX, MU, ASML).
  F4: un solo método de precio en 18/30, calidad ≥ 95 en 5, DCF de fiabilidad baja en 11. F5: determinista;
  live = replay salvo Rf y precio en 23/30. Latencia: p50 6.7 s, p95 45.9 s, máx 52.5 s; JPM en frío 46.1 s.
- **Hallazgos nuevos:** (1) **Yahoo devuelve a Render datos distintos que a una IP residencial** en 7/30
  (acciones, balance trimestral, acciones diluidas trimestrales), con local estable; la captura local con Render
  simulado tiene ese límite y `panel_run --mode live` lo vigila. (2) **`golden/prod` ya no representa
  producción**: sus fixtures (11-oct) no tienen trimestrales y su replay sale en base anual, mientras prod calcula
  en TTM (D8). (3) NVO cambia de nivel de precio con 10 pb de Rf. (4) `muestra` se capturó por quoteSummary sin
  Finnhub: no representa producción (la sustituye `panel`).

### 7.19 Fase 1 del plan de fiabilidad: lo visible hoy

*Operador F1, 14–15-oct-2026. Detalle: [`fiabilidad/F1_DIFF_GOLDEN.md`](fiabilidad/F1_DIFF_GOLDEN.md) (diff de
golden causa por causa), [`fiabilidad/F1_DISENO_GUARDIAN.md`](fiabilidad/F1_DISENO_GUARDIAN.md); bitácora, registros
#7–#15. Deploy `9e78f3b..4e90ff6` (rollback `9e78f3b`).*

- **D8:** retirados los juegos `prod` y `muestra`; sus tests corren sobre el panel.
- **Guardián narrativo** (`lib/claims.py`, `tests/guardian.py`): cada afirmación se declara junto a su texto y se
  comprueba contra el dato; red de seguridad sobre el display y el PDF normalizado; lista negra (inglés, códigos fuera
  del anexo); reglas estructurales (#6 mercado/sector, #7 veredicto, #10 "no aplica" sin cifra en tarjetas y tablas,
  #17 moneda, #20 base temporal, posición 0–100, ningún múltiplo negativo como nivel en una tarjeta) e **identidades
  entre datos** (dividend yield frente a payout × E/P, shareholder yield = dividendo + recompras). Entró en rojo con 85
  xfail y cierra con 0 en 37 informes (1112 comprobaciones); `test_guardian_detecta.py` prueba cada mecanismo.
- **Arreglos de texto y lógica (un commit por causa):** cobertura de intereses por el signo del EBIT y del
  resultado financiero (PLTR: `sin_carga`, rating AAA, nivel de precio sin cambio); "STRONG"/"N/A" en castellano;
  D1: anexo "Detalle técnico para auditoría" al final del PDF y la web sin códigos; cota del ciclo medio dicha como
  cota; invariante del crecimiento con el signo del verbo; V "frente al mercado"; BRK-B "último ejercicio"; AMT sin
  dilución inexistente; rango de 52 semanas con la cotización; caja neta en la portada; "No aplica" sin cifra en
  tarjetas y tablas (cambia la regla de la 9b por decisión del usuario); dividendo sostenible por payout; etiqueta del
  P/B justificado; ROCE visible en la web y en el resumen del PDF (sin bandas: comparación con el ROIC).
- **Identidad del dividendo (BCS):** el 50.46% de BCS venía de Finnhub (dividendo de la acción ordinaria en peniques,
  11.5) dividido por el precio del ADR en dólares: peniques, sin factor ADR y sin conversión de moneda (≈ 18×). El
  mismo defecto en TSM (6.05%), NVO (30.69%) y NVDA (0.45%). El yield que supera 2 veces lo pagado sale sin dato con
  aviso y no puntúa; el origen se arregla en la fase 2.
- **Maquetación del PDF:** página 2 en flujo natural a ancho completo; celdas largas partidas en su columna; anexo sin
  partir; `tests/pdf_geometry.py` (pypdfium2): texto dentro del área útil, sin solapes y escala de encogimiento
  ≥ 0.85 (mínimas: portada 0.936, página 2 0.968).
- **Producción:** push `9e78f3b..4e90ff6` el 15-oct a las 10:41 (Nueva York), sello servido a las 10:43.
  `panel_run --mode live` frente a F0 live: NVO cambia de nivel por Rf y precio (efecto frontera conocido) y JNJ por
  el dato (Finnhub impuso su `epsTTM` sobre el BPA TTM de Yahoo); nada atribuible al código. Detalle en
  `DEPLOY_VERIFICATION.md`.
- **Panel:** BCS añadido (grupo "Revisión externa"). Frente a la corrida F0, ningún cambio de arquetipo, nivel de
  calidad, nivel de precio ni confianza; el único cambio de puntuación (fila de cobertura de PLTR) cae en una
  categoría ya en su tope.
- **Métricas F3 de cierre:** contradicciones 0 (línea base: PLTR); palabras en inglés 0 (STRONG en 4); códigos fuera
  del anexo 0 (30/30); defectos de maquetación 0 (página 2 en todos); fallos del guardián 0 (85 al entrar); xfail de
  invariantes 0 (2).
- **Pendientes que deja (mapa de la bitácora):** origen del dividendo en ADR (fase 2), identidad del dividendo a la
  baja (fase 2), métricas que aplican a FINANCIAL (fase 3), factor ADR 4.154 frente a 4 y AT1 (fase 2/3), ROCE con
  referencia y bandas (fase 4).

### 7.20 Fase 2a del plan de fiabilidad: verdad de datos (medir)

*Operador F2a, 15-oct-2026. Detalle: [`fiabilidad/F2_EDGAR_DIAGNOSTICO.md`](fiabilidad/F2_EDGAR_DIAGNOSTICO.md)
(cobertura, conceptos, huecos y factores ADR), [`fiabilidad/F2_DISCREPANCIAS.md`](fiabilidad/F2_DISCREPANCIAS.md)
(línea base de F1, causas y efecto en el veredicto) y [`fiabilidad/F2_PRECEDENCIA.md`](fiabilidad/F2_PRECEDENCIA.md)
(escenarios de D2, diseño de D7 y beta); bitácora, registros #17–#19. Deploy `8ed57a0..25b9d8a` (rollback
`8ed57a0`). La 2a no corrige datos del motor: todo lo que encuentra va a la 2b.*

- **T0, `/api/health`:** devuelve el commit desplegado (`RENDER_GIT_COMMIT`). Es el único cambio de código de
  producción de la 2a. Verificado en finanzer.app: `{"status":"ok","commit":"25b9d8a3…"}` a las 16:34:57 (Nueva York).
- **T1, panel ampliado:** HSBC, SHEL, UL y TM (grupo "Extranjeros (fase 2)"), capturados el 15-oct tras el cierre de
  Nueva York. El panel pasa a **36 tickers**, con golden. El guardián tenía un falso positivo en UL ("sin TTM" leído
  como "TTM"): arreglado con su test (`385e441`).
- **T2, EDGAR:** extractos de companyfacts de los 35 emisores con estados, más los filings con XBRL que la API aún no
  trae, leídos de su instancia. Incluye la tabla de conceptos por campo (US GAAP e IFRS) y los factores ADR con su
  fuente (20-F y F-6).
- **T3, línea base de F1 ("dato correcto"): 90.0%** de los campos comparables dentro de tolerancia (1,262 de 1,403);
  PLAN §3 pide ≥ 95% para cerrar la fase 2.
  - Por origen: EE. UU. 91.6%; extranjeros 82.9%.
  - Ratios recalculados con EDGAR: 84.7%.
  - Causas de lo que queda fuera: definición 78, fuente errónea 41, periodo 14, unidad + factor ADR 4, factor ADR 4.
  - Hay 220 comparaciones sin dato del periodo en EDGAR y quedan fuera del porcentaje.
  - Herramientas: `tests/edgar_verify.py` y `tests/beta_ref.py`.
- **Efecto en el veredicto:**
  - corregir solo los errores de dato: **0 cambios de nivel en 35**;
  - EDGAR con la tabla de conceptos tal cual: 1 (NFLX, por la definición de D&A);
  - deuda con la regla de coherencia con el EBITDA: 0;
  - beta propia: 3 (BRK-B, NVO y NFLX).
- **Casos confirmados:**
  - el dividendo de Finnhub de los 7 ADR (BCS, TSM, NVO, HSBC, SHEL, UL y TM) viene en la moneda de la línea local y
    por acción ordinaria;
  - BCS: factor 4.154 por desfase de fechas (recompras) y cupones AT1 en los dividendos y el BPA;
  - UL: perímetro (Yahoo ya trae los ingresos reexpresados) y factor 1.012, sin efecto;
  - JNJ: BPA de Finnhub con un trimestre más que los estados (en vivo) y utilidades retenidas solo en EDGAR;
  - la beta de Finnhub en los ADR: 6 de 8 difieren más de 0.3 de la de referencia.
- **Casos descartados:** NVDA tiene bien el dato de origen. Es un **falso positivo** de la identidad del dividendo de
  la fase 1 (subida del trimestral de 0.01 a 0.25), en producción.
- **Casos nuevos:**
  - TM: factor 11.07 frente a 10 oficial, porque la capitalización de Yahoo sale un 9.6% corta;
  - HSBC: AT1 al revés que BCS (Yahoo da los dividendos al ordinario);
  - deuda de O (+6.2%) y DUK (+1.1%): fuente errónea, con hipótesis para la 2b;
  - la fase 0 vio datos distintos de Yahoo en Render y en local (7/30). Medidos contra EDGAR: Render tenía razón en 3,
    en 2 son cortes distintos y los dos datos son reales, y 2 no se pueden verificar.
- **T4, F2_PRECEDENCIA (criterios del usuario):**
  - precedencia por campo con corte coherente;
  - deuda coherente con el EBITDA: arrendamientos de IFRS 16 y financieros de US GAAP sí; operativos de US GAAP no;
    en FINANCIAL, sin la subordinada. Solo cuentan los arrendamientos en balance (MSFT, AMZN y MU verificados);
  - aviso "La empresa publicó resultados el <fecha>; este análisis aún no los incorpora";
  - beta propia recomendada;
  - D7: emisores registrados en la SEC.
- **D2 decidida (usuario, 15-oct; literal):** "acepto tus recomendaciones". La recomendación aceptada: "D2 = EDGAR como
  verificación por ahora, y como respaldo para lo que Yahoo no da (utilidades retenidas de JNJ, D&A de BCS). La 2b
  arregla en origen los errores de dato: dividendo de Finnhub, factor ADR oficial, corte coherente y el falso positivo
  de NVDA. EDGAR pasará a fuente principal campo a campo cuando la fase 3 cierre las definiciones (deuda, capex, EBIT
  bancario)."
- **Pendientes que deja para la 2b** (mapa de la bitácora): dividendo de Finnhub de los ADR en origen, factor ADR
  oficial, corte coherente del BPA (JNJ), falso positivo de NVDA e identidad a la baja (PGR), EDGAR como respaldo
  (utilidades retenidas de JNJ; D&A de BCS y de BRK-B), beta propia, deuda de O y DUK.
  - Para la fase 3: definiciones de deuda, capex y EBIT bancario, y AT1 en el método de FINANCIAL.

### 7.21 Fase 2b del plan de fiabilidad: verdad de datos (corregir)

*Operador F2b, 16-oct-2026. Detalle: [`fiabilidad/F2b_PARADA1.md`](fiabilidad/F2b_PARADA1.md),
[`fiabilidad/F2b_PARADA2.md`](fiabilidad/F2b_PARADA2.md) (medida final, diff de golden causa por causa, tiempo) y
[`fiabilidad/F2b_MUESTREO_MANUAL.md`](fiabilidad/F2b_MUESTREO_MANUAL.md); bitácora, registros #21 y #22. Rama
`fiabilidad/f2b-corregir`, fusionada en `main` por avance directo desde `60f8a69`. Producción: `103c76f` (rollback de
código: `60f8a69`). Todo arreglo es de fondo: la 2b retira las dos protecciones provisionales de la fase 1.*

- **T1, factor ADR oficial** (`b25aed6`): tabla con fuente y fecha (20-F, F-6). El factor implícito queda solo como
  comprobación. BCS 4 (el implícito daba 4.154), UL 1 y TM 10.
- **T2, dividendo en la moneda y la clase del precio** (`c9b661d`): se calcula con los pagos del propio título de la
  serie de precios.
  - Identidad en los dos sentidos con magnitudes equivalentes: NVDA, subida verificada; PGR, el ordinario con la nota
    del extraordinario.
  - **Protección 1 retirada.**
  - Panel: BCS 2.71%, TSM 0.90%, NVO 4.86%, UL 3.44% (habría salido 251.70%).
- **T3, corte coherente** (`0c8d211`, `d984181`, `e6364b2`, `c0b0414`, `4c102ee`):
  - `as_of` por campo, y la regla `periodo_incoherente`;
  - Finnhub solo entra si casa con el corte (JNJ: P/E 30.1x, no 39.4x);
  - BPA TTM = suma de los BPA diluidos de los cuatro trimestres;
  - aviso de resultados publicados y aún no incorporados;
  - base temporal declarada en el Piotroski.
- **T4, cliente de EDGAR en `lib/`** (`104df65`..`08c97a1`):
  - caché, presupuesto de 3 s y degradación sin EDGAR;
  - respaldo de lo que Yahoo no da del mismo corte (JNJ vuelve a tener Altman; D&A de BCS);
  - regla B del factor (portada del 20-F);
  - D7: emisor sin estados en la SEC, con aviso, insignia y techo de confianza "baja".
- **T5, deuda coherente con el EBITDA** (`4f01557`, `4fca871`, `61a964c`, `4960463`):
  - la fila "Capital Lease Obligations" de Yahoo es el arrendamiento operativo de US GAAP y sale de la deuda;
  - el arrendamiento financiero entra si no está ya;
  - IFRS 16, tal cual;
  - MSFT 56.8 → 106.9; AMZN 209.9 → 132.4;
  - O, resuelto (la deuda de Yahoo era la correcta); DUK, financiero del 10-K con aviso de fecha;
  - bancos fuera de las ratios de apalancamiento de empresa;
  - cautiva de CAT (34.46 mil millones), declarada;
  - Altman X4 sin el arrendamiento operativo.
- **T6, beta y rango desde la serie** (`01324a3`, `c8ae863`):
  - beta propia (2 años semanales frente al S&P 500, Blume) o, con R² < 0.1, la del sector de Damodaran;
  - rango de 52 semanas de la serie;
  - **Protección 2 retirada.**
- **T7, mapa de la fase 2:** las 29 filas tienen destino.
  - Interanual en la base de los estados, rotulado "(último ejercicio)" (`f762e03`).
  - forwardPE declarado como consenso (`8f461cf`).
  - Factor de split del plan B (`20fc859`).
  - NFLX: comisión de ruptura de WBD verificada (`a2bb87a`).
  - Beneficio y patrimonio del accionista ordinario, con AT1 y preferentes separados; ROE y P/B del ordinario
    (`7b610a7`).
  - Cambio de perímetro declarado: UL, BAC, AMT, JNJ, DUK (`a435698`).
  - **Movidas:** BRK-B en base anual, a la fase 3 (definición de ingresos: Yahoo suma las ganancias de inversión);
    Yahoo 401 y Yahoo distinto en Render, a la fase 6.
- **T8, medida final.**
  - **F1: 1290/1411 (91.4%)** de los campos; ratios 193/216 (89.4%). Línea base de la 2a: 90.0%.
  - Dos arreglos de la herramienta, autorizados por el usuario: emparejamiento por el periodo que declara el
    pipeline (`db4db68`) y referencia del accionista ordinario (`a3b4c7a`). Sin ellos: 1276/1411 (90.4%).
  - **Objetivo del 95% no alcanzado.** De las 121 filas fuera:
    - 31 son definiciones que cierra la fase 3 por D2 (capex, ingresos y caja de bancos y aseguradoras);
    - 21 son el EBIT que construye Yahoo, ahora marcado "estimado por la fuente" (`4310fc8`);
    - 15 son el dividendo indicado frente al declarado (definición por diseño);
    - 14 son la deuda de la regla frente a `LongTermDebt` (definición por diseño);
    - el resto, fuente o periodo, caso por caso en el informe.
  - Golden aprobados y regenerados (`dcdda74`). Cambios de nivel solo por la beta (T6): BRK-B, JNJ, NVO, TM y NFLX.
  - Tiempo en frío: mediana ≈ 3.2 s (T0 ≈ 4.2 s).
- **Deploy y producción** (`/api/health` = `103c76f`, 2026-10-16, ~21:00 de Nueva York, concurrencia 3): 11 casos.
  - Dividendos correctos en los ADR; beta propia o del sector; corte coherente; aviso de resultados pendientes.
  - **Fallo de producción corregido en origen** (`103c76f`): Yahoo da la barra del día sin cierre y la serie la
    descartaba. XOM salía con el rango "sin dato"; ahora 111.18–179.16, "En máximos de 52 semanas".
  - **Gotcha de deploy:** `frontend/out` se compila con `npm run build` (Turbopack + sello del contrato) en el
    checkout principal. Con webpack, `build.sh` de Render rechaza el deploy (`fafee5d`).
- **Pendiente del usuario:** `SEC_EDGAR_USER_AGENT` en Render. Sin él, producción va sin EDGAR ("verificación oficial
  no disponible"): sin respaldo, sin deuda de la regla (MSFT y AMZN con la de la fuente), sin la marca del EBIT y sin
  el aviso D7. Con la variable puesta, hay que repetir la comprobación.
- **Para la fase 3** (bitácora, mapa):
  - definiciones de D2: capex, EBIT y EBIT bancario, ingresos de bancos y de BRK-B, caja de bancos y aseguradoras;
  - EDGAR como fuente principal campo a campo;
  - ROTE ajustado por AT1, con las filas anuales del ordinario ya en los datos;
  - uso de la deuda de la cautiva de CAT;
  - crecimiento sin el cambio de perímetro (UL);
  - crecimiento de los ADR en la moneda de los estados (UL: +0.5% en USD frente a −3.8% en EUR).

### 7.22 Fase 3 del plan de fiabilidad: método por tipo de negocio

*Operador F3, 16–17-oct-2026. Detalle: [`fiabilidad/F3_T1_PARADA1.md`](fiabilidad/F3_T1_PARADA1.md),
[`fiabilidad/F3_T2_PARADA2.md`](fiabilidad/F3_T2_PARADA2.md) y
[`fiabilidad/F3_T7_PARADA3.md`](fiabilidad/F3_T7_PARADA3.md); bitácora, registros #24–#31. Rama
`fiabilidad/f3-metodo`, **sin subir**. Desde el registro #29 el operador decide bajo la delegación del usuario. Todo
arreglo es de fondo; la fase no deja protecciones provisionales nuevas.*

- **T1/T1b, definiciones y capa de datos** (`3d52202`…`3966a43`): las definiciones de D2 que dejó la 2b.
  - Capex sin el equipo arrendado de la cautiva; EBIT reportado; EBIT de bancos "no aplica".
  - Ingresos netos totales en bancos; ingresos de BRK-B sin ganancias de inversión.
  - Caja con las inversiones a corto plazo.
  - EDGAR principal en esos campos.
  - EBITDA = EBIT + D&A.
  - Crecimiento en la moneda de los estados.
  - F1: 94.9% (93.5% sin las definiciones de la fase 3; 91.4% al cierre de la 2b).
- **T2, clasificador con la historia de EDGAR** (`dc62a83`…`9e76d50`, `0fe8ef0`).
  - Ciclicidad: 8+ ejercicios con episodios repetidos, que son caídas de ingresos ≥ 10% confirmadas por ≥ 2 pp de
    margen operativo, o desplomes del BPA que coinciden con una caída de ingresos.
  - Recortes de perímetro y roturas de estructura de capital.
  - GROWTH_PROFITABLE y subtipos de FINANCIAL.
  - Sensibilidad ±20% ("frontera").
  - 8 cambios de arquetipo. KO, que salía cíclica por la refranquicia, se queda MATURE con la condición de
    apalancamiento operativo.
- **T3, DCF** (`f8e5750`…`787317a`):
  - una sola estructura: 5 años constantes y convergencia lineal en los años 6–10;
  - FCF − SBC;
  - DCF inverso contra tasas base: lognormal de Mauboussin y Callahan (2021), por tamaño e industria, comparado con
    la historia propia;
  - opción 3 de §7.17;
  - contraste independiente Δ = 0.000000 pp.
- **T4, financieras** (`e2b4c3b`, `afae76a`, `1c3dbad`, `6912ded`, `9155044`):
  - ROTE ordinario (sin AT1);
  - ROTE/ROE implícito = P/TBV × (Ke − g) + g, con bandas y sensibilidad;
  - ROE medio en aseguradoras;
  - P/E aplicable a bancos y aseguradoras (registro #14);
  - subtipo visible;
  - margen de intereses mostrado aparte.
- **T5, crecimiento** (`c12ad29`, `381c863`, `e353392`, `57e8d46`, `afdd1d8`, `26aa866`):
  - retorno total en MATURE con dividendo ≥ 4%;
  - perímetro homogéneo (UL);
  - ciclo medio de pico a pico (la cota −5%/+10% queda solo con historia corta);
  - base ≤ 0, no significativo (AMZN);
  - mezcla declarada del interanual y del CAGR a 3 años.
- **T6, lecturas por modelo de negocio** (`ceac134`, `4ae7705`, `51201e2`, `d2a6adc`, `784b7eb`):
  - circulante negativo estructural, Altman referencial y avisos del Piotroski;
  - cautiva fuera de la deuda industrial (CAT 34.5 mil millones);
  - DuPont, margen FCF con tendencia, regla de 40 y SBC como coste;
  - cobertura de intereses con EBITDA, tendencia, intereses pagados y FFO en REIT;
  - PEG a 3 años.
- **T7, verificación** (`3f4be83`, `c8ab2fe`, `52403a2`, `8a58618`, `2e4d6ad`).
  - Método intrínseco con FCF − SBC ≤ 0 (flujo de mantenimiento) y en utilities (P/B frente al ROE regulado).
  - Panel: un solo método evaluable 18 → 2 de 37. Precio muy exigente/exigente/razonable/atractivo pasa de
    3/14/15/4 a 10/7/16/3. Confianza alta/media/baja pasa de 5/28/3 a 10/23/3.
  - Revisión externa: NOW destapó el CAGR que contaba puntos como años, arreglado; DE, cautiva sin desglose,
    declarada; SAN, sin hallazgos.
  - Web comprobada en replay. Tiempo del panel 7.7 → 7.9 s.
- **Mapa:** 25 filas cerradas. 2 movidas a la fase 6: BRK-B en base anual y su P/E (TTM), que necesitan el corte LTM
  con los 10-Q de EDGAR. Compromisos fuera de balance, descartados: XBRL no trae el importe. La inflación de TXRH,
  descartada: no hay fuente.
- **Pendiente del usuario:**
  - regenerar los golden (`diff_golden.py --regenerate --yes` en `panel` y `local`, y `contract_forced.py --write`);
    el clasificador de permisos de la sesión lo bloqueó, y la suite falla solo en esas muestras;
  - `SEC_EDGAR_USER_AGENT` en Render;
  - "ok, pushea";
  - deploy y comprobación en producción;
  - `npm run build` del frontend en el checkout principal.
- **Para la fase 4:**
  - referencias por industria y geografía (TXRH, BCS);
  - bandas paralelas;
  - techo de calidad;
  - confianza "alta" con convergencia media;
  - efecto frontera (NVO).

### 7.23 Fase 4 del plan de fiabilidad: escalas y confianza honestas

*Operador, 17-oct-2026, bajo la delegación del usuario (bitácora #29 y #32). Detalle en
[`fiabilidad/F4_PARADA.md`](fiabilidad/F4_PARADA.md). Rama `fiabilidad/f4-escalas`, que sale de
`fiabilidad/f3-metodo`, sin subir.*

- **§4.1 saturación** (`1f12e33`, `92a279e`):
  - la calidad por encima de 80 exige persistencia: 80 + (calidad − 80) × persistencia ponderada de las categorías
    del tramo alto (lib/persistence.py);
  - anclas en 5 ejercicios: margen ≥ 75% del actual, ingresos al alza, flujo operativo ≥ beneficio y FCF > 0;
  - historia de EDGAR completada con los estados, por ejercicio canónico;
  - panel: > 95 pasa de 4 a 2 (TSM 99, V 96); ningún 100;
  - NFLX 100 → 93, PLTR 99 → 95, MU 95 → 90.
- **§4.2 confianza** (`122cbb4`, `e5baf6e`):
  - la fuente cuenta solo las incidencias del dato usado;
  - "alta" exige que ninguna dimensión sea baja;
  - el resumen cita el motivo real del techo;
  - panel: alta 10 → 12.
- **Efecto frontera** (`a0aa922`): aviso a ≤ 2 puntos de un umbral de nivel.
- **§4.3 pre-mortem** (`bc4fa89`, `f99859a`):
  - lib/premortem.py, hasta 3 condiciones con su cifra: crecimiento exigido o ROTE/ROE implícito en el sentido del
    nivel, margen frente a su historia y deuda;
  - en Valoración (web y PDF), con predicado del guardián.
- **Bandas paralelas** (`ea2926b`, `71b5184`): alertas, lecturas, gráficos y tooltips del DCF, la cobertura, la deuda
  neta/EBITDA y la beta con una sola fuente de umbrales.
- **Revisión de código de la fase 3:** 7 arreglos (`6578a63`…`8c53940`); el hallazgo 3 no se reproduce.
- **Revisión externa:** SAN destapó la ventana anclada en una serie cortada, arreglado; DE, cautiva en el pre-mortem,
  declarada.
- **En espera del usuario:**
  - permiso para descargar los datos sectoriales de Damodaran: referencias por industria y geografía, y medianas con
    fuente y fecha;
  - golden;
  - `SEC_EDGAR_USER_AGENT`;
  - "ok, pushea".
- **Movido a la fase 7:** bandas de REIT y utilities sin muestra.

### 7.24 Fase 5 del plan de fiabilidad: capa técnica y conductual

*Operador, 17-oct-2026, bajo la delegación del usuario (bitácora #33). Detalle en
[`fiabilidad/F5_PARADA.md`](fiabilidad/F5_PARADA.md). Rama `fiabilidad/f5-contexto`, sin subir. D5: solo contexto.*

- **Datos** (`9363163`): ETF del sector como tercera serie, en caché 6 h por proceso y por sector; fixtures derivados
  sin red de F5prep.
- **Contexto** (`309ed32`):
  - lib/market_context.py con las señales de F5prep sobre el cierre ajustado de 2 años;
  - lectura conductual solo cuando los datos la sostienen: anclaje 52 semanas, sobrerreacción sin deterioro y
    extrapolación frente a tasas base;
  - titulares de 7 días de Finnhub, sin interpretar;
  - pestaña web y sección 07 del PDF, en tono neutro;
  - guardián con predicados `market_signal` y `behavioral`;
  - D5 con test estructural: se calcula después del veredicto y nada del motor lo lee.
- **Verificado:**
  - contraste independiente a 1e-9 (7 tickers);
  - 0 cambios de nivel;
  - revisión externa (NOW, DE, SAN) y web.
- **Abierto:** PEAD (sin sorpresa del BPA con fuente); latencia en Render (con el deploy).

### 7.25 Fase 6 del plan de fiabilidad: infraestructura

*Operador, 17-oct-2026, bajo la delegación del usuario (bitácora #34). Detalle en
[`fiabilidad/F6_PARADA.md`](fiabilidad/F6_PARADA.md). Rama `fiabilidad/f6-infra`, sin subir. D6: sin plan de pago.*

- **Cola en serie quitada** (`6fb46c3`): análisis, PDF y búsqueda en hilos con un semáforo de 4. 12 análisis en frío a la vez pasan de 26 s a 7.5 s en local, y `/api/health` deja de bloquearse.
- **Estado compartido seguro entre hilos** (revisión, `2006379`, `dd0ca0a`, `ead7808`):
  - caché con lock;
  - presupuesto de EDGAR que no paga la cola, con tope;
  - sesión y clase sin carreras.
- **Caché de los estados de 6 h** (`1b8f5ca`) y trimestrales en paralelo (`fafdf3b`).
- **Procedencia por fuente en el anexo técnico** (`b586299`, `a83fe4e`, `0d86c00`).
- **Corte de doce meses de EDGAR sin trimestres de Yahoo** (`9b7bbc4`): BRK-B al 30-jun-2026, con el balance de Yahoo de esa fecha y el BPA aproximado declarado. Solo si no pierde campos (UL no).
- **Abierto:**
  - arranque en frío de Render (D6);
  - medida en Render (con el deploy);
  - beneficio operativo de aseguradoras y conglomerados (BRK-B: ganancias no realizadas en el beneficio GAAP).

### 7.26 Fase 7 del plan de fiabilidad: revisión de parámetros y calibración histórica

*Operador, 17-oct-2026, bajo la delegación del usuario (bitácora #35). Detalle en
[`fiabilidad/F7_CALIBRACION.md`](fiabilidad/F7_CALIBRACION.md). Rama `fiabilidad/f7-calibracion`, sin subir.*

- **Parámetros con fuente y fecha legibles por programa** (`config/review.toml`, `tests/revision_parametros.py`). Cumple lo que pide §7.13.
- **Estudio de calibración:**
  - el motor real sobre 968 fechas pasadas, con los datos de entonces;
  - hipótesis fijadas antes de correrlo y muestras de entrenamiento y prueba por periodo y por empresa;
  - versión 2, tras una revisión que encontró una fuga de splits futuros en los precios;
  - solo H2 (calidad → menor caída) sale validada con la regla, y no es robusta a empresa × año ni al sector;
  - el precio no anticipa la rentabilidad de forma demostrable (H3a y H3b, no concluyentes);
  - la app no promete rentabilidades.
- **Bandas de REIT y utilities** contrastadas con 51 empresas:
  - bien centradas: utilities y P/FFO;
  - en el límite: la deuda de los REIT, que sigue PROVISIONAL;
  - satura: FFO/patrimonio de los REIT (decisión del usuario).
- **Abierto:**
  - decisiones del usuario (F7_CALIBRACION §6);
  - repetir el estudio con más empresas y con prima de riesgo point-in-time.
- **Decisiones de método posteriores (bitácora #36):**
  - REIT: FFO/activos totales sustituye a FFO/patrimonio (decisión del usuario);
  - aseguradoras y conglomerados: P/E operativo, sin las ganancias de su cartera (ASC 321), con la rentabilidad sobre el reportado (decisión del operador). BRK-B: 13.2 → 26.8x.


### 7.27 Referencias por industria y región (Damodaran) y estudio v3

*Operador, 17-oct-2026, con el permiso del usuario para descargar los datos de Damodaran. Detalle en
[`fiabilidad/GOLDEN_DIFF_DAMODARAN.md`](fiabilidad/GOLDEN_DIFF_DAMODARAN.md) y F7_CALIBRACION §10.*

- **Datos:** 31 Excel de Damodaran de enero de 2026 (P/E, P/B, EV/EBITDA, ROE, márgenes y deuda; EE. UU., Europa,
  Japón, emergentes y global), `indname.xls` (48 157 empresas con su industria, país y grupo regional) y
  `histimpl.xls`. Están en `~/Downloads/finanzer_damodaran/raw`, fuera del repositorio.
  `tools/damodaran_import.py` genera `config/industries.toml` y `config/damodaran_firms.tsv.gz`.
- **Referencia:**
  - la industria de la empresa: su clasificación en Damodaran por el símbolo o, para un ADR, por el nombre legal; si
    no, el mapa de la industria de Yahoo;
  - la región: la de la empresa en Damodaran o la de su país;
  - si la fila no es representativa (menos de 10 empresas, o agregado ≥ 1.5 × la media simple), la industria global;
  - solo se muestra lo que tiene fuente.
- **País del emisor:** la dirección comercial de EDGAR (Yahoo no lo da en Render) o el sufijo del ticker.
- **Arreglo de paso** (`e2529d6`): el guion interno del nombre de industria (KO: beta del sector 0.80 → 0.64).
- **Panel:**
  - 9 cambios de nivel de precio (BCS y HSBC frente a la banca europea, TM frente a la automoción japonesa…), 0 de
    calidad y 7 de confianza;
  - golden y muestras forzadas sin regenerar: esperan la aprobación del usuario.
- **Estudio v3:** H3a pasa la regla prerregistrada, pero no es robusta. Ninguna escala cambia.
