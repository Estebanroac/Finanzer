"""
F9 · R1c (decisiones del PM del 27-oct, forma continua): el BPA forward se acota al que respalda el histórico,
BPA_fwd creíble = BPA_TTM × (1 + mín(g implícito, CAGR observado del BPA a 3 años)), y la compresión puntúa con el
P/E forward creíble. Sin CAGR observable, se muestra y no puntúa, declarado. Sin parámetros nuevos ni tope fijo.
"""
import pytest

from financial_ratios import score_valoracion


def _fwd(**kw):
    base = dict(pe=17.0, p_fcf=None, ev_ebitda=None, peg=None, sector_pe=9.1, sector_forward_pe=9.1,
                forward_pe=11.0, eps_growth_3y=0.80)
    r = score_valoracion(**{**base, **kw})
    return next(x for x in r["adjustments"] if x["metric"] == "Forward P/E")


def test_nu_scores_because_the_history_grew_faster():
    """NU: 17x → 11x implica un BPA +55 %; su BPA creció más del 80 % anual: puntúa (+3)."""
    f = _fwd()
    assert f["adjustment"] == 3 and "not_scored" not in f
    assert f["implied_eps_growth"] == pytest.approx(17 / 11 - 1)


def test_implied_growth_above_history_counts_only_the_backed_part():
    """17x → 11x implica +55 %; con un histórico del +27 % anual, el forward creíble es 17 / 1,27 = 13,4x: la
    compresión (21 %) puntúa en su banda, no en la de +55 %."""
    f = _fwd(eps_growth_3y=0.27, sector_pe=15.0, sector_forward_pe=15.0)   # 13,4x fuera de la peor banda (> 19,5x)
    assert f["credible_forward_pe"] == pytest.approx(17 / 1.27) and f["value"] == "11.00x"
    assert f["adjustment"] == 2 and "not_scored" not in f
    assert f["reason"] == ("P/E mejorando (17x → 13x forward creíble); forward 11.0x (implica +55% de BPA); con el "
                           "crecimiento que respalda su histórico (+27% anual del BPA a 3 años), 13.4x")


def test_consensus_in_line_with_history_is_untouched():
    f = _fwd(eps_growth_3y=0.55)
    assert "credible_forward_pe" not in f and f["adjustment"] == 3


def test_credible_forward_in_the_worst_band_has_no_effect():
    """Con la referencia de NU (9,1x × 1,3 = 11,8x), el forward creíble de 13,4x sigue en la peor banda (Etapa 11b)."""
    f = _fwd(eps_growth_3y=0.27)
    assert f["adjustment"] == 0 and "sin efecto: el Forward P/E creíble (13.4x) sigue en la peor banda" in f["reason"]


def test_negative_history_leaves_no_compression():
    f = _fwd(eps_growth_3y=-0.07)
    assert f["adjustment"] == 0 and f["credible_forward_pe"] == pytest.approx(17 / 0.93)


def test_without_observable_history_it_does_not_score_and_says_why():
    """NU (decisión del PM): pérdida en 2022, sin CAGR del BPA a 3 años: no puntúa; el texto dice el implícito y por
    qué no hay histórico."""
    f = _fwd(eps_growth_3y=None, eps_growth_reason="BPA inicial <= 0: CAGR no definido")
    assert f["adjustment"] == 0
    assert f["not_scored"] == ("el forward implica +55%, pero no hay histórico de BPA de 3 años comparable (BPA "
                               "inicial <= 0: CAGR no definido); la compresión no puntúa")


def test_no_compression_is_untouched():
    f = _fwd(forward_pe=17.5, eps_growth_3y=None)
    assert f["adjustment"] == 0 and "not_scored" not in f
