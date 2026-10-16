"""Etapa 9a: calidad del negocio y atractivo del precio, veredicto verbal y ajustes de RECON."""
import pytest

import fixture_backend as fb
import invariants as inv
from financial_ratios import score_crecimiento
from settings import cfg
from valuation_confidence import verdict_confidence
from verdict import confidence_phrase, part_score, price, quality, verdict


def _envs():
    """Juegos para los tests atados a los 6 tickers (local y panel)."""
    import conftest
    return conftest.BOUND_ENVS


def _generic_envs():
    """Juegos para los bucles que recorren TODOS los tickers de un juego: solo local (sobre el panel, esos
    invariantes los corre test_panel_invariants)."""
    import conftest
    return conftest.ENVS


def _cat(name, score, conclusive=True, applicable=True, low=False):
    return {"category": name, "score": score, "max_score": 20, "conclusive": conclusive,
            "applicable": applicable, "coverage": {"low_confidence": low}}


CATS = [_cat("Solidez Financiera", 16), _cat("Rentabilidad", 18), _cat("Valoración", 7),
        _cat("Calidad de Ganancias", 14), _cat("Crecimiento", 12)]


# ─────────────────────────── composición ───────────────────────────
def test_quality_is_four_categories_rescaled_and_price_is_valuation():
    q = quality(CATS)
    assert q["score"] == round((16 + 18 + 14 + 12) * 100 / 80) == 75
    assert [c["category"] for c in q["components"]] == list(cfg("thresholds.score.quality.categories"))
    p = price(CATS, "alta")
    assert p["score_raw"] == p["score"] == 35 and p["factor"] == 1.0 and not p["contracted"]


def test_inconclusive_or_not_applicable_categories_are_rescaled_out():
    cats = [_cat("Solidez Financiera", 16), _cat("Rentabilidad", 18), _cat("Valoración", 7),
            _cat("Calidad de Ganancias", 14, applicable=False), _cat("Crecimiento", 2, conclusive=False)]
    q = quality(cats)
    assert q["score"] == round((16 + 18) * 100 / 40) and q["basis"] == "calculado sobre 2 de 4 categorías"
    assert q["excluded_categories"] == ["Crecimiento"] and q["not_applicable_categories"] == ["Calidad de Ganancias"]
    assert q["low_confidence"] is True                    # cobertura baja: categoría no concluyente
    assert quality([_cat("Solidez Financiera", 10, low=True)])["low_confidence"] is True
    assert part_score([_cat("Valoración", 9, conclusive=False)], ["Valoración"])["score"] is None


# ─────────────────────────── contracción por confianza ───────────────────────────
@pytest.mark.parametrize("level,factor,shown", [("alta", 1.0, 80), ("media", 0.75, 72), ("baja", 0.5, 65)])
def test_price_contracts_towards_50_by_confidence(level, factor, shown):
    assert cfg("thresholds.score.price.confidence_factor")[level] == factor
    p = price([_cat("Valoración", 16)], level)             # crudo 80
    assert p["score_raw"] == 80 and p["score"] == shown == round(50 + 30 * factor)
    assert p["contracted"] is (factor != 1.0) and p["confidence"] == level


def test_quality_is_not_contracted_by_convergence(outputs_by_env):
    a = outputs_by_env("panel")["NFLX"][0]                  # convergencia baja, confianza media
    assert a["confidence"]["level"] == "media"
    q = a["quality"]
    by = {k: v["score"] for k, v in a["score"]["breakdown"].items()}
    assert q["score"] == round(sum(by[k] for k in cfg("thresholds.score.quality.categories")) * 100 / 80)
    p = a["price_attractiveness"]
    assert p["score"] == round(50 + (p["score_raw"] - 50) * 0.75) and p["factor"] == 0.75
    assert p["contracted"] is (p["score"] != p["score_raw"])


# ─────────────────────────── veredicto verbal ───────────────────────────
@pytest.mark.parametrize("value,level", [(80, "excelente"), (79, "sólida"), (65, "sólida"), (64, "media"),
                                         (45, "media"), (44, "débil"), (0, "débil")])
def test_quality_level_band_edges(value, level):
    cats = [_cat(n, value / 5) for n in cfg("thresholds.score.quality.categories")]
    assert quality(cats)["level"] == level


@pytest.mark.parametrize("raw,level", [(65, "atractivo"), (64, "razonable"), (45, "razonable"), (44, "exigente"),
                                       (30, "exigente"), (29, "muy exigente")])
def test_price_level_band_edges_on_contracted_value(raw, level):
    p = price([_cat("Valoración", raw / 5)], "alta")
    assert p["level"] == level
    # sobre el valor contraído: crudo 20 con confianza baja -> 35 "exigente", no "muy exigente"
    assert price([_cat("Valoración", 4)], "baja")["level"] == "exigente"


def test_verdict_sentence_and_confidence_phrase():
    conf = {"level": "media", "reasons": ["convergencia baja: …"],
            "dimensions": {"convergence": {"level": "baja", "methods": [
                {"method": "DCF", "evaluable": True}, {"method": "múltiplos frente al sector", "evaluable": True}]}}}
    v = verdict({"level": "sólida"}, {"level": "exigente"}, conf)
    assert v["text"] == "Calidad sólida · precio exigente"
    assert v["confidence_text"] == "(confianza media: el DCF y los múltiplos discrepan)"
    assert v["full"] == "Calidad sólida · precio exigente (confianza media: el DCF y los múltiplos discrepan)"
    assert confidence_phrase({"level": "media", "dimensions": {"convergence": {"level": "no_evaluable"}}}) \
        == "un solo método de valoración evaluable, sin contraste"
    # convergencia media por "uno en precio y otro con dirección": no se dice que coincidan en dirección
    mixed = {"level": "media", "dimensions": {"convergence": {"level": "media", "methods": [
        {"method": "DCF", "evaluable": True, "direction": "cara"},
        {"method": "múltiplos frente al sector", "evaluable": True, "direction": "en precio"}]}}}
    assert confidence_phrase(mixed) == "el DCF la ve cara y los múltiplos en precio"
    mixed["dimensions"]["convergence"]["methods"][1]["direction"] = "cara"
    assert confidence_phrase(mixed) == "el DCF y los múltiplos coinciden en dirección pero no en magnitud"


def test_verdicts_in_fixtures(outputs_by_env):
    for env in _generic_envs():
        for sym, (a, pdf) in outputs_by_env(env).items():
            inv.verdict_in_pdf(a, fb.pdf_text(pdf))


# ─────────────────────────── regla de confianza alta ───────────────────────────
def test_high_confidence_requires_high_convergence():
    def d(level):
        return {"level": level, "reasons": [level]}
    r = verdict_confidence({"convergence": d("media"), "coverage": d("alta"), "source": d("alta"),
                            "stability": d("alta")})
    assert r["score"] == pytest.approx(0.8) and r["level"] == "media" and r["capped_from"] == "alta"
    assert "alta exige convergencia alta" in r["reasons"][-1]
    assert verdict_confidence({"convergence": d("alta"), "coverage": d("alta"), "source": d("alta"),
                               "stability": d("alta")})["level"] == "alta"


def test_v_local_confidence_follows_the_statements_dcf(outputs_by_env):
    """RECON 7.13 / etapa 9b: la confianza alta de V local era falsa porque el DCF usaba el
    interanual de la fuente (23.8%: "barata") frente a múltiplos "cara". Con el CAGR de los
    estados (10.9%) ambos dicen "cara": la convergencia es alta y la confianza también."""
    a = outputs_by_env("local")["V"][0]
    conv = a["confidence"]["dimensions"]["convergence"]
    assert a["dcf"]["growth_rate"] == pytest.approx(0.109, abs=1e-3)
    assert {m["direction"] for m in conv["methods"] if m.get("evaluable")} == {"cara"}
    assert conv["level"] == "alta" and a["confidence"]["level"] == "alta"


# ─────────────────────────── REIT: retorno total ───────────────────────────
def test_reit_total_return_bands():
    T = cfg("thresholds.score.crecimiento")
    assert tuple(T["reit_total_return_bounds"]) == (0.10, 0.07, 0.04)

    def adj(ffo_ps, dy):
        r = score_crecimiento(ffo_ps, None, None, archetype="REIT", dividend_yield=dy)
        return next(a for a in r["adjustments"] if a["metric"].startswith("Retorno total"))
    assert adj(0.05, 0.06)["adjustment"] == T["reit_total_return_points"][0]     # 11%
    assert adj(0.0, 0.06)["adjustment"] == T["reit_total_return_points"][2]      # 6%
    assert "rentabilidad por dividendo 6.0%" in adj(0.0, 0.06)["reason"]
    r = score_crecimiento(0.03, None, None, archetype="REIT", dividend_yield=None)
    assert "Retorno total" in r["coverage"]["missing"]


def test_reit_dividend_yield_counted_once(outputs_by_env):
    for env in _envs():
        a = outputs_by_env(env)["O"][0]
        val = [x["metric"] for x in a["score"]["breakdown"]["Valoración"]["adjustments"]]
        cre = next(x for x in a["score"]["breakdown"]["Crecimiento"]["adjustments"]
                   if x["metric"].startswith("Retorno total"))
        assert not any("dividendo" in m.lower() for m in val)
        dy, ffo = a["key_metrics"]["dividend_yield"], a["archetype_metrics"]["ffo_per_share_cagr_3y"]
        assert cre["value"] == f"{dy + (0.0 if -0.02 <= ffo < 0 else ffo):.1%}"


# ─────────────────────────── precio sin calidad (etapa 9a) ───────────────────────────
def test_price_excludes_quality_built_bonuses_and_growth_bands(outputs_by_env):
    T = cfg("thresholds.score.valoracion")
    for k in ("garp_points", "growth_bonus_points", "rescue_quality_max", "pe_growth_mults",
              "pfcf_growth_bounds", "ev_ebitda_growth_mults", "quality_growth_min_quality"):
        assert k not in T, k
    for env in _generic_envs():
        for sym, (a, _) in outputs_by_env(env).items():
            inv.price_excludes_quality_built_bonuses(a, None)
    # Forward P/E y PEG se mantienen (son múltiplos)
    nflx = {x["metric"] for x in outputs_by_env("panel")["NFLX"][0]["score"]["breakdown"]["Valoración"]["adjustments"]}
    assert {"Forward P/E", "PEG Ratio"} <= nflx


# ─────────────────────────── bandas: una sola fuente ───────────────────────────
def test_pdf_readings_use_score_bands():
    import pdf_report as pr
    from financial_ratios import SECTOR_THRESHOLDS
    th = SECTOR_THRESHOLDS["technology"]
    T = cfg("thresholds.score.rentabilidad")
    assert pr.read_roe(th.roe_high * T["roe_high_mult"], 0.1, th)[0] == "Excepcional"
    assert pr.read_roe(th.roe_low, 0.1, th)[0] == "Competitivo"
    assert pr.read_roe(th.roe_low - 0.001, 0.1, th)[0] == "Bajo"
    b = cfg("thresholds.score.solidez.coverage_bounds")
    assert pr.read_coverage(b[0])[0] == "Muy holgada" and pr.read_coverage(b[3] - 0.01)[0] == "Crítica"
    assert pr.read_current(cfg("thresholds.score.solidez.current_bounds")[0])[0] == "Holgada"
    u = cfg("thresholds.score.valoracion.dcf_upside_bounds")
    assert pr.read_upside(u[1] * 100)[0] == "Infravalorada" and pr.read_upside(u[2] * 100)[0] == "Precio justo"
    for k in ("roe_bounds", "current_bounds", "de_bounds", "coverage_bounds", "growth_bounds", "upside_bounds",
              "spread_bounds"):
        assert k not in cfg("thresholds.pdf"), k


# ─────────────────────────── benchmark: sector o mercado ───────────────────────────
@pytest.mark.parametrize("sector,arch,profile", [
    ("financials", "MATURE", "market"), ("financials", "FINANCIAL", "sector"),
    ("real_estate", "CYCLICAL", "market"), ("real_estate", "REIT", "sector"),
    ("technology", "GROWTH_PRE_PROFIT", "sector"), ("communication", "MATURE", "sector")])
def test_benchmark_switches_to_market_when_archetype_contradicts_sector(sector, arch, profile):
    import main
    b = main._select_benchmark(sector, arch)
    assert b["profile"] == profile
    if profile == "market":
        M = cfg("sectors.benchmarks.market")
        assert all(b["values"][k] == v for k, v in M.items()) and set(b["sources"]) == set(M)
        from classify import archetype_label
        assert "mercado amplio" in b["reason"] and archetype_label(arch) in b["reason"]   # etapa 9b: etiqueta
    else:
        assert b["values"] == main._get_sector_benchmarks(sector) and b["reason"] is None


def test_market_profile_has_source_and_date_for_every_median():
    M, src = cfg("sectors.benchmarks.market"), cfg("sectors.benchmarks.market_source")
    assert set(M) == set(src) and set(M) <= set(cfg("sectors.benchmarks.default"))
    for k in M:
        assert "S&P 500" in src[k] and any(y in src[k] for y in ("2025", "2026")), k


def test_v_uses_market_benchmark_and_records_it(outputs_by_env):
    for env in _envs():
        res = outputs_by_env(env)
        a, pdf = res["V"]
        b = a["benchmark"]
        assert b["profile"] == "market" and b["sector"] == "financials"
        pe = next(x for x in a["score"]["breakdown"]["Valoración"]["adjustments"]
                  if x["metric"].startswith("P/E") and x["metric"].endswith("vs mercado"))
        assert f"vs {cfg('sectors.benchmarks.market.pe'):.1f}x mercado" in pe["reason"]
        text = fb.pdf_text(pdf).replace("\n", " ")
        assert "MERCADO" in text and "Referencia: medianas y umbrales del mercado amplio (S&P 500)" in text
        for sym in ("NFLX", "JPM", "O", "FCX", "SNOW"):
            assert res[sym][0]["benchmark"]["profile"] == "sector", (env, sym)


# ─────────────────────────── BPA frente a ingresos: informativo ───────────────────────────
def test_eps_vs_revenue_growth_is_informative_only(outputs_by_env):
    from financial_ratios import eps_vs_revenue_growth
    tol = cfg("thresholds.pdf.eps_revenue_gap")
    assert eps_vs_revenue_growth(0.10, 0.10 + tol + 0.01)["state"] == "expansion"
    assert eps_vs_revenue_growth(0.10, 0.10 - tol - 0.01)["state"] == "compresion"
    assert eps_vs_revenue_growth(0.10, 0.10)["state"] == "en_linea"
    assert eps_vs_revenue_growth(None, 0.1) is None and eps_vs_revenue_growth(0.1, 0.2, "REIT") is None
    for env in _generic_envs():
        for sym, (a, pdf) in outputs_by_env(env).items():
            inv.eps_vs_revenue_growth_is_informative_only(a, fb.pdf_text(pdf))
    nflx = outputs_by_env("panel")["NFLX"][0]["eps_vs_revenue_growth"]
    assert nflx["state"] == "expansion" and nflx["gap"] == pytest.approx(nflx["eps_growth"] - nflx["revenue_growth"])


# ─────────────────────────── perfil market completo (umbrales y alertas) ───────────────────────────
def _alert_text(a):
    return " ".join(f"{x['reason']} {x['detail']}" for k in ("red_flags", "warnings", "strengths")
                    for x in a["alerts"][k])


def test_market_profile_overrides_thresholds_and_alert_texts(outputs_by_env):
    D = cfg("sectors.score_thresholds.default")
    for env in _envs():
        res = outputs_by_env(env)
        a, _ = res["V"]
        b = a["benchmark"]
        assert b["thresholds_key"] == "market"
        assert b["thresholds"]["debt_equity_high"] == D["debt_equity_high"] and b["thresholds"]["roe_high"] == D["roe_high"]
        sol = {x["metric"]: x for x in a["score"]["breakdown"]["Solidez Financiera"]["adjustments"]}
        # D/E 0.66x frente a 1.0x del mercado: "controlada" (+2), no "muy baja" frente a los 10x de un banco
        assert sol["Deuda/Equity"]["adjustment"] == cfg("thresholds.score.solidez.de_points")[1]
        roe = next(x for x in a["score"]["breakdown"]["Rentabilidad"]["adjustments"] if x["metric"].startswith("ROE"))
        assert f"vs {D['roe_high']:.0%} rango alto del mercado" in roe["reason"] and "sector" not in roe["reason"]
        assert "del sector" not in _alert_text(a) and "del mercado" in _alert_text(a)
        assert res["JPM"][0]["benchmark"]["thresholds_key"] == "financials"


# ─────────────────────────── bloque de múltiplos correlacionados ───────────────────────────
def test_multiples_block_averages_members_and_caps_at_max(outputs_by_env):
    for env in _generic_envs():
        for sym, (a, _) in outputs_by_env(env).items():
            inv.multiples_block_averages_members_and_caps_at_max(a, None)
    v = outputs_by_env("panel")["V"][0]["score"]["breakdown"]["Valoración"]["adjustments"]
    blk = next(x for x in v if x["metric"] == "Bloque de múltiplos")
    # Etapa 11b: la compresión del Forward P/E no suma si el Forward P/E está en la peor banda. Con la mediana
    # forward explícita del perfil market (18.9x), 24.2x queda bajo el corte de la peor banda (18.9 × 1.3 = 24.6x):
    # la compresión suma (+2 → +0.67 en el bloque) y el bloque queda en −3 (−4 con el 18x heredado de default).
    assert blk["block_members"] == ["P/E", "Forward P/E", "P/FCF", "EV/EBITDA", "PEG"] and blk["adjustment"] == -3
    fpe = next(x for x in v if x["metric"] == "Forward P/E")
    # Fase 2b (T3): el P/E TTM usa el BPA del corte (10.73), no el de Finnhub que antes se imponía (11.75): 36.5x en
    # lugar de 33.3x, y la compresión hacia el forward suma 3 en lugar de 2 (el bloque sigue en −3).
    assert fpe["adjustment"] == 3 and "sin efecto" not in fpe["reason"]


def test_block_pdf_shows_each_multiple_and_the_block_line(outputs_by_env):
    text = fb.pdf_text(outputs_by_env("panel")["V"][1]).replace("\n", " ")
    assert "Bloque de múltiplos" in text and "(-4)" in text and "reescalados a ±1" in text


# ─────────────────────────── reportado / normalizado ───────────────────────────
def test_normalized_figures_are_labelled(outputs_by_env):
    for env in _generic_envs():
        for sym, (a, pdf) in outputs_by_env(env).items():
            inv.normalized_figures_are_labelled(a, fb.pdf_text(pdf))
    v = outputs_by_env("panel")["V"][0]
    roe = next(x for x in v["score"]["breakdown"]["Rentabilidad"]["adjustments"] if x["metric"] == "ROE normalizado")
    # El ROE que puntúa es el normalizado y no el reportado (panel: 66.6% frente a 64.2%; antes, prod 55.9%).
    assert roe["normalized"] is True and v["earnings_normalization"]["differs"]
    assert roe["value"] != f"{v['key_metrics']['roe']:.1%}"


# ─────────────────────────── crecimiento: CAGR 3 años, no interanual ───────────────────────────
def test_growth_scores_three_year_cagr_not_yoy(outputs_by_env):
    def crec(a, metric):
        return next((x for x in a["score"]["breakdown"]["Crecimiento"]["adjustments"] if x["metric"] == metric), None)
    prod, local = outputs_by_env("panel")["NFLX"][0], outputs_by_env("local")["NFLX"][0]
    # el interanual de Yahoo difiere entre capturas (16.0% / 24.0%); el CAGR de los estados anuales no
    assert prod["key_metrics"]["revenue_growth"] != local["key_metrics"]["revenue_growth"]
    for m in ("Crecimiento Ingresos 3Y", "Crecimiento EPS 3Y"):
        assert crec(prod, m)["value"] == crec(local, m)["value"], m
    ci = prod["classification"]["inputs"]["revenue_cagr_3y"]
    if "ingresos" not in prod["growth_basis"]["applied_to"]:
        assert crec(prod, "Crecimiento Ingresos 3Y")["value"] == f"{ci:.1%}"


# ─────────────────────────── rango de 52 semanas: solo posición ───────────────────────────
def test_52_week_range_is_position_only(outputs_by_env):
    import re
    import pdf_report as pr
    for p in (1, 15, 50, 80, 99):
        lab, tone, txt = pr.read_pos52(p)
        assert tone == "neu" and not re.search(r"\bcara\b|barata", f"{lab} {txt}", re.I)
    for env in _generic_envs():
        for sym, (a, pdf) in outputs_by_env(env).items():
            inv.range_52w_is_position_only(a, fb.pdf_text(pdf))


# ─────────────────────────── ronda 3 de la etapa 9a ───────────────────────────
def _bd(a, cat):
    return {x["metric"]: x for x in a["score"]["breakdown"][cat]["adjustments"]}


def test_cyclical_eps_growth_uses_cycle_average(outputs_by_env):
    for env in _envs():
        a = outputs_by_env(env)["FCX"][0]
        eps = _bd(a, "Crecimiento")["Crecimiento EPS 3Y"]
        assert "normalizado de ciclo medio" in eps["reason"]
        g = a["archetype_metrics"]["eps_growth_normalized"]
        assert eps["value"] == f"{g:.1%}"


def test_cyclical_pfcf_normalized_uses_maintenance_fcf(outputs_by_env):
    for env in _envs():
        a = outputs_by_env(env)["FCX"][0]
        xm = a["archetype_metrics"]
        assert xm["p_fcf_normalized"] == pytest.approx(a["key_metrics"]["market_cap"] / xm["fcf_maintenance"])


def test_reit_profitability_on_ffo_and_leverage_on_net_debt(outputs_by_env):
    for env in _envs():
        a = outputs_by_env(env)["O"][0]
        rent = _bd(a, "Rentabilidad")
        assert {"FFO / patrimonio", "Margen FFO"} <= set(rent)
        assert not {"ROE", "ROA", "Margen Neto", "ROIC vs WACC", "Margen Operativo"} & set(rent)
        na = a["score_coverage"]["rentabilidad"]["not_applicable"]
        assert {"ROE", "ROA", "Margen neto", "ROIC−WACC", "Margen bruto", "Margen operativo"} <= set(na)
        sol = _bd(a, "Solidez Financiera")
        assert sol["Deuda/Equity"]["adjustment"] == 0 and sol["Deuda/Equity"].get("informative")
        assert sol["Deuda neta/EBITDA"]["adjustment"] >= 0          # ~6x: adecuado para un REIT, no riesgo
        reasons = [x["reason"] for k in ("red_flags", "warnings", "strengths") for x in a["alerts"][k]]
        assert not any(r.startswith(("Margen bruto", "Destruye valor", "Apalancamiento elevado")) for r in reasons)


def test_growth_pre_profit_profitability_and_regla_m(outputs_by_env):
    for env in _envs():
        a = outputs_by_env(env)["SNOW"][0]
        rent = _bd(a, "Rentabilidad")
        assert {"Margen bruto", "Margen operativo", "Mejora del margen operativo", "Margen FCF − SBC"} <= set(rent)
        assert not {"ROE", "ROA", "Margen Neto", "ROIC vs WACC"} & set(rent)
        assert "Growth Company" not in _bd(a, "Crecimiento")
        if (a["key_metrics"].get("net_debt") or 0) < 0:                          # caja neta: el D/E no puntúa
            assert _bd(a, "Solidez Financiera")["Deuda/Equity"]["adjustment"] == 0
        assert _bd(a, "Calidad de Ganancias").get("FCF / beneficio neto", {}).get("value") in (None, "No significativo")
        reasons = [x["reason"] for k in ("red_flags", "warnings", "strengths") for x in a["alerts"][k]]
        assert "Calidad del beneficio baja" not in reasons and not any(r.startswith("Destruye valor") for r in reasons)
    # Regla M del ROIC (capital invertido < 10% de los activos). Antes con SNOW prod; en el panel SNOW tiene deuda
    # neta y ROIC calculable, y el caso lo da CRWD (capital invertido 8% de los activos).
    p = outputs_by_env("panel")["CRWD"][0]["key_metrics"]
    assert p["roic"] is None and "ROIC no significativo" in p["roic_reason"]


def test_financial_pb_block_and_policy_substitution(outputs_by_env):
    for env in _envs():
        a = outputs_by_env(env)["JPM"][0]
        blk = _bd(a, "Valoración")["Bloque P/B y P/TBV"]
        assert blk["block_max"] == cfg("thresholds.score.valoracion.multiples_block_max_by_members")[1]
        src = a["confidence"]["dimensions"]["source"]["reasons"]
        assert not any("crecimiento_financiera_estados" in r for r in src)
        flags = [f for f in a["data_validation"] if f.get("rule") == "crecimiento_financiera_estados"]
        assert all(f["action"] == "politica" for f in flags)


def test_no_text_cites_a_not_applicable_metric(outputs_by_env):
    for env in _generic_envs():
        for sym, (a, pdf) in outputs_by_env(env).items():
            inv.no_text_cites_a_not_applicable_metric(a, fb.pdf_text(pdf))


# ─────────────────────────── ronda 4: SBC y "no significativo" ───────────────────────────
def test_growth_pre_profit_uses_fcf_minus_sbc_but_runway_uses_cash(outputs_by_env):
    for env in _envs():
        a = outputs_by_env(env)["SNOW"][0]
        sb, xm = a["sbc"], a["archetype_metrics"]
        assert sb["sbc"] > 0 and xm["fcf_margin"] == pytest.approx(sb["fcf_margin_adjusted"])
        assert xm["fcf_margin"] == pytest.approx((sb["fcf"] - sb["sbc"]) / sb["revenue"])
        assert xm["rule_of_40"] == pytest.approx(xm["revenue_cagr_3y"] + xm["fcf_margin"])
        assert xm["runway"]["state"] == "autofinanciada" and xm["runway"]["fcf"] > 0      # caja pura
        rent = _bd(a, "Rentabilidad")["Margen FCF − SBC"]
        assert rent["value"] == f"{sb['fcf_margin_adjusted']:.1%}"
        # el crecimiento del FCF se mide sobre FCF − SBC; negativo en los 4 ejercicios = señal, peor tramo
        g = _bd(a, "Crecimiento")["Crecimiento FCF − SBC 3Y"]
        assert g["value"] == "Negativo sostenido" and g["adjustment"] == cfg("thresholds.score.crecimiento.fcf_points")[-1]
        assert not a["score_coverage"]["crecimiento"]["missing"]
        cal = _bd(a, "Calidad de Ganancias")["FCF − SBC"]
        assert cal["value"] == "Negativo" and "Free Cash Flow" not in _bd(a, "Calidad de Ganancias")
        al = [x for x in a["alerts"]["strengths"] if x["reason"].startswith("Autofinanciada")]
        assert al and al[0]["reason"].startswith("Autofinanciada en caja") and "dilución" in al[0]["detail"]
        assert f"{sb['sbc_to_revenue']:.1%}" in al[0]["detail"] and "depender" not in al[0]["detail"]
    # Con trimestrales (panel) la SBC es TTM; el juego prod, sin trimestrales, daba FY.
    assert outputs_by_env("panel")["SNOW"][0]["sbc"]["basis"].startswith("TTM")


def test_sbc_without_data_is_sin_dato():
    from archetype_metrics import sbc_adjustment
    r = sbc_adjustment(fcf=100.0, revenue=1000.0, fcf_is_ttm=True, sbc_ttm=None, st={})
    assert r["value"] is None and "no se usa el FCF bruto" in r["reason"]
    r = sbc_adjustment(fcf=None, revenue=None, fcf_is_ttm=False, sbc_ttm=None,
                       st={"free_cash_flow": [100.0], "revenue": [1000.0], "cf_years": ["2025"]})
    assert r["value"] is None and "Stock Based Compensation" in r["reason"]


def test_not_significant_is_excluded_like_not_applicable(outputs_by_env):
    # CRWD del panel: EBIT GAAP < 0 con caja neta (antes SNOW prod).
    a = outputs_by_env("panel")["CRWD"][0]
    sol = a["score_coverage"]["solidez"]
    assert "Cobertura de intereses" in sol["not_significant"] and "Cobertura de intereses" not in sol["missing"]
    assert not any(x["metric"] == "Cobertura" for x in a["score"]["breakdown"]["Solidez Financiera"]["adjustments"])


def test_cyclical_growth_narrative_uses_cycle_average(outputs_by_env):
    for env in _envs():
        a, pdf = outputs_by_env(env)["FCX"]
        text = fb.pdf_text(pdf).replace("\n", " ")
        assert "propio de compañías growth" not in text
        assert "Crecimiento del BPA (ciclo medio)" in text and "Crecimiento de beneficios (YoY)" not in text
        assert f"{a['archetype_metrics']['eps_growth_normalized'] * 100:.1f}%".lstrip("-") in text


def test_sustained_negative_is_a_signal_not_missing():
    from historical_metrics import growth_rate, is_sustained_negative
    r = growth_rate([-5.0, -4.0, -6.0, -3.0], 3, what="FCF")
    assert r["value"] is None and r.get("sustained_negative") and is_sustained_negative(r["reason"])
    r = growth_rate([5.0, -4.0, 6.0, 3.0], 3, what="FCF")               # cambio de signo: sigue sin dato
    assert r["value"] is None and not r.get("sustained_negative")


def test_cover_fits_one_page(outputs_by_env):
    for env in _generic_envs():
        for sym, (a, pdf) in outputs_by_env(env).items():
            inv.cover_fits_one_page(a, fb.pdf_text(pdf))


def test_singular_growth_reading_agrees():
    import pdf_report as pr
    assert pr.read_growth(-0.05, "el BPA", "eps", cycle=True)[2].startswith("el BPA se contrae un")
    assert pr.read_growth(-0.05, "los ingresos", cycle=True)[2].startswith("los ingresos se contraen un")
