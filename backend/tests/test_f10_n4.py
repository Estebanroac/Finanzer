"""F10 · N4 (revisión del informe de NVIDIA): votos correlacionados y tasas base.

  · Bloque de múltiplos (financial_ratios.multiples_block): P/E, Forward P/E y PEG son una sola lectura, su media.
  · Confianza (valuation_confidence.verdict_confidence): con un DCF inverso que exige un crecimiento sostenido por menos
    de `base_rate_min_share` de las comparables, un escalón menos."""
import pytest

from financial_ratios import multiples_block
from settings import cfg
from valuation_confidence import verdict_confidence

PTS = [2, 1, 0, -1, -2]


def _dims(level="alta"):
    return {k: {"level": level, "reasons": []} for k in ("convergence", "coverage", "source", "stability")}


def test_nvda_earnings_family_is_one_vote():
    """NVDA (panel, tras N3): P/E +1, Forward P/E +1, P/FCF −1, EV/EBITDA 0. Antes: media de 4 = +0,25 → +2. Ahora:
    BPA (+1), P/FCF (−1), EV/EBITDA (0) → 0."""
    r = multiples_block({"P/E": (2, PTS), "Forward P/E": (2, PTS), "P/FCF": (-2, PTS), "EV/EBITDA": (0, PTS)},
                        "Bloque de múltiplos")
    assert r["mean"] == pytest.approx(0.0) and r["block"] == 0
    assert r["adjustment"]["block_votes"] == {"BPA (P/E, Forward P/E)": 1.0, "P/FCF": -1.0, "EV/EBITDA": 0.0}
    assert r["readings"] == {"P/E": 1.0, "Forward P/E": 1.0, "P/FCF": -1.0, "EV/EBITDA": 0.0}   # cada lectura, visible
    assert "BPA (P/E, Forward P/E): P/E +1.00, Forward P/E +1.00 → +1.00" in r["adjustment"]["reason"]
    assert "los mueve el mismo BPA" in r["adjustment"]["formula"]


def test_family_mean_and_max_from_votes():
    r = multiples_block({"P/E": (-1, PTS), "Forward P/E": (2, PTS), "PEG": (0, PTS), "P/FCF": (-2, PTS)}, "B")
    fam = (-0.5 + 1.0 + 0.0) / 3
    assert r["mean"] == pytest.approx((fam - 1.0) / 2)
    assert r["max"] == cfg("thresholds.score.valoracion.multiples_block_max_by_members")[1]       # 2 lecturas


def test_without_family_members_nothing_changes():
    r = multiples_block({"P/FCF": (2, PTS), "EV/EBITDA": (-1, PTS)}, "B")
    assert r["mean"] == pytest.approx((1.0 - 0.5) / 2) and "BPA (" not in r["adjustment"]["reason"]


def test_base_rate_below_threshold_steps_confidence_down():
    thr = cfg("thresholds.confidence.base_rate_min_share")
    c = verdict_confidence(_dims("alta"), base_rate={"share": thr / 10, "g10": 0.212, "horizon_years": 10})
    assert c["level"] == "media" and c["base_rate_step"]["from"] == "alta"
    assert any("tasas base" in r and "21.2%" in r and "(< 5%)" in r for r in c["reasons"])
    assert verdict_confidence(_dims("alta"), base_rate={"share": thr, "g10": 0.1, "horizon_years": 10})["level"] == "alta"
    assert verdict_confidence(_dims("alta"))["base_rate_step"] is None


def test_base_rate_step_from_low_stays_low():
    c = verdict_confidence(_dims("baja"), base_rate={"share": 0.0, "g10": 0.3, "horizon_years": 10})
    assert c["level"] == "baja" and any("ya estaba en baja" in r for r in c["reasons"])


@pytest.mark.parametrize("sym", ["AAPL", "MSFT", "AMZN"])
def test_base_rate_step_does_not_move_price_or_quality(sym):
    """Decisión del PM (F10 · N4, opción a): AAPL, MSFT y AMZN bajan un escalón de confianza por las tasas base, pero
    su precio y su calidad son los de la confianza previa (`contraction_basis`): con la contracción hacia 50 saldrían
    más atractivas justo las que exigen un crecimiento casi imposible. Una sola confianza a la vista."""
    import json
    import os
    from verdict import contract_quality, reprice
    a = json.load(open(os.path.join(os.path.dirname(__file__), "golden", "panel", f"{sym}.json"), encoding="utf-8"))
    c, pa, q = a["confidence"], a["price_attractiveness"], a["quality"]
    assert c["base_rate_step"] and c["contraction_basis"] != c["level"]
    assert pa["confidence"] == c["contraction_basis"]
    assert reprice(pa, c["contraction_basis"])["score"] == pa["score"]
    assert contract_quality(q, c["contraction_basis"])["score"] == q["score"]
    assert a["display"]["confidence"]["level"] == c["level"]                      # una sola confianza visible
    assert "por confianza " + c["contraction_basis"] not in json.dumps(a["display"]["summary"], ensure_ascii=False)
