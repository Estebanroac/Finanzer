"""
F11 · T6: series de los ETF de país para el replay del análisis (fuerza relativa frente al país de la sede), con red.

El análisis de una empresa con sede fuera de EE. UU. (lib/market_context.py) descarga además el ETF de su país
(`market.country_etfs`). Se graban los de los países de los golden (panel y local) con el mismo rango de fechas que el
resto del juego del historial (desde el primer día grabado hasta el de la captura, 2026-10-16), descarga real como
`price_history.yfinance_fetcher` (sin ajustar, cierre ajustado aparte, eventos). Las barras del 2026-10-16 son el
cierre de ese día, no la barra intradía de la captura original: se declara en la metadata.

    cd finanzer_next/backend
    ../.venv313/bin/python tests/f11_country_etf_fixtures.py
"""
import json
import os

import history_fixtures as hf
from price_history import normalize

ETFS = ("EWU", "EWN", "EWQ", "EWJ", "EWT", "EDEN")    # Reino Unido, Países Bajos, Francia, Japón, Taiwán, Dinamarca
UNTIL = "2026-10-17"                                   # excluido: hasta el día de la captura del juego


def main():
    import yfinance as yf
    meta_path = os.path.join(hf.HISTORY_DIR, "metadata.json")
    meta = json.load(open(meta_path, encoding="utf-8"))
    since = min(v["first"] for v in meta["symbols"].values() if v.get("first"))
    for sym in ETFS:
        raw = yf.Ticker(sym).history(start=since, end=UNTIL, interval="1d", auto_adjust=False, actions=True)
        frame = normalize(raw)
        if frame is None:
            raise SystemExit(f"{sym}: sin serie")
        hf.save(sym, frame)
        dates = [d.strftime("%Y-%m-%d") for d in frame.index]
        meta["symbols"][sym] = {"first": dates[0], "last": dates[-1], "rows": len(dates), "status": "ok",
                                "dividends": int((frame["dividend"] > 0).sum()), "splits": {},
                                "captured": "F11 · T6 (2026-11-04): descarga real con start/end fijos; la barra del "
                                            "2026-10-16 es el cierre, no la intradía de la captura original"}
        print(sym, dates[0], dates[-1], len(dates))
    with open(meta_path, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=1)
        fh.write("\n")


if __name__ == "__main__":
    main()
