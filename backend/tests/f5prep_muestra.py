"""
Tablas de docs/fiabilidad/F5PREP_MUESTRA.md desde los fixtures de precios (sin red):

    cd finanzer_next/backend
    ../.venv313/bin/python tests/f5prep_muestra.py > /tmp/tablas.md

1. señales de los 36 tickers; 2. beta propia frente a Finnhub (golden del panel) y frente a la referencia de
la 2a; 3. latencia de la captura por ticker y total.
"""
import json
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import price_fixtures as pf  # noqa: E402
import fixture_backend as fb  # noqa: E402
import market_signals as ms  # noqa: E402


def pct(x, d=1):
    return "—" if x is None else f"{x * 100:+.{d}f}%"


def num(x, d=2):
    return "—" if x is None else f"{x:.{d}f}"


def v(sig, key="value"):
    return sig.get(key) if sig.get("status") == "ok" else None


def golden_beta(t):
    path = os.path.join(fb.golden_dir("panel"), f"{t}.json")
    if not os.path.isfile(path):
        return None, None
    with open(path, encoding="utf-8") as fh:
        a = json.load(fh)
    src = ((a.get("data_provenance") or {}).get("fields") or {}).get("beta") or {}
    return (a.get("beta") or {}).get("raw"), src.get("source")


def main():
    meta = pf.metadata()
    with open(os.path.join(pf.PRICES_DIR, "ref_2a_beta.json"), encoding="utf-8") as fh:
        ref2a = json.load(fh)["betas"]
    rows, betas = [], []
    for t in pf.panel_tickers():
        s = pf.replay_series(t)
        sig = ms.all_signals(s)
        tr, rs, dd1, dd3 = sig["trend"], sig["relative_strength"], sig["max_drawdown"]["1"], sig["max_drawdown"]["3"]
        w = rs.get("windows") or {}
        rows.append(
            f"| {t} | {s['status']} | {pct(v(sig['momentum_12_1']))} | {pct(v(tr))} | {pct(v(tr, 'slope'))} | "
            f"{v(tr, 'regime') or '—'} | {pct(v(sig['realized_volatility']), 0)} | "
            f"{pct(v(dd1), 0)} ({dd1.get('peak_date', '—')} → {dd1.get('trough_date', '—')}) | {pct(v(dd3), 0)} | "
            f"{s['sector_etf']} | {pct((w.get('126') or {}).get('difference'))} | "
            f"{pct((w.get('252') or {}).get('difference'))} | {num(v(sig['abnormal_volume']))} | "
            f"{num(v(sig['range_52w_position']) * 100 if v(sig['range_52w_position']) is not None else None, 0)}% |")
        b = sig["beta"]
        fh_beta, fh_src = golden_beta(t)
        r2a = (ref2a.get(t) or {}).get("beta_ref")
        own = v(b, "raw")
        betas.append((t, own, v(b, "adjusted"), v(b, "r2"), b.get("observations"), fh_beta, fh_src, r2a))

    print("### 1. Señales\n")
    print("| Ticker | Serie | Momentum 12-1 | Precio vs MM200 | Pendiente MM200 (21 s.) | Régimen | Volatilidad 1a "
          "| Drawdown 1a (pico → valle) | Drawdown 3a | ETF | FR 6m | FR 12m | Volumen z | Rango 52s |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    print("\n".join(rows))

    print("\n### 2. Beta propia frente a Finnhub y a la referencia de la 2a\n")
    print("| Ticker | Propia cruda | Propia Blume | R² | Semanas | Finnhub (golden) | Fuente | Propia − Finnhub "
          "| Ref. 2a | Propia − 2a |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    diffs, diffs2a = [], []
    for t, own, adj, r2, n, fhb, src, r2a in betas:
        d = None if own is None or fhb is None else own - fhb
        d2 = None if own is None or r2a is None else own - r2a
        if d is not None:
            diffs.append(abs(d))
        if d2 is not None:
            diffs2a.append(abs(d2))
        mark = " **←**" if t in ("BCS", "NVO") else ""
        print(f"| {t}{mark} | {num(own)} | {num(adj)} | {num(r2)} | {n or '—'} | {num(fhb)} | {src or '—'} | "
              f"{'—' if d is None else f'{d:+.2f}'} | {num(r2a)} | {'—' if d2 is None else f'{d2:+.3f}'} |")
    print(f"\n|propia − Finnhub|: mediana {statistics.median(diffs):.2f}, > 0.3 en {sum(x > 0.3 for x in diffs)} de "
          f"{len(diffs)}, > 0.5 en {sum(x > 0.5 for x in diffs)}.")
    print(f"|propia − ref. 2a|: mediana {statistics.median(diffs2a):.4f}, máx. {max(diffs2a):.4f} ({len(diffs2a)} "
          f"tickers).")

    print("\n### 3. Latencia (captura local, en frío, en serie)\n")
    print("| Ticker | Empresa (s) | ^GSPC (s) | ETF (s) | Total (s) |")
    print("|---|---|---|---|---|")
    lat = meta["latency_s"]
    for t in pf.panel_tickers():
        x = lat[t]
        print(f"| {t} | {x['company_s']:.2f} | {x['market_s']:.2f} | {x['sector_s']:.2f} | {x['total_s']:.2f} |")
    tot = [lat[t]["total_s"] for t in lat]
    co = [lat[t]["company_s"] for t in lat]
    print(f"\nTotal por ticker (tres series): mediana {statistics.median(tot):.2f} s, máx. {max(tot):.2f} s, suma "
          f"{sum(tot):.1f} s. Solo la serie de la empresa: mediana {statistics.median(co):.2f} s, máx. {max(co):.2f} s.")


if __name__ == "__main__":
    main()
