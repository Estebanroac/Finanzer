"""
Fase 7 (PLAN §4, punto 3): el motor real, en replay, sobre los fixtures point-in-time del estudio. Sin red.

    cd finanzer_next/backend
    ../.venv313/bin/python tests/calibracion_ejecutar.py --data ~/Downloads/finanzer_calibracion [--fy 2015] [--tickers A B]

Por empresa y ejercicio: `_compute_analysis` con lo que se sabía en D (tests/calibracion_generar.py). Cambia frente al
replay del panel:
  · la Rf es el cierre de ^TNX en D (en el panel, la de config);
  · EDGAR sale de <data>/edgar_pit, cortado en D por el replay;
  · sin Finnhub ni calendario de resultados (no hay histórico).
Lo que NO es point-in-time (se declara en el informe): la prima de riesgo (4.20% de oct-2026; con --erp, la de
Damodaran a 31 de diciembre del año anterior a D, la que se conocía en D), las referencias de industria (Damodaran,
enero de 2026) y los umbrales sectoriales de config, las tasas base del DCF inverso (1984–2020), el sector y la
industria de hoy.
Salida: <data>/<--out-dir, por defecto resultados>/FY<año>.jsonl, una línea por análisis con lo que usa el estudio.
"""
import argparse
import json
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fixture_backend as fb  # noqa: E402
import history_fixtures as hf  # noqa: E402


def _rf_at(data):
    obj = json.load(open(hf.series_file("^TNX", data)))
    dates, close = obj["dates"], obj["close"]

    def at(day):
        i = max((k for k, d in enumerate(dates) if d <= day and close[k] is not None), default=None)
        return None if i is None else {"value": close[i] / 100, "as_of": dates[i]}
    return at


def _erp_at(path):
    by_year = json.load(open(os.path.expanduser(path)))["by_year"]

    def at(day):
        return by_year.get(str(int(day[:4]) - 1))       # la publicada el 1 de enero: la del cierre del año anterior
    return at


def _cfg_with(erp_of_current):
    """cfg de cost_of_capital con la prima del análisis en curso (las demás claves, intactas)."""
    from settings import cfg as real

    def f(key, *a, **k):
        v = real(key, *a, **k)
        erp = erp_of_current()
        if erp is None:
            return v
        if key == "valuation.capm.market_risk_premium":
            return erp
        if key == "valuation.capm":
            return {**v, "market_risk_premium": erp}
        return v
    return f


def _summary(a, meta):
    km = a.get("key_metrics") or {}
    q, p, c = a.get("quality") or {}, a.get("price_attractiveness") or {}, a.get("confidence") or {}
    rd = (a.get("reverse_dcf") or {}).get("main") or {}
    cats = {k: (v or {}).get("score") for k, v in ((a.get("score") or {}).get("breakdown") or {}).items()}
    return {
        "ticker": a.get("symbol"), **{k: meta["calibracion"][k] for k in ("fy", "fy_end", "D", "price", "sector")},
        "archetype": (a.get("classification") or {}).get("archetype"),
        "quality_score": q.get("score"), "quality_level": q.get("level"), "quality_partial": q.get("partial"),
        "price_score": p.get("score"), "price_level": p.get("level"), "price_score_raw": p.get("score_raw"),
        "price_level_raw": p.get("level_raw"), "confidence": c.get("level"), "categories": cats,
        "rf": (a.get("risk_free") or {}).get("value"), "mrp": (a.get("wacc") or {}).get("mrp"),
        "dcf_upside": (a.get("dcf") or {}).get("upside"), "rdcf_band": rd.get("band"), "rdcf_g10": rd.get("g10"),
        **{k: km.get(k) for k in ("pe", "pb", "ev_ebitda", "fcf_yield", "roe", "roic", "operating_margin",
                                  "net_margin", "de", "market_cap", "revenue", "net_income")},
    }


def run(data, fys, only=None, erp=None, out_name="resultados"):
    import cost_of_capital
    import f2b_fixtures
    import finnhub_fallback
    import logging
    import sec_edgar
    logging.disable(logging.CRITICAL)
    rf_at = _rf_at(data)
    erp_at = _erp_at(erp) if erp else None
    out_dir = os.path.join(data, out_name)
    os.makedirs(out_dir, exist_ok=True)
    for fy in fys:
        base = os.path.join(data, "fixtures", f"FY{fy}")
        if not os.path.isdir(base):
            continue
        syms = sorted(only or os.listdir(base))
        rows = []
        with fb.replay(base) as store:
            p = fb._Patcher()
            p.set(sec_edgar, "FETCHER", f2b_fixtures.edgar_fetcher(store, base=os.path.join(data, "edgar_pit")))
            p.set(finnhub_fallback, "earnings_calendar", lambda *a, **k: None)
            p.set(cost_of_capital, "_fetch_risk_free",
                  lambda: rf_at(str(store.meta[store.current]["captured_at_local"])[:10]))
            if erp_at:
                p.set(cost_of_capital, "cfg", _cfg_with(
                    lambda: erp_at(str(store.meta[store.current]["captured_at_local"])[:10])))
            try:
                for sym in syms:
                    if not os.path.isdir(os.path.join(base, sym)):
                        continue
                    store.misses.clear()
                    try:
                        a = fb.run_analysis(sym, store)
                        row = _summary(a, store.meta[sym])
                        row["misses"] = sorted(set(store.misses))
                        row["errors"] = [str(e)[:200] for e in (a.get("errors") or [])][:5]
                    except Exception as e:
                        row = {"ticker": sym, "fy": fy, "error": f"{type(e).__name__}: {e}"[:300],
                               "trace": traceback.format_exc()[-800:], "misses": sorted(set(store.misses))}
                    rows.append(row)
            finally:
                p.undo()
        with open(os.path.join(out_dir, f"FY{fy}.jsonl"), "w") as fh:
            for r in rows:
                fh.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")
        ok = sum(1 for r in rows if "error" not in r)
        print(f"FY{fy}: {ok}/{len(rows)} analizados", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--fy", type=int, nargs="*")
    ap.add_argument("--tickers", nargs="*")
    ap.add_argument("--erp", help="JSON de la prima implícita histórica (tools/damodaran_import.py --erp-out)")
    ap.add_argument("--out-dir", default="resultados")
    a = ap.parse_args()
    run(os.path.expanduser(a.data), a.fy or range(2012, 2022), a.tickers, a.erp, a.out_dir)


if __name__ == "__main__":
    main()
