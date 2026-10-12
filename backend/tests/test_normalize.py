"""Etapa 7: TTM, partidas no recurrentes, crecimiento por acción y base anómala."""
import pandas as pd
import pytest

import fixture_backend as fb
from historical_metrics import growth_rate, per_share, per_share_basis
from normalize import explicit_items, infer_peaks, normalize
from settings import cfg
from ttm import build_ttm, consecutive

B = 1e9


# ─────────────────────────── TTM ───────────────────────────
def _q(dates, rows):
    return pd.DataFrame(rows, index=pd.to_datetime(dates)).T


Q4 = ["2026-06-30", "2026-03-31", "2025-12-31", "2025-09-30", "2025-06-30"]


def test_ttm_sums_four_consecutive_quarters_and_takes_last_balance():
    inc = _q(Q4, {"Total Revenue": [12, 11, 10, 9, 8], "Net Income": [3, 2, 2, 1, 1]})
    cf = _q(Q4, {"Free Cash Flow": [1, 1, 1, 1, 1]})
    bs = _q(Q4, {"Total Assets": [100, 90, 80, 70, 60], "Stockholders Equity": [50, 49, 48, 47, 46]})
    t = build_ttm(inc, cf, bs)
    assert t["values"]["totalRevenue"] == 42 and t["values"]["netIncome"] == 8
    assert t["values"]["freeCashflow"] == 4
    assert t["values"]["totalAssets"] == 100 and t["balance_date"] == "2026-06-30"


def test_ttm_needs_consecutive_quarters_else_annual_with_reason():
    gap = ["2026-06-30", "2026-03-31", "2025-09-30", "2025-06-30"]          # falta un trimestre
    assert not consecutive(gap) and consecutive(Q4)
    t = build_ttm(_q(gap, {"Total Revenue": [1, 1, 1, 1]}), None, None)
    assert "totalRevenue" not in t["values"]
    assert t["missing"]["totalRevenue"] == "los 4 últimos trimestres no son consecutivos"
    t = build_ttm(_q(Q4, {"Total Revenue": [1, None, 1, 1, 1]}), None, None)
    assert "sin dato en alguno" in t["missing"]["totalRevenue"]


def test_prod_replay_falls_back_to_annual_with_flag(outputs_by_env):
    import conftest
    if "prod" not in conftest.ENVS:
        pytest.skip("falta el juego prod")
    for sym, (a, _) in outputs_by_env("prod").items():
        t = a["data_provenance"]["ttm"]
        assert t["basis"] == "anual" and t["ttm_fields"] == [], sym
        assert "totalRevenue" in t["annual_fields"] and t["errors"], sym


def test_local_uses_ttm(outputs_by_env):
    a = outputs_by_env("local")["NFLX"][0]
    t = a["data_provenance"]["ttm"]
    assert t["basis"] == "ttm" and t["quarters"]["inc"] == ["2026-06-30", "2026-03-31", "2025-12-31", "2025-09-30"]
    assert a["key_metrics"]["revenue"] == pytest.approx((12.56 + 12.25 + 12.051 + 11.51) * B, rel=1e-3)


# ─────────────────────────── ítems explícitos ───────────────────────────
def test_explicit_total_unusual_items_with_tax_effect():
    n = normalize(net_income=65 * B, explicit_rows={"Total Unusual Items": 4.8 * B,
                                                    "Tax Effect Of Unusual Items": 1.1 * B},
                  quarterly=None, basis="TTM")
    it = n["items"][0]
    assert it["type"] == "explicita" and it["confidence"] == "alta" and it["applied"]
    assert it["net"] == pytest.approx(3.7 * B)
    assert n["normalized_net_income"] == pytest.approx(61.3 * B)
    assert n["one_off_pct"] == pytest.approx(3.7 / 65)
    assert n["applied"] and not n["pe_unreliable"]          # explícitos: se aplican aunque sean < 10%


def test_no_double_counting_total_and_components():
    rows = {"Total Unusual Items": -0.34 * B, "Write Off": 0.47 * B, "Gain On Sale Of Security": 0.16 * B,
            "Restructuring And Mergern Acquisition": 0.05 * B}
    ex = explicit_items(rows)
    assert ex["level"] == "total_unusual_items" and ex["gross"] == pytest.approx(-0.34 * B)


def test_sign_convention_income_effect():
    """Filas "de gasto" (cargo en positivo) cambian de signo; las "de resultado" no."""
    ex = explicit_items({"Restructuring And Mergern Acquisition": 0.63 * B, "Write Off": 0.2 * B,
                         "Gain On Sale Of Ppe": 0.1 * B})
    assert ex["level"] == "componentes" and ex["gross"] == pytest.approx(-0.73 * B)
    # Special Income Charges ya es efecto sobre el beneficio; Other Special Charges no se suma aparte
    ex = explicit_items({"Special Income Charges": 1.03 * B, "Other Special Charges": -0.4 * B,
                         "Gain On Sale Of Security": -0.03 * B})
    assert ex["level"] == "special_income_charges" and ex["gross"] == pytest.approx(1.0 * B)


def test_explicit_without_tax_effect_uses_effective_rate():
    n = normalize(net_income=10 * B, explicit_rows={"Total Unusual Items": -1 * B}, quarterly=None,
                  basis="FY", tax_rate_fallback=0.2)
    assert n["items"][0]["net"] == pytest.approx(-0.8 * B)
    assert n["normalized_net_income"] == pytest.approx(10.8 * B)


# ─────────────────────────── ítems inferidos ───────────────────────────
def _quarters(nonop, op=3.0, unusual=None):
    pre = [op + x for x in nonop]
    q = {"dates": Q4[:len(nonop)], "Pretax Income": [p * B for p in pre],
         "Operating Income": [op * B] * len(nonop), "Tax Provision": [0.17 * p * B for p in pre]}
    if unusual:
        q["Total Unusual Items"] = unusual
    return q


def test_inferred_peak_detected_nflx_like():
    q = _quarters([-0.124, 2.59, -0.189, -0.139, -0.143])
    r = infer_peaks(q)
    assert [p["quarter"] for p in r["peaks"]] == ["2026-03-31"]
    assert r["peaks"][0]["gross"] == pytest.approx((2.59 + 0.141) * B, rel=1e-2)


def test_ordinary_noise_is_not_a_peak():
    assert infer_peaks(_quarters([-0.12, -0.15, -0.19, -0.14, -0.13]))["peaks"] == []


def test_quarter_with_explicit_items_is_not_inferred_again():
    q = _quarters([-0.124, 2.59, -0.189, -0.139, -0.143], unusual=[0.0, 2.6 * B, 0.0, 0.0, 0.0])
    assert infer_peaks(q)["peaks"] == []


def test_inferred_needs_history():
    r = infer_peaks(_quarters([-0.1, 2.0, -0.1]))
    assert r["available"] is False and "trimestres" in r["reason"]


def test_one_off_threshold_for_inferred_items():
    """Inferidos: normalizan solo por encima de one_off_pct y bajan la confianza."""
    q = _quarters([-0.124, 2.59, -0.189, -0.139, -0.143])
    big = normalize(net_income=13.65 * B, explicit_rows={}, quarterly=q, basis="TTM")
    assert big["applied"] and big["confidence"] == "media" and big["pe_unreliable"]
    assert big["one_off_pct"] > cfg("thresholds.normalization.one_off_pct")
    small = normalize(net_income=60 * B, explicit_rows={}, quarterly=q, basis="TTM")   # 2.3/60 < 10%
    assert small["items"][0]["applied"] is False and not small["applied"]
    assert small["normalized_net_income"] == 60 * B and not small["pe_unreliable"]


def test_nflx_breakup_fee_detected_and_pe_normalized(outputs_by_env):
    """Caso de control (RECON C1): NFLX 1T-26 +2.59B no operativo."""
    n = outputs_by_env("local")["NFLX"][0]["earnings_normalization"]
    inf = [i for i in n["items"] if i["type"] == "inferida"]
    assert len(inf) == 1 and "2026-03-31" in inf[0]["origin"] and inf[0]["applied"]
    assert n["pe_unreliable"] and n["pe_normalized"] > n["pe_reported"]
    assert n["reported_net_income"] == pytest.approx(13.65 * B, rel=1e-3)
    assert n["normalized_net_income"] == pytest.approx(11.39 * B, rel=5e-3)


def test_reit_ffo_uses_reported_income_not_normalized(outputs_by_env):
    """REIT: el FFO va sobre el beneficio REPORTADO; el normalizado no entra en él,
    así que las ganancias por venta no se restan dos veces."""
    for env in ("local", "prod"):
        a = outputs_by_env(env)["O"][0]
        n, km = a["earnings_normalization"], a["key_metrics"]
        assert n["applied"] and n["normalized_net_income"] != n["reported_net_income"]
        assert km["net_income"] == pytest.approx(n["reported_net_income"])
        assert km["p_ffo"] == pytest.approx(km["market_cap"] / km["ffo"], rel=1e-6)


# ─────────────────────────── crecimiento por acción ───────────────────────────
def test_per_share_basis_threshold():
    assert cfg("thresholds.growth.per_share_min_shares_cagr") == 0.02
    assert per_share_basis([110.0, 105.0, 100.0, 95.0])["basis"] == "por_accion"     # +5%
    assert per_share_basis([100.0, 100.0, 99.0, 98.0])["basis"] == "agregado"        # +0.7%
    assert per_share_basis([100.0, 99.0])["basis"] == "agregado"
    assert per_share([10.0, None], [2.0, 2.0]) == [5.0, None]


def test_per_share_applied_to_revenue_and_fcf(outputs_by_env):
    """SNOW: acciones +2.1% anual -> ingresos y FCF por acción; el BPA ya lo es."""
    for env in ("local", "prod"):
        a = outputs_by_env(env)["SNOW"][0]
        g = a["growth_basis"]
        assert g["basis"] == "por_accion" and g["applied_to"] == ["ingresos", "FCF"] and g["shares_cagr_3y"] > 0.02
        rev = next(x for x in a["score"]["breakdown"]["Crecimiento"]["adjustments"]
                   if x["metric"] == "Crecimiento Ingresos 3Y")
        assert "por acción" in rev["reason"]
    assert outputs_by_env("local")["NFLX"][0]["growth_basis"]["basis"] == "agregado"


# ─────────────────────────── base anómala ───────────────────────────
def test_anomalous_base_uses_loglinear():
    r = growth_rate([9.46, 6.92, 6.93, 1.62, None], 3, what="FCF")          # NFLX: 2022 deprimido
    assert r["anomalous_base"] and r["method"] == "log_lineal" and r["years_used"] == 4
    assert 0.6 < r["value"] < 0.8                                         # frente al 80% de punta a punta
    normal = growth_rate([9.46, 8.0, 7.0, 6.0], 3)
    assert normal["method"] == "cagr" and not normal["anomalous_base"]


def test_anomalous_base_with_non_positive_values_is_sin_dato():
    r = growth_rate([10.0, 8.0, 9.0, 1.0, -2.0], 3)                      # base anómala; serie con -2
    assert r["value"] is None and r["anomalous_base"] and "<= 0" in r["reason"]


def test_nflx_fcf_growth_marked_anomalous(outputs_by_env):
    import conftest
    for env in conftest.ENVS:
        a = outputs_by_env(env)["NFLX"][0]
        assert a["growth_basis"]["fcf_cagr"]["anomalous_base"] is True
        fcf = next(x for x in a["score"]["breakdown"]["Crecimiento"]["adjustments"]
                   if x["metric"] == "Crecimiento FCF 3Y")
        assert fcf["value"] == "69.8%"
