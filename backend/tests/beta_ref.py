"""
Fase 2a (T3): beta de referencia para el informe de discrepancias (no entra en el motor).

Beta = cov(r, r_m) / var(r_m) con rendimientos SEMANALES simples de 2 años (104 semanas, cierre ajustado del viernes)
frente al S&P 500 (^GSPC), con yfinance. Se compara con la beta que usa el pipeline (replay del fixture: Finnhub o
Yahoo, según data_provenance.fields.beta).

    cd finanzer_next/backend
    ../.venv313/bin/python tests/beta_ref.py --out <dir>          # beta.json; precios en <dir>/beta_prices.json
"""
import argparse
import json
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fixture_backend as fb  # noqa: E402


def weekly_returns(series):
    s = series.dropna().resample("W-FRI").last().dropna()
    return s.pct_change().dropna()


def beta(r, rm):
    import pandas as pd
    df = pd.concat([r, rm], axis=1, join="inner").dropna().tail(104)
    if len(df) < 52:
        return None, len(df)
    cov = df.iloc[:, 0].cov(df.iloc[:, 1])
    return cov / df.iloc[:, 1].var(), len(df)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--tickers", nargs="*")
    a = ap.parse_args()
    logging.disable(logging.CRITICAL)
    import yfinance as yf
    out = Path(os.path.expanduser(a.out))
    out.mkdir(parents=True, exist_ok=True)
    tickers = a.tickers or [t for t in fb.env_tickers("panel") if t != "SPY"]
    px = yf.download(tickers + ["^GSPC"], period="2y", interval="1d", auto_adjust=True, progress=False,
                     group_by="ticker", threads=False)
    rm = weekly_returns(px["^GSPC"]["Close"])
    rows = {}
    for t in tickers:
        try:
            b, n = beta(weekly_returns(px[t]["Close"]), rm)
        except KeyError:
            b, n = None, 0
        golden = fb.golden_dir("panel")
        a_json = json.loads(Path(golden, f"{t}.json").read_text()) if Path(golden, f"{t}.json").exists() else {}
        src = ((a_json.get("data_provenance") or {}).get("fields") or {}).get("beta") or {}
        rows[t] = {"beta_ref": b, "semanas": n, "beta_pipeline": (a_json.get("beta") or {}).get("raw"),
                   "fuente_pipeline": src.get("source"), "detalle": src.get("detail")}
        print(f"{t:6} ref {b if b is None else round(b, 3)!s:>6} ({n} sem.)  pipeline "
              f"{rows[t]['beta_pipeline']!s:>8} [{rows[t]['fuente_pipeline']}]", flush=True)
    (out / "beta.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False))
    last = px.index.max()
    print(f"\nprecios hasta {last.date()} → {out / 'beta.json'}")


if __name__ == "__main__":
    main()
