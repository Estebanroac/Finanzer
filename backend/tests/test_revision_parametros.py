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
    erp = P["market_risk_premium"]
    assert R.estado(erp, dt.date(2026, 10, 17))[0] == "vigente"
    assert R.estado(erp, dt.date(2026, 11, 2)) == ("revisar", dt.date(2026, 11, 1))
    assert R.estado(P["sector_medians"], dt.date(2026, 10, 17)) == ("sin fuente", None)
    # consultado después de la publicación esperada (2021 + 5 años) y sin edición nueva: cuenta desde la consulta
    assert R.estado(P["base_rates"], dt.date(2026, 10, 17))[0] == "vigente"
