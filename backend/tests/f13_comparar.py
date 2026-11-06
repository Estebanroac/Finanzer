"""
F13: compara dos corridas del banco de 110 empresas (tests/f13_banco110.py --run) y dice qué cambió, empresa a empresa.

    ../.venv313/bin/python tests/f13_comparar.py <antes> <despues> [--md salida.md]

Por empresa: veredicto, nivel y nota de precio, nivel de calidad, confianza, WACC y upside del DCF. Arriba, el reparto de
niveles de precio y de confianza antes y después, y los movimientos de banda (hacia «barata» o hacia «cara»). Los 11
«no se sostiene» de la revisión se señalan aparte: son los primeros tests de regresión.
"""
import argparse
import json
import os
from collections import Counter

PRICE = ["muy exigente", "exigente", "razonable", "atractivo", "muy atractivo"]
CONF = ["baja", "media", "alta"]
NOT_HOLD = ["ORCL", "META", "WBD", "EA", "GM", "KHC", "HON", "XEL", "WELL", "NEM", "APD"]


def load(d):
    r = json.load(open(os.path.join(d, "resumen.json"), encoding="utf-8"))
    rows = r if isinstance(r, list) else r.get("empresas", r)
    if isinstance(rows, dict):
        rows = [{"t": k, **v} for k, v in rows.items()]
    return {x["t"]: x for x in rows}


def _pct(x):
    return "—" if x is None else f"{x * 100:.1f} %"


def compare(a_dir, b_dir):
    A, B = load(a_dir), load(b_dir)
    lines, moves = [], Counter()
    for t in sorted(set(A) | set(B)):
        a, b = A.get(t) or {}, B.get(t) or {}
        diff = [k for k in ("veredicto", "nivel_precio", "nota_precio", "nivel_calidad", "confianza") if a.get(k) != b.get(k)]
        if not diff:
            continue
        pa, pb = a.get("nivel_precio"), b.get("nivel_precio")
        if pa in PRICE and pb in PRICE and pa != pb:
            moves["hacia barata" if PRICE.index(pb) > PRICE.index(pa) else "hacia cara"] += 1
        lines.append(f"| {t}{' ★' if t in NOT_HOLD else ''} | {a.get('veredicto')} ({a.get('confianza')}) | "
                     f"{b.get('veredicto')} ({b.get('confianza')}) | {a.get('nota_precio')} → {b.get('nota_precio')} | "
                     f"{_pct(a.get('wacc'))} → {_pct(b.get('wacc'))} |")
    dist = lambda X, k, order: " · ".join(f"{v}: {Counter(x.get(k) for x in X.values())[v]}" for v in order)
    head = [f"Antes: `{a_dir}` · después: `{b_dir}`", "",
            f"- Precio antes: {dist(A, 'nivel_precio', PRICE)}", f"- Precio después: {dist(B, 'nivel_precio', PRICE)}",
            f"- Confianza antes: {dist(A, 'confianza', CONF)}", f"- Confianza después: {dist(B, 'confianza', CONF)}",
            f"- Cambian: {len(lines)} empresas; bandas de precio: {dict(moves) or 'ninguna'}", "",
            "| Empresa | Antes | Después | Nota de precio | WACC |", "|---|---|---|---|---|"]
    return "\n".join(head + lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("antes")
    ap.add_argument("despues")
    ap.add_argument("--md")
    a = ap.parse_args()
    txt = compare(a.antes, a.despues)
    if a.md:
        open(a.md, "w", encoding="utf-8").write(txt)
    print(txt)


if __name__ == "__main__":
    main()
