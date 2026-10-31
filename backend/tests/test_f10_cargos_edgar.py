"""
F10 · cargos con etiquetas estándar de EDGAR (Plan, 29-oct). Los residuos del margen operativo sin cargos identificados
eran cargos reales que las filas de Yahoo no recogen (GIS: reestructuración y deterioros, 2,98 B$; ABBV: I+D en proceso
adquirida, 4,98 B$; INTC). Regla general, solo con etiquetas estándar us-gaap e IFRS (sin las propias del emisor):
deterioros de fondo de comercio, intangibles y activos, reestructuración, litigios, I+D adquirida y ventas de negocios
o activos. Sin doble conteo (las etiquetas paraguas frente a sus partes; lo que ya recogen las filas de Yahoo), con la
prueba de recurrencia de siempre, y dentro o debajo del operativo según la identidad del estado (normalize.operating).
"""
import datetime as dt

import pytest

import sec_edgar as edgar
from normalize import normalize
from settings import cfg

B = 1e9


def _flow(start, end, val, filed, form="10-Q"):
    return {"start": start, "end": end, "val": val, "filed": filed, "form": form, "accn": filed}


def _facts(tags):
    return {"facts": {"us-gaap": {**{t: {"units": {"USD": fs}} for t, fs in tags.items()},
                                  "Assets": {"units": {"USD": [{"end": "2026-06-30", "val": 1, "filed": "2026-08-01",
                                                                "form": "10-Q", "accn": "x"}]}}}}}


def _ttm(v_fy, v_h1, v_h1p, filed_fy="2026-02-20"):
    return [_flow("2025-01-01", "2025-12-31", v_fy, filed_fy, "10-K"), _flow("2026-01-01", "2026-06-30", v_h1, "2026-08-01"),
            _flow("2025-01-01", "2025-06-30", v_h1p, "2025-08-01")]


def test_standard_tags_add_up_without_double_counting_umbrellas():
    f = _facts({"GoodwillImpairmentLoss": _ttm(2.0 * B, 0, 0), "RestructuringCharges": _ttm(0.3 * B, 0.1 * B, 0.1 * B),
                "AssetImpairmentCharges": _ttm(0.2 * B, 0, 0),
                "RestructuringSettlementAndImpairmentProvisions": _ttm(0.6 * B, 0.1 * B, 0.1 * B),
                "ResearchAndDevelopmentInProcess": _ttm(0, 1.0 * B, 0),
                "GainLossOnSaleOfBusiness": _ttm(0.5 * B, 0, 0)})
    r = edgar.charges_ttm(f, dt.date(2026, 6, 30), 14)
    # fondo de comercio 2,0 + la paraguas 0,6 (manda sobre sus partes, que pueden solaparse: INTC) + I+D 1,0
    assert r["neg"] == pytest.approx(-(2.0 + 0.6 + 1.0) * B)
    assert "AssetImpairmentCharges" not in r["detail"] and "RestructuringCharges" not in r["detail"]
    assert r["pos"] == pytest.approx(0.5 * B)
    assert set(r["detail"]) >= {"GoodwillImpairmentLoss", "ResearchAndDevelopmentInProcess", "GainLossOnSaleOfBusiness"}


def test_the_umbrella_wins_even_if_its_parts_add_up_to_more():
    # INTC: deterioros 4,07 B$ y reestructuración 4,06 B$ que se solapan; la paraguas, 4,385 B$, es el total
    f = _facts({"AssetImpairmentCharges": _ttm(4.07 * B, 0, 0), "RestructuringCharges": _ttm(4.06 * B, 0, 0),
                "RestructuringSettlementAndImpairmentProvisions": _ttm(4.385 * B, 0, 0)})
    assert edgar.charges_ttm(f, dt.date(2026, 6, 30), 14)["neg"] == pytest.approx(-4.385 * B)


def test_the_annual_series_feeds_the_recurrence_test():
    fs = [_flow(f"{y}-01-01", f"{y}-12-31", 0.2 * B, f"{y + 1}-02-20", "10-K") for y in range(2021, 2026)]
    f = _facts({"RestructuringCharges": fs + [_flow("2026-01-01", "2026-06-30", 0.1 * B, "2026-08-01"),
                                              _flow("2025-01-01", "2025-06-30", 0.1 * B, "2025-08-01")]})
    r = edgar.charges_ttm(f, dt.date(2026, 6, 30), 14)
    n = min(5, cfg("thresholds.normalization.recurrence_window"))
    assert [a["neg"] for a in r["annual"]] == [pytest.approx(-0.2 * B)] * n


def test_without_standard_tags_there_is_nothing():
    assert edgar.charges_ttm(_facts({}), dt.date(2026, 6, 30), 14) is None


def _n(rows, ec, ni=1.0):
    return normalize(net_income=ni * B, explicit_rows=rows, quarterly=None, basis="TTM (4 trimestres)",
                     tax_rate_fallback=0.2, edgar_charges=ec)


def _edgar_items(r):
    return [i for i in r["items"] if str(i.get("item_type", "")).startswith("EDGAR")]


def test_charges_edgar_identifies_and_yahoo_does_not_are_normalized():
    # ABBV: 4,98 B$ de I+D adquirida; Yahoo no trae ninguna fila
    r = _n({}, {"neg": -4.98 * B, "pos": 0.0, "annual": [], "detail": {"ResearchAndDevelopmentInProcess": 4.98 * B}})
    it = _edgar_items(r)
    assert len(it) == 1 and it[0]["applied"] and it[0]["gross"] == pytest.approx(-4.98 * B)
    assert it[0]["net"] == pytest.approx(-4.98 * B * 0.8)
    assert r["normalized_net_income"] == pytest.approx(1.0 * B + 4.98 * B * 0.8)


def test_only_what_yahoo_does_not_already_identify():
    # Yahoo ya trae 2 B$ de cargos especiales; EDGAR, 3 B$: solo sale el B$ de más
    r = _n({"Special Income Charges": -2.0 * B}, {"neg": -3.0 * B, "pos": 0.0, "annual": [], "detail": {}})
    assert _edgar_items(r)[0]["gross"] == pytest.approx(-1.0 * B)
    r = _n({"Special Income Charges": -3.5 * B}, {"neg": -3.0 * B, "pos": 0.0, "annual": [], "detail": {}})
    assert _edgar_items(r) == []


def test_recurring_restructuring_only_its_excess():
    ann = [{"neg": -0.2 * B, "pos": 0.0}] * 5
    r = _n({}, {"neg": -0.3 * B, "pos": 0.0, "annual": ann, "detail": {}})
    it = _edgar_items(r)[0]
    assert it["recurrent"] and it["gross"] == pytest.approx(-0.1 * B)


def test_sales_of_businesses_in_both_directions():
    r = _n({}, {"neg": 0.0, "pos": 0.6 * B, "annual": [], "detail": {}})
    assert _edgar_items(r)[0]["gross"] == pytest.approx(0.6 * B)


def test_a_gain_yahoo_already_has_under_another_row_is_not_counted_again():
    # DLR: Yahoo trae la venta de inmuebles como «Gain On Sale Of Security» (0,33 B$); EDGAR, como venta de activos
    r = _n({"Gain On Sale Of Security": 0.33 * B}, {"neg": 0.0, "pos": 0.33 * B, "annual": [], "detail": {}})
    assert _edgar_items(r) == []


def test_a_sale_gain_inside_the_discontinued_operations_is_not_counted_again():
    # MLM: 1,53 B$ netos de discontinuadas (la venta a Quikrete); EDGAR da la ganancia bruta, 1,99 B$
    r = normalize(net_income=0.96 * B, explicit_rows={}, quarterly=None, basis="TTM (4 trimestres)",
                  tax_rate_fallback=0.23, discontinued={"value": 1.53 * B, "source": "prueba", "period_total": 0.96 * B},
                  edgar_charges={"neg": 0.0, "pos": 1.99 * B, "annual": [], "detail": {}})
    ev = _edgar_items(r)
    assert not ev or ev[0]["gross"] == pytest.approx(max(0.0, 1.99 - 1.53 / 0.77) * B)


def test_the_cache_keeps_only_the_recent_charges_facts():
    # Plan, 29-oct (memoria): de las etiquetas de cargos y ventas solo se guardan los periodos que se usan (el TTM y la
    # ventana de recurrencia); el resto de conceptos no se toca
    old = [_flow(f"{y}-01-01", f"{y}-12-31", 1.0, f"{y + 1}-02-20", "10-K") for y in range(2008, 2026)]
    f = _facts({"RestructuringCharges": old, "OperatingIncomeLoss": old})
    out = edgar._recent_only(f)
    ends = sorted(x["end"][:4] for x in out["facts"]["us-gaap"]["RestructuringCharges"]["units"]["USD"])
    keep = cfg("thresholds.normalization.recurrence_window") + 2
    assert ends[0] == str(2025 - keep) and ends[-1] == "2025"
    assert len(out["facts"]["us-gaap"]["OperatingIncomeLoss"]["units"]["USD"]) == len(old)
