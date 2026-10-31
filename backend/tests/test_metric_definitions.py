"""
Rediseño E5: las definiciones de las métricas del PDF nuevo (backend/assets/metric_definitions.json) son las de la web
(frontend/src/lib/tooltips.ts), generadas por backend/tools/gen_metric_definitions.py.
"""
import os
import re
import sys

import pytest

TOOLS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools")
sys.path.insert(0, TOOLS)
import gen_metric_definitions as gen  # noqa: E402

from pdf_v2 import definitions as D  # noqa: E402


def test_json_is_in_sync_with_the_frontend():
    with open(gen.OUT, encoding="utf-8") as fh:
        assert fh.read() == gen.render(), "ejecuta python3 backend/tools/gen_metric_definitions.py"


def test_every_key_of_the_ts_is_read():
    src = open(gen.TS, encoding="utf-8").read()
    body = src[src.index("export const DEFINITIONS"):src.index("export function definitionFor")]
    keys = re.findall(r"^  ([A-Za-z_][A-Za-z0-9_]*): \{", body, flags=re.M)
    assert keys and list(D.definitions()) == keys


def test_parser_reads_concatenation_escapes_and_comments():
    ts = '''export const DEFINITIONS: Record<string, Definition> = {
      // comentario
      roe: { title: "ROE", description: "Uno " + "dos \\"tres\\"", tip: "x" },
      "p/e": { title: "P/E", description: "d", },
    };'''
    out = gen.parse(ts)
    assert out == {"roe": {"title": "ROE", "description": 'Uno dos "tres"', "tip": "x"},
                   "p/e": {"title": "P/E", "description": "d"}}


@pytest.mark.parametrize("bad", [
    'export const DEFINITIONS: Record<string, Definition> = { a: { title: `x`, description: "d" } };',
    'export const DEFINITIONS: Record<string, Definition> = { a: { title: X, description: "d" } };',
    'export const DEFINITIONS: Record<string, Definition> = { a: { title: "x" } };',
    'export const DEFINITIONS: Record<string, Definition> = { a: { title: "x", description: "d", foo: "z" } };',
])
def test_parser_rejects_what_it_does_not_understand(bad):
    with pytest.raises(gen.ParseError):
        gen.parse(bad)


def test_meaning_is_the_first_sentence():
    assert D.meaning("roe") == "Cuánto beneficio genera la empresa por cada dólar de los accionistas."
    assert D.meaning("no_existe") is None
