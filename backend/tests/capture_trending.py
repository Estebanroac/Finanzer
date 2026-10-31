"""
Rediseño E2b (Task 4): descarga real del universo para el replay y los tests de las tendencias
(tests/fixtures/trending/batch.json), con el tiempo de la descarga y la memoria pico del proceso.

    cd finanzer_next/backend
    ../.venv313/bin/python tests/capture_trending.py

Guarda por símbolo las fechas, cierres, cierres ajustados y volúmenes (lo único que usa trending.compute; P8b:
diaria de `history_days` días, con «Adj Close» para la rentabilidad de cada periodo). `replay_fetcher()` devuelve
un FETCH_BATCH que reconstruye la forma de yf.download(group_by="ticker") y la sesión de la captura.
"""
import datetime as dt
import json
import os
import resource
import sys
import time

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
for _p in (os.path.dirname(TESTS_DIR), os.path.join(os.path.dirname(TESTS_DIR), "lib"), TESTS_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import trending  # noqa: E402

BATCH_FILE = os.path.join(TESTS_DIR, "fixtures", "trending", "batch.json")


def _rss_mb():
    r = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return r / (1024 * 1024) if sys.platform == "darwin" else r / 1024     # macOS: bytes; Linux: KB


def replay_fetcher(path=BATCH_FILE):
    import pandas as pd
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)

    def fetch(symbols):
        cols = {}
        for s in symbols:
            d = data["symbols"].get(s)
            if not d:
                continue
            idx = pd.to_datetime(d["dates"])
            cols[(s, "Close")] = pd.Series(d["close"], index=idx, dtype="float64")
            cols[(s, "Adj Close")] = pd.Series(d.get("adj", d["close"]), index=idx, dtype="float64")
            cols[(s, "Volume")] = pd.Series(d["volume"], index=idx, dtype="float64")
        df = pd.DataFrame(cols)
        if len(df.columns):
            df.columns = pd.MultiIndex.from_tuples(df.columns, names=["Ticker", "Price"])
        return df
    return fetch, data["session"]


def main():
    base = _rss_mb()
    session = trending.last_closed_session()
    raw = {}

    def fetch(symbols):
        df = trending.yf_batch(symbols)
        for s in symbols:
            if s in set(df.columns.get_level_values(0)):
                sub = df[s][["Close", "Adj Close", "Volume"]].dropna(subset=["Close"])
                raw[s] = {"dates": [d.strftime("%Y-%m-%d") for d in sub.index],
                          "close": [round(float(v), 4) for v in sub["Close"]],
                          "adj": [round(float(a), 4) if a == a else round(float(c), 4)
                                  for a, c in zip(sub["Adj Close"], sub["Close"])],
                          "volume": [None if v != v else float(v) for v in sub["Volume"]]}
        return df
    t0 = time.monotonic()
    out = trending.compute(fetch, session=session)
    secs = time.monotonic() - t0
    os.makedirs(os.path.dirname(BATCH_FILE), exist_ok=True)
    with open(BATCH_FILE, "w", encoding="utf-8") as fh:
        json.dump({"captured": dt.date.today().isoformat(), "session": session, "symbols": raw}, fh,
                  separators=(",", ":"), sort_keys=True)
        fh.write("\n")
    print(f"sesión {out['session']} (esperada {session}); {out['count']} valores de "
          f"{len(trending._universe_symbols())}; lotes fallidos {out['failed_batches']}")
    print(f"descarga + cálculo: {secs:.1f} s; memoria pico del proceso {_rss_mb():.0f} MB (base {base:.0f} MB)")
    for p, lists in out["lists"].items():
        print(p, out["periods"][p])
        for k, items in lists.items():
            print("  ", k, ", ".join(f"{x['symbol']} {x['change_pct']:+.1%} ${(x['dollar_volume'] or 0) / 1e9:.1f}B"
                                     for x in items[:5]))
    fetch2, sess2 = replay_fetcher()
    again = trending.compute(fetch2, session=sess2)
    # el fixture guarda los precios con 4 decimales: mismo orden y variaciones iguales a 1e-6
    same = all([x["symbol"] for x in again["lists"][p][k]] == [x["symbol"] for x in out["lists"][p][k]] and
               all(abs(a["change_pct"] - b["change_pct"]) < 1e-6
                   for a, b in zip(again["lists"][p][k], out["lists"][p][k]))
               for p in out["lists"] for k in out["lists"][p])
    print("replay", "idéntico" if same else "DISTINTO")
    if not same:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
