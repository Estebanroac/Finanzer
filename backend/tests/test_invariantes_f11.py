"""
F11 · revisión externa de NU y NFLX (4-nov-2026; docs/fiabilidad/revision-nu-nflx-2026-11-04.md): las reglas de cordura
nuevas de lib/model_invariants.py.

Fixtures: la salida real de prod (main 43080175) de /api/analysis y el texto del PDF v2 de NU y NFLX del 4-nov
(tests/fixtures/f11). Cada regla salta donde la revisión verificada dice que falla y no salta donde no aplica; y cada una
deja de saltar cuando se le da la salida corregida (el criterio de aceptación de la corrección en origen). Sin red.
"""
import copy
import gzip
import json
import os

import pytest

import model_invariants as inv

HERE = os.path.dirname(os.path.abspath(__file__))
F11 = os.path.join(HERE, "fixtures", "f11")


def _load(sym):
    with gzip.open(os.path.join(F11, f"{sym}.analysis.json.gz"), "rt", encoding="utf-8") as fh:
        a = json.load(fh)
    with gzip.open(os.path.join(F11, f"{sym}.pdf_v2.txt.gz"), "rt", encoding="utf-8") as fh:
        return a, fh.read()


@pytest.fixture(scope="module")
def nu():
    return _load("NU")


@pytest.fixture(scope="module")
def nflx():
    return _load("NFLX")


def _run(rule, a, text=None):
    return inv.RULES[rule][0](a, {"pdf_text": text, "universe": None, "today": None})


# (regla, estado en NU, estado en NFLX) con la salida de prod del 4-nov
EXPECTED = [
    ("caida_avisada", inv.VIOLATION, inv.VIOLATION),
    ("riesgo_critico_medido", inv.VIOLATION, inv.NOT_APPLICABLE),
    ("una_definicion_ttm_fy", inv.VIOLATION, inv.NOT_APPLICABLE),
    ("implicito_mismo_modelo", inv.VIOLATION, inv.NOT_APPLICABLE),
    ("cota_aplicada", inv.VIOLATION, inv.OK),
    ("referencia_representativa", inv.VIOLATION, inv.VIOLATION),
    ("voto_estable", inv.NOT_APPLICABLE, inv.VIOLATION),
    ("inverso_tasa_base", inv.NOT_APPLICABLE, inv.VIOLATION),
    ("convergencia_independiente", inv.VIOLATION, inv.NOT_APPLICABLE),
    ("calidad_sin_saturar", inv.NOT_APPLICABLE, inv.VIOLATION),
    ("forward_creible", inv.NOT_APPLICABLE, inv.VIOLATION),
    ("beta_contrastada", inv.VIOLATION, inv.OK),
    ("causalidad_sostenida", inv.VIOLATION, inv.VIOLATION),
    ("metodo_citado_aplicable", inv.VIOLATION, inv.VIOLATION),
]


def test_todas_las_reglas_f11_estan_en_la_tabla():
    assert {r for r, _, _ in EXPECTED} == {k for k, (_, d) in inv.RULES.items() if d.startswith("F11")}


@pytest.mark.parametrize("rule,st_nu,st_nflx", EXPECTED, ids=[r for r, _, _ in EXPECTED])
def test_salta_donde_la_revision_verificada_dice(rule, st_nu, st_nflx, nu, nflx):
    for (a, text), want in ((nu, st_nu), (nflx, st_nflx)):
        r = _run(rule, a, text)
        assert r["state"] == want, (a["symbol"], rule, r)
        for v in r["violations"]:
            assert v["rule"] == rule and v["detail"] and v["cause"] and v["severity"] > 0


# ── Cifras de la revisión ──

def test_cifras_de_nu(nu):
    a, text = nu
    v = _run("implicito_mismo_modelo", a)["violations"][0]["values"]
    assert abs(v["sensitivity_0"] - 3.047) < 0.01 and abs(v["justified"] - 2.538) < 0.01
    v = _run("cota_aplicada", a)["violations"]
    assert abs(v[0]["values"]["growth"] - 0.852) < 0.001 and abs(v[0]["values"]["bound"] - 0.4876) < 0.001
    assert any(x["values"].get("window") == "FY2020–FY2025" for x in v)
    v = _run("referencia_representativa", a)["violations"][0]["values"]
    assert v["peers"] == 19 and v["other_region"] == 17
    det = " ".join(x["detail"] for x in _run("metodo_citado_aplicable", a, text)["violations"])
    for s in ("DCF: supuestos", "DCF inverso", "Precio de mercado", "margen neto"):
        assert s in det, s


def test_cifras_de_nflx(nflx):
    a, _ = nflx
    v = _run("voto_estable", a)["violations"][0]["values"]
    assert v["flips"] == [65.86] and abs(v["price"] - 66.44) < 0.01
    assert abs(_run("inverso_tasa_base", a)["violations"][0]["values"]["share"] - 0.2825) < 0.001
    cols = {x["values"]["column"] for x in _run("referencia_representativa", a)["violations"]}
    assert cols == {"roe", "net_margin"}


# ── La salida corregida deja de violar (criterio de aceptación de cada corrección) ──

def _fixed(a, fn):
    b = copy.deepcopy(a)
    fn(b)
    return b


def test_salida_corregida_no_viola(nu, nflx):
    a_nu, t_nu = nu
    a_nf, t_nf = nflx
    alert = {"reason": "Caída pronunciada en el año — −46.4%"}
    assert _run("caida_avisada", _fixed(a_nf, lambda b: b["alerts"]["warnings"].append(alert)))["state"] == inv.OK
    assert _run("riesgo_critico_medido", _fixed(
        a_nu, lambda b: b["confidence"]["dimensions"]["coverage"].update(level="media")))["state"] == inv.OK
    assert _run("una_definicion_ttm_fy", _fixed(
        a_nu, lambda b: b["data_provenance"]["fields"]["totalRevenue"].update(source="sec_edgar")))["state"] == inv.OK

    def two_stage_sens(b):
        s = next(x for x in b["archetype_metrics"]["implied"]["sensitivity"] if x["delta"] == 0)
        s["multiple_justified"] = b["archetype_metrics"]["ptbv_justified"]
    assert _run("implicito_mismo_modelo", _fixed(a_nu, two_stage_sens))["state"] == inv.OK

    def bounded(b):
        x = b["score"]["breakdown"]["Crecimiento"]["adjustments"][0]
        x.update(raw=b["growth_basis"]["revenue_cagr"]["bound"]["value"], metric="Crecimiento de ingresos a 5 años")
    assert _run("cota_aplicada", _fixed(a_nu, bounded))["state"] == inv.OK

    def no_dcf_vote(b):
        x = next(x for x in b["score"]["breakdown"]["Valoración"]["adjustments"] if x["metric"].startswith("DCF"))
        x["adjustment"] = 0
    assert _run("voto_estable", _fixed(a_nf, no_dcf_vote))["state"] == inv.NOT_APPLICABLE
    assert _run("inverso_tasa_base", _fixed(
        a_nf, lambda b: b["reverse_dcf"]["main"].update(band="exigente")))["state"] == inv.NOT_APPLICABLE
    assert _run("convergencia_independiente", _fixed(
        a_nu, lambda b: b["confidence"]["dimensions"]["convergence"].update(level="media")))["state"] == inv.NOT_APPLICABLE
    assert _run("calidad_sin_saturar", _fixed(
        a_nf, lambda b: b["score"]["breakdown"]["Calidad de Ganancias"].update(score=17)))["state"] == inv.OK

    def credible(b):
        x = next(x for x in b["score"]["breakdown"]["Valoración"]["adjustments"] if x["metric"] == "Forward P/E")
        x["implied_eps_growth"] = 0.15
    assert _run("forward_creible", _fixed(a_nf, credible))["state"] == inv.OK
    assert _run("beta_contrastada", _fixed(a_nu, lambda b: b["beta"].update(adjusted=1.10)))["state"] == inv.OK

    def neutral(b):
        mc = b["market_context"]
        mc["behavioral"] = []
    assert _run("causalidad_sostenida", _fixed(a_nf, neutral))["state"] == inv.OK
    assert _run("metodo_citado_aplicable", a_nf,
                t_nf.replace("Precio de mercado\nPuntuación de 0 a 100", "Precio de mercado\nPrecio"))["state"] == inv.OK
