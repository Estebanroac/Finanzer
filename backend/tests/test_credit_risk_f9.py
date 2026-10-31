"""
F9 · R6 (revisión externa de NU, 27-oct-2026): riesgo de crédito de un banco con fuentes gratuitas (lib/credit_risk.py,
XBRL de la SEC). NU lo etiqueta con extensiones propias: «no medido», declarado, y nunca «0 riesgos» a secas. JPM, BAC,
BCS y HSBC: medido con sus conceptos estándar. «Capitalización» pasa a «patrimonio / activos (no es capital
regulatorio)».
"""
import json
import os

import pytest

import alert_interpretations as ai
import credit_risk
import display
import financial_ratios as fr

HERE = os.path.dirname(__file__)


def _golden(env, t):
    with open(os.path.join(HERE, "golden", env, f"{t}.json"), encoding="utf-8") as fh:
        return json.load(fh)


def _facts(tax, unit, concepts):
    """companyfacts mínimo: {concepto: [(inicio, fin, valor)]} de un 10-K / 20-F (más Assets para el ejercicio)."""
    form = "10-K" if tax == "us-gaap" else "20-F"
    out = {"facts": {tax: {}}}
    for c, rows in {**concepts, "Assets": [(None, "2025-12-31", 1e12), (None, "2024-12-31", 1e12)]}.items():
        out["facts"][tax][c] = {"units": {unit: [{"start": s, "end": e, "val": v, "form": form, "filed": "2026-02-20",
                                                  "accn": "x"} for s, e, v in rows]}}
    return out


def test_banco_us_gaap_medido_con_cartera_media():
    f = _facts("us-gaap", "USD", {
        "FinancingReceivableExcludingAccruedInterestBeforeAllowanceForCreditLoss": [(None, "2025-12-31", 1000.0),
                                                                                    (None, "2024-12-31", 900.0)],
        "FinancingReceivableAllowanceForCreditLossExcludingAccruedInterest": [(None, "2025-12-31", 20.0)],
        "FinancingReceivableExcludingAccruedInterestCreditLossExpenseReversal": [("2025-01-01", "2025-12-31", 19.0)],
        "FinancingReceivableExcludingAccruedInterest90DaysOrMorePastDueStillAccruing": [(None, "2025-12-31", 5.0)],
    })
    m = credit_risk.measure(f)
    assert m["status"] == "medido" and m["loans_basis"] == "bruta" and m["average_loans"]
    assert m["cost_of_risk"] == pytest.approx(19 / 950) and m["allowance_ratio"] == pytest.approx(0.02)
    assert m["past_due_90_ratio"] == pytest.approx(0.005) and m["nonaccrual_ratio"] is None


def test_banco_ifrs_sin_provision_estandar():
    f = _facts("ifrs-full", "GBP", {
        "LoansAndAdvancesToCustomersAtAmortisedCost": [(None, "2025-12-31", 350.0)],
        "AdjustmentsForImpairmentLossesReversalOfImpairmentLossesRecognisedInProfitOrLossFinancialAssets":
            [("2025-01-01", "2025-12-31", 2.3)],
    })
    m = credit_risk.measure(f)
    assert m["status"] == "medido" and m["allowance_ratio"] is None and not m["average_loans"]
    assert "neta" in m["loans_basis"] and "activos financieros" in m["expense_scope"]
    rows = {r["key"]: r for r in display.credit_rows(m)}
    assert rows["allowance_ratio"]["state"] == "sin_dato" and "NIIF" in rows["allowance_ratio"]["text"]


def test_sin_conceptos_estandar_no_medido_y_lo_dice():
    """NU: su 20-F etiqueta el crédito con extensiones propias; companyfacts no las publica."""
    f = _facts("ifrs-full", "USD", {"LoansAndAdvancesToCustomers": [(None, "2024-12-31", 5.3e9)]})
    m = credit_risk.measure(f)
    assert m["status"] == "no_medido" and "riesgo de crédito no medido" in m["reason"]
    rows = display.credit_rows(m)
    assert [(r["value"], r["state"]) for r in rows] == [("No medido", "sin_dato")]
    assert credit_risk.measure(None)["status"] == "no_medido"


def test_banco_no_medido_lleva_la_advertencia():
    ctx = ai.Ctx({}, {"credit_risk": credit_risk.measure(None)}, sector="Financial Services", real_sector="",
                 archetype="FINANCIAL")
    s = ai._credit(ctx)
    assert s and s["kind"] == "warning" and s["reason"] == "Riesgo de crédito no medido"
    assert ai._credit(ai.Ctx({}, {"credit_risk": {"status": "medido"}}, sector="Financial Services", real_sector="",
                             archetype="FINANCIAL")) is None


@pytest.mark.parametrize("t,cost", [("JPM", 0.0083), ("BAC", 0.0049), ("BCS", 0.0066), ("HSBC", 0.0043)])
def test_bancos_del_panel_medidos(t, cost):
    a = _golden("panel", t)
    cr = a["credit_risk"]
    assert cr["status"] == "medido" and cr["cost_of_risk"] == pytest.approx(cost, abs=5e-5)
    keys = [r["key"] for r in a["display"]["sections"]["solvency"]["rows"]]
    assert "cost_of_risk" in keys and "credit_risk" not in keys
    assert a["display"]["summary"]["alert_counts"]["unmeasured"] is None


def test_solo_bancos():
    for t in ("PGR", "BRK-B", "AAPL"):
        assert "credit_risk" not in _golden("panel", t)


def test_patrimonio_sobre_activos_no_es_capital_regulatorio():
    """NU: «Capitalización 16%» era patrimonio / activos; el texto dice ahora qué es y qué no es."""
    *_x, details = fr.financial_health_score(0.04, 0.27, 16.0, 100.0, None)
    d = next(x for x in details if x["metric"] == "Equity/Assets")
    assert d["detail"].startswith("Patrimonio / activos sólido (16.0%") and "no es capital regulatorio" in d["detail"]
    assert "Capitalización" not in json.dumps(details, ensure_ascii=False)
