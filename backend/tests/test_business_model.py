"""Fase 3 (T6, F3_DISENO §5): lecturas que entienden el modelo de negocio."""
import business_model as bm
from financial_ratios import score_solidez_financiera


def _st(ca, cl):
    return {"current_assets": ca, "current_liabilities": cl}


def test_structural_current_ratio_does_not_score_unless_it_worsens():
    ok = bm.current_ratio_context("Household & Personal Products", _st([70, 72, 71, 69], [100] * 4), 0.70)
    assert ok["structural"] and ok["applies"] and not ok["worsening"]
    bad = bm.current_ratio_context("Household & Personal Products", _st([50, 72, 71, 69], [100] * 4), 0.50)
    assert bad["worsening"] and not bad["applies"]
    # Fuera de la lista, un current ratio < 1 sigue siendo tensión.
    assert not bm.current_ratio_context("Drug Manufacturers - General", _st([87] * 4, [100] * 4), 0.87)["applies"]


def test_solidity_score_with_business_model():
    ctx = {"current_ratio": {"applies": True}, "altman_referential": True}
    r = score_solidez_financiera(3.5, "SAFE", 0.7, 0.5, 10.0, business_model=ctx)
    rows = {a["metric"]: a for a in r["adjustments"]}
    assert rows["Current Ratio"]["adjustment"] == 0 and "estructural" in rows["Current Ratio"]["reason"]
    assert rows["Altman Z-Score"]["adjustment"] == 0 and rows["Altman Z-Score"]["reason"].startswith("Referencial")
    assert {"Altman Z", "Current ratio"} <= set(r["coverage"]["not_significant"])


def test_altman_referential_only_where_the_model_was_not_designed():
    assert bm.altman_referential("Restaurants") and bm.altman_referential("Internet Retail")
    assert not bm.altman_referential("Household & Personal Products")     # consumo básico que fabrica
    assert bm.piotroski_caveat("Restaurants") and bm.piotroski_caveat("Steel") is None
