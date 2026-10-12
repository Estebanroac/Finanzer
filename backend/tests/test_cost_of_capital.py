"""Etapa 8: WACC real, inputs del DCF, fiabilidad, DCF en el score y confianza."""
import pytest

import fixture_backend as fb
import cost_of_capital as cc
from financial_ratios import dcf_multi_stage, dcf_sensitivity_analysis, score_valoracion
from settings import cfg
from valuation_confidence import (convergence, dcf_reliability, stability_dimension, source_dimension,
                                  verdict_confidence)

RF = {"value": 0.045, "source": "config", "fallback": True, "reason": "test", "as_of": None}
TAX = {"rate": 0.20, "source": "efectiva", "reason": None}
C = cfg("valuation.capm")
MRP = C["market_risk_premium"]


def _ke(raw_beta):
    return 0.045 + (C["blume_weight"] * raw_beta + C["blume_prior"]) * MRP


def _envs():
    import conftest
    return conftest.ENVS


# ─────────────────────────── WACC ───────────────────────────
def test_wacc_without_debt_is_ke():
    w = cc.wacc(beta=1.2, rf=RF, market_cap=100.0, total_debt=0.0, interest_coverage=None,
                coverage_state=None, tax=TAX)
    assert w["value"] == pytest.approx(_ke(1.2)) and w["kd"] is None
    assert w["weights"] == {"equity": 1.0, "debt": 0.0}


def test_wacc_with_debt_weights_kd_after_tax():
    w = cc.wacc(beta=1.2, rf=RF, market_cap=6e9, total_debt=3e9, interest_coverage=5.0,
                coverage_state=None, tax=TAX)
    ke, kd = _ke(1.2), 0.045 + 0.0078                     # grande, cobertura 5.0 -> A (spread ene-2026)
    assert w["rating"]["rating"] == "A" and w["kd"] == pytest.approx(kd)
    assert w["value"] == pytest.approx(2 / 3 * ke + 1 / 3 * kd * 0.8)
    assert w["value"] < ke                                 # ya no es solo el coste del equity (C4)


def test_wacc_single_clamp_range_and_default_beta():
    W = cfg("valuation.wacc")
    w = cc.wacc(beta=6.0, rf=RF, market_cap=1.0, total_debt=0.0, interest_coverage=None,
                coverage_state=None, tax=TAX)                      # β ajustada 4.35 -> Ke > 20%
    assert w["clamped"] and w["value"] == W["clamp_max"] and w["raw"] > W["clamp_max"]
    assert w["bounds"] == [W["clamp_min"], W["clamp_max"]]
    w = cc.wacc(beta=None, rf=RF, market_cap=1.0, total_debt=0.0, interest_coverage=None,
                coverage_state=None, tax=TAX)
    assert w["beta_default"] and w["ke"] == pytest.approx(0.045 + MRP)    # Blume(1.0) = 1.0
    assert cc.wacc(beta=1.0, rf=RF, market_cap=None, total_debt=1.0, interest_coverage=None,
                   coverage_state=None, tax=TAX)["value"] is None


def test_blume_adjusted_beta_and_implied_erp():
    assert (C["blume_weight"], C["blume_prior"]) == (0.67, 0.33)
    assert cc.adjusted_beta(1.61) == pytest.approx(0.67 * 1.61 + 0.33)
    assert cc.adjusted_beta(None) == pytest.approx(1.0)
    w = cc.wacc(beta=1.61, rf=RF, market_cap=1.0, total_debt=0.0, interest_coverage=None,
                coverage_state=None, tax=TAX)
    assert w["beta_raw"] == 1.61 and w["beta"] == pytest.approx(1.4087) and w["beta_method"] == "Blume"
    assert MRP == 0.042            # Damodaran, ERP implícita a 1-oct-2026 (config: fuente y fecha)


def test_synthetic_rating_spreads_damodaran_jan_2026():
    R = cfg("valuation.synthetic_rating")
    sp = dict(zip(R["ratings"], R["spreads"]))
    assert (sp["AAA"], sp["A"], sp["BBB"], sp["B-"], sp["D"]) == (0.0040, 0.0078, 0.0111, 0.0509, 0.19)
    assert list(R["large_coverage_bounds"])[:3] == [8.5, 6.5, 5.5]
    assert list(R["small_coverage_bounds"])[:3] == [12.5, 9.5, 7.5]


def test_synthetic_rating_tables_and_rule_m():
    assert cc.synthetic_rating(7.0, 10e9)["rating"] == "AA"            # grandes: 6.5-8.5
    assert cc.synthetic_rating(7.0, 1e9)["rating"] == "A"              # pequeñas: 6-7.5
    assert cc.synthetic_rating(0.1, 10e9)["rating"] == "D"
    r = cc.synthetic_rating(-5.0, 10e9, "no_significativo")
    assert r["rating"] == cfg("valuation.synthetic_rating.net_cash_rating") and "caja neta" in r["flag"]
    r = cc.synthetic_rating(-5.0, 10e9, "negativa")
    assert r["rating"] == "D" and "peor tramo" in r["flag"]
    r = cc.synthetic_rating(None, 10e9)
    assert r["rating"] == cfg("valuation.synthetic_rating.no_coverage_rating") and r["flag"]
    R = cfg("valuation.synthetic_rating")
    assert len(R["ratings"]) == len(R["spreads"]) == len(R["large_coverage_bounds"]) + 1
    assert list(R["spreads"]) == sorted(R["spreads"])


def test_effective_tax_rate_bounded_with_statutory_fallback():
    lo, hi = cfg("valuation.tax.effective_bounds")
    assert cc.effective_tax_rate(100.0, 17.0)["rate"] == pytest.approx(0.17)
    t = cc.effective_tax_rate(100.0, 5.0)
    assert t["rate"] == lo and t["bounded"] and t["raw"] == pytest.approx(0.05)
    assert cc.effective_tax_rate(100.0, 60.0)["rate"] == hi
    t = cc.effective_tax_rate(-50.0, 2.0)
    assert t["source"] == "legal" and t["rate"] == cfg("valuation.tax.statutory_rate")
    assert cc.effective_tax_rate(None, None)["source"] == "legal"


def test_risk_free_reads_tnx_cached_or_falls_back(monkeypatch):
    cc.reset_cache()
    calls = []
    monkeypatch.setattr(cc, "_fetch_risk_free", lambda: calls.append(1) or {"value": 0.0412, "as_of": "2026-10-09"})
    r = cc.risk_free(now=1000.0)
    assert (r["value"], r["source"], r["fallback"]) == (0.0412, "^TNX", False)
    cc.risk_free(now=1000.0 + 23 * 3600)
    assert len(calls) == 1                                               # caché de 24 h
    cc.risk_free(now=1000.0 + 25 * 3600)
    assert len(calls) == 2
    cc.reset_cache()

    def boom():
        raise ConnectionError("bloqueado")
    monkeypatch.setattr(cc, "_fetch_risk_free", boom)
    r = cc.risk_free()
    assert r["fallback"] and r["value"] == cfg("valuation.capm.risk_free_rate") and "ConnectionError" in r["reason"]
    monkeypatch.setattr(cc, "_fetch_risk_free", lambda: {"value": 0.9, "as_of": "x"})
    assert cc.risk_free()["fallback"]                                    # fuera de rango
    cc.reset_cache()


def test_one_wacc_everywhere(outputs_by_env):
    """El WACC mostrado es el usado: key_metrics, DCF, base del grid y spread ROIC−WACC."""
    for env in _envs():
        for sym in ("NFLX", "V", "FCX", "SNOW"):
            a = outputs_by_env(env)[sym][0]
            w = a["wacc"]["value"]
            assert a["key_metrics"]["wacc"] == w == a["dcf"]["wacc"], (env, sym)
            assert a["sensitivity"]["base_case"]["discount_rate"] == pytest.approx(w)
            assert a["key_metrics"]["roic_wacc_spread"] == pytest.approx(a["key_metrics"]["roic"] - w)
        jpm = outputs_by_env(env)["JPM"][0]
        assert jpm["wacc"]["applicable"] is False and jpm["key_metrics"]["wacc"] is None
        o = outputs_by_env(env)["O"][0]
        assert o["wacc"]["value"] is not None and o.get("dcf") is None       # REIT: WACC sin DCF


def test_roic_uses_the_wacc_tax_rate(outputs_by_env):
    a = outputs_by_env("prod")["NFLX"][0]
    t = a["tax_rate"]
    assert t["source"] == "efectiva" and a["wacc"]["tax_rate"] == t["rate"]
    assert t["rate"] == pytest.approx(1.741 / 12.723, rel=1e-3)           # provisión / BAI FY2025


def test_beta_raw_and_adjusted_exposed_and_used_by_financial(outputs_by_env):
    for env in _envs():
        a = outputs_by_env(env)["NFLX"][0]
        assert a["beta"]["raw"] == a["wacc"]["beta_raw"] and a["beta"]["adjusted"] == pytest.approx(a["wacc"]["beta"])
        jpm, pdf = outputs_by_env(env)["JPM"]
        xm = jpm["archetype_metrics"]
        assert xm["beta_adjusted"] == pytest.approx(cc.adjusted_beta(jpm["beta"]["raw"]))
        assert xm["cost_of_equity"] == pytest.approx(cfg("valuation.capm.risk_free_rate") + xm["beta_adjusted"] * MRP)
        assert "β ajustada" in fb.pdf_text(pdf)


def test_rf_fallback_marked_in_replay(outputs_by_env):
    a = outputs_by_env("prod")["NFLX"][0]
    assert a["risk_free"]["fallback"] and a["wacc"]["rf"] == cfg("valuation.capm.risk_free_rate")


# ─────────────────────────── DCF: inputs ───────────────────────────
def test_cyclical_dcf_uses_maintenance_fcf(outputs_by_env):
    for env in _envs():
        a = outputs_by_env(env)["FCX"][0]
        nz = a["dcf"]["normalized"]
        assert nz["fcf_used"] == "mantenimiento" and a["dcf"]["fcf_input"] == pytest.approx(nz["fcf_maintenance"])
        assert nz["fcf_maintenance"] > nz["fcf"]           # el normalizado incluye el capex de expansión
        assert nz["fcf_maintenance_years"] >= 3


def test_grid_trimmed_at_growth_cap_and_wacc_range():
    s = dcf_sensitivity_analysis(fcf=100.0, shares_outstanding=10.0, current_price=50.0,
                                 base_growth_rate=0.30, base_discount_rate=0.065)
    assert s["growth_rates"] == pytest.approx([0.25, 0.275, 0.30])          # sin 32.5% ni 35%
    assert s["discount_rates"] == pytest.approx([0.065, 0.075, 0.085])      # sin 4.5% ni 5.5% (< 6%)
    assert s["trimmed"]["growth"] == pytest.approx([0.325, 0.35])
    assert s["trimmed"]["discount"] == pytest.approx([0.045, 0.055])
    assert "crecimiento recortado" in s["trimmed"]["note"] and "WACC recortado" in s["trimmed"]["note"]
    assert s["base_growth_idx"] == 2 and s["discount_rates"][s["base_discount_idx"]] == pytest.approx(0.065)
    assert max(s["growth_rates"]) <= cfg("valuation.dcf.source_cap_revenue") + 1e-9
    base = dcf_multi_stage(fcf=100.0, shares_outstanding=10.0, high_growth_rate=0.30, discount_rate=0.065,
                           terminal_growth=0.025, decay_type="linear")
    assert s["base_case"]["fair_value"] == base["fair_value_per_share"]


def test_short_term_growth_below_terminal_is_kept_and_converges():
    low = dcf_multi_stage(fcf=100.0, shares_outstanding=10.0, high_growth_rate=0.016, discount_rate=0.10,
                          terminal_growth=0.025, decay_type="step")
    floor = dcf_multi_stage(fcf=100.0, shares_outstanding=10.0, high_growth_rate=0.025, discount_rate=0.10,
                            terminal_growth=0.025, decay_type="step")
    r1, r2 = low["stages"]["high_growth"]["rates"], low["stages"]["transition"]["rates"]
    assert r1[0] == pytest.approx(0.016) and r2[-1] == pytest.approx(0.025)        # converge en la etapa 2
    assert all(a <= b + 1e-12 for a, b in zip(r2, r2[1:]))
    assert low["fair_value_per_share"] < floor["fair_value_per_share"]


def test_terminal_growth_at_or_above_wacc_is_sin_dato():
    r = dcf_multi_stage(fcf=100.0, shares_outstanding=10.0, high_growth_rate=0.05, discount_rate=0.025,
                        terminal_growth=0.025)
    assert r["is_valid"] is False and r["fair_value_per_share"] is None and "g >= WACC" in r["warnings"][0]
    assert "no está definido" in r["invalid_reason"]


# ─────────────────────────── fiabilidad del DCF ───────────────────────────
def _grid(price=50.0, base_g=0.10):
    return dcf_sensitivity_analysis(fcf=100.0, shares_outstanding=10.0, current_price=price,
                                    base_growth_rate=base_g, base_discount_rate=0.10)


def _rel(price, sens=None, tv=50.0, arch="MATURE", pc=False, flags=(), src="yfinance_statements"):
    s = sens or _grid(price)
    dcf = {"fair_value": s["base_case"]["fair_value"], "value_composition": {"terminal_pct": tv}}
    return dcf_reliability(dcf=dcf, sensitivity=s, price=price, archetype=arch, possible_cyclical=pc,
                           fcf_flags=list(flags), fcf_source=src)


def test_reliability_rules():
    base = _grid()["base_case"]["fair_value"]
    assert _rel(base)["level"] == "alta"
    r = _rel(base * 10)
    assert r["level"] == "baja" and r["grid_contains_price"] is False and "no contiene el precio" in r["reasons"][0]
    assert _rel(base, tv=86.0)["level"] == "baja"
    assert _rel(base, flags=["freeCashflow: fcf_supera_ocf"])["level"] == "baja"
    assert _rel(base, src="finnhub")["level"] == "baja"
    m = _grid()["matrix"]
    corner = m[0][-1]       # mínimo del grid (menor crecimiento, mayor WACC): fuera del bloque central ±1
    assert corner < min(v for row in m[1:4] for v in row[1:4])
    r = _rel(corner)
    assert r["level"] == "media" and "fuera del caso base" in r["reasons"][0]
    assert _rel(base, arch="CYCLICAL")["level"] == "media"
    assert _rel(base, pc=True)["level"] == "media"
    assert dcf_reliability(dcf=None, sensitivity=None, price=1.0, archetype=None, possible_cyclical=False,
                           fcf_flags=[], fcf_source=None) is None


# ─────────────────────────── DCF en el score ───────────────────────────
def _val(dcf):
    return score_valoracion(pe=None, p_fcf=None, ev_ebitda=None, peg=None, archetype="MATURE", dcf=dcf)


def _dcf_row(v):
    return next((a for a in v["adjustments"] if a["metric"] == "DCF (upside)"), None)


def test_dcf_component_bounded_by_reliability():
    T = cfg("thresholds.score.valoracion")
    assert _dcf_row(_val({"upside": 0.40, "reliability": "alta"}))["adjustment"] == T["dcf_points_high"][0] == 4
    assert _dcf_row(_val({"upside": 0.40, "reliability": "media"}))["adjustment"] == T["dcf_points_medium"][0] == 2
    assert _dcf_row(_val({"upside": -0.50, "reliability": "alta"}))["adjustment"] == -4
    assert _dcf_row(_val({"upside": 0.05, "reliability": "alta"}))["adjustment"] == 0
    low = _dcf_row(_val({"upside": -0.50, "reliability": "baja", "grid_contains_price": False}))
    assert low["adjustment"] == 0
    assert low["reason"].startswith("El DCF no concilia con el precio bajo ningún supuesto razonable; "
                                    "no se usa en el score")
    v = _val({"na": "No aplica a REIT"})
    assert _dcf_row(v) is None and "DCF" in v["coverage"]["not_applicable"]
    v = _val({"missing_reason": "FCF <= 0"})
    assert "DCF" in v["coverage"]["missing"]


def test_dcf_subtracts_in_valuation(outputs_by_env):
    """Fallo 1 del spec: el DCF resta. NFLX prod (−26%, fiabilidad media) -> −1, y Valoración
    es la suma de sus ajustes (el rescate de growth no lo compensa)."""
    a = outputs_by_env("prod")["NFLX"][0]
    val = a["score"]["breakdown"]["Valoración"]
    row = _dcf_row(val)
    assert a["dcf"]["reliability"]["level"] == "media" and row["adjustment"] == -1
    assert val["score"] == min(20, 10 + sum(x["adjustment"] for x in val["adjustments"]))


def test_low_reliability_dcf_explicit_in_report(outputs_by_env):
    a, pdf = outputs_by_env("prod")["SNOW"]
    assert a["dcf"]["reliability"]["level"] == "baja" and a["dcf"]["reliability"]["grid_contains_price"] is False
    text = fb.pdf_text(pdf).replace("\n", " ")
    assert "El DCF no concilia con el precio bajo ningún supuesto razonable; no se usa en el score" in text


# ─────────────────────────── confianza del veredicto ───────────────────────────
def _m(name, s, rel=None):
    return {"method": name, "signal": s, "reliability": rel}


def test_convergence_cases():
    assert convergence([_m("DCF", -0.9), _m("múltiplos", 0.4)])["level"] == "baja"           # opuestas
    assert convergence([_m("DCF", -0.5), _m("múltiplos", -0.4)])["level"] == "alta"
    assert convergence([_m("DCF", -0.5, "baja"), _m("múltiplos", -0.4)])["level"] == "media"  # DCF no fiable
    assert convergence([_m("DCF", -0.1), _m("múltiplos", -0.9)])["level"] == "media"          # magnitudes
    assert convergence([_m("múltiplos", 0.3)])["level"] == "media"                            # un solo método


def test_verdict_confidence_weights():
    def d(level):
        return {"level": level, "reasons": [level]}
    assert verdict_confidence({"convergence": d("alta"), "coverage": d("alta"), "source": d("alta"),
                               "stability": d("alta")})["level"] == "alta"
    r = verdict_confidence({"convergence": d("baja"), "coverage": d("alta"), "source": d("media"),
                            "stability": d("alta")})
    assert r["level"] == "media" and r["limits_score"] is False and r["reasons"][0].startswith("convergencia baja")
    assert verdict_confidence({"convergence": d("baja"), "coverage": d("media"), "source": d("baja"),
                               "stability": d("baja")})["level"] == "baja"
    assert stability_dimension("CYCLICAL", {})["level"] == "baja"
    assert stability_dimension("MATURE", {"alerts": [{"code": "posible_ciclica"}]})["level"] == "media"
    s = source_dimension(input_flags=[], normalization=None, ttm={"basis": "anual"}, provenance_fields={})
    assert s["level"] == "media" and "sin TTM" in s["reasons"][0]


def test_nflx_prod_contradiction_lowers_confidence(outputs_by_env):
    """Fallo 1 del spec: múltiplos dicen barata y el DCF cara -> convergencia baja."""
    c = outputs_by_env("prod")["NFLX"][0]["confidence"]
    conv = c["dimensions"]["convergence"]
    assert conv["level"] == "baja" and "direcciones opuestas" in conv["reasons"][0]
    assert c["level"] != "alta" and c["limits_score"] is False
