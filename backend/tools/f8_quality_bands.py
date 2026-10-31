"""
F8 · E11: distribución de los niveles de calidad en los 69 casos de la calibración (las 26 de la auditoría en vivo, de
dos corridas guardadas por f8_evidencia, y los 43 golden de panel y local frente a un ref de git), con distintos
umbrales de «excelente». Sin red.

    python tools/f8_quality_bands.py <tag_antes> <tag_despues> <ref_antes>
"""
import gzip
import json
import os
import subprocess
import sys
from collections import Counter
from glob import glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EV = os.path.join(ROOT, "..", "docs", "fiabilidad", "f8_evidencia")
ORDER = ["excelente", "sólida", "media", "débil"]


def level(s, top):
    return None if s is None else ORDER[0] if s >= top else ORDER[1] if s >= 65 else ORDER[2] if s >= 45 else ORDER[3]


def live_docs(tag):
    """Los análisis guardados de una corrida de f8_evidencia, por «vivo/TICKER»."""
    out = {}
    for p in glob(os.path.join(EV, tag, "*.json.gz")):
        d = json.load(gzip.open(p))
        out["vivo/" + os.path.basename(p)[:-8]] = d.get("analysis", d)
    return out


def golden_docs(ref=None):
    """Los golden de panel y local, por «juego/TICKER»: los del disco o los de un ref de git."""
    out = {}
    for env in ("panel", "local"):
        for p in glob(os.path.join(ROOT, "tests", "golden", env, "*.json")):
            if ref:
                rel = os.path.relpath(p, os.path.join(ROOT, ".."))
                try:
                    d = json.loads(subprocess.check_output(["git", "-C", ROOT, "show", f"{ref}:{rel}"],
                                                           stderr=subprocess.DEVNULL))
                except subprocess.CalledProcessError:
                    continue
            else:
                d = json.load(open(p))
            out[f"{env}/{os.path.basename(p)[:-5]}"] = d
    return out


def live(tag):
    return {k: (a.get("quality") or {}).get("score") for k, a in live_docs(tag).items()}


def golden(ref=None):
    return {k: (a.get("quality") or {}).get("score") for k, a in golden_docs(ref).items()}


def main(tag_a, tag_b, ref):
    before = {**live(tag_a), **golden(ref)}
    after = {**live(tag_b), **golden()}
    for name, sc, top in (("antes (umbral 80)", before, 80), ("E11 con umbral 80", after, 80),
                          ("E11 con umbral 85", after, 85)):
        vals = [v for v in sc.values() if v is not None]
        c = Counter(level(v, top) for v in vals)
        print(f"{name}: n={len(vals)} · " + " · ".join(f"{k} {c[k]} ({c[k] / len(vals):.0%})" for k in ORDER))
    # Quién deja «excelente» (antes ≥ 80, ahora < 85) y por qué: la contracción basta (< 80), la contracción y el umbral
    # (contraída a 80–84) o solo el umbral (misma puntuación).
    gone = sorted((k for k in before if (before[k] or 0) >= 80 and (after.get(k) or 0) < 85), key=lambda k: -before[k])
    for why, keys in (("por la contracción sola", [k for k in gone if after[k] < 80]),
                      ("por la contracción y el umbral", [k for k in gone if 80 <= after[k] < before[k]]),
                      ("solo por el umbral 85", [k for k in gone if after[k] == before[k]])):
        print(f"dejan «excelente» {why} ({len(keys)}): " + ", ".join(f"{k} {before[k]}→{after[k]}" for k in keys))
    vals = sorted(v for v in after.values() if v is not None)
    q = lambda f: vals[min(len(vals) - 1, int(f * len(vals)))]
    print(f"E11, cuantiles de la calidad: p50 {q(0.5)} · p75 {q(0.75)} · p90 {q(0.9)} · máx {vals[-1]}")


if __name__ == "__main__":
    main(*sys.argv[1:4])
