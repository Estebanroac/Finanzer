"""
Fase 7 (F4_PARADA §5: "bandas de REIT y utilities sin muestra: se calibran en la fase 7 con la historia de EDGAR de
una muestra amplia"). Distribución de cada métrica en una muestra amplia frente a los tramos de config.

    cd finanzer_next/backend
    SEC_EDGAR_USER_AGENT=... ../.venv313/bin/python tests/calibracion_bandas.py --data ~/Downloads/finanzer_calibracion \
        [--sin-red] --out <informe.md>

Empresa-año (ejercicios 2012–2025, hechos de EDGAR de hoy; precio de cierre del último día del ejercicio de Yahoo):
  · REIT: deuda neta/EBITDA, FFO/patrimonio, FFO/ingresos, dividendos/FFO, P/FFO (FFO = beneficio neto + D&A, la
    definición del motor);
  · UTILITY: deuda neta/EBITDA, cobertura de intereses (EBIT/intereses), rentabilidad por dividendo.
Para cada métrica: percentiles 10/25/50/75/90 y la proporción de la muestra en cada tramo de config. Criterio (fijado
antes de mirar): un tramo está bien centrado si la mediana de la muestra cae en el tramo neutro (0 puntos) o en uno de
los dos contiguos, y si ningún tramo extremo recoge más del 40% de la muestra. Lo que no cumpla se propone revisar;
no se cambia nada sin decisión.
"""
import argparse
import json
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fixture_backend  # noqa: E402,F401
import calibracion_datos as CD  # noqa: E402
import calibracion_generar as G  # noqa: E402
from settings import cfg  # noqa: E402

REITS = ["SPG", "PSA", "EQR", "AVB", "WELL", "O", "PLD", "AMT", "EXR", "ESS", "MAA", "UDR", "CPT", "VTR", "BXP",
         "ARE", "KIM", "REG", "FRT", "HST", "DLR", "NNN", "WPC", "OHI", "CUBE", "ELS", "SUI", "CCI"]
UTILITIES = ["SO", "D", "AEP", "EXC", "XEL", "SRE", "DUK", "NEE", "ED", "PEG", "EIX", "WEC", "ES", "DTE", "ETR", "PPL",
             "AEE", "CMS", "CNP", "FE", "ATO", "LNT", "NI", "PNW", "OGE"]
YEARS = range(2012, 2026)


def _fy_ends(facts):
    return sorted({f["end"] for f in G._facts(facts, "Assets", G._usd) if f.get("form") in ("10-K", "10-K/A")
                   and not f.get("start") and int(f["end"][:4]) in YEARS})


def _close_at(data, sym, day):
    import history_fixtures as hf
    p = hf.series_file(sym, data)
    if not os.path.isfile(p):
        return None
    obj = json.load(open(p))
    idx = [i for i, d in enumerate(obj["dates"]) if d <= day]
    return obj["close"][idx[-1]] if idx else None


def metrics(data, t, kind):
    tick = json.load(open(os.path.join(data, "edgar", "company_tickers.json")))
    cik = (tick.get(t) or {}).get("cik")
    if not cik:
        return []
    facts = json.load(open(os.path.join(data, "edgar", "companyfacts", f"CIK{int(cik):010d}.json")))
    out = []
    for e in _fy_ends(facts):
        inc, bs, cf, _ = G.statements(facts, G._d(e), "9999-12-31", n=1, reit_debt=(kind == "reit"))
        if inc.empty:
            continue
        col = lambda df, row: (float(df.loc[row].iloc[0]) if row in df.index and df.loc[row].iloc[0] == df.loc[row].iloc[0]
                               else None)
        ni, oi, rev = col(inc, "Net Income"), col(inc, "Operating Income"), col(inc, "Total Revenue")
        da, intr = col(cf, "Depreciation And Amortization"), col(inc, "Interest Expense")
        debt, cash = col(bs, "Total Debt"), col(bs, "Cash And Cash Equivalents")
        eq, div = col(bs, "Stockholders Equity"), col(cf, "Common Stock Dividend Paid")
        sh = col(inc, "Diluted Average Shares")
        ebitda = (oi + da) if (oi is not None and da is not None) else None
        nd = (debt - (cash or 0.0)) if debt is not None else None
        r = {"ticker": t, "fy_end": e}
        if nd is not None and ebitda and ebitda > 0:
            r["nde"] = nd / ebitda
        px = _close_at(data, t, e)
        mcap = px * sh if (px and sh) else None
        if kind == "reit":
            ffo = (ni + da) if (ni is not None and da is not None) else None
            if ffo is not None and eq and eq > 0:
                r["ffo_equity"] = ffo / eq
            if ffo is not None and rev and rev > 0:
                r["ffo_margin"] = ffo / rev
            if ffo and ffo > 0 and div is not None:
                r["ffo_payout"] = abs(div) / ffo
            if ffo and ffo > 0 and mcap:
                r["pffo"] = mcap / ffo
        else:
            if oi is not None and intr and intr > 0:
                r["coverage"] = oi / intr
            if div is not None and mcap:
                r["yield"] = abs(div) / mcap
        out.append(r)
    return out


# (métrica, clave de config de los tramos, sentido: True = mejor cuanto MENOR ("≤"), puntos)
BANDS = {"reit": [("nde", "thresholds.score.solidez.reit_nde_bounds", True, "thresholds.score.solidez.reit_nde_points"),
                  ("ffo_equity", "thresholds.score.rentabilidad.reit_ffo_equity_bounds", False,
                   "thresholds.score.rentabilidad.reit_ffo_equity_points"),
                  ("ffo_margin", "thresholds.score.rentabilidad.reit_ffo_margin_bounds", False,
                   "thresholds.score.rentabilidad.reit_ffo_margin_points"),
                  ("ffo_payout", "thresholds.score.calidad.reit_ffo_payout_bounds", True,
                   "thresholds.score.calidad.reit_ffo_payout_points"),
                  ("pffo", "thresholds.score.valoracion.reit_pffo_bounds", True,
                   "thresholds.score.valoracion.reit_pffo_points")],
         "utility": [("nde", "thresholds.score.solidez.utility_nde_bounds", True,
                      "thresholds.score.solidez.utility_nde_points"),
                     ("coverage", "thresholds.score.solidez.utility_coverage_bounds", False,
                      "thresholds.score.solidez.utility_coverage_points"),
                     ("yield", "thresholds.score.valoracion.utility_yield_bounds", False,
                      "thresholds.score.valoracion.utility_yield_points")]}


def _band(x, bounds, lower_better):
    for i, b in enumerate(bounds):
        if (x <= b) if lower_better else (x >= b):
            return i
    return len(bounds)


def _q(xs, p):
    xs = sorted(xs)
    k = (len(xs) - 1) * p
    f = int(k)
    return xs[f] + (xs[min(f + 1, len(xs) - 1)] - xs[f]) * (k - f)


def study(data):
    lines = ["# Bandas de REIT y utilities frente a la muestra (fase 7)\n"]
    verdicts = []
    for kind, tickers in (("reit", REITS), ("utility", UTILITIES)):
        rows = [r for t in tickers for r in metrics(data, t, kind)]
        firms = len({r["ticker"] for r in rows})
        lines.append(f"## {kind.upper()} · {firms} empresas, {len(rows)} empresa-año (2012–2025)\n")
        lines.append("| Métrica | n | p10 | p25 | p50 | p75 | p90 | Tramos de config | Puntos | Proporción por tramo | "
                     "Tramo de la mediana | Veredicto |")
        lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
        for m, bkey, lower, pkey in BANDS[kind]:
            xs = [r[m] for r in rows if r.get(m) is not None]
            if len(xs) < 20:
                lines.append(f"| {m} | {len(xs)} | muestra insuficiente |")
                continue
            bounds, pts = list(cfg(bkey)), list(cfg(pkey))
            share = [0] * (len(bounds) + 1)
            for x in xs:
                share[_band(x, bounds, lower)] += 1
            share = [s / len(xs) for s in share]
            med_band = _band(statistics.median(xs), bounds, lower)
            neutral = pts.index(0) if 0 in pts else None
            ok_center = neutral is not None and abs(med_band - neutral) <= 1
            ok_tails = share[0] <= 0.40 and share[-1] <= 0.40
            v = "bien centrada" if (ok_center and ok_tails) else "revisar"
            verdicts.append((kind, m, v))
            qs = " | ".join(f"{_q(xs, p):.3g}" for p in (0.1, 0.25, 0.5, 0.75, 0.9))
            lines.append(f"| {m} | {len(xs)} | {qs} | {bounds} | {pts} | "
                         f"{' / '.join(f'{s * 100:.0f}%' for s in share)} | {med_band} (neutro {neutral}) | **{v}** |")
        lines.append("")
    return "\n".join(lines), verdicts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--sin-red", action="store_true")
    a = ap.parse_args()
    data = os.path.expanduser(a.data)
    if not a.sin_red:
        ua = os.environ.get("SEC_EDGAR_USER_AGENT", "").strip()
        if not ua:
            sys.exit("falta SEC_EDGAR_USER_AGENT en el entorno")
        CD.fetch_edgar(data, ua, REITS + UTILITIES)
        CD.fetch_edgar(data, ua, REITS, force=True)      # con las etiquetas de deuda de los REIT (EXTRA)
        CD.fetch_yahoo(data, REITS + UTILITIES)
    txt, verdicts = study(data)
    with open(os.path.expanduser(a.out), "w") as fh:
        fh.write(txt)
    print(txt)


if __name__ == "__main__":
    main()
