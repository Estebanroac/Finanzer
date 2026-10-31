"""
F10 · N1b (escaneo de control del 29-oct, regla `margen_neto_techo`: 28 empresas): N1 mira antes de impuestos, de
minoritarios y de discontinuadas, y se le escapan (1) las operaciones discontinuadas (OXY: la venta de OxyChem, 3,12 B$
en un trimestre) y (2) lo que entra después de impuestos: participadas netas de impuestos (FIS: 2,21 B$ de la venta de
su parte de Worldpay; MKC: 0,89 B$) y beneficios fiscales puntuales (UBER: −4,05 B$ de impuestos en un trimestre).
Regla: el normalizado parte del beneficio de operaciones continuadas (las discontinuadas salen y se dicen) y, después
de impuestos, no puede superar (operativo + financieros netos + participadas) × (1 − t normalizada) + 2 pp de los
ingresos; el exceso sale con su motivo. t normalizada: la mediana de los tipos efectivos no negativos del periodo y los
últimos ejercicios; con menos de `tax_median_min` de ellos, el tipo legal.
"""
import pytest

from normalize import normalize, tax_rate_normalized
from settings import cfg

B = 1e9


def _parts(op, rev, pt, tx, nint=0.0, eq=0.0, eq_net=None, fy=()):
    return {"operating_income": op * B, "revenue": rev * B, "pretax": pt * B, "tax": tx * B, "net_interest": nint * B,
            "equity_income": eq * B, "equity_income_net_of_tax": None if eq_net is None else eq_net * B,
            "tax_history": [(p * B, t * B) for p, t in fy]}


def _norm(ni, parts=None, disc=None, rows=None):
    return normalize(net_income=ni * B, explicit_rows=rows or {}, quarterly=None, basis="TTM (4 trimestres)",
                     coherence_parts=parts, discontinued=None if disc is None else {
                         "value": disc * B, "source": "Yahoo (prueba)", "period_total": ni * B})


def _item(r, kind):
    return next((i for i in r["items"] if i["type"] == kind), None)


def test_discontinued_operations_leave_the_normalized_and_are_declared():
    # OXY: 6,53 B$ del común con 3,38 B$ de discontinuadas (OxyChem)
    r = _norm(6.532, _parts(5.883, 21.671, 5.287, 1.433, nint=-0.746, eq=0.304, fy=[(3.05, 1.02), (3.27, 1.16),
                                                                                   (4.24, 1.33)]), disc=3.381)
    d = _item(r, "discontinuadas")
    assert d and d["applied"] and d["net"] == pytest.approx(3.381 * B)
    assert "discontinuadas" in d["label"] and "Yahoo" in d["origin"]
    assert r["normalized_net_income"] == pytest.approx((6.532 - 3.381) * B)
    assert _item(r, "despues_de_impuestos") is None          # el continuado cabe en su techo


def test_discontinued_already_outside_the_income_used_are_not_subtracted_again():
    # UL en vivo: el beneficio usado (6,48 B) ya es el continuado; el FY2025 lleva 9,47 B con 3,80 B de discontinuadas
    r = normalize(net_income=6.48 * B, explicit_rows={}, quarterly=None, basis="FY2025 (sin TTM)",
                  discontinued={"value": 3.798 * B, "source": "Yahoo (prueba)", "period_total": 9.469 * B})
    d = _item(r, "discontinuadas")
    assert d and not d["applied"] and "ya es el de operaciones continuadas" in d["origin"]
    assert r["normalized_net_income"] == pytest.approx(6.48 * B)


def test_loss_from_discontinued_returns_to_the_normalized():
    r = _norm(1.0, None, disc=-0.4)
    assert r["normalized_net_income"] == pytest.approx(1.4 * B)


def test_after_tax_equity_gain_is_normalized_with_its_reason():
    # FIS: 3,37 B$ con 1,36 B$ antes de impuestos; 2,21 B$ de participadas netas de impuestos (Worldpay)
    p = _parts(2.036, 12.201, 1.36, 0.342, nint=-0.575, eq_net=2.394, fy=[(1.176, 0.265), (1.297, 0.362),
                                                                       (0.662, 0.157), (0.898, 0.314)])
    r = _norm(3.371, p)
    x = _item(r, "despues_de_impuestos")
    assert x and x["applied"]
    t = r["after_tax"]["tax_rate"]
    ceiling = (2.036 - 0.575) * B * (1 - t) + cfg("thresholds.normalization.nonoperating_tolerance_revenue") * 12.201 * B
    assert x["net"] == pytest.approx(3.371 * B - ceiling)
    assert "participadas netas de impuestos" in x["origin"]


def test_one_off_tax_benefit_uses_the_statutory_rate_without_enough_normal_years():
    # UBER: impuestos del periodo −3,05 B$ (liberación de la provisión por activos fiscales diferidos)
    p = _parts(6.7, 55.227, 6.684, -3.052, nint=0.278, fy=[(5.8, -4.346), (4.125, -5.758), (2.321, 0.213)])
    r = _norm(9.579, p)
    at = r["after_tax"]
    assert at["tax_rate"] == pytest.approx(cfg("valuation.tax.statutory_rate"))
    assert "legal" in at["tax_source"]
    x = _item(r, "despues_de_impuestos")
    assert x and "tipo efectivo del periodo" in x["origin"] and "negativo" in x["origin"]


def test_normal_years_give_the_median_rate():
    t = tax_rate_normalized(1.0 * B, 0.02 * B, [(1 * B, 0.20 * B), (1 * B, 0.22 * B), (1 * B, 0.19 * B)])
    assert t["rate"] == pytest.approx(0.195) and "mediana" in t["source"]


def test_recurring_low_rate_is_not_anomalous():
    # utility con créditos fiscales recurrentes (NEE): tipos bajos, pero positivos todos los años: fuera de alcance
    t = tax_rate_normalized(1.0 * B, 0.03 * B, [(1 * B, 0.05 * B), (1 * B, 0.02 * B), (1 * B, 0.04 * B)])
    assert t["rate"] == pytest.approx(0.035)


def test_continuous_at_the_tolerance():
    tol = cfg("thresholds.normalization.nonoperating_tolerance_revenue")
    fy = [(1.0, 0.2), (1.0, 0.2), (1.0, 0.2)]
    base = 1.0 * B * 0.8 + tol * 10 * B
    # (con 1 B$ de ganancias de inversiones nombradas en EDGAR: el exceso tiene con qué recortarse; Plan, 29-oct)
    p = {**_parts(1.0, 10.0, 1.0, 0.2, fy=fy), "named_gains": 1.0 * B}
    below = _norm(base / B - 0.001, p)
    above = _norm(base / B + 0.05, p)
    assert _item(below, "despues_de_impuestos") is None
    assert _item(above, "despues_de_impuestos")["net"] == pytest.approx(0.05 * B)


def test_charges_returned_raise_the_ceiling():
    # un deterioro dentro del resultado operativo que la normalización devuelve no se toma por exceso
    fy = [(1.0, 0.2), (1.0, 0.2), (1.0, 0.2)]
    r = _norm(0.8, _parts(1.0, 10.0, 1.0, 0.2, fy=fy), rows={"Asset Impairment Charge": 1.0 * B})
    assert _item(r, "despues_de_impuestos") is None


def test_no_parts_no_after_tax_check():
    r = _norm(5.0, None)
    assert r["after_tax"] is None and _item(r, "despues_de_impuestos") is None


def test_minority_share_is_attribution_not_a_gain():
    # NEE: los minoritarios absorben pérdidas (+1,86 B$ al accionista): el techo los suma como se reportan
    fy = [(1.0, 0.2), (1.0, 0.2), (1.0, 0.2)]
    p = {**_parts(1.0, 10.0, 1.0, 0.2, fy=fy), "minority_interests": 0.5 * B}
    assert _item(_norm(1.0 * 0.8 + 0.5 + 0.1, p), "despues_de_impuestos") is None
    assert _item(_norm(1.0 * 0.8 + 0.1, {**p, "minority_interests": None}), "despues_de_impuestos") is None


def test_ul_spin_off_is_discontinued_and_its_pe_is_market_cap_over_continuing():
    """UL (panel): la escisión de los helados (Magnum) es discontinuada; el P/E normalizado es capitalización /
    beneficio continuado normalizado (el BPA de Yahoo no tiene una base fija con discontinuadas)."""
    import json
    import os
    with open(os.path.join(os.path.dirname(__file__), "golden", "panel", "UL.json"), encoding="utf-8") as fh:
        a = json.load(fh)
    en = a["earnings_normalization"]
    d = next(i for i in en["items"] if i["type"] == "discontinuadas")
    assert d["applied"] and d["net"] > 0
    assert en["pe_normalized"] == pytest.approx(a["key_metrics"]["market_cap"] / en["normalized_net_income"])
    assert "continuadas" in en["pe_normalized_basis"]


# ── Plan, 29-oct: N1b solo recorta lo que puede nombrar ──

def test_after_tax_cut_needs_a_named_item():
    # el mismo exceso que «continuous_at_the_tolerance», sin participadas, sin beneficio fiscal y sin ganancias
    # nombradas: no se recorta; se declara
    tol = cfg("thresholds.normalization.nonoperating_tolerance_revenue")
    fy = [(1.0, 0.2), (1.0, 0.2), (1.0, 0.2)]
    r = _norm((1.0 * B * 0.8 + tol * 10 * B) / B + 0.05, _parts(1.0, 10.0, 1.0, 0.2, fy=fy))
    assert _item(r, "despues_de_impuestos") is None
    assert r["after_tax"]["unexplained"] == pytest.approx(0.05 * B)
    assert r["unexplained"]["after_tax"] == pytest.approx(0.05 * B)


def test_a_tax_benefit_against_the_normalized_rate_is_named():
    # UBER: impuestos de −3,05 B$ frente al 21 % legal: 4,46 B$ de beneficio fiscal nombrado
    p = _parts(6.7, 55.227, 6.684, -3.052, nint=0.278, fy=[(5.8, -4.346), (4.125, -5.758), (2.321, 0.213)])
    at = _norm(9.579, p)["after_tax"]
    assert at["named_tax_benefit"] == pytest.approx(0.21 * 6.684 * B + 3.052 * B)
    assert at["out"] == pytest.approx(min(at["excess"], at["named"]))


def test_a_tax_benefit_on_a_loss_is_not_named():
    # ECHO: pérdida antes de impuestos con impuesto negativo: no es un beneficio fiscal puntual
    p = _parts(-16.5, 14.6, -8.6, -2.93, fy=[(1.0, 0.2), (1.0, 0.2), (1.0, 0.2)])
    at = _norm(0.47, p)["after_tax"]
    assert at["named_tax_benefit"] == 0.0 and at["out"] == 0.0 and at["unexplained"] > 0


def test_named_gains_left_by_n1_are_named_after_tax():
    tol = cfg("thresholds.normalization.nonoperating_tolerance_revenue")
    fy = [(1.0, 0.2), (1.0, 0.2), (1.0, 0.2)]
    p = {**_parts(1.0, 10.0, 1.0, 0.2, fy=fy), "named_gains": 0.03 * B}
    r = _norm((1.0 * B * 0.8 + tol * 10 * B) / B + 0.05, p)
    assert _item(r, "despues_de_impuestos")["net"] == pytest.approx(0.03 * B * 0.8)


def test_an_unexplained_excess_lowers_the_confidence_only_if_it_is_material():
    from valuation_confidence import source_dimension
    tol = cfg("thresholds.normalization.label_min_diff")

    def issues(un):
        n = {"reported_net_income": 100 * B, "unexplained": {"pre_tax": 0.0, "after_tax": un}}
        return source_dimension(input_flags=[], normalization=n, ttm=None, provenance_fields={})["reasons"]
    assert issues(100 * B * tol * 0.5) == []                               # MSFT: 48 M$ sobre 130 B$
    assert any("no se recorta" in x for x in issues(100 * B * tol * 2))    # PLTR: ~3 % del beneficio
