"""
Fase 1 del plan de fiabilidad (T3.3, D1): los códigos internos y los motivos técnicos salen de las páginas de
lectura y se reúnen en un anexo final del PDF, "Detalle técnico para auditoría". La web no los muestra.
"""
import json

import pytest

import fixture_backend as fb
from invariants import ANNEX_TITLE, CODES, reading_text

CASES = ([("panel", t) for t in fb.PANEL_TICKERS if t != "SPY"] if fb.panel_available() else []) + \
        [("local", t) for t in fb.TICKERS]


@pytest.mark.parametrize("env,sym", CASES, ids=[f"{e}-{t}" for e, t in CASES])
def test_annex_at_the_end_with_the_codes(env, sym, outputs_by_env):
    a, pdf = outputs_by_env(env)[sym]
    txt = fb.pdf_text(pdf)
    assert txt.count(ANNEX_TITLE) == 1, "el anexo técnico aparece una vez"
    annex = txt[txt.index(ANNEX_TITLE):]
    assert f"Arquetipo {a['classification']['archetype']}" in annex.replace("\n", " ")
    assert "Metodología." not in annex, "el anexo es lo último del informe"
    assert not CODES.search(reading_text(txt))


@pytest.mark.parametrize("env,sym", CASES, ids=[f"{e}-{t}" for e, t in CASES])
def test_web_contract_has_no_technical_detail(env, sym, outputs_by_env):
    d = outputs_by_env(env)[sym][0]["display"]
    assert "classification_detail" not in d["cover"]
    assert all("detail" not in r for r in (d.get("confidence") or {}).get("reasons") or [])
    visible = json.dumps({k: v for k, v in d.items() if k != "annex"}, ensure_ascii=False)
    assert "validación: " not in visible and "(regla " not in visible


@pytest.mark.parametrize("env,sym", CASES, ids=[f"{e}-{t}" for e, t in CASES])
def test_annex_is_not_split_across_pages(env, sym, outputs_by_env):
    """El título del anexo y sus líneas van en la misma página (AAPL y SNOW lo partían)."""
    pages = fb.pdf_text(outputs_by_env(env)[sym][1]).split("===== página ")
    holder = [p for p in pages if ANNEX_TITLE in p]
    assert len(holder) == 1 and holder[0] is pages[-1], "el anexo empieza y termina en la última página"
