"""
Detector de fugas: busca fechas posteriores al corte (2025-11-05) dentro de cada análisis y las agrupa por la ruta
JSON donde aparecen. Una fecha futura legítima (próximos resultados estimados, vencimientos de deuda, fecha de
revisión de un parámetro) se lista igual: se revisa a mano, no se filtra.

    python -I tests/hacia_atras/fugas.py <carpeta de la corrida>
"""
import collections
import gzip
import json
import os
import re
import sys

CUT = os.environ.get("HACIA_ATRAS_CORTE") or "2025-11-05"
DATE = re.compile(r"^(20\d\d-\d\d-\d\d)")
YEAR_TXT = re.compile(r"\b(20(?:2[6-9]|3\d))\b")


def walk(o, path, out):
    if isinstance(o, dict):
        for k, v in o.items():
            walk(v, f"{path}.{k}", out)
    elif isinstance(o, list):
        for v in o:
            walk(v, path + "[]", out)
    elif isinstance(o, str):
        m = DATE.match(o)
        if m and m.group(1) > CUT:
            out[path].append(o[:10])
        elif not m:
            for y in YEAR_TXT.findall(o):
                out[path + " (texto)"].append(y)


def main():
    d = sys.argv[1]
    agg, ejemplos = collections.Counter(), {}
    for f in sorted(os.listdir(d)):
        if not f.endswith(".json.gz"):
            continue
        out = collections.defaultdict(list)
        walk(json.load(gzip.open(os.path.join(d, f))), "", out)
        for p, vs in out.items():
            agg[p] += 1
            ejemplos.setdefault(p, (f[:-8], sorted(set(vs))[:3]))
    for p, n in agg.most_common():
        print(f"{n:4d}  {p}  ej. {ejemplos[p]}")


if __name__ == "__main__":
    main()
