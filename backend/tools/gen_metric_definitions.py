"""
Genera backend/assets/metric_definitions.json desde frontend/src/lib/tooltips.ts (rediseño E5).

Es `gen_frontend_config.py` a la inversa: las definiciones de las métricas (qué es, fórmula, cómo leerla) se escriben
una vez, en el frontend, y el PDF nuevo (lib/pdf_v2) las lee de este JSON sin depender de Node ni del frontend en
tiempo de ejecución.

    python3 backend/tools/gen_metric_definitions.py          # escribe el JSON
    python3 backend/tools/gen_metric_definitions.py --check  # 1 si está desincronizado

El lector entiende solo el subconjunto que usa `DEFINITIONS`: claves identificador, objetos de propiedades y cadenas
entre comillas dobles (con escapes JSON) unidas con `+`; comentarios `//` y `/* */`. Cualquier otra cosa (plantillas,
variables, expresiones) es un error explícito, no un dato perdido. tests/test_metric_definitions.py falla si el JSON no
coincide con el .ts o si el lector deja de entenderlo.
"""
import json
import os
import re
import sys

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TS = os.path.normpath(os.path.join(BACKEND, "..", "frontend", "src", "lib", "tooltips.ts"))
OUT = os.path.join(BACKEND, "assets", "metric_definitions.json")
FIELDS = ("title", "description", "formula", "good", "bad", "tip")


class ParseError(ValueError):
    pass


_TOKEN = re.compile(r'''
    (?P<ws>\s+)
  | (?P<lcomment>//[^\n]*)
  | (?P<bcomment>/\*.*?\*/)
  | (?P<string>"(?:[^"\\\n]|\\.)*")
  | (?P<ident>[A-Za-z_$][A-Za-z0-9_$]*)
  | (?P<punct>[{}:,+])
''', re.S | re.X)


def _tokens(src: str):
    i = 0
    while i < len(src):
        m = _TOKEN.match(src, i)
        if not m:
            raise ParseError(f"carácter inesperado {src[i]!r} en la posición {i}: {src[i:i + 40]!r}")
        i = m.end()
        kind = m.lastgroup
        if kind in ("ws", "lcomment", "bcomment"):
            continue
        yield kind, m.group(0)


def parse(ts_source: str) -> dict:
    """{clave: {campo: texto}} del objeto `export const DEFINITIONS … = { … };`."""
    m = re.search(r"export const DEFINITIONS\s*:\s*Record<string,\s*Definition>\s*=\s*\{", ts_source)
    if not m:
        raise ParseError("no encuentro `export const DEFINITIONS: Record<string, Definition> = {`")
    toks, depth = [], 1
    for tok in _tokens(ts_source[m.end():]):   # hasta la llave que cierra DEFINITIONS
        depth += {"{": 1, "}": -1}.get(tok[1], 0) if tok[0] == "punct" else 0
        toks.append(tok)
        if depth == 0:
            break
    else:
        raise ParseError("DEFINITIONS no se cierra")
    pos = 0

    def take(kind=None, value=None):
        nonlocal pos
        if pos >= len(toks):
            raise ParseError("fin inesperado del objeto")
        k, v = toks[pos]
        if (kind and k != kind) or (value and v != value):
            raise ParseError(f"se esperaba {value or kind}, hay {v!r} (token {pos})")
        pos += 1
        return v

    def peek():
        return toks[pos] if pos < len(toks) else (None, None)

    out = {}
    while True:
        k, v = peek()
        if (k, v) == ("punct", "}"):
            break
        key = take("ident") if k == "ident" else json.loads(take("string"))
        take("punct", ":")
        take("punct", "{")
        entry = {}
        while peek() != ("punct", "}"):
            field = take("ident")
            if field not in FIELDS:
                raise ParseError(f"{key}: campo desconocido {field!r}")
            take("punct", ":")
            parts = [json.loads(take("string"))]
            while peek() == ("punct", "+"):
                take("punct", "+")
                parts.append(json.loads(take("string")))
            entry[field] = "".join(parts)
            if peek() == ("punct", ","):
                take("punct", ",")
        take("punct", "}")
        if "title" not in entry or "description" not in entry:
            raise ParseError(f"{key}: falta title o description")
        if key in out:
            raise ParseError(f"clave repetida {key!r}")
        out[key] = entry
        if peek() == ("punct", ","):
            take("punct", ",")
    return out


def render() -> str:
    with open(TS, encoding="utf-8") as fh:
        defs = parse(fh.read())
    payload = {"_generado": "backend/tools/gen_metric_definitions.py desde frontend/src/lib/tooltips.ts; no editar",
               "definitions": defs}
    return json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=False) + "\n"


def main(argv):
    text = render()
    if "--check" in argv:
        try:
            with open(OUT, encoding="utf-8") as fh:
                same = fh.read() == text
        except FileNotFoundError:
            same = False
        print("sincronizado" if same else f"DESINCRONIZADO: ejecuta python3 {os.path.relpath(__file__)}")
        return 0 if same else 1
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(text)
    print(f"escrito {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
