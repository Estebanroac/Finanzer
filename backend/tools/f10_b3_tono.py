"""
F10 · B3 (escaneo del modelo general, `alertas_coherentes`): alertas con el tono contrario a su fila. Una fortaleza
cuya fila del display tiene tono negativo, o una alerta (aviso o riesgo) cuya fila tiene tono positivo. La misma regla
que backend/lib/invariants.py de la rama modelo/general-inventario (06b7d51a), sobre los golden o la evidencia.

    cd backend && ../../finanzer_next/.venv313/bin/python tools/f10_b3_tono.py [--env panel|local] [--tag f10_n2b]
"""
import argparse
import glob
import gzip
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
OTHER_BASIS = ["normalizad", "sin el pico", "ciclo medio", "creíble"]
LABELS = [(r"\bforward p/e\b", "forward_pe"), (r"\bp/e\b", "pe"), (r"\bev/ebitda\b", "ev_ebitda"),
          (r"\bp/fcf\b", "pfcf"), (r"\bpeg\b", "peg"), (r"\bp/b\b", "pb"), (r"fcf yield", "fcf_yield"),
          (r"\broe\b", "roe"), (r"\broa\b", "roa"), (r"margen neto", "net_margin"),
          (r"margen operativo", "operating_margin"), (r"margen bruto", "gross_margin"), (r"\bbeta\b", "beta"),
          (r"piotroski", "piotroski"), (r"altman", "altman"), (r"deuda neta/ebitda", "net_debt_to_ebitda"),
          (r"cobertura", "interest_coverage"), (r"liquidez", "current_ratio")]


def alert_key(text):
    t = text.lower()
    if any(m in t for m in OTHER_BASIS):
        return None
    return next((k for p, k in LABELS if re.search(p, t)), None)


def rows(a):
    secs = ((a.get("display") or {}).get("sections") or {})
    return [r for s in secs.values() if isinstance(s, dict) for r in (s.get("rows") or []) if isinstance(r, dict)]


def contradictions(a):
    out = []
    al = a.get("alerts") or {}
    for kind in ("strengths", "warnings", "red_flags"):
        for x in al.get(kind) or []:
            reason = str(x.get("reason") or "")
            label, _, tail = reason.partition(" — ")
            key = alert_key(label) or alert_key(tail)
            r = next((r for r in rows(a) if r.get("key") == key), None) if key else None
            if r and r.get("state") == "con_dato":
                if (kind == "strengths" and r.get("tone") == "neg") or (kind != "strengths" and r.get("tone") == "pos"):
                    out.append((kind, reason, key, r.get("reading"), r.get("bench")))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--env", default="panel")
    ap.add_argument("--tag")
    a = ap.parse_args()
    if a.tag:
        files = sorted(glob.glob(os.path.join(HERE, "..", "..", "docs", "fiabilidad", "f8_evidencia", a.tag, "*.gz")))
        load = lambda f: (lambda d: d.get("analysis", d))(json.load(gzip.open(f)))  # noqa: E731
    else:
        files = sorted(glob.glob(os.path.join(HERE, "..", "tests", "golden", a.env, "*.json")))
        load = lambda f: json.load(open(f, encoding="utf-8"))  # noqa: E731
    n = 0
    for f in files:
        sym = os.path.basename(f).split(".json")[0]
        for kind, reason, key, reading, bench in contradictions(load(f)):
            n += 1
            print(f"{sym:6} {kind:10} «{reason}» · fila {key}: {reading} (ref. {bench})")
    print(f"{n} contradicciones en {len(files)} empresas")


if __name__ == "__main__":
    main()
