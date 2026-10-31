"""
V4b · 4 (PM): la prueba general de la presentación de las ausencias. Sobre un recuento de
frontend/scripts/auditoria-faltantes.mjs (el panel en el replay con el build), clasifica cada marca con las reglas de
tools/auditoria_faltantes.py y cuenta las de presentación: el motor tiene el motivo y la página no lo pinta en su sitio.
La web cumple cuando no queda ninguna.

    cd backend && ../.venv313/bin/python tools/auditoria_presentacion.py <recuento.json[.gz]> [--ejemplos N]

Sale con 1 si queda alguna (y la lista por regla y página, con ejemplos).
"""
import argparse
import collections
import gzip
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from auditoria_faltantes import classify  # noqa: E402


def _load(path):
    op = gzip.open if path.endswith(".gz") else open
    with op(path, "rt", encoding="utf-8") as f:
        return json.load(f)


def presentation_marks(data):
    """[(ticker, página, regla, marca)] de las marcas de presentación (y los errores de carga, como marcas)."""
    out = []
    for t, pages in data.items():
        for page, marks in pages.items():
            if not isinstance(marks, list):
                out.append((t, page, "la página no cargó", {"text": str(marks)}))
                continue
            for m in marks:
                cls, rule, pres, _why = classify(t, page, m)
                if pres:
                    out.append((t, page, f"{cls} · {rule}", m))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("recuento")
    ap.add_argument("--ejemplos", type=int, default=3)
    a = ap.parse_args(argv)
    marks = presentation_marks(_load(a.recuento))
    by = collections.defaultdict(list)
    for t, page, rule, m in marks:
        by[(page, rule)].append((t, m))
    for (page, rule), xs in sorted(by.items(), key=lambda kv: -len(kv[1])):
        ex = "; ".join(f"{t}: {m.get('sec', '')[:40]} · {m.get('row', '')[:30]} · {m.get('col', '')} «{(m.get('text') or m.get('kind') or '')[:50]}»"
                       for t, m in xs[:a.ejemplos])
        print(f"{len(xs):5d}  {page:11s} {rule}\n       {ex}")
    print(f"marcas de presentación: {len(marks)}")
    return 1 if marks else 0


if __name__ == "__main__":
    sys.exit(main())
