"""
El D&A del EBITDA sin amortizaciones de activos operativos recurrentes (escalera de márgenes de NFLX, 30-oct): efecto en
vivo sobre el universo.

    python tools/v4_ebitda_medida.py CACHE_DESPUES [--antes CACHE_ANTES] [--out FICHERO.md]
    python tools/v4_ebitda_medida.py CACHE_DESPUES --lista [--control N]    # afectadas (+ N de control) para el «antes»

Cachés de `tools/universe_scan.py` (<SIMBOLO>.analysis.json.gz). Del registro de EDGAR del «después»
(data_provenance.edgar.primary.da, lib/edgar_primary._da_reconcile) saca:
  · cuántas empresas tienen la amortización de intangibles de la fuente respaldada por EDGAR, cuántas no verificable
    (por debajo de la materialidad de N1 o sin etiquetas) y a cuáles se les quita del EBITDA;
  · con el «antes» (las afectadas y las de control), qué cambia: margen EBITDA, EV/EBITDA, nivel de precio y de calidad;
  · el invariante del mecanismo (model_invariants.ebitda_sin_amortizacion_operativa) sobre todo el universo.
"""
import argparse
import collections
import glob
import gzip
import json
import os
import random
import sys

sys.path[:0] = [os.path.join(os.path.dirname(__file__), "..", "lib"), os.path.join(os.path.dirname(__file__), "..")]


def _load(cache, only=None):
    out = {}
    for f in glob.glob(os.path.join(cache, "*.analysis.json.gz")):
        sym = os.path.basename(f).split(".analysis")[0]
        if only is not None and sym not in only:
            continue
        with gzip.open(f) as fh:
            a = json.load(fh).get("analysis") or {}
        if a.get("symbol"):
            out[a["symbol"]] = a
    return out


def _da(a):
    return ((((a.get("data_provenance") or {}).get("edgar") or {}).get("primary") or {}).get("da")) or {}


def _rev(a):
    return (a.get("key_metrics") or {}).get("revenue")


def affected(D):
    return sorted(s for s, a in D.items() if _da(a).get("status") == "excluido")


def report(despues, antes):
    import model_invariants as inv
    D = _load(despues)
    by = collections.Counter(_da(a).get("status") or "sin desglose" for a in D.values())
    hit = affected(D)
    nv = sorted((s for s, a in D.items() if _da(a).get("status") == "no_verificable" and _da(a).get("support") is not None
                 and _rev(a)), key=lambda s: -(_da(D[s])["unsupported"] / abs(_rev(D[s]))))
    out = [f"# El D&A del EBITDA sin amortizaciones de activos operativos recurrentes ({len(D)} empresas)", "",
           "Estado de la amortización de intangibles del D&A de la fuente (data_provenance.edgar.primary.da):", ""]
    out += [f"- {k}: **{v}**" for k, v in by.most_common()]
    out += ["", f"## Quitada del EBITDA (sin respaldo en EDGAR y > materialidad de N1): {len(hit)}", "",
            "| Empresa | Amortización de la fuente (B) | Respaldo en EDGAR (B) | Quitada (B) | % de los ingresos |",
            "|---|---|---|---|---|"]
    for s in hit:
        d = _da(D[s])
        out.append(f"| {s} | {d['amortization'] / 1e9:.2f} | {d['support'] / 1e9:.2f} | {d['excluded'] / 1e9:.2f} | "
                   f"{d['excluded'] / abs(_rev(D[s])):.1%} |")
    out += ["", f"## No verificable con respaldo medido (por debajo de la materialidad; no se toca): {len(nv)}", ""]
    out.append(", ".join(f"{s} ({_da(D[s])['unsupported'] / abs(_rev(D[s])):.1%})" for s in nv) or "—")
    out.append("")
    if antes:
        A = _load(antes)
        common = sorted(set(A) & set(D))
        out += [f"## Antes (46a9b78f) y después: {len(common)} empresas (las afectadas y las de control)", "",
                "| Empresa | Margen EBITDA | EV/EBITDA | Precio | Calidad |", "|---|---|---|---|---|"]
        g = lambda v, p=False: "—" if v is None else (f"{v:.1%}" if p else f"{v:.1f}x")   # noqa: E731
        changed = []
        for s in common:
            ka, kd = A[s].get("key_metrics") or {}, D[s].get("key_metrics") or {}
            pa, pd = A[s].get("price_attractiveness") or {}, D[s].get("price_attractiveness") or {}
            qa, qd = A[s].get("quality") or {}, D[s].get("quality") or {}
            lv = pa.get("level") != pd.get("level") or qa.get("level") != qd.get("level")
            if lv:
                changed.append(s)
            out.append(f"| {s}{' (afectada)' if s in hit else ''}{' **cambia de nivel**' if lv else ''} | "
                       f"{g(ka.get('ebitda_margin'), 1)} → {g(kd.get('ebitda_margin'), 1)} | "
                       f"{g(ka.get('ev_ebitda'))} → {g(kd.get('ev_ebitda'))} | {pa.get('level')} {pa.get('score')} → "
                       f"{pd.get('level')} {pd.get('score')} | {qa.get('level')} {qa.get('score')} → {qd.get('level')} "
                       f"{qd.get('score')} |")
        out += ["", f"Cambian de nivel: **{len(changed)}** ({', '.join(changed) or '—'}).", ""]
    fy = {s: [x for x in ((((a.get("data_provenance") or {}).get("edgar") or {}).get("primary") or {}).get("da_fy") or [])
              if x.get("status") == "excluido"] for s, a in D.items()}
    fy = {s: v for s, v in fy.items() if v}
    cyc = sorted(s for s in fy if (D[s].get("classification") or {}).get("archetype") == "CYCLICAL")
    out += [f"## Filas anuales: ejercicios con la amortización quitada del EBITDA: {len(fy)} empresas", ""]
    out += [f"- {s}: " + ", ".join(f"{x['fy_end'][:4]} {x['excluded'] / 1e9:.2f} B" for x in v) for s, v in sorted(fy.items())]
    out += ["", f"Cíclicas entre ellas (EV/EBITDA normalizado con el EBITDA medio anual): {', '.join(cyc) or 'ninguna'}.", ""]
    capped = sorted(s for s, a in D.items() if ((a.get("key_metrics") or {}).get("ev_ebitda") or 0) >
                    __import__("settings").cfg("thresholds.multiples_display.ev_ebitda_shown_max"))
    out += [f"## EV/EBITDA mostrado como «> 100x» (EBITDA casi nulo): {len(capped)}", "", ", ".join(capped) or "—", ""]
    res = collections.Counter()
    bad = []
    for s, a in D.items():
        r = inv.ebitda_sin_amortizacion_operativa(a, {})
        res[r["state"]] += 1
        if r["state"] == inv.VIOLATION:
            bad.append(s)
    out += ["## Invariante ebitda_sin_amortizacion_operativa", "",
            ", ".join(f"{k}: {v}" for k, v in res.most_common()) + f". Violaciones: {', '.join(bad) or 'ninguna'}.", ""]
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("despues")
    ap.add_argument("--antes")
    ap.add_argument("--lista", action="store_true")
    ap.add_argument("--control", type=int, default=20)
    ap.add_argument("--out")
    args = ap.parse_args(argv)
    if args.lista:
        D = _load(args.despues)
        hit = affected(D)
        pool = sorted(s for s, a in D.items() if s not in hit and _da(a).get("status") in ("respaldado", "no_verificable"))
        random.seed(7)
        print(",".join(hit + random.sample(pool, min(args.control, len(pool)))))
        return 0
    txt = report(args.despues, args.antes)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(txt + "\n")
    print(txt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
