"""Fase 6 (bitácora: "BRK-B en base anual"): sin 4 trimestres consecutivos de Yahoo, el corte pasa al último trimestre
presentado en EDGAR (10-Q) con los doce meses que acaban en él. Sin red."""
import copy

import edgar_backup as eb


def _f(start, end, val, filed, form="10-Q", accn="q"):
    out = {"end": end, "val": val, "filed": filed, "form": form, "accn": accn}
    if start:
        out["start"] = start
    return out


def _flow(fy, ytd, prior):
    return [_f("2025-01-01", "2025-12-31", fy, "2026-02-25", "10-K", "k"),
            _f("2026-01-01", "2026-06-30", ytd, "2026-08-03", "10-Q", "q2"),
            _f("2025-01-01", "2025-06-30", prior, "2026-08-03", "10-Q", "q2")]


def _facts(with_q2_assets=True):
    assets = [_f(None, "2025-12-31", 5000, "2026-02-25", "10-K", "k")]
    if with_q2_assets:
        assets.append(_f(None, "2026-06-30", 5200, "2026-08-03", "10-Q", "q2"))
    g = {"Revenues": _flow(1000, 560, 500), "NetIncomeLoss": _flow(100, 70, 50),
         "NetCashProvidedByUsedInOperatingActivities": _flow(150, 80, 70), "Assets": assets}
    return {"facts": {"us-gaap": {c: {"units": {"USD": fs}} for c, fs in g.items()}}}


def _info():
    fy = lambda t: {"period_end": "2025-12-31", "period_type": t}
    return {"totalRevenue": 1000.0, "netIncome": 100.0, "operatingCashflow": 150.0, "totalAssets": 5000.0,
            "cash": 30.0, "trailingEps": 2.0, "currency": "USD",
            "_as_of": {"type": "fy", "date": "2025-12-31", "reason": "sin corte trimestral",
                       "fields": {"totalRevenue": fy("fy"), "netIncome": fy("fy"), "operatingCashflow": fy("fy"),
                                  "totalAssets": fy("fy_balance"), "cash": fy("fy_balance")}},
            "_fy_dates": {"inc": "2025-12-31", "bs": "2025-12-31", "cf": "2025-12-31"},
            "_ttm": {"basis": "anual", "annual_fields": {"netIncome": "x"}}}


def test_annual_cut_moves_to_the_last_10q_with_twelve_months():
    info, ed = _info(), {"status": "ok", "facts": _facts()}
    rec = eb.recut(info, ed)
    assert rec["date"] == "2026-06-30" and rec["from"] == "2025-12-31"
    eb.apply(info, ed)
    eb.recut_eps(info, rec)
    ao = info["_as_of"]
    assert ao["type"] == "ttm" and ao["date"] == "2026-06-30" and "reason" not in ao
    assert info["netIncome"] == 120 and info["totalRevenue"] == 1060 and info["totalAssets"] == 5200
    assert ao["fields"]["netIncome"]["period_end"] == "2026-06-30"
    # BPA del corte: el del ejercicio escalado por el beneficio (acciones medias del ejercicio)
    assert info["trailingEps"] == 2.4 and info["_eps_net_income"] == 120
    # lo que EDGAR no da del nuevo corte se queda con su periodo: validate lo descarta (nunca mezcla periodos)
    assert ao["fields"]["cash"]["period_end"] == "2025-12-31" and "cash" in rec["not_in_cut"]
    assert info["_ttm"]["basis"] == "ttm_edgar" and info["_ttm"]["annual_fields"] == {}


def test_without_a_complete_later_quarter_nothing_changes():
    info, ed = _info(), {"status": "ok", "facts": _facts(with_q2_assets=False)}
    before = copy.deepcopy(info)
    assert eb.recut(info, ed) is None and info == before


def test_yahoo_quarterly_cut_is_never_replaced():
    info = _info()
    info["_as_of"]["type"] = "ttm"
    assert eb.recut(info, {"status": "ok", "facts": _facts()}) is None


def test_other_currency_is_not_mixed():
    info = _info()
    info["_currency"] = {"statements": "EUR"}
    assert eb.recut(info, {"status": "ok", "facts": _facts()}) is None


def test_balance_of_the_new_cut_comes_from_yahoo_when_it_has_that_quarter():
    """BRK-B: Yahoo trae el balance del 2T-2026 aunque le falte el 3T-2025 de resultados; caja y deuda con su
    definición (EDGAR no las da con la misma)."""
    info, ed = _info(), {"status": "ok", "facts": _facts()}
    info["_latest_q_balance"] = {"date": "2026-06-30", "values": {"cash": 36.0, "totalAssets": 5210.0},
                                 "ordinary": {"commonStockEquity": 900.0}}
    rec = eb.recut(info, ed)
    eb.apply(info, ed)
    eb.recut_eps(info, rec)
    assert info["cash"] == 36.0 and info["totalAssets"] == 5210.0          # Yahoo del mismo corte: EDGAR no lo pisa
    assert info["_as_of"]["fields"]["cash"]["period_end"] == "2026-06-30" and rec["not_in_cut"] == []
    assert info["_ordinary_src"] == {"period_type": "ttm", "netIncomeToCommon": None, "commonStockEquity": 900.0}


def test_a_fresher_but_incomplete_cut_is_rejected():
    """UL: el 6-K semestral no trae la deuda ni el EBITDA; perderlos no compensa seis meses de frescura."""
    ok = eb.recut_verdict({"date": "2026-06-30", "from": "2025-12-31", "not_in_cut": ["netInterestIncome"]})
    assert ok["status"] == "aplicado"
    no = eb.recut_verdict({"date": "2026-06-30", "from": "2025-12-31", "not_in_cut": ["totalDebt", "ebitda"]})
    assert no["status"] == "descartado" and no["lost"] == ["totalDebt", "ebitda"] and "se mantiene el ejercicio" in no["reason"]
