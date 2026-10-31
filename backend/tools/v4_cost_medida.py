"""
Revisión de COST (30-oct): efecto en vivo de los fallos baratos y generales que entran en la v4, antes (ad178cb9) y
después, sobre las mismas empresas.

    python tools/v4_cost_medida.py --bpa CACHE                      # empresas con el BPA «sin dato» y ≥ 4 ejercicios
    python tools/v4_cost_medida.py CACHE_ANTES CACHE_DESPUES [--out FICHERO.md]

Cachés de `tools/universe_scan.py` (<SIMBOLO>.analysis.json.gz). Dice:
  · hallazgo 2: las empresas con el crecimiento del BPA «sin dato» y ≥ 4 ejercicios de beneficio en EDGAR, antes y
    después; los PEG que cambian (valor, base, no significativo) y su tramo;
  · hallazgo 4: el escalón de las tasas base con un precio crudo por encima de 50 (el único caso que contrae ahora);
  · los cambios de nivel de calidad y de precio, y del margen de seguridad mostrado.
"""
import argparse
import glob
import gzip
import json
import os
import sys

sys.path[:0] = [os.path.join(os.path.dirname(__file__), "..", "lib"), os.path.join(os.path.dirname(__file__), "..")]

EPS = "Crecimiento del BPA"


def _load(cache):
    out = {}
    for f in glob.glob(os.path.join(cache, "*.analysis.json.gz")):
        with gzip.open(f) as fh:
            a = json.load(fh).get("analysis") or {}
        if a.get("symbol"):
            out[a["symbol"]] = a
    return out


def _ni_years(a):
    h = (((a.get("data_provenance") or {}).get("edgar") or {}).get("history") or {}).get("net_income") or {}
    return h.get("years") or 0


def _eps_missing(a):
    return (((a.get("score_coverage") or {}).get("crecimiento") or {}).get("missing_reasons") or {}).get(EPS)


def _eps(a):
    for x in (((a.get("score") or {}).get("breakdown") or {}).get("Crecimiento") or {}).get("adjustments") or []:
        if str(x.get("metric") or "").startswith(EPS):
            return x.get("raw")
    return None


def _peg(a):
    pb = a.get("peg_basis") or {}
    ns = ((a.get("score_coverage") or {}).get("valoracion") or {}).get("not_significant") or {}
    v = (a.get("key_metrics") or {}).get("peg")
    if v is not None:
        return f"{v:.2f}" + (" (propio)" if pb.get("own") else " (fuente)")
    return "n.s." if ns.get("PEG") else "—"


def _peg_band(a):
    from financial_ratios import peg_band
    v = (a.get("key_metrics") or {}).get("peg")
    return None if v is None else peg_band(v)


def _levels(a):
    q, p = a.get("quality") or {}, a.get("price_attractiveness") or {}
    return (f"{q.get('level')} {q.get('score')}", f"{p.get('level')} {p.get('score')}")


def _mos(a):
    for r in (((a.get("display") or {}).get("sections") or {}).get("valuation") or {}).get("intrinsic", {}).get(
            "rows") or []:
        if r.get("key") == "margin_of_safety":
            return r.get("value")
    return None


def candidates(cache):
    rows = {s: a for s, a in _load(cache).items() if _eps_missing(a) and _ni_years(a) >= 4}
    by = {}
    for s, a in rows.items():
        by.setdefault(_eps_missing(a), []).append(s)
    return rows, by


def compare(antes, despues):
    A, D = _load(antes), _load(despues)
    common = sorted(set(A) & set(D))
    out = [f"# Revisión de COST: antes y después ({len(common)} empresas)", ""]
    miss_a = [s for s in common if _eps_missing(A[s]) and _ni_years(A[s]) >= 4]
    miss_d = [s for s in common if _eps_missing(D[s]) and _ni_years(D[s]) >= 4]
    fixed = [s for s in miss_a if s not in miss_d]
    out += [f"## Hallazgo 2 · BPA «sin dato» con ≥ 4 ejercicios de beneficio en EDGAR",
            f"- Antes: **{len(miss_a)}**; después: **{len(miss_d)}**; recuperadas: {len(fixed)}.", ""]
    if fixed:
        out += ["| Empresa | Motivo antes | Crecimiento del BPA después |", "|---|---|---|"]
        out += [f"| {s} | {_eps_missing(A[s])} | {_eps(D[s]):.1%} |" if _eps(D[s]) is not None else
                f"| {s} | {_eps_missing(A[s])} | {_eps_missing(D[s]) or 'n.s.'} |" for s in fixed]
        out.append("")
    if miss_d:
        by = {}
        for s in miss_d:
            by.setdefault(_eps_missing(D[s]), []).append(s)
        out += ["Siguen «sin dato» (por motivo):", ""]
        out += [f"- {why}: {len(ss)} ({', '.join(ss)})" for why, ss in sorted(by.items(), key=lambda x: -len(x[1]))]
        out.append("")
    pegs = [s for s in common if _peg(A[s]) != _peg(D[s])]
    band = [s for s in pegs if _peg_band(A[s]) != _peg_band(D[s])]
    out += ["## Hallazgo 2 · PEG", f"- Cambia el PEG en **{len(pegs)}**; cambia su tramo (o pasa a n.s.) en "
            f"**{len(band)}**.", ""]
    if band:
        out += ["| Empresa | PEG antes | PEG después | Precio (antes → después) |", "|---|---|---|---|"]
        out += [f"| {s} | {_peg(A[s])} | {_peg(D[s])} | {_levels(A[s])[1]} → {_levels(D[s])[1]} |" for s in band]
        out.append("")
    ql = [s for s in common if _levels(A[s])[0].split()[0] != _levels(D[s])[0].split()[0]]
    pl = [s for s in common if _levels(A[s])[1].split()[0] != _levels(D[s])[1].split()[0]]
    out += ["## Niveles", f"- Cambia el nivel de calidad en **{len(ql)}**: {', '.join(ql) or '—'}.",
            f"- Cambia el nivel de precio en **{len(pl)}**: {', '.join(pl) or '—'}.", ""]
    if ql or pl:
        out += ["| Empresa | Calidad | Precio | PEG | Crecimiento del BPA |", "|---|---|---|---|---|"]
        for s in sorted(set(ql) | set(pl)):
            ea, ed = _eps(A[s]), _eps(D[s])
            out.append(f"| {s} | {_levels(A[s])[0]} → {_levels(D[s])[0]} | {_levels(A[s])[1]} → {_levels(D[s])[1]} | "
                       f"{_peg(A[s])} → {_peg(D[s])} | {'—' if ea is None else f'{ea:.1%}'} → "
                       f"{'—' if ed is None else f'{ed:.1%}'} |")
        out.append("")
    br = [s for s in common if (D[s].get("confidence") or {}).get("base_rate_step")]
    hit = [s for s in br if ((D[s].get("confidence") or {}).get("base_rate_step") or {}).get("contracts")]
    out += ["## Hallazgo 4 · el escalón de las tasas base", f"- Con escalón: {len(br)}; contrae ahora (precio crudo > "
            f"50): **{len(hit)}** {', '.join(hit)}.", ""]
    mos = [s for s in common if _mos(A[s]) != _mos(D[s]) and str(_mos(D[s])).startswith(("<", ">"))]
    out += ["## Hallazgo 6 · margen de seguridad acotado", f"- Se muestra acotado en **{len(mos)}**.", ""]
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("caches", nargs="+")
    ap.add_argument("--bpa", action="store_true")
    ap.add_argument("--out")
    args = ap.parse_args(argv)
    if args.bpa:
        rows, by = candidates(args.caches[0])
        print(f"{len(rows)} empresas con el BPA «sin dato» y ≥ 4 ejercicios de beneficio en EDGAR")
        for why, ss in sorted(by.items(), key=lambda x: -len(x[1])):
            print(f"  {len(ss):3d}  {why}: {' '.join(sorted(ss))}")
        return 0
    txt = compare(args.caches[0], args.caches[1])
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(txt + "\n")
    print(txt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
