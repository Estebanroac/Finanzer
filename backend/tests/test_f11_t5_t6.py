"""
F11 · paso 5 (revisión de NU y NFLX): T5, la beta sustituta contrastada con la propia; T6, la causalidad de una caída
sostenida por los datos (la fuerza relativa frente al país de la sede y la sobrerreacción solo con reacción no negativa).
"""
import market_context as mc
from beta import contrast
from plain_language import translate


def _own(raw, se, r2):
    return {"raw": raw, "se": se, "r2": r2}


def test_beta_contrast_flags_a_substitute_outside_the_own_interval():
    """NU: industria 0,60 frente a la propia 1,32 ± 2 · 0,28 → fuera, con el intervalo."""
    c = contrast("sector", 0.60, _own(1.32, 0.28, 0.20))
    assert c and c["low"] < 1.32 < c["high"] and not (c["low"] <= 0.60 <= c["high"])


def test_beta_contrast_is_silent_inside_without_fit_or_on_own_beta():
    assert contrast("sector", 1.10, _own(1.32, 0.28, 0.20)) is None          # dentro de ± 2 EE
    assert contrast("sector", 0.60, _own(1.32, 0.28, 0.02)) is None          # R² ≈ 0 (KO, HSY): nada que contrastar
    assert contrast("propia", 0.60, _own(1.32, 0.28, 0.20)) is None          # usa la propia
    assert contrast("sector", 0.60, None) is None


def test_beta_contrast_reason_has_plain_translation():
    txt = translate("beta sustituta 1.46 fuera de la propia 0.73 ± 2 EE (0.39–1.07, R² 0.15)")
    assert "beta de su industria (1.46)" in txt and "(la suya: 0.73)" in txt


def _rs(company, sector, country=None, country_status="ok"):
    sig = {"relative_strength": {"status": "ok", "windows": {"1A": {"status": "ok", "company": company,
                                                                    "sector": sector,
                                                                    "difference": company - sector}}}}
    if country is not None or country_status != "ok":
        sig["relative_strength_country"] = {
            "status": country_status, "country": "Brazil", "etf": "EWZ",
            "windows": ({"1A": {"status": "ok", "company": company, "sector": country,
                                "difference": company - (country or 0)}} if country_status == "ok" else {})}
    ctx = {"signals": sig, "sector_etf": "XLF"}
    return next(r["text"] for r in mc.readings(ctx) if r["key"] == "relative_strength")


def test_foreign_issuer_is_own_only_against_sector_and_country():
    assert _rs(0.40, 0.05, 0.38).endswith("se mueve con su país")
    assert _rs(0.40, 0.05, 0.02).endswith("el movimiento es propio de la empresa")
    assert _rs(0.06, 0.05, 0.40).endswith("se mueve con su sector")
    assert "no hay serie de su país (Brazil)" in _rs(0.40, 0.05, country_status="sin_dato")
    assert _rs(0.40, 0.05).endswith("el movimiento es propio de la empresa")   # emisor de EE. UU.: como siempre


def _drop_case(reaction):
    a = {"key_metrics": {"price": 50, "price_52w_high": 100}, "quality": {"level": "excelente"},
         "classification": {"archetype": "QUALITY_GROWTH", "inputs": {"revenue_cagr_3y": 0.12}},
         "score": {"breakdown": {"Crecimiento": {"adjustments": [{"metric": "Crecimiento del BPA (3 años)",
                                                                  "raw": 0.30}]}}}}
    ctx = {"series_drawdown": {"from_high": -0.47, "years": 2, "high_date": "2025-06-30"},
           "pead": {"status": "ok", "reaction": reaction} if reaction is not None else {"status": "sin_dato"}}
    return next(b for b in mc.behavioral(ctx, a) if b["field"] == "market_context.series_drawdown.from_high")


def test_overreaction_only_with_a_non_negative_earnings_reaction():
    """NFLX: −47 % desde el máximo con una reacción de −4,9 % a sus resultados no es «sobrerreacción»."""
    assert _drop_case(0.03)["kind"] == "sobrerreaccion"
    neg = _drop_case(-0.049)
    assert neg["kind"] == "caida_sin_explicar" and "No es una señal de compra" in neg["text"]
    assert "De Bondt" not in neg["text"]
    assert _drop_case(None)["kind"] == "caida_sin_explicar"
