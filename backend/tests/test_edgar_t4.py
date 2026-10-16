"""
Fase 2b (T4): EDGAR en el análisis: cliente con hechos XBRL (companyfacts e instancias de los filings pendientes),
respaldo del mismo corte, factor ADR de la portada del 20-F (regla B) y D7 (emisor sin estados en la SEC).
"""
import datetime as dt
import json
import os

import pytest

import fixture_backend as fb
import f2b_fixtures as ff
import edgar_backup
import sec_edgar as edgar
from currency import StatementContext, cover_official, is_adr
from valuation_confidence import official_dimension, verdict_confidence

D = dt.date.fromisoformat


# ───────────── portada del 20-F (regla B) ─────────────

@pytest.mark.parametrize("title,factor", [
    ("American Depositary Shares, each representing four 25p ordinary shares", 4),                       # BCS
    ("American Depositary Shares, each representing 5 Ordinary Shares of nominal value US$0.50 each", 5),  # HSBC
    ("American Depositary Shares representing two ordinary shareswith a nominal value of €0.07 each", 2),  # SHEL
    ("American Depositary Receipts, each representing one B Share", 1),                                    # NVO
    ("American Depositary Shares, each representing one half of one ordinary share, par value €2", 0.5),   # SNY
    ("American Depositary Shares each representedby one Equity Share, par value ₹5/- per share", 1),       # INFY
    ("American Depositary Shares, each representing eight Ordinary Shares", 8),                            # BABA
    ("each ADS represents five (5) common shares", 5),                                                     # TSM (F-6)
])
def test_parse_ratio_reads_the_cover_wording(title, factor):
    assert edgar.parse_ratio(title) == factor


def test_parse_ratio_without_a_number_is_none():
    assert edgar.parse_ratio("American Depositary Shares") is None          # TM, BP, GSK: la portada no lo dice


def _cover(*titles):
    rows = "".join(f"<tr><td>Title of 12(b) Security</td><td>{t}</td></tr><tr><td>Trading Symbol</td><td>X</td></tr>"
                   for t in titles)
    return f"<html><body><table>{rows}</table></body></html>"


def test_parse_cover_uses_only_depositary_titles():
    c = edgar.parse_cover(_cover("Ordinary Shares of 25p each",
                                 "American Depositary Shares, each representing four 25p ordinary shares",
                                 "4.375% Notes due 2028"))
    assert c["factor"] == 4 and "Depositary" in c["title"]


def test_parse_cover_with_conflicting_ratios_is_none():
    assert edgar.parse_cover(_cover("American Depositary Shares, each representing two shares",
                                    "American Depositary Shares, each representing three shares")) is None


def _ctx(implied_stmt_shares, price_shares, lookup):
    import pandas as pd
    ctx = StatementContext("ZZZ", "USD", "USD", "test", price_shares, None)
    ctx.cover_lookup = lookup
    bs = pd.DataFrame({pd.Timestamp("2025-12-31"): [implied_stmt_shares]}, index=["Ordinary Shares Number"])
    ctx.prepare_class(bs)
    return ctx


def test_rule_b_cover_factor_is_official():
    cover = {"factor": 8.0, "title": "American Depositary Shares, each representing eight Ordinary Shares",
             "form": "20-F", "date": "2026-05-20", "accn": "0000-00-000001"}
    ctx = _ctx(8.3e9, 1.0e9, lambda: cover)
    d = ctx.class_detail
    assert d["basis"] == "oficial" and d["factor"] == 8.0 and d["official"]["origin"] == "portada_20f"
    assert is_adr(d["official"])
    assert d["implied_check"]["deviation"] == pytest.approx(8.3 / 8 - 1)     # el implícito sigue comprobando


def test_rule_a_when_the_cover_does_not_say_it():
    ctx = _ctx(5.02e9, 1.0e9, lambda: None)
    assert ctx.class_detail["basis"] == "inferido" and ctx.class_detail["factor"] == 5.0


def test_same_class_does_not_wait_for_edgar():
    calls = []
    _ctx(1.0e9, 1.0e9, lambda: calls.append(1))
    assert calls == [], "una acción de la misma clase (EE. UU.) no consulta la portada"


def test_cover_official_shape():
    assert cover_official(None) is None
    o = cover_official({"factor": 2, "title": "t", "form": "20-F", "date": "2026-03-12", "accn": "a"})
    assert o["factor"] == 2.0 and o["adr"] is True and "SEC EDGAR" in o["source"]


# ───────────── instancias y periodos ─────────────

def _f(start, end, val, filed, form="10-Q", accn="a"):
    out = {"end": end, "val": val, "filed": filed, "form": form, "accn": accn}
    if start:
        out["start"] = start
    return out


def test_parse_instance_round_trip_and_skips_dimensions():
    facts = {"facts": {"ifrs-full": {"Revenue": {"units": {"GBP": [_f("2026-01-01", "2026-06-30", 100, "x")]}},
                                     "Assets": {"units": {"GBP": [_f(None, "2026-06-30", 900, "x")]}}}}}
    xml = ff.instance_xml(facts).replace(
        "</xbrli:xbrl>",
        '<xbrli:context id="dim"><xbrli:entity><xbrli:identifier scheme="s">0</xbrli:identifier><xbrli:segment>'
        '<x/></xbrli:segment></xbrli:entity><xbrli:period><xbrli:instant>2026-06-30</xbrli:instant></xbrli:period>'
        '</xbrli:context><ifrs-full:Assets contextRef="dim" unitRef="u0">1</ifrs-full:Assets></xbrli:xbrl>')
    out = edgar.parse_instance(xml.encode(), "6-K", "2026-07-28", "0000312069-26-000001")
    rev = out["facts"]["ifrs-full"]["Revenue"]["units"]["GBP"]
    assets = out["facts"]["ifrs-full"]["Assets"]["units"]["GBP"]
    assert rev == [{"start": "2026-01-01", "end": "2026-06-30", "val": 100, "filed": "2026-07-28", "form": "6-K",
                    "accn": "0000312069-26-000001"}]
    assert [a["val"] for a in assets] == [900], "el hecho con dimensiones no entra"
    assert out["accns"] == ["0000312069-26-000001"]


def test_flow_ttm_fiscal_year_plus_ytd_minus_prior_ytd():
    fs = [_f("2025-01-01", "2025-12-31", 1000, "2026-02-10", "20-F", "fy"),
          _f("2026-01-01", "2026-06-30", 600, "2026-07-28", "6-K", "h1"),
          _f("2025-01-01", "2025-06-30", 450, "2026-07-28", "6-K", "h1")]
    r = edgar.flow_ttm(fs, D("2026-06-30"), 14)
    assert r["value"] == 1150 and "acumulado" in r["how"]


def test_flow_ttm_prefers_the_fiscal_year_and_latest_filing():
    fs = [_f("2025-01-01", "2025-12-31", 1000, "2026-02-10", "10-K", "old"),
          _f("2025-01-01", "2025-12-31", 1010, "2027-02-10", "10-K", "restated")]
    r = edgar.flow_ttm(fs, D("2025-12-28"), 14)
    assert r["value"] == 1010 and r["accns"] == ["restated"]


def test_stock_at_tolerance():
    fs = [_f(None, "2026-06-28", 171, "2026-07-20")]
    assert edgar.stock_at(fs, D("2026-06-30"), 14)["value"] == 171
    assert edgar.stock_at(fs, D("2026-03-31"), 14) is None


def test_pending_filings_after_the_last_in_companyfacts():
    facts = edgar._index_facts({"facts": {"us-gaap": {"Assets": {"units": {"USD": [
        _f(None, "2026-03-31", 1, "2026-05-01", "10-Q", "0001-26-000001")]}}}}})
    fl = [{"form": "10-Q", "filingDate": "2026-08-01", "accessionNumber": "0001-26-000002", "isXBRL": True},
          {"form": "8-K", "filingDate": "2026-07-25", "accessionNumber": "0001-26-000003", "isXBRL": True},
          {"form": "10-Q", "filingDate": "2026-05-01", "accessionNumber": "0001-26-000001", "isXBRL": True}]
    assert [f["accessionNumber"] for f in edgar.pending_filings(fl, facts)] == ["0001-26-000002"]


# ───────────── cliente: degradación y D7 ─────────────

class _Fake:
    def __init__(self, routes):
        self.routes, self.calls = routes, []

    def __call__(self, url, _t):
        self.calls.append(url)
        for k, v in self.routes.items():
            if k in url:
                return v
        return None, 404


@pytest.fixture
def ua(monkeypatch):
    monkeypatch.setenv("SEC_EDGAR_USER_AGENT", "test test@example.invalid")
    edgar.reset()
    yield
    edgar.reset()


def _tickers(**t):
    return json.dumps({str(i): {"ticker": k, "cik_str": v, "title": k} for i, (k, v) in enumerate(t.items())}).encode()


def test_without_user_agent_it_is_disabled(monkeypatch):
    monkeypatch.delenv("SEC_EDGAR_USER_AGENT", raising=False)
    ed = edgar.fetch("AAPL")
    assert ed["status"] == "desactivado"
    o = edgar_backup.official_source(ed, D("2026-10-16"))
    assert o["registered"] is None and o["note"] == "verificación oficial no disponible"
    assert official_dimension(o)["level"] == "no_evaluable"


def test_no_cik_is_d7(ua, monkeypatch):
    monkeypatch.setattr(edgar, "FETCHER", _Fake({"company_tickers": (_tickers(AAPL=320193), 200)}))
    ed = edgar.fetch("MC.PA")
    o = edgar_backup.official_source(ed, D("2026-10-16"))
    assert ed["status"] == "sin_cik" and o["registered"] is False and o["note"] == edgar_backup.OFFICIAL_SOURCE_NOTICE


def test_cik_without_companyfacts_is_d7(ua, monkeypatch):
    sub = json.dumps({"filings": {"recent": {"form": ["N-CSR"], "filingDate": ["2026-01-01"],
                                             "accessionNumber": ["x"]}}}).encode()
    monkeypatch.setattr(edgar, "FETCHER", _Fake({"company_tickers": (_tickers(SPY=884394), 200),
                                                 "submissions": (sub, 200)}))
    ed = edgar.fetch("SPY")
    assert ed["status"] == "ok" and ed["facts_status"] == "sin_estados"
    assert edgar_backup.official_source(ed, D("2026-10-16"))["status"] == "sin_fuente_oficial"


def test_sec_down_is_not_the_issuers_fault(ua, monkeypatch):
    monkeypatch.setattr(edgar, "FETCHER", _Fake({"company_tickers": (None, 503)}))
    ed = edgar.fetch("AAPL")
    o = edgar_backup.official_source(ed, D("2026-10-16"))
    assert ed["status"] == "no_disponible" and o["registered"] is None
    conf = verdict_confidence({"convergence": {"level": "alta", "reasons": []},
                               "coverage": {"level": "alta", "reasons": []},
                               "source": {"level": "alta", "reasons": []},
                               "stability": {"level": "alta", "reasons": []},
                               "fuente_oficial": official_dimension(o)})
    assert conf["level"] == "alta" and conf["capped_from"] is None


def test_d7_caps_confidence_at_baja():
    dims = {k: {"level": "alta", "reasons": []} for k in ("convergence", "coverage", "source", "stability")}
    dims["fuente_oficial"] = official_dimension({"registered": False})
    conf = verdict_confidence(dims)
    assert conf["level"] == "baja" and conf["capped_from"] == "alta"
    assert any("sin fuente oficial" in r for r in conf["reasons"])


def test_stale_annual_report_is_verified_with_fy():
    facts = edgar._index_facts({"facts": {"us-gaap": {"Assets": {"units": {"USD": [
        _f(None, "2024-12-31", 1, "2025-02-01", "10-K", "k")]}}}}})
    ed = {"status": "ok", "facts_status": "ok", "cik": 1, "facts": facts, "pending_filings": [],
          "filings": [{"form": "10-K", "filingDate": "2025-02-01", "accessionNumber": "k", "isXBRL": True}]}
    o = edgar_backup.official_source(ed, D("2026-10-16"))
    assert o["status"] == "verificado_fy" and o["fy"] == "2024" and o["registered"] is True
    assert official_dimension(o)["level"] == "alta", "nota informativa, sin techo"


# ───────────── respaldo del mismo corte ─────────────

def _info(**kw):
    info = {"currency": "USD", "_as_of": {"type": "ttm", "date": "2026-06-30", "fields": {}}, "_provenance": {}}
    info.update(kw)
    return info


def _ed(concepts, unit="USD", tax="us-gaap"):
    facts = {"facts": {tax: {"Assets": {"units": {unit: [_f(None, "2025-12-31", 10, "2026-02-01", "10-K", "k")]}},
                             **concepts}}}
    return {"status": "ok", "facts_status": "ok", "facts": edgar._index_facts(facts)}


def test_backup_fills_what_yahoo_does_not_give_for_the_cut():
    ed = _ed({"RetainedEarningsAccumulatedDeficit": {"units": {"USD": [_f(None, "2026-06-28", 171, "2026-07-20")]}}})
    info = _info(retainedEarnings=None)
    log = edgar_backup.apply(info, ed)
    assert info["retainedEarnings"] == 171
    assert info["_provenance"]["retainedEarnings"]["source"] == "sec_edgar"
    assert info["_as_of"]["fields"]["retainedEarnings"] == {"period_end": "2026-06-30", "period_type": "balance",
                                                            "source": "sec_edgar"}
    assert [x["field"] for x in log["cut"]] == ["retainedEarnings"]


def test_backup_never_replaces_yahoo_of_the_same_cut():
    ed = _ed({"RetainedEarningsAccumulatedDeficit": {"units": {"USD": [_f(None, "2026-06-28", 171, "2026-07-20")]}}})
    info = _info(retainedEarnings=150)
    info["_as_of"]["fields"]["retainedEarnings"] = {"period_end": "2026-06-30", "period_type": "balance"}
    assert edgar_backup.apply(info, ed)["cut"] == [] and info["retainedEarnings"] == 150


def test_backup_replaces_a_field_of_another_period():
    ed = _ed({"PaymentsOfDividends": {"units": {"USD": [
        _f("2025-01-01", "2025-12-31", 100, "2026-02-01", "10-K", "k"),
        _f("2026-01-01", "2026-06-30", 60, "2026-07-30", "10-Q", "q"),
        _f("2025-01-01", "2025-06-30", 50, "2026-07-30", "10-Q", "q")]}}})
    info = _info(dividendsPaid=-90)
    info["_as_of"]["fields"]["dividendsPaid"] = {"period_end": "2025-12-31", "period_type": "fy"}
    edgar_backup.apply(info, ed)
    assert info["dividendsPaid"] == -110, "pago en positivo en XBRL; salida de caja en Yahoo"


def test_bank_operating_income_waits_for_phase_3():
    ed = _ed({"OperatingIncomeLoss": {"units": {"USD": [_f("2025-07-01", "2026-06-30", 5, "2026-07-30", "10-K")]}}})
    info = _info(operatingIncome=None, sector="Financial Services", industry="Banks - Diversified")
    log = edgar_backup.apply(info, ed)
    assert info["operatingIncome"] is None
    assert any("EBIT bancario" in x["reason"] for x in log["skipped"])


def test_backup_does_not_mix_currencies():
    ed = _ed({}, unit="GBP", tax="ifrs-full")
    info = _info(retainedEarnings=None, _currency={"statements": "USD"})
    log = edgar_backup.apply(info, ed)
    assert log["cut"] == [] and "no se mezclan" in log["reason"]


def test_fy_rows_fill_only_the_years_the_analysis_uses():
    ed = _ed({"Liabilities": {"units": {"USD": [_f(None, f"{y}-12-31", y, f"{y + 1}-02-01", "10-K", str(y))
                                                for y in range(2020, 2026)]}}})
    st = {"bs_ends": [f"{y}-12-31" for y in (2025, 2024, 2023, 2022, 2021)], "total_liabilities": []}
    info = _info(_statements_fy=st)
    edgar_backup.apply(info, ed)
    assert st["total_liabilities"] == [2025, 2024, 2023, 2022, None]


# ───────────── replay del panel ─────────────

needs_panel = pytest.mark.skipif(not fb.panel_available() or not ff.available(), reason="sin fixtures del panel")


def _run(sym, env="panel", **env_overrides):
    with fb.replay(fb.fixtures_dir(env)) as store:
        for k, v in env_overrides.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        return fb.run_analysis(sym, store)


@needs_panel
def test_jnj_altman_comes_back_with_edgar_retained_earnings():
    a = _run("JNJ")
    assert a["altman_z"]["z_score"] is not None
    assert a["data_provenance"]["fields"]["retainedEarnings"]["source"] == "sec_edgar"


@needs_panel
def test_mc_pa_is_d7():
    a = _run("MC.PA")
    assert a["data_provenance"]["official_source"]["registered"] is False
    assert a["confidence"]["level"] == "baja"
    assert edgar_backup.OFFICIAL_SOURCE_NOTICE in a["display"]["cover"]["data_notices"]
    assert a["display"]["cover"]["official_source_badge"]["label"] == "Sin fuente oficial"
    assert any(i["label"] == "Fuente oficial" and i["text"].startswith("no.") for i in a["display"]["annex"]["items"])


@needs_panel
def test_without_user_agent_the_analysis_has_no_cap():
    a = _run("MC.PA", SEC_EDGAR_USER_AGENT=None)
    o = a["data_provenance"]["official_source"]
    assert o["registered"] is None and o["note"] == "verificación oficial no disponible"
    assert a["confidence"]["dimensions"]["fuente_oficial"]["level"] == "no_evaluable"
    assert not any("fuente oficial" in r for r in a["confidence"]["reasons"])


@needs_panel
def test_tm_annual_statements_drop_the_empty_interim_columns():
    import yf_adapter
    with fb.replay(fb.fixtures_dir("panel")) as store:
        store.current = "TM"
        st = yf_adapter.get_ticker_info("TM")["_statements_fy"]
    assert st["inc_ends"][:2] == ["2026-03-31", "2025-03-31"] and st["revenue"][1] is not None
