"""
F8: conjunto de referencia de la auditoría externa del 26-oct-2026 (§6). Los 26 tickers del informe, desde el replay:
los 12 del panel (tests/fixtures/panel) y 13 grabados para F8 (tests/fixtures/f8, comprimidos, capturados el 27-oct
con Render simulado). LIN queda fuera: el capturador no reproduce la historia de EDGAR de su predecesora (Praxair).

Cada corrección de la Fase A añade aquí sus afirmaciones; los controles de pipeline valen para todos.
"""
import os

import pytest

import fixture_backend as fb
from settings import cfg

PANEL = fb.fixtures_dir("panel")
F8 = os.path.join(os.path.dirname(PANEL), "f8")
AUDIT = ["MSFT", "NVDA", "LLY", "UNH", "JPM", "CB", "AMZN", "MCD", "GOOGL", "VZ", "CAT", "UNP", "KO", "WMT", "XOM",
         "KMI", "NEE", "AWK", "PLD", "O", "FCX", "ASML", "SAP", "MRNA", "BA"]

pytestmark = pytest.mark.skipif(not (fb.panel_available() and os.path.isdir(F8)), reason="sin panel o sin fixtures F8")


@pytest.fixture(scope="module")
def ref():
    out = {}
    for s in AUDIT:
        base = PANEL if os.path.isdir(os.path.join(PANEL, s)) else F8
        with fb.replay(base, extra_dirs=(F8,)) as store:
            out[s] = fb.run_analysis(s, store)
    return out


# ── controles de pipeline (§6) ──

def test_ke_above_kd_plus_spread(ref):
    for s, a in ref.items():
        w = a.get("wacc") or {}
        if w.get("kd") is not None:
            assert w["ke"] >= w["kd"] + cfg("valuation.capm.ke_floor_over_kd") - 1e-12, s


def test_ke_above_half_market(ref):
    for s, a in ref.items():
        ce = a["cost_of_equity"]
        assert ce["value"] >= ce["rf"] + cfg("valuation.capm.ke_floor_erp_multiple") * ce["erp"] - 1e-12, s


def test_beta_in_range_or_industry(ref):
    lo, hi = cfg("market.beta_choice.own_range")
    for s, a in ref.items():
        b = a["beta"]
        assert b["source"] == "sector" or lo <= b["raw"] <= hi, s


def test_terminal_growth_not_above_rf(ref):
    for s, a in ref.items():
        assert cfg("valuation.dcf.terminal_growth") <= a["risk_free"]["value"], s


def test_single_ke_and_dated_pair(ref):
    C = cfg("valuation.capm")
    for s, a in ref.items():
        ce, w, xm = a["cost_of_equity"], a.get("wacc") or {}, a.get("archetype_metrics") or {}
        assert (a["risk_free"]["value"], a["risk_free"]["erp"], a["risk_free"]["as_of"]) == \
            (C["risk_free_rate"], C["market_risk_premium"], C["pair_as_of"]), s
        if w.get("ke") is not None:
            assert w["ke"] == ce["value"], s
        if xm.get("cost_of_equity") is not None:
            assert xm["cost_of_equity"] == pytest.approx(ce["value"]), s


# ── E1 (§3 E1 y §6) ──

def test_awk_ke_not_below_kd(ref):
    """§6: AWK, Ke ≥ Kd. La auditoría: Ke 5,14 % con la beta propia −0,44 (R² 0,11) frente a Kd 5,88 %."""
    a = ref["AWK"]
    assert a["beta"]["source"] == "sector" and "descartada" in a["beta"]["reason"]
    assert a["wacc"]["ke"] >= a["wacc"]["kd"] + 0.01


def test_e1_audit_cases(ref):
    """§3 E1: XOM (Ke 6,25 %, Rf + 1,3 pp) y CB (Ke 7,0 %) ya no quedan por debajo del piso de medio mercado. XOM, con
    el piso. F9 · R2b: CB (sede operativa en Zúrich) toma la beta de aseguradoras de Europa (0,56
    frente a 0,48 de EE. UU.) y su CAPM ya supera el piso.
    F14 · paso 1: con el Rf de 4,94 %, XOM deja de ser dependiente de Ke."""
    for s in ("XOM", "CB"):
        ce = ref[s]["cost_of_equity"]
        assert ce["value"] >= max(ce["floors"].values()) - 1e-12, s
    # F14 · paso 1 (Rf 5,29 % → 4,94 %): XOM sigue con el piso, pero su nivel de precio ya no cambia con ±1 pp de Ke
    assert ref["XOM"]["cost_of_equity"]["floor"]["rule"].startswith("Rf")
    assert ref["CB"]["beta"]["region"]["region"] == "europe"


def test_beta_rule_is_visible(ref):
    for s, a in ref.items():
        assert a["beta"]["rule"] and a["beta"]["reason"], s


# ── E4 y E5 (§3 E4 y E5, y §6) ──

def _growth_adjs(a):
    return {x["metric"]: x for x in (((a.get("score") or {}).get("breakdown") or {}).get("Crecimiento") or {})
            .get("adjustments") or []}


def test_vz_headline_cites_revenue_growth_not_total_return(ref):
    """§6: el titular de VZ cita el crecimiento de los ingresos del DCF (0,33 %), no el retorno total (6,8 %)."""
    a = ref["VZ"]
    tr = _growth_adjs(a)["Retorno total (dividendo + ingresos por acción)"]
    assert tr["revenue_growth"] == pytest.approx(0.0033, abs=5e-4) and tr["raw"] > 0.06
    txt = a["display"]["readings"]["revenue_growth"]["text"]
    assert "0.3%" in txt and "6.8" not in txt
    rows = {r["key"]: r for r in a["display"]["sections"]["growth"]["rows"]}
    assert rows["revenue_growth"]["value"] == "0.33%" and rows["total_return"]["value"] == "6.76%"


def test_growth_readings_never_present_total_return_as_revenue(ref):
    """Control de pipeline: con un ajuste de retorno total, la lectura de los ingresos cita el crecimiento de los
    ingresos que el ajuste guarda; el retorno total va rotulado en su fila."""
    for s, a in ref.items():
        adj = _growth_adjs(a).get("Retorno total (dividendo + ingresos por acción)") or \
            _growth_adjs(a).get("Retorno total (dividendo + ingresos)")
        if not adj or adj.get("revenue_growth") is None:
            continue
        rows = {r["key"]: r for r in a["display"]["sections"]["growth"]["rows"]}
        assert rows["revenue_growth"]["value"] == f"{adj['revenue_growth']:.2%}", s
        assert "total_return" in rows, s


def test_peg_not_significant_when_eps_does_not_grow(ref):
    """§6: VZ, PEG n.s. con el BPA en −7,1 % (la auditoría: PEG 0,80 «muy atractivo»). Control de pipeline: ningún PEG
    puntúa ni se muestra con el crecimiento del BPA del informe ≤ 0."""
    a = ref["VZ"]
    assert a["key_metrics"]["peg"] is None
    assert "PEG" in a["score_coverage"]["valoracion"]["not_significant"]
    for s, a in ref.items():
        e3 = next((x.get("raw") for k, x in _growth_adjs(a).items() if k.startswith("Crecimiento del BPA")), None)
        if a["key_metrics"].get("peg") is not None and e3 is not None:
            assert e3 > 0, (s, e3)


def test_convergence_alta_has_no_contrary_extreme_multiple(ref):
    """§6: «alta» exige que ningún múltiplo individual contradiga la dirección común con lectura extrema (±1)."""
    ext = cfg("thresholds.confidence.convergence_extreme_reading")
    for s, a in ref.items():
        c = ((a.get("confidence") or {}).get("dimensions") or {}).get("convergence") or {}
        if c.get("level") != "alta":
            continue
        d = next(m["direction"] for m in c["methods"] if m.get("evaluable"))
        for m in c["methods"]:
            for k, v in (m.get("readings") or {}).items():
                assert not ((d == "barata" and v <= -ext) or (d == "cara" and v >= ext)), (s, k, v)


def test_vz_fcf_subtracts_ten_year_spectrum(ref):
    """§3 E4 con la ventana del PM (27-oct): FCF de telecom − media de 10 años de las compras de espectro (EDGAR:
    PaymentsToAcquireIntangibleAssets; VZ FY2016–FY2025, 65,7 mil millones con la banda C de 2021)."""
    a = ref["VZ"]
    sp = a["spectrum_adjustment"]
    assert sp["status"] == "ok" and sp["years"] == [str(y) for y in range(2025, 2015, -1)]
    assert sp["average"] == pytest.approx(6.574e9, rel=1e-3)
    assert "media de 10 años" in a["dcf"]["fcf_basis"]
    assert a["key_metrics"]["pfcf"] == pytest.approx(a["profile"]["market_cap"] / sp["fcf_adjusted"], rel=1e-6)
    assert "espectro" in a["dcf"]["fcf_basis"]
    for s, b in ref.items():
        if s != "VZ":
            assert b.get("spectrum_adjustment") is None, s


def test_front_page_uses_normalized_pe_when_reported_is_unreliable(ref):
    """§6 (E5): GOOGL y AMZN; y como control, toda empresa con el P/E reportado marcado como no fiable."""
    for s in ("GOOGL", "AMZN"):
        assert ref[s]["earnings_normalization"]["pe_unreliable"], s
    for s, a in ref.items():
        n = a.get("earnings_normalization") or {}
        if not (n.get("pe_unreliable") and n.get("pe_normalized")) or not a["display"]["readings"].get("pe"):
            continue      # el arquetipo no lee el P/E (REIT, CYCLICAL: lo dicen su rama y el ciclo medio)
        txt = a["display"]["readings"]["pe"]["text"]
        assert f"{n['pe_normalized']:.1f}x el beneficio normalizado" in txt and "no es fiable" in txt, s
        val = next(i["text"] for i in a["display"]["summary"]["exec_items"] if i["label"] == "ATRACTIVO DEL PRECIO")
        assert f"{n['pe_normalized']:.1f}x" in val, s


# ── E2 (§3 E2) ──

def test_peak_flag_rules_hold_on_every_company(ref):
    """Controles de pipeline: con la bandera de pico, el P/E que puntúa es el de la bandera y la lectura lo declara;
    sin la segunda condición con un forward fiable, nunca hay bandera (el mercado cree en el nivel: NVDA, LLY). NEE se
    comprueba con datos reales (tests/test_f8_e2.py y la corrida «e2»): en el replay, grabado a mediados de octubre, su
    TTM queda un 31 % sobre la mediana, por debajo del umbral."""
    for s, a in ref.items():
        p = a.get("earnings_peak")
        if not p:
            continue
        if p["forward"]["coherent"] and p["conditions"]["b"] is False:
            assert not p["flag"], s
        if p["flag"]:
            pe = next(x for x in a["score"]["breakdown"]["Valoración"]["adjustments"]
                      if x["metric"] == "P/E frente al sector")
            assert pe["value"] == f"{p['pe_score']:.1f}x" and f"{p['period']} atípico" in pe["reason"], s
            txt = a["display"]["readings"]["pe"]["text"]
            assert txt.startswith(f"el mercado paga {p['pe_score']:.1f}x") and "beneficio atípico" in txt, s
    for s in ("NVDA", "LLY"):
        assert ref[s]["earnings_peak"]["conditions"]["a"] and not ref[s]["earnings_peak"]["flag"], s


# ── E8 (§3 E8) ──

def test_dcf_reliability_never_cites_the_price(ref):
    """Control de pipeline: ningún motivo de la fiabilidad del DCF habla del precio (eso es la convergencia); la tabla
    que no contiene el precio solo informa. La auditoría: MSFT, GOOGL, LIN, WMT, CAT, FCX y ASML se descartaban así."""
    for s, a in ref.items():
        rel = (a.get("dcf") or {}).get("reliability") or {}
        assert not any("precio" in r for r in rel.get("reasons") or []), (s, rel.get("reasons"))
    for s in ("MSFT", "GOOGL", "WMT"):          # LIN no está en el replay
        rel = ref[s]["dcf"]["reliability"]
        assert rel["level"] != "baja", (s, rel)


# ── E9 (§3 E9 y §6) ──

def test_profitability_never_excellent_while_destroying_value(ref):
    """Control de pipeline: con ROIC − WACC < 0, Rentabilidad ≤ 10/20; < −3 pp, ≤ 6/20 (la auditoría: NEE 20/20,
    AWK 19/20 y KMI 16/20 con diferencial negativo)."""
    for s, a in ref.items():
        sp = (a.get("key_metrics") or {}).get("roic_wacc_spread")
        r = ((a.get("score") or {}).get("breakdown") or {}).get("Rentabilidad") or {}
        if sp is None or r.get("score") is None or (a.get("classification") or {}).get("archetype") == "FINANCIAL":
            continue
        if sp < -0.03:
            assert r["score"] <= 6, (s, sp, r["score"])
        elif sp < 0:
            assert r["score"] <= 10, (s, sp, r["score"])


def test_unh_dcf_is_not_reliable_with_its_margin_collapsing(ref):
    """§3 E7/E8 (PM, 27-oct): UNH crece en el DCF mientras el margen cae; su DCF no puede puntuar con fiabilidad alta."""
    rel = ref["UNH"]["dcf"]["reliability"]
    assert rel["level"] == "baja" and rel["criteria"]["margin_trend"]["drop"] >= 0.40
    assert ref["UNH"]["verdict"]["price_level"] != "atractivo"


# ── E11 (§3 E11) ──

def test_confidence_never_above_any_rated_dimension(ref):
    """Control de pipeline: la más baja manda (la cobertura incluida); y con confianza baja la calidad está contraída."""
    order = ("alta", "media", "baja")
    for s, a in ref.items():
        c = a.get("confidence") or {}
        if c.get("level") not in order:
            continue
        for k, d in (c.get("dimensions") or {}).items():
            if k in ("convergence", "coverage", "source", "stability") and d.get("level") in order:
                assert order.index(c["level"]) >= order.index(d["level"]), (s, k, d["level"], c["level"])
        q = a.get("quality") or {}
        # F10 · N4: contrae la base de contracción (sin el escalón de las tasas base, que no contrae)
        if (c.get("contraction_basis") or c["level"]) == "baja" and q.get("score_raw") is not None \
                and q["score_raw"] != 50:
            assert q["contracted"] and abs(q["score"] - 50) < abs(q["score_raw"] - 50), s
