"""
Modelo general (rama modelo/general-inventario): las reglas de cordura de lib/model_invariants.py.

Cada regla, con un caso sintético que la viola y otro en el borde que no; los casos de la revisión de NVIDIA (margen neto
por encima de su techo operativo, CAGR del BPA desde un año valle, la empresa que pesa media industria) con sus cifras.
Además: toda regla tiene umbral y peso en config/invariants.toml, y sobre los golden ninguna lanza.

"""
import copy
import glob
import json
import os

import pytest

from settings import cfg

HERE = os.path.dirname(os.path.abspath(__file__))
import model_invariants as inv  # noqa: E402

GOLDEN = sorted(p for env in ("panel", "local") for p in glob.glob(os.path.join(HERE, "golden", env, "*.json")))


def _state(fn, a, **ctx):
    r = fn(a, {"pdf_text": None, "universe": None, "today": None, **ctx})
    return r["state"], r


# ── Catálogo ──

def test_cada_regla_tiene_umbral_y_peso_en_config():
    C = cfg("invariants")
    for name in inv.RULES:
        assert name in C, name
        assert C[name]["weight"] in (1, 2, 3), name
    assert set(k for k in C if hasattr(C[k], "keys")) - {"escaneo"} == set(inv.RULES)


@pytest.mark.parametrize("path", GOLDEN, ids=lambda p: f"{os.path.basename(os.path.dirname(p))}-{os.path.basename(p)[:-5]}")
def test_ninguna_regla_lanza_sobre_los_golden(path):
    with open(path, encoding="utf-8") as fh:
        a = json.load(fh)
    if "display" not in a:
        pytest.skip("sin display (ETF)")
    for name, r in inv.evaluate(a).items():
        assert r["state"] in (inv.OK, inv.VIOLATION, inv.NOT_APPLICABLE, inv.NOT_EVALUABLE), name
        assert not (r["reason"] or "").startswith("la regla falló"), (name, r["reason"])
        assert (r["state"] == inv.VIOLATION) == bool(r["violations"]), name
        for v in r["violations"]:
            assert v["rule"] == name and v["detail"] and v["cause"] and v["severity"] > 0


# ── 1. Margen neto ──

def _nvda_margins(**over):
    """Las cifras de la revisión de NVIDIA (TTM a 2026-06-30)."""
    km = {"revenue": 302.9e9, "operating_margin": 0.652, "net_margin": 0.6366, "net_income_normalized": 186.39e9,
          "net_interest_income": 2.0e9, "cash": 60e9}
    km.update(over)
    return {"classification": {"archetype": "GROWTH_PROFITABLE"}, "key_metrics": km, "tax_rate": {"rate": 0.16},
            "risk_free": {"value": 0.0529}, "earnings_normalization": {"used_in_score": True, "one_off_net": 6.49e9}}


def test_margen_neto_por_encima_del_techo_operativo_nvda():
    st, r = _state(inv.margen_neto_techo, _nvda_margins())
    assert st == inv.VIOLATION
    v = r["violations"][0]
    assert "mostrado" in v["detail"] and v["values"]["excess_income"] > 20e9
    assert "la normalización solo quitó 6.49 B" in v["cause"]


def test_margen_neto_en_el_techo_no_es_violacion():
    a = _nvda_margins()
    rev, om, fin, t = 302.9e9, 0.652, 2.0e9 / 302.9e9, 0.16
    ceiling = (om + fin) * (1 - t) + cfg("invariants.margen_neto_techo.tolerance_pp")
    a["key_metrics"].update(net_margin=ceiling - 1e-6, net_income_normalized=(ceiling - 1e-6) * rev)
    assert _state(inv.margen_neto_techo, a)[0] == inv.OK


def test_margen_neto_sin_resultado_financiero_usa_la_cota_de_la_caja():
    a = _nvda_margins(net_interest_income=None, net_margin=0.55, net_income_normalized=0.55 * 302.9e9)
    # techo con la caja al Rf: (0.652 + 60e9 × 5.29% / 302.9e9) × 0.84 + 2 pp ≈ 57.6 %
    assert _state(inv.margen_neto_techo, a)[0] == inv.OK
    a["key_metrics"]["cash"] = 0
    st, r = _state(inv.margen_neto_techo, a)
    assert st == inv.OK      # 55 % < 0.652 × 0.84 + 2 pp = 56.8 %
    a["key_metrics"].update(net_margin=0.58, net_income_normalized=0.58 * 302.9e9)
    st, r = _state(inv.margen_neto_techo, a)
    assert st == inv.VIOLATION and "cota: caja × Rf" in r["violations"][0]["detail"]


def test_margen_neto_con_las_piezas_de_n1b_minoritarios_y_tipo_normalizado():
    """F10 · N1b (NEE, panel): con el bloque `after_tax` el techo es el de la normalización: (operativo de la suma
    trimestral + financieros netos + participadas) × (1 − t normalizada) + minoritarios. Sin los minoritarios el
    margen de NEE (los que absorben pérdidas suben el beneficio del accionista) saldría por encima."""
    rev = 28.701e9
    at = {"operating_income": 8.135e9, "revenue": rev, "net_interest": -3.512e9, "equity_income": 0.79e9,
          "minority_interests": 1.761e9, "tax_rate": 0.138, "tax_source": "mediana de 3 tipos efectivos",
          "charges_back": 0.0}
    ceiling = ((8.135e9 - 3.512e9 + 0.79e9) * (1 - 0.138) + 1.761e9) / rev
    a = _nvda_margins(revenue=rev, operating_margin=0.28, net_margin=ceiling + 0.015, net_interest_income=-3.512e9,
                      net_income_normalized=(ceiling + 0.015) * rev)
    a["earnings_normalization"]["after_tax"] = at
    assert _state(inv.margen_neto_techo, a)[0] == inv.OK
    a["earnings_normalization"]["after_tax"] = dict(at, minority_interests=0.0)
    st, r = _state(inv.margen_neto_techo, a)
    assert st == inv.VIOLATION and "N1b" in r["violations"][0]["detail"]


def test_margen_neto_normalizado_con_los_cargos_devueltos():
    """APD en el escaneo: un deterioro deja el operativo en −4.7 % y el margen normalizado (sin el cargo) en 13.4 %."""
    rev = 12e9
    a = _nvda_margins(revenue=rev, operating_margin=-0.047, net_margin=-0.05, net_income_normalized=0.134 * rev,
                      net_interest_income=-0.018 * rev)
    a["tax_rate"]["rate"] = 0.21
    a["earnings_normalization"]["items"] = [{"applied": True, "gross": -2.6e9}]
    assert _state(inv.margen_neto_techo, a)[0] == inv.OK
    a["earnings_normalization"]["items"] = []
    st, r = _state(inv.margen_neto_techo, a)
    assert st == inv.VIOLATION and "puntuado" in r["violations"][0]["detail"]


def test_margen_neto_con_las_piezas_de_f10_n1():
    """Tras F10 · N1: NVDA normalizado (172,5 B$) dentro del techo; KO con sus participadas como operación."""
    a = _nvda_margins(net_income_normalized=172.48e9)
    a["earnings_normalization"].update(applied=True, coherence={
        "operating_income": 197.579e9, "net_interest": 1.765e9, "equity_income": 0.0, "revenue": 302.969e9,
        "tax_rate": 0.1605})
    assert _state(inv.margen_neto_techo, a)[0] == inv.OK          # el reportado (63,7 %) va marcado
    ko = _nvda_margins(revenue=50.129e9, operating_margin=0.318, net_margin=0.2856, net_income_normalized=14.316e9,
                       net_interest_income=-0.728e9)
    ko["earnings_normalization"] = {"used_in_score": True, "applied": True, "items": [], "coherence": {
        "operating_income": 15.941e9, "net_interest": -0.728e9, "equity_income": 2.107e9, "revenue": 50.129e9,
        "tax_rate": 0.164}}
    assert _state(inv.margen_neto_techo, ko)[0] == inv.OK


def test_margen_neto_no_aplica_a_un_reit():
    a = _nvda_margins()
    a["display"] = {"na_keys": ["net_margin", "roe"]}
    assert _state(inv.margen_neto_techo, a)[0] == inv.NOT_APPLICABLE


def test_margen_neto_no_aplica_a_una_financiera():
    a = _nvda_margins()
    a["classification"]["archetype"] = "FINANCIAL"
    assert _state(inv.margen_neto_techo, a)[0] == inv.NOT_APPLICABLE


# ── 2. Ke frente a Kd ──

def test_ke_por_debajo_de_kd_mas_un_punto():
    gap = cfg("invariants.ke_sobre_kd.min_gap")
    assert _state(inv.ke_sobre_kd, {"cost_of_equity": {"value": 0.07, "kd": 0.07 - gap}})[0] == inv.OK
    st, r = _state(inv.ke_sobre_kd, {"cost_of_equity": {"value": 0.065, "kd": 0.06}})
    assert st == inv.VIOLATION and "Ke 6.50%" in r["violations"][0]["detail"]
    assert _state(inv.ke_sobre_kd, {"cost_of_equity": {"value": 0.08}})[0] == inv.NOT_APPLICABLE


# ── 3. Beta ──

def _beta(source="propia", raw=1.1, r2=0.3, se=0.15, used=1.07, reason="motivo"):
    return {"beta": {"source": source, "raw": raw, "adjusted": used, "reason": reason,
                     "own": {"raw": raw, "r2": r2, "se": se}}, "wacc": {"beta": used}}


def test_beta_propia_que_no_pasa_los_filtros():
    assert _state(inv.beta_en_rango, _beta())[0] == inv.OK
    st, r = _state(inv.beta_en_rango, _beta(r2=0.1))
    assert st == inv.VIOLATION and "R²" in r["violations"][0]["detail"]


def test_beta_usada_fuera_de_rango_aunque_sea_sustituta():
    lo, hi = cfg("invariants.beta_en_rango.used_range")
    assert _state(inv.beta_en_rango, _beta(source="sector", used=lo))[0] == inv.OK
    st, r = _state(inv.beta_en_rango, _beta(source="sector", used=0.29))     # XOM en el panel
    assert st == inv.VIOLATION and "fuera de" in r["violations"][0]["detail"]
    st, r = _state(inv.beta_en_rango, _beta(source="sector", reason=None))
    assert st == inv.VIOLATION and "sin motivo" in r["violations"][0]["detail"]


# ── 4. g terminal ──

def test_g_terminal_por_encima_de_rf():
    a = {"dcf": {"available": True, "terminal_growth": 0.025}, "wacc": {"rf": 0.025}}
    assert _state(inv.g_terminal_bajo_rf, a)[0] == inv.OK
    a["dcf"]["terminal_growth"] = 0.03
    assert _state(inv.g_terminal_bajo_rf, a)[0] == inv.VIOLATION
    assert _state(inv.g_terminal_bajo_rf, {"dcf": {"available": False}})[0] == inv.NOT_APPLICABLE


# ── 5. Capitalización ──

def test_capitalizacion_frente_a_precio_por_acciones():
    tol = cfg("invariants.capitalizacion.tolerance")
    a = {"price": 100.0, "key_metrics": {"market_cap": 100.0 * 1e9 * (1 + tol * 0.99), "shares_outstanding": 1e9}}
    assert _state(inv.capitalizacion, a)[0] == inv.OK
    a["key_metrics"]["market_cap"] = 100.0 * 1e9 * 5     # un ADR de 5 acciones con las ordinarias
    st, r = _state(inv.capitalizacion, a)
    assert st == inv.VIOLATION and "+400.0%" in r["violations"][0]["detail"]


# ── 6. ROE con patrimonio ≤ 0 ──

def _roe_case(equity, adj, shown="35.0%"):
    return {"key_metrics": {"total_equity": equity},
            "score": {"breakdown": {"Rentabilidad": {"adjustments": [
                {"metric": "ROE", "value": shown, "adjustment": adj}]}}},
            "display": {"sections": {"profitability": {"rows": [{"key": "roe", "state": "con_dato", "value": shown}]}}}}


def test_roe_con_patrimonio_negativo_no_puntua_ni_se_ensena():
    assert _state(inv.roe_patrimonio_negativo, _roe_case(1e9, 4))[0] == inv.NOT_APPLICABLE
    st, r = _state(inv.roe_patrimonio_negativo, _roe_case(-2e9, 4))
    assert st == inv.VIOLATION and len(r["violations"]) == 2
    ok = _roe_case(-2e9, 0, shown="n.s.")
    assert _state(inv.roe_patrimonio_negativo, ok)[0] == inv.OK


# ── 7. PEG con crecimiento ≤ 0 ──

def _peg_case(g, value="0.80", adj=2):
    return {"peg_basis": {"eps_cagr_3y": g},
            "score": {"breakdown": {"Valoración": {"adjustments": [{"metric": "PEG", "value": value, "adjustment": adj}]}}}}


def test_peg_con_crecimiento_del_bpa_negativo():
    assert _state(inv.peg_crecimiento_no_positivo, _peg_case(0.05))[0] == inv.NOT_APPLICABLE
    st, r = _state(inv.peg_crecimiento_no_positivo, _peg_case(-0.071))    # VZ en la auditoría F8
    assert st == inv.VIOLATION and "−7.1%" in r["violations"][0]["detail"]
    assert _state(inv.peg_crecimiento_no_positivo, _peg_case(0.0, value="No significativo", adj=0))[0] == inv.OK
    assert _state(inv.peg_crecimiento_no_positivo, {})[0] == inv.NOT_APPLICABLE


# ── 8. Una sola cifra ──

def test_una_cifra_por_metrica_reutiliza_la_coherencia_de_f9():
    a = {"display": {"cover": {"kpis": [{"key": "pb", "label": "P/B", "value": "5.33x"}]},
                     "sections": {"valuation": {"rows": [{"key": "pb", "label": "P/B", "value": "4.54x"}]}}}}
    st, r = _state(inv.cifra_unica, a)
    assert st == inv.VIOLATION and r["count"] == 1 and "pb (corte)" in r["violations"][0]["detail"]
    a["display"]["cover"]["kpis"][0]["value"] = "4.54x"
    assert _state(inv.cifra_unica, a)[0] == inv.OK


# ── 9. Peso en la referencia de industria ──

def _weight_case(mc):
    a = {"symbol": "NVDA", "key_metrics": {"market_cap": mc},
         "benchmark": {"profile": "sector", "industry": {"basis": "industria", "damodaran": "Semiconductor",
                                                         "region": "us"}}}
    U = {"firm": {"NVDA": ("Semiconductor", "us")}, "caps": {("Semiconductor", "us"): 10e12},
         "counts": {("Semiconductor", "us"): 30}}
    return a, U


def test_la_empresa_que_pesa_media_industria():
    mx = cfg("invariants.peso_en_referencia.max_share")
    a, U = _weight_case(5e12)
    st, r = _state(inv.peso_en_referencia, a, universe=U)
    assert st == inv.VIOLATION and "50%" in r["violations"][0]["detail"] and "cota superior" in r["violations"][0]["detail"]
    a, U = _weight_case(10e12 * mx)
    assert _state(inv.peso_en_referencia, a, universe=U)[0] == inv.OK
    assert _state(inv.peso_en_referencia, a)[0] == inv.NOT_EVALUABLE          # sin el universo
    U["counts"][("Semiconductor", "us")] = cfg("invariants.peso_en_referencia.min_universe_peers") - 1
    assert _state(inv.peso_en_referencia, a, universe=U)[0] == inv.NOT_EVALUABLE          # sola en el universo
    # F10 · N2: con la referencia ya sin la empresa, la regla se cumple aunque pese la mitad; si Damodaran no la cuenta,
    # no aplica
    a["benchmark"]["industry"]["self_exclusion"] = {"method": "sin_empresa", "weight": 0.5}
    assert _state(inv.peso_en_referencia, a, universe=U)[0] == inv.OK
    a["benchmark"]["industry"]["self_exclusion"] = {"method": "no_figura", "weight": None}
    assert _state(inv.peso_en_referencia, a, universe=U)[0] == inv.NOT_APPLICABLE
    a["benchmark"]["industry"].pop("self_exclusion")
    U["firm"]["NVDA"] = ("Computers/Peripherals", "us")
    assert _state(inv.peso_en_referencia, a, universe=U)[0] == inv.NOT_APPLICABLE


# ── 10. Crecimiento robusto ──

def _growth_case(reason="BPA excepcional (198.0%)", ni_base=4.37e9, marked=True):
    return {"growth_basis": {"revenue_window": "FY2023–FY2026",
                             "revenue_cagr": {"anomalous_base": marked, "method": "log_lineal" if marked else "cagr"}},
            "yearly_financials": [{"year": 2023, "net_income": ni_base}, {"year": 2024, "net_income": 29.76e9},
                                  {"year": 2025, "net_income": 72.88e9}, {"year": 2026, "net_income": 99.2e9}],
            "peg_basis": {"eps_cagr_3y": 1.98},
            "score": {"breakdown": {
                "Crecimiento": {"adjustments": [{"metric": "Crecimiento del BPA a 3 años", "value": "198.0%",
                                                 "adjustment": 5, "raw": 1.98, "reason": reason}]},
                "Valoración": {"adjustments": [{"metric": "PEG", "value": "0.14", "adjustment": 4}]}}}}


def test_bpa_con_cagr_desde_un_ano_valle_nvda():
    st, r = _state(inv.crecimiento_robusto, _growth_case())
    assert st == inv.VIOLATION and len(r["violations"]) == 2
    assert "FY2023" in r["violations"][0]["detail"] and "6%" in r["violations"][0]["detail"]


def test_bpa_con_metodo_robusto_o_base_normal_no_es_violacion():
    # el motivo robusto salva al BPA; el PEG, que hereda el CAGR, sigue
    st, r = _state(inv.crecimiento_robusto, _growth_case(reason="BPA (regresión log-lineal: base anómala)"))
    assert [v["detail"].startswith("PEG") for v in r["violations"]] == [True]
    base_normal = _growth_case(ni_base=40e9, marked=False)
    assert _state(inv.crecimiento_robusto, base_normal)[0] == inv.OK
    # la marca en los ingresos sola no hace anómalo al BPA (FITB en el escaneo)
    assert _state(inv.crecimiento_robusto, _growth_case(ni_base=40e9, marked=True))[0] == inv.OK


def test_bpa_con_metodo_robusto_publicado_no_es_violacion():
    """F10: el método del BPA en growth_basis.eps_cagr (serie larga de EDGAR) es robusto."""
    a = _growth_case()
    a["growth_basis"]["eps_cagr"] = {"method": "log_lineal_edgar", "robust": True}
    assert _state(inv.crecimiento_robusto, a)[0] == inv.OK


def test_cagr_con_base_marcada_es_contradiccion_del_motor():
    a = _growth_case(ni_base=40e9)
    a["growth_basis"]["revenue_cagr"]["method"] = "cagr"
    st, r = _state(inv.crecimiento_robusto, a)
    assert st == inv.VIOLATION and "ingresos por CAGR" in r["violations"][0]["detail"]


# ── 11. Alertas frente a cifras ──

def _alert_case(reason, kind="strengths", value="27.98x", tone="pos"):
    return {"alerts": {kind: [{"reason": reason}]},
            "display": {"sections": {"valuation": {"rows": [{"key": "pe", "label": "P/E (TTM)", "state": "con_dato",
                                                             "value": value, "tone": tone, "reading": "x"}]}}}}


def test_alerta_que_cita_otra_cifra_o_contradice_el_tono():
    assert _state(inv.alertas_coherentes, _alert_case("Cotiza con descuento — P/E 28.0x"))[0] == inv.OK
    st, r = _state(inv.alertas_coherentes, _alert_case("Cotiza con descuento — P/E 22.0x"))
    assert st == inv.VIOLATION and "27.98x" in r["violations"][0]["detail"]
    st, r = _state(inv.alertas_coherentes, _alert_case("Cotiza con descuento — P/E 28.0x", tone="neg"))
    assert st == inv.VIOLATION and "tono neg" in r["violations"][0]["detail"]
    # otra base de la cifra (normalizada): no se compara con la reportada
    assert _state(inv.alertas_coherentes, _alert_case("Cotiza con descuento — P/E normalizado 29.0x"))[0] == inv.OK


# ── 12. Una sola beta ──

def test_una_misma_beta_en_todas_las_capas():
    a = {"wacc": {"beta": 1.565}, "key_metrics": {"beta_ke": 1.565}, "beta": {"adjusted": 1.565},
         "alerts": {"warnings": [{"reason": "Volatilidad elevada — Beta 1.57"}]}}
    assert _state(inv.beta_unica, a)[0] == inv.OK
    a["alerts"]["warnings"][0]["reason"] = "Volatilidad elevada — Beta 1.84"      # la bruta
    st, r = _state(inv.beta_unica, a)
    assert st == inv.VIOLATION and "1.84" in r["violations"][0]["detail"]
    a["alerts"]["warnings"] = []
    a["archetype_metrics"] = {"beta_adjusted": 1.30}
    assert _state(inv.beta_unica, a)[0] == inv.VIOLATION


# ── 13. Estados al día ──

def test_estados_antiguos_sin_marca():
    lim = cfg("invariants.estados_al_dia.max_days_ttm")
    a = {"data_provenance": {"staleness": {"status": "al_dia", "days_since_cut": lim, "text": None},
                             "as_of": {"type": "ttm", "date": "2026-03-31"}}, "display": {}}
    assert _state(inv.estados_al_dia, a)[0] == inv.OK
    a["data_provenance"]["staleness"]["days_since_cut"] = 197          # ASML en el panel
    assert _state(inv.estados_al_dia, a)[0] == inv.VIOLATION
    a["data_provenance"]["staleness"].update(status="desfasado", text="Estados desfasados: cifras al 31 de marzo")
    assert _state(inv.estados_al_dia, a)[0] == inv.VIOLATION            # la marca no llega al display
    a["display"] = {"cover": {"note": "Estados desfasados: cifras al 31 de marzo"}}
    assert _state(inv.estados_al_dia, a)[0] == inv.OK


# ── 14. Confianza ≤ cobertura ──

def test_confianza_por_encima_de_su_cobertura():
    a = {"confidence": {"level": "media", "dimensions": {"coverage": {"level": "media", "coverage": 0.8}}}}
    assert _state(inv.confianza_cobertura, a)[0] == inv.OK
    a["confidence"]["level"] = "alta"
    assert _state(inv.confianza_cobertura, a)[0] == inv.VIOLATION


# ── 15. Motivo de cada vacío ──

def test_cada_vacio_con_su_motivo():
    a = {"score_coverage": {"solidez": {"missing": ["Cobertura de intereses"], "missing_reasons": {}}},
         "display": {"summary": {"cards": [{"key": "roe", "state": "no_aplica", "bench": "No aplica a REIT"},
                                           {"key": "pe", "state": "sin_dato", "pill": "Sin dato", "value": "—"}]}}}
    st, r = _state(inv.motivo_de_vacio, a)
    assert st == inv.VIOLATION and r["count"] == 2
    assert {v["values"].get("component") or v["values"].get("path") for v in r["violations"]} == {
        "Cobertura de intereses", "summary.cards[1]"}
    a["score_coverage"]["solidez"]["missing_reasons"] = {"Cobertura de intereses": "sin gasto por intereses en los estados"}
    a["display"]["summary"]["cards"][1]["text"] = "sin BPA estimado de consenso"
    assert _state(inv.motivo_de_vacio, a)[0] == inv.OK


def test_evaluate_aisla_una_regla_que_lanza():
    a = copy.deepcopy(_nvda_margins())
    a["key_metrics"] = ["una forma inesperada"]
    res = inv.evaluate(a, rules=["margen_neto_techo", "ke_sobre_kd"])
    assert set(res) == {"margen_neto_techo", "ke_sobre_kd"}
    assert res["margen_neto_techo"]["state"] == inv.NOT_EVALUABLE
    assert res["margen_neto_techo"]["reason"].startswith("la regla falló: AttributeError")


# ── El escaneo respeta los límites compartidos ──

def test_el_escaneo_limita_edgar_y_finnhub_y_salta_lo_que_no_usa(monkeypatch):
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(HERE), "tools"))
    import finnhub_fallback
    import sec_edgar
    import time
    import universe_scan as us
    calls = []

    class _B:
        q = 0.0

        def add_queue(self, s):
            self.q += s

    monkeypatch.setattr(sec_edgar, "_pace", lambda budget: calls.append("edgar") or 1.0)
    monkeypatch.setattr(finnhub_fallback, "_get", lambda path, params: calls.append(path) or {"ok": 1})
    monkeypatch.setattr(time, "sleep", lambda s: calls.append(("sleep", round(s, 2))))
    us.install_limits()
    E = cfg("invariants.escaneo")
    b = _B()
    sec_edgar._pace(b)
    sec_edgar._pace(b)
    assert calls.count("edgar") == 2
    assert any(isinstance(c, tuple) and 0 < c[1] <= 1 / E["edgar_max_rps"] for c in calls)   # la segunda espera
    for p in E["finnhub_skip_paths"]:
        assert finnhub_fallback._get(p, {}) is None
    assert finnhub_fallback._get("/stock/metric", {"symbol": "X"}) == {"ok": 1}
    assert [c for c in calls if isinstance(c, str) and c.startswith("/")] == ["/stock/metric"]


# ── 1b. Una sola verdad para el margen operativo (PM, 29-oct) ──

def test_margen_operativo_de_yahoo_frente_a_la_suma_trimestral_de_edgar():
    """FIX: 7,9 % enseñado (EDGAR TTM) frente al 16,7 % de las piezas de la normalización (Yahoo, 4 trimestres)."""
    a = {"classification": {"archetype": "MATURE"}, "key_metrics": {"operating_margin": 0.079},
         "earnings_normalization": {"after_tax": {"operating_income": 1.67e9, "revenue": 10e9}},
         "score": {"breakdown": {"Rentabilidad": {"adjustments": [
             {"metric": "Margen operativo", "value": "7.90%", "adjustment": 1}]}}}}
    st, r = _state(inv.margen_operativo_unico, a)
    assert st == inv.VIOLATION and r["violations"][0]["values"]["scores"] is True
    assert "puntúa en Rentabilidad" in r["violations"][0]["detail"]
    a["key_metrics"]["operating_margin"] = 0.16
    assert _state(inv.margen_operativo_unico, a)[0] == inv.OK
    a["earnings_normalization"] = {}
    assert _state(inv.margen_operativo_unico, a)[0] == inv.NOT_EVALUABLE


def test_margen_neto_cortado_justo_en_el_techo_de_n1b_no_es_violacion():
    """ARM, MKC, RDDT, SKYD (escaneo de la puerta): N1b corta el normalizado justo en su techo sobre los ingresos de la
    suma trimestral; medido sobre los de Yahoo (algo menores) quedaba una décima por encima."""
    arev = 10.0e9
    at = {"operating_income": 2.0e9, "revenue": arev, "net_interest": 0.0, "equity_income": 0.0,
          "minority_interests": 0.0, "tax_rate": 0.2, "charges_back": 0.0, "tax_source": "legal"}
    ni = (2.0e9 * 0.8) + cfg("invariants.margen_neto_techo.tolerance_pp") * arev
    ni = ni * (1 + 1e-16) + 1e-7                      # el redondeo con que llega el corte de N1b
    a = _nvda_margins(revenue=9.9e9, operating_margin=0.2, net_margin=0.30, net_income_normalized=ni)
    a["earnings_normalization"].update(after_tax=at, applied=True)
    assert _state(inv.margen_neto_techo, a)[0] == inv.OK


def test_margen_neto_con_el_techo_final_de_n1b_marca_solo_lo_no_declarado():
    """F10 · N1b final (solo se recorta lo nombrable; el resto se declara en `unexplained`): la regla lee el techo de
    la normalización (`after_tax.explained` + `tolerance`) y lo declarado; solo lo que pasa de ahí es violación."""
    rev = 10.0e9
    at = {"operating_income": 2.0e9, "revenue": rev, "net_interest": 0.0, "equity_income": 0.0,
          "minority_interests": 0.0, "tax_rate": 0.2, "charges_back": 0.0, "tax_source": "legal",
          "explained": 1.6e9, "tolerance": 0.2e9, "out": 0.1e9, "unexplained": 0.3e9}
    a = _nvda_margins(revenue=rev, operating_margin=0.2, net_margin=0.22, net_income_normalized=2.1e9)
    a["earnings_normalization"].update(after_tax=at, applied=True, unexplained={"after_tax": 0.3e9})
    st, r = _state(inv.margen_neto_techo, a)
    assert st == inv.OK                                              # 2,1 = 1,6 + 0,2 + 0,3 declarados
    a["key_metrics"]["net_income_normalized"] = 2.4e9                # 0,3 más, sin declarar
    st, r = _state(inv.margen_neto_techo, a)
    v = r["violations"][0]
    assert st == inv.VIOLATION and abs(v["values"]["excess_income"] - 0.3e9) < 1e6
    assert "declarado" in v["detail"] or "sin declarar" in v["cause"]
