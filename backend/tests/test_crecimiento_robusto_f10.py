"""
F10 · crecimiento desde una base anómala (escaneo de control del 29-oct: 46 empresas puntúan el «Crecimiento del BPA a
3 años» desde un año valle; NVDA +198 %, VRT +282 %, PODD +245 %). Regla general para todo crecimiento a 3 años
(historical_metrics.robust_growth):

- sin base anómala, el CAGR de siempre (robusto);
- con base anómala, la regresión log-lineal; es robusta si tiene ejercicios fuera de la ventana;
- si no lo es, la serie larga de EDGAR (≥ thresholds.growth.long_years ejercicios contiguos que lleguen al último);
- y si tampoco, no significativo con su motivo (nunca una cifra que dependa del año anómalo).
"""
import pytest

import historical_metrics as hm
from settings import cfg

N = cfg("thresholds.growth.long_years")


def _edgar(values_oldest_first, last_year=2026, month_day="01-25"):
    """history_fy de EDGAR para un campo: un ejercicio por año, el último en `last_year`."""
    n = len(values_oldest_first)
    return {"values": [{"fy_end": f"{last_year - n + 1 + i}-{month_day}", "value": v}
                       for i, v in enumerate(values_oldest_first)]}


# NVDA, BPA de FY2023 a FY2026 (de la más reciente a la más antigua): FY2023 es el 6 % de la mediana del resto.
NVDA_EPS = [4.53, 2.94, 1.19, 0.17]


def test_sin_base_anomala_el_cagr_de_siempre_y_robusto():
    r = hm.robust_growth([133.0, 121.0, 110.0, 100.0], what="ingresos")
    assert r["method"] == "cagr" and r["robust"] is True and r["value"] == pytest.approx(0.1, abs=1e-3)
    assert not r.get("not_significant")


def test_base_anomala_con_ejercicios_fuera_de_la_ventana_es_robusta():
    r = hm.robust_growth([4.5, 2.9, 1.2, 0.17, 0.7, 0.6], what="BPA")
    assert r["anomalous_base"] and r["method"] == "log_lineal" and r["robust"] is True and r["value"] is not None


def test_base_anomala_sin_serie_larga_no_es_significativo():
    r = hm.robust_growth(NVDA_EPS, what="BPA")
    assert r["value"] is None and r["not_significant"] is True and r["robust"] is False
    assert r["reason"].startswith(hm.ANOMALOUS_NOT_SIGNIFICANT)
    assert "6%" in r["reason"] and "sin serie larga" in r["reason"]
    assert hm.is_anomalous_not_significant(r["reason"])


def test_base_anomala_con_serie_larga_de_edgar_usa_la_regresion_larga():
    long = _edgar([1.0, 1.2, 1.1, 4.4, 29.8, 72.9][:N - 4] + [4.4, 29.8, 72.9, 99.2])   # termina en FY2026
    r = hm.robust_growth([99.2, 72.9, 29.8, 4.4], what="beneficio", long=long, end="2026-01-25")
    assert r["robust"] is True and r["method"] == "log_lineal_edgar" and r["value"] is not None
    assert r["years_used"] == N and "EDGAR" in r["note"]


def test_serie_larga_que_no_llega_al_ultimo_ejercicio_no_sirve():
    long = _edgar([1.0, 1.2, 1.1, 4.4, 29.8, 72.9, 99.2][:N], last_year=2024)
    r = hm.robust_growth([99.2, 72.9, 29.8, 4.4], what="beneficio", long=long, end="2026-01-25")
    assert r["value"] is None and r["not_significant"] and "no llega al último ejercicio" in r["reason"]


def test_serie_larga_corta_o_con_valores_no_positivos_no_sirve():
    short = _edgar([4.4, 29.8, 72.9, 99.2])
    r = hm.robust_growth([99.2, 72.9, 29.8, 4.4], what="beneficio", long=short, end="2026-01-25")
    assert r["not_significant"] and f"hacen falta {N}" in r["reason"]
    neg = _edgar([-1.0] + [1.0] * (N - 5) + [4.4, 29.8, 72.9, 99.2])
    r = hm.robust_growth([99.2, 72.9, 29.8, 4.4], what="beneficio", long=neg, end="2026-01-25")
    assert r["not_significant"]


def test_serie_larga_con_un_hueco_solo_cuenta_lo_contiguo():
    vals = [{"fy_end": f"{y}-01-25", "value": v} for y, v in
            ((2017, 1.0), (2018, 1.1), (2020, 1.2), (2021, 1.3), (2022, 1.4), (2023, 4.4), (2024, 29.8),
             (2025, 72.9), (2026, 99.2))]
    r = hm.robust_growth([99.2, 72.9, 29.8, 4.4], what="beneficio", long={"values": vals}, end="2026-01-25")
    assert r["robust"] is (2026 - 2020 + 1 >= N)


def test_strict_cagr_y_fcf_cagr_dicen_no_significativo_con_base_anomala():
    v, why = hm.strict_cagr(NVDA_EPS)
    assert v is None and hm.is_anomalous_not_significant(why)
    v, why = hm.fcf_cagr(NVDA_EPS)
    assert v is None and hm.is_anomalous_not_significant(why)


def test_los_motivos_de_siempre_no_cambian():
    assert hm.robust_growth([1.0, 2.0], what="BPA")["reason"].startswith("menos de 4 ejercicios")
    assert "inicial <= 0" in hm.robust_growth([1.0, 2.0, 3.0, -1.0], what="BPA")["reason"]


# ── La puntuación: no significativo, sin restar cobertura y con su línea ──

def test_crecimiento_no_significativo_no_puntua_ni_resta_cobertura():
    import financial_ratios as fr
    ns = hm.robust_growth(NVDA_EPS, what="BPA")["reason"]
    c = fr.score_crecimiento(revenue_growth_3y=0.12, eps_growth_3y=None, fcf_growth_3y=0.08, eps_reason=ns,
                             archetype="MATURE")
    assert "Crecimiento del BPA" in c["coverage"]["not_significant"]
    assert "Crecimiento del BPA" not in c["coverage"]["missing"]
    line = next(x for x in c["adjustments"] if x["metric"].startswith("Crecimiento del BPA"))
    assert line["value"] == "No significativo" and line["adjustment"] == 0 and "año base anómalo" in line["reason"]


def test_ingresos_no_significativos():
    import financial_ratios as fr
    ns = hm.robust_growth([133.0, 121.0, 110.0, 20.0], what="ingresos", strict_ends_only=True)["reason"]
    c = fr.score_crecimiento(revenue_growth_3y=None, eps_growth_3y=0.1, fcf_growth_3y=0.1, revenue_reason=ns,
                             archetype="MATURE")
    assert "Crecimiento de ingresos" in c["coverage"]["not_significant"]


def test_valor_en_libros_no_significativo_en_calidad():
    import financial_ratios as fr
    ns = hm.robust_growth([30.0, 28.0, 26.0, 5.0], what="valor en libros", strict_ends_only=True)["reason"]
    c = fr.score_calidad_ganancias(None, None, None, None, None, archetype="FINANCIAL",
                                   xv={"book_value_cagr_3y": None, "book_value_cagr_3y_reason": ns})
    assert "Crecimiento del valor en libros" in c["coverage"]["not_significant"]


# ── El periodo que se lee: la cifra de la serie larga no dice «en 3 años» ──

def test_el_periodo_de_la_serie_larga_dice_sus_ejercicios():
    import classify
    assert classify.growth_span({"window_3y": "FY2023–FY2026"}, 3) == "en 3 años (FY2023–FY2026)"
    t = classify.growth_span({"window_3y": "FY2021–FY2026", "years_3y": 6}, 3)
    assert t.startswith("en 6 ejercicios (FY2021–FY2026") and "ventana de 3 años es anómalo" in t


def test_crecimiento_rentable_con_base_anomala_usa_la_regresion_larga():
    import cyclicality as cy
    vals = [1.0, 1.3, 1.6, 1.7, 4.4, 29.8, 72.9]          # FY2020…FY2026: el FY2023 (1.7) es el 6 % de la mediana
    hist = {"revenue": {"values": [{"fy_end": f"{2020 + i}-01-25", "value": v} for i, v in enumerate(vals)]}}
    m = cy.growth_profitable_measures(hist)
    assert m["method_3y"]["method"] == "log_lineal_edgar" and m["years_3y"] == N
    assert m["window_3y"] == f"FY{2027 - N}–FY2026"


def test_el_peg_propio_de_la_serie_larga_dice_sus_ejercicios(outputs_by_env):
    """NVDA (panel): el BPA de FY2023 es anómalo; con la serie larga de EDGAR el PEG es propio y su rótulo lo dice, y
    el tipo dice los ejercicios de su regresión, no «en 3 años»."""
    a = outputs_by_env("panel")["NVDA"][0]
    assert a["peg_basis"]["own"] and a["peg_basis"]["years"] == N
    row = next(r for r in a["display"]["sections"]["valuation"]["rows"] if r["label"].startswith("PEG"))
    assert row["label"] == f"PEG (BPA, {N} ejercicios)"
    plain = a["classification"]["reason_plain"]
    assert f"en {N} ejercicios" in plain and "en 3 años" not in plain


def test_pb_justificado_sin_crecimiento_del_valor_en_libros_significativo_es_de_una_etapa_declarada():
    import archetype_metrics as am
    ns = hm.robust_growth([30.0, 28.0, 26.0, 5.0], what="valor en libros", strict_ends_only=True)["reason"]
    xm = {"book_value_cagr_3y": None, "book_value_cagr_3y_reason": ns, "roe_reference": 0.2, "cost_of_equity": 0.1,
          "terminal_growth": 0.03}
    ts = am.apply_two_stage(xm, 0.12, 0.3, 0.02)["two_stage"]
    assert ts["applied"] is False and "una sola etapa" in ts["reason"] and "año base anómalo" in ts["reason"]


# ── La clasificación: un criterio no significativo no cuenta ni a favor ni en contra (PM, 29-oct) ──

def _rivn_like():
    """Ingresos de RIVN de FY2022 a FY2025 (de la más reciente a la más antigua): el FY2022 es el 33 % de la mediana."""
    return {"revenue": [5.3e9, 4.97e9, 4.43e9, 1.66e9], "inc_ends": ["2025-12-31", "2024-12-31", "2023-12-31",
                                                                    "2022-12-31"]}


def test_pre_beneficio_con_crecimiento_no_significativo_sigue_siendo_pre_beneficio():
    import classify
    c = classify.classify(sector="Consumer Cyclical", industry="Auto Manufacturers", eps_ttm=-2.58,
                          net_margin_ttm=-0.55, statements_fy=_rivn_like(), history=None)
    assert c["inputs"]["revenue_cagr_3y"] is None and hm.is_anomalous_not_significant(c["inputs"]["revenue_cagr_3y_reason"])
    assert c["archetype"] == classify.GROWTH_PRE_PROFIT and c["rule"] == "pre_beneficio_con_crecimiento"
    assert "ni a favor ni en contra" in c["reason_plain"]


def test_con_beneficio_el_crecimiento_no_significativo_no_lo_hace_pre_beneficio():
    import classify
    c = classify.classify(sector="Consumer Cyclical", industry="Auto Manufacturers", eps_ttm=1.2,
                          net_margin_ttm=0.05, statements_fy=_rivn_like(), history=None)
    assert c["archetype"] != classify.GROWTH_PRE_PROFIT


def test_crecimiento_rentable_con_la_tasa_a_3_anos_no_significativa_decide_el_resto():
    import classify
    gp = classify._growth_profitable(2.0, 0.30, None, None,
                                     {"revenue": [133.0, 121.0, 110.0, 20.0], "ordinary_shares": [1.0] * 4})
    assert gp["revenue_ps_cagr_3y"] is None and 3 in gp["not_significant"] and gp["meets"] is True
    gp = classify._growth_profitable(2.0, 0.02, None, None,
                                     {"revenue": [133.0, 121.0, 110.0, 20.0], "ordinary_shares": [1.0] * 4})
    assert gp["meets"] is False                        # sin margen no es crecimiento rentable, crezca o no


def test_rivn_del_panel_sigue_siendo_pre_beneficio_con_veredicto_de_precio(outputs_by_env):
    a = outputs_by_env("panel")["RIVN"][0]
    assert a["classification"]["archetype"] == "GROWTH_PRE_PROFIT"
    assert a["display"]["cover"]["price"]["score"] is not None


def test_regla_de_40_con_crecimiento_no_significativo_y_cota_que_no_decide_no_puntua():
    import archetype_metrics as am
    ns = hm.robust_growth([133.0, 121.0, 110.0, 20.0], what="ingresos", strict_ends_only=True)
    x = am._growth_pre_profit({"revenue": 100.0}, None, {}, {"fcf_margin_adjusted": 0.05}, ns["reason"], ns["bound"])
    assert x["rule_of_40"] is None and x["rule_of_40_bound"] is None and x["rule_of_40_reason"] == ns["reason"]


# ── La cota (PM, 29-oct): desde una base anómala baja, la tasa de punta a punta es una cota superior ──

def test_growth_rate_expone_la_cota_de_una_base_anomala_baja():
    r = hm.robust_growth(NVDA_EPS, what="BPA")
    assert r["bound"]["direction"] == "superior"
    assert r["bound"]["value"] == pytest.approx((4.53 / 0.17) ** (1 / 3) - 1)
    assert "bound" not in hm.robust_growth([133.0, 121.0, 110.0, 100.0])


def test_la_cota_solo_decide_el_tramo_que_no_depende_de_lo_desconocido():
    up = {"value": -0.10, "direction": "superior"}
    assert hm.bound_decides(up, [0.25, 0.12, 0.05, 0.0]) == -0.10            # aun en la cota, el peor tramo
    assert hm.bound_decides({"value": 0.30, "direction": "superior"}, [0.25, 0.12, 0.05, 0.0]) is None
    assert hm.bound_decides({"value": 3.0, "direction": "inferior"}, [0.8, 1.2, 1.8, 2.5],
                            higher_is_better=False) == 3.0                    # PEG: aun en la cota, el peor
    assert hm.bound_decides({"value": 1.0, "direction": "inferior"}, [0.8, 1.2, 1.8, 2.5],
                            higher_is_better=False) is None


def test_crecimiento_puntua_con_la_cota_solo_si_decide():
    import financial_ratios as fr
    ns = hm.robust_growth(NVDA_EPS, what="BPA")["reason"]
    c = fr.score_crecimiento(revenue_growth_3y=0.12, eps_growth_3y=None, fcf_growth_3y=0.08, eps_reason=ns,
                             archetype="MATURE", bounds={"eps": {"value": -0.08, "direction": "superior"}})
    row = next(x for x in c["adjustments"] if x["metric"].startswith("Crecimiento del BPA"))
    assert row["value"].startswith("≤ ") and row["adjustment"] == cfg("thresholds.score.crecimiento.eps_points")[-1]
    assert "techo" in row["reason"] and "Crecimiento del BPA" not in c["coverage"]["not_significant"]
    c = fr.score_crecimiento(revenue_growth_3y=0.12, eps_growth_3y=None, fcf_growth_3y=0.08, eps_reason=ns,
                             archetype="MATURE", bounds={"eps": {"value": 0.5, "direction": "superior"}})
    assert "Crecimiento del BPA" in c["coverage"]["not_significant"]


def test_regla_de_40_con_la_cota_en_el_peor_tramo_puntua_y_lo_declara(outputs_by_env):
    """RIVN (panel): el crecimiento de los ingresos no es significativo (FY2022 al 33 % de la mediana), pero con su
    cota superior más el margen FCF − SBC (−73 %) la regla de 40 ya está en su peor tramo: puntúa y lo dice."""
    a = outputs_by_env("panel")["RIVN"][0]
    row = next(x for x in a["score"]["breakdown"]["Valoración"]["adjustments"] if x["metric"] == "Regla de 40")
    assert row["value"].startswith("≤ ") and row["adjustment"] == cfg("thresholds.score.valoracion.rule_of_40_points")[-1]
    assert "techo" in row["reason"] and row["bound"]["direction"] == "superior"
    assert a["display"]["cover"]["price"]["score"] is not None


# ── ENB (PM, 29-oct): un tiempo agotado de EDGAR no cambia la referencia de la industria en silencio ──

def _ed_timeout(retried=True):
    return {"status": "ok", "cik": 895728, "facts": None, "facts_status": "no_disponible",
            "facts_reason": "EDGAR no respondió a tiempo", "retried": retried}


def test_tiempo_agotado_de_edgar_se_reintenta_con_su_presupuesto():
    import sec_edgar
    calls = []

    def again(ticker, stage1, budget):
        calls.append((ticker, budget.total))
        return {"status": "ok", "cik": 895728, "facts": {"x": 1}, "facts_status": "ok"}
    r = sec_edgar.retry_if_transient(_ed_timeout(False), "ENB", fetcher=again)
    assert calls == [("ENB", cfg("data.edgar.retry_s"))] and r["facts_status"] == "ok" and r["retried"]
    ok = {"status": "ok", "facts_status": "ok", "facts": {}}
    assert sec_edgar.retry_if_transient(ok, "ENB", fetcher=lambda *a: 1 / 0) is ok          # sin fallo, sin reintento
    nf = {"status": "ok", "facts_status": "sin_estados"}
    assert sec_edgar.retry_if_transient(nf, "X", fetcher=lambda *a: 1 / 0) is nf           # «no existe» no se reintenta
    r = sec_edgar.retry_if_transient(_ed_timeout(False), "ENB", fetcher=lambda *a: _ed_timeout(False))
    assert r["facts_status"] == "no_disponible" and r["retried"]


def test_tiempo_agotado_tras_el_reintento_usa_la_cache_y_si_no_degrada():
    import self_exclusion as se
    se._LAST_OK.clear()
    r = se.figures_resilient("ENB", {"currency": "USD"}, _ed_timeout(), None)
    assert r["status"] == "sin_dato" and r["degraded"] and "reintentado" in r["reason"]
    se._LAST_OK[("ENB", cfg("industries.dollar_as_of"))] = {"status": "ok", "values": {"mcap": 1.0}}
    r = se.figures_resilient("ENB", {"currency": "USD"}, _ed_timeout(), None)
    assert r["status"] == "ok" and r["from_cache"] and "caché" in r["cache_note"]
    se._LAST_OK.clear()


def test_sin_estados_no_es_un_tiempo_agotado():
    import self_exclusion as se
    ed = {"status": "ok", "cik": 1, "facts": None, "facts_status": "sin_estados", "facts_reason": "sin XBRL"}
    assert not se.figures_resilient("X", {"currency": "USD"}, ed, None).get("degraded")


def test_referencia_degradada_se_declara_en_la_fila_y_en_la_confianza():
    import industry_bench as ib
    import valuation_confidence as vc
    out = ib._self({"pe": 17.9, "ev_ebitda": 11.7}, "global", "Oil/Gas Distribution", 50, "ENB", None, "Canada",
                   {"status": "sin_dato", "degraded": True, "reason": "EDGAR no respondió a tiempo (reintentado)"},
                   "Enbridge", member=True)
    sx = out["self_exclusion"]
    assert sx["method"] == "mediana_pares" and sx["degraded"] and sx["declaration"].startswith("referencia degradada")
    d = vc.source_dimension(input_flags=[], normalization=None, ttm=None, provenance_fields={}, self_exclusion=sx)
    assert d["level"] != "alta" and any("degradada" in x for x in d["reasons"])
