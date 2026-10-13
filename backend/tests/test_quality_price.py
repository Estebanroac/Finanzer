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
