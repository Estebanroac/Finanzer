"""
Memoria por minuto de una prueba de carga (tools/load_test.py): de la serie del informe JSON (`memoria.serie`, una
muestra cada `--sample-s` con RSS y huella física) saca, minuto a minuto, el máximo de las dos medidas y la pendiente de
cada mitad de la carga (MB/min, mínimos cuadrados). Sirve para distinguir una excursión (sube con la concurrencia y se
estabiliza: cachés acotadas) de una fuga (crece de forma sostenida).

    ../../finanzer_next/.venv313/bin/python tools/memoria_por_minuto.py ../docs/rediseno/verificacion/V4_carga_cierre_12min.json
"""
import json
import sys
from typing import List, Tuple

BARS = " ▁▂▃▄▅▆▇█"


def slope(points: List[Tuple[float, float]]) -> float:
    """MB por minuto (mínimos cuadrados) de (segundos, MB)."""
    n = len(points)
    if n < 2:
        return 0.0
    mx = sum(t for t, _ in points) / n
    my = sum(v for _, v in points) / n
    den = sum((t - mx) ** 2 for t, _ in points)
    return 60 * sum((t - mx) * (v - my) for t, v in points) / den if den else 0.0


def main(path: str) -> None:
    with open(path, encoding="utf-8") as fh:
        d = json.load(fh)
    serie = d["memoria"]["serie"]
    mem = [(s["t"], max(s.get("rss_mb") or 0, s.get("footprint_mb") or 0)) for s in serie]
    end = mem[-1][0]
    start = end - d["duracion_carga_s"]          # la carga son los últimos `duracion_carga_s`; antes, el calentamiento
    lo, hi = min(v for _, v in mem), max(v for _, v in mem)
    print(f"# Memoria por minuto · {path.rsplit('/', 1)[-1]}\n")
    print(f"Máximo de RSS y huella física, una muestra cada ~{serie[1]['t'] - serie[0]['t']:.0f} s. "
          f"La carga empieza en t = {start / 60:.1f} min.\n")
    print("| Minuto | Fase | Máx. (MB) | Media (MB) | |")
    print("|---|---|---|---|---|")
    minute = 0
    while minute * 60 <= end:
        vals = [v for t, v in mem if minute * 60 <= t < (minute + 1) * 60]
        if vals:
            bar = BARS[min(len(BARS) - 1, int((max(vals) - lo) / max(hi - lo, 1) * (len(BARS) - 1)))]
            fase = "carga" if minute * 60 >= start else ("calentamiento" if (minute + 1) * 60 <= start else "→ carga")
            print(f"| {minute} | {fase} | {max(vals):.0f} | {sum(vals) / len(vals):.0f} | {bar} |")
        minute += 1
    load = [(t, v) for t, v in mem if t >= start]
    mid = start + (end - start) / 2
    first = [p for p in load if p[0] < mid]
    second = [p for p in load if p[0] >= mid]
    print(f"\nPendiente: 1.ª mitad de la carga {slope(first):+.1f} MB/min; 2.ª mitad {slope(second):+.1f} MB/min. "
          f"Pico {hi:.0f} MB; 2.ª mitad entre {min(v for _, v in second):.0f} y {max(v for _, v in second):.0f} MB.")


if __name__ == "__main__":
    main(sys.argv[1])
