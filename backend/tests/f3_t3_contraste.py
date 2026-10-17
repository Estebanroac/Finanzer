"""
F3 · T3: contraste independiente del DCF inverso (prompt F3 §T3: "una hoja o un script aparte, no el código del
motor; el crecimiento exigido coincide a ±0.1 pp").

No importa nada del motor. Lee de la salida del panel (`panel_run.py --out DIR`) los supuestos de cada lectura
(precio, flujo y deuda neta por acción, tasa, crecimiento terminal) y resuelve g con su propia implementación:
tabla explícita de 10 flujos (g constante años 1–5; años 6–10, interpolación lineal hasta el terminal), valor terminal
de Gordon y método de la secante. Compara con g* del motor.

    cd finanzer_next/backend
    ../.venv313/bin/python tests/f3_t3_contraste.py --panel <DIR> [--tickers KO V NFLX DOW PG]
"""
import argparse
import json
import sys
from pathlib import Path


def value(g, fps, rate, tg, nds, price=None):
    rates = [g] * 5 + [g + (tg - g) * k / 5 for k in range(1, 6)]
    cf, pv = fps, 0.0
    for t, r in enumerate(rates, start=1):
        cf = cf * (1 + r)
        pv += cf / (1 + rate) ** t
    tv = cf * (1 + tg) / (rate - tg)
    return pv + tv / (1 + rate) ** 10 - nds


def solve(price, fps, rate, tg, nds):
    a, b = 0.0, 0.10
    fa, fb = value(a, fps, rate, tg, nds) - price, value(b, fps, rate, tg, nds) - price
    for _ in range(200):
        if fb == fa:
            break
        c = b - fb * (b - a) / (fb - fa)
        a, fa = b, fb
        b, fb = c, value(c, fps, rate, tg, nds) - price
        if abs(fb) < 1e-10 * price:
            break
    return b


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", required=True)
    ap.add_argument("--tickers", nargs="*", default=["KO", "V", "NFLX", "DOW", "PG"])
    args = ap.parse_args()
    rows, worst = [], 0.0
    for t in args.tickers:
        a = json.loads((Path(args.panel) / f"{t}.json").read_text())
        m = ((a.get("reverse_dcf") or {}).get("main")) or {}
        if m.get("state") != "ok":
            print(f"{t}: sin lectura ok ({m.get('state')})")
            continue
        price = a.get("price") or (a.get("key_metrics") or {}).get("price")
        g = solve(price, m["flow_per_share"], m["rate"], m["terminal_growth"], m["net_debt_per_share"])
        d = abs(g - m["g_star"]) * 100
        worst = max(worst, d)
        rows.append(f"| {t} | {price:.2f} | {m['flow_per_share']:.4f} | {m['net_debt_per_share']:.4f} | "
                    f"{m['rate'] * 100:.3f}% | {m['g_star'] * 100:.4f}% | {g * 100:.4f}% | {d:.6f} |")
    print("| Ticker | Precio | Flujo/acción | Deuda neta/acción | Tasa | g* motor | g* independiente | Δ (pp) |")
    print("|---|---|---|---|---|---|---|---|")
    print("\n".join(rows))
    ok = worst <= 0.1
    print(f"\nMáxima diferencia: {worst:.6f} pp -> {'COINCIDE (±0.1 pp)' if ok else 'NO COINCIDE'}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
