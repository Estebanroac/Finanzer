"""
F10 · B1 (escaneo del modelo general, 28-oct-2026: 289 vacíos sin motivo en 97 empresas): ningún vacío sin motivo, en
la puntuación, el display (web) y el PDF. La regla está en lib/empty_reasons.py: denominador ≤ 0 → «n. s.» con su
motivo («patrimonio negativo», «beneficio negativo»…); sin el denominador, «sin dato» y qué falta.
"""
import glob
import json
import os

import pytest

import empty_reasons as ER
from financial_ratios import CategoryCoverage

HERE = os.path.dirname(__file__)
GOLDEN = sorted(p for env in ("panel", "local", "forzados") for p in glob.glob(os.path.join(HERE, "golden", env, "*.json")))


def _id(p):
    return f"{os.path.basename(os.path.dirname(p))}-{os.path.basename(p)[:-5]}"


def _load(p):
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def _flat(t):
    return " ".join(str(t).split()).lower()


# ── La regla ──
@pytest.mark.parametrize("metric,inputs,expected", [
    ("ROE", {"total_equity": -2.0e9}, ("no_significativo", "patrimonio negativo")),     # ABBV, AZO, BKNG
    ("D/E", {"common_equity": -1.0, "total_equity": 5.0}, ("no_significativo", "patrimonio negativo")),
    ("P/E", {"net_income": -3.0e8}, ("no_significativo", "beneficio negativo")),
    ("P/FCF", {"free_cash_flow": -2.4e9}, ("no_significativo", "flujo de caja libre negativo")),   # AMZN
    ("EV/EBITDA", {"ebitda": 0.0}, ("no_significativo", "EBITDA negativo")),
    ("P/FFO", {}, ("sin_dato", "sin el FFO en las fuentes")),                            # REIT sin FFO
    ("ROE", {"total_equity": 4.0e9}, None),                                              # la regla no decide
])
def test_denominator_rule(metric, inputs, expected):
    assert ER.reason(metric, inputs) == expected


def test_score_component_with_negative_denominator_is_not_significant():
    token = ER.INPUTS.set({"total_equity": -1.0, "net_income": 5.0})
    try:
        cov = CategoryCoverage()
        cov.comp("ROE", [-2, 3], None)
        cov.comp("Cobertura de intereses", [-2, 3], None)
    finally:
        ER.INPUTS.reset(token)
    rep = cov.report()
    assert rep["not_significant"] == {"ROE": "patrimonio negativo"} and "ROE" not in rep["missing"]
    assert rep["missing_reasons"]["Cobertura de intereses"].startswith("la empresa no presenta gasto por intereses")


def test_display_block_gets_its_reason_and_state():
    d = {"cards": [{"key": "roe", "label": "ROE", "value": "—", "state": "sin_dato"},
                   {"key": "p_ffo", "label": "P/FFO", "value": "—", "state": "sin_dato", "text": "sin FFO según Nareit: x"},
                   {"key": "zz", "label": "Otra", "state": "sin_dato"}]}
    ER.fill_display(d, {"key_metrics": {"total_equity": -3.0}})
    a, b, c = d["cards"]
    assert (a["state"], a["text"]) == ("no_significativo", "Patrimonio negativo")
    assert b["text"] == "sin FFO según Nareit: x"                                    # el suyo no se toca
    assert c["text"] == "La fuente no da la cifra"


# ── Los golden: display (web) y PDF ──
@pytest.mark.parametrize("path", GOLDEN, ids=_id)
def test_no_empty_without_reason(path):
    a = _load(path)
    bad = []
    for cat, c in (a.get("score_coverage") or {}).items():
        bad += [f"{cat}: {n}" for n in (c or {}).get("missing") or [] if not (c.get("missing_reasons") or {}).get(n)]
        for kind in ("not_applicable", "not_significant"):
            bad += [f"{cat}: {n} ({kind})" for n, w in ((c or {}).get(kind) or {}).items()
                    if not isinstance(w, str) or len(w.strip()) < ER.MIN_REASON_CHARS]

    def walk(o, p):
        if isinstance(o, dict):
            if o.get("state") in ER.EMPTY_STATES and not ER.has_reason(o):
                bad.append(f"{p}: {o.get('key') or o.get('label')} «{o['state']}»")
            for k, v in o.items():
                walk(v, f"{p}.{k}")
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, f"{p}[{i}]")
    walk(a.get("display") or {}, "display")
    assert not bad, "\n".join(bad[:10])


@pytest.mark.parametrize("path", [p for p in GOLDEN if "/forzados/" not in p], ids=_id)
def test_pdf_says_the_reason(path):
    """El PDF nuevo imprime el motivo de cada cifra clave y tarjeta sin dato (como la web)."""
    env, t = os.path.basename(os.path.dirname(path)), os.path.basename(path)[:-5]
    pdf = os.path.join(HERE, "golden", f"{env}_pdf_v2", f"{t}.pdf.txt")
    if not os.path.exists(pdf):
        pytest.skip("sin PDF nuevo en el golden")
    with open(pdf, encoding="utf-8") as fh:
        text = _flat(fh.read())
    d = _load(path).get("display") or {}
    blocks = list((d.get("cover") or {}).get("kpis") or []) + list(((d.get("summary") or {}).get("cards") or [])[:6])
    missing = []
    for b in blocks:
        why = b.get("text") or b.get("bench")
        if b.get("state") in ER.EMPTY_STATES and why and _flat(why)[:30].rstrip(".") not in text:
            missing.append(f"{b.get('label')}: {why}")
    assert not missing, "\n".join(missing)
