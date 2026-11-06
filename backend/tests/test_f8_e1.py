"""
F8 · E1 (auditoría externa del 26-oct-2026, §3 E1): coste del patrimonio con controles de cordura.

- beta propia solo si pasa los filtros (R² ≥ 0,20, error estándar ≤ 0,25, beta entre 0,4 y 2,5); si no, la de abajo
  hacia arriba: βU de la industria de Damodaran reapalancada con la D/E de mercado, βL = βU × [1 + (1 − t) × D/E];
- pisos del Ke: Rf + 0,5 × ERP y, con deuda, Kd + 1 pp; un solo Ke por análisis (WACC, P/B justificado, REIT);
- Rf y ERP de la misma fecha (el par de Damodaran);
- prueba de sensibilidad: si el nivel de precio cambia con Ke ± 1 pp, «dependiente de Ke» y confianza −1 escalón.
"""
import numpy as np
import pandas as pd
import pytest

import beta as B
import cost_of_capital as coc
import ke_sensitivity
import market_signals
from settings import cfg

CAPM = cfg("valuation.capm")
RF, ERP = CAPM["risk_free_rate"], CAPM["market_risk_premium"]


def _own(raw, r2, se=0.15, n=104):
    return {"status": "ok", "raw": raw, "adjusted": 0.67 * raw + 0.33, "r2": r2, "se": se, "observations": n}


# ── beta propia: filtros ──

def test_own_beta_standard_error_matches_the_ols_formula():
    rng = np.random.default_rng(7)
    idx = pd.date_range("2024-01-05", periods=106, freq="W-FRI")
    rm = rng.normal(0.002, 0.02, len(idx))
    r = 0.9 * rm + rng.normal(0, 0.02, len(idx))
    m = pd.Series(100 * np.cumprod(1 + rm), index=idx)
    c = pd.Series(100 * np.cumprod(1 + r), index=idx)
    out = market_signals.beta(c, m)
    # F10: la semana de la última sesión no entra (solo semanas completas)
    rr, mm = c.pct_change().dropna().iloc[:-1].tail(104), m.pct_change().dropna().iloc[:-1].tail(104)
    slope, icept = np.polyfit(mm, rr, 1)
    resid = rr - (slope * mm + icept)
    se = np.sqrt((resid ** 2).sum() / (len(rr) - 2) / ((mm - mm.mean()) ** 2).sum())
    assert out["raw"] == pytest.approx(slope) and out["se"] == pytest.approx(se)


@pytest.mark.parametrize("own,fails", [
    (_own(1.13, 0.305, 0.169), []),                                   # MSFT del 26-oct: pasa
    (_own(-0.44, 0.112, 0.122), ["R²", "fuera de"]),                  # AWK: R² bajo y beta negativa
    (_own(1.68, 0.296, 0.256), ["error estándar"]),                   # FCX: R² bueno, pendiente imprecisa
    (_own(2.7, 0.5, 0.2), ["fuera de"]),                              # beta fuera del rango
    ({**_own(1.0, 0.3), "se": None}, ["sin error estándar"]),          # caché antigua sin EE
])
def test_own_beta_filters(own, fails):
    got = B.own_filters(own)
    assert len(got) == len(fails) and all(any(f in g for g in got) for f in fails)


def test_awk_like_own_beta_is_discarded_and_declared():
    c = B.choose(_own(-0.4365, 0.112, 0.122), 0.6, "finnhub", "Utilities", "Utilities—Regulated Water")
    assert c["source"] == "sector" and c["bottom_up"]["damodaran"] == "Utility (Water)"
    assert c["bottom_up"]["value"] == pytest.approx(0.28)
    assert "descartada" in c["reason"] and "R²" in c["discarded"]
    assert "propia si pasa los filtros" in c["rule"]


# ── de abajo hacia arriba: reapalancar ──

def test_relever_with_market_de_and_tax():
    c = B.choose(_own(0.1, 0.01), None, None, "Utilities", "Utilities—Regulated Water")
    r = B.relever(c, debt=14e9, equity=28e9, tax=0.21, financial=False)
    assert r["value"] == pytest.approx(0.28 * (1 + 0.79 * 0.5))
    assert r["relevered"] == {"unlevered": 0.28, "de": 0.5, "de_basis": "de mercado de la empresa", "tax": 0.21}


def test_relever_without_market_cap_uses_the_industry_de():
    c = B.choose(_own(0.1, 0.01), None, None, "Utilities", "Utilities—Regulated Water")
    r = B.relever(c, debt=14e9, equity=None, tax=0.21, financial=False)
    de = cfg("betas.unlevered")["Utility (Water)"][2]
    assert r["value"] == pytest.approx(0.28 * (1 + 0.79 * de)) and "media de la industria" in r["relevered"]["de_basis"]


def test_non_comparable_capital_structure_is_not_relevered():
    """TM (panel): D/E 1,20 con su financiera cautiva frente a 0,20 de Auto & Truck: βL 2,56 sin sentido."""
    c = B.choose(_own(0.72, 0.15), None, None, "Consumer Cyclical", "Auto Manufacturers")
    r = B.relever(c, debt=1.2e11, equity=1e11, tax=0.2, financial=False)
    assert r["relevered"] is None and r["value"] == pytest.approx(cfg("betas.industries")["Auto & Truck"][1])
    assert "no comparable" in r["reason"] and r["not_comparable"]["ratio"] == 3.0
    assert B.relever(c, debt=0.5e11, equity=1e11, tax=0.2, financial=False)["relevered"] is not None


def test_financial_is_not_relevered():
    c = B.choose(_own(0.1, 0.007), None, None, "Financial Services", "Insurance—Property & Casualty")
    r = B.relever(c, debt=20e9, equity=110e9, tax=0.2, financial=True)
    assert r["value"] == pytest.approx(0.48) and r["relevered"] is None and "sin reapalancar" in r["reason"]


def test_own_and_source_betas_are_not_touched_by_relever():
    c = B.choose(_own(1.1, 0.3), 1.0, "finnhub", "Technology", "Semiconductors")
    assert B.relever(c, 1e9, 1e10, 0.2, False) is c


def test_every_mapped_industry_has_an_unlevered_row():
    inds, unl = cfg("betas.industries"), cfg("betas.unlevered")
    assert set(inds) == set(unl)
    assert all(0 < row[1] < 3 and row[2] >= 0 and 0 <= row[3] < 1 for row in unl.values())


# ── pisos del Ke y un solo Ke ──

def test_ke_floor_half_market():
    ke = coc.equity_cost(0.30, RF, None, preadjusted=True)        # XOM: CAPM Rf + 1,3 pp
    assert ke["capm"] == pytest.approx(RF + 0.30 * ERP)
    assert ke["value"] == pytest.approx(RF + 0.5 * ERP) and ke["floor"]["rule"].startswith("Rf")


def test_ke_floor_over_kd():
    kd = RF + 0.0245
    ke = coc.equity_cost(0.48, RF, kd, preadjusted=True)
    assert ke["value"] == pytest.approx(kd + 0.01) and ke["floor"]["rule"].startswith("Kd")


def test_ke_without_floor_when_capm_is_above():
    ke = coc.equity_cost(1.5, RF, RF + 0.01)
    assert ke["floor"] is None and ke["value"] == ke["capm"]


def test_wacc_uses_the_single_ke_and_keeps_ke_above_kd():
    tax = {"rate": 0.21, "source": "efectiva"}
    rf = {"value": RF, "source": "par Rf–ERP de Damodaran", "fallback": False, "as_of": CAPM["pair_as_of"]}
    w = coc.wacc(beta=-0.4365, rf=rf, market_cap=28e9, total_debt=14e9, interest_coverage=3.0,
                 coverage_state=None, tax=tax)
    assert w["ke"] >= w["kd"] + 0.01 - 1e-12 and w["ke_floor"] is not None
    ke = coc.equity_cost(1.0, RF, w["kd"])
    assert coc.wacc(beta=-0.4365, rf=rf, market_cap=28e9, total_debt=14e9, interest_coverage=3.0,
                    coverage_state=None, tax=tax, ke=ke)["ke"] == ke["value"]


def test_ke_shift_enters_the_single_ke_only_inside_its_context():
    import contextvars

    def run():
        coc.KE_SHIFT.set(0.01)
        return coc.equity_cost(1.0, RF)["value"]
    assert contextvars.copy_context().run(run) == pytest.approx(coc.equity_cost(1.0, RF)["value"] + 0.01)
    assert coc.KE_SHIFT.get() == 0.0


# ── Rf y ERP de la misma fecha ──

def test_rf_and_erp_come_from_the_same_date(monkeypatch):
    monkeypatch.setattr(coc, "risk_free", lambda now=None: {"value": 0.045, "source": "^TNX", "as_of": "2026-10-23",
                                                            "fallback": False, "reason": None})
    r = coc.capm_rates()
    assert (r["value"], r["erp"], r["as_of"]) == (RF, ERP, CAPM["pair_as_of"])
    assert r["market"]["value"] == 0.045 and "debe actualizarse" in r["reason"]
    monkeypatch.setattr(coc, "risk_free", lambda now=None: {"value": 0.0484, "source": "^TNX", "as_of": "2026-11-05",
                                                            "fallback": False, "reason": None})
    assert coc.capm_rates()["reason"] is None                 # 0,10 pp del par (5-nov): dentro del margen


def test_drift_warning_catches_a_pair_copied_wrong(monkeypatch):
    """F14 · paso 1: el 6-nov el par llevaba 5,29 % (copiado de la portada) y el ^TNX estaba al 4,84 %: 0,45 pp. Con el
    umbral de 0,5 pp no saltó; con 0,3 pp, sí."""
    capm = {**CAPM, "risk_free_rate": 0.0529}
    monkeypatch.setattr(coc, "cfg", lambda path: capm if path == "valuation.capm" else cfg(path))
    monkeypatch.setattr(coc, "risk_free", lambda now=None: {"value": 0.0484, "source": "^TNX", "as_of": "2026-11-05",
                                                            "fallback": False, "reason": None})
    assert "debe actualizarse" in coc.capm_rates()["reason"]


def test_rf_pair_without_market_reading(monkeypatch):
    monkeypatch.setattr(coc, "risk_free", lambda now=None: {"value": RF, "source": "config", "as_of": None,
                                                            "fallback": True, "reason": "sin cotización"})
    r = coc.capm_rates()
    assert r["market"] is None and r["reason"] is None and r["fallback"] is False


# ── prueba de sensibilidad ──

def _result(level="razonable", score=55, conf="alta"):
    return {"price_attractiveness": {"level": level, "score": score, "score_raw": score, "factor": 1.0},
            "confidence": {"level": conf, "reasons": []}, "cost_of_equity": {"value": 0.08},
            "quality": {"level": "sólida"}}


def _rerun(levels):
    it = iter(levels)

    def f():
        lvl, sc = next(it)
        return {"price_attractiveness": {"level": lvl, "score": sc},
                "cost_of_equity": {"value": 0.08 + coc.KE_SHIFT.get()}}
    return f


def test_sensitivity_dependent_lowers_confidence_one_step_and_reprices():
    r = _result(level="atractivo", score=70, conf="alta")
    ke_sensitivity.apply(r, _rerun([("atractivo", 75), ("razonable", 59)]))
    ks = r["ke_sensitivity"]
    assert ks["dependent"] and ks["minus"]["ke"] == pytest.approx(0.07) and ks["plus"]["ke"] == pytest.approx(0.09)
    assert r["confidence"]["level"] == "media" and r["confidence"]["ke_dependent"]["from"] == "alta"
    assert r["price_attractiveness"]["score"] == round(50 + 20 * 0.75)          # contraído con la confianza nueva
    assert "dependiente de Ke" in r["confidence"]["reasons"][-1]
    assert "coste del capital" in r["verdict"]["confidence_text"]


def test_sensitivity_stable_changes_nothing():
    r = _result()
    ke_sensitivity.apply(r, _rerun([("razonable", 58), ("razonable", 52)]))
    assert not r["ke_sensitivity"]["dependent"] and r["confidence"]["level"] == "alta" and "verdict" not in r


def test_sensitivity_already_low_stays_low_and_says_so():
    r = _result(conf="baja")
    ke_sensitivity.apply(r, _rerun([("atractivo", 66), ("razonable", 50)]))
    assert r["confidence"]["level"] == "baja" and "ya era baja" in r["confidence"]["reasons"][-1]


def test_sensitivity_failure_never_blocks():
    r = _result()

    def boom():
        raise RuntimeError("x")
    ke_sensitivity.apply(r, boom)
    assert r["ke_sensitivity"]["status"] == "sin_dato" and r["confidence"]["level"] == "alta"


# Los controles de pipeline de la auditoría (§6) sobre el replay: tests/test_f8_referencia.py.
