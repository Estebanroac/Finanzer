"""
Fase 5: series de los ETF de sector para el replay del análisis (fuerza relativa), derivadas SIN RED de los fixtures
de F5prep (tests/fixtures/prices, captura del 2026-10-15 tras el cierre, `auto_adjust=True`).

El análisis (lib/market_context.py) solo usa el cierre ajustado del ETF: se graba como `adj_close` y como `close`
(no hay cierre sin ajustar en esa captura; se declara en la metadata), recortado a los 2 años del juego del
historial. Se anota cada símbolo en tests/fixtures/history/metadata.json con su origen.

    cd finanzer_next/backend
    ../.venv313/bin/python tests/f5_sector_etf_fixtures.py
"""
import json
import os

import history_fixtures as hf
import price_fixtures as pf

ETFS = ("XLB", "XLC", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY", "VNQ")


def main():
    meta_path = os.path.join(hf.HISTORY_DIR, "metadata.json")
    meta = json.load(open(meta_path, encoding="utf-8"))
    since = min(v["first"] for v in meta["symbols"].values() if v.get("first"))
    for sym in ETFS:
        src = pf.load_obj(sym)
        keep = [i for i, d in enumerate(src["dates"]) if d >= since]
        dates = [src["dates"][i] for i in keep]
        close = [src["close"][i] for i in keep]
        obj = {"symbol": sym, "tz": hf.TZ, "dates": dates, "open": [None] * len(dates), "high": [None] * len(dates),
               "low": [None] * len(dates), "close": close, "adj_close": close,
               "volume": [src["volume"][i] for i in keep], "dividend": {}, "split": {}}
        with open(hf.series_file(sym), "w", encoding="utf-8") as fh:
            json.dump(obj, fh, separators=(",", ":"))
            fh.write("\n")
        meta["symbols"][sym] = {"first": dates[0], "last": dates[-1], "rows": len(dates), "status": "ok",
                                "derived_from": "tests/fixtures/prices (F5prep, 2026-10-15, auto_adjust=True): "
                                                "cierre ajustado como close y adj_close, sin máximos ni mínimos"}
        print(sym, dates[0], dates[-1], len(dates))
    with open(meta_path, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=1)
        fh.write("\n")


if __name__ == "__main__":
    main()
