"""
Captura (con red) las series diarias de precios de los 36 tickers del panel ampliado y mide la latencia.
Uso EXPLÍCITO, nunca automático, DESPUÉS del cierre de Nueva York y en una sola sesión:

    cd finanzer_next/backend
    ../.venv313/bin/python tests/capture_prices.py                  # los 36 → tests/fixtures/prices/
    ../.venv313/bin/python tests/capture_prices.py --dir /tmp/x AAPL

Por cada ticker descarga sus TRES series en frío (empresa, ^GSPC y ETF del sector) con
price_series.fetch_price_series, en serie (concurrencia 1) y con una pausa entre tickers: la latencia
medida es la de un análisis sin caché. Las series compartidas (^GSPC y los ETF) se graban una vez y se
comprueba que las descargas posteriores coinciden con la grabada (determinismo de la fuente en la sesión).

El sector sale del golden del panel (`sector_info.sector`); para los tickers que aún no están en el panel,
de yfinance `info` (se declara en `sector_source`). Sin secretos: Yahoo no usa clave.
"""
import argparse
import datetime as _dt
import json
import logging
import os
import platform
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import price_fixtures as pf  # noqa: E402  (añade backend/ y lib/ al path)
import fixture_backend as fb  # noqa: E402
import price_series  # noqa: E402
from settings import cfg  # noqa: E402

PAUSE_BETWEEN_TICKERS_S = 1.0
CLOSE_REL_TOL = 1e-6   # el ruido observado entre descargas es ~1e-7 relativo


def sector_of(ticker):
    path = os.path.join(fb.golden_dir("panel"), f"{ticker}.json")
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as fh:
            si = json.load(fh).get("sector_info") or {}
        if si.get("sector"):
            return si["sector"], "golden del panel (sector_info.sector)"
    import yfinance as yf
    return (yf.Ticker(ticker).info or {}).get("sector"), "yfinance info (en la captura)"


def compare(a, b):
    """None si son iguales; "ruido" si solo difieren en el redondeo del cierre ajustado (float32 de Yahoo al
    recalcular el ajuste por dividendos) o en el volumen de la última sesión; "distinta" en otro caso."""
    if a == b:
        return None
    if a["dates"] != b["dates"] or a.get("splits") != b.get("splits"):
        return "distinta"
    if any(abs(x - y) > CLOSE_REL_TOL * abs(x) for x, y in zip(a["close"], b["close"])):
        return "distinta"
    if a["volume"][:-1] != b["volume"][:-1]:
        return "distinta"
    return "ruido"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tickers", nargs="*")
    ap.add_argument("--dir", default=pf.PRICES_DIR)
    a = ap.parse_args()
    logging.disable(logging.CRITICAL)
    import pandas
    import yfinance

    base = os.path.abspath(os.path.expanduser(a.dir))
    os.makedirs(os.path.join(base, "series"), exist_ok=True)
    tickers = a.tickers or pf.panel_tickers()
    P = cfg("market.price_series")
    started = _dt.datetime.now(_dt.timezone.utc)
    recorded = {}          # símbolo → objeto JSON grabado
    mismatches = []        # descargas posteriores de una serie compartida que no coinciden
    noise = []             # ... que solo difieren en redondeo del ajuste o en el volumen de hoy
    meta_t, latency = {}, {}

    def fetcher(symbol, period, interval):
        return price_series.yfinance_fetcher(symbol, period, interval)

    for i, t in enumerate(tickers):
        if i:
            time.sleep(PAUSE_BETWEEN_TICKERS_S)
        sector, src = sector_of(t)
        res = price_series.fetch_price_series(t, sector, fetcher=fetcher)
        for role, s in res["series"].items():
            if s["frame"] is None:
                continue
            obj = pf.frame_to_obj(s["symbol"], s["frame"])
            if s["symbol"] in recorded:
                kind = compare(recorded[s["symbol"]], obj)
                if kind:
                    (noise if kind == "ruido" else mismatches).append({"ticker": t, "symbol": s["symbol"]})
            else:
                recorded[s["symbol"]] = obj
        meta_t[t] = {"sector": sector, "sector_source": src, "sector_etf": res["sector_etf"],
                     "market_symbol": res["market_symbol"], "market_fallback": res["market_fallback"],
                     "status": res["status"], "reasons": res["reasons"]}
        latency[t] = {"total_s": round(res["latency_s"], 3),
                      **{f"{role}_s": round(s["latency_s"], 3) for role, s in res["series"].items()},
                      "attempts": {role: s["attempts"] for role, s in res["series"].items()}}
        print(f"{t:6} {res['status']:10} {latency[t]['total_s']:6.2f}s  "
              f"({', '.join(f'{r} {s['symbol']} {s.get('rows')}' for r, s in res['series'].items())})"
              + (f"  {res['reasons']}" if res["reasons"] else ""), flush=True)

    for sym, obj in recorded.items():
        with open(pf.series_file(sym, base), "w", encoding="utf-8") as fh:
            json.dump(obj, fh, separators=(",", ":"))
    ended = _dt.datetime.now(_dt.timezone.utc)
    ny = _dt.timezone(_dt.timedelta(hours=-4))  # EDT (octubre)
    tot = [v["total_s"] for v in latency.values()]
    meta = {
        "captured_at_utc": started.isoformat(timespec="seconds"),
        "captured_until_utc": ended.isoformat(timespec="seconds"),
        "captured_at_new_york": started.astimezone(ny).isoformat(timespec="seconds"),
        "source": "Yahoo Finance vía yfinance Ticker.history(auto_adjust=True): cierre y volumen ajustados "
                  "por splits y dividendos",
        "versions": {"python": platform.python_version(), "yfinance": yfinance.__version__,
                     "pandas": pandas.__version__},
        "git_commit": fb.git_commit(),
        "period": P["period"], "interval": P["interval"], "market_symbol": P["market_symbol"],
        "concurrency": 1, "pause_between_tickers_s": PAUSE_BETWEEN_TICKERS_S,
        "tickers": meta_t,
        "latency_s": latency,
        "latency_summary_s": {"tickers": len(tot), "sum": round(sum(tot), 3),
                              "median": round(sorted(tot)[len(tot) // 2], 3), "max": round(max(tot), 3)},
        "shared_series_mismatches": mismatches,
        "shared_series_noise": {"count": len(noise), "close_rel_tol": CLOSE_REL_TOL,
                                "note": "redondeo float32 del cierre ajustado o volumen de la última sesión"},
        "symbols": sorted(recorded),
    }
    with open(os.path.join(base, "metadata.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=1, ensure_ascii=False)
    print(f"\n{len(recorded)} series → {base}; latencia por ticker mediana {meta['latency_summary_s']['median']} s, "
          f"máx. {meta['latency_summary_s']['max']} s; series compartidas distintas: {len(mismatches)} (solo ruido: {len(noise)})")


if __name__ == "__main__":
    main()
