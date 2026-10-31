"""
Rediseño E5 (Task 6): el guardián narrativo (tests/guardian.py) sobre el texto del PDF nuevo en el panel completo.

Mismas reglas que con el informe actual; la única diferencia es el glosario de métricas (definiciones de la web bajo
el nombre de cada métrica), que no afirma nada de la empresa y la red de seguridad no trata como afirmación.
"""
import re

import pytest

import fixture_backend as fb
import guardian as g

CASES = [t for t in fb.env_tickers(fb.PANEL_ENV) if t != "SPY"] if fb.panel_available() else []


@pytest.fixture(scope="module")
def glossary():
    return g.glossary_texts()


@pytest.mark.parametrize("sym", CASES)
def test_guardian_on_pdf_v2(sym, glossary):
    a, txt, recs = g.run(sym, fb.PANEL_ENV, pdf="v2")
    assert txt, "sin texto del PDF nuevo"
    fails = g.check(a, txt, recs, glossary=glossary)
    assert not fails, "\n".join(f"{f['rule']}: {f['detail']}" for f in fails[:8])
    said = motor_outside_methodology(txt)
    assert not said, f"«motor» fuera de la metodología y el anexo: {said[:5]}"


# V7 (PM): «motor» no aparece en el PDF nuevo salvo en la metodología y el anexo, donde se explica cómo funciona. «Motor»
# con mayúscula es un nombre propio (Toyota Motor, Motor Vehicles) y «motor de creación de valor», otro sentido.
_METHODOLOGY_START = re.compile(r"^METODOLOGÍA\n", re.M)
_GLOSSARY_START = re.compile(r"^GLOSARIO\n", re.M)
_OTHER_SENSE = re.compile(r"motor\s+de\s+creación\s+de\s+valor")


def motor_outside_methodology(txt: str) -> list:
    """Frases con «motor» fuera de la metodología y el anexo (de METODOLOGÍA a GLOSARIO)."""
    start, end = _METHODOLOGY_START.search(txt), _GLOSSARY_START.search(txt)
    outside = txt[:start.start()] + txt[end.start():] if start and end else txt
    outside = _OTHER_SENSE.sub("", " ".join(outside.split()))
    return re.findall(r"[^.]{0,50}\bmotor\b[^.]{0,30}", outside)


def test_motor_rule_is_not_vacuous():
    """La regla ve «motor» en el cuerpo y en el glosario, y no en la metodología, el anexo ni con otro sentido."""
    doc = lambda body, method="x", glossary="x": f"{body}\nMETODOLOGÍA\n{method}\nANEXO\nx\nGLOSARIO\n{glossary}\n"
    assert motor_outside_methodology(doc("Lectura del motor"))
    assert motor_outside_methodology(doc("x", glossary="lo detecta el motor"))
    assert not motor_outside_methodology(doc("x", method="Bandas del motor"))
    assert not motor_outside_methodology(doc("el principal motor de\ncreación de valor. Toyota Motor Corporation"))
