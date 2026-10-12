"""Bugs verificados en docs/RECON.md, uno por test, marcados xfail(strict).

Cada test afirma el comportamiento CORRECTO, así que hoy falla (XFAIL). Cuando
el bug se corrija pasará (XPASS) y, por `xfail_strict = true` en pytest.ini,
la suite fallará a propósito: es la señal de que el bug quedó corregido y hay
que quitar su marca xfail (y regenerar los golden de forma explícita).
"""
import copy

import pytest

import fixture_backend as fb

RF, MRP = 0.045, 0.055  # config.DCF_RISK_FREE_RATE / DCF_MARKET_RISK_PREMIUM


def _frame(store, sym, attr):
    return fb.obj_to_df(store.yf[sym][attr])


def _ticker_info(sym):
    """Dict interno de yf_adapter (lo que consume el motor), desde fixtures."""
    import yf_adapter
    with fb.replay() as store:
        fb.run_analysis(sym, store)
        return copy.deepcopy(yf_adapter._cache[sym.upper()][1])


@pytest.mark.xfail(raises=AssertionError, reason="RECON C5: FCF = financialData.freeCashflow (FCF apalancado de Yahoo) "
                          "y no OCF−capex; NFLX 25.4B > OCF 12.0B (data_fetcher.py:478)")
def test_bug_fcf_exceeds_ocf_nflx(analysis):
    km = analysis("NFLX")["key_metrics"]
    assert km["free_cash_flow"] <= km["operating_cash_flow"]


@pytest.mark.xfail(raises=AssertionError, reason="RECON C3: Piotroski/buyback usan 'Share Issued' (incluye autocartera) "
                          "en vez de 'Ordinary Shares Number' (yf_adapter.py:783, 863)")
def test_bug_shares_issued_vs_ordinary_nflx(fixture_store):
    bs = _frame(fixture_store, "NFLX", "balance_sheet")
    ordinary = bs.loc["Ordinary Shares Number"]
    info = _ticker_info("NFLX")
    assert info["_piotroski_current"]["shares"] == pytest.approx(float(ordinary.iloc[0]))
    assert info["_prior_year"]["shares"] == pytest.approx(float(ordinary.iloc[1]))


@pytest.mark.xfail(raises=AssertionError, reason="RECON C4: calculate_wacc se llama solo con beta y devuelve el coste "
                          "del equity (Rf + β·MRP), sin ponderar la deuda (main.py:489, 762)")
def test_bug_wacc_is_only_cost_of_equity_nflx(analysis):
    km = analysis("NFLX")["key_metrics"]
    assert km["total_debt"] and km["total_debt"] > 0  # empresa apalancada
    ke = RF + km["beta"] * MRP
    assert abs(km["wacc"] - ke) > 1e-4


@pytest.mark.xfail(raises=AssertionError, reason="RECON §6.5: el DCF topa el crecimiento en 30% y el grid en 50% (y con "
                          "decay distinto): SNOW DCF $142.6 vs caso base del grid $318.9")
def test_bug_dcf_vs_grid_growth_snow(analysis):
    a = analysis("SNOW")
    fair = a["dcf"]["fair_value"]
    base = a["sensitivity"]["base_case"]["fair_value"]
    assert base == pytest.approx(fair, rel=0.01)


@pytest.mark.xfail(raises=AssertionError, reason="RECON §1.4: el PDF exige sensitivity['base_growth_idx'/'base_discount_idx'] "
                          "que dcf_sensitivity_analysis nunca devuelve: el recuadro base no se dibuja")
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


@pytest.mark.xfail(raises=AssertionError, reason="RECON C6: revenueGrowth de Yahoo para JPM (30.4%) es un artefacto de la "
                          "definición de 'revenue' bancario; los estados dan ~7% interanual")
def test_bug_jpm_revenue_growth_artifact(analysis, fixture_store):
    inc = _frame(fixture_store, "JPM", "income_stmt")
    rev = inc.loc["Total Revenue"]
    statement_yoy = float(rev.iloc[0]) / float(rev.iloc[1]) - 1
    km = analysis("JPM")["key_metrics"]
    assert abs(km["revenue_growth"] - statement_yoy) < 0.05


# CORREGIDO en la etapa 3 (bug a): el plan B toma sector/industria de la búsqueda de Yahoo.
def test_bug_prod_sector_unknown_outside_known_list_o(outputs_by_env):
    import conftest
    if "prod" not in conftest.ENVS:
        pytest.skip("falta el juego prod")
    profile = outputs_by_env("prod")["O"][0]["profile"]
    assert profile["sector"] == "Real Estate"
