"""
F3 · T2: medidas de ciclicidad (§1.2) y de crecimiento rentable (§1.3) del panel, con la historia de EDGAR del replay,
y sensibilidad de la decisión a ±20% en cada umbral. No toca el motor: solo lee lo que el análisis ya calcula.

    cd finanzer_next/backend
    ../.venv313/bin/python tests/f3_t2_measures.py --out <dir>        # medidas.json + medidas.md
"""
import argparse
import json
import logging
import os
import sys
from pathlib import Path

B = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(B), str(B / "lib"), str(B / "tests")]
logging.disable(logging.CRITICAL)

import fixture_backend as fb  # noqa: E402
import cyclicality as cy  # noqa: E402
from settings import cfg  # noqa: E402

def capture(sym):
    import yf_adapter
    got = {}
    with fb.replay(fb.fixtures_dir("panel")) as store:
        orig = yf_adapter.get_ticker_info

        def wrap(s, *a, **kw):
            r = orig(s, *a, **kw)
            if s.upper() == sym and isinstance(r, dict):
                got.setdefault("info", r)
            return r
        yf_adapter.get_ticker_info = wrap
        import data_fetcher
        data_fetcher.get_ticker_info = wrap
        try:
            got["analysis"] = fb.run_analysis(sym, store)
        finally:
            yf_adapter.get_ticker_info = orig
            data_fetcher.get_ticker_info = orig
    return got


def sensitivity(hist):
    """Qué umbrales, movidos ±20%, cambian la decisión (la misma prueba que lib/classify._cyclicality)."""
    import classify
    r = classify._cyclicality(hist)
    return r["sensitivity"] if r else []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--tickers", nargs="*")
    args = ap.parse_args()
    out = Path(os.path.expanduser(args.out))
    out.mkdir(parents=True, exist_ok=True)
    rows, hists = [], {}
    for t in args.tickers or fb.env_tickers("panel"):
        try:
            g = capture(t)
        except Exception as e:          # SPY: ETF, 422 (no se analiza)
            print(t, f"sin análisis ({type(e).__name__})", flush=True)
            continue
        a, info = g.get("analysis") or {}, g.get("info") or {}
        hist = info.get("_history_fy") or {}
        m = cy.measure(hist)
        d = cy.decide(m)
        gp = cy.growth_profitable_measures(hist)
        cls = a.get("classification") or {}
        m["design"] = m.get("design") or {}
        km = a.get("key_metrics") or {}
        hists[t] = hist
        rows.append({"ticker": t, "arquetipo_hoy": cls.get("archetype"), "regla_hoy": cls.get("rule"),
                     "industria": cls.get("industry"), **m, **m["design"], **d,
                     "regla_nueva": cls.get("rule"), "frontera": cls.get("frontier"), "subtipo": cls.get("subtype"), "sensibilidad": sensitivity(hist), **gp,
                     "operating_margin": km.get("operating_margin"), "eps_ttm": km.get("eps")})
        print(t, "ok", flush=True)
    (out / "historias.json").write_text(json.dumps(hists, ensure_ascii=False, default=str))
    (out / "medidas.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False, default=str))
    L = ["| Ticker | Arquetipo (regla) | Años | Base | Episodios de caída de ingresos | Desplomes BPA con caída | "
         "Perímetro | Cíclica | Frontera | CAGR ing./acc. 3a | 5a | Margen op. | Diseño: caída máx. · amplitud · "
         "desplomes BPA |", "|" + "---|" * 13]

    def p(x):
        return "—" if x is None else f"{x * 100:.0f}%"

    def yrs(xs):
        return ", ".join(y[:4] for y in xs) or "—"
    for r in rows:
        eps_ = ", ".join(e[0][:4] + (f"–{e[-1][:4]}" if len(e) > 1 else "") for e in r["decline_episodes"]) or "—"
        amp = "—" if r.get("op_margin_amplitude") is None else f"{r['op_margin_amplitude']:.2f}"
        L.append(f"| {r['ticker']} | {r['arquetipo_hoy']} ({r['regla_nueva']}) | {r['years']} | {r['basis']} | "
                 f"{eps_} | {yrs(r['eps_collapse_with_decline'])} | {yrs(r['perimeter_years'])} | "
                 f"{'sí' if r['cyclical'] else ('sin historia' if not r['enough'] else 'no')} | "
                 f"{'; '.join(r['frontera'] or []) or '—'} | {p(r['revenue_ps_cagr_3y'])} | "
                 f"{p(r['revenue_ps_cagr_5y'])} | {p(r['operating_margin'])} | "
                 f"{p(r.get('revenue_drawdown'))} · {amp} · {len(r.get('eps_shock_years') or [])} |")
    (out / "medidas.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
