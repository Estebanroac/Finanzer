# Rediseño · Etapa E2a: datos del motor — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Añadir al motor los datos nuevos de la spec §4 que salen de fuentes ya conectadas (EDGAR, serie de precios, Finnhub), corregir en origen tres textos del motor y enseñar lo esencial en `/v2`, sin cambiar ninguna cifra ni veredicto existente.

**Architecture:** Cada dato nuevo se calcula en el backend (en `lib/`, junto a la fuente que ya lo descarga), entra al análisis como clave **aditiva** y se publica formateado en un bloque nuevo `display.extended` (la regla del proyecto: lo que se lee se calcula una vez en `display` y lo consumen web y PDF). Lo caro o interactivo va en endpoints `/api/v2/…` aparte (serie de 5 años con eventos; escenarios sin estado). El contrato `api.ts` crece de forma aditiva. Los textos corregidos cambian el golden: un commit por causa y `GOLDEN_DIFF_E2A.md` con la aprobación literal del usuario.

**Tech Stack:** Python 3.13.4 (`.venv313`), FastAPI, pandas, pytest; Next.js 16 / React 19 / TypeScript en `/v2`; Vitest y Playwright (los de E1).

**Especificación:** `docs/superpowers/specs/2026-10-17-rediseno-experiencia-design.md` (§4 datos nuevos, §7 verificación). **Etapa anterior:** E1 cerrada en la rama `rediseno/e1-sistema-historia` (registro `docs/rediseno/E1_REGISTRO.md`, con los pendientes de E2).

**Fuera de E2a (van en E2b, plan aparte):** ingresos por segmento (instancias XBRL con dimensiones), rivales y tendencias de la portada (necesitan un universo de valores). **Fuera de E2:** empleados (no llega en producción: el plan B de yfinance no lo trae y EDGAR solo lo tiene en 3 de 36 emisores; decisión del PM, sin hueco "Sin dato" permanente).

## Global Constraints

- **Ninguna cifra ni veredicto existente cambia.** Los únicos cambios del golden permitidos son: (a) claves nuevas aditivas, (b) los tres textos corregidos en origen (T1–T2). Cualquier otro cambio del golden es un bug.
- **Trazabilidad del golden:** un commit por causa, el golden regenerado se commitea junto con el cambio que lo provoca (`backend/tests/diff_golden.py --regenerate`), y `docs/fiabilidad/GOLDEN_DIFF_E2A.md` sigue la convención de `GOLDEN_DIFF_DAMODARAN.md` (cabecera con commits, tabla "Por commit": Commit | Causa | Tickers | Campos | Líneas PDF | Cambios de veredicto). **PARADA** para la aprobación del usuario antes de dar el golden por bueno (Task 11).
- **Guardián narrativo:** toda frase nueva en `display` se declara con `_record(texto, _claim(...), source=...)` o va en `SKIP_PATHS` si es dato y no prosa (`backend/tests/guardian.py`); `tests/test_guardian.py` y `tests/test_guardian_detecta.py` en verde.
- **Sin parches:** lo que está mal se arregla donde nace (motor), no en `/v2`.
- **Nunca bloquear el análisis:** toda consulta nueva corre dentro de los presupuestos y esperas existentes (`data.edgar.budget_s`, `market.context.wait_timeout_s`) y, si falla, el dato sale `sin_dato` con su motivo.
- **Render gratuito (512 MB, se duerme):** nada que cargue en memoria más de una serie de 5 años por símbolo; cachés con TTL y tamaño acotado.
- **Límites:** SEC ≤ 10 peticiones/s con User-Agent; Finnhub ≤ 60/min.
- **Secretos:** `finanzer-finnhub` y `finanzer-sec-ua` en el Llavero; nunca se imprimen ni se escriben en fixtures, logs o el chat. Las capturas de fixtures se hacen con las variables de entorno leídas del Llavero en el mismo comando.
- **Config, no literales:** todo umbral, tamaño o periodo nuevo va en `backend/config/*.toml` con su comentario; el frontend no escribe cortes (guardián `check-analysis-literals.mjs`).
- **Diseño de `/v2`:** todas las reglas de E1 siguen (spec §5 revisada: lectura 16/17 px, mínimo 12 px, simetría, sin neón, zoom permitido).
- **Sin push, sin merge a `main`, sin deploy.** Nada se sube sin un "ok, pushea" explícito del usuario.

## File Structure

```
backend/
  config/market.toml        +[exchanges] (código → nombre), +[history] chart_period/chart_cache_ttl_s,
                            +[context] news_max_v2/news_summary_chars/news_lang/next_earnings_days
  config/valuation.toml     +[scenario] límites de los supuestos del usuario
  lib/verdict.py            border(): frase con mayúscula inicial (T1)
  lib/display.py            read_spread(): "pp" (T1); +_extended_block() → display["extended"] (T3–T9)
  lib/alert_interpretations.py  spread en "pp" (T1)
  lib/exchanges.py          NUEVO  nombre de la bolsa desde el código (T2)
  lib/sec_edgar.py          submissions(): +profile {sic, …} (T3); fetch()/summary(): lo propagan
  lib/price_history.py      +day_change(frame, price) (T4); +chart(symbol) serie de 5 años con eventos (T9)
  lib/history_10y.py        NUEVO  10 ejercicios desde _history_fy (T5)
  lib/financial_ratios.py   piotroski_evaluate(): cur/prev por criterio (T6)
  lib/scenario.py           NUEVO  escenario del usuario con el mismo DCF del motor (T7)
  lib/market_context.py     news(): campos extra (T8); +next_earnings() (T8)
  lib/prices_v2.py          serialize(): +a (ajustado) y eventos (T9)
  main.py                   claves aditivas en result; POST /api/v2/scenario; /api/v2/prices con 5 años y eventos
  tests/…                   tests nuevos por tarea; f2b_fixtures/fixture_backend ampliados; capturas nuevas
frontend/
  src/lib/api.ts            +tipos aditivos (Extended, ScenarioRequest/Response) ; check-contract en verde
  src/v2/…                  cableado mínimo (T10)
docs/
  fiabilidad/GOLDEN_DIFF_E2A.md   NUEVO
  rediseno/E2A_REGISTRO.md        NUEVO
```

---

### Task 0: Worktree desde E1, puesto al día con `main`

**Files:** ninguno (git).

- [ ] **Step 1: Parar los servidores de E1.** La sesión de E1 dejó `next dev` (3000) y el replay (8767) levantados. Playwright usa `reuseExistingServer: true`: si siguen vivos, los tests de E2a correrían contra el código de E1.

```bash
lsof -ti tcp:3000 -sTCP:LISTEN | xargs -r kill
lsof -ti tcp:8767 -sTCP:LISTEN | xargs -r kill
```
Expected: `lsof -i tcp:3000 -i tcp:8767` vacío.

- [ ] **Step 2: Rama y worktree**

```bash
cd /Users/joseestebanroa/Downloads/finanzer_next
git worktree add ../finanzer_next-e2a -b rediseno/e2a-datos-motor rediseno/e1-sistema-historia
cd ../finanzer_next-e2a
git merge --no-ff main -m "E2a: main al día en la rama del rediseño (F6/F7 tras el corte de E1)"
```
Conflicto conocido (anotado en el cierre de E1): `backend/main.py`, el arranque de `keepalive` y el endpoint `/api/v2/prices` cayeron en el mismo sitio. Resolución: **conservar los dos bloques** (primero el endpoint, luego `import keepalive` / `_keepalive.start()` tal como está en `main`).

- [ ] **Step 3: Dependencias y suite en verde antes de tocar nada**

```bash
cd frontend && npm ci && cd ../backend
../.venv313/bin/python tools/gen_frontend_config.py --check
../.venv313/bin/python -m pytest tests -q
cd ../frontend && npm run check && npm run test:v2 && npm run e2e:v2
```
Expected: todo en verde (el `.venv313` está en el checkout principal; usa la ruta absoluta `/Users/joseestebanroa/Downloads/finanzer_next/.venv313/bin/python` si no existe en el worktree). Si algo falla aquí, es de la fusión: arréglalo en un commit propio antes de seguir.

---

### Task 1: Dos textos del motor corregidos en origen (spread en "pp", frontera con mayúscula)

**Files:**
- Modify: `backend/lib/display.py` (`read_spread`, ~línea 260), `backend/lib/alert_interpretations.py` (~líneas 305–312), `backend/lib/verdict.py` (`border`, ~línea 47)
- Test: `backend/tests/test_textos_origen.py` (nuevo)

**Interfaces:**
- Produces: `numfmt.pp(v: Optional[float], dec: int = 1) -> str` — diferencia de porcentajes en puntos: `0.884 → "+88.4 pp"`, `-0.02 → "−2.0 pp"` (signo menos tipográfico, como `numfmt.signed_pct`).

- [ ] **Step 1: Test que falla `backend/tests/test_textos_origen.py`**

```python
import numfmt
from display import read_spread
from alert_interpretations import interpret_spread   # nombre real: el de la función de las líneas ~295-315
from verdict import border


def test_pp_formatea_diferencias_de_porcentajes():
    assert numfmt.pp(0.884) == "+88.4 pp"
    assert numfmt.pp(-0.02) == "−2.0 pp"
    assert numfmt.pp(None) == "—"


def test_spread_en_puntos_porcentuales():
    label, tone, text = read_spread(0.884, 0.98, 0.096)
    assert "+88.4 pp" in text and "%:" not in text
    _, _, text2 = read_spread(0.03, 0.12, 0.09)
    assert "en +3.0 pp" in text2


def test_frontera_empieza_con_mayuscula():
    b = border(46, [65, 45, 30], ["atractivo", "razonable", "exigente", "muy exigente"], 2)
    assert b is not None and b["text"].startswith("En la frontera con «exigente»")
```
Antes de escribirlo, abre `alert_interpretations.py` alrededor de la línea 295 y usa el nombre real de la función que produce `"spread +{_pct(sp)}"`; abre `verdict.border` para su firma real (valor, bandas, rótulos, k) y ajusta la llamada del test a esa firma.

- [ ] **Step 2: Ejecutar y ver que falla**

Run: `cd backend && ../.venv313/bin/python -m pytest tests/test_textos_origen.py -q`
Expected: FAIL (`numfmt.pp` no existe; textos con "%").

- [ ] **Step 3: Implementar**
  - En `lib/numfmt.py`, junto a `signed_pct`:
```python
def pp(v: Optional[float], dec: int = 1) -> str:
    """Diferencia entre dos porcentajes, en puntos porcentuales (0.884 → "+88.4 pp")."""
    if v is None:
        return "—"
    return f"{_sign(v)}{abs(v) * 100:.{dec}f} pp"
```
    (usa `_sign` del propio módulo; si `_sign` no devuelve "+" para positivos, construye el signo igual que `signed_pct`).
  - `display.read_spread`: `f"un spread de {numfmt.pp(spread)}: …"` y `f"… supera al WACC ({_pct(wacc)}) en {numfmt.pp(spread)}, …"`.
  - `alert_interpretations`: los tres `spread +{_pct(sp)}` / `spread {_pct(sp)}` pasan a `spread {numfmt.pp(sp)}`.
  - `verdict.border`: `"text": f"En la frontera con «{nb}» …"`. Busca con `grep -rn "en la frontera con" backend/lib` todo lugar que concatene este texto tras otro (p. ej. `display.py` ~1157: `price_note + "; " + _bp`) y, donde quede a mitad de frase, pásalo a minúscula **allí** con `_bp[0].lower() + _bp[1:]`; donde empiece frase (nota sola), queda con mayúscula. El regex del guardián (`frontera_nivel`) trabaja en minúsculas: no cambia.

- [ ] **Step 4: Ejecutar**

Run: `../.venv313/bin/python -m pytest tests/test_textos_origen.py tests/test_guardian.py tests/test_guardian_detecta.py -q`
Expected: PASS.

- [ ] **Step 5: Golden y commit (uno por causa)**

```bash
../.venv313/bin/python tests/diff_golden.py --env panel          # revisar: solo cambian estas frases
../.venv313/bin/python tests/diff_golden.py --env local
```
Anota en `docs/fiabilidad/GOLDEN_DIFF_E2A.md` (créalo con la cabecera de la convención) los tickers, campos y líneas del PDF afectados. Si aparece cualquier otro cambio, para y averigua por qué. Luego:
```bash
../.venv313/bin/python tests/diff_golden.py --regenerate --yes --env panel
../.venv313/bin/python tests/diff_golden.py --regenerate --yes --env local
../.venv313/bin/python tests/contract_forced.py --write
../.venv313/bin/python -m pytest tests -q
git add lib/numfmt.py lib/display.py lib/alert_interpretations.py lib/verdict.py tests/test_textos_origen.py tests/golden ../docs/fiabilidad/GOLDEN_DIFF_E2A.md
git commit -m "E2a: spread ROIC−WACC en puntos porcentuales y frontera de nivel con mayúscula (golden: solo esas frases)"
```

---

### Task 2: Nombre de la bolsa en lugar del código ("NMS" → "Nasdaq")

**Files:**
- Create: `backend/lib/exchanges.py`
- Modify: `backend/config/market.toml` (+`[exchanges]`), `backend/main.py` (bloque `result["profile"]`, ~línea 409)
- Test: `backend/tests/test_exchanges.py`

**Interfaces:**
- Produces: `exchanges.name(code: Optional[str]) -> Optional[str]`; `result["profile"]["exchange"]` = nombre; `result["profile"]["exchange_code"]` = código original (aditivo).

- [ ] **Step 1: Config** — añade a `backend/config/market.toml`:

```toml
[exchanges]
# Código de bolsa de Yahoo (fast_info.exchange / exchangeName) → nombre para el lector. Fuente: códigos MIC/Yahoo.
# Un código que no está aquí se muestra tal cual y se registra en el log (para añadirlo).
NMS = "Nasdaq"
NGM = "Nasdaq"
NCM = "Nasdaq"
NAS = "Nasdaq"
NasdaqGS = "Nasdaq"
NasdaqGM = "Nasdaq"
NasdaqCM = "Nasdaq"
NYQ = "NYSE"
NYSE = "NYSE"
ASE = "NYSE American"
PCX = "NYSE Arca"
BTS = "Cboe BZX"
PAR = "Euronext París"
AMS = "Euronext Ámsterdam"
LSE = "Bolsa de Londres"
GER = "Xetra"
FRA = "Bolsa de Fráncfort"
MCE = "BME (Madrid)"
TOR = "Bolsa de Toronto"
TYO = "Bolsa de Tokio"
HKG = "Bolsa de Hong Kong"
```
Antes de cerrar la lista, ejecuta `grep -h '"exchange"' backend/tests/golden/*/*.json | sort | uniq -c` y añade cualquier código que aparezca en el golden y falte aquí.

- [ ] **Step 2: Test que falla `backend/tests/test_exchanges.py`**

```python
import exchanges


def test_codigos_conocidos():
    assert exchanges.name("NMS") == "Nasdaq"
    assert exchanges.name("NYQ") == "NYSE"


def test_desconocido_se_muestra_tal_cual():
    assert exchanges.name("XYZ") == "XYZ"
    assert exchanges.name(None) is None


def test_todos_los_codigos_del_golden_tienen_nombre():
    import glob, json
    codes = {json.load(open(p))["profile"].get("exchange_code") or json.load(open(p))["profile"].get("exchange")
             for p in glob.glob("tests/golden/panel/*.json")}
    assert {c for c in codes if c and exchanges.name(c) == c} == set()
```

- [ ] **Step 3: Implementar `backend/lib/exchanges.py`**

```python
"""Rediseño E2a: nombre legible de la bolsa a partir del código del proveedor (config/market.toml [exchanges])."""
import logging
from typing import Optional

from settings import cfg

logger = logging.getLogger(__name__)


def name(code: Optional[str]) -> Optional[str]:
    if not code:
        return None
    table = cfg("market.exchanges") or {}
    out = table.get(str(code))
    if out is None:
        logger.info(f"[exchanges] código sin nombre: {code}")
        return str(code)
    return out
```
En `main.py`, en el dict `result["profile"]`: `"exchange": exchanges.name(profile.exchange), "exchange_code": profile.exchange,` (import arriba, con los demás de `lib`).

- [ ] **Step 4: Ejecutar, golden, commit**

Run: `../.venv313/bin/python -m pytest tests/test_exchanges.py -q` → PASS. Luego el mismo ciclo de golden de Task 1 (anotar en `GOLDEN_DIFF_E2A.md`: cambia `profile.exchange` y la línea de bolsa del PDF; nada más).
```bash
git commit -am "E2a: nombre de la bolsa en lugar del código del proveedor (NMS → Nasdaq)"
```
(incluye `lib/exchanges.py`, `tests/test_exchanges.py` y el golden con `git add` explícito).

---

### Task 3: Ficha de la empresa desde EDGAR (SIC, sede, constitución, cierre fiscal, tipo de emisor)

**Files:**
- Modify: `backend/lib/sec_edgar.py` (`submissions.make`, `fetch`, `summary`), `backend/tests/f2b_fixtures.py` (`save_submissions`), `backend/main.py` (clave aditiva)
- Create: `backend/tests/f2b_enrich_profile.py` (enriquece los fixtures sin red desde `tests/fixtures/edgar/raw/`), `backend/lib/company_profile.py`
- Test: `backend/tests/test_company_profile.py`

**Interfaces:**
- Produces: `sec_edgar.submission_profile(raw: dict) -> dict` → `{sic, sic_description, state_of_incorporation, fiscal_year_end, city, state_or_country, category, website}` (cada uno `None` si falta); `submissions()` devuelve además `"profile"`; `fetch()` lo pone en `res["profile"]`; `summary()` lo incluye; `result["company_profile"]` = salida de `company_profile.build(edgar_profile, profile)` → `{rows: [{key, label, value}], source, status, reason}`.

- [ ] **Step 1: Test que falla `backend/tests/test_company_profile.py`**

```python
import sec_edgar
import company_profile

RAW = {"sic": "3571", "sicDescription": "Electronic Computers", "stateOfIncorporation": "CA",
       "stateOfIncorporationDescription": "CA", "fiscalYearEnd": "0926", "category": "Large accelerated filer",
       "website": "", "addresses": {"business": {"city": "CUPERTINO", "stateOrCountry": "CA",
                                                 "stateOrCountryDescription": "CA"}}}


def test_submission_profile_extrae_los_campos():
    p = sec_edgar.submission_profile(RAW)
    assert p["sic"] == "3571" and p["sic_description"] == "Electronic Computers"
    assert p["fiscal_year_end"] == "0926" and p["city"] == "CUPERTINO"
    assert p["website"] is None


def test_ficha_legible():
    f = company_profile.build(sec_edgar.submission_profile(RAW), {"country": "United States"})
    rows = {r["key"]: r["value"] for r in f["rows"]}
    assert rows["sic"] == "3571 · Electronic Computers"
    assert rows["hq"] == "Cupertino, CA"
    assert rows["fiscal_year_end"] == "26 de septiembre"
    assert rows["category"] == "Gran emisor (large accelerated filer)"
    assert f["source"].startswith("SEC EDGAR")


def test_sin_edgar_dice_por_que():
    f = company_profile.build(None, {"country": "France"})
    assert f["status"] == "sin_dato" and f["rows"] == [] and f["reason"]
```

- [ ] **Step 2: Ejecutar y ver que falla**

Run: `../.venv313/bin/python -m pytest tests/test_company_profile.py -q` → FAIL.

- [ ] **Step 3: Implementar**
  - `sec_edgar.py`, junto a `issuer_country`:
```python
def submission_profile(sub: Dict[str, Any]) -> Dict[str, Any]:
    """Rediseño E2a: ficha del emisor en EDGAR (submissions), sin red adicional: viene en la misma respuesta."""
    b = (sub.get("addresses") or {}).get("business") or {}
    v = lambda x: (str(x).strip() or None) if x is not None else None
    return {"sic": v(sub.get("sic")), "sic_description": v(sub.get("sicDescription")),
            "state_of_incorporation": v(sub.get("stateOfIncorporationDescription") or sub.get("stateOfIncorporation")),
            "fiscal_year_end": v(sub.get("fiscalYearEnd")), "city": v(b.get("city")),
            "state_or_country": v(b.get("stateOrCountryDescription") or b.get("stateOrCountry")),
            "category": v(sub.get("category")), "website": v(sub.get("website"))}
```
    En `submissions.make()`: `return {"filings": …, "country": issuer_country(raw), "profile": submission_profile(raw)}`. En `fetch()`: `res["profile"] = _sub.get("profile")`. En `summary()`: añade `"profile"` a la tupla de claves.
  - `lib/company_profile.py`:
```python
"""Rediseño E2a: ficha legible de la empresa (capítulo 1) desde EDGAR submissions. Solo datos, sin lecturas."""
from typing import Any, Dict, Optional

from settings import cfg

_MONTHS = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
           "noviembre", "diciembre"]


def _fye(mmdd: Optional[str]) -> Optional[str]:
    if not mmdd or len(mmdd) != 4 or not mmdd.isdigit():
        return None
    return f"{int(mmdd[2:])} de {_MONTHS[int(mmdd[:2]) - 1]}"


def _title(s: Optional[str]) -> Optional[str]:
    return " ".join(w.capitalize() for w in s.split()) if s else None


def build(ed_profile: Optional[Dict[str, Any]], profile: Dict[str, Any]) -> Dict[str, Any]:
    src = "SEC EDGAR (submissions del emisor)"
    if not ed_profile:
        return {"status": "sin_dato", "rows": [], "source": src,
                "reason": "el emisor no presenta en la SEC: sin ficha oficial"}
    cats = cfg("market.filer_categories") or {}
    p = ed_profile
    hq = ", ".join(x for x in (_title(p.get("city")), p.get("state_or_country")) if x) or None
    sic = " · ".join(x for x in (p.get("sic"), p.get("sic_description")) if x) or None
    cand = [("sic", "Industria (código SIC)", sic), ("hq", "Sede", hq),
            ("incorporation", "Constituida en", p.get("state_of_incorporation")),
            ("fiscal_year_end", "Cierre del ejercicio", _fye(p.get("fiscal_year_end"))),
            ("category", "Tipo de emisor", cats.get((p.get("category") or "").lower(), p.get("category"))),
            ("website", "Web", p.get("website"))]
    rows = [{"key": k, "label": l, "value": v} for k, l, v in cand if v]
    return {"status": "ok" if rows else "sin_dato", "rows": rows, "source": src,
            "reason": None if rows else "EDGAR no trae la ficha del emisor"}
```
    Añade a `config/market.toml`:
```toml
[filer_categories]   # categoría de emisor de la SEC → texto (submissions.category, en minúsculas)
"large accelerated filer" = "Gran emisor (large accelerated filer)"
"accelerated filer" = "Emisor acelerado (accelerated filer)"
"non-accelerated filer" = "Emisor no acelerado (non-accelerated filer)"
"smaller reporting company" = "Pequeña empresa declarante (smaller reporting company)"
```
    (Comprueba en `tests/fixtures/edgar/raw/*.submissions.json` del checkout principal los valores reales de `category`: pueden venir combinados, p. ej. "Non-accelerated filer<br>Smaller reporting company"; normaliza separando por `<br>` y uniendo los textos con " · ".)
  - `main.py`: tras el bloque de `market_context`, `result["company_profile"] = company_profile.build((data_provenance edgar)["profile"], result["profile"])`. Localiza dónde está disponible `ed` (la salida de `sec_edgar.collect`) o `data_provenance.edgar` y usa esa; envuelve en `try/except → _sin_dato("company_profile", e)` como los demás bloques.
  - Fixtures: en `tests/f2b_fixtures.py::save_submissions` añade `"sic", "sicDescription", "stateOfIncorporation", "stateOfIncorporationDescription", "category", "website"` y `city` en `addresses`. Crea `tests/f2b_enrich_profile.py` siguiendo el patrón de `tests/f3_extend_history_fixtures.py`: lee `/Users/joseestebanroa/Downloads/finanzer_next/backend/tests/fixtures/edgar/raw/*.submissions.json` (no está en git: ruta absoluta del checkout principal), y añade esos campos a los `tests/fixtures/f2b/edgar/submissions/CIK*.json` existentes sin tocar `filings`. Ejecútalo y commitea los fixtures enriquecidos.

- [ ] **Step 4: Ejecutar**

Run: `../.venv313/bin/python tests/f2b_enrich_profile.py && ../.venv313/bin/python -m pytest tests/test_company_profile.py -q && ../.venv313/bin/python tests/diff_golden.py --env panel AAPL`
Expected: PASS; el diff de AAPL solo muestra la clave nueva `company_profile` y `data_provenance.edgar.profile`.

- [ ] **Step 5: Commit** (golden con las claves nuevas regenerado en el commit de la Task 11, todas las aditivas juntas; aquí solo código, test y fixtures)

```bash
git add lib/sec_edgar.py lib/company_profile.py config/market.toml main.py tests/f2b_fixtures.py tests/f2b_enrich_profile.py tests/test_company_profile.py tests/fixtures/f2b/edgar/submissions
git commit -m "E2a: ficha de la empresa desde EDGAR (SIC, sede, constitución, cierre fiscal, tipo de emisor)"
```
Nota: la suite de regresión fallará por las claves nuevas hasta la Task 11. Para no trabajar en rojo, marca en `tests/test_regression.py` (solo en esta rama, temporalmente) las claves aditivas de E2a como ignoradas con una lista `E2A_ADDITIVE = {"company_profile", …}` que la Task 11 **retira** al regenerar el golden. Anótalo en el registro.

---

### Task 4: Variación del día

**Files:**
- Modify: `backend/lib/price_history.py` (+`day_change`), `backend/main.py` (clave aditiva `price_change`)
- Test: `backend/tests/test_day_change.py`

**Interfaces:**
- Produces: `price_history.day_change(frame: Optional[pd.DataFrame], price: Optional[float]) -> Dict` → `{status, prev_close, change, change_pct, session, reason}`. La última fila del frame es la sesión del precio aunque su `close` sea NaN (caso XOM, docstring de `normalize`); `prev_close` es el `close` (sin ajustar) de la sesión anterior; `change = price − prev_close`, `change_pct = price / prev_close − 1`.

- [ ] **Step 1: Test que falla**

```python
import math
import pandas as pd
import price_history as ph


def _f(closes):
    idx = pd.to_datetime([f"2026-10-{d:02d}" for d in range(13, 13 + len(closes))])
    return pd.DataFrame({"close": closes, "adj_close": closes, "volume": [1.0] * len(closes),
                         "dividend": [0.0] * len(closes), "split": [0.0] * len(closes)}, index=idx)


def test_variacion_contra_el_cierre_anterior():
    r = ph.day_change(_f([100.0, 102.0, 101.0]), 103.0)
    assert r["status"] == "ok" and r["prev_close"] == 102.0
    assert math.isclose(r["change"], 1.0) and math.isclose(r["change_pct"], 103 / 102 - 1)
    assert r["session"] == "2026-10-15"


def test_ultima_sesion_sin_cierre_cuenta_como_la_del_precio():
    r = ph.day_change(_f([100.0, 102.0, float("nan")]), 104.0)
    assert r["prev_close"] == 102.0


def test_sin_serie_o_sin_precio():
    assert ph.day_change(None, 100.0)["status"] == "sin_dato"
    assert ph.day_change(_f([100.0, 101.0]), None)["status"] == "sin_dato"
    assert ph.day_change(_f([100.0]), 100.0)["status"] == "sin_dato"
```

- [ ] **Step 2: FAIL** — `../.venv313/bin/python -m pytest tests/test_day_change.py -q`.

- [ ] **Step 3: Implementar** en `price_history.py`, junto a `dividend_events`:

```python
def day_change(frame: Optional[pd.DataFrame], price: Optional[float]) -> Dict[str, Any]:
    """Rediseño E2a: variación del precio frente al cierre de la sesión anterior. La última fila es la sesión del
    precio (puede venir sin cierre: normalize la conserva a propósito)."""
    if frame is None or price is None or len(frame) < 2:
        return {"status": "sin_dato", "prev_close": None, "change": None, "change_pct": None, "session": None,
                "reason": "sin serie de precios o sin precio" if frame is None or price is None else "una sola sesión"}
    prev = frame["close"].iloc[:-1].dropna()
    if prev.empty or not prev.iloc[-1] or prev.iloc[-1] <= 0:
        return {"status": "sin_dato", "prev_close": None, "change": None, "change_pct": None, "session": None,
                "reason": "sin cierre de la sesión anterior"}
    pc = float(prev.iloc[-1])
    return {"status": "ok", "prev_close": pc, "change": price - pc, "change_pct": price / pc - 1,
            "session": frame.index[-1].strftime("%Y-%m-%d"), "reason": None}
```
En `main.py`, junto al bloque de `market_context`: `result["price_change"] = _ph.day_change((_ph.peek(symbol) or {}).get("frame"), result.get("price"))` en su propio `try/except → _sin_dato("price_change", e)`. **Comprueba** que `peek(symbol)` devuelve el dict con `frame` (si devuelve otra forma, usa la misma vía que `market_context.build`).

- [ ] **Step 4: PASS y comprobación con el replay**

Run: `../.venv313/bin/python -m pytest tests/test_day_change.py -q` y, con el replay levantado (`tests/replay_server.py --env panel --port 8767`), `curl -s localhost:8767/api/analysis/XOM | python3 -c "import json,sys; print(json.load(sys.stdin)['price_change'])"`. Expected: `status ok` y `prev_close` igual al penúltimo `close` de `tests/fixtures/history/series/XOM.json`.

- [ ] **Step 5: Commit** — `git commit -m "E2a: variación del día frente al cierre anterior (serie de la misma sesión)"` con los archivos tocados.

---

### Task 5: Historia de 10 ejercicios

**Files:**
- Create: `backend/lib/history_10y.py`
- Modify: `backend/main.py` (clave aditiva `history_10y`), `backend/config/market.toml` (`[history] years_v2 = 10`)
- Test: `backend/tests/test_history_10y.py`

**Interfaces:**
- Consumes: `yinfo["_history_fy"]` (forma de `sec_edgar.history()`: lee en `lib/sec_edgar.py` ~922 y `lib/persistence.py::merge_history` ~58 la estructura exacta antes de escribir; el test usa esa forma).
- Produces: `history_10y.build(history_fy, currency: str, years: int) -> {status, currency, source, rows: [{year, revenue, operating_income, net_income, diluted_eps, operating_cash_flow, capex, free_cash_flow, operating_margin, net_margin, revenue_growth}], reason}` con los `years` ejercicios más recientes, del más antiguo al más reciente; `free_cash_flow = operating_cash_flow − |capex|` solo si los dos existen; márgenes sobre `revenue` > 0; `revenue_growth` frente al año anterior de la propia lista.

- [ ] **Step 1: Test que falla** — escribe `tests/test_history_10y.py` con una `history_fy` sintética de 12 años **en la forma real** (cópiala de cómo la arma `sec_edgar.history`), y comprueba: 10 filas, la primera es el año 3 de los 12, FCF = OCF − |capex|, margen neto = NI/ingresos, crecimiento del primer año calculado con el año anterior aunque no se publique, `status "ok"`; con 4 años: 4 filas y `reason` = "EDGAR trae 4 ejercicios"; con `None`: `status "sin_dato"`.

- [ ] **Step 2: FAIL**; **Step 3:** implementa `build` (función pura, sin red); en `main.py`: `result["history_10y"] = history_10y.build(yinfo.get("_history_fy"), profile.currency, cfg("market.history.years_v2"))` con su `try/except`. Si la moneda de los estados difiere de la del precio (ADR: BCS en GBP), `currency` es la de los estados (búscala donde `persistence` o `display` ya la resuelven) y la fila no se convierte: la ficha dice la moneda.

- [ ] **Step 4: PASS** y con el replay: AAPL debe dar 10 filas (FY2016–FY2025), MC.PA `sin_dato` con motivo.

- [ ] **Step 5: Commit** — `"E2a: historia de 10 ejercicios desde EDGAR (sin red adicional)"`.

---

### Task 6: Piotroski con los valores de cada criterio

**Files:**
- Modify: `backend/lib/financial_ratios.py` (`piotroski_evaluate`), `backend/main.py` (`f_criteria`, ~1288)
- Test: `backend/tests/test_piotroski_valores.py`

**Interfaces:**
- Produces: cada criterio de `piotroski_evaluate(...)["criteria"]` trae además `cur`, `prev` (float o None) y `unit` ∈ {`"pct"`, `"money"`, `"ratio"`, `"shares"`}; `result["piotroski_f"]["details"][key]` los propaga. Para `earnings_quality`, `cur` = flujo operativo y `prev` = beneficio neto (no son dos años: `compare = "ni"`); para los criterios 1 y 2, `prev` = None y `compare = "zero"`; el resto `compare = "prior_year"`.

- [ ] **Step 1: Test que falla**

```python
from financial_ratios import piotroski_evaluate

ARGS = dict(net_income=90.0, roa_current=0.25, roa_prior=0.20, operating_cash_flow=110.0,
            long_term_debt_current=80.0, long_term_debt_prior=90.0, current_ratio_current=1.1,
            current_ratio_prior=0.9, shares_current=15.0, shares_prior=16.0, gross_margin_current=0.46,
            gross_margin_prior=0.44, asset_turnover_current=1.1, asset_turnover_prior=1.0)


def test_cada_criterio_trae_sus_valores():
    c = {x["key"]: x for x in piotroski_evaluate(**ARGS)["criteria"]}
    assert (c["roa_improved"]["cur"], c["roa_improved"]["prev"], c["roa_improved"]["unit"]) == (0.25, 0.20, "pct")
    assert (c["earnings_quality"]["cur"], c["earnings_quality"]["prev"], c["earnings_quality"]["compare"]) == (110.0, 90.0, "ni")
    assert c["roa_positive"]["prev"] is None and c["roa_positive"]["compare"] == "zero"
    assert c["no_dilution"]["unit"] == "shares" and c["debt_reduced"]["unit"] == "money"


def test_estados_y_puntuacion_no_cambian():
    r = piotroski_evaluate(**ARGS)
    assert r["score"] == 9 and all(x["state"] == "cumple" for x in r["criteria"])
```

- [ ] **Step 2: FAIL**; **Step 3:** cambia `add(key, state, detail)` por `add(key, state, detail, cur=None, prev=None, unit=None, compare="prior_year")` que guarde esas claves, y pasa los valores en cada llamada (en `cmp`, `cur`/`prev` ya son los argumentos). Unidades: ROA y márgenes `pct`; CFO, beneficio y deuda `money`; current ratio y rotación `ratio`; acciones `shares`. En `main.py`, `f_criteria` añade `"cur": c.get("cur"), "prev": c.get("prev"), "unit": c.get("unit"), "compare": c.get("compare")`.

- [ ] **Step 4: PASS**, y `../.venv313/bin/python -m pytest tests/test_smoke.py -q` sigue en verde (los estados y la puntuación son los mismos).

- [ ] **Step 5: Commit** — `"E2a: Piotroski con el valor actual y el de comparación de cada criterio"`.

---

### Task 7: Escenarios del usuario con el mismo DCF del motor

**Files:**
- Create: `backend/lib/scenario.py`
- Modify: `backend/config/valuation.toml` (+`[scenario]`), `backend/main.py` (clave aditiva `scenario_inputs`; `POST /api/v2/scenario`)
- Test: `backend/tests/test_scenario.py`

**Interfaces:**
- Produces:
  - `result["scenario_inputs"]` = `{fcf, shares_outstanding, net_debt, base: {high_growth_rate, high_growth_years, transition_years, terminal_growth, discount_rate, decay_type}, price, currency}` — exactamente los argumentos con los que el motor llamó a `dcf_multi_stage` dentro de `dcf_multi_stage_dynamic` (léelos de `dcf_result["inputs"]`; abre `financial_ratios.py` ~1274 para ver qué guarda `inputs` y, si falta alguno, añádelo allí **sin cambiar el cálculo**). `None` si el DCF no es significativo (con `reason`).
  - `scenario.run(inputs: dict, assumptions: dict) -> {status, fair_value, upside, assumptions_used, clamped: [campos recortados], reason}`; `assumptions` puede traer cualquier subconjunto de `base`; lo que falta se toma de `base`; cada valor se recorta a `[scenario]` y `terminal_growth < discount_rate − margen`.
  - `POST /api/v2/scenario` con cuerpo `{"inputs": <scenario_inputs>, "assumptions": {...}}` → la salida de `scenario.run`. Sin estado: no recalcula el análisis.

- [ ] **Step 1: Config** `backend/config/valuation.toml`:

```toml
[scenario]   # Rediseño E2a: límites de los supuestos que el usuario puede mover (no cambian el veredicto)
growth_min = -0.10
growth_max = 0.30            # el mismo tope que aplica el DCF del motor (growth_cap)
discount_min = 0.05
discount_max = 0.16
terminal_min = 0.0
terminal_max = 0.03
terminal_gap_min = 0.02      # el terminal queda al menos 2 pp por debajo de la tasa de descuento
years_min = 3
years_max = 15
```
(Si `growth_cap` del motor no es 0.30, usa su valor: `grep -rn growth_cap backend/config`.)

- [ ] **Step 2: Test que falla `backend/tests/test_scenario.py`**

```python
import glob, json
import pytest
import scenario


@pytest.mark.parametrize("path", sorted(glob.glob("tests/golden/panel/*.json")))
def test_con_los_supuestos_base_reproduce_el_valor_del_motor(path):
    a = json.load(open(path))
    si = a.get("scenario_inputs")
    if not si or (a.get("dcf") or {}).get("fair_value") is None:
        pytest.skip("sin DCF significativo")
    r = scenario.run(si, {})
    assert r["status"] == "ok"
    assert r["fair_value"] == pytest.approx(a["dcf"]["fair_value"], rel=1e-9)


def test_recorta_supuestos_fuera_de_rango():
    si = {"fcf": 100.0, "shares_outstanding": 10.0, "net_debt": 0.0, "price": 100.0, "currency": "USD",
          "base": {"high_growth_rate": 0.1, "high_growth_years": 5, "transition_years": 5, "terminal_growth": 0.025,
                   "discount_rate": 0.09, "decay_type": "step"}}
    r = scenario.run(si, {"high_growth_rate": 0.9, "terminal_growth": 0.085})
    assert r["status"] == "ok"
    assert r["assumptions_used"]["high_growth_rate"] == 0.30
    assert r["assumptions_used"]["terminal_growth"] <= 0.09 - 0.02
    assert set(r["clamped"]) == {"high_growth_rate", "terminal_growth"}
```
(El primer test necesita el golden regenerado con `scenario_inputs`: hasta la Task 11, ejecútalo contra las respuestas del replay en vez del golden —`requests` al 8767 o `fixture_backend` directo— y cámbialo al golden en la Task 11.)

- [ ] **Step 3: Implementar `backend/lib/scenario.py`**

```python
"""Rediseño E2a: escenario del usuario con el mismo DCF por etapas del motor. No cambia el veredicto: es una
herramienta de exploración. Los supuestos se recortan a config/valuation.toml [scenario]."""
from typing import Any, Dict

from financial_ratios import dcf_multi_stage
from settings import cfg

_KEYS = ("high_growth_rate", "high_growth_years", "transition_years", "terminal_growth", "discount_rate")


def _clamp(name: str, v: float, S: Dict[str, Any], disc: float) -> float:
    lo, hi = {"high_growth_rate": (S["growth_min"], S["growth_max"]),
              "discount_rate": (S["discount_min"], S["discount_max"]),
              "terminal_growth": (S["terminal_min"], min(S["terminal_max"], disc - S["terminal_gap_min"])),
              "high_growth_years": (S["years_min"], S["years_max"]),
              "transition_years": (0, S["years_max"])}[name]
    return min(max(v, lo), hi)


def run(inputs: Dict[str, Any], assumptions: Dict[str, Any]) -> Dict[str, Any]:
    S = cfg("valuation.scenario")
    base = dict(inputs["base"])
    used, clamped = {}, []
    disc = float(assumptions.get("discount_rate", base["discount_rate"]))
    disc = min(max(disc, S["discount_min"]), S["discount_max"])
    for k in _KEYS:
        raw = assumptions.get(k, base[k])
        v = _clamp(k, float(raw), S, disc)
        if k in assumptions and v != float(raw):
            clamped.append(k)
        used[k] = int(round(v)) if k.endswith("_years") else v
    if "discount_rate" in assumptions and disc != float(assumptions["discount_rate"]):
        clamped.append("discount_rate")
    r = dcf_multi_stage(fcf=inputs["fcf"], shares_outstanding=inputs["shares_outstanding"],
                        high_growth_rate=used["high_growth_rate"], high_growth_years=used["high_growth_years"],
                        transition_years=used["transition_years"], terminal_growth=used["terminal_growth"],
                        discount_rate=used["discount_rate"], decay_type=base.get("decay_type", "step"),
                        net_debt=inputs.get("net_debt"))
    fv = r.get("fair_value_per_share")
    if not r.get("is_valid") or fv is None or fv <= 0:
        return {"status": "sin_dato", "fair_value": None, "upside": None, "assumptions_used": used,
                "clamped": sorted(set(clamped)), "reason": r.get("invalid_reason") or "valor no significativo"}
    price = inputs.get("price")
    return {"status": "ok", "fair_value": fv, "upside": (fv / price - 1) if price else None,
            "assumptions_used": used, "clamped": sorted(set(clamped)), "reason": None}
```
Revisa la firma real de `dcf_multi_stage` (`financial_ratios.py` ~1115: `margin_of_safety_pct`, `net_debt`) y pasa los mismos valores que el motor; el test de equivalencia es el que manda. En `main.py`: construye `result["scenario_inputs"]` justo después de `result["dcf"]` (mismos `fcf`, acciones, `_net_debt` y supuestos usados), y el endpoint:
```python
@app.post("/api/v2/scenario")
def scenario_v2(body: dict):
    """Rediseño E2a: escenario del usuario (sin estado; no toca el análisis ni el veredicto)."""
    import scenario as _sc
    si = (body or {}).get("inputs")
    if not si or "base" not in si:
        raise HTTPException(status_code=422, detail="faltan los supuestos base del análisis (scenario_inputs)")
    return _sc.run(si, (body or {}).get("assumptions") or {})
```

- [ ] **Step 4: PASS** (equivalencia en todos los tickers del panel con DCF; recorte) y `curl -s -X POST localhost:8767/api/v2/scenario -H 'content-type: application/json' -d "$(curl -s localhost:8767/api/analysis/AAPL | python3 -c 'import json,sys; print(json.dumps({"inputs": json.load(sys.stdin)["scenario_inputs"], "assumptions": {"discount_rate": 0.11}}))')"` devuelve un `fair_value` menor que el del motor.

- [ ] **Step 5: Commit** — `"E2a: escenarios del usuario con el mismo DCF del motor (endpoint sin estado)"`.

---

### Task 8: Noticias completas y próximos resultados

**Files:**
- Modify: `backend/lib/market_context.py` (`news`, `build`; +`next_earnings`), `backend/config/market.toml` (`[context]`), `backend/tests/fixture_backend.py` (`replay_finnhub` para `/company-news` y `/calendar/earnings` a futuro), `backend/tests/capture_*.py` (captura nueva)
- Test: `backend/tests/test_news_v2.py`, `backend/tests/test_next_earnings.py`

**Interfaces:**
- Produces:
  - `news()["items"][i]` añade `summary` (recortado a `news_summary_chars` en límite de palabra, con "…"), `image` (solo `https://`, si no `None`), `category`, `datetime` (ISO 8601 UTC con hora), `lang` (= `news_lang`); se devuelven hasta `max(news_max, news_max_v2)` y el bloque actual de `display` sigue cortando a `news_max` (la web actual no cambia).
  - `market_context.next_earnings(symbol, filings, today) -> {status, date, kind: "anunciada"|"estimada", hour, source, basis, reason}`: primero Finnhub `earnings_calendar(symbol, hoy, hoy + next_earnings_days)` (la primera fecha ≥ hoy, con `hour` = bmo/amc si viene); si no hay, **estimada** = último 8-K de resultados (apartado 2.02 en `filings`) + `estimate_cadence_days`, solo si esa fecha cae en el futuro; si no, `sin_dato` "Sin fecha anunciada". Va en `result["market_context"]["next_earnings"]`, pedida en paralelo con las noticias dentro de `wait_timeout_s`.

- [ ] **Step 1: Config** — en `[context]` de `market.toml`:

```toml
news_max_v2 = 6                     # rediseño /v2: 6 titulares (rejilla simétrica de 2 × 3); la web actual sigue con news_max
news_summary_chars = 280            # resumen de Finnhub recortado (en límite de palabra)
news_lang = "en"                    # /company-news de Finnhub publica medios en inglés: se indica el idioma original
next_earnings_days = 120            # calendario de resultados hacia delante
estimate_cadence_days = 91          # sin fecha anunciada: último 8-K de resultados + un trimestre, marcado "estimada"
```

- [ ] **Step 2: Tests que fallan**
  - `test_news_v2.py`: con `company_news` simulado (`monkeypatch` sobre `finnhub_fallback.company_news` y `is_enabled`) que devuelve 8 noticias de AAPL con `summary` largo, `image` `http://` en una y `https://` en otras, comprueba: 6 items, resumen ≤ 281 caracteres y termina en "…" si se recortó, `image` None para la `http://`, `datetime` con hora, `lang == "en"`.
  - `test_next_earnings.py`: (a) calendario con una fecha futura → `kind "anunciada"`; (b) calendario vacío y un 8-K 2.02 de hace 40 días → `kind "estimada"` y fecha = esa + 91; (c) sin nada → `sin_dato`. Pasa `today` como argumento (sin reloj real).

- [ ] **Step 3: Implementar** según las interfaces. En `news()`: cambia el comprehension de `items` para añadir los campos y usa `C["news_max_v2"]` como corte del raw; en `display._market_block`, `"news": (…items…)[: cfg("market.context.news_max")]` para que la web actual siga igual. En `build()`: lanza `next_earnings` en el mismo pool/espera que `news` y guárdalo en `out["next_earnings"]`.

- [ ] **Step 4: Fixtures sin red.** `replay_finnhub` hoy busca la clave exacta (con fechas `from`/`to`, que cambian cada día) y devuelve `None` en noticias. Cámbialo para que `/company-news` y `/calendar/earnings` se busquen **por símbolo y ruta**, ignorando las fechas (el fixture se grabó en su fecha de captura). Captura: añade a la herramienta de captura de Finnhub (la que generó `finnhub.json`; búscala con `grep -rln "finnhub.json" backend/tests/*.py`) las llamadas `/company-news` (7 días) y `/calendar/earnings` (hoy → +120) para los 8 tickers de verificación, con la clave del Llavero en el entorno del mismo comando (`FINNHUB_API_KEY="$(security find-generic-password -s finanzer-finnhub -w)" ../.venv313/bin/python tests/<captura>.py AAPL JPM O NEE XOM PLTR RIVN BCS`), sin imprimirla. Comprueba que ningún fixture contiene la clave (`grep -rn "token=" tests/fixtures` vacío).

- [ ] **Step 5: PASS** + replay: `display.sections.market.news` de AAPL sigue con ≤ 5 items; `market_context.news.items` con hasta 6 y los campos nuevos; `market_context.next_earnings` con fecha.

- [ ] **Step 6: Commit** — `"E2a: noticias con resumen, imagen y hora; próximos resultados (anunciados o estimados)"`.

---

### Task 9: Serie de 5 años con eventos para la gráfica

**Files:**
- Modify: `backend/lib/price_history.py` (+`chart`), `backend/lib/prices_v2.py`, `backend/main.py` (`/api/v2/prices`), `backend/config/market.toml` (`[history] chart_period = "5y"`, `chart_cache_ttl_s = 21600`, `chart_cache_max = 32`), `backend/tests/capture_history.py` (+5 años), `frontend/src/v2/lib/prices.ts`
- Test: `backend/tests/test_prices_v2.py` (ampliado)

**Interfaces:**
- Produces:
  - `price_history.chart(symbol) -> {symbol, frame, reason}` con `chart_period` (5 años), caché LRU propia (`chart_cache_max` símbolos, `chart_cache_ttl_s`), mismo `FETCHER` (en tests, el replay). **No** cambia `company()` ni el periodo de 2 años del motor (la beta y las señales siguen igual).
  - `prices_v2.serialize(res, symbol)` → puntos `{t, c, a, v}` (`c` = cierre sin ajustar por dividendos, `a` = ajustado) y `events: [{t, kind: "dividend"|"split"|"earnings", value, label}]`.
  - `/api/v2/prices/{symbol}` usa `chart()` para empresa, S&P 500 y ETF del sector; añade `events` de la empresa (dividendos y splits de la serie; resultados = fechas de los 8-K 2.02 de EDGAR vía `sec_edgar.cik_for` + `submissions`, con un `Budget()` propio y sin bloquear: si EDGAR no responde, sin eventos de resultados y `events_reason`).
  - Frontend `prices.ts`: tipos con `a` y `events`.

- [ ] **Step 1: Tests que fallan** (amplía `test_prices_v2.py`): `serialize` devuelve `c` y `a` distintos cuando hay dividendos; `events` con un dividendo y un split del frame sintético; `chart()` usa `chart_period` (mock de `FETCHER` que registra el periodo pedido) y no toca la caché de `company()`.
- [ ] **Step 2: FAIL**; **Step 3:** implementa. La rentabilidad total del periodo se calcula en el cliente con `a`; la de precio con `c`.
- [ ] **Step 4: Fixtures de 5 años.** Amplía `tests/capture_history.py` con `--chart` para grabar 5 años en `tests/fixtures/history/chart/<T>.json` (los 8 tickers, `^GSPC` y los ETF de sus sectores: XLK, XLF, XLRE, XLU, XLE, XLY y el de BCS si lo tiene) y engánchalo en `fixture_backend` para `chart()`. Yahoo funciona en local; no necesita claves.
- [ ] **Step 5: PASS** y `curl -s localhost:8767/api/v2/prices/AAPL | python3 -c "import json,sys; d=json.load(sys.stdin); p=d['company']['points']; print(len(p), p[0]['t'], [e['kind'] for e in d['company']['events']][:6])"` → unas 1 250 sesiones desde hace 5 años y eventos de dividendos/resultados.
- [ ] **Step 6: Commit** — `"E2a: serie de 5 años para la gráfica, con cierre ajustado y eventos (dividendos, splits, resultados)"`.

---

### Task 10: `display.extended`, contrato y cableado mínimo en `/v2`

**Files:**
- Modify: `backend/lib/display.py` (+`_extended_block`, `build_display` lo añade como `display["extended"]`), `backend/tests/guardian.py` (`SKIP_PATHS` para lo que es dato), `frontend/src/lib/api.ts` (tipos aditivos), `frontend/src/v2/…` (cableado)
- Test: `backend/tests/test_display_extended.py`; Vitest y Playwright de `/v2` ampliados

**Interfaces:**
- Produces `display.extended`:
```ts
interface Extended {
  price_change: { status: string; value_txt: string | null; pct_txt: string | null; tone: Tone; session: string | null };
  company_profile: { status: string; rows: Array<{ key: string; label: string; value: string }>; source: string; reason: string | null };
  history_10y: { status: string; currency: string | null; source: string; reason: string | null;
                 rows: Array<{ year: number; revenue_txt: string; net_income_txt: string; fcf_txt: string;
                               operating_margin_txt: string; net_margin_txt: string; revenue_growth_txt: string }> };
  piotroski_values: Array<{ key: string; cur_txt: string | null; prev_txt: string | null; compare: "zero" | "ni" | "prior_year" }>;
  next_earnings: { status: string; date_txt: string | null; kind: "anunciada" | "estimada" | null; basis: string | null; reason: string | null };
  news: Array<{ date: string | null; datetime: string | null; source: string | null; headline: string; url: string | null;
                summary: string | null; image: string | null; lang: string | null }>;
}
```
  Todos los `*_txt` con `numfmt` (la misma presentación que el resto de la web y el PDF). `price_change.tone` es **neutro** si el cambio es 0 y `pos`/`neg` por el signo (solo describe, no valora). Ninguna frase nueva: son datos; añade `extended` a `SKIP_PATHS` del guardián **salvo** `next_earnings.basis` (frase): decláralo con `_record(..., _claim("next_earnings", field="market_context.next_earnings.date", value=…, kind=…))` y crea su predicado `_p_next_earnings` (la fecha del texto coincide con `date`) con su caso en `test_guardian_detecta.CASES`.

- [ ] **Step 1: Tests que fallan** — `test_display_extended.py` con el análisis del replay de AAPL, JPM y MC.PA (este último sin EDGAR: `company_profile.status == "sin_dato"` con motivo, `history_10y` con los años que haya y su `reason`).
- [ ] **Step 2: FAIL**; **Step 3:** implementa `_extended_block(a)` y añádelo en `build_display`. Tipos en `api.ts` (`Display.extended?: Extended`, opcional para que la web actual compile igual) y `npm run check` (contrato) en verde.
- [ ] **Step 4: Cableado mínimo en `/v2`** (nada de profundidad: eso es E3):
  1. **Cabecera:** junto al precio, la variación del día (`value_txt` y `pct_txt`, en la escala tipográfica de E1; en móvil al lado del precio de 32 px, sin romper la línea).
  2. **Capítulo 1:** la tabla de la tarjeta visual pasa a la ficha de EDGAR (`company_profile.rows`), conservando "Por qué es «…»" arriba; sin EDGAR, la tabla actual (industria, sector, país, moneda) con la nota `reason`.
  3. **Capítulo 3, gráfica:** 5 años reales en 3A/5A; marcas de eventos en la serie de la empresa (dividendo, split, resultados) con `setMarkers`/`createSeriesMarkers` de Lightweight Charts v5, discretas, en los tokens de color; tabla de rentabilidad con dos filas por serie: **precio** (`c`) y **total con dividendos** (`a`).
  4. **Capítulo 8, Actualidad:** noticias en tarjetas 2 × 3 (imagen arriba si existe con `alt` = titular; si no, tarjeta sin imagen de la misma altura), medio, fecha, resumen y la marca "En inglés"; y una cifra clave "Próximos resultados" con la fecha y "anunciada"/"estimada".
  Todas las pruebas de E1 (simetría con huecos internos, 12 px, zoom 200 %, axe) siguen en verde; añade Vitest para el formato de las tarjetas y un Playwright que compruebe 6 tarjetas de noticias con alturas iguales en AAPL (replay con las noticias capturadas).
- [ ] **Step 5: Commit** — `"E2a: display.extended en el contrato y cableado mínimo en /v2 (variación, ficha, 5 años con eventos, noticias, próximos resultados)"`.

---

### Task 11: Golden de las claves aditivas, diff explicado y PARADA

**Files:** `backend/tests/golden/**`, `docs/fiabilidad/GOLDEN_DIFF_E2A.md`, `backend/tests/test_regression.py` (retirar `E2A_ADDITIVE`)

- [ ] **Step 1:** retira la lista temporal `E2A_ADDITIVE` de `test_regression.py`.
- [ ] **Step 2:** `../.venv313/bin/python tests/diff_golden.py --env panel --full > /tmp/e2a_panel.diff` y lo mismo con `--env local`. Clasifica **cada** diferencia: clave aditiva (esperada) o cambio de valor (no permitido salvo T1–T2). Escribe la tabla en `GOLDEN_DIFF_E2A.md`: por commit, causa, tickers, campos y líneas del PDF; y una línea explícita "Cambios de veredicto: 0" (compruébalo: `quality.score`, `price_attractiveness`, niveles y confianza idénticos en los 37 + MC.PA).
- [ ] **Step 3: PARADA.** Presenta al usuario `GOLDEN_DIFF_E2A.md` (resumen en lenguaje llano: qué frases cambian y por qué, qué datos nuevos aparecen, "ningún veredicto cambia") y espera su aprobación literal. Los golden de T1–T2 ya se regeneraron en su commit para trabajar en verde, pero **no se dan por buenos** sin esta aprobación: si el usuario rechaza un cambio, se revierte su commit (código y golden juntos). **No regeneres las claves aditivas hasta tenerla.**
- [ ] **Step 4:** con la aprobación: `--regenerate --yes` en panel y local, `contract_forced.py --write`, suite completa en verde, la cita literal en `GOLDEN_DIFF_E2A.md` y commit `"E2a: golden con los datos nuevos (aditivos) — aprobado por el usuario"`.

---

### Task 12: Verificación final, capturas y registro

- [ ] **Step 1:** web actual intacta en comportamiento: `git diff rediseno/e1-sistema-historia --stat -- frontend/src/components frontend/src/app/stock frontend/src/app/page.tsx frontend/out` vacío; y el texto del PDF de los 8 tickers solo cambia en las frases de T1–T2 y la bolsa (compáralo con `diff_golden`).
- [ ] **Step 2:** suite completa del backend, `npm run check`, `test:v2`, `e2e:v2` (escritorio y móvil), axe, y las 32 capturas regeneradas en `docs/rediseno/capturas-e2a/`.
- [ ] **Step 3:** `docs/rediseno/E2A_REGISTRO.md`: commits, salidas literales de verificación, desviaciones con su motivo, lo que se ve nuevo en `/v2` por ticker, y pendientes para E2b/E3.
- [ ] **Step 4: PARADA final.** Presenta al PM (el planificador) el registro y las capturas; el PM revisa y lo lleva al usuario. Sin push ni merge.

> **Evidencia fuera de `main` (E6, 31-oct):** las capturas (`docs/rediseno/capturas-*`), `docs/fiabilidad/f8_evidencia/` y los volcados JSON de escaneo y medida de `docs/` no están en `main`. Siguen en las ramas locales del rediseño y de la fiabilidad (`rediseno/v4-f8`) y en el archivo `v4_evidencia_8e4f3952.tar.gz` de `/Users/joseestebanroa/Downloads/finanzer_next-archivo`, fuera del repositorio.
