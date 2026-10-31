"""V2 con fuentes reales (F9 · R3): la comparación web ↔ PDF de la portada (tools/coherencia_portada.py) separa dos
valores distintos (fallo) de la misma cifra con otra precisión (aviso), y empareja la misma métrica con otro nombre."""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import coherencia_portada as C  # noqa: E402


@pytest.mark.parametrize("web,pdf,expected", [
    ("39.33x", "39.3x", "≈"),            # otra precisión
    ("20.55%", "20.5%", "≈"),            # doble redondeo (20.548)
    ("−0.09%", "-0.1%", "≈"),            # signo menos tipográfico
    ("1.97%", "2.0%", "≈"),
    ("No aplica", "No aplica", "="),
    ("5.34x", "4.55x", "≠"),             # la revisión de NU: P/B 5,34 frente a 4,55
    ("52.3%", "48.8%", "≠"),             # CAGR 52,3 frente a 48,8
    ("2.46x", "2.5%", "≠"),              # otra unidad
    ("Sin dato", "12.0%", "≠"),
])
def test_same_value(web, pdf, expected):
    assert C.same_value(web, pdf) == expected


def test_labels_reportado_pair_with_plain():
    assert C.loose_key("P/E reportado (TTM)") == C.loose_key("P/E (TTM)")
    assert C.loose_key("ROE reportado") == C.loose_key("ROE")


def test_check_pairs_kpis_and_flags_contradictions(tmp_path, monkeypatch):
    analysis = {"display": {"summary": {"cards": [
        {"label": "P/B", "value": "4.55", "unit": "x", "state": "con_dato"},
        {"label": "ROE", "value": "20.5", "unit": "%", "state": "con_dato"},
        {"label": "EV/EBITDA", "value": "", "unit": "", "state": "no_aplica"}]}}}
    (tmp_path / "NU.analysis.json").write_text(json.dumps(analysis), encoding="utf-8")
    (tmp_path / "NU.pdf").write_bytes(b"%PDF")
    web = {"price": "$14.20", "kpis": [{"label": "P/B", "value": "5.34x"}, {"label": "ROE reportado", "value": "20.55%"},
                                       {"label": "Beta bruta", "value": "0.40"}]}
    monkeypatch.setattr(C, "cover_text", lambda _p: "$14.20 P/B 4.55x ROE 20.5% EV/EBITDA No aplica")
    rows, notes = C.check("NU", {"web": web, "pdf_status": 200}, str(tmp_path))
    by = {r[0]: r for r in rows}
    assert by["Precio"][3] == "="
    assert by["Cifra clave · P/B"][3] == "≠"
    assert by["Cifra clave · ROE reportado (en el PDF, «ROE»)"][3] == "≈"
    assert "solo en la web (La empresa): Beta bruta" in notes
    assert "solo en la portada del PDF: EV/EBITDA" in notes
