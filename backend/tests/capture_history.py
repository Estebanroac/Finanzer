"""
Fase 2b: captura (con red) de la serie diaria que el análisis descarga desde la 2b (lib/price_history.py), para el
replay del panel y del juego local. Uso EXPLÍCITO, nunca automático, fuera de la ventana de 15:55 a 16:45 de Nueva
York y en una sola sesión:

    cd finanzer_next/backend
    ../.venv313/bin/python tests/capture_history.py                # panel + local + ^GSPC y SPY → tests/fixtures/history/
    ../.venv313/bin/python tests/capture_history.py --dir /tmp/x AAPL
    ../.venv313/bin/python tests/capture_history.py --chart AAPL JPM O NEE XOM PLTR RIVN BCS ^GSPC SPY \
        XLK XLF VNQ XLU XLE XLY        # rediseño E2a: 5 años para la gráfica de /v2 → tests/fixtures/history/chart/

Los fixtures del panel (14 y 15-oct) y del juego local (11 y 12-oct) son anteriores a la 2b y no traen esta serie.
Se capturan aparte, con la misma llamada que hace producción (price_history.yfinance_fetcher: precios SIN ajustar
por dividendos, cierre ajustado aparte, dividendos y splits declarados), y el replay corta cada serie en la fecha
de captura del ticker analizado (fixture_backend): los precios sin ajustar y los eventos de fechas pasadas no
cambian, así que la serie cortada es la que se habría descargado ese día (salvo una reexpresión por split
posterior, que se comprueba aquí: ningún split después de la fecha de corte). Sin secretos: Yahoo no usa clave.
"""
import argparse
import datetime as _dt
import json
import os
import platform
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fixture_backend as fb  # noqa: E402
import history_fixtures as hf  # noqa: E402  (añade backend/ y lib/ al path)
import price_history  # noqa: E402
from settings import cfg  # noqa: E402

PAUSE_S = 0.5


def default_symbols():
    local = sorted(d for d in os.listdir(fb.fixtures_dir("local")) if os.path.isdir(os.path.join(fb.fixtures_dir("local"), d)))
    panel = sorted(d for d in os.listdir(fb.fixtures_dir(fb.PANEL_ENV)) if os.path.isdir(os.path.join(fb.fixtures_dir(fb.PANEL_ENV), d)))
    P = cfg("market.price_series")
    return sorted(set(panel) | set(local)) + [P["market_symbol"], P["market_fallback_symbol"]]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("symbols", nargs="*")
    ap.add_argument("--dir", default=hf.HISTORY_DIR)
    ap.add_argument("--chart", action="store_true",
                    help="rediseño E2a: la serie larga de la gráfica de /v2 (chart_period) en <dir>/chart")
    ap.add_argument("--since", type=_dt.date.fromisoformat,
                    help="V4b: desde esta fecha (AAAA-MM-DD; se descargan 10 años y se recorta). Para capturar días "
                         "después del juego: el replay corta en la fecha de captura de cada ticker y la serie tiene que "
                         "cubrir el periodo completo antes de ella (rentabilidad a 5 años)")
    args = ap.parse_args(argv)
    if args.chart and not args.symbols:
        ap.error("--chart necesita los símbolos (los 8 de verificación, ^GSPC, SPY y los ETF de sus sectores)")
    syms = [s.upper() for s in args.symbols] or default_symbols()
    sub = "chart" if args.chart else "series"
    os.makedirs(os.path.join(args.dir, sub), exist_ok=True)
    H = cfg("market.history")
    period = "10y" if args.since else H["chart_period"] if args.chart else H["period"]
    t0 = _dt.datetime.now(_dt.timezone.utc)
    report = {}
    for s in syms:
        res = price_history._download(s, price_history.yfinance_fetcher, period=period)
        f = res["frame"]
        if f is not None and args.since:
            f = f[[d.date() >= args.since for d in f.index]]
        if f is None:
            report[s] = {"status": "sin_dato", "reason": res["reason"]}
            print(f"[{s}] SIN DATO: {res['reason']}")
            continue
        hf.save(s, f, args.dir, sub)
        divs = int((f["dividend"] > 0).sum())
        splits = {d.strftime("%Y-%m-%d"): float(x) for d, x in f["split"].items() if x}
        report[s] = {"status": "ok", "rows": len(f), "first": f.index[0].strftime("%Y-%m-%d"),
                     "last": f.index[-1].strftime("%Y-%m-%d"), "dividends": divs, "splits": splits,
                     "latency_s": round(res["latency_s"], 3)}
        print(f"[{s}] OK {len(f)} sesiones {report[s]['first']}..{report[s]['last']}, {divs} dividendos, "
              f"splits {splits or '—'}, {res['latency_s']:.2f}s")
        time.sleep(PAUSE_S)
    import yfinance
    import pandas
    meta = {"captured_at_utc": t0.isoformat(timespec="seconds"),
            "captured_until_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
            "source": "Yahoo Finance vía yfinance Ticker.history(auto_adjust=False, actions=True): precios sin ajustar "
                      "por dividendos, cierre ajustado, dividendos y splits (price_history.yfinance_fetcher)",
            "period": period, "since": args.since.isoformat() if args.since else None, "interval": H["interval"],
            "versions": {"python": platform.python_version(), "yfinance": yfinance.__version__,
                         "pandas": pandas.__version__},
            "replay": "cada serie se corta en la fecha de captura del ticker analizado (fixture_backend)",
            "symbols": report}
    path = os.path.join(args.dir, "chart", "metadata.json") if args.chart else os.path.join(args.dir, "metadata.json")
    if os.path.isfile(path) and args.symbols:
        with open(path, encoding="utf-8") as fh:
            old = json.load(fh)
        old["symbols"].update(report)
        meta["symbols"] = old["symbols"]
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=1, sort_keys=True, ensure_ascii=False)
        fh.write("\n")
    bad = [s for s, r in report.items() if r["status"] != "ok"]
    print(f"\n{len(report) - len(bad)}/{len(report)} series → {args.dir}" + (f"; sin dato: {bad}" if bad else ""))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
