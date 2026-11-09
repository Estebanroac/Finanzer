"""
V4b (auditoría de información faltante, punto 2 del encargo del PM): lo que el análisis o una fuente que ya usamos
tiene y la página perdía (clase b), y los fixtures del replay recapturados (clase c).
"""
import json
import os

import pytest

import fixture_backend as fb
from settings import cfg

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.join(TESTS_DIR, "fixtures")


def _rows(a):
    return {r["key"]: r for s in ("valuation", "profitability", "solvency", "growth")
            for r in a["display"]["sections"][s]["rows"]}


@pytest.fixture(scope="module")
def panel(outputs_by_env):
    return outputs_by_env("panel")


# ─────────────── (b) el porqué de lo que no aplica llega a la fila ───────────────
@pytest.mark.parametrize("sym,key,why", [
    ("DUK", "de", "deuda neta/EBITDA"),                    # utility: D/E
    ("DUK", "current_ratio", "circulante negativo"),
    ("O", "current_ratio", "deuda a largo plazo"),         # REIT
    ("ASML", "pe", "fase del ciclo"),                      # cíclica: P/E
    ("JPM", "ev_ebitda", "depósitos y préstamos"),         # banco
    ("SNOW", "net_margin", "aún sin beneficio"),           # crecimiento sin beneficio
])
def test_a_not_applicable_row_says_why(panel, sym, key, why):
    # cierre de la 1.0: la fila del P/E de la tabla es la de la regla L1; la TTM (que la tabla de rivales lee) va aparte
    r = (panel[sym][0]["display"]["sections"]["valuation"].get("pe_ttm_row") if key == "pe" else None) \
        or _rows(panel[sym][0])[key]
    assert r["state"] == "no_aplica"
    assert r["text"] and why in r["text"], r
    # el porqué, sin repetir el «No aplica a …» de la lectura
    assert not r["text"].startswith("No aplica")


def test_every_not_applicable_row_of_the_panel_has_its_reason(panel):
    missing = [(s, r["key"]) for s, (a, _pdf) in panel.items() if "display" in a
               for r in _rows(a).values() if r["state"] == "no_aplica" and not r.get("text")]
    assert missing == []


# ─────────────── (b) la referencia de industria de D/E y cobertura llega a Solidez ───────────────
def test_solvency_de_and_coverage_carry_the_industry_reference(panel):
    """V4b (b): Damodaran publica D/E y cobertura de intereses por industria (config/industries.toml) y el análisis las
    tiene en benchmark.values, pero la tabla de Solidez las dejaba sin referencia ni brecha. La lectura no cambia (sigue
    siendo la de los umbrales del sector)."""
    seen = 0
    for sym, (a, _pdf) in panel.items():
        if "display" not in a:
            continue
        bv = (a.get("benchmark") or {}).get("values") or {}
        for key in ("de", "interest_coverage"):
            r = _rows(a).get(key)
            if not r or r["state"] != "con_dato" or r["value"] in ("Sin carga",) or r["value"].startswith("Negativa"):
                continue
            if bv.get(key):
                assert r["bench"] == f"{bv[key]:.2f}x", (sym, key, r)
                assert r["gap"] and r["gap"].endswith("%"), (sym, key, r)
                seen += 1
            else:
                assert r["bench"] in (None, "—"), (sym, key, r)
    assert seen >= 20
    # los PDF siguen con su tabla de tres columnas
    assert panel["AAPL"][0]["display"]["sections"]["solvency"]["columns"] == ["MÉTRICA", "VALOR", "LECTURA"]


# ─────────────── (b) el porqué de un crecimiento sin tasa llega al gráfico de Crecimiento ───────────────
def test_growth_bar_without_rate_says_why(panel):
    """V4b (b): con el BPA o el FCF del año base ≤ 0 (AMZN) la CAGR no está definida; la cobertura del score lo sabe
    («no significativo; el crecimiento se mide con los ingresos»), pero la barra decía «Sin dato» sin motivo."""
    bars = {b["key"]: b for b in panel["AMZN"][0]["display"]["charts"]["growth"]}
    for k in ("eps", "fcf"):
        assert bars[k]["state"] == "no_significativo", bars[k]
        assert "≤ 0" in bars[k]["text"] and "ingresos" in bars[k]["text"], bars[k]
    missing = [(s, b["key"]) for s, (a, _pdf) in panel.items() if "display" in a
               for b in a["display"]["charts"]["growth"] if b["state"] != "con_dato" and not b.get("text")]
    assert missing == []


def test_roic_wacc_card_that_does_not_apply_says_why(panel):
    """V4b (b): la tarjeta ROIC − WACC de un banco, un REIT o un pre-beneficio decía «No aplica» sin motivo. F10
    (crecimiento desde una base anómala): RIVN deja de ser pre-beneficio (su CAGR de ingresos dependía del año base
    anómalo); el pre-beneficio entra si el panel tiene alguno."""
    pre = [s for s, (a, _pdf) in panel.items() if (a.get("classification") or {}).get("archetype") == "GROWTH_PRE_PROFIT"]
    for sym in ("JPM", "AMT", *pre):
        sp = panel[sym][0]["display"]["charts"]["profitability"]["spread"]
        assert sp["state"] == "no_aplica" and sp["text"] and sp["text"].startswith("No aplica a"), (sym, sp)


# ─────────────── (c) fixtures del replay recapturados: lo que el backend real trae ───────────────
def _panel_meta():
    base = fb.fixtures_dir("panel")
    out = {}
    for sym in fb.env_tickers("panel"):
        with open(os.path.join(base, sym, "metadata.json"), encoding="utf-8") as fh:
            meta = json.load(fh)
        with open(os.path.join(base, sym, "finnhub.json"), encoding="utf-8") as fh:
            calls = json.load(fh)
        out[sym] = (meta, calls)
    return out


# Sin segmentos ni Finnhub por diseño: SPY es un ETF; MC.PA no presenta en la SEC y Finnhub gratuito no cubre París
# (403). Lo dicen sus motivos en la página (clase a).
NO_SEC = {"SPY", "MC.PA"}
NO_FINNHUB = {"SPY", "MC.PA"}
# Cotiza desde después del inicio de la ventana de 5 años (salida a bolsa): su serie empieza ese día.
LISTED_LATER = {"RIVN": "2021-11-10"}


def test_every_panel_ticker_has_segments_and_a_five_year_chart():
    import datetime as dt
    import history_fixtures as hf
    for sym, (meta, _calls) in _panel_meta().items():
        if sym not in NO_SEC:
            assert os.path.isfile(os.path.join(FIX, "segments", f"{sym}.json")), sym
        f = hf.load_frame(sym, meta["captured_at_utc"][:10], sub="chart")
        cut = dt.date.fromisoformat(meta["captured_at_utc"][:10])
        first = f.index[0].date()
        # la gráfica pide 5 años: la serie cortada en la captura los cubre (con la holgura de un fin de semana largo)
        if sym in LISTED_LATER:
            assert first.isoformat() == LISTED_LATER[sym], (sym, first)
            continue
        assert first <= cut.replace(year=cut.year - 5) + dt.timedelta(days=5), (sym, first, cut)


def test_news_and_calendar_are_what_was_known_at_capture():
    for sym, (meta, calls) in _panel_meta().items():
        paths = {c["path"]: c for c in calls}
        if sym in NO_FINNHUB:
            continue
        assert "/company-news" in paths and "/calendar/earnings" in paths, sym
        import datetime as dt
        ts = int(dt.datetime.fromisoformat(meta["captured_at_utc"]).timestamp())
        assert all(int(x.get("datetime") or 0) <= ts for x in paths["/company-news"]["response"]), sym
        day = meta["captured_at_utc"][:10]
        for e in paths["/calendar/earnings"]["response"].get("earningsCalendar") or []:
            if e["date"] > day or (e["date"] == day and e.get("hour") != "bmo"):
                assert e.get("epsActual") is None and e.get("revenueActual") is None, (sym, e)
    # las grandes no se quedan sin titulares por la ventana (Finnhub devuelve solo los más recientes de la ventana)
    news = {s: len({c["path"]: c for c in calls}["/company-news"]["response"])
            for s, (_m, calls) in _panel_meta().items() if s not in NO_FINNHUB}
    assert min(news[s] for s in ("AAPL", "MSFT", "NVDA", "AMZN", "TSM", "BRK-B")) > 0, news


def test_calendar_cut_keeps_dates_and_hides_later_actuals():
    import capture_finnhub_e2a as cap
    meta = {"captured_at_utc": "2026-10-14T20:15:00+00:00"}
    resp = {"earningsCalendar": [
        {"date": "2026-10-13", "hour": "amc", "epsActual": 1.0, "revenueActual": 9},
        {"date": "2026-10-14", "hour": "bmo", "epsActual": 2.0, "revenueActual": 9},
        {"date": "2026-10-14", "hour": "amc", "epsActual": 3.0, "revenueActual": 9},
        {"date": "2026-10-21", "hour": "", "epsActual": 4.0, "revenueActual": 9, "epsEstimate": 3.9}]}
    got = cap.calendar_until_capture(resp, meta)["earningsCalendar"]
    assert [e["epsActual"] for e in got] == [1.0, 2.0, None, None]
    assert got[3]["date"] == "2026-10-21" and got[3]["epsEstimate"] == 3.9 and got[3]["revenueActual"] is None
    assert cap.calendar_until_capture(None, meta) is None


# ─────────────── (a) con el motivo: lo que EDGAR no trae en la historia de 10 años ───────────────
@pytest.mark.parametrize("sym,year,field", [
    ("JNJ", 2025, "operating_margin"), ("DOW", 2025, "operating_margin"), ("V", 2025, "diluted_eps"),
    ("SHEL", 2025, "operating_margin"), ("NEE", 2025, "capex"), ("NEE", 2025, "fcf")])   # F8: SHEL ya tiene BPA
def test_history_row_says_why_a_figure_is_missing(panel, sym, year, field):
    """V4b: la ficha del ejercicio decía «—» sin motivo donde EDGAR (companyfacts) no trae el concepto estándar del
    dato. El motor da el porqué en `reasons` (la ficha lo pinta: presentación, E3); el texto de la cifra sigue «—»
    (la tabla del PDF es estrecha)."""
    rows = {r["year"]: r for r in panel[sym][0]["display"]["extended"]["history_10y"]["rows"]}
    r = rows[year]
    assert "EDGAR" in r["reasons"][field], r
    every = [(s, r["year"], f) for s, (a, _pdf) in panel.items() if "display" in a
             for r, raw in zip(a["display"]["extended"]["history_10y"]["rows"], a["history_10y"]["rows"])
             for f, k in (("operating_margin", "operating_income"), ("diluted_eps", "diluted_eps"), ("capex", "capex"))
             if raw.get("revenue") is not None and raw.get(k) is None and f not in r["reasons"]]
    assert every == []


# ─────────────── (b) motivos que el motor tenía y la página perdía ───────────────
def test_partial_signals_note_says_why_a_series_is_missing(panel):
    """V4b (b): MC.PA cotiza en EUR y los ETF de sector de referencia son de EE. UU.; el aviso decía «la serie del
    sector es sin dato» sin el porqué que market_context sí tenía."""
    mc = panel["MC.PA"][0]["market_context"]
    assert mc["series_status"]["sector"] != "ok" and "EUR" in mc["series_reasons"]["sector"]
    note = panel["MC.PA"][0]["display"]["sections"]["market"]["status_note"]
    assert "es sin dato" not in note and "EUR" in note, note


def test_discarded_fields_are_named_in_spanish(panel):
    """V4b: el aviso de datos descartados citaba nombres internos de Yahoo (capitalLeaseObligations, commercialPaper)."""
    import re
    for sym, (a, _pdf) in panel.items():
        for n in (a.get("display") or {}).get("cover", {}).get("data_notices") or []:
            if n.startswith("Sin dato del corte"):
                assert not re.search(r"\b[a-z]+[A-Z][A-Za-z]+\b", n), (sym, n)


def test_charts_keep_the_not_applicable_head_with_the_reason(panel):
    """V4b: la escalera de márgenes, los medidores y las barras frente a la referencia dicen «No aplica a …: porqué»
    (la fila trae la lectura y el porqué por separado)."""
    jpm = panel["JPM"][0]["display"]["charts"]
    ladder = {s["key"]: s for s in jpm["profitability"]["margin_ladder"]["steps"]}
    assert ladder["gross_margin"]["text"].startswith("No aplica a") and "depósitos" in ladder["gross_margin"]["text"]
    gauges = {g["key"]: g for g in jpm["solvency"]["gauges"]}
    assert gauges["de"]["text"].startswith("No aplica a"), gauges["de"]
    for s, (a, _pdf) in panel.items():
        ch = (a.get("display") or {}).get("charts") or {}
        items = (ch.get("profitability", {}).get("returns", []) + ch.get("profitability", {}).get("margins", [])
                 + ch.get("valuation", {}).get("multiples", []) + ch.get("solvency", {}).get("gauges", [])
                 + ch.get("profitability", {}).get("margin_ladder", {}).get("steps", []))
        for it in items:
            if it.get("state") == "no_aplica":
                assert str(it.get("text") or "").startswith("No aplica"), (s, it)


def test_no_engine_state_without_reason(panel):
    """V4b: en display, ningún «sin dato», «no aplica» o «no significativo» sin su motivo (text, reason, bench, body
    o note): el recuento de tools/auditoria_faltantes.py (motor) a cero en el panel."""
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(TESTS_DIR), "tools"))
    import auditoria_faltantes as AF
    missing = []
    for sym, (a, _pdf) in panel.items():
        found = []
        AF._walk(a.get("display") or {}, "display", found)
        missing += [(sym, p, st) for p, st, why in found if not why]
    assert missing == []


@pytest.mark.parametrize("sym,where,why", [
    ("AAPL", ("solvency", "gauges", "interest_coverage"), "otro periodo"),     # gastos financieros del corte
    ("NVO", ("solvency", "gauges", "interest_coverage"), "otro periodo"),
    ("CRWD", ("profitability", "spread", None), "no significativo"),           # ROIC n. s. → spread n. s.
    ("MC.PA", ("valuation", "multiples", "forward_pe"), "BPA estimado"),        # la fuente no da estimación
])
def test_chart_items_carry_the_reason_the_analysis_has(panel, sym, where, why):
    ch = panel[sym][0]["display"]["charts"][where[0]][where[1]]
    item = ch if where[2] is None else next(x for x in ch if x["key"] == where[2])
    assert item["state"] != "con_dato" and why in (item.get("text") or ""), item
