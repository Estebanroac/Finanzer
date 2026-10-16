"""
Fase 2b (T3): corte coherente (F2_PRECEDENCIA §1). Todos los campos de los estados pertenecen al mismo corte
(`as_of`): el último trimestre con ingresos y beneficio de 4 trimestres consecutivos y balance a esa fecha. Lo que
no es de ese corte se descarta con aviso (validate: periodo_incoherente); Finnhub solo entra si casa con el corte.
"""
import pandas as pd
import pytest

from ttm import build_ttm


def _q(dates, rows):
    return pd.DataFrame(rows, index=pd.to_datetime(dates)).T


Q5 = ["2026-06-30", "2026-03-31", "2025-12-31", "2025-09-30", "2025-06-30"]


def test_cut_is_the_last_quarter_with_core_flows_and_balance():
    """AMZN/BAC: resultados a junio y balance a marzo → el corte es marzo, para todo."""
    inc = _q(Q5, {"Total Revenue": [12, 11, 10, 9, 8], "Net Income": [3, 2, 2, 1, 1]})
    cf = _q(Q5, {"Operating Cash Flow": [5, 4, 4, 3, 3]})
    bs = _q(Q5[1:], {"Total Assets": [90, 80, 70, 60]})
    t = build_ttm(inc, cf, bs)
    assert t["cut"] == "2026-03-31" and t["balance_date"] == "2026-03-31"
    assert t["values"]["totalRevenue"] == 38 and t["values"]["netIncome"] == 6
    assert t["values"]["operatingCashflow"] == 14 and t["values"]["totalAssets"] == 90
    assert t["quarters"]["inc"] == Q5[1:]
    assert t["quarterly"]["dates"][0] == "2026-03-31"


def test_core_gap_in_the_newest_quarter_moves_the_cut_back():
    inc = _q(Q5, {"Total Revenue": [12, 11, 10, 9, 8], "Net Income": [None, 2, 2, 1, 1]})
    bs = _q(Q5, {"Total Assets": [100, 90, 80, 70, 60]})
    t = build_ttm(inc, None, bs)
    assert t["cut"] == "2026-03-31" and t["values"]["totalAssets"] == 90


def test_non_core_field_without_four_quarters_at_the_cut_is_marked_with_its_reason():
    inc = _q(Q5, {"Total Revenue": [12, 11, 10, 9, 8], "Net Income": [3, 2, 2, 1, 1]})
    cf = _q(Q5, {"Operating Cash Flow": [5, 4, 4, 3, 3], "Common Stock Dividend Paid": [-1, None, -1, -1, -1]})
    bs = _q(Q5, {"Total Assets": [100, 90, 80, 70, 60]})
    t = build_ttm(inc, cf, bs)
    assert t["cut"] == "2026-06-30" and "dividendsPaid" not in t["values"]
    assert "sin dato en alguno de los 4 trimestres del corte" in t["missing"]["dividendsPaid"]


def test_no_quarterly_cut_means_annual_cut_without_quarterly_balance():
    """UL: sin cuenta de resultados trimestral, el corte es el ejercicio y el balance no se toma del trimestre."""
    bs = _q(Q5, {"Total Assets": [100, 90, 80, 70, 60]})
    t = build_ttm(None, None, bs)
    assert t["cut"] is None and t["balance_date"] is None and "totalAssets" not in t["values"]
    assert t["missing"]["totalAssets"] == "sin corte trimestral: el balance es el del ejercicio"


def test_quarterly_cash_flow_is_part_of_the_cut_when_the_issuer_reports_it():
    """ASML: flujos trimestrales hasta marzo, resultados y balance hasta junio → corte en marzo."""
    inc = _q(Q5, {"Total Revenue": [12, 11, 10, 9, 8], "Net Income": [3, 2, 2, 1, 1]})
    cf = _q(Q5[1:], {"Operating Cash Flow": [4, 4, 3, 3]})
    bs = _q(Q5, {"Total Assets": [100, 90, 80, 70, 60]})
    assert build_ttm(inc, cf, bs)["cut"] == "2026-03-31"
    assert build_ttm(inc, None, bs)["cut"] == "2026-06-30"        # sin flujos trimestrales (BCS, HSBC)


def test_ttm_eps_is_the_sum_of_the_four_quarterly_diluted_eps():
    """RIVN: con dilución, beneficio TTM / acciones del último trimestre sesga el BPA (−2.44 frente a −2.59 de
    EDGAR). El BPA TTM es la suma de los BPA diluidos de los 4 trimestres del corte."""
    inc = _q(Q5, {"Total Revenue": [12, 11, 10, 9, 8], "Net Income": [-4, -4, -4, -4, -4],
                  "Diluted EPS": [-0.40, -0.42, -0.44, -0.46, -0.5],
                  "Diluted Average Shares": [10, 9.5, 9.1, 8.7, 8]})
    bs = _q(Q5, {"Total Assets": [100, 90, 80, 70, 60]})
    t = build_ttm(inc, None, bs)
    assert t["eps"]["value"] == pytest.approx(-1.72) and t["eps"]["basis"] == "suma_bpa_trimestral"
    inc2 = inc.drop(index="Diluted EPS")
    t2 = build_ttm(inc2, None, bs)
    assert t2["eps"]["value"] == pytest.approx(-16 / ((10 + 9.5 + 9.1 + 8.7) / 4))
    assert t2["eps"]["basis"] == "beneficio_entre_acciones_medias"
