# Línea base y red de regresión del motor (etapa 2)

> ⚠️ **Los golden describen el comportamiento ACTUAL del motor, con sus bugs; no el correcto.**
> Que un test de regresión falle significa "el comportamiento cambió", no "algo se rompió".
> Revisa el cambio con `diff_golden.py` y decide. Los bugs conocidos están en
> `test_known_bugs.py` (ver abajo).

## Correr los tests

```bash
cd finanzer_next/backend
python3 -m pytest tests          # ~5 s, sin red
```

Dependencias de test: `tests/requirements-test.txt` (pytest, pypdf, además de las de producción).
No se tocó `requirements.txt`, ni Render las instala.

| Archivo | Qué cubre |
|---|---|
| `test_regression.py` | Para los 6 tickers, `_compute_analysis` desde los fixtures == `golden/<T>.json`, y el texto del PDF == `golden/<T>.pdf.txt`. Además: existen los puntos de enganche, los metadatos y ningún acceso queda sin fixture. |
| `test_determinism.py` | Dos corridas en el mismo proceso, y dos procesos con `PYTHONHASHSEED` distinto, dan salidas idénticas **byte a byte** (análisis sin redondear y bytes del PDF). |
| `test_smoke.py` | Piezas aisladas con valores calculados a mano: `piotroski_f_score`, `altman_z_score`, `calculate_wacc`, `dcf_multi_stage`, `dcf_sensitivity_analysis`, `calculate_score_v2`. |
| `test_known_bugs.py` | Un test por bug verificado en `docs/RECON.md`, marcado `xfail(strict=True, raises=AssertionError)`. Afirma el comportamiento **correcto**, así que hoy falla. |

### Tests de bug conocido (xfail)

| Test | Bug (RECON) |
|---|---|
| `test_bug_fcf_exceeds_ocf_nflx` | C5: el FCF viene de `financialData.freeCashflow` (apalancado): 25.4B > OCF 12.0B |
| `test_bug_shares_issued_vs_ordinary_nflx` | C3: se usa `Share Issued` en vez de `Ordinary Shares Number` |
| `test_bug_wacc_is_only_cost_of_equity_nflx` | C4: el WACC es solo Ke (Rf + β·MRP) |
| `test_bug_dcf_vs_grid_growth_snow` | §6.5: el DCF ($142.6) y el caso base del grid ($318.9) usan crecimientos distintos |
| `test_bug_base_case_box_never_drawn_nflx` | §1.4: el recuadro del escenario base nunca se dibuja en el PDF |
| `test_bug_jpm_revenue_growth_artifact` | C6: crecimiento de ingresos de JPM 30.4% frente a ~7.3% en los estados |

**Cuando arregles uno**, su test pasará (XPASS) y, por `xfail_strict = true`, **la suite fallará a propósito**.
Es la señal de que quedó corregido: quita su `@pytest.mark.xfail`. El arreglo también cambiará salidas,
así que revisa `diff_golden.py` y regenera los golden de forma explícita.
`raises=AssertionError` garantiza que un test roto por otra causa (KeyError, etc.) **no** se cuente como bug conocido.

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

`fixtures/<TICKER>/` congela lo que consume `_compute_analysis`. La línea base congela las **entradas**
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

### Recapturar (con red, explícito)

```bash
python3 tests/capture_fixtures.py                  # crea los que falten
python3 tests/capture_fixtures.py NFLX --force     # recaptura uno
```

Tras grabar, el script reproduce el análisis desde los fixtures y exige que coincida **byte a byte**
con la corrida en vivo. Si el pipeline consumió algo no grabado, falla y no sobrescribe nada.
Para incluir Finnhub, exporta `FINNHUB_API_KEY` en tu terminal antes de capturar. La clave nunca se
escribe: `token`, `crumb` y `apikey` se eliminan antes de guardar. Antes de commitear, verifícalo:
`grep -rniE "ghp_|token=|apikey" tests/fixtures`.

Recapturar cambia los inputs: después hay que regenerar los golden y revisar el diff.

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
