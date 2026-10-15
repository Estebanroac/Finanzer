"""
Fase 1 del plan de fiabilidad (T3.2): el motor conserva sus códigos ("STRONG", "N/A"); la capa de presentación
(display y PDF) los dice en castellano. Sin dato: "—".
"""
import pytest

import fixture_backend as fb
from display import FIN_HEALTH_LEVEL_ES, fv, _es_value


def test_formatters_never_say_na():
    assert fv(None) == "—" and fv("x", "pct") == "—" and _es_value("N/A") == "—" and _es_value("12%") == "12%"
    assert set(FIN_HEALTH_LEVEL_ES) == {"STRONG", "GOOD", "NEUTRAL", "WEAK"}


@pytest.mark.parametrize("sym", ["JPM", "BAC", "PGR", "BRK-B", "DOW", "SNOW"])
def test_bank_health_and_missing_values_in_spanish(sym, outputs_by_env):
    if not fb.panel_available():
        pytest.skip("sin panel")
    a, pdf = outputs_by_env("panel")[sym]
    txt = fb.pdf_text(pdf)
    for w in ("STRONG", "GOOD", "WEAK", "N/A"):
        assert w not in txt, (sym, w)
    import json
    disp = json.dumps(a["display"], ensure_ascii=False)
    assert "STRONG" not in disp and '"N/A"' not in disp
    fh = a.get("financial_health") or {}
    if fh.get("level") == "STRONG":                     # el motor sigue con su código
        card = next(c for c in a["display"]["sections"]["institutional"]["cards"] if c["key"] == "financial_health")
        assert card["subtitle"] == "Sólida"
