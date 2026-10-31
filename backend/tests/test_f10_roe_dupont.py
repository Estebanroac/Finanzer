"""
F10 · N6 (revisión externa de NVDA, 28-oct-2026): la fortaleza del ROE decía «amplificado por una base de patrimonio
reducida por recompras» con un apalancamiento DuPont de 1.31. Ahora la causa la dice el DuPont: amplificado solo con el
apalancamiento por encima de `alerts.roe.amplified_leverage_min`; si no, de dónde sale (margen y rotación); sin
DuPont, sin causa. El ROE negativo con ROA positivo se atribuye al patrimonio negativo, no a recompras que no se miden.
"""
import json
import os

import pytest

import alert_interpretations as ai
from settings import cfg

HERE = os.path.dirname(__file__)


def _ctx(roe, roa=0.2, dupont=None):
    # F10 · B3: la alerta lee el ROE frente a la industria de su fila (sin ella, ninguna)
    return ai.Ctx({"roe": roe, "roa": roa}, {"dupont": dupont, "ttm_basis": "ttm", "industry_roe": 0.15},
                  sector="Technology", real_sector="Technology", archetype="MATURE")


def _dup(lev, fy=2026, margin=0.556, turnover=1.04):
    return {"current": {"fy": fy, "leverage": lev, "margin": margin, "turnover": turnover, "roe": margin * turnover * lev}}


def test_nvda_is_not_amplified():
    s = ai._roe(_ctx(0.814, dupont=_dup(1.31)))
    assert "excepcional" in s["reason"] and "recompras" not in s["detail"] and "amplificado" not in s["detail"]
    assert "No lo infla un patrimonio reducido (DuPont de FY2026: apalancamiento 1.31)" in s["detail"]
    assert "margen neto (55.6%)" in s["detail"] and "rotación de activos (1.04) de ese ejercicio" in s["detail"]


def test_aapl_is_amplified():
    s = ai._roe(_ctx(1.2, dupont=_dup(4.87, fy=2025, margin=0.24, turnover=1.1)))
    assert ("está amplificado por un patrimonio reducido frente a los activos (DuPont de FY2025: apalancamiento 4.87: "
            "los activos son 4.9 veces el patrimonio)") in s["detail"]


def test_without_dupont_no_cause_is_claimed():
    s = ai._roe(_ctx(0.6))
    assert "amplificado" not in s["detail"] and "No lo infla" not in s["detail"] and "recompras" not in s["detail"]
    assert s["detail"].endswith("15.0% del sector.")   # termina en la referencia: ninguna causa


def test_high_roe_only_says_leverage_when_it_is_there():
    t = cfg("thresholds.alerts.roe.amplified_leverage_min")
    hi = ai._roe(_ctx(0.30, dupont=_dup(t + 0.5)))
    lo = ai._roe(_ctx(0.30, dupont=_dup(t - 0.5)))
    assert "elevado" in hi["reason"] and "en parte por un patrimonio reducido" in hi["detail"]
    assert "uso muy eficiente del capital" in lo["detail"] and "patrimonio reducido" not in lo["detail"]


def test_negative_equity_is_not_blamed_on_buybacks():
    s = ai._roe(_ctx(-0.5, roa=0.12))
    assert s["kind"] == "strength" and "patrimonio negativo, no por pérdidas" in s["reason"]
    assert "recompras" not in s["reason"] + s["detail"]


@pytest.mark.parametrize("t", ["NVDA", "MU", "ASML", "V", "NVO", "AAPL", "CAT"])
def test_panel_goldens_follow_their_dupont(t):
    with open(os.path.join(HERE, "golden", "panel", f"{t}.json"), encoding="utf-8") as fh:
        a = json.load(fh)
    lev = a["quality_readings"]["dupont"]["current"]["leverage"]
    row = next(r for s in a["display"]["sections"].values() if isinstance(s, dict) for r in s.get("rows") or []
               if r.get("key") == "roe")
    s = next((x for x in a["alerts"]["strengths"] if x["reason"].startswith("ROE")), None)
    if row.get("bench") in (None, "—"):     # F10 · B3: sin referencia en la fila (AAPL tras N2), sin alerta
        assert s is None
        return
    assert ("amplificado" in s["detail"]) == (lev >= cfg("thresholds.alerts.roe.amplified_leverage_min"))
    assert "recompras" not in s["detail"]
