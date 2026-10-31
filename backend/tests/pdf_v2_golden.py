"""
Rediseño E5: golden de texto del PDF nuevo (tests/golden/panel_pdf_v2/<T>.pdf.txt). No toca los golden existentes.

    cd backend && ../.venv313/bin/python tests/pdf_v2_golden.py              # diferencias (1 si hay)
    cd backend && ../.venv313/bin/python tests/pdf_v2_golden.py --regenerate # reescribe (decisión explícita)

El texto sale con la misma extracción que el golden del informe actual (fixture_backend.pdf_text: pypdf), del análisis
del golden del panel, las series grabadas y la fecha de captura (tests/pdf_v2_samples.build).
"""
import argparse
import difflib
import os
import sys

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
for _p in (TESTS_DIR, os.path.join(os.path.dirname(TESTS_DIR), "lib")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import fixture_backend as fb  # noqa: E402
import pdf_v2_samples as S  # noqa: E402

GOLDEN_DIR = os.path.join(TESTS_DIR, "golden", "panel_pdf_v2")


def path(sym):
    return os.path.join(GOLDEN_DIR, f"{sym}.pdf.txt")


def current(sym):
    return fb.pdf_text(S.build(sym))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("symbols", nargs="*")
    ap.add_argument("--regenerate", action="store_true")
    args = ap.parse_args(argv)
    syms = args.symbols or S.panel_symbols()
    os.makedirs(GOLDEN_DIR, exist_ok=True)
    changed = 0
    for sym in syms:
        txt = current(sym)
        if args.regenerate:
            with open(path(sym), "w", encoding="utf-8") as fh:
                fh.write(txt)
            continue
        old = open(path(sym), encoding="utf-8").read() if os.path.isfile(path(sym)) else ""
        if old != txt:
            changed += 1
            print(f"── {sym}")
            sys.stdout.writelines(list(difflib.unified_diff(old.splitlines(True), txt.splitlines(True), n=1))[:60])
    if not args.regenerate:
        print("sin diferencias" if not changed else f"{changed} con diferencias")
    return 1 if changed else 0


if __name__ == "__main__":
    sys.exit(main())
