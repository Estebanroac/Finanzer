"""Etapa 5: datos faltantes y cobertura.

Principio: un dato ausente nunca cuenta como incumplimiento ni como cero. Se
excluye, se reporta la cobertura y, si es insuficiente, el indicador se declara
no concluyente. Datos sintéticos.
"""
import pytest

import fixture_backend  # noqa: F401  (añade backend/ y lib/ al path)
from financial_ratios import piotroski_evaluate, piotroski_f_score, piotroski_level
from settings import cfg

_FULL = dict(
    net_income=100, roa_current=0.10, roa_prior=0.08, operating_cash_flow=150,
    long_term_debt_current=80, long_term_debt_prior=100,
    current_ratio_current=2.0, current_ratio_prior=1.5,
    shares_current=95, shares_prior=100,
    gross_margin_current=0.50, gross_margin_prior=0.40,
    asset_turnover_current=1.1, asset_turnover_prior=1.0,
)
_PRIORS = ("roa_prior", "long_term_debt_prior", "current_ratio_prior", "shares_prior",
           "gross_margin_prior", "asset_turnover_prior")


def _states(r):
    return {c["key"]: c["state"] for c in r["criteria"]}


# ─────────────────────────── Piotroski: tres estados ───────────────────────────
def test_piotroski_states_cumple_no_cumple_sin_dato():
    r = piotroski_evaluate(**dict(_FULL, roa_current=-0.01, shares_prior=None))
    st = _states(r)
    assert st["roa_positive"] == "no_cumple"
    assert st["roa_improved"] == "no_cumple"
    assert st["no_dilution"] == "sin_dato"
    assert st["cfo_positive"] == "cumple"
    assert set(st.values()) <= {"cumple", "no_cumple", "sin_dato"}


def test_missing_data_is_not_a_failure():
    """Un criterio sin dato no resta: X/N con N < 9."""
    r = piotroski_evaluate(**dict(_FULL, shares_prior=None))
    assert r["score"] == 8 and r["evaluated"] == 8


def test_full_coverage_is_identity():
    r = piotroski_evaluate(**_FULL)
    assert r["evaluated"] == 9 and r["scaled_score"] == 9 and isinstance(r["scaled_score"], int)
    assert r["conclusive"] and r["interpretation"].startswith("Excelente")


def test_scaling_with_seven_or_eight_evaluated():
    # 6 de 8 evaluados -> 6·9/8 = 6.75 -> banda >= 6 ("Bueno")
    r = piotroski_evaluate(**dict(_FULL, shares_prior=None, gross_margin_current=0.30,
                                  asset_turnover_current=0.9))
    assert (r["score"], r["evaluated"]) == (6, 8)
    assert r["scaled_score"] == pytest.approx(6.75)
    assert r["interpretation"].startswith("Bueno") and piotroski_level(r["scaled_score"], True) == "Bueno"
    # 7 evaluados es el mínimo concluyente
    r7 = piotroski_evaluate(**dict(_FULL, shares_prior=None, gross_margin_prior=None))
    assert r7["evaluated"] == 7 and r7["conclusive"] and r7["scaled_score"] == pytest.approx(9.0)


def test_below_min_evaluated_is_inconclusive():
    assert cfg("valuation.models.piotroski.min_evaluated") == 7
    r = piotroski_evaluate(**dict(_FULL, shares_prior=None, gross_margin_prior=None,
                                  asset_turnover_prior=None))
    assert r["evaluated"] == 6 and not r["conclusive"] and r["scaled_score"] is None
    assert "no concluyente" in r["interpretation"]
    assert piotroski_level(None, False) == "No concluyente"


def test_no_history_is_inconclusive_and_not_counted_as_failures():
    r = piotroski_evaluate(**{k: (None if k in _PRIORS else v) for k, v in _FULL.items()})
    assert (r["score"], r["evaluated"]) == (3, 3) and not r["conclusive"]
    assert sum(1 for c in r["criteria"] if c["state"] == "no_cumple") == 0


def test_legacy_wrapper_keeps_contract():
    score, details, interp = piotroski_f_score(**_FULL)
    assert score == 9 and len(details) == 9 and all(d.startswith("✓") for d in details)


def test_main_reads_structured_state_not_symbol(outputs_by_env):
    """main.py expone el estado estructurado; 'passed' sale del estado, no del texto."""
    import conftest
    for env in conftest.ENVS:
        for sym, (a, _) in outputs_by_env(env).items():
            pf = a["piotroski_f"]
            for key, c in pf["details"].items():
                assert c["state"] in {"cumple", "no_cumple", "sin_dato"}, (env, sym, key)
                assert c["passed"] == (c["state"] == "cumple")
            n_eval = sum(1 for c in pf["details"].values() if c["state"] != "sin_dato")
            assert pf["evaluated"] == n_eval
            assert pf["score"] == sum(1 for c in pf["details"].values() if c["state"] == "cumple")


# ─────────────────────────── Altman: todos los componentes o sin dato ───────────────────────────
from financial_ratios import altman_model, altman_z_score  # noqa: E402

_ALT = dict(working_capital=20, total_assets=100, retained_earnings=30, ebit=15,
            market_value_equity=120, total_liabilities=50, sales=150, book_value_equity=40)


@pytest.mark.parametrize("field,label", [("working_capital", "capital de trabajo"),
                                         ("retained_earnings", "utilidades retenidas")])
def test_altman_missing_component_is_sin_dato_not_zero(field, label):
    z, zone, interp, det = altman_z_score(**dict(_ALT, **{field: None}), sector="Industrials")
    assert z is None and zone == "N/A"
    assert det["reason"] == "sin_dato" and label in det["missing"] and label in interp


def test_altman_original_needs_sales_but_z_double_prime_does_not():
    z, _, _, det = altman_z_score(**dict(_ALT, sales=None), sector="Industrials")
    assert z is None and "ventas" in det["missing"]
    z2, zone2, _, det2 = altman_z_score(**dict(_ALT, sales=None), sector="Technology")
    assert z2 is not None and zone2 == "SAFE" and "Z''" in det2["model"]


def test_altman_model_depends_only_on_sector_and_industry():
    """Etapa 7: el modelo sale del sector/industria de la clasificación (coincidencia
    exacta), no de los datos disponibles ni de subcadenas."""
    assert altman_model("Industrials") == altman_model("Basic Materials") == altman_model("Energy") == "original"
    assert altman_model("Financial Services") == "z_double_prime"      # antes entraba por "services"
    assert altman_model("Technology", "Software - Application") == altman_model("") == "z_double_prime"
    # sin la X4 de la variante: "sin dato", ya no cambia en silencio al Z' de empresas privadas
    z, zone, _, det = altman_z_score(**dict(_ALT, market_value_equity=None), sector="Industrials")
    assert z is None and det["reason"] == "sin_dato" and "valor de mercado del patrimonio" in det["missing"]
    z, zone, _, det = altman_z_score(**dict(_ALT, book_value_equity=None), sector="Technology")
    assert z is None and det["reason"] == "sin_dato" and "patrimonio contable" in det["missing"]


def test_altman_x4_follows_each_variant():
    """Z original: capitalización / pasivo. Z'': patrimonio contable / pasivo (Altman 1995);
    los coeficientes y cortes solo valen con sus variables."""
    _, _, _, det = altman_z_score(**_ALT, sector="Industrials")
    assert det["X4_mcap_tl"] == 2.4 and "X4_book_tl" not in det
    _, _, _, det = altman_z_score(**_ALT, sector="Technology")
    assert det["X4_book_tl"] == 0.8 and "X4_mcap_tl" not in det
    # la capitalización ya no mueve el Z''
    assert altman_z_score(**dict(_ALT, market_value_equity=1e6), sector="Technology")[0] == \
        altman_z_score(**_ALT, sector="Technology")[0]


def test_altman_z_double_prime_with_book_equity_in_fixtures(outputs_by_env):
    """NFLX y V siguen en zona segura con el patrimonio contable; SNOW ya no usa Altman."""
    import conftest
    for env in conftest.ENVS:
        out = outputs_by_env(env)
        for sym in ("NFLX", "V"):
            z = out[sym][0]["altman_z"]
            assert "Z''" in z["model"] and z["zone"] == "safe" and "X4_book_tl" in z["details"], (env, sym)
        assert out["SNOW"][0]["altman_z"]["applicable"] is False


def test_altman_same_model_in_both_envs(outputs_by_env):
    import conftest
    if len(conftest.ENVS) < 2:
        pytest.skip("faltan los dos juegos")
    for sym in fixture_backend.TICKERS:
        models = {env: outputs_by_env(env)[sym][0]["altman_z"]["model"] for env in conftest.ENVS}
        assert len(set(models.values())) == 1, (sym, models)


def test_altman_complete_unchanged():
    z, zone, _, det = altman_z_score(**_ALT, sector="Industrials")
    assert z == pytest.approx(4.095, abs=0.006) and "warnings" not in det


# ─────────────────────────── Reescalado por categoría ───────────────────────────
from financial_ratios import CategoryCoverage, calculate_score_v2  # noqa: E402

# Perfiles sintéticos con TODOS los componentes del score con dato.
TECH_R = dict(roe=0.22, roa=0.10, operating_margin=0.25, net_margin=0.18, roic=0.20,
              current_ratio=1.8, debt_to_equity=0.4, interest_coverage=15.0,
              pe=25.0, forward_pe=21.0, p_fcf=22.0, ev_ebitda=16.0, peg=1.5,
              fcf_yield=0.045, dividend_yield=0.01, fcf=1e9, operating_cash_flow=1.3e9,
              net_income=9e8, fcf_to_net_income=1.1, pb=6.0, payout_ratio=0.2)
TECH_C = dict(sector_pe=25.0, sector_ev_ebitda=16.0, revenue_cagr_3y=0.12, eps_cagr_3y=0.14,
              fcf_cagr_3y=0.08, total_equity=5e9, total_assets=1e10)
WEAK_R = dict(TECH_R, roe=0.04, roa=0.01, operating_margin=0.03, net_margin=0.01, roic=0.02,
              current_ratio=0.7, debt_to_equity=2.5, interest_coverage=1.2, pe=60.0, forward_pe=70.0,
              p_fcf=80.0, ev_ebitda=40.0, peg=3.0, fcf=-1e8, operating_cash_flow=-5e7,
              net_income=1e8, fcf_to_net_income=0.2)
WEAK_C = dict(TECH_C, revenue_cagr_3y=-0.05, eps_cagr_3y=-0.10, fcf_cagr_3y=-0.20)
BANK_R = dict(TECH_R, debt_to_equity=8.0, roa=0.012, roe=0.15, pb=1.4)
BANK_C = dict(TECH_C, book_value=50.0, book_value_prior=46.0)
# Etapa 6: métricas de la rama FINANCIAL (lib/archetype_metrics.py), completas.
BANK_XV = dict(pb=1.4, ptbv=1.8, pb_justified=1.5, ptbv_justified=1.9, pb_ratio=1.4 / 1.5, ptbv_ratio=1.8 / 1.9,
               cost_of_equity=0.10, terminal_growth=0.025, roe_std=0.015, roe_years=4,
               efficiency_ratio=0.56, book_value_cagr_3y=0.07, book_value_basis="tangible")
REIT_R = dict(TECH_R, p_ffo=14.0, roe=0.07, roa=0.03, debt_to_equity=1.2, ffo_payout=0.8, dividend_yield=0.05,
              net_debt_to_ebitda=5.5)
# Etapa 9a: rentabilidad del REIT sobre el FFO (archetype_metrics._reit).
REIT_XV = dict(ffo_to_equity=0.085, ffo_margin=0.55)
REIT_C = dict(TECH_C, sector_pe=35.0, sector_ev_ebitda=20.0)
CASES = {
    "tech_full": (TECH_R, TECH_C, dict(z_score_value=4.0, z_score_level="SAFE", f_score_value=7,
                                       sector_key="technology", real_sector="Technology", wacc=0.10)),
    "weak_full": (WEAK_R, WEAK_C, dict(z_score_value=1.2, z_score_level="DISTRESS", f_score_value=2,
                                       sector_key="industrials", real_sector="Industrials", wacc=0.11)),
    "bank_full": (BANK_R, BANK_C, dict(f_score_value=6, sector_key="financials", real_sector="Financial Services",
                                       archetype="FINANCIAL", archetype_values=BANK_XV)),
    "reit_full": (REIT_R, REIT_C, dict(z_score_value=1.5, z_score_level="GREY", f_score_value=5,
                                       sector_key="real_estate", real_sector="Real Estate", wacc=0.08,
                                       archetype="REIT", archetype_values=REIT_XV)),
}
MID_R = dict(TECH_R, roe=0.10, roa=0.04, operating_margin=0.12, net_margin=0.06, roic=0.09,
             current_ratio=1.2, debt_to_equity=0.9, interest_coverage=4.0, pe=19.0, forward_pe=18.5,
             p_fcf=24.0, ev_ebitda=13.0, peg=2.0, fcf=4e8, operating_cash_flow=6e8,
             net_income=5e8, fcf_to_net_income=0.8)
MID_C = dict(TECH_C, sector_pe=20.0, sector_ev_ebitda=13.0, revenue_cagr_3y=0.04, eps_cagr_3y=0.06,
             fcf_cagr_3y=0.02)
CASES["mid_full"] = (MID_R, MID_C, dict(z_score_value=2.4, z_score_level="GREY", f_score_value=5,
                                        sector_key="industrials", real_sector="Industrials", wacc=0.09))

# Salida de calculate_score_v2 ANTES de la etapa 5 (capturada con el código de 16b4c0f).
EXPECTED_FULL = {
 "tech_full": {
  "score": 98,
  "cats": {
   "Solidez Financiera": 20,
   "Rentabilidad": 20,
   "Valoración": 11,
   "Calidad de Ganancias": 20,
   "Crecimiento": 18
  }
 },
 "weak_full": {
  "score": 0,
  "cats": {
   "Solidez Financiera": 0,
   "Rentabilidad": 0,
   "Valoración": 5,
   "Calidad de Ganancias": 0,
   "Crecimiento": 0
  }
 },
 "bank_full": {
  "score": 96,
  "cats": {
   "Solidez Financiera": 18,
   "Rentabilidad": 20,
   "Valoración": 20,
   "Calidad de Ganancias": 20,
   "Crecimiento": 18
  }
 },
 "reit_full": {
  "score": 88,
  "cats": {
   "Solidez Financiera": 15,
   "Rentabilidad": 20,
   "Valoración": 16,
   "Calidad de Ganancias": 19,
   "Crecimiento": 18
  }
 },
 "mid_full": {
  "score": 61,
  "cats": {
   "Solidez Financiera": 8,
   "Rentabilidad": 14,
   "Valoración": 10,
   "Calidad de Ganancias": 17,
   "Crecimiento": 12
  }
 }
}

_CAT_KEY = {"Solidez Financiera": "solidez", "Rentabilidad": "rentabilidad", "Valoración": "valoracion",
            "Calidad de Ganancias": "calidad", "Crecimiento": "crecimiento"}


def _cats(res):
    return {c["category"]: c["score"] for c in res["categories"]}


@pytest.mark.parametrize("case", ["tech_full", "weak_full", "mid_full"])
def test_full_data_gives_exactly_the_previous_score(case):
    """MATURE con todos los datos: categorías idénticas a antes de la etapa 5 (y de la 6).
    Etapa 9a: sin total único; calidad = 4 categorías y precio = Valoración, a 100.
    tech_full: Valoración 20 -> 14 a propósito (sin bandas growth ni bono GARP) y 14 -> 11 con el
    bloque de múltiplos; weak_full: 0 -> 5 (el bloque acota a -6 los múltiplos correlacionados, que antes
    se sumaban)."""
    r, c, kw = CASES[case]
    res = calculate_score_v2(r, c, **kw)
    assert res["archetype"] == "MATURE"
    cats = EXPECTED_FULL[case]["cats"]
    assert _cats(res) == cats
    q = [cats[k] for k in ("Solidez Financiera", "Rentabilidad", "Calidad de Ganancias", "Crecimiento")]
    assert res["quality"]["score"] == round(sum(q) * 100 / 80)
    assert res["price_raw"]["score"] == cats["Valoración"] * 5
    assert "score" not in res and "level" not in res
    assert all(v["coverage"] == 1.0 and not v["missing"] and not v["not_applicable"]
               for v in res["coverage"].values())


@pytest.mark.parametrize("case,na", [
    ("bank_full", {"solidez": {"D/E bancario"},
                   "rentabilidad": {"Margen operativo", "ROIC−WACC"},
                   "valoracion": {"P/E", "P/FCF", "EV/EBITDA", "PEG"},
                   "calidad": {"Piotroski F", "Flujo operativo", "FCF", "FCF / beneficio neto"},
                   "crecimiento": {"Crecimiento del FCF"}}),
    ("reit_full", {"solidez": {"Altman Z", "Current ratio"},
                   "rentabilidad": {"ROE", "ROA", "Margen neto", "ROIC−WACC", "Margen bruto", "Margen operativo"},
                   "valoracion": {"P/E", "P/FCF", "PEG"},
                   "calidad": {"Piotroski F", "FCF / beneficio neto"}, "crecimiento": {"Crecimiento del BPA"}}),
])
def test_archetype_branch_with_full_data_has_full_coverage(case, na):
    """Con todos los datos de su rama, FINANCIAL y REIT tienen cobertura completa:
    lo que no aplica no cuenta como dato ausente."""
    r, c, kw = CASES[case]
    res = calculate_score_v2(r, c, **kw)
    for key, cov in res["coverage"].items():
        assert cov["coverage"] == 1.0 and not cov["missing"], (key, cov)
        assert set(cov["not_applicable"]) == na[key], key


def test_coverage_helper_rescales_positive_and_negative_parts():
    cov = CategoryCoverage()
    cov.comp("a", (6, -6), 6)
    cov.comp("b", (4, -4), -2)
    cov.comp("c", (5, -5), None)
    adj = []
    # positiva 6 × 15/10 = 9 ; negativa −2 × 15/10 = −3  -> 6 (antes 4) -> delta +2
    assert cov.apply(10, adj) == 12
    assert adj[-1]["metric"] == "Cobertura" and adj[-1]["adjustment"] == 2 and adj[-1]["value"] == "2/3 componentes"
    rep = cov.report()
    assert rep["evaluated"] == 2 and rep["components"] == 3 and rep["missing"] == ["c"]


def test_coverage_helper_full_is_identity_and_empty_is_neutral():
    cov = CategoryCoverage()
    cov.comp("a", (6, -6), 3)
    adj = []
    assert cov.apply(13, adj) == 13 and adj == []
    empty = CategoryCoverage()
    empty.comp("a", (6, -6), None)
    assert empty.apply(10, []) == 10 and empty.report()["coverage"] == 0.0


def test_low_confidence_threshold():
    thr = cfg("thresholds.score.coverage.low_confidence_below")
    assert thr == 0.6
    r, c, kw = CASES["mid_full"]
    res = calculate_score_v2(r, dict(c, eps_cagr_3y=None, fcf_cagr_3y=None), **kw)
    cr = res["coverage"]["crecimiento"]
    assert cr["evaluated"] == 1 and cr["low_confidence"] is True       # 1/3 < 60%
    res2 = calculate_score_v2(r, dict(c, fcf_cagr_3y=None), **kw)
    assert res2["coverage"]["crecimiento"]["low_confidence"] is False  # 2/3 >= 60%


def test_low_confidence_does_not_change_the_score():
    r, c, kw = CASES["mid_full"]
    base = calculate_score_v2(r, dict(c, fcf_cagr_3y=None), **kw)
    # mismo cálculo; el flag es solo informativo
    assert base["category_scores"]["crecimiento"] == next(
        x["score"] for x in base["categories"] if x["category"] == "Crecimiento")


def test_piotroski_inconclusive_is_excluded_from_calidad():
    r, c, kw = CASES["mid_full"]
    res = calculate_score_v2(r, c, **dict(kw, f_score_value=None))
    cal = res["coverage"]["calidad"]
    assert "Piotroski F" in cal["missing"] and cal["evaluated"] == 3


def test_altman_sin_dato_rescales_solidez():
    r, c, kw = CASES["mid_full"]
    res = calculate_score_v2(r, c, **dict(kw, z_score_value=None, z_score_level="N/A"))
    sol = res["coverage"]["solidez"]
    assert sol["missing"] == ["Altman Z"] and sol["evaluated"] == 3


# ─────────────────────────── Cobertura de intereses con EBIT < 0 ───────────────────────────
from financial_ratios import interest_coverage_state  # noqa: E402


def test_interest_coverage_state():
    assert interest_coverage_state(None, -1e9) is None
    assert interest_coverage_state(4.0, -1e9) == "ok"
    assert interest_coverage_state(-8.4, -1e9) == "no_significativo"   # EBIT < 0, caja > deuda
    assert interest_coverage_state(-8.4, 4e8) == "negativa"            # EBIT < 0, deuda neta
    assert interest_coverage_state(-8.4, None) == "negativa"           # sin dato de caja: se penaliza


# ─────────────────────────── Deuda neta/EBITDA con EBITDA <= 0 ───────────────────────────
from financial_ratios import net_debt_ebitda_state  # noqa: E402
from pdf_report import read_nde  # noqa: E402


def test_net_debt_ebitda_state():
    assert net_debt_ebitda_state(-5e8, 4e8) == "no_significativo"     # deuda neta, EBITDA < 0
    assert net_debt_ebitda_state(-5e8, -1e9) == "no_significativo"    # caja neta, EBITDA < 0
    assert net_debt_ebitda_state(0.0, 4e8) == "no_significativo"
    assert net_debt_ebitda_state(5e8, -1e9) == "caja_neta"
    assert net_debt_ebitda_state(5e8, 4e8) == "ok"
    assert net_debt_ebitda_state(None, 4e8) is None


def test_read_nde_net_cash_only_when_cash_exceeds_debt():
    # EBITDA < 0 con deuda neta: ND/EBITDA = -0.4x no se lee como caja neta
    lab, tone, txt = read_nde(-0.4, "no_significativo", 4e8)
    assert lab == "No significativa" and "caja neta" not in txt
    # EBITDA < 0 con caja neta: no significativa, pero la caja neta es real
    lab, tone, txt = read_nde(1.2, "no_significativo", -1e9)
    assert lab == "No significativa" and "caja neta" in txt and "manejable" not in txt
    # EBITDA > 0 con caja neta: lectura de siempre
    assert read_nde(-0.3, "caja_neta", -1e9)[0] == "Caja neta"


def test_net_debt_ebitda_end_to_end(outputs_by_env):
    """SNOW local (EBITDA < 0, deuda neta) y prod (EBITDA < 0, caja neta): ratio fuera del JSON;
    la frase de caja neta solo en prod. El score no usa la ratio."""
    import conftest
    if not {"prod", "local"} <= set(conftest.ENVS):
        pytest.skip("faltan juegos de fixtures")
    for env, net_cash in (("local", False), ("prod", True)):
        a, pdf = outputs_by_env(env)["SNOW"]
        txt = fixture_backend.pdf_text(pdf) if isinstance(pdf, bytes) else pdf
        km = a["key_metrics"]
        assert km["net_debt_to_ebitda_state"] == "no_significativo"
        assert km["net_debt_to_ebitda"] is None and a["ratios"]["net_debt_to_ebitda"] is None
        assert any(f["field"] == "key_metrics.net_debt_to_ebitda" for f in a["data_validation"])
        assert (km["net_debt"] < 0) is net_cash
        assert ("(caja neta)" in txt) is net_cash
        assert "x EBITDA) es manejable" not in txt and "Deuda neta / EBITDA\n—\nNo significativa" in txt
    # con EBITDA > 0 no cambia nada
    assert outputs_by_env("prod")["NFLX"][0]["key_metrics"]["net_debt_to_ebitda_state"] in ("ok", "caja_neta")


def _sol(res):
    return next(x for x in res["categories"] if x["category"] == "Solidez Financiera")


def test_negative_coverage_with_net_cash_is_not_significant():
    r, c, kw = CASES["mid_full"]
    res = calculate_score_v2(dict(r, interest_coverage=-8.4, net_debt=-1e9), c, **kw)
    sol, cov = _sol(res), res["coverage"]["solidez"]
    # Etapa 9a: "no significativo" se trata como "no aplica": fuera del denominador y sin reescalado.
    assert cov["missing"] == [] and "caja neta" in cov["not_significant"]["Cobertura de intereses"]
    row = next(a for a in sol["adjustments"] if a["metric"] == "Cobertura Intereses")
    assert row["adjustment"] == 0 and row["value"] == "No significativo"
    assert not any(a["metric"] == "Cobertura" for a in sol["adjustments"])


def test_negative_coverage_with_net_debt_keeps_the_penalty():
    r, c, kw = CASES["mid_full"]
    res = calculate_score_v2(dict(r, interest_coverage=-8.4, net_debt=4e8), c, **kw)
    sol = _sol(res)
    assert "Cobertura de intereses" not in res["coverage"]["solidez"]["missing"]
    row = next(a for a in sol["adjustments"] if a["metric"] == "Cobertura Intereses")
    worst = cfg("thresholds.score.solidez.coverage_points")[-1]
    assert row["adjustment"] == worst and row["value"] == "EBIT < 0" and "deuda neta" in row["reason"]


def test_negative_coverage_end_to_end(outputs_by_env):
    """SNOW prod (caja neta): no significativa, fuera del JSON y sin −3.
    SNOW local (deuda neta): penaliza y el PDF no imprime −8.4x como cobertura."""
    import conftest
    if not {"prod", "local"} <= set(conftest.ENVS):
        pytest.skip("faltan juegos de fixtures")
    a, pdf = outputs_by_env("prod")["SNOW"]
    assert a["key_metrics"]["interest_coverage_state"] == "no_significativo"
    assert a["key_metrics"]["interest_coverage"] is None and a["ratios"]["interest_coverage"] is None
    assert any(f["rule"] == "ratio_no_significativa" for f in a["data_validation"])
    assert "Cobertura de intereses" in a["score_coverage"]["solidez"]["not_significant"]
    assert not any(x["metric"] == "Cobertura" for x in a["score"]["breakdown"]["Solidez Financiera"]["adjustments"])
    assert not any("Cobertura de intereses" in s.get("reason", "") for k in ("red_flags", "warnings") for s in a["alerts"][k])
    a, pdf = outputs_by_env("local")["SNOW"]
    txt = fixture_backend.pdf_text(pdf) if isinstance(pdf, bytes) else pdf
    assert a["key_metrics"]["interest_coverage_state"] == "negativa"
    _ic = next(x for x in a["score"]["breakdown"]["Solidez Financiera"]["adjustments"]
               if x["metric"] == "Cobertura Intereses")
    assert _ic["adjustment"] == cfg("thresholds.score.solidez.coverage_points")[-1]   # la penalización se mantiene
    assert "Cobertura de intereses\nNegativa (EBIT < 0)" in txt
    assert "-8.4x" not in txt


# Para cada componente: (dónde vive, clave, valor favorable, valor desfavorable, categoría)
_BOUNDS = [
    ("kw", "z", ("SAFE", 6.0), ("DISTRESS", 0.5), "Solidez Financiera"),
    ("r", "current_ratio", 3.0, 0.5, "Solidez Financiera"),
    ("r", "debt_to_equity", 0.05, 9.0, "Solidez Financiera"),
    ("r", "interest_coverage", 50.0, 0.5, "Solidez Financiera"),
    ("r", "roe", 0.9, -0.5, "Rentabilidad"),
    ("r", "roa", 0.5, -0.2, "Rentabilidad"),
    ("r", "operating_margin", 0.5, -0.3, "Rentabilidad"),
    ("r", "net_margin", 0.5, -0.3, "Rentabilidad"),
    ("r", "roic", 0.9, -0.9, "Rentabilidad"),
    ("r", "p_fcf", 1.0, 900.0, "Valoración"),
    ("r", "ev_ebitda", 1.0, 900.0, "Valoración"),
    ("r", "peg", 0.1, 9.0, "Valoración"),
    ("kw", "f", 9, 0, "Calidad de Ganancias"),
    ("r", "operating_cash_flow", 1e9, -1e9, "Calidad de Ganancias"),
    ("r", "fcf", 1e9, -1e9, "Calidad de Ganancias"),
    ("r", "fcf_to_net_income", 3.0, 0.0, "Calidad de Ganancias"),
    ("c", "eps_cagr_3y", 0.6, -0.6, "Crecimiento"),
    ("c", "fcf_cagr_3y", 0.6, -0.6, "Crecimiento"),
]


def _score_with(case, where, key, value):
    r, c, kw = CASES[case]
    r, c, kw = dict(r), dict(c), dict(kw)
    if where == "kw" and key == "z":
        if value is None:
            kw.update(z_score_value=None, z_score_level="N/A")
        else:
            kw.update(z_score_level=value[0], z_score_value=value[1])
    elif where == "kw" and key == "f":
        kw["f_score_value"] = value
    else:
        {"r": r, "c": c}[where][key] = value
    return _cats(calculate_score_v2(r, c, **kw))


@pytest.mark.parametrize("case", ["mid_full", "tech_full", "weak_full", "reit_full"])
@pytest.mark.parametrize("where,key,fav,unfav,cat", _BOUNDS, ids=[b[1] for b in _BOUNDS])
def test_missing_never_below_unfavorable_nor_above_favorable(case, where, key, fav, unfav, cat):
    """Un dato ausente no penaliza como un incumplimiento (>= dato desfavorable)
    ni premia por ocultarlo (<= dato favorable)."""
    if case == "reit_full" and key == "p_fcf":
        pytest.skip("P/FCF no aplica a REITs")
    missing = _score_with(case, where, key, None)[cat]
    best = _score_with(case, where, key, fav)[cat]
    worst = _score_with(case, where, key, unfav)[cat]
    assert worst <= missing <= best, (case, key, worst, missing, best)


def test_pe_is_monotone_after_removing_growth_tolerances():
    """Hasta la etapa 9a Valoración no era monótona en el P/E: el P/E alimentaba el tipo
    de empresa, que activaba bandas growth, el ajuste por calidad del crecimiento y el
    bono GARP. Sin ellos (el crecimiento entra solo por PEG y DCF), un P/E más alto nunca
    mejora la valoración."""
    fav = _score_with("tech_full", "r", "pe", 1.0)["Valoración"]
    unfav = _score_with("tech_full", "r", "pe", 900.0)["Valoración"]
    assert fav > unfav


def test_rescaling_bound_holds_for_random_components():
    """Cota del reescalado en sí: para cualquier combinación de componentes, el
    resultado con uno ausente queda entre el de ese componente en su mínimo y
    en su máximo."""
    import random
    rnd = random.Random(20261012)
    for _ in range(3000):
        n = rnd.randint(2, 5)
        comps = []
        for i in range(n):
            mx = rnd.randint(1, 7)
            mn = -rnd.randint(1, 7)
            comps.append((f"c{i}", (mx, mn), rnd.randint(mn, mx)))
        miss = rnd.randrange(n)

        def run(value):
            cov = CategoryCoverage()
            s = 0
            for j, (name, pts, adj) in enumerate(comps):
                a = value if j == miss else adj
                cov.comp(name, pts, a)
                s += a or 0
            return cov.apply(10 + s, [])

        mx, mn = comps[miss][1]
        assert run(mn) <= run(None) <= run(mx), comps


def test_fcf_cagr_reaches_the_scorer_with_reason(outputs_by_env):
    """fcf_cagr_3y sale de los 4 ejercicios anuales; indefinido -> sin dato con motivo."""
    import conftest
    if "prod" not in conftest.ENVS:
        pytest.skip("falta el juego prod")
    out = outputs_by_env("prod")
    nflx = out["NFLX"][0]["score_coverage"]["crecimiento"]
    assert "Crecimiento del FCF" not in nflx["missing"] and not nflx["not_applicable"]
    # Etapa 6: en JPM (FINANCIAL, FCF 107 -> 13 -> -42 -> -148) y FCX (CYCLICAL) no aplica;
    # el motivo de un CAGR indefinido sigue llegando al scorer en una MATURE.
    for sym in ("JPM", "FCX"):
        cre = out[sym][0]["score_coverage"]["crecimiento"]
        assert "Crecimiento del FCF" in cre["not_applicable"] and "Crecimiento del FCF" not in cre["missing"]
    r, c, kw = CASES["mid_full"]
    res = calculate_score_v2(r, dict(c, fcf_cagr_3y=None,
                                     fcf_cagr_3y_reason="el FCF cambia de signo en el periodo: CAGR no definido"), **kw)
    assert "signo" in res["coverage"]["crecimiento"]["missing_reasons"]["Crecimiento del FCF"]


# ─────────────────────────── Cobertura mínima (50%) ───────────────────────────
def test_category_below_min_coverage_is_excluded_and_total_rescaled():
    assert cfg("thresholds.score.coverage.min_conclusive") == 0.5
    r, c, kw = CASES["mid_full"]
    res = calculate_score_v2(r, dict(c, eps_cagr_3y=None, fcf_cagr_3y=None), **kw)   # Crecimiento 1/3
    cre = next(x for x in res["categories"] if x["category"] == "Crecimiento")
    assert cre["conclusive"] is False and cre["coverage"]["conclusive"] is False
    assert res["excluded_categories"] == ["Crecimiento"]
    others = [x["score"] for x in res["categories"] if x["category"] not in ("Crecimiento", "Valoración")]
    assert res["quality"]["score"] == round(sum(others) * 100 / (20 * 3))     # calidad sobre 3 de 4
    assert res["quality"]["basis"] == "calculado sobre 3 de 4 categorías"
    assert res["quality"]["low_confidence"] is True
    # sin reescalado: el único componente con dato conserva su ajuste
    assert cre["adjustments"][-1]["metric"] == "Cobertura" and cre["adjustments"][-1]["adjustment"] == 0


def test_category_at_50_percent_is_rescaled_and_low_confidence():
    r, c, kw = CASES["mid_full"]
    res = calculate_score_v2(dict(r, p_fcf=None, ev_ebitda=None), c, **kw)   # Valoración 2/4 = 50%
    val = res["coverage"]["valoracion"]
    assert val["coverage"] == 0.5 and val["conclusive"] is True and val["low_confidence"] is True
    assert res["excluded_categories"] == []


def test_all_categories_inconclusive_is_neutral():
    res = calculate_score_v2({}, {}, sector_key="default")
    assert res["quality"]["score"] is None and res["price_raw"]["score"] is None   # sin dato, no un 50
    assert res["score_conclusive"] is False
    assert len(res["excluded_categories"]) == 5


# ─────────────────────────── Total parcial declarado ───────────────────────────
def test_partial_total_declares_its_basis():
    r, c, kw = CASES["mid_full"]
    full = calculate_score_v2(r, c, **kw)
    assert (full["quality"]["categories_included"], full["quality"]["categories_total"]) == (4, 4)
    part = calculate_score_v2(r, dict(c, eps_cagr_3y=None, fcf_cagr_3y=None), **kw)
    assert (part["quality"]["categories_included"], part["quality"]["categories_total"]) == (3, 4)
    assert part["quality"]["partial"] is True and part["price_raw"]["partial"] is False


def test_partial_total_is_shown_in_json_and_pdf(outputs_by_env):
    """Etapa 9a: cobertura parcial de cada puntuación, en el JSON y en la portada del PDF.
    Se fuerza sobre SNOW: Crecimiento no concluyente (calidad sobre 3 de 4) y Valoración
    no concluyente (precio sin dato)."""
    import copy
    import conftest
    if "prod" not in conftest.ENVS:
        pytest.skip("falta el juego prod")
    a0, _ = outputs_by_env("prod")["SNOW"]
    a = copy.deepcopy(a0)
    a["score"]["breakdown"]["Valoración"].update(conclusive=False, coverage=0.25)
    a["score"]["breakdown"]["Crecimiento"].update(conclusive=False, coverage=0.33)
    a["quality"].update(partial=True, basis="calculado sobre 3 de 4 categorías", categories_included=3,
                        excluded_categories=["Crecimiento"])
    a["price_attractiveness"].update(score=None, score_raw=None, level=None, partial=True,
                                     basis="calculado sobre 0 de 1 categorías")
    with fixture_backend.replay(fixture_backend.fixtures_dir("prod")) as store:
        store.load("SNOW")
        pdf = fixture_backend.build_pdf_bytes(a, fixture_backend.capture_date(store.meta["SNOW"]))
    txt = (fixture_backend.pdf_text(pdf) if isinstance(pdf, bytes) else pdf).replace("\n", " ")
    cover = txt.split("===== página 2")[0]
    assert "Calidad calculado sobre 3 de 4 categorías (Crecimiento no concluyente)" in cover
    assert "Precio sin dato: Valoración no concluyente" in cover
    assert "No concluyente · cobertura 25%" in cover
    nflx = outputs_by_env("prod")["NFLX"][0]
    assert nflx["quality"]["partial"] is False and nflx["quality"]["basis"] is None
    assert a0["quality"]["partial"] is False          # SNOW real (etapa 6): 4 de 4


# ─────────────────────────── etapa 6: "no aplica" frente a "sin dato" ───────────────────────────
def _cov(*specs):
    cov = CategoryCoverage()
    for name, adj, na in specs:
        cov.comp(name, [3, -3], adj, na=na)
    return cov


NA = "No aplica a REIT: prueba"


def test_not_applicable_does_not_count_in_coverage():
    cov = _cov(("A", 2, None), ("B", None, NA))
    rep = cov.report()
    assert (rep["components"], rep["evaluated"], rep["coverage"]) == (1, 1, 1.0)
    assert rep["missing"] == [] and rep["not_applicable"] == {"B": NA}
    adj = []
    assert cov.apply(12, adj) == 12                       # sin reescalado
    assert adj[0]["metric"] == "No aplica" and adj[0]["value"] == "B" and adj[0]["adjustment"] == 0


def test_not_applicable_cannot_make_a_category_inconclusive():
    with_na = _cov(("A", 2, None), ("B", None, None), ("C", None, NA), ("D", None, NA))
    with_missing = _cov(("A", 2, None), ("B", None, None), ("C", None, None), ("D", None, None))
    assert with_na.report()["coverage"] == 0.5 and with_na.conclusive
    assert with_missing.report()["coverage"] == 0.25 and not with_missing.conclusive


def test_not_applicable_and_missing_are_reported_apart():
    cov = _cov(("A", 2, None), ("B", None, None), ("C", None, NA))
    adj = []
    cov.apply(12, adj)
    metrics = [a["metric"] for a in adj]
    assert metrics == ["No aplica", "Cobertura"]
    assert "C" not in adj[1]["reason"] and "B" in adj[1]["reason"]      # "sin dato: B"
    assert NA in adj[0]["reason"]


def test_category_with_nothing_applicable_is_not_applicable():
    cov = _cov(("A", None, NA))
    assert cov.report()["applicable"] is False and cov.report()["components"] == 0


# ─────────────────────────── estancamiento (etapa 6) ───────────────────────────
from financial_ratios import growth_for_bands, score_crecimiento  # noqa: E402


def test_stagnation_tolerance_from_config():
    tol = cfg("thresholds.score.crecimiento.flat_tolerance")
    assert tol == 0.02
    assert growth_for_bands(-0.019) == 0.0 and growth_for_bands(-0.021) == -0.021
    assert growth_for_bands(0.01) == 0.01 and growth_for_bands(None) is None


@pytest.mark.parametrize("arch,key", [(None, "Crecimiento Ingresos 3Y"),
                                      ("REIT", "Retorno total (dividendo + FFO por acción)")])
def test_stagnation_scores_like_the_flat_band(arch, key):
    def adj(g):
        res = score_crecimiento(g, None, None, archetype=arch, dividend_yield=0.05)
        return next(a["adjustment"] for a in res["adjustments"] if a["metric"] == key)
    assert adj(-0.001) == adj(0.01) == adj(-0.019)          # plano
    assert adj(-0.03) < adj(-0.019)                           # contracción real
