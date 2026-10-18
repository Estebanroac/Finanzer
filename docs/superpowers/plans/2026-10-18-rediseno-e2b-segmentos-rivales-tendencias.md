# Rediseño · Etapa E2b: segmentos, rivales y tendencias — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Añadir los tres datos de la spec §4 que necesitan fuentes o cálculos nuevos —ingresos por segmento (XBRL con dimensiones), rivales analizados con el motor completo y tendencias diarias de la portada— como endpoints `/api/v2/…` del backend, probados sin red y sin tocar el análisis existente.

**Architecture:** Tres módulos nuevos e independientes en `backend/lib/` (`segments.py`, `peers.py`, `trending.py`) más una pieza compartida (`universe.py` sobre `config/universe.tsv`, generado por una herramienta). Cada uno se expone en su endpoint perezoso (se calcula cuando alguien lo pide, en segundo plano, con caché y estado progresivo), **fuera** del camino de `/api/analysis` (no gasta su presupuesto ni cambia su golden). Sin UI en esta etapa: el cableado en `/v2` es de E3 (profundidad) y E4 (portada).

**Tech Stack:** Python 3.13.4 (`.venv313`), FastAPI, `xml.etree.ElementTree.iterparse`, pandas, yfinance (descarga por lotes), pytest; TypeScript solo para los tipos en `api.ts`.

**Especificación:** `docs/superpowers/specs/2026-10-17-rediseno-experiencia-design.md` §4 (datos 3, 7 y 10). **Decisiones del usuario y del PM (2026-10-17):**
- **Rivales con el análisis completo del motor** para cada rival (literal del usuario al elegir: "Análisis completo (Recomendado)"): las cifras coinciden con las del resto de la página. Se aceptan ~1 min la primera vez en Render; se rellenan uno a uno con estado progresivo y quedan en caché.
- **Candidatos por la industria de Damodaran** (la misma clasificación que la referencia del sector, `industry_bench.firm`), no por SIC: es la que ya usa el motor y trae 82 000 empresas sin red. Desviación de la spec (que decía SIC) decidida por el PM; anótala.
- **Universo de la portada y de los rivales preferentes:** S&P 500 + ADR principales (spec §4.10), en un archivo versionado con su fecha.

## Global Constraints

- **El análisis no cambia:** `/api/analysis` y el PDF quedan idénticos; el golden **no** cambia en E2b (ni una línea). Si cambia, es un bug.
- **Nunca bloquear:** todo lo nuevo corre en hilos propios con colas acotadas; los endpoints responden enseguida con el estado (`calculando`, `listo`, `sin_dato` + motivo) y el cliente vuelve a preguntar.
- **Render gratuito (512 MB):** un único hilo para los rivales (un análisis de rival a la vez, detrás de los análisis de usuarios: usa el mismo `_ANALYSIS_SLOTS`), cachés con tamaño máximo, instancias XBRL leídas en flujo (iterparse) sin guardarlas enteras.
- **Límites:** SEC ≤ 10 peticiones/s con User-Agent (usa el `Budget` y el ritmo de `sec_edgar`); Finnhub ≤ 60/min; Yahoo por lotes.
- **Secretos:** `finanzer-finnhub` y `finanzer-sec-ua` del Llavero, solo en el entorno del comando que captura; nunca en archivos, fixtures, logs ni el chat.
- **Config, no literales:** tamaños, TTL, número de rivales, tolerancias, en `config/*.toml` con comentario.
- **Sin push, sin merge a `main`, sin deploy.** Las aprobaciones de esta etapa las da el PM por delegación del usuario.

## File Structure

```
backend/
  config/universe.tsv            NUEVO (generado)  símbolo, nombre, origen (sp500|adr), sector GICS, industria Damodaran, fecha
  config/market.toml             +[universe] +[segments] +[peers] +[trending]
  tools/build_universe.py        NUEVO  genera universe.tsv (S&P 500 de la tabla pública + ADR de la config + industria Damodaran)
  lib/universe.py                NUEVO  carga y consulta del universo
  lib/segments.py                NUEVO  ingresos por segmento desde la instancia XBRL del último 10-K/20-F
  lib/sec_edgar.py               +parse_segments(), +labels() (linkbase de etiquetas); reutiliza _get/_cached/Budget
  lib/peers.py                   NUEVO  candidatos, orden por tamaño, cola de análisis de rivales y resumen compacto
  lib/trending.py                NUEVO  más negociadas / mayores subidas / mayores caídas del día sobre el universo
  main.py                        +GET /api/v2/segments/{symbol}, +GET /api/v2/peers/{symbol}[?symbols=…], +GET /api/v2/trending
  tests/test_universe.py, test_segments.py, test_peers.py, test_trending.py   NUEVOS
  tests/fixtures/segments/<T>.json, tests/fixtures/trending/batch.json, tests/fixtures/peers/caps.json   NUEVOS (capturados)
frontend/src/lib/api.ts          +tipos Segments, Peers, Trending (aditivos)
docs/rediseno/E2B_REGISTRO.md    NUEVO
```

---

### Task 0: Worktree

- [ ] `git worktree add ../finanzer_next-e2b -b rediseno/e2b-segmentos-rivales-tendencias rediseno/e1-sistema-historia`, luego `git merge --no-ff main` (conflicto conocido en `backend/main.py`: conserva el endpoint `/api/v2/prices` **y** el arranque de `keepalive`). `npm ci` en `frontend/`; suite del backend en verde con `/Users/joseestebanroa/Downloads/finanzer_next/.venv313/bin/python -m pytest tests -q`. **Puertos:** la sesión de E2a usa 3000/8767; tú usa el replay en **8768** y, si necesitas `next dev`, el **3001** (no los pares de E2a).

---

### Task 1: Universo de valores (S&P 500 + ADR principales)

**Files:** Create `backend/tools/build_universe.py`, `backend/lib/universe.py`, `backend/config/universe.tsv`, `backend/tests/test_universe.py`; Modify `backend/config/market.toml`.

**Interfaces:**
- `config/universe.tsv`: cabecera `# GENERADO por tools/build_universe.py el AAAA-MM-DD desde <fuente>`; columnas `symbol\tname\torigin\tgics_sector\tdamodaran_industry`. Símbolos en formato Yahoo (`BRK-B`, no `BRK.B`).
- `universe.load() -> List[Dict]`, `universe.symbols(origin: Optional[str] = None) -> List[str]`, `universe.by_industry(industry: str) -> List[str]`, `universe.meta() -> {date, source, count}`.

- [ ] **Step 1: Config** (`market.toml`):
```toml
[universe]
# S&P 500 (tabla pública de constituyentes, instantánea fechada) + ADR principales: base de la portada (tendencias) y
# de los rivales preferentes. Se regenera con tools/build_universe.py; el archivo dice su fecha.
sp500_source = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
max_age_days = 120          # más viejo: /api/v2/trending lo dice en su nota ("universo del AAAA-MM-DD")
adrs = ["TSM", "ASML", "NVO", "SAP", "TM", "SONY", "BABA", "PDD", "SHEL", "BP", "TTE", "HSBC", "BCS", "UL", "AZN",
        "GSK", "NVS", "RIO", "BHP", "SAN", "BBVA", "ING", "DEO", "BTI", "MUFG", "SMFG", "HDB", "IBN", "INFY", "SHOP",
        "RY", "TD", "ENB", "CNQ", "BN", "ARM", "SPOT", "NU", "MELI", "SE"]
```
(Revisa que cada ADR de `config/adr.toml [factors.*]` esté en la lista.)
- [ ] **Step 2: Test que falla** `test_universe.py`: con un `universe.tsv` sintético en `tmp_path` (monkeypatch de la ruta): `symbols()` devuelve todos; `symbols("adr")` solo los ADR; `by_industry("Computers/Peripherals")` filtra; `meta()["date"]` sale de la cabecera; un símbolo con punto se normaliza a guion.
- [ ] **Step 3: Implementar** `lib/universe.py` (lectura una vez por proceso, como `industry_bench._load_firms`) y `tools/build_universe.py`: descarga la tabla (pandas `read_html`, requiere red: herramienta local, no en Render), normaliza símbolos, añade los ADR de la config, pone la industria con `industry_bench.firm(symbol)` (sin red) y escribe el TSV ordenado. Si la descarga falla, sale con error y **no** sobrescribe el archivo.
- [ ] **Step 4:** Ejecuta la herramienta, revisa el número (≈ 503 + 40) y que `firm()` resuelve industria para ≥ 95 % (anota los que no), commit del TSV y del código. `"E2b: universo de valores (S&P 500 + ADR principales) con su industria de Damodaran"`.

---

### Task 2: Ingresos por segmento desde la instancia XBRL

**Files:** Modify `backend/lib/sec_edgar.py` (+`parse_segments`, +`labels`); Create `backend/lib/segments.py`, `backend/tests/test_segments.py`, `backend/tests/capture_segments.py`, `backend/tests/fixtures/segments/<T>.json`; Modify `backend/config/market.toml` (+`[segments]`), `backend/main.py` (+endpoint).

**Interfaces:**
- `sec_edgar.parse_segments(xml: bytes, axes: Tuple[str, ...], concepts: Tuple[str, ...]) -> Dict[str, Dict[str, Dict[str, float]]]` → `{axis: {member_qname: {"YYYY-MM-DD/YYYY-MM-DD": valor}}}`: contextos de **duración** con **una sola** `explicitMember` cuyo eje está en `axes`; conceptos `us-gaap` o `ifrs-full` en `concepts`; si un mismo miembro y periodo trae varios conceptos, se queda el primero de la lista `concepts` (prioridad). Lectura en flujo igual que `parse_instance`.
- `sec_edgar.labels(xml_lab: bytes, qnames: Set[str]) -> Dict[str, str]`: etiqueta estándar (`role/label`) de cada miembro desde el linkbase `*_lab.xml` del filing.
- `segments.build(symbol) -> {status, fiscal_years: [..], axis, axis_label, segments: [{member, label, values: {FY: valor}, share_last}], total_reported: {FY: valor}, reconciles: bool, gap_pct, secondary: {axis, axis_label, segments} | None, currency, source: {form, filed, accn}, reason}`.
  - Filing: el último 10-K/20-F/40-F con XBRL de `submissions` (forms anuales).
  - Ejes por prioridad (config): `StatementBusinessSegmentsAxis` → `ProductOrServiceAxis` → `StatementGeographicalAxis` (este último va a `secondary` si hay uno de los anteriores).
  - Años: los periodos de ~1 año (≥ `min_period_days`) del filing (suelen ser 3); `FY` = año del fin del periodo.
  - Conciliación: suma de segmentos del último año vs ingresos consolidados del mismo periodo (concepto sin dimensión en la misma instancia, o `revenue` de companyfacts): `reconciles` si `|gap| ≤ reconcile_tolerance`. Si no concilia, **se publica igual** con `reconciles: false` y `gap_pct` (hay eliminaciones intersegmento): la UI lo dirá; nunca se esconde.
  - Sin dimensiones utilizables: `status "sin_dato"`, `reason "el 10-K no desglosa ingresos por segmento en XBRL"`.
- `GET /api/v2/segments/{symbol}` → `segments.build(symbol)`; caché por número de filing (`segments_ttl_s`), máximo `segments_cache_max` entradas; `Budget` propio de `segments_budget_s` (fuera del análisis).

- [ ] **Step 1: Config**
```toml
[segments]
axes = ["StatementBusinessSegmentsAxis", "ProductOrServiceAxis", "StatementGeographicalAxis"]
revenue_concepts = ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet",
                    "RevenuesNetOfInterestExpense", "Revenue"]   # el último: ifrs-full
min_period_days = 350
reconcile_tolerance = 0.02
segments_budget_s = 8.0      # endpoint perezoso: más margen que el análisis (3 s), sigue acotado
segments_ttl_s = 604800      # 7 días por filing (no cambia hasta el siguiente 10-K)
segments_cache_max = 64
max_instance_mb = 25         # instancia mayor: sin_dato con motivo (memoria de Render)
```
- [ ] **Step 2: Tests que fallan** `test_segments.py`:
  - `parse_segments` sobre una instancia sintética (amplía `tests/f2b_fixtures.instance_xml` para emitir contextos de **duración** con miembro, o escribe el XML mínimo en el test) con dos ejes, tres años y un contexto con dos dimensiones (debe ignorarse).
  - `labels` sobre un linkbase sintético mínimo.
  - `segments.build` con un `FETCHER` falso que sirve índice, instancia y linkbase: elige `StatementBusinessSegmentsAxis`, ordena los segmentos por el último año (de mayor a menor), `share_last` suma 1 ± 1e-9, `secondary` = geográfico, `reconciles` verdadero con el consolidado; y otro caso con `gap` del 5 % → `reconciles: false`, `gap_pct ≈ 0.05`.
  - Fixtures reales: para AAPL, JPM y XOM, `segments.build` con `tests/fixtures/segments/<T>.json` (Step 4) da `status "ok"` y al menos 2 segmentos; para MC.PA, `sin_dato` (no presenta en la SEC).
- [ ] **Step 3: Implementar.** Reutiliza `_get`, `_get_json`, `ARCHIVE_URL`, `_cached`, `Budget` de `sec_edgar`. El nombre de la instancia y del linkbase salen del `index.json` del filing (`*_htm.xml` y `*_lab.xml`). Antes de parsear, si el tamaño de la respuesta supera `max_instance_mb`, `sin_dato` con motivo.
- [ ] **Step 4: Fixtures sin red.** `tests/capture_segments.py <T…>`: con el User-Agent del Llavero en el entorno, descarga índice, instancia y linkbase del último 10-K/20-F de cada ticker y guarda **solo lo que usa** `build` (contextos con los ejes de la config, los hechos de los conceptos de ingresos con y sin dimensión, y las etiquetas de los miembros) en `tests/fixtures/segments/<T>.json`; un `FETCHER` de replay los sirve. Captura los 8 tickers de verificación (AAPL, JPM, O, NEE, XOM, PLTR, RIVN, BCS) y MC.PA (sin SEC).
- [ ] **Step 5:** PASS; con el replay en 8768, `curl -s localhost:8768/api/v2/segments/AAPL` muestra iPhone, Mac, iPad, Wearables y Services (o los segmentos geográficos como secundarios) y `reconciles`. Revisa a mano los 8: anota en el registro, por ticker, eje usado, segmentos y conciliación. Commit `"E2b: ingresos por segmento desde la instancia XBRL del último 10-K (endpoint perezoso)"`.

---

### Task 3: Rivales analizados con el motor completo

**Files:** Create `backend/lib/peers.py`, `backend/tests/test_peers.py`, `backend/tests/fixtures/peers/caps.json`; Modify `backend/config/market.toml` (+`[peers]`), `backend/main.py` (+endpoint, +hilo de rivales).

**Interfaces:**
- `peers.candidates(symbol: str, industry: str, region: str) -> List[str]`: misma industria de Damodaran; primero los del universo (`universe.by_industry`), después el resto de `industry_bench._load_firms()` de la misma región; sin el propio símbolo ni otras clases de la misma empresa (`BRK-A`/`BRK-B`, `GOOG`/`GOOGL`).
- `peers.rank(symbol, cands, caps) -> List[str]`: por cercanía de capitalización (|log(cap_r / cap_s)|), los `peers_count` primeros; `caps` de Finnhub `profile2` (`marketCapitalization`), cacheado `caps_ttl_s`. Con menos de `min_peers` candidatos: devuelve los que haya y `note "menos de 3 comparables en su industria"`.
- `peers.summary(analysis) -> Dict`: resumen **compacto** de un análisis del motor (no el análisis entero, por memoria): `{symbol, name, price, currency, quality: {score, level}, price_score: {score, level}, confidence, metrics: {key: {value, value_txt}}}` con las claves de `display.charts.comparison` (las que la tabla de rivales compara) y `market_cap`.
- `peers.queue`: cola de un solo hilo; `peers.request(symbol, rivals) -> {status, rivals: [{symbol, status: "listo"|"analizando"|"en_cola"|"fallo", summary | reason}], note}`; los resúmenes se guardan en una caché LRU (`summary_cache_max`, `summary_ttl_s`). Cada análisis de rival corre con `main._compute_limited` (comparte `_ANALYSIS_SLOTS`: un usuario nunca espera por un rival más que por otro usuario) y con prioridad baja: si hay análisis de usuarios esperando, el hilo de rivales espera.
- `GET /api/v2/peers/{symbol}` → `request(symbol, rank(...))`; `?symbols=A,B,C` (máx. `peers_count`, símbolos válidos `^[A-Z0-9.\-]{1,10}$`) sustituye a los automáticos (rivales editables). Respuesta inmediata; el cliente repite cada `poll_s` hasta que todos estén `listo` o `fallo`.

- [ ] **Step 1: Config**
```toml
[peers]
peers_count = 5
min_peers = 3
caps_ttl_s = 604800         # capitalizaciones de Finnhub: 7 días (solo ordenan por tamaño)
summary_ttl_s = 86400       # resumen del análisis de un rival: 1 día
summary_cache_max = 64
poll_s = 4                  # el cliente vuelve a preguntar cada 4 s mientras haya rivales en cola
max_queue = 20              # rivales en cola como máximo (protege Render); por encima: "fallo" con motivo "cola llena"
```
- [ ] **Step 2: Tests que fallan** `test_peers.py`:
  - `candidates`: con un `_load_firms` y un universo sintéticos, orden universo primero, sin el propio símbolo ni sus otras clases.
  - `rank`: por cercanía de capitalización; con 2 candidatos → `note`.
  - `summary`: sobre un golden real (`tests/golden/panel/AAPL.json`) devuelve las claves de comparación con `value_txt` idéntico al de `display.charts.comparison` (mismas cifras que la página).
  - Cola: con `_compute_limited` falso (que duerme y devuelve un golden), dos `request` seguidos no lanzan dos veces el mismo rival; el estado pasa de `en_cola` → `analizando` → `listo`; un fallo del análisis da `fallo` con motivo y no rompe la cola; con `max_queue` superado, `fallo "cola llena"`.
  - Endpoint con `?symbols=` inválido → 422.
- [ ] **Step 3: Implementar** según las interfaces. La cola es un `threading.Thread` daemon con `queue.Queue(maxsize=max_queue)`; arranca la primera vez que se pide (no al importar: en tests y en el replay no debe haber hilos sueltos).
- [ ] **Step 4: Fixtures:** `tests/fixtures/peers/caps.json` con las capitalizaciones de los candidatos de los 8 tickers (captura con la clave del Llavero en el entorno). Con el replay en 8768 (que ya tiene los análisis del panel en fixtures), `GET /api/v2/peers/AAPL` debe acabar con 5 rivales `listo` que estén en el panel (si los candidatos no tienen fixtures en el panel, el replay los da como `fallo` "sin fixtures": en el test de integración usa `?symbols=` con tickers del panel, p. ej. `MSFT,DELL,HPQ` si están; si no, los del panel de la misma industria).
- [ ] **Step 5:** PASS; registro con los rivales automáticos propuestos para los 8 tickers (y si tienen sentido como comparables: revisión a mano, una línea por ticker). Commit `"E2b: rivales automáticos y editables, analizados con el motor completo en segundo plano"`.

---

### Task 4: Tendencias del día (más negociadas, mayores subidas, mayores caídas)

**Files:** Create `backend/lib/trending.py`, `backend/tests/test_trending.py`, `backend/tests/fixtures/trending/batch.json`; Modify `backend/config/market.toml` (+`[trending]`), `backend/main.py` (+endpoint y precalentado al arrancar).

**Interfaces:**
- `trending.compute(fetch_batch) -> {session, as_of, lists: {most_traded: [...], gainers: [...], losers: [...]}, universe_date, count}` donde cada item es `{symbol, name, price, change_pct, dollar_volume}`; `most_traded` por volumen en dólares (`close × volume`) de la última sesión; `gainers`/`losers` por variación frente a la sesión anterior; `top_n` por lista; excluye los que no tienen las dos sesiones.
- `trending.get() -> {status: "listo"|"calculando"|"sin_dato", data, reason}`: devuelve la última lista buena (memoria del proceso) y, si es de una sesión anterior a la última cerrada (o no hay), lanza el cálculo en un hilo (uno a la vez). Tras un reinicio de Render, el primer pedido devuelve `calculando` y el cliente repite.
- `fetch_batch(symbols) -> DataFrame` por defecto `yf.download(symbols, period="5d", interval="1d", group_by="ticker", threads=True, auto_adjust=False)` en trozos de `batch_size`; inyectable (tests y replay).
- `GET /api/v2/trending` → `trending.get()`. En el arranque de la app, un precalentado en segundo plano (como `keepalive`, solo en Render: `RENDER_EXTERNAL_URL`).

- [ ] **Step 1: Config**
```toml
[trending]
top_n = 10
batch_size = 100           # símbolos por descarga de Yahoo (lotes: menos peticiones)
min_price = 1.0            # excluye cotizaciones residuales
refresh_after_close_min = 30   # la sesión se da por cerrada 30 min después del cierre de NY (16:00 ET)
```
- [ ] **Step 2: Tests que fallan:** `compute` con un DataFrame sintético multi-ticker (forma real de `yf.download(group_by="ticker")`): orden correcto de las tres listas, exclusión de quien no tiene dos sesiones o precio < `min_price`, `dollar_volume` = cierre × volumen; `get()` con un `fetch_batch` lento: primera llamada `calculando`, después `listo`; dos llamadas a la vez lanzan un solo cálculo; sesión nueva → recalcula.
- [ ] **Step 3: Implementar.** La "última sesión cerrada" se calcula con la zona `America/New_York` y `refresh_after_close_min` (sin festivos: si Yahoo no trae sesión nueva, la lista sigue siendo la anterior, con su fecha).
- [ ] **Step 4: Fixture** `tests/fixtures/trending/batch.json` con una descarga real del universo (5 días) para el replay; `GET /api/v2/trending` en el replay devuelve las tres listas con datos de esa fecha. Mide y anota en el registro: tiempo de la descarga real completa y memoria pico del proceso (`resource.getrusage`), para confirmar que cabe en Render.
- [ ] **Step 5:** PASS; commit `"E2b: tendencias del día sobre el universo (más negociadas, subidas, caídas) con cálculo perezoso"`.

---

### Task 5: Contrato, verificación y registro

- [ ] **Step 1:** Tipos aditivos en `frontend/src/lib/api.ts`: `SegmentsResponse`, `PeersResponse`, `TrendingResponse` (formas exactas de las Tasks 2–4) y funciones cliente `fetchSegments`, `fetchPeers(symbol, symbols?)`, `fetchTrending` en `frontend/src/v2/lib/` (sin UI). `npm run check` en verde.
- [ ] **Step 2:** Golden intacto: `git diff main --stat -- backend/tests/golden` vacío y `../.venv313/bin/python tests/diff_golden.py --env panel` sin diferencias. Suite completa en verde.
- [ ] **Step 3:** Prueba de carga en local contra el backend real (no el replay), con las claves del Llavero en el entorno: `segments` de los 8 tickers, `peers` de AAPL hasta completar, `trending` completo; anota tiempos, memoria pico y errores. Si algo pasa de 400 MB de pico, redúcelo antes de cerrar.
- [ ] **Step 4:** `docs/rediseno/E2B_REGISTRO.md` (commits, salidas de verificación, desviaciones, tabla por ticker de segmentos y rivales, medidas de carga). Termina tu turno con el informe para el PM. Sin push ni merge.
