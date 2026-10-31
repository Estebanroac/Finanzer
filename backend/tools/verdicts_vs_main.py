"""
Pasada final de la v4 (PM): los veredictos de los 43 golden (37 del panel y 6 locales) frente a `main`, en 11 campos.

    cd backend && ../.venv313/bin/python tools/verdicts_vs_main.py [--ref main] [--out ../docs/rediseno/verificacion/x.md]

Los 11 campos son las cifras y niveles del veredicto, no su redacción: calidad (puntuación y nivel), atractivo del precio
(puntuación, puntuación sin contraer, nivel y confianza), veredicto (texto «Calidad X · precio Y» y sus tres niveles) y
el nivel de la confianza. Lee los golden de `--ref` con `git show` (sin tocar el árbol) y los de la rama del disco.
Código de salida 1 si algún campo cambia.
"""
import argparse
import json
import os
import subprocess
import sys

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(BACKEND)
GOLDEN = os.path.join("backend", "tests", "golden")
FIELDS = [
    ("quality", "score"), ("quality", "level"),
    ("price_attractiveness", "score"), ("price_attractiveness", "score_raw"),
    ("price_attractiveness", "level"), ("price_attractiveness", "confidence"),
    ("verdict", "text"), ("verdict", "quality_level"), ("verdict", "price_level"), ("verdict", "confidence"),
    ("confidence", "level"),
]


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, check=True).stdout


def _fields(a: dict) -> dict:
    return {f"{blk}.{key}": (a.get(blk) or {}).get(key) for blk, key in FIELDS}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", default="main")
    ap.add_argument("--out")
    args = ap.parse_args()
    rows, changed = [], []
    for env in ("panel", "local"):
        names = [n for n in _git("ls-tree", "--name-only", args.ref, f"{GOLDEN}/{env}/").split() if n.endswith(".json")]
        for path in sorted(names):
            sym = os.path.basename(path)[:-5]
            old = _fields(json.loads(_git("show", f"{args.ref}:{path}")))
            here = os.path.join(REPO, path)
            new = _fields(json.load(open(here, encoding="utf-8"))) if os.path.isfile(here) else None
            diff = ["(falta en la rama)"] if new is None else [f"{k}: {old[k]!r} → {new[k]!r}" for k in old if old[k] != new[k]]
            rows.append((env, sym, old["verdict.text"], diff))
            if diff:
                changed.append((env, sym, diff))
    head = _git("rev-parse", "--short", "HEAD").strip()
    ref = _git("rev-parse", "--short", args.ref).strip()
    lines = [f"# Veredictos de los golden frente a `{args.ref}` ({ref}) en la rama ({head})", "",
             f"{len(rows)} golden ({sum(r[0] == 'panel' for r in rows)} del panel y "
             f"{sum(r[0] == 'local' for r in rows)} locales) × {len(FIELDS)} campos: "
             + ", ".join(f"`{b}.{k}`" for b, k in FIELDS) + ".", "",
             f"**Cambios: {len(changed)}.**", "", "| juego | ticker | veredicto | cambios |", "|---|---|---|---|"]
    lines += [f"| {e} | {s} | {v or '—'} | {'; '.join(d) if d else '0'} |" for e, s, v, d in rows]
    text = "\n".join(lines) + "\n"
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text)
    print(f"{len(rows)} golden × {len(FIELDS)} campos frente a {args.ref}: {len(changed)} con cambios")
    for e, s, d in changed:
        print(f"  {e}/{s}: {'; '.join(d)}")
    return 1 if changed else 0


if __name__ == "__main__":
    sys.exit(main())
