"""
Fase 2b (T2): dividendo indicado en la moneda y la clase del precio (lib/dividends.py) y su integración
(yf_adapter._apply_dividend). Sin red: pagos sintéticos y el panel en replay (serie de tests/fixtures/history).
"""
import datetime as dt

import pytest
from fastapi import HTTPException

import dividends as D
import fixture_backend as fb
import history_fixtures as hf

d = dt.date


def q(start, amounts, step=91):
    """Pagos trimestrales desde `start`."""
    return [(start + dt.timedelta(days=step * i), a) for i, a in enumerate(amounts)]


# ── reglas, con pagos sintéticos ──
def test_level_change_is_an_increase_not_an_extraordinary():
    ev = q(d(2024, 12, 5), [0.01, 0.01, 0.01, 0.01, 0.25, 0.25])          # NVDA
    p = D.from_payments(ev, d(2026, 4, 1))
    assert p["rate"] == pytest.approx(1.0) and p["basis"] == "ultimo_x_frecuencia"
    assert p["change"]["kind"] == "aumento" and p["extraordinary"] == []


def test_single_new_level_payment_is_regular_if_the_source_declares_it():
    ev = q(d(2025, 3, 1), [0.01, 0.01, 0.01, 0.01, 0.25])
    assert D.from_payments(ev, d(2026, 4, 1))["extraordinary"]                  # sin la fuente: parece extraordinario
    p = D.from_payments(ev, d(2026, 4, 1), declared_hint=1.0)                   # Finnhub 1.00 = 0.25 × 4
    assert p["rate"] == pytest.approx(1.0) and not p["extraordinary"]


def test_annual_variable_dividend_is_extraordinary():
    ev = q(d(2025, 1, 10), [4.6, 0.1, 0.1, 0.1, 13.6, 0.1, 0.1, 0.1])     # PGR
    p = D.from_payments(ev, d(2026, 10, 14))
    assert p["rate"] == pytest.approx(0.4)
    assert [e["amount"] for e in p["extraordinary"]] == [13.6]


def test_uneven_quarterly_cycle_with_a_larger_final_is_ordinary():
    ev = [(d(2025, 3, 7), 1.8), (d(2025, 5, 9), 0.5), (d(2025, 8, 15), 0.5), (d(2025, 11, 7), 0.5),
          (d(2026, 3, 13), 2.25), (d(2026, 5, 15), 0.5), (d(2026, 8, 14), 0.5)]   # HSBC
    p = D.from_payments(ev, d(2026, 10, 15))
    assert p["extraordinary"] == [] and p["rate"] == pytest.approx(3.75) and p["basis"] == "suma_ultimo_ciclo"
    assert "change" not in p


def test_semiannual_cycle_is_summed():
    ev = [(d(2025, 3, 31), 1.099), (d(2025, 8, 18), 0.584), (d(2026, 3, 30), 1.275), (d(2026, 8, 17), 0.579)]
    p = D.from_payments(ev, d(2026, 10, 15))                                  # NVO
    assert p["frequency"] == 2 and p["rate"] == pytest.approx(1.854)


def test_stale_history_has_no_rate():
    p = D.from_payments([(d(2024, 9, 30), 2.6), (d(2025, 3, 31), 3.457)], d(2026, 10, 15))   # TM en Yahoo
    assert p["rate"] is None and "historial incompleto" in p["reason"]


def test_foreign_line_uses_the_adr_payments_not_the_local_amount():
    ev = [(d(2025, 2, 28), 0.274), (d(2025, 8, 8), 0.16), (d(2026, 2, 20), 0.307), (d(2026, 8, 7), 0.313)]
    r = D.assess(ev, d(2026, 10, 15), 11.5, "finnhub", True, 0.9, unit="ADR")   # BCS: 11.5 peniques por ordinaria
    assert r["rate"] == pytest.approx(0.62) and r["source"] == "pagos"
    assert "11.5" in r["source_note"]


def test_domestic_source_accepted_within_tolerance_and_corrected_outside():
    ev = q(d(2025, 11, 20), [0.91, 0.91, 0.91, 0.91])                         # MSFT, subida declarada a 0.98
    ok = D.assess(ev, d(2026, 10, 14), 3.92, "finnhub", False, 3.5)
    assert ok["rate"] == 3.92 and ok["source"] == "finnhub"
    assert any("declarado mayor" in n for n in ok["notes"])
    bad = D.assess(ev, d(2026, 10, 14), 91.0, "finnhub", False, 3.5)          # unidad ajena (×25)
    assert bad["rate"] == pytest.approx(3.64) and bad["source"] == "pagos"


def test_fallback_conversion_must_match_what_the_statements_pay():
    cands = [(6.33, "100 JPY × 10 × 0.00633"), (0.0633, "100 céntimos")]
    r = D.assess([(d(2025, 3, 31), 3.457)], d(2026, 10, 15), 100.0, "finnhub", True, 6.16, cands, unit="ADR")
    assert r["rate"] == pytest.approx(6.33) and r["source"] == "fuente_local_convertida"
    none = D.assess([(d(2025, 3, 31), 3.457)], d(2026, 10, 15), 100.0, "finnhub", True, 60.0, cands)
    assert none["rate"] is None and "ninguna conversión cuadra" in none["reason"]


def test_non_payer_is_zero_and_unknown_payer_is_no_data():
    assert D.assess([], d(2026, 10, 15), None, None, False, None)["rate"] == 0.0
    r = D.assess(None, d(2026, 10, 15), None, None, True, 1.2)                # sin serie y los estados pagan
    assert r["rate"] is None


# ── panel en replay ──
CASES = {   # ticker: (yield esperado aprox., fuente, texto que debe llevar la nota)
    "BCS": (0.027, "pagos", None), "TSM": (0.009, "pagos", None), "NVO": (0.0486, "pagos", None),
    "UL": (0.0344, "pagos", None), "HSBC": (0.0397, "pagos", None), "SHEL": (0.0292, "pagos", None),
    "TM": (0.033, "fuente_local_convertida", None), "NVDA": (0.0045, "finnhub", "dividendo aumentado el 2026-06-04"),
    "PGR": (0.0019, "finnhub", "excluye el extraordinario de 13.60"),
}


@pytest.fixture(scope="module")
def panel():
    if not (fb.panel_available() and hf.available()):
        pytest.skip("sin fixtures del panel o del historial")
    out = {}
    with fb.replay(fb.fixtures_dir(fb.PANEL_ENV)) as store:
        for sym in CASES:
            out[sym] = fb.run_analysis(sym, store)
        assert not store.misses, store.misses
    return out


@pytest.mark.parametrize("sym", sorted(CASES))
def test_panel_dividend_in_price_unit(panel, sym):
    dy, src, note = CASES[sym]
    a = panel[sym]
    dv = a["data_provenance"]["dividend"]
    assert dv["source"] == src
    assert a["key_metrics"]["dividend_yield"] == pytest.approx(dy, rel=0.05)
    assert a["key_metrics"]["dividend_yield"] == pytest.approx(dv["rate"] / a["price"])
    assert not any(f["rule"] in ("identidad_dividendo", "dividendo_sin_fuente") for f in a["data_validation"])
    if note:
        assert any(note in n for n in dv["notes"]), dv["notes"]
