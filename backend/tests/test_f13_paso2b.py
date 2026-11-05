"""
F13 · paso 2b (revisión de 110 empresas, patrón 8): la deuda y la caja de una financiera cautiva que presenta su propio
10-K/10-Q (config data.edgar.captive_filers) salen de la deuda neta industrial, con el dato del mismo corte.
"""
import datetime as dt

import debt
import sec_edgar
from settings import cfg


def _facts(debt_by_date, cash_by_date, concept="DebtAndCapitalLeaseObligations"):
    def facts(d):
        return [{"end": k, "val": v, "form": "10-Q", "filed": k, "accn": f"x-{k}"} for k, v in d.items()]
    return {"facts": {"us-gaap": {
        concept: {"units": {"USD": facts(debt_by_date)}},
        "CashAndCashEquivalentsAtCarryingValue": {"units": {"USD": facts(cash_by_date)}}}}}


def test_filer_series_has_debt_and_cash_by_date(monkeypatch):
    f = _facts({"2026-06-30": 137.348e9, "2026-09-30": 139.393e9}, {"2026-06-30": 8.426e9, "2026-09-30": 8.251e9})
    monkeypatch.setattr(sec_edgar, "company_facts", lambda cik, budget: f)
    r = sec_edgar.captive_filer_debt(cfg("data.edgar.captive_filers")["F"], None)
    assert r["status"] == "ok" and r["series"]["2026-09-30"]["value"] == 139.393e9
    assert r["series"]["2026-09-30"]["cash"] == 8.251e9


def test_filer_parts_are_summed_only_when_all_are_there(monkeypatch):
    """Cat Financial: largo plazo + parte corriente + corto plazo, en la misma fecha."""
    rows = lambda v: {"units": {"USD": [{"end": "2026-09-30", "val": v, "form": "10-Q", "filed": "2026-11-04"}]}}
    f = {"facts": {"us-gaap": {"LongTermDebtNoncurrent": rows(21.55e9), "LongTermDebtCurrent": rows(8.14e9),
                               "ShortTermBorrowings": rows(4.86e9)}}}
    monkeypatch.setattr(sec_edgar, "company_facts", lambda cik, budget: f)
    r = sec_edgar.captive_filer_debt(cfg("data.edgar.captive_filers")["CAT"], None)
    assert abs(r["series"]["2026-09-30"]["value"] - 34.55e9) < 1e6
    del f["facts"]["us-gaap"]["ShortTermBorrowings"]
    assert sec_edgar.captive_filer_debt(cfg("data.edgar.captive_filers")["CAT"], None)["status"] == "sin_dato"


def test_deere_stays_declared_not_separated():
    """John Deere Capital no etiqueta un total de deuda estándar: sigue sin separarse (se declara)."""
    assert "DE" not in cfg("data.edgar.captive_filers") and "DE" in cfg("data.edgar.captive_unseparable")


def test_series_date_matching_the_cut_is_the_one_used():
    """De la serie de la filial se toma la fecha más cercana al corte de la deuda de la matriz."""
    cap = {"status": "ok", "name": "GM Financial", "cik": 804269,
           "series": {"2026-06-30": {"value": 111.7e9, "parts": {}, "form": "10-Q", "accn": "a", "cash": 4.99e9},
                      "2026-09-30": {"value": 112.9e9, "parts": {}, "form": "10-Q", "accn": "b", "cash": 4.43e9}}}
    info = {"totalDebt": 127.7e9, "cash": 24.7e9,
            "_as_of": {"date": "2026-06-30", "fields": {"totalDebt": {"period_end": "2026-06-30"}}}}
    out = debt.apply(info, {"status": "no_disponible", "captive": cap}, symbol="GM")
    c = out["components"]["captive"]
    assert c["date"] == "2026-06-30" and c["value"] == 111.7e9 and c.get("cash") == 4.99e9
