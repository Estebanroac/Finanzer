"""
Fase 2b (T6, F2_PRECEDENCIA §5; D5): beta propia (o del sector, o de la fuente con aviso) y rango de 52 semanas desde la
serie de precios; la protección 2 (rango ensanchado con el precio) retirada.
"""
import numpy as np
import pandas as pd
import pytest

import beta as B
import cost_of_capital
import fixture_backend as fb
from settings import cfg


def test_sector_beta_by_industry_with_normalized_dashes():
    a = B.sector_beta("Utilities", "Utilities—Regulated Electric")
    b = B.sector_beta("Utilities", "Utilities - Regulated Electric")
    assert a == b and a["damodaran"] == "Power" and a["value"] == pytest.approx(0.48)
    assert "Damodaran" in a["source"]


def test_sector_beta_falls_back_to_the_firm_weighted_sector():
    r = B.sector_beta("Energy", "Industria que no está en la tabla")
    rows = [cfg("betas.industries")[i] for i in cfg("betas.yahoo_sectors")["Energy"]]
    assert r["basis"] == "sector" and r["value"] == pytest.approx(sum(n * b for n, b in rows) / sum(n for n, _ in rows))
    assert B.sector_beta("Sin sector", "Sin industria") is None


def _own(raw, r2, status="ok", n=104):
    return {"status": status, "raw": raw, "adjusted": 0.67 * raw + 0.33, "r2": r2, "observations": n}


def test_reliable_own_beta_is_used_with_blume():
    c = B.choose(_own(1.1, 0.3), 1.0, "finnhub", "Technology", "Semiconductors")
    assert (c["source"], c["value"], c["adjusted"], c["discrepancy"]) == ("propia", 1.1, False, None)


def test_low_r2_uses_the_sector_beta_already_adjusted():
    c = B.choose(_own(-0.12, 0.01), 0.33, "finnhub", "Utilities", "Utilities—Regulated Electric")
    assert c["source"] == "sector" and c["adjusted"] and c["value"] == pytest.approx(0.48)
    assert "R²" in c["reason"]


def test_without_series_the_source_beta_comes_with_a_warning():
    c = B.choose({"status": "sin_dato", "reason": "sin serie de la empresa"}, 1.3, "finnhub", "Technology", None)
    assert c["source"] == "fuente" and c["value"] == 1.3 and B.SOURCE_UNVERIFIED in c["reason"]


def test_discrepancy_between_sources_is_flagged():
    c = B.choose(_own(2.47, 0.26), 1.63, "finnhub", "Technology", "Software—Infrastructure")
    assert c["discrepancy"]["own"] == 2.47 and c["discrepancy"]["source"] == 1.63


def test_sector_beta_is_not_blume_adjusted_again():
    assert cost_of_capital.adjusted_beta(0.48, preadjusted=True) == 0.48
    assert cost_of_capital.adjusted_beta(0.48) == pytest.approx(0.67 * 0.48 + 0.33)


def _frame(days=420, last="2026-10-14"):
    idx = pd.bdate_range(end=last, periods=days)
    close = pd.Series(np.linspace(100, 150, len(idx)), index=idx)
    return pd.DataFrame({"close": close, "high": close + 1, "low": close - 1})


def test_range_uses_the_last_year_without_the_same_day_last_year():
    f = _frame()
    f.loc[pd.Timestamp("2025-10-14"), "low"] = 1.0           # el mismo día de hace un año: fuera
    r = B.range_52w(f, 150.0)
    assert r["status"] == "ok" and r["low"] > 1.0 and r["first_session"] > "2025-10-14"
    assert r["high"] == pytest.approx(151.0)


def test_price_outside_the_series_range_is_a_data_fault_not_widened():
    r = B.range_52w(_frame(), 200.0)
    assert r["status"] == "sin_dato" and r["high"] is None and "sesiones distintas" in r["reason"]


needs_panel = pytest.mark.skipif(not fb.panel_available(), reason="sin panel")


def _run(sym):
    with fb.replay(fb.fixtures_dir("panel")) as store:
        return fb.run_analysis(sym, store)


@needs_panel
def test_duk_uses_the_sector_beta():
    a = _run("DUK")
    assert a["beta"]["source"] == "sector" and a["wacc"]["beta"] == pytest.approx(0.48)
    assert a["wacc"]["beta_method"] == "beta del sector (sin Blume)"


@needs_panel
def test_pltr_discrepancy_is_registered():
    a = _run("PLTR")
    assert a["beta"]["source"] == "propia"
    assert any(f["rule"] == "beta_discrepante" for f in a["data_validation"])


@needs_panel
def test_xom_range_comes_from_the_series_and_contains_the_price():
    a = _run("XOM")
    km, rg = a["key_metrics"], a["data_provenance"]["range52"]
    assert rg["status"] == "ok" and km["price_52w_low"] <= a["price"] <= km["price_52w_high"]
    assert "ampliado con la cotización" not in str(a["data_provenance"]["fields"])


@needs_panel
def test_without_price_series_beta_from_source_and_range_without_data():
    import price_history

    def broken(*_a, **_k):
        raise ConnectionError("Yahoo history no responde")
    # Sin monkeypatch: al salir, el replay devuelve el descargador al que había antes de entrar.
    with fb.replay(fb.fixtures_dir("panel")) as store:
        price_history.FETCHER = broken
        a = fb.run_analysis("MSFT", store)
    assert a["beta"]["source"] == "fuente" and B.SOURCE_UNVERIFIED in a["beta"]["reason"]
    assert a["key_metrics"]["price_52w_high"] is None and a["data_provenance"]["range52"]["status"] == "sin_dato"


def test_session_without_close_kept_for_the_range():
    """Producción, XOM 2026-10-16: Yahoo da la barra de hoy sin cierre (máximo 179.16, mínimo 175.15) y la cotización
    178.98 es de hoy. Sin esa fila, el precio quedaba fuera de la serie y el rango salía sin dato."""
    import pandas as pd
    import price_history
    import beta as B
    idx = pd.date_range("2025-10-01", "2026-10-16", freq="B", tz="America/New_York")
    raw = pd.DataFrame({"Open": 150.0, "High": 160.0, "Low": 140.0, "Close": 155.0, "Volume": 1.0}, index=idx)
    raw.loc[idx[-2], ["High", "Close"]] = [178.69, 174.68]
    raw.loc[idx[-1], ["High", "Low", "Close"]] = [179.16, 175.15, float("nan")]
    frame = price_history.normalize(raw)
    assert frame.index[-1] == pd.Timestamp("2026-10-16") and pd.isna(frame["close"].iloc[-1])
    rg = B.range_52w(frame, 178.98)
    assert rg["status"] == "ok" and rg["high"] == 179.16 and rg["last_session"] == "2026-10-16"
    raw.loc[idx[-1], ["High", "Low"]] = [float("nan"), float("nan")]
    assert price_history.normalize(raw).index[-1] == pd.Timestamp("2026-10-15")   # sin datos de la sesión: fuera


def test_sector_beta_keeps_the_hyphen_inside_a_word():
    """Fase 4/7: "Beverages—Non-Alcoholic" (KO) casa con su industria de Damodaran; antes la normalización partía el
    guion interno ("non - alcoholic") y caía a la media del sector."""
    import beta
    sb = beta.sector_beta("Consumer Defensive", "Beverages—Non-Alcoholic")
    assert sb["basis"] == "industria" and sb["damodaran"] == "Beverage (Soft)"
