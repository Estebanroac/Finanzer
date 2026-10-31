"""
P8: descarga real de las mini-gráficas para el replay y los tests (tests/fixtures/sparklines/<rango>_<intervalo>.json),
con el tiempo de cada descarga. Los símbolos son los de todas las listas y sectores de las tendencias del replay
(tests/fixtures/trending/batch.json), así el cintillo del replay tiene gráfica en cualquier lista.

    cd finanzer_next/backend
    ../.venv313/bin/python tests/capture_sparklines.py

Guarda por símbolo [(fecha u hora ISO, cierre)], lo único que usa lib/sparklines.py. `replay_fetcher()` devuelve un
FETCH que sirve esas series sin red (un símbolo que no está en la captura sale sin serie, como si Yahoo no lo diera).
"""
import datetime as dt
import json
import os
import sys
import time

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
for _p in (os.path.dirname(TESTS_DIR), os.path.join(os.path.dirname(TESTS_DIR), "lib"), TESTS_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

DIR = os.path.join(TESTS_DIR, "fixtures", "sparklines")


def _file(rng, interval):
    return os.path.join(DIR, f"{rng}_{interval}.json")


def replay_fetcher(base=DIR):
    cache = {}

    def fetch(symbols, rng, interval):
        key = (rng, interval)
        if key not in cache:
            path = os.path.join(base, f"{rng}_{interval}.json")
            with open(path, encoding="utf-8") as fh:
                cache[key] = json.load(fh)["symbols"]
        data = cache[key]
        return {s: [tuple(x) for x in data[s]] for s in symbols if s in data}
    return fetch


def _symbols():
    """P8b: por periodo, los símbolos de sus listas y de sus sectores (cada periodo tiene las suyas)."""
    import capture_trending
    import trending
    fetch, session = capture_trending.replay_fetcher()
    out = trending.compute(fetch, session=session)
    by_period = {}
    for p in out["lists"]:
        syms = []
        for rows in list(out["lists"][p].values()) + list(out["sectors"][p].values()):
            syms += [x["symbol"] for x in rows if x["symbol"] not in syms]
        by_period[p] = syms
    return by_period, session


def main():
    import sparklines
    from settings import cfg
    by_period, session = _symbols()
    os.makedirs(DIR, exist_ok=True)
    P = cfg("market.sparklines.periods")
    # 1D usa además el cierre diario de 5 días (la referencia: el cierre anterior)
    pairs = [(P[p]["range"], P[p]["interval"], by_period[p]) for p in P] + [("5d", "1d", by_period["1D"])]
    B = cfg("market.sparklines.batch_size")
    for rng, interval, syms in pairs:
        t0 = time.monotonic()
        got = {}
        for i in range(0, len(syms), B):
            got.update(sparklines.yf_fetch(syms[i:i + B], rng, interval))
        secs = time.monotonic() - t0
        with open(_file(rng, interval), "w", encoding="utf-8") as fh:
            json.dump({"captured": dt.date.today().isoformat(), "session": session, "range": rng,
                       "interval": interval,
                       "symbols": {s: [[t, round(v, 4)] for t, v in got[s]] for s in sorted(got)}},
                      fh, separators=(",", ":"), sort_keys=True)
            fh.write("\n")
        print(f"{rng}/{interval}: {len(got)} de {len(syms)} símbolos en {secs:.1f} s "
              f"(lotes de {B}); puntos medios {sum(len(v) for v in got.values()) / max(len(got), 1):.0f}")


if __name__ == "__main__":
    main()
