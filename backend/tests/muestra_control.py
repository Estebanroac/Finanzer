"""
F15 (expectativas golden): la muestra de control contra el sobreajuste. 300 empresas del universo (config/universe.tsv)
que NO están entre las 110 de tests/expectativas/golden_110.yaml, al azar con semilla fija y estratificadas por sector
GICS (reparto proporcional, restos al mayor decimal). Nadie las revisa ni se usan para ajustar el motor: al cerrar cada
versión se mide en ellas el número de incumplimientos de las reglas globales y el reparto de etiquetas de precio y de
confianza. Si una mejora aparece en las 110 y no en el control, es sobreajuste.

    cd finanzer_next/backend
    ../.venv313/bin/python tests/muestra_control.py --elegir            # escribe tests/expectativas/muestra_control.txt
    ../.venv313/bin/python tests/muestra_control.py --medir <carpeta>   # <carpeta>/<T>.json(.gz): análisis descargados

Medir no ajusta nada: compara con las 110 (la condición 4 de «terminado»: la proporción de «muy exigente» y de
confianza baja del control no se aleja más de 10 pp de la de las 110).
"""
import argparse
import collections
import csv
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import expectativas as X  # noqa: E402

UNIVERSE = os.path.join(HERE, "..", "config", "universe.tsv")
LISTA = os.path.join(HERE, "expectativas", "muestra_control.txt")
SEED, N = 20261106, 300


def choose(seed: int = SEED, n: int = N):
    golden = {e["ticker"] for e in X.load_yaml()["empresas"]}
    with open(UNIVERSE, encoding="utf-8") as fh:
        rows = [r for r in csv.DictReader((ln for ln in fh if not ln.startswith("#")), delimiter="\t")
                if r["symbol"] not in golden]
    by = collections.defaultdict(list)
    for r in rows:
        by[r["gics_sector"] or "—"].append(r["symbol"])
    total = sum(len(v) for v in by.values())
    quota = {s: n * len(v) / total for s, v in by.items()}
    take = {s: int(q) for s, q in quota.items()}
    for s in sorted(quota, key=lambda s: quota[s] - take[s], reverse=True)[:n - sum(take.values())]:
        take[s] += 1
    rnd = random.Random(seed)
    out = []
    for s in sorted(by):
        out += sorted(rnd.sample(sorted(by[s]), take[s]))
    return sorted(out)


def distribution(banco: str, tickers):
    price, conf, rules, n = collections.Counter(), collections.Counter(), [], 0
    for t in tickers:
        a = X._load(banco, t)
        if a is None or "__http_error__" in a:
            continue
        n += 1
        price[X.price_label(a)] += 1
        conf[(a.get("verdict") or {}).get("confidence")] += 1
        rules += [f"{t}: {r}" for r in X.global_rules(t, a)]
    return {"n": n, "price": price, "conf": conf, "rules": rules}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--elegir", action="store_true")
    ap.add_argument("--medir")
    ap.add_argument("--banco110", help="carpeta con las 110 para comparar los repartos")
    a = ap.parse_args()
    if a.elegir:
        with open(LISTA, "w", encoding="utf-8") as fh:
            fh.write(f"# muestra de control: semilla {SEED}, {N} empresas, estratificada por sector GICS "
                     "(tests/muestra_control.py)\n" + "\n".join(choose()) + "\n")
        print(f"escrita {os.path.relpath(LISTA, HERE)}")
    if a.medir:
        with open(LISTA, encoding="utf-8") as fh:
            ts = [ln.strip() for ln in fh if ln.strip() and not ln.startswith("#")]
        d = distribution(a.medir, ts)
        sh = lambda c, k: c[k] / max(1, sum(c.values()))
        print(f"Control: {d['n']} analizadas · muy exigente {sh(d['price'], 'muy exigente'):.0%} · "
              f"confianza baja {sh(d['conf'], 'baja'):.0%}")
        print("  precio:", dict(d["price"].most_common()))
        print("  confianza:", dict(d["conf"].most_common()))
        print(f"  reglas globales: {len(d['rules'])}", *d["rules"][:30], sep="\n    ")
        if a.banco110:
            g = distribution(a.banco110, [e["ticker"] for e in X.load_yaml()["empresas"]])
            for lab, k, c1, c2 in (("muy exigente", "muy exigente", d["price"], g["price"]),
                                   ("confianza baja", "baja", d["conf"], g["conf"])):
                gap = sh(c1, k) - sh(c2, k)
                print(f"  {lab}: control {sh(c1, k):.0%} frente a las 110 {sh(c2, k):.0%} "
                      f"({gap * 100:+.0f} pp; {'dentro' if abs(gap) <= 0.10 else 'FUERA'} de ±10 pp)")


if __name__ == "__main__":
    main()
