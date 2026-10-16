# Línea base y red de regresión del motor (etapa 2)

> ⚠️ **Los golden describen el comportamiento ACTUAL del motor, con sus bugs; no el correcto.**
> Que un test de regresión falle significa "el comportamiento cambió", no "algo se rompió".
> Revisa el cambio con `diff_golden.py` y decide. Los bugs conocidos están en
> `test_known_bugs.py` (ver abajo).

## Juegos de datos (entornos)

Hay dos juegos, cada uno con sus fixtures y sus golden: **`local`** (captura en desarrollo, ruta quoteSummary; los 6
tickers de los tests de humo y de bugs conocidos) y **`panel`** (36 tickers capturados con Render simulado: la ruta de
producción, plan B + Finnhub; ver más abajo). La regresión y el determinismo corren contra los dos.
`diff_golden.py` y `capture_fixtures.py` aceptan `--env`.

**Retirados en la fase 1 del plan de fiabilidad (decisión D8):** el juego `prod` (capturado en Render el 11-oct con
`/api/_capture`; sin estados trimestrales, así que su replay salía en base anual mientras producción calcula en TTM)
y el juego `muestra` (etapa 11b; capturado por quoteSummary y sin Finnhub). Sus tests se reescribieron contra el
panel (`test_panel_cases.py` y los atados a los 6 tickers vía `conftest.BOUND_ENVS = ["local", "panel"]`). Quedan
en el historial de git, igual que `import_prod_capture.py`, `supplement_prod_search.py` y el modo
`diff_golden.py --local-vs-prod`.

## Correr los tests (en el entorno espejo de prod, `.venv313`)

La suite se corre en **`finanzer_next/.venv313`**: Python 3.13.4 con las mismas versiones que prod. Ahí ya se verificó
que todos los golden (local y panel) se mantienen.

```bash
cd finanzer_next/backend
../.venv313/bin/python -m pytest tests      # ~20 s, sin red
```

Crear el venv (una vez; uv y Python 3.13.4 se instalan en tu usuario, sin admin):

```bash
python3 -m pip install --user uv
~/Library/Python/3.9/bin/uv python install 3.13.4
cd finanzer_next && ~/Library/Python/3.9/bin/uv venv --python 3.13.4 .venv313
~/Library/Python/3.9/bin/uv pip install --python .venv313/bin/python -r backend/tests/requirements-venv313.lock
```

`requirements-venv313.lock` congela **todas** las versiones con las que pasó la suite. Python, yfinance, pandas y
curl_cffi están confirmadas por la captura de prod; numpy, pydantic, reportlab y requests son **provisionales**
(última versión al 11-oct-2026) hasta contrastarlas con el log de build de Render. Ojo: reportlab resolvió a
**5.0.1**, versión mayor nueva. La suite también pasa con el Python 3.9 del sistema
(`python3 -m pytest tests`), pero el entorno de referencia es `.venv313`.

Dependencias de test: `tests/requirements-test.txt` (pytest, pypdf, además de las de producción).
No se tocó `requirements.txt`, ni Render las instala.

| Archivo | Qué cubre |
|---|---|
| `test_regression.py` | Para los 6 tickers, `_compute_analysis` desde los fixtures == `golden/<env>/<T>.json`, y el texto del PDF == `golden/<env>/<T>.pdf.txt`. Además: existen los puntos de enganche, los metadatos y ningún acceso queda sin fixture. |
| `test_determinism.py` | Dos corridas en el mismo proceso, y dos procesos con `PYTHONHASHSEED` distinto, dan salidas idénticas **byte a byte** (análisis sin redondear y bytes del PDF). |
| `test_smoke.py` | Piezas aisladas con valores calculados a mano: `piotroski_f_score`, `altman_z_score`, `dcf_multi_stage`, `dcf_sensitivity_analysis`, `calculate_score_v2`. |
| `test_cost_of_capital.py` | Etapa 8: WACC real (rating sintético, tasa efectiva, Rf con fallback), recorte del grid, g >= WACC, crecimiento bajo el terminal, fiabilidad del DCF, DCF en Valoración y confianza del veredicto. |
| `test_known_bugs.py` | Un test por bug verificado en `docs/RECON.md`. Afirma el comportamiento **correcto**; los de la tabla de abajo ya están corregidos y pasan. Un bug nuevo entra marcado `xfail(strict=True, raises=AssertionError)`. |

### Tests de bug conocido (antes xfail; hoy todos corregidos)

Hoy **no queda ningún test xfail**: los bugs verificados en RECON se corrigieron y sus tests pasan como tests
normales (verificado el 2026-10-14: `597 passed, 1 skipped`, 0 xfail). Se conservan como regresión:

| Test | Bug (RECON) | Corregido en |
|---|---|---|
| `test_bug_fcf_exceeds_ocf_nflx` | C5: FCF apalancado (25.4B) > OCF (12.0B) | etapa 3 (bug d): FCF = OCF − capex |
| `test_bug_shares_issued_vs_ordinary_nflx` | C3: `Share Issued` en vez de `Ordinary Shares Number` | etapa 3 (bug c) |
| `test_bug_wacc_is_only_cost_of_equity_nflx` | C4: el WACC era solo Ke | etapa 8 (WACC real) |
| `test_bug_dcf_vs_grid_growth_snow` | §6.5: DCF y grid con crecimientos distintos | etapas 4 y 8 |
| `test_bug_base_case_box_never_drawn_nflx` | §1.4: el recuadro del caso base no se dibujaba | etapa 8 |
| `test_bug_jpm_revenue_growth_artifact` | C6: crecimiento de JPM 30.4% frente a ~7.3% | etapa 3 (bug e) |
| `test_bug_prod_sector_unknown_outside_known_list_o` | Sector "Unknown" fuera de `KNOWN_SECTORS` en prod | etapa 3 (bug a) |
| `test_bug_incoherent_revenue_growth_is_informative_only` | G3: el crecimiento incoherente solo avisa | etapa 3 |

**Para un bug nuevo** se mantiene la convención: test que afirma el comportamiento correcto, marcado
`xfail(strict=True, raises=AssertionError)`. Al arreglarlo pasará (XPASS) y, por `xfail_strict = true`, la suite
fallará a propósito: quita la marca y regenera los golden de forma explícita.
`raises=AssertionError` garantiza que un test roto por otra causa (KeyError, etc.) **no** se cuente como bug conocido.

## Configuración única (etapa 4)

Todos los umbrales del motor, las alertas y el PDF viven en `backend/config/`:
`thresholds.toml` (bandas del score, alertas y lecturas del PDF), `sectors.toml` (medianas y umbrales por sector,
**provisionales**), `valuation.toml` (CAPM, WACC, DCF, grid, Graham, Altman, Piotroski), `validation.toml` (capa de
validación) y `data.toml` (cachés, timeouts, reintentos). `lib/settings.py` los carga con `tomllib` y los valida
contra `config/schema.toml` al importar: una clave que falta o sobra, o un tipo distinto (`int` frente a `float`),
lanza `SettingsError` con todos los problemas.

- `test_settings.py`: el cargador falla con config inválida.
- `test_config_literals.py`: las funciones migradas no contienen literales numéricos fuera de la lista de
  excepciones justificadas (`EXCEPTIONS`). Si añades un umbral nuevo, va al TOML y a `schema.toml`.
- Donde hoy conviven dos valores para un mismo concepto (p. ej. niveles del score 80/65/50/35 en el motor y
  80/60/40/20 en el PDF) hay dos claves: la unificación se decide aparte.

## Validación de entrada y trazabilidad (etapa 3)

`lib/validate.py` corre en `yf_adapter.get_ticker_info` después de la ingesta (Yahoo o plan B, último-bueno-conocido
y Finnhub) y antes del motor. Umbrales en `validate.THRESHOLDS`. Cada intervención queda en
`analysis["data_validation"]` (`field`, `rule`, `action` = recalculado | sin_dato | aviso, `old`, `new`, `reason`) y la
procedencia de cada campo en `analysis["data_provenance"]` (`path`, `fields`, `errors`). Los tests de cada regla, con
casos positivos y negativos sintéticos, están en `test_validation.py`. La regla del crecimiento está documentada en
RECON §7.6.

## Juego `panel` y `panel_run` (fase 0 del plan de fiabilidad)

36 tickers en 11 grupos (`fixture_backend.PANEL_GROUPS`), capturados con `--render-sim` tras el cierre: 31 el
14-oct-2026 (SPY incluido), BCS el 15-oct (fase 1) y HSBC, SHEL, UL y TM el 15-oct (fase 2a, grupo
"Extranjeros (fase 2)"). Entran en la regresión y el determinismo (`conftest.REG_ENVS`), **no** en `conftest.ENVS`:
los tests atados a
los 6 tickers no recorren el panel entero (indexan sus 6 tickers vía `BOUND_ENVS`). Los invariantes genéricos viven en `invariants.py` y
`test_panel_invariants.py` los corre sobre los 36 (los fallos conocidos, como xfail estricto en
`PANEL_KNOWN_FAILURES`); `test_invariants_detectan.py` prueba que cada uno detecta su violación.

```bash
../.venv313/bin/python tests/panel_run.py --mode replay --out ~/Downloads/panel_replay
../.venv313/bin/python tests/panel_run.py --mode live --base-url https://finanzer.app --out ~/Downloads/panel_live
../.venv313/bin/python tests/panel_run.py --mode replay --out <nueva> --compare <anterior>
python3 tests/diff_golden.py --env panel [TICKERS]
```

Línea base: `docs/fiabilidad/F0_LINEA_BASE.md`.

## Revisar el efecto de un cambio: `diff_golden.py`

```bash
python3 tests/diff_golden.py                 # todos los tickers
python3 tests/diff_golden.py NFLX SNOW       # algunos
python3 tests/diff_golden.py --full          # sin recortar
```

Por ticker muestra `campo: anterior → nuevo`, agrupado en score, piotroski, altman, dcf, grid, alertas,
métricas y otros, más el diff del texto del PDF. Sale con código 1 si hay diferencias.

### Regenerar los golden (explícito, nunca automático)

```bash
python3 tests/diff_golden.py --regenerate            # muestra el diff y pide escribir SI
python3 tests/diff_golden.py --regenerate --yes NFLX
```

Los tests **nunca** escriben golden. Regenera solo cuando hayas revisado y aceptado el cambio,
y commitea el golden en el mismo commit que el cambio que lo provocó.

## Fixtures: inputs crudos congelados

`fixtures/<env>/<TICKER>/` congela lo que consume `_compute_analysis`. La línea base congela las **entradas**
y no solo las salidas: el veredicto depende del snapshot de datos (RECON C5).

| Archivo | Contenido |
|---|---|
| `yahoo_http.json` | Respuesta cruda de `v10/finance/quoteSummary` (sin `crumb`) |
| `yfinance.json` | `income_stmt`, `balance_sheet` y `cashflow` anuales de yfinance (los usa `_enrich_prior_year_data`); `fast_info`/`info` si se activó `_fallback_yfinance` |
| `finnhub.json` | Respuestas de Finnhub `/stock/metric` (sin `token`); vacío si no participó |
| `metadata.json` | Fecha y hora de captura (UTC y local), entorno, versiones (yfinance, curl_cffi, pandas, Python), commit, si Finnhub participó, si Yahoo vino degradado o se usó el fallback |

Captura actual: **11-oct-2026, local, sin `FINNHUB_API_KEY` (Finnhub no participó), Yahoo sin degradar,
sin fallback**. Por ticker hay 1 llamada a quoteSummary y 3 estados anuales. En producción (Render)
Yahoo puede venir degradado y Finnhub participa, así que **estos golden no garantizan el comportamiento en prod**.

### Serie diaria de precios (fase 2b): `fixtures/history/`

Desde la 2b el análisis descarga una serie diaria de 2 años del título y del S&P 500 (`lib/price_history.py`:
dividendos del propio título, rango de 52 semanas y beta). Los fixtures del panel y del juego local son anteriores y
no la traen: el replay la sirve del juego aparte `fixtures/history/` (`history_fixtures.py`), **cortada en la fecha
de captura del ticker analizado**, así el análisis ve lo que habría descargado ese día (precios sin ajustar y
eventos pasados no cambian). Un fixture capturado desde la 2b la lleva dentro (`yfinance.json`: `price_history` y
`market_history`) y manda sobre el juego aparte.

```bash
../.venv313/bin/python tests/capture_history.py          # panel + local + ^GSPC y SPY (fuera de 15:55–16:45 NY)
```

### SEC EDGAR y calendario de resultados (fase 2b): `fixtures/f2b/`

El análisis consulta EDGAR (`lib/sec_edgar.py`): la lista de emisores y de filings (aviso de resultados publicados,
D7), la portada del 20-F de los ADR fuera de `config/adr.toml` (factor, regla B) y los hechos XBRL para el respaldo
del mismo corte (`lib/edgar_backup.py`): `companyfacts` reducido a los conceptos que se usan y la instancia de cada
filing que companyfacts aún no traía el día de la captura (XBRL mínimo con los mismos conceptos). El replay lo sirve
de `fixtures/f2b/` (`f2b_fixtures.py`) **cortado en la fecha de captura del ticker analizado** (filings y hechos con
`filed` posterior no existían ese día). Un `.404` junto a un companyfacts es la respuesta grabada de la SEC (SPY).
`MC.PA` (LVMH, grupo "Sin CIK" del panel) no está en la lista de emisores: es el caso D7.

```bash
SEC_EDGAR_USER_AGENT="$(security find-generic-password -s finanzer-sec-ua -w)" \
FINNHUB_API_KEY="$(security find-generic-password -s finanzer-finnhub -w)" \
../.venv313/bin/python tests/capture_f2b_sources.py           # listas de filings y calendario
SEC_EDGAR_USER_AGENT="$(security find-generic-password -s finanzer-sec-ua -w)" \
../.venv313/bin/python tests/capture_f2b_sources.py --facts   # solo hechos (companyfacts e instancias pendientes)
```

### Recapturar (con red, explícito)

```bash
python3 tests/capture_fixtures.py                  # crea los que falten
python3 tests/capture_fixtures.py NFLX --force     # recaptura uno
```

Tras grabar, el script reproduce el análisis desde los fixtures y exige que coincida **byte a byte**
con la corrida en vivo. Si el pipeline consumió algo no grabado, falla y no sobrescribe nada.
Para incluir Finnhub, exporta `FINNHUB_API_KEY` en tu terminal antes de capturar. La clave nunca se
escribe: `token`, `crumb` y `apikey` se eliminan antes de guardar. Antes de commitear, verifícalo:
`grep -rniE "ghp_|token=|apikey" tests/fixtures tests/golden`.

Recapturar cambia los inputs: después hay que regenerar los golden y revisar el diff.

### Captura con Render simulado (fase 0 del plan de fiabilidad)

`--render-sim` reproduce en local el camino de datos de producción (RECON §7.1, §7.5) con dos ganchos de
`fixture_backend.render_sim()`: **S1** `quoteSummary` responde 401 "Invalid Crumb" y **S2** `yfinance.Ticker.info`
devuelve `{}`. Así el pipeline va por el plan B (`plan_b_yfinance`) + Finnhub, como en Render. Finnhub se limita a
una petición cada 1.1 s (límite gratuito: 60/min). Los metadatos registran `render_simulation` (S1, S2),
`finnhub.participated` y `risk_free.frozen` (la Rf de config: el replay no depende del día; prod en vivo usa ^TNX).

```bash
python3 tests/capture_fixtures.py --env panel --render-sim               # los 31 del panel (exige FINNHUB_API_KEY)
python3 tests/capture_fixtures.py --render-sim --dir /ruta JPM NFLX      # a otra carpeta (validaciones)
```

Validado el 2026-10-14 contra `finanzer.app` del mismo día (bitácora de fiabilidad, registro #2 y siguientes).

## Cómo funciona la capa de inyección (`fixture_backend.py`)

**No cambia ni una línea de producción.** Engancha por monkeypatch, con save/restore, en estos puntos:

| Enganche | Qué intercepta |
|---|---|
| `yf_adapter._ensure_session` | En replay instala una sesión falsa que sirve `quoteSummary` desde `yahoo_http.json` (y un crumb ficticio); en record envuelve la sesión `curl_cffi` real. `_do_fetch` usa la sesión global, así que no se toca. |
| `yfinance.Ticker` | `yf_adapter` hace `import yfinance as yf` dentro de `_enrich_prior_year_data`/`_fallback_yfinance`, así que reemplazar el atributo del módulo basta. En replay devuelve DataFrames reconstruidos (columnas como fechas, NaN preservado). |
| `finnhub_fallback._get` | Sirve o graba `/stock/metric`. En replay, Finnhub solo se "activa" (con una clave ficticia) si el fixture lo grabó. |
| Red | En replay, `socket.connect` y `create_connection` lanzan error: lo no grabado falla en vez de salir a internet. |
| Estado | `reset_state()` vacía `yf_adapter._cache`/`_best_cache`, `data_fetcher._data_cache` y `finnhub_fallback._cache` antes de cada corrida; `time.sleep` es no-op en replay. |
| PDF | `build_pdf_bytes` usa reportlab con `rl_config.invariant = 1` (sin fecha ni ID variables) y congela `pdf_report.datetime.now` a la fecha de captura. |

Si en producción se renombra uno de estos puntos, `test_seams_exist` falla en vez de que la capa
deje de interceptar en silencio.

## No determinismo encontrado y cómo se neutralizó

- `pdf_report._fecha_es()` imprime `datetime.now()` → se congela a la fecha de captura.
- reportlab incrusta fecha de creación e ID aleatorio → `invariant = 1`.
- Cachés en memoria entre corridas (incluido el "último bueno conocido" de 24 h, que mezclaría snapshots) → `reset_state()`.
- No se encontró dependencia del orden de hash: mismas huellas con `PYTHONHASHSEED` 0 y 4242.
