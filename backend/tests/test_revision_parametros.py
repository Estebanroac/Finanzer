"""Fase 7: cada parámetro de mercado tiene fuente y fechas, y los pares van juntos (config/review.toml). Sin red."""
import datetime as dt

from settings import cfg
import revision_parametros as R

P = cfg("review.parameters")


def test_every_parameter_resolves_and_is_dated_or_declared_provisional():
    for name, it in P.items():
        cfg(it["key"])                                     # la clave existe en la configuración
        assert it["source"] and it["cadence_days"] > 0, name
        if it["consulted"]:
            dt.date.fromisoformat(it["consulted"])
            if it["published"]:
                assert dt.date.fromisoformat(it["published"]) <= dt.date.fromisoformat(it["consulted"]), name
        else:
            assert it["source"].startswith("PROVISIONAL"), name


def test_pairs_are_updated_together():
    """RECON §7.13: la prima implícita se calcula con ese Rf; los dos cambian a la vez."""
    for name, it in P.items():
        if it["pair"]:
            other = P[it["pair"]]
            assert other["pair"] == name
            assert (other["published"], other["consulted"]) == (it["published"], it["consulted"])


def test_status_by_cadence():
    erp = dict(P["market_risk_premium"], published="2026-10-01", consulted="2026-10-12")   # el par de octubre
    assert R.estado(erp, dt.date(2026, 10, 17))[0] == "vigente"
    assert R.estado(erp, dt.date(2026, 11, 2)) == ("revisar", dt.date(2026, 11, 1))
    # fase 4/7: las referencias por industria ya tienen fuente (Damodaran, ene-2026); los umbrales siguen sin ella
    assert R.estado(P["sector_medians"], dt.date(2026, 10, 17)) == ("vigente", dt.date(2027, 1, 5))
    assert R.estado(P["score_thresholds"], dt.date(2026, 10, 17)) == ("sin fuente", None)
    # consultado después de la publicación esperada (2021 + 5 años) y sin edición nueva: cuenta desde la consulta
    assert R.estado(P["base_rates"], dt.date(2026, 10, 17))[0] == "vigente"


def test_monthly_cadence_follows_the_calendar_and_old_data_is_flagged():
    """Revisión de F7, hallazgo 10."""
    erp = dict(P["market_risk_premium"], published="2026-11-01", consulted="2026-11-03")
    assert R.estado(erp, dt.date(2026, 11, 20))[1] == dt.date(2026, 12, 1)
    assert R.estado(P["market_ev_ebitda"], dt.date(2026, 10, 17))[0] == "vigente, dato antiguo"


def test_market_pair_is_not_overdue_today():
    """F13 · paso 1 (decisión del usuario): la alarma de vencimiento. Falla el día en que la revisión mensual del par
    Rf–ERP de Damodaran vence: actualizar los dos valores en config/valuation.toml y sus filas aquí (review.toml)."""
    import parameter_review
    for name in ("market_risk_premium", "risk_free_rate"):
        r = parameter_review.parameter(name, dt.date.today())
        assert r["status"] != "revisar", (f"{name}: la revisión venció el {r['due']} (dato de {r['published']}); "
                                          "actualizar el par con la prima implícita de Damodaran del mes")


def test_overdue_pair_is_flagged_in_the_analysis(monkeypatch):
    """F13 · paso 1: con la revisión vencida, capm_rates lo dice (y la portada lo avisa: display.data_notices)."""
    import cost_of_capital
    import display
    monkeypatch.setattr(cost_of_capital, "_today", lambda: dt.date(2027, 1, 15))
    monkeypatch.setattr(cost_of_capital, "risk_free", lambda now=None: {"fallback": True})
    r = cost_of_capital.capm_rates()
    assert r["review"]["status"] == "revisar" and "venció" in r["reason"]
    notes = display.data_notices({"risk_free": r})
    assert any("revisión mensual venció" in n for n in notes)
    monkeypatch.setattr(cost_of_capital, "_today", lambda: dt.date(2026, 11, 20))
    r = cost_of_capital.capm_rates()
    assert r["review"]["status"] == "vigente" and not r["reason"]
