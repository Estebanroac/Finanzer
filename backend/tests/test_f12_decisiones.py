"""
F12 · decisiones del usuario sobre F11 (5-nov-2026).

D1: el peso de la alerta «Caída pronunciada» crece con la caída medida en la volatilidad anual realizada de la acción
(z = |caída| / volatilidad), de w a w_max, y w_max no pasa del menor peso de las advertencias de solidez financiera.
D2: el forward solo puntúa con un respaldo histórico que no salga de un año base deprimido frente a la historia larga
(historical_metrics.backing_base) y con el forward en la misma base que el P/E que puntúa (normalizado frente a
reportado, forward_basis_gap).
"""
import pytest

import alert_interpretations as ai
import financial_ratios as fr
from historical_metrics import backing_base, cagr
from settings import cfg

D = cfg("thresholds.alerts.drawdown")


def _dd(dd, vol):
    return ai._drawdown(ai.Ctx({}, {"max_drawdown_1y": dd, "realized_volatility_1y": vol},
                               sector="default", real_sector=""))


def test_drawdown_weight_grows_with_the_drop_in_its_own_volatility():
    assert _dd(-0.29, 0.30) is None                                       # por encima del piso: sin alerta
    assert _dd(-0.35, 0.50)["weight"] == D["w"]                           # z 0,7: lo que suele moverse
    assert _dd(-0.62, 0.50)["weight"] == pytest.approx(D["w"] + (1.24 - 1.0) / 0.5 * (D["w_max"] - D["w"]))
    assert _dd(-0.80, 0.40)["weight"] == D["w_max"]                       # z 2: tope
    ws = [_dd(-0.50, v)["weight"] for v in (0.80, 0.50, 0.40, 0.35, 0.30)]
    assert ws == sorted(ws)                                               # misma caída, menos volatilidad: más peso
    assert _dd(-0.62, None)["weight"] == D["w"]                           # sin volatilidad, el peso de siempre


def test_drawdown_text_says_how_unusual_the_drop_is_only_when_it_is():
    assert "1.2 veces su volatilidad anual (50%)" in _dd(-0.62, 0.50)["detail"]
    assert "volatilidad" not in _dd(-0.55, 0.79)["detail"]                # CIEN: dentro de lo que se mueve


def test_drawdown_cap_never_outranks_a_solvency_warning():
    """Las advertencias de solidez financiera (mismo grupo que la caída) pesan al menos w_max; con empate, la caída va
    detrás (último interpretador). Las de solvencia graves son banderas rojas, otro grupo."""
    A = cfg("thresholds.alerts")
    solvency = [A["liquidity"]["w_tight"], A["runway"]["w_tight"], A["coverage"]["w_tight"],
                A["leverage"]["w_high_warning"], A["credit_risk"]["w_not_measured"]]
    assert D["w_max"] <= min(solvency)
    assert ai.INTERPRETERS[-1] is ai._drawdown


def test_backing_base_flags_a_depressed_base_against_the_long_history():
    r = backing_base([10, 9, 8, 2, 7, 6, 5])                    # base 2 frente a una mediana de 7,5
    assert r["checked"] and r["anomalous"] and r["ratio"] == pytest.approx(2 / 7.5)
    assert r["value"] == pytest.approx(min(cagr(10, 8, 2), cagr(10, 5, 6)))
    assert "deprimido" in r["reason"]
    assert not backing_base([10, 9, 8, 7, 6])["anomalous"]
    short = backing_base([10, 9, 8, 2])
    assert not short["checked"] and not short["anomalous"]                # menos de 5 ejercicios: no se juzga


BASE = dict(p_fcf=None, ev_ebitda=None, peg=None, sector_pe=30.0, archetype="MATURE")


def _fwd(**kw):
    v = fr.score_valoracion(**{**BASE, **kw})
    return {x["metric"]: x for x in v["adjustments"]}["Forward P/E"]


def test_forward_on_a_different_basis_than_the_scored_pe_does_not_score():
    """NFLX (escaneo del 4-nov): P/E normalizado 22,7x, reportado 19,2x, forward 17,6x: +29 % frente al normalizado y
    +9 % frente al reportado."""
    nflx = dict(pe=22.69, forward_pe=17.60, eps_growth_3y=0.365, eps_growth_last_fy=0.276)
    x = _fwd(**nflx, pe_reported=19.19)
    assert x["adjustment"] == 0 and "bases distintas" in x["reason"] and "+9%" in x["reason"]
    assert x["implied_eps_growth_reported"] == pytest.approx(19.19 / 17.60 - 1)
    assert _fwd(**nflx, pe_reported=22.69)["adjustment"] > 0              # misma base: puntúa como antes
    assert _fwd(**nflx)["adjustment"] > 0                                 # sin reportado: como antes


def test_a_depressed_base_year_does_not_back_the_forward():
    """DIS: BPA FY2022 deprimido frente a su historia; el respaldo es el de la ventana que empieza después."""
    dis = dict(pe=25.0, forward_pe=15.87, eps_growth_3y=0.585, eps_growth_last_fy=0.60)
    bk = {"checked": True, "anomalous": True, "value": 0.10, "window": "FY2023–FY2025", "base_fy": "FY2022",
          "ratio": 0.41, "reason": "año base FY2022 deprimido: 41% de la mediana de 10 ejercicios", "for_value": 0.585}
    x = _fwd(**dis, eps_growth_backing=bk)
    assert x["credited_eps_growth"] == pytest.approx(0.10)
    assert "FY2023–FY2025, sin el año base deprimido" in x["reason"]
    assert x["adjustment"] < _fwd(**dis)["adjustment"]
    # la comprobación es de esa tasa: si el perímetro o el ciclo medio la sustituyen, no se aplica
    assert _fwd(**dis, eps_growth_backing={**bk, "for_value": 0.3})["adjustment"] == _fwd(**dis)["adjustment"]
    none = _fwd(**dis, eps_growth_backing={**bk, "value": None})
    assert none["adjustment"] == 0 and "no hay otra ventana" in none["reason"]
