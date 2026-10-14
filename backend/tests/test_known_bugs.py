"""Bugs verificados en docs/RECON.md, uno por test, marcados xfail(strict).

Cada test afirma el comportamiento CORRECTO, así que hoy falla (XFAIL). Cuando
el bug se corrija pasará (XPASS) y, por `xfail_strict = true` en pytest.ini,
la suite fallará a propósito: es la señal de que el bug quedó corregido y hay
que quitar su marca xfail (y regenerar los golden de forma explícita).
"""
import copy

import pytest

import fixture_backend as fb



def _frame(store, sym, attr):
    return fb.obj_to_df(store.yf[sym][attr])


def _ticker_info(sym):
    """Dict interno de yf_adapter (lo que consume el motor), desde fixtures."""
    import yf_adapter
    with fb.replay() as store:
        fb.run_analysis(sym, store)
        return copy.deepcopy(yf_adapter._cache[sym.upper()][1])


# CORREGIDO en la etapa 3 (bug d): validate._rule_fcf recalcula FCF = OCF − capex
# del estado de flujos cuando FCF > OCF (NFLX 25.4B > OCF 12.0B -> 9.46B FY2025).
def test_bug_fcf_exceeds_ocf_nflx(analysis):
    km = analysis("NFLX")["key_metrics"]
    assert km["free_cash_flow"] <= km["operating_cash_flow"]


# CORREGIDO en la etapa 3 (bug c): Ordinary Shares Number antes que Share Issued.
def test_bug_shares_issued_vs_ordinary_nflx(fixture_store):
    bs = _frame(fixture_store, "NFLX", "balance_sheet")
    ordinary = bs.loc["Ordinary Shares Number"]
    info = _ticker_info("NFLX")
    assert info["_piotroski_current"]["shares"] == pytest.approx(float(ordinary.iloc[0]))
    assert info["_prior_year"]["shares"] == pytest.approx(float(ordinary.iloc[1]))


# CORREGIDO en la etapa 8 (C4): WACC = E/(D+E)·Ke + D/(D+E)·Kd·(1−t) (lib/cost_of_capital.py).
def test_bug_wacc_is_only_cost_of_equity_nflx(analysis):
    km = analysis("NFLX")["key_metrics"]
    assert km["total_debt"] and km["total_debt"] > 0  # empresa apalancada
    from settings import cfg
    C = cfg("valuation.capm")
    ke = analysis("NFLX")["wacc"]["ke"]
    beta_adj = C["blume_weight"] * km["beta"] + C["blume_prior"]
    assert ke == pytest.approx(C["risk_free_rate"] + beta_adj * C["market_risk_premium"])
    assert abs(km["wacc"] - ke) > 1e-4


# CORREGIDO en la etapa 4 (decisión 6): el grid parte del crecimiento usado por el DCF
# (tope 30%, mismo suelo) con su mismo decaimiento. Etapa 8: la celda base usa el WACC
# exacto (sin redondear), así que coincide con el DCF.
def test_bug_dcf_vs_grid_growth_snow(analysis):
    a = analysis("SNOW")
    fair = a["dcf"]["fair_value"]
    base = a["sensitivity"]["base_case"]["fair_value"]
    assert base == pytest.approx(fair, rel=0.01)


# CORREGIDO en la etapa 8 (§1.4): el grid devuelve base_growth_idx / base_discount_idx.
def test_bug_base_case_box_never_drawn_nflx(analysis, fixture_store):
    import pdf_report
    from reportlab.platypus import TableStyle

    recorded = []

    class _RecordingTableStyle(TableStyle):
        def __init__(self, cmds=None, *a, **kw):
            recorded.append(list(cmds or []))
            super().__init__(cmds, *a, **kw)

    a = analysis("NFLX")
    assert a["sensitivity"]["matrix"], "NFLX debe tener grid para que el test sea válido"
    fb.build_pdf_bytes(a, fb.capture_date(fixture_store.meta["NFLX"]),
                       table_style_cls=_RecordingTableStyle)
    assert recorded, "la captura de TableStyle no interceptó nada (test inválido)"
    boxes = [c for cmds in recorded for c in cmds
             if c and c[0] == "BOX" and len(c) >= 5 and c[3] == 1.4 and c[4] == pdf_report.BRAND]
    assert boxes, "el recuadro verde del escenario base no se dibujó"


# CORREGIDO en la etapa 3 (bug e): en financieras, un crecimiento que difiere >15 pp
# del YoY de los estados se sustituye por este (JPM 30.4% -> 7.3%, con flag).
def test_bug_jpm_revenue_growth_artifact(analysis, fixture_store):
    inc = _frame(fixture_store, "JPM", "income_stmt")
    rev = inc.loc["Total Revenue"]
    statement_yoy = float(rev.iloc[0]) / float(rev.iloc[1]) - 1
    km = analysis("JPM")["key_metrics"]
    assert abs(km["revenue_growth"] - statement_yoy) < 0.05


# CORREGIDO en la etapa 3 (bug a): el plan B toma sector/industria de la búsqueda de Yahoo.
def test_bug_prod_sector_unknown_outside_known_list_o(outputs_by_env):
    import conftest
    if "panel" not in conftest.BOUND_ENVS:
        pytest.skip("falta el panel")
    profile = outputs_by_env("panel")["O"][0]["profile"]
    assert profile["sector"] == "Real Estate"


# CORREGIDO en la etapa 9b (opción b): el DCF usa siempre el crecimiento de los estados
# (el mismo que puntúa Crecimiento). Historia del bug: un revenueGrowth
# marcado "crecimiento_incoherente" (acción "aviso": el valor se conserva) debería ser
# solo informativo, pero entra en el score: es el crecimiento de entrada del DCF
# (main: growth = financials.revenue_growth_yoy, con tope del 30%) y el DCF puntúa en
# Valoración y vota en la convergencia de la confianza. Hoy no altera ningún golden
# (SNOW local: DCF de fiabilidad baja, ajuste 0; FCX prod: CYCLICAL usa el crecimiento
# normalizado), pero con un DCF fiable sí: V prod con +17 pp pasa de precio 39 a 48 y
# confianza de media a baja. Se fuerza el caso inyectando el dato en la entrada.
def _run_with_revenue_growth(sym, env, delta):
    import validate
    orig = validate.validate_info

    def patched(info, symbol=""):
        info["revenueGrowth"] = info["revenueGrowth"] + delta
        return orig(info, symbol)

    validate.validate_info = patched
    try:
        with fb.replay(fb.fixtures_dir(env)) as store:
            return fb.run_analysis(sym, store)
    finally:
        validate.validate_info = orig


def test_bug_incoherent_revenue_growth_is_informative_only():
    import conftest
    if "panel" not in conftest.BOUND_ENVS:
        pytest.skip("falta el panel")
    base = _run_with_revenue_growth("V", "panel", 0.0)
    flagged = _run_with_revenue_growth("V", "panel", 0.17)
    assert any(f["rule"] == "crecimiento_incoherente" for f in flagged["data_validation"])
    assert not any(f["rule"] == "crecimiento_incoherente" for f in base["data_validation"])
    # Solo informativo: ni el desglose, ni las dos puntuaciones, ni la confianza cambian.
    assert flagged["score"]["breakdown"] == base["score"]["breakdown"]
    assert flagged["quality"] == base["quality"]
    assert flagged["price_attractiveness"] == base["price_attractiveness"]
    assert flagged["confidence"]["level"] == base["confidence"]["level"]
