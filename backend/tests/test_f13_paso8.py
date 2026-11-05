"""
F13 · paso 8 (revisión de 110 empresas, familia F): sin veredicto de precio cuando el precio no es de hoy (EA, WBD) y
una beta negativa de la fuente fuera del CAPM (WBD). Cifras del banco congelado del 5-nov-2026.
"""
import beta
import verdict


def _ph(last, mkt="2026-11-05", rows=502):
    return {"last_date": last, "rows": rows, "market": {"last_date": mkt}}


def test_stale_quote_has_no_price_verdict():
    """EA: un solo precio, del 4-ago-2026, 93 días antes que el mercado."""
    why = verdict.abstention(_ph("2026-08-04", rows=1), "Unknown")
    assert why and "93 días" in why and "4 de agosto de 2026" in why
    assert verdict.abstention(_ph("2026-11-04"), "Technology") is None       # un festivo o un día sin sesión: no


def test_no_profile_and_short_history_has_no_price_verdict():
    assert "sin perfil" in verdict.abstention(_ph("2026-11-05", rows=5), "Unknown")
    assert verdict.abstention(_ph("2026-11-05", rows=5), "Technology") is None   # salida a bolsa reciente con perfil


def test_abstained_price_keeps_its_reason_through_the_verdict_and_reprice():
    p = verdict.abstain({"score": 40, "score_raw": 30, "level": "exigente"}, "motivo")
    v = verdict.verdict({"level": "sólida"}, p, {"level": "baja"})
    assert v["full"] == "Calidad sólida · precio sin veredicto (motivo)" and v["price_level"] is None
    assert verdict.reprice(p, "media")["level"] is None


def test_negative_source_beta_does_not_enter_the_capm():
    """WBD: −0,60 de Finnhub, sin historial propio ni industria."""
    own = {"status": "historia_insuficiente", "observations": 0, "reason": "0 semanas"}
    out = beta.choose(own, -0.597, "finnhub", "Unknown", "Unknown")
    assert out["value"] is None and out["source"] == "sin_dato" and "negativa" in out["reason"]
    assert beta.choose(own, 0.85, "finnhub", "Unknown", "Unknown")["value"] == 0.85
