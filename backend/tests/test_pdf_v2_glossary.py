"""
V7 · P3: glosario de una página al final del informe nuevo, con la jerga que usa (las definiciones de la web,
backend/assets/metric_definitions.json, generadas desde frontend/src/lib/tooltips.ts).
"""
import pytest

import pdf_inspect as pi
import pdf_v2_samples as S
from pdf_v2 import methodology as M
from pdf_v2.definitions import definition, first_sentence
from settings import cfg


def test_every_glossary_key_has_a_definition():
    keys = cfg("pdf.glossary")["keys"]
    assert len(keys) == len(set(keys))
    missing = [k for k in keys if not (definition(k) or {}).get("description")]
    assert missing == []
    assert [t for t, _ in M.glossary_terms()] == [definition(k)["title"] for k in keys]


def test_the_terms_the_new_reader_did_not_understand_are_there():
    """La lectura V7 citó FCF − SBC, ROTE, PEAD, Momentum 12-1 y XLK sin definir."""
    titles = " · ".join(t for t, _ in M.glossary_terms())
    for term in ("FCF − SBC", "ROTE", "PEAD", "Momentum 12-1", "ETF del sector"):
        assert term in titles
    assert "XLK" in dict(M.glossary_terms())["ETF del sector"]


@pytest.mark.parametrize("sym", S.panel_symbols())
def test_glossary_is_the_last_page_and_fits_in_one(sym):
    pages = [" ".join(p.split()) for p in pi.page_texts(S.build(sym))]
    start = [i for i, p in enumerate(pages) if "GLOSARIO Qué quiere decir cada término" in p]
    assert start == [len(pages) - 1], f"{sym}: el glosario empieza en {start} de {len(pages)} páginas"
    last = pages[-1]
    for title, sentence in M.glossary_terms():
        assert " ".join(f"{title}. {first_sentence(sentence)}".split()) in last
    # y el índice lo enlaza
    assert f"Glosario {len(pages)}" in pages[1]
