"""
Fase 2b (T1): factor oficial de clase (ADR y clases de acciones) en lib/currency.py.

  · Los emisores de config/adr.toml usan el factor del depositario; el implícito (acciones de los estados /
    acciones de la cotización) solo es una comprobación: si difiere más de un 2%, se anota "recompras/emisiones
    desde el cierre" con la cifra, sin tocar el factor (BCS 4.154 → 4; TM 11.07 → 10).
  · Fuera de la tabla (propuesta para el punto de parada 1): el implícito se ajusta a la fracción simple más cercana
    si está a ≤ 2%, declarado "inferido"; si no, se aplica tal cual con aviso.
Sin red: contexto con datos sintéticos y el panel en replay.
"""
import pandas as pd
import pytest
from fastapi import HTTPException

import fixture_backend as fb
from currency import StatementContext


def _ctx(symbol, statement_shares, price_shares):
    ctx = StatementContext(symbol, "USD", "USD", "test", price_shares, ticker_cls=None)
    bs = pd.DataFrame({pd.Timestamp("2025-12-31"): [statement_shares]}, index=["Ordinary Shares Number"])
    ctx.prepare_class(bs)
    return ctx


# ── unidad: emisores de la tabla ──
def test_official_factor_overrides_implied_and_notes_the_buyback_gap():
    ctx = _ctx("BCS", 13_844_768_457, 3_332_849_568)      # implícito 4.154 (recompras de 2026)
    d = ctx.class_detail
    assert ctx.class_factor == 4.0 and ctx.class_applied
    assert d["basis"] == "oficial"
    assert d["official"]["depositary"] == "JPMorgan" and "20-F" in d["official"]["source"]
    assert d["implied"] == pytest.approx(4.154, abs=1e-3)
    gap = d["implied_check"]
    assert gap["deviation"] == pytest.approx(0.0385, abs=1e-3)
    assert "recompras/emisiones desde el cierre" in gap["note"]


def test_official_factor_one_is_not_applied_and_small_gap_is_silent():
    ctx = _ctx("UL", 2_179_500_000, 2_153_500_000)        # implícito 1.012 (dentro del 2%)
    assert ctx.class_factor == 1.0 and not ctx.class_applied
    assert ctx.class_detail["basis"] == "oficial"
    assert "implied_check" not in ctx.class_detail


def test_official_class_factor_brk_b():
    ctx = _ctx("BRK-B", 1_438_000, 2_140_000_000)         # acciones A equivalentes / acciones B
    assert ctx.class_factor == pytest.approx(1 / 1500) and ctx.class_applied
    assert ctx.class_detail["basis"] == "oficial"


def test_official_factor_without_statement_shares_is_still_applied():
    ctx = StatementContext("TSM", "USD", "TWD", "test", 5_186_000_000, ticker_cls=None)
    ctx.prepare_class(None)
    assert ctx.class_factor == 5.0 and ctx.class_applied
    assert ctx.class_detail["implied"] is None


# ── unidad: fuera de la tabla (propuesta) ──
def test_inferred_factor_snaps_to_simple_fraction_within_2pct():
    ctx = _ctx("ZZZ", 4.03e9, 1.0e9)
    assert ctx.class_factor == 4.0 and ctx.class_applied
    assert ctx.class_detail["basis"] == "inferido"
    assert "sin verificar con el depositario" in ctx.class_detail["note"]


def test_inferred_factor_without_simple_fraction_keeps_implied_with_warning():
    ctx = _ctx("ZZZ", 4.154e9, 1.0e9)
    assert ctx.class_factor == pytest.approx(4.154) and ctx.class_applied
    assert ctx.class_detail["basis"] == "implicito"
    assert "sin fracción simple" in ctx.class_detail["note"]


def test_same_class_outside_table_is_not_restated():
    ctx = _ctx("ZZZ", 1.012e9, 1.0e9)
    assert not ctx.class_applied
    assert ctx.class_detail["basis"] == "misma_clase"


# ── panel en replay ──
@pytest.fixture(scope="module")
def panel():
    if not fb.panel_available():
        pytest.skip("sin fixtures del panel")
    out = {}
    with fb.replay(fb.fixtures_dir(fb.PANEL_ENV)) as store:
        for sym in ("BCS", "TM", "UL", "TSM", "HSBC", "SHEL", "BRK-B"):
            try:
                out[sym] = fb.run_analysis(sym, store)
            except HTTPException as e:
                out[sym] = e
    return out


@pytest.mark.parametrize("sym,factor,gap", [("BCS", 4.0, True), ("TM", 10.0, True), ("TSM", 5.0, False),
                                            ("HSBC", 5.0, False), ("SHEL", 2.0, False)])
def test_panel_adr_uses_official_factor(panel, sym, factor, gap):
    sc = panel[sym]["data_provenance"]["currency"]["share_class"]
    assert sc["factor"] == factor and sc["applied"] and sc["basis"] == "oficial"
    assert ("implied_check" in sc) is gap


def test_panel_tm_gap_is_the_toyota_buyback(panel):
    gap = panel["TM"]["data_provenance"]["currency"]["share_class"]["implied_check"]
    # 13,033 millones de acciones a 2026-03-31 frente a 11,778 millones de hoy (1,178 millones de ADR × 10).
    assert gap["deviation"] == pytest.approx(0.1066, abs=2e-3)
    assert gap["price_shares_in_statement_class"] == pytest.approx(11_778_065_510, rel=1e-6)


def test_panel_ul_official_factor_one(panel):
    sc = panel["UL"]["data_provenance"]["currency"]["share_class"]
    assert sc["factor"] == 1.0 and not sc["applied"] and sc["basis"] == "oficial"
