"""
F10 (PM, 29-oct; MSCI): la beta propia solo con semanas completas. Medida en el universo con las MISMAS series: para
cada empresa se descarga una vez su serie de precios (lib/price_history, como el análisis; solo Yahoo) y se calcula
la beta con la regla de antes (la semana de la última sesión entra) y con la de ahora (market_signals.beta), y si
pasa los filtros de la beta propia (lib/beta.own_filters): propia o de sector.

    cd backend
    ../../finanzer_next/.venv313/bin/python tools/f10_beta_semanas_medida.py --out medida.json [SYM...]

Sin símbolos, el universo (config/universe.tsv). Ritmo: un símbolo cada 0,3 s.
"""
import argparse
import json
import logging
import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, "..", "lib"), os.path.join(HERE, "..")]
logging.disable(logging.CRITICAL)

import pandas as pd  # noqa: E402

import beta as beta_mod  # noqa: E402
import market_signals as ms  # noqa: E402
import price_history  # noqa: E402
from settings import cfg  # noqa: E402


def beta_antes(close, market_close):
    """La regresión de market_signals.beta antes de F10 (con la semana de la última sesión)."""
    B, C = cfg("market.signals.beta"), cfg("valuation.capm")
    df = pd.concat([ms.weekly_returns(close, B["frequency"]), ms.weekly_returns(market_close, B["frequency"])],
                   axis=1, join="inner").dropna().tail(B["window_weeks"])
    if len(df) < B["min_weeks"]:
        return {"status": "historia_insuficiente", "observations": len(df)}
    r, rm = df.iloc[:, 0], df.iloc[:, 1]
    var_m = float(rm.var())
    raw = float(r.cov(rm)) / var_m
    corr = float(r.corr(rm))
    resid = (r - r.mean()) - raw * (rm - rm.mean())
    se = math.sqrt(float((resid ** 2).sum()) / (len(df) - 2) / (var_m * (len(df) - 1)))
    return {"status": "ok", "raw": raw, "adjusted": C["blume_weight"] * raw + C["blume_prior"], "r2": corr * corr,
            "se": se, "observations": len(df), "last_week": str(df.index[-1].date())}


def _universe():
    path = os.path.join(HERE, "..", "config", "universe.tsv")
    with open(path, encoding="utf-8") as fh:
        return [ln.split("\t")[0] for ln in fh if ln.strip() and not ln.startswith(("#", "symbol"))]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("symbols", nargs="*")
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    syms = args.symbols or _universe()
    out = []
    for s in syms:
        t0 = time.monotonic()
        try:
            hist = price_history.collect(price_history.start(s))
            frame, market = (hist or {}).get("frame"), ((hist or {}).get("market") or {}).get("frame")
            if frame is None or market is None:
                out.append({"symbol": s, "error": "sin serie"})
                continue
            old = beta_antes(frame["adj_close"], market["adj_close"])
            new = beta_mod.own_beta(frame, (hist or {}).get("market"))
            row = {"symbol": s, "last_session": str(frame.index[-1].date()), "antes": old,
                   "ahora": {k: new.get(k) for k in ("status", "raw", "adjusted", "r2", "se", "observations",
                                                     "last_week")}}
            for k, b in (("antes", old), ("ahora", new)):
                row[k]["fails"] = beta_mod.own_filters(b) if b.get("status") == "ok" else ["sin beta propia"]
                row[k]["metodo"] = "propia" if not row[k]["fails"] else "otra (sector o fuente)"
            out.append(row)
        except Exception as e:  # noqa: BLE001
            out.append({"symbol": s, "error": f"{type(e).__name__}: {e}"})
        time.sleep(max(0.0, 0.3 - (time.monotonic() - t0)))
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1, default=str)
    ok = [r for r in out if "error" not in r]
    flips = [r["symbol"] for r in ok if r["antes"]["metodo"] != r["ahora"]["metodo"]]
    d = sorted(abs((r["ahora"].get("adjusted") or 0) - (r["antes"].get("adjusted") or 0)) for r in ok
               if r["antes"].get("status") == r["ahora"].get("status") == "ok")
    print(f"{len(ok)} con serie, {len(out) - len(ok)} sin ella; cambian de método {len(flips)}: {flips}")
    if d:
        print(f"|Δ beta ajustada|: mediana {d[len(d) // 2]:.4f}, p90 {d[int(len(d) * 0.9)]:.4f}, máx. {d[-1]:.4f}")


if __name__ == "__main__":
    main()
