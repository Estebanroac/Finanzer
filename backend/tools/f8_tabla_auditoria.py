"""
F8 (fusión): la tabla de las 26 empresas de la auditoría, el informe original frente al motor corregido. Lee dos
corridas guardadas por f8_evidencia (la de antes de las correcciones y la del código fusionado) y escribe una tabla
Markdown con calidad, precio y confianza de cada una, junto al estado que le dio la auditoría (§4). Sin red.

    python tools/f8_tabla_auditoria.py <tag_original> <tag_corregido>
"""
import gzip
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EV = os.path.join(ROOT, "..", "docs", "fiabilidad", "f8_evidencia")
# Auditoría §4, «Estado de cada informe».
STATE = {**{s: "no utilizable" for s in ("VZ", "AWK", "NEE", "PLD", "UNH", "XOM", "CB")},
         **{s: "utilizable con múltiplos y DCF inverso" for s in ("MSFT", "GOOGL", "AMZN", "LIN", "UNP", "WMT", "CAT",
                                                                  "FCX", "ASML", "KMI", "O")},
         **{s: "razonablemente sólido" for s in ("NVDA", "LLY", "JPM", "MCD", "KO", "SAP")},
         **{s: "sin precio, correctamente" for s in ("MRNA", "BA")}}
ORDER = ["VZ", "AWK", "NEE", "PLD", "UNH", "XOM", "CB", "MSFT", "GOOGL", "AMZN", "LIN", "UNP", "WMT", "CAT", "FCX",
         "ASML", "KMI", "O", "NVDA", "LLY", "JPM", "MCD", "KO", "SAP", "MRNA", "BA"]


def load(tag, sym):
    d = json.load(gzip.open(os.path.join(EV, tag, f"{sym}.json.gz")))
    return d.get("analysis", d)


def cell(a):
    q, p, c = a.get("quality") or {}, a.get("price_attractiveness") or {}, a.get("confidence") or {}
    qs = f"{q.get('score')} {q.get('level')}" if q.get("score") is not None else "—"
    ps = f"{p.get('score')} {p.get('level')}" if p.get("score") is not None else "sin dato"
    return qs, ps, c.get("level") or "—"


def main(tag_a, tag_b):
    print("| Empresa | Estado en la auditoría | Calidad (original → corregido) | Precio (original → corregido) "
          "| Confianza (original → corregido) |")
    print("|---|---|---|---|---|")
    for s in ORDER:
        (qa, pa, ca), (qb, pb, cb) = cell(load(tag_a, s)), cell(load(tag_b, s))
        f = lambda x, y: x if x == y else f"{x} → **{y}**"
        print(f"| {s} | {STATE[s]} | {f(qa, qb)} | {f(pa, pb)} | {f(ca, cb)} |")


if __name__ == "__main__":
    main(*sys.argv[1:3])
