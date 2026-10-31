"""
Rediseño E5: PDF de muestra del informe nuevo y capturas PNG de cada página, sin red.

    cd backend && ../.venv313/bin/python tests/pdf_v2_capturas.py AAPL JPM
    → docs/rediseno/capturas-e5/<T>-p<N>.png (pypdfium2, 2× = 144 ppp)

Usa el análisis del replay congelado en el golden del panel y las series de precios grabadas (tests/pdf_v2_samples.py);
la fecha del informe es fija para que las capturas sean comparables entre corridas.
"""
import argparse
import os
import sys
import time
from datetime import date

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
for _p in (TESTS_DIR, os.path.join(os.path.dirname(TESTS_DIR), "lib")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import pypdfium2 as pdfium  # noqa: E402

import pdf_v2_samples as S  # noqa: E402
from pdf_v2 import build_pdf  # noqa: E402

REPO = os.path.dirname(os.path.dirname(TESTS_DIR))
OUT = os.path.join(REPO, "docs", "rediseno", "capturas-e5")
TODAY = date(2026, 10, 17)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("symbols", nargs="+")
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--scale", type=float, default=2.0)
    args = ap.parse_args(argv)
    os.makedirs(args.out, exist_ok=True)
    for sym in args.symbols:
        t0 = time.perf_counter()
        pdf = build_pdf(S.analysis(sym), S.prices(sym), today=TODAY)
        dt = time.perf_counter() - t0
        doc = pdfium.PdfDocument(pdf)
        for i in range(len(doc)):
            doc[i].render(scale=args.scale).to_pil().save(os.path.join(args.out, f"{sym}-p{i + 1}.png"), optimize=True)
        print(f"{sym}: {len(doc)} páginas, {len(pdf) / 1024:.0f} KB, {dt:.2f} s")


if __name__ == "__main__":
    main()
