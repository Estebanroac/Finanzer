"""
F13 · paso 10 (revisión de 110 empresas, decisión del usuario): riesgos del sector en dos niveles, aparte y sin
puntuar (lib/sector_risks.py). Cifras del banco congelado del 5-nov-2026 (MOS, B-) y de la medida en las 543.
"""
import sector_risks as sr


def _facts(values, end="2025-12-31"):
    us = {"Assets": {"units": {"USD": [{"end": end, "val": 1e10, "form": "10-K", "filed": "2026-02-20", "accn": "a"}]}}}
    for concept, v in values.items():
        us[concept] = {"units": {"USD": [{"end": end, "val": v, "form": "10-K", "filed": "2026-02-20", "accn": "a"}]}}
    us["Revenues"] = {"units": {"USD": [{"start": "2025-01-01", "end": end, "val": 1e10, "form": "10-K",
                                         "filed": "2026-02-20", "accn": "a", "fy": 2025, "fp": "FY"}]}}
    return {"facts": {"us-gaap": us}}


MOS = {"LongTermDebtMaturitiesRepaymentsOfPrincipalInNextTwelveMonths": 43.1e6,
       "LongTermDebtMaturitiesRepaymentsOfPrincipalInYearTwo": 727.4e6, "ShortTermBorrowings": 759.9e6}


def test_debt_due_in_24_months():
    d = sr.debt_due(_facts(MOS))
    assert d["status"] == "ok" and abs(d["due_24m"] - 1530.4e6) < 1 and d["fy_end"] == "2025-12-31"


def test_refinancing_needs_both_conditions():
    """MOS: 1,53 B$ en 24 meses frente a 0,29 B$ de caja y rating B-. Con rating AA (VZ, HD, CAT) no salta."""
    d = sr.debt_due(_facts(MOS))
    out = sr.build(archetype="CYCLICAL", industry="Agricultural Inputs", country="United States", state="FL", debt=d,
                   cash=294e6, rating="B-", coverage=1.3, today="2026-09-30")
    assert [x["key"] for x in out["company"]] == ["refinanciacion"] and "B-" in out["company"][0]["text"]
    assert not sr.build(archetype="CYCLICAL", industry=None, country=None, state=None, debt=d, cash=294e6,
                        rating="AA", coverage=9.0, today="2026-09-30")["company"]
    assert not sr.build(archetype="CYCLICAL", industry=None, country=None, state=None, debt=d, cash=2e9,
                        rating="B-", coverage=1.3, today="2026-09-30")["company"]


def test_utilities_and_reits_refinance_by_design():
    """Sin la exclusión, «vence más que la caja» salía en el 49 % (EVRG, SRE: 100–200 veces la caja)."""
    d = sr.debt_due(_facts(MOS))
    for arch in ("UTILITY", "REIT", "FINANCIAL"):
        assert not sr.build(archetype=arch, industry=None, country=None, state=None, debt=d, cash=1e6, rating="BB",
                            coverage=1.0, today="2026-09-30")["company"]


def test_old_balance_is_not_read():
    d = sr.debt_due(_facts(MOS, end="2024-06-30"))
    assert not sr.build(archetype="MATURE", industry=None, country=None, state=None, debt=d, cash=1e6, rating="B",
                        coverage=1.0, today="2026-09-30")["company"]


def test_industry_risks_by_headquarters_with_their_label():
    """PCG y SRE (California): incendios; NEE (Florida): huracanes. Yahoo escribe la industria con raya o guion."""
    out = sr.build(archetype="UTILITY", industry="Utilities—Diversified", country="United States", state="CA",
                   debt=None, cash=None, rating=None, coverage=None)
    assert [x["key"] for x in out["industry"]] == ["incendios"]
    assert out["industry"][0]["label"] == sr.INDUSTRY_LABEL and "California" in out["industry"][0]["text"]
    assert [x["key"] for x in sr.build(archetype="UTILITY", industry="Utilities - Regulated Electric",
                                       country="United States", state="FL", debt=None, cash=None, rating=None,
                                       coverage=None)["industry"]] == ["huracanes"]
    # una utility del medio oeste, o una empresa de otra industria en California: nada
    assert not sr.build(archetype="UTILITY", industry="Utilities - Regulated Electric", country="United States",
                        state="MN", debt=None, cash=None, rating=None, coverage=None)["industry"]
    assert not sr.build(archetype="MATURE", industry="Consumer Electronics", country="United States", state="CA",
                        debt=None, cash=None, rating=None, coverage=None)["industry"]


def test_what_cannot_be_measured_is_said():
    assert "no se mide ni se estima" in sr.build(archetype="REIT", industry=None, country=None, state=None, debt=None,
                                                 cash=None, rating=None, coverage=None)["not_measured"]
