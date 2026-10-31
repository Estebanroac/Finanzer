"""
F8: compara dos volcados de análisis (tools/f8_replay_dump.py o tools/f8_evidencia.py) campo a campo:

    ../../finanzer_next/.venv313/bin/python tools/f8_compare.py <antes> <después> VZ GOOGL -- campo.a campo.b
"""
import gzip
import json
import os
import sys


def load(d, s):
    with gzip.open(os.path.join(d, f"{s}.json.gz"), "rt", encoding="utf-8") as fh:
        return json.load(fh)


def get(o, dotted):
    for k in dotted.split("."):
        if isinstance(o, list):
            try:
                o = o[int(k)]
            except (ValueError, IndexError):
                return None
        elif isinstance(o, dict):
            o = o.get(k)
        else:
            return None
    return o


def main(argv):
    i = argv.index("--")
    before, after, syms, fields = argv[0], argv[1], argv[2:i], argv[i + 1:]
    for s in syms:
        a, b = load(before, s), load(after, s)
        print(f"== {s}")
        for f in fields:
            va, vb = get(a, f), get(b, f)
            mark = "  " if va == vb else "≠ "
            print(f"{mark}{f}: {json.dumps(va, ensure_ascii=False)[:300]}  →  {json.dumps(vb, ensure_ascii=False)[:300]}")


if __name__ == "__main__":
    main(sys.argv[1:])
