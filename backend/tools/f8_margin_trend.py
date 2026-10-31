"""
F8 · E8 (criterio 5, PM 27-oct): calibración del deterioro de margen con crecimiento proyectado. Para las 26 de la
auditoría (una corrida en vivo de docs/fiabilidad/f8_evidencia/<tag>) y los 43 golden: margen operativo (o neto) TTM
frente a la mediana de los 5 últimos ejercicios de EDGAR, caída relativa, cambios anuales a la baja de los 4 últimos y
g del DCF.

    ../../finanzer_next/.venv313/bin/python tools/f8_margin_trend.py e9
"""
import glob
import gzip
import json
import os
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(HERE)
EVID = os.path.join(BACKEND, "..", "docs", "fiabilidad", "f8_evidencia")


def rows(tag):
    for p in sorted(glob.glob(os.path.join(EVID, tag, "*.json.gz"))):
        with gzip.open(p, "rt", encoding="utf-8") as fh:
            yield "vivo:" + os.path.basename(p)[:-8], json.load(fh)
    for env in ("panel", "local"):
        for p in sorted(glob.glob(os.path.join(BACKEND, "tests", "golden", env, "*.json"))):
            with open(p, encoding="utf-8") as fh:
                yield f"{env}:" + os.path.basename(p)[:-5], json.load(fh)


def measure(a):
    h = ((a.get("history_10y") or {}).get("rows") or [])[-5:]
    km = a.get("key_metrics") or {}
    for key, kmk in (("operating_margin", "operating_margin"), ("net_margin", "net_margin")):
        m = [r.get(key) for r in h]
        if len(m) == 5 and all(x is not None for x in m) and km.get(kmk) is not None:
            med = st.median(m)
            cur = km[kmk]
            drop = (med - cur) / abs(med) if med > 0 else None
            downs = sum(1 for x, y in zip(m[-5:], m[-4:]) if y < x)
            return key, med, cur, drop, downs, m
    return None


def main(tag):
    for n, a in rows(tag):
        r = measure(a)
        g = (a.get("dcf") or {}).get("growth_rate")
        if r is None:
            print(f"{n:16} sin 5 ejercicios")
            continue
        key, med, cur, drop, downs, m = r
        print(f"{n:16} {key[:3]} med={med:.3f} cur={cur:.3f} caída={drop if drop is None else round(drop, 2)} "
              f"bajadas={downs}/4 g={g if g is None else round(g, 3)} serie={[round(x, 3) for x in m]}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "e9")
