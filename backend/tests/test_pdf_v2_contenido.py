"""
Rediseño E5 (Task 6): nada de lo que trae el informe actual se pierde en el nuevo.

Para los 8 tickers de verificación, cada token con cifra del texto del PDF actual (su golden,
tests/golden/panel/<T>.pdf.txt) está en el texto del PDF nuevo, salvo las excepciones justificadas de abajo. Se compara
la cifra (con su signo y su $): la unidad puede quedar en otra línea según la maquetación ("29.3\\npp").
"""
import re

import pytest

import fixture_backend as fb
import pdf_v2_samples as S

TICKERS = ["AAPL", "JPM", "O", "NEE", "XOM", "PLTR", "RIVN", "BCS"]
TOKEN = re.compile(r"[-−]?\$?\d[\d.,]*(?:%|x| pp|B|T|M)?")
EXCEPTIONS = {
    "01": "número de sección del informe actual (01 VALORACIÓN…): el nuevo numera sus capítulos del 1 al 9",
    "02": "número de sección del informe actual", "03": "número de sección del informe actual",
    "04": "número de sección del informe actual", "05": "número de sección del informe actual",
    "06": "número de sección del informe actual", "07": "número de sección del informe actual",
}


def _core(tok):
    t = tok.replace("−", "-").rstrip(".,")
    return re.sub(r"(%|x| pp|B|T|M)$", "", t)


def cores(text):
    return {_core(m.group(0)) for m in TOKEN.finditer(text.replace(" ", " "))}


@pytest.mark.parametrize("sym", TICKERS)
def test_every_figure_of_the_current_pdf_is_in_the_new_one(sym):
    with open(f"{S.TESTS_DIR}/golden/panel/{sym}.pdf.txt", encoding="utf-8") as fh:
        old = cores(fh.read())
    new = cores(fb.pdf_text(S.build(sym)))
    missing = sorted(t for t in old - new if t not in EXCEPTIONS)
    assert not missing, missing


def test_exceptions_are_justified():
    assert all(len(v) > 20 for v in EXCEPTIONS.values())
