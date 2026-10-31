"""
F10 · margen operativo con una sola verdad (puerta de la v4, 29-oct: regla `margen_operativo_unico`, 46 empresas).
El margen operativo que se enseña y puntúa es el del EBIT que presenta el emisor (SEC EDGAR, fuente principal desde la
fase 3), pero la normalización medía el beneficio con la fila trimestral «Operating Income» de Yahoo: dos cifras del
mismo periodo (GILD −8,2 % frente a 38,5 %). Y los cargos que la normalización ya quita del beneficio (deterioros,
litigios, reestructuración) seguían dentro del operativo que puntúa, mientras que el margen neto puntúa sin ellos.
Regla:
  1. una sola cifra: las piezas de la normalización usan el operativo del corte (el que se enseña); la fila trimestral
     de Yahoo solo como respaldo declarado, cuando el corte no es del mismo periodo;
  2. puntúa el margen operativo sin los cargos operativos que la normalización ya quita (como el margen neto); se
     enseñan las dos cifras, el reportado y el normalizado con su motivo.
"""
import pytest

from normalize import fy_operating, operating, pieces_operating_income
from settings import cfg

B = 1e9


def _it(row, gross, applied=True, kind="explicita", recurrent=False):
    return {"type": kind, "item_type": row, "label": row, "applied": applied, "gross": gross * B,
            "period_gross": gross * B, "net": gross * B * 0.8, "recurrent": recurrent}


# ── 2. El operativo sin los cargos que la normalización ya quita ──

def test_operating_charges_come_back_and_non_operating_items_do_not():
    # GILD: 10,34 B$ de cargos especiales dentro del operativo; las ganancias por venta de valores, debajo de él
    r = operating(-2.497 * B, 30.456 * B, [_it("Special Income Charges", -10.342),
                                          _it("Gain On Sale Of Security", 1.221)])
    assert r["reported"] == pytest.approx(-2.497 * B)
    assert r["normalized"] == pytest.approx(7.845 * B)
    assert r["margin_reported"] == pytest.approx(-2.497 / 30.456)
    assert r["margin_normalized"] == pytest.approx(7.845 / 30.456)
    assert [i["item_type"] for i in r["items"]] == ["Special Income Charges"]
    assert r["differs"]


def test_operating_gains_inside_the_operating_line_also_leave():
    # simétrico, como el margen neto: un ingreso especial dentro del operativo también sale
    r = operating(5 * B, 50 * B, [_it("Special Income Charges", 1.5)])
    assert r["normalized"] == pytest.approx(3.5 * B)


@pytest.mark.parametrize("row", ["Restructuring And Mergern Acquisition", "Write Off", "Asset Impairment Charge",
                                 "Impairment Of Capital Assets", "Other Special Charges"])
def test_every_operating_charge_type_counts(row):
    assert operating(1 * B, 10 * B, [_it(row, -0.5)])["normalized"] == pytest.approx(1.5 * B)


def test_only_applied_items_and_only_their_non_recurrent_excess():
    # recurrente: el ítem ya trae solo el exceso sobre su promedio (gross); no aplicado: no cuenta
    r = operating(1 * B, 10 * B, [_it("Special Income Charges", -0.2, recurrent=True),
                                  _it("Write Off", -3, applied=False)])
    assert r["normalized"] == pytest.approx(1.2 * B)


@pytest.mark.parametrize("kind,row", [("inferida", "pico_no_operativo"), ("coherencia", "ganancias_no_operativas"),
                                      ("despues_de_impuestos", "beneficio_despues_de_impuestos"),
                                      ("discontinuadas", "operaciones_discontinuadas"),
                                      ("explicita", "Gain On Sale Of Security")])
def test_items_outside_the_operating_line_do_not_touch_it(kind, row):
    # inferidas, coherencia, después de impuestos, discontinuadas y ganancias por venta de valores: debajo del operativo
    r = operating(1 * B, 10 * B, [_it(row, -0.5, kind=kind)])
    assert r["normalized"] == pytest.approx(1 * B) and not r["differs"] and not r["items"]


def test_below_the_label_threshold_the_reported_figure_scores():
    tol = cfg("thresholds.normalization.label_min_diff")
    r = operating(10 * B, 100 * B, [_it("Special Income Charges", -10 * tol / 2)])
    assert not r["differs"]


def test_without_operating_income_or_revenue_there_is_nothing_to_normalize():
    assert operating(None, 10 * B, [])["normalized"] is None
    assert operating(1 * B, 0, [])["margin_normalized"] is None


def test_the_operating_types_are_configuration():
    assert "Special Income Charges" in cfg("thresholds.normalization.operating_item_types")


def test_a_gain_that_the_non_operating_result_explains_is_below_the_line():
    # WDC: +5,77 B$ de «Special Income Charges» con 10,61 B$ antes de impuestos sobre 5,71 B$ de operativo: 4,98 B$ no
    # operativos (la participación en Sandisk). La identidad del estado del emisor dice que la ganancia va debajo del
    # operativo: solo lo que el no operativo no explica (0,79 B$) estaba dentro
    r = operating(5.71 * B, 14.48 * B, [_it("Special Income Charges", 5.77)], pretax=10.61 * B,
                  net_interest=-0.08 * B)
    assert r["below_the_line"] == pytest.approx(4.98 * B)
    assert r["gross"] == pytest.approx(0.79 * B)
    assert r["normalized"] == pytest.approx((5.71 - 0.79) * B)


def test_a_gain_fully_explained_below_the_line_does_not_touch_the_operating_margin():
    # GEV: +4,19 B$ (la venta de Prolec) con 5,42 B$ no operativos: todo debajo del operativo
    r = operating(2.83 * B, 44.04 * B, [_it("Special Income Charges", 4.19)], pretax=8.91 * B,
                  net_interest=0.66 * B)
    assert r["gross"] == pytest.approx(0.0) and r["normalized"] == pytest.approx(2.83 * B) and not r["differs"]


def test_charges_inside_the_operating_line_come_back_whole():
    # GILD y FANG: el no operativo es positivo (ganancias): no explica ningún cargo; los cargos estaban dentro
    r = operating(1.08 * B, 16.98 * B, [_it("Special Income Charges", -3.6)], pretax=1.85 * B, net_interest=-0.27 * B)
    assert r["below_the_line"] == pytest.approx(0.0) and r["normalized"] == pytest.approx(4.68 * B)


def test_non_operating_items_already_identified_are_not_counted_twice_below_the_line():
    # 1 B$ no operativo, del que 0,8 B$ son ganancias por venta de valores ya identificadas: solo 0,2 B$ pueden ser
    # parte del ingreso especial de 0,5 B$
    r = operating(5 * B, 50 * B, [_it("Special Income Charges", 0.5), _it("Gain On Sale Of Security", 0.8)],
                  pretax=6 * B)
    assert r["below_the_line"] == pytest.approx(0.2 * B) and r["gross"] == pytest.approx(0.3 * B)


# ── 1. Una sola cifra: las piezas con el operativo del corte ──

def test_pieces_use_the_cut_operating_income_when_it_is_the_same_period():
    # FIX: 0,99 B$ del EBIT de EDGAR (el que se enseña) frente a 2,09 B$ de la suma trimestral de Yahoo
    r = pieces_operating_income(0.990 * B, {"period_end": "2026-06-30", "period_type": "ttm", "source": "sec_edgar"},
                                "2026-06-30", 2.089 * B)
    assert r["value"] == pytest.approx(0.990 * B)
    assert "EDGAR" in r["source"]
    assert r["yahoo_quarterly"] == pytest.approx(2.089 * B)


def test_pieces_fall_back_to_yahoo_quarterly_declared_when_the_cut_is_another_period():
    r = pieces_operating_income(0.990 * B, {"period_end": "2025-12-31", "period_type": "fy", "source": "sec_edgar"},
                                "2026-06-30", 2.089 * B)
    assert r["value"] == pytest.approx(2.089 * B)
    assert "respaldo" in r["source"]
    r = pieces_operating_income(None, None, "2026-06-30", 2.089 * B)
    assert r["value"] == pytest.approx(2.089 * B) and "respaldo" in r["source"]


def test_pieces_from_yahoo_cut_say_so():
    r = pieces_operating_income(2.089 * B, {"period_end": "2026-06-30", "period_type": "ttm"}, "2026-06-30",
                                2.089 * B)
    assert r["value"] == pytest.approx(2.089 * B) and "Yahoo" in r["source"] and "respaldo" not in r["source"]


# ── Puntuación y página ──

def test_the_scored_row_says_normalized():
    from financial_ratios import label_normalized
    cats = [{"adjustments": [{"metric": "Margen operativo", "value": "25.76%"}]}]
    label_normalized(cats, ["operating_margin"])
    assert cats[0]["adjustments"][0]["metric"] == "Margen operativo normalizado"
    assert cats[0]["adjustments"][0]["normalized"]


def test_golden_v_shows_both_figures_and_scores_the_normalized():
    # V (réplica del panel): 0,99 B$ de cargos especiales dentro del EBIT de EDGAR; reportado 60,7 %, normalizado 62,9 %
    import json
    import os
    with open(os.path.join(os.path.dirname(__file__), "golden", "panel", "V.json"), encoding="utf-8") as fh:
        a = json.load(fh)
    op, km = a["earnings_normalization"]["operating"], a["key_metrics"]
    assert "EDGAR" in op["pieces_source"] and op["reported"] == pytest.approx(km["operating_income"])
    assert km["operating_margin_normalized"] == pytest.approx(op["margin_normalized"])
    keys = [r["key"] for r in a["display"]["sections"]["profitability"]["rows"]]
    assert keys.index("operating_margin_normalized") == keys.index("operating_margin") + 1
    row = next(r for r in a["display"]["sections"]["profitability"]["rows"] if r["key"] == "operating_margin_normalized")
    assert "cargos especiales" in row["text"] and "Es el que puntúa" in row["text"]
    scored = next(x for x in a["score"]["breakdown"]["Rentabilidad"]["adjustments"]
                  if x["metric"].startswith("Margen operativo"))
    assert scored["metric"] == "Margen operativo normalizado"
    assert scored["value"] == f"{km['operating_margin_normalized']:.2%}"


# ── Ventas de negocios o activos dentro del operativo (Plan, 29-oct: SOLV, BA) ──

def test_a_gain_on_a_sale_inside_the_operating_line_leaves_it():
    # SOLV: +1,47 B$ del total de Yahoo (la venta de P&F, sin componentes que cuadren); 2,08 B$ de operativo con 1,70 B$
    # antes de impuestos: el no operativo (−0,11 B$) no explica ninguna ganancia: estaba dentro del operativo
    r = operating(2.076 * B, 8.309 * B, [_it("Total Unusual Items", 1.467)], pretax=1.696 * B, net_interest=-0.266 * B)
    assert r["below_the_line"] == pytest.approx(0.0)
    assert r["normalized"] == pytest.approx((2.076 - 1.467) * B)


@pytest.mark.parametrize("row", ["Gain On Sale Of Business", "Gain On Sale Of Ppe"])
def test_sales_of_businesses_or_assets_count_in_both_directions(row):
    assert operating(1 * B, 10 * B, [_it(row, 0.4)])["normalized"] == pytest.approx(0.6 * B)
    assert operating(1 * B, 10 * B, [_it(row, -0.4)])["normalized"] == pytest.approx(1.4 * B)


def test_the_non_operating_result_only_explains_items_of_its_own_sign():
    # 10 B$ de cargos dentro del operativo y una ganancia por venta de 3 B$ debajo (el no operativo es +3 B$): la
    # ganancia sale debajo y los cargos se devuelven enteros
    r = operating(-2 * B, 30 * B, [_it("Special Income Charges", -10), _it("Gain On Sale Of Business", 3)],
                  pretax=1 * B)
    assert r["below_the_line"] == pytest.approx(3 * B)
    assert r["normalized"] == pytest.approx(8 * B)


# ── Sin TTM trimestral: el margen del último ejercicio de los estados (verificación, regla 4: CRL, FDXF) ──

def test_without_a_quarterly_cut_the_margin_is_the_last_fiscal_year():
    # CRL: quoteSummary daba 604 M$ (sin el deterioro); el ejercicio presentado es 25 M$ sobre 4.050 M$
    r = fy_operating({"inc_years": ["2025", "2024"], "operating_income": [25e6, 300e6], "revenue": [4050e6, 4100e6]})
    assert r["value"] == pytest.approx(25 / 4050)
    assert r["operating_income"] == pytest.approx(25e6) and r["year"] == "2025"


def test_without_the_fiscal_year_pieces_there_is_no_margin_to_replace():
    assert fy_operating({"operating_income": [None], "revenue": [4050e6]}) is None
    assert fy_operating({"operating_income": [25e6], "revenue": [0]}) is None
    assert fy_operating({}) is None


def test_charges_corroborated_by_edgar_operating_tags_stay_inside():
    # ABBV: 2,67 B$ de cargos especiales (Yahoo) y un no operativo negativo (pagos contingentes): la identidad sola los
    # mandaría debajo; EDGAR presenta 4,98 B$ de I+D adquirida, un gasto operativo: están dentro
    r = operating(16.0 * B, 61.0 * B, [_it("Special Income Charges", -2.668)], pretax=10.0 * B,
                  net_interest=-1.0 * B, known_inside=-4.98 * B)
    assert r["below_the_line"] == pytest.approx(0.0)
    assert r["normalized"] == pytest.approx((16.0 + 2.668) * B)


def test_only_the_charges_edgar_does_not_corroborate_go_through_the_identity():
    r = operating(16.0 * B, 61.0 * B, [_it("Special Income Charges", -10.0)], pretax=10.0 * B,
                  net_interest=-1.0 * B, known_inside=-3.0 * B)
    # 3 B$ dentro por EDGAR; de los 7 restantes, el no operativo (−5 B$) explica 5 debajo
    assert r["below_the_line"] == pytest.approx(-5.0 * B)
    assert r["normalized"] == pytest.approx((16.0 + 5.0) * B)
