"""
F8 · E10 (peso de Altman): distribución de Solidez Financiera en los 69 casos de la calibración (las 26 de la auditoría
en vivo, de dos corridas guardadas por f8_evidencia, y los 43 golden de panel y local frente a un ref de git), por los
tonos de una categoría (thresholds.pdf.category_tone_bounds) y el techo de 20, con la zona de Altman. Sin red.

    python tools/f8_solidez_bands.py <tag_antes> <tag_despues> <ref_antes>
"""
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib"))
from settings import cfg  # noqa: E402
from tools.f8_quality_bands import golden_docs, live_docs  # noqa: E402

CAT = "Solidez Financiera"
ORDER = ["20 (techo)", "positivo", "aviso", "negativo", "sin dato"]


def solidez(a):
    """(puntos, zona de Altman) de un análisis."""
    bd = ((a.get("score") or {}).get("breakdown") or {}).get(CAT) or {}
    zone = next((x.get("reason", "").split(" - ")[0] for x in bd.get("adjustments") or []
                 if x.get("metric") == "Altman Z-Score"), "sin Altman")
    pts = next((c.get("score") for c in (a.get("quality") or {}).get("components") or [] if c["category"] == CAT), None)
    return pts, zone


def tone(pts):
    if pts is None:
        return "sin dato"
    if pts >= cfg("thresholds.score.category.max"):
        return "20 (techo)"
    hi, lo = cfg("thresholds.pdf.category_tone_bounds")
    pct = 100 * pts / cfg("thresholds.score.category.max")
    return "positivo" if pct >= hi else "aviso" if pct >= lo else "negativo"


def main(tag_a, tag_b, ref):
    before = {k: solidez(a) for k, a in {**live_docs(tag_a), **golden_docs(ref)}.items()}
    after = {k: solidez(a) for k, a in {**live_docs(tag_b), **golden_docs()}.items()}
    for name, sc in (("antes [6, -2, -6]", before), ("después [3, -1, -3]", after)):
        c = Counter(tone(p) for p, _ in sc.values())
        print(f"{name}: n={len(sc)} · " + " · ".join(f"{k} {c[k]}" for k in ORDER if c[k]))
    print("zonas de Altman:", dict(Counter(z for _, z in after.values())))
    moved = sorted((k for k in after if before.get(k) and before[k][0] != after[k][0]),
                   key=lambda k: (after[k][1], k))
    for k in moved:
        (pa, _), (pb, z) = before[k], after[k]
        print(f"  {k}: {pa} → {pb} ({z}{'; cambia de tono' if tone(pa) != tone(pb) else ''})")


if __name__ == "__main__":
    main(*sys.argv[1:4])
