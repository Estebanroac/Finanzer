"""F10 · N1 (revisión del informe de NVIDIA, 28-oct-2026): ganancias no operativas que la operación no explica
(lib/normalize.coherence). Cifras TTM a julio de 2026 de NVDA (Yahoo; EDGAR: GainLossOnInvestments 15,94 B$ en abril y
7,77 B$ en julio) y casos de control."""
import pytest

from normalize import coherence, normalize
from settings import cfg

TOL = cfg("thresholds.normalization.nonoperating_tolerance_revenue")
# named_gains: las ganancias de inversiones que presenta el emisor en EDGAR (GainLossOnInvestments, TTM: 30,55 B$): la
# partida que nombra el recorte (Plan, 29-oct)
NVDA = {"operating_income": 197.579e9, "net_interest": 1.765e9, "equity_income": 0.0, "pretax": 229.744e9,
        "tax": 36.865e9, "revenue": 302.969e9, "named_gains": 30.55e9}


def test_nvda_gains_above_what_operations_explain_leave_the_score():
    """NVDA: 30,4 B$ no operativos antes de impuestos; Yahoo ya marcó 7,77 (julio); sale lo que pasa del 2 % de los
    ingresos, neto al tipo efectivo (16 %)."""
    co = coherence(NVDA, already_gross=7.771e9)
    assert co["nonoperating"] == pytest.approx(30.4e9)
    assert co["residual"] == pytest.approx(30.4e9 - 7.771e9)
    assert co["excess"] == pytest.approx(co["residual"] - TOL * NVDA["revenue"])
    assert co["named"] == pytest.approx(30.55e9 - 7.771e9)
    assert co["gross"] == pytest.approx(co["excess"]) and co["unexplained"] == pytest.approx(0.0)
    assert co["out"] == pytest.approx(co["gross"] * (1 - NVDA["tax"] / NVDA["pretax"]))
    assert co["applied"] and 13e9 < co["out"] < 15e9


def test_within_tolerance_and_equity_method_are_operations():
    """KO: su resultado de participadas (embotelladoras) cuenta como operación; dentro de la tolerancia nada sale."""
    ko = {"operating_income": 15.9e9, "net_interest": -0.73e9, "equity_income": 2.11e9, "pretax": 17.6e9,
          "tax": 2.9e9, "revenue": 47.0e9}
    co = coherence(ko)
    assert not co["applied"] and co["out"] == 0.0
    assert co["nonoperating"] == pytest.approx(17.6e9 - (15.9e9 - 0.73e9 + 2.11e9))


def test_continuous_only_the_part_above_the_tolerance():
    base = dict(NVDA, pretax=NVDA["operating_income"] + NVDA["net_interest"])
    tol = TOL * base["revenue"]
    outs = [coherence(dict(base, pretax=base["pretax"] + x))["gross"] for x in (tol - 1e6, tol, tol + 1e6, tol + 2e6)]
    assert outs[0] == outs[1] == 0.0 and outs[2] == pytest.approx(1e6) and outs[3] == pytest.approx(2e6)


def test_tax_credits_do_not_look_like_gains():
    """NEE: impuesto negativo (créditos fiscales) → tipo acotado a 0, y se mira antes de impuestos: el crédito no es
    una ganancia no operativa."""
    nee = {"operating_income": 8.1e9, "net_interest": -3.5e9, "equity_income": 0.8e9, "pretax": 5.4e9, "tax": -0.6e9,
           "revenue": 28.7e9}
    co = coherence(nee)
    assert co["tax_rate"] == 0.0 and co["nonoperating"] == pytest.approx(0.0, abs=1e3) and not co["applied"]


@pytest.mark.parametrize("parts,why", [
    ({"operating_income": None, "revenue": 1.0, "pretax": 1.0, "tax": 0.2}, "sin resultado operativo"),
    ({"operating_income": 1.0, "revenue": 1.0, "pretax": -1.0, "tax": 0.0}, "no positivo"),
])
def test_without_a_basis_nothing_is_removed(parts, why):
    co = coherence(parts)
    assert not co["applied"] and why in co["reason"]


def test_in_normalize_it_is_one_more_item_and_not_with_structural_gains():
    n = normalize(net_income=192.879e9, explicit_rows={"Total Unusual Items": 7.771e9}, quarterly=None,
                  basis="TTM (4 trimestres)", tax_rate_fallback=0.16, coherence_parts=NVDA)
    co = [i for i in n["items"] if i["type"] == "coherencia"]
    assert len(co) == 1 and co[0]["applied"] and co[0]["item_type"] == "ganancias_no_operativas"
    assert n["normalized_net_income"] == pytest.approx(192.879e9 - sum(i["net"] for i in n["items"] if i["applied"]))
    assert n["coherence"]["already_normalized"] == pytest.approx(7.771e9)
    # aseguradora o conglomerado: la cartera ya sale entera como partida estructural; no se mira otra vez
    s = normalize(net_income=192.879e9, explicit_rows={}, quarterly=None, basis="TTM", tax_rate_fallback=0.16,
                  investment_gains={"value": 20e9, "concept": "x", "how": "y"}, coherence_parts=NVDA)
    assert s["coherence"] is None and not any(i["type"] == "coherencia" for i in s["items"])


# ── Plan, 29-oct: N1 solo recorta lo que puede nombrar ──

def test_an_excess_without_a_named_item_is_not_cut_but_declared():
    # D, ECHO: «otros ingresos» sin partida que los nombre (AFUDC, fideicomisos): no se recortan; se declaran
    co = coherence({k: v for k, v in NVDA.items() if k != "named_gains"}, already_gross=7.771e9)
    assert co["gross"] == 0.0 and co["out"] == 0.0 and not co["applied"]
    assert co["unexplained"] == pytest.approx(co["excess"]) and co["excess"] > 0


def test_the_cut_is_the_smaller_of_the_excess_and_what_is_named():
    co = coherence(dict(NVDA, named_gains=7.771e9 + 5e9), already_gross=7.771e9)
    assert co["gross"] == pytest.approx(5e9)
    assert co["unexplained"] == pytest.approx(co["excess"] - 5e9)
