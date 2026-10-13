"""Etapa 9a: calidad del negocio y atractivo del precio, veredicto verbal y ajustes de RECON."""
import pytest

import fixture_backend as fb
from financial_ratios import score_crecimiento
from settings import cfg
from valuation_confidence import verdict_confidence
from verdict import confidence_phrase, part_score, price, quality, verdict


def _envs():
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
    a = outputs_by_env("prod")["NFLX"][0]                  # convergencia baja, confianza media
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
    for env in _envs():
        for sym, (a, pdf) in outputs_by_env(env).items():
            v = a["verdict"]
            assert v["text"].startswith("Calidad ") and " · precio " in v["text"]
            text = fb.pdf_text(pdf)
            assert v["text"] in text.replace("\n", " "), (env, sym)
            for banned in ("score total", "puntuación global", "Puntuación propietaria"):
                assert banned not in text.lower(), (env, sym, banned)
            assert "total_score" not in a["score"] and "max_score" not in a["score"]


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


def test_v_local_no_longer_high_confidence(outputs_by_env):
    c = outputs_by_env("local")["V"][0]["confidence"]
    assert c["dimensions"]["convergence"]["level"] != "alta" and c["level"] != "alta"


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
    for env in _envs():
        for sym, (a, _) in outputs_by_env(env).items():
            metrics = {x["metric"] for x in a["score"]["breakdown"]["Valoración"]["adjustments"]}
            assert not metrics & {"Perfil GARP", "Growth Quality", "Ajuste Growth", "Ajuste Crecimiento"}, (env, sym)
    # Forward P/E y PEG se mantienen (son múltiplos)
    nflx = {x["metric"] for x in outputs_by_env("prod")["NFLX"][0]["score"]["breakdown"]["Valoración"]["adjustments"]}
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
        assert "mercado amplio" in b["reason"] and arch in b["reason"]
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
    for env in _envs():
        for sym, (a, pdf) in outputs_by_env(env).items():
            e = a.get("eps_vs_revenue_growth")
            metrics = {x["metric"] for c in a["score"]["breakdown"].values() for x in c["adjustments"]}
            assert not any("frente a ingresos" in m for m in metrics), (env, sym)   # no puntúa
            if e:
                assert e["scored"] is False and "Dato informativo, no puntúa" in fb.pdf_text(pdf).replace("\n", " ")
    nflx = outputs_by_env("prod")["NFLX"][0]["eps_vs_revenue_growth"]
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
    M = cfg("thresholds.score.valoracion.multiples_block_max")
    for env in _envs():
        for sym, (a, _) in outputs_by_env(env).items():
            val = a["score"]["breakdown"]["Valoración"]
            members = [x for x in val["adjustments"] if x.get("in_block")]
            blk = [x for x in val["adjustments"] if x["metric"] == "Bloque de múltiplos"]
            if not members:
                assert not blk, (env, sym)
                continue
            assert len(blk) == 1 and len(blk[0]["block_members"]) == len(members), (env, sym)
            raw = blk[0]["block_mean"] * M
            assert abs(blk[0]["adjustment"]) <= M
            assert blk[0]["adjustment"] == int(abs(raw) + 0.5) * (1 if raw >= 0 else -1), (env, sym)
            counted = sum(x["adjustment"] for x in val["adjustments"] if not x.get("in_block"))
            assert val["score"] == max(0, min(20, 10 + counted)), (env, sym)
    v = outputs_by_env("prod")["V"][0]["score"]["breakdown"]["Valoración"]["adjustments"]
    blk = next(x for x in v if x["metric"] == "Bloque de múltiplos")
    assert blk["block_members"] == ["P/E", "Forward P/E", "P/FCF", "EV/EBITDA", "PEG"] and blk["adjustment"] == -3


def test_block_pdf_shows_each_multiple_and_the_block_line(outputs_by_env):
    text = fb.pdf_text(outputs_by_env("prod")["V"][1]).replace("\n", " ")
    assert "Bloque de múltiplos" in text and "(-4)" in text and "promedio normalizado" in text


# ─────────────────────────── reportado / normalizado ───────────────────────────
def test_normalized_figures_are_labelled(outputs_by_env):
    for env in _envs():
        for sym, (a, pdf) in outputs_by_env(env).items():
            if not (a.get("earnings_normalization") or {}).get("used_in_score"):
                continue
            metrics = [x["metric"] for c in a["score"]["breakdown"].values() for x in c["adjustments"]]
            assert "ROE" not in metrics and "Margen Neto" not in metrics, (env, sym)
            if "ROE normalizado" in metrics:
                assert all("ROE" not in x["reason"].split(" — ")[0] or "normalizado" in x["reason"]
                           for k in ("red_flags", "warnings", "strengths") for x in a["alerts"][k]
                           if x["category"] == "Rentabilidad" and x["reason"].startswith("ROE")), (env, sym)
            cover = fb.pdf_text(pdf).split("===== página 2")[0]
            assert "REPORTADO" in cover or a["classification"]["archetype"] in ("REIT",), (env, sym)
    v = outputs_by_env("prod")["V"][0]
    roe = next(x for x in v["score"]["breakdown"]["Rentabilidad"]["adjustments"] if x["metric"] == "ROE normalizado")
    assert roe["value"] == "55.9%" and roe["normalized"] is True


# ─────────────────────────── crecimiento: CAGR 3 años, no interanual ───────────────────────────
def test_growth_scores_three_year_cagr_not_yoy(outputs_by_env):
    def crec(a, metric):
        return next((x for x in a["score"]["breakdown"]["Crecimiento"]["adjustments"] if x["metric"] == metric), None)
    prod, local = outputs_by_env("prod")["NFLX"][0], outputs_by_env("local")["NFLX"][0]
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
    for env in _envs():
        for sym, (a, pdf) in outputs_by_env(env).items():
            text = fb.pdf_text(pdf)
            assert "PRECIO · 52 SEM." not in text and "¿Cara o barata hoy?" not in text, (env, sym)
            for line in text.splitlines():
                if "52 semanas" in line or "52 SEM" in line:
                    assert not re.search(r"\bcara\b|barata", line, re.I), (env, sym, line)
