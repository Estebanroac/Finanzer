"""
Fase 1 del plan de fiabilidad (BCS): en la salud financiera bancaria, "Dividendo sostenible" evalúa y cita el
payout, no el dividend yield (BCS decía "Dividendo sostenible (50.46%)" con un yield imposible y un payout de 28%).
"""
import pytest

import fixture_backend as fb

BANKS = ["JPM", "BAC", "PGR", "BRK-B", "BCS"]


@pytest.mark.parametrize("sym", BANKS)
def test_bank_dividend_component_cites_the_payout(sym, outputs_by_env):
    if not fb.panel_available():
        pytest.skip("sin panel")
    a = outputs_by_env("panel")[sym][0]
    km = a["key_metrics"]
    div = [d for d in (a.get("financial_health") or {}).get("details") or [] if d.get("metric") == "Dividendo"]
    po = km.get("payout_ratio")
    if po is None or po == 0:
        assert not div, "sin payout no se evalúa el dividendo"
        return
    assert len(div) == 1
    assert f"payout {po:.0%}" in div[0]["detail"], div[0]["detail"]
    dy = km.get("dividend_yield")
    if dy:
        assert f"{dy * 100:.2f}%" not in div[0]["detail"]
