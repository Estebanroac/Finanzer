"""
Verificación del margen operativo con dos verdades (puerta de la v4, regla `margen_operativo_unico`). Solo lectura.

Para cada empresa, contra los propios estados en SEC EDGAR (companyfacts), los 4 trimestres del TTM del análisis:
  · EDGAR trimestral: el resultado operativo de cada trimestre (el valor de 3 meses; si el emisor no lo presenta, el
    Q4 como ejercicio − 9 meses, dicho), y los ingresos de los mismos trimestres;
  · nuestro constructor (lo que enseña y puntúa key_metrics): ejercicio + acumulado del año − acumulado del año
    anterior (`data_provenance.fields.operatingIncome`), recalculado desde los mismos hechos;
  · Yahoo trimestral: la suma de las 4 filas «Operating Income» (las piezas de N1/N1b).

    cd backend
    SEC_EDGAR_USER_AGENT="$(security find-generic-password -s finanzer-sec-ua -w)" \\
        ../../finanzer_next/.venv313/bin/python tools/verif_margen_operativo.py --cache <caché del escaneo> SYM...

Escribe el detalle en --out (json). Ritmo ≤ 4 peticiones/s a la SEC.
"""
import argparse
import datetime as dt
import gzip
import json
import os
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, "..", "lib"), os.path.join(HERE, "..")]

OP_TAGS = [("us-gaap", "OperatingIncomeLoss"), ("ifrs-full", "ProfitLossFromOperatingActivities")]
REV_TAGS = [("us-gaap", "Revenues"), ("us-gaap", "RevenueFromContractWithCustomerExcludingAssessedTax"),
            ("us-gaap", "SalesRevenueNet"), ("us-gaap", "RevenuesNetOfInterestExpense"), ("ifrs-full", "Revenue")]
_last = [0.0]


def _get(url):
    wait = _last[0] + 0.25 - time.monotonic()
    if wait > 0:
        time.sleep(wait)
    _last[0] = time.monotonic()
    req = urllib.request.Request(url, headers={"User-Agent": os.environ["SEC_EDGAR_USER_AGENT"],
                                               "Accept-Encoding": "gzip"})
    with urllib.request.urlopen(req, timeout=60) as r:
        body = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            body = gzip.decompress(body)
    return json.loads(body)


def _d(s):
    return dt.date.fromisoformat(s[:10])


def _days(f):
    return (_d(f["end"]) - _d(f["start"])).days if f.get("start") else None


def _facts(cf, tax, tag):
    units = ((cf.get("facts") or {}).get(tax) or {}).get(tag, {}).get("units") or {}
    out = []
    for u, fs in units.items():
        out += [dict(f, unit=u) for f in fs]
    return out


ANNUAL_FORMS = ("10-K", "10-K/A", "10-KT", "20-F", "20-F/A", "40-F", "40-F/A")


def _latest(fs, strict=False):
    """Por (start, end), el último presentado (las reexpresiones posteriores mandan). `strict`: un periodo de un
    ejercicio solo de un informe anual (FIX: el 10-Q del Q1 de 2026 etiqueta su trimestre comparativo de 2025 con el
    periodo del ejercicio entero, y por ser posterior al 10-K lo sustituía)."""
    best = {}
    for f in fs:
        if strict and _days(f) and _days(f) > 330 and f.get("form") not in ANNUAL_FORMS:
            continue
        k = (f.get("start"), f["end"])
        if k not in best or (f.get("filed") or "") > (best[k].get("filed") or ""):
            best[k] = f
    return list(best.values())


def _near(a, b, tol=14):
    return abs((_d(a) - _d(b)).days) <= tol


def quarter(fs, end):
    """(valor del trimestre que acaba en `end`, cómo): el de 3 meses; si no, ejercicio − 9 meses (Q4 derivado); o, si
    solo hay acumulados, acumulado − acumulado anterior. Con los ejercicios solo de informes anuales."""
    fs = _latest(fs, strict=True)
    q = [f for f in fs if _days(f) and 80 <= _days(f) <= 100 and _near(f["end"], end)]
    if q:
        return q[0]["val"], "3 meses"
    for long_ in sorted((f for f in fs if _days(f) and _days(f) > 100 and _near(f["end"], end)), key=_days):
        shorter = [f for f in fs if f.get("start") == long_["start"] and _days(f) and
                   80 <= _days(long_) - _days(f) <= 100]
        if shorter:
            s = max(shorter, key=_days)
            return long_["val"] - s["val"], f"{_days(long_)} − {_days(s)} días ({'Q4 derivado' if _days(long_) > 330 else 'acumulados'})"
    return None, "sin dato"


def builder(fs, ends):
    """Nuestro constructor: ejercicio + acumulado − acumulado del año anterior (o la suma si el TTM es un ejercicio)."""
    fs = _latest(fs)
    fys = sorted((f for f in fs if _days(f) and 350 <= _days(f) <= 380), key=lambda f: f["end"], reverse=True)
    cut = ends[0]
    fy = next((f for f in fys if _d(f["end"]) <= _d(cut) + dt.timedelta(days=14)), None)
    if fy is None:
        return None, "sin ejercicio"
    if _near(fy["end"], cut):
        return fy["val"], f"ejercicio {fy['start']}…{fy['end']}"
    ytd = next((f for f in fs if _near(f["end"], cut) and _days(f) and 80 <= _days(f) <= 300
                and _d(f["start"]) > _d(fy["end"])), None)
    if ytd is None:
        return None, "sin acumulado del año"
    prior = next((f for f in fs if _days(f) and abs(_days(f) - _days(ytd)) <= 14
                  and abs((_d(f["end"]) - (_d(ytd["end"]) - dt.timedelta(days=365))).days) <= 14), None)
    if prior is None:
        return None, "sin acumulado del año anterior"
    return (fy["val"] + ytd["val"] - prior["val"],
            f"FY {fy['end']} {fy['val'] / 1e6:.0f} + acumulado {ytd['start']}…{ytd['end']} {ytd['val'] / 1e6:.0f} − "
            f"acumulado {prior['start']}…{prior['end']} {prior['val'] / 1e6:.0f} (presentado {prior.get('filed')})")


def analyze(sym, cache, ciks):
    with gzip.open(os.path.join(cache, f"{sym}.analysis.json.gz"), "rt", encoding="utf-8") as fh:
        a = json.load(fh)["analysis"]
    km = a.get("key_metrics") or {}
    dp = a.get("data_provenance") or {}
    ends = (((dp.get("ttm") or {}).get("quarters") or {}).get("inc") or [])[:4]
    en = a.get("earnings_normalization") or {}
    pieces = next((p for p in (en.get("after_tax"), en.get("coherence")) if p and p.get("operating_income") is not None),
                  {})
    rev = km.get("revenue")
    out = {"symbol": sym, "quarters": ends, "revenue_ttm": rev,
           "shown_margin": km.get("operating_margin"),
           "shown_op": (km.get("operating_margin") or 0) * (rev or 0),
           "shown_source": ((dp.get("fields") or {}).get("operatingIncome") or {}).get("detail"),
           "yahoo_q_op": pieces.get("operating_income"), "yahoo_q_rev": pieces.get("revenue")}
    cik = ciks.get(sym.replace("-", ".").upper()) or ciks.get(sym.upper())
    if not cik:
        out["error"] = "sin CIK"
        return out
    cf = _get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json")
    out["cik"] = cik
    op_tag = next(((t, g) for t, g in OP_TAGS if _facts(cf, t, g)), None)
    out["op_tag"] = f"{op_tag[0]}:{op_tag[1]}" if op_tag else None
    if op_tag and len(ends) == 4:
        fs = _facts(cf, *op_tag)
        qs = [quarter(fs, e) for e in ends]
        out["edgar_quarters"] = [{"end": e, "op": v, "how": h} for e, (v, h) in zip(ends, qs)]
        out["edgar_q_op"] = sum(v for v, _ in qs) if all(v is not None for v, _ in qs) else None
        out["builder_op"], out["builder_how"] = builder(fs, ends)              # como hoy (el último presentado)
        out["builder_strict_op"], out["builder_strict_how"] = builder([f for f in fs if not (
            _days(f) and _days(f) > 330 and f.get("form") not in ANNUAL_FORMS)], ends)
        bad = [f for f in fs if _days(f) and _days(f) > 330 and f.get("form") not in ANNUAL_FORMS
               and f["end"] >= ends[-1][:10] and f["end"] <= ends[0][:10]]
        out["annual_in_quarterly"] = [f"{f['start']}…{f['end']} {f['val'] / 1e6:.0f} en {f.get('form')} "
                                      f"{f.get('fp')} {f.get('fy')} ({f.get('filed')})" for f in bad]
        # las etiquetas con que el emisor presenta cada periodo (si cambia de etiqueta, el constructor mezcla)
        out["op_forms"] = sorted({f"{f.get('form')}:{f.get('fp')}" for f in _latest(fs) if f["end"] >= ends[-1][:10]})
    for t, g in REV_TAGS:
        fs = _facts(cf, t, g)
        if fs and len(ends) == 4:
            qs = [quarter(fs, e) for e in ends]
            if all(v is not None for v, _ in qs):
                out["edgar_q_rev"], out["rev_tag"] = sum(v for v, _ in qs), f"{t}:{g}"
                break
    return out


def verdict(o):
    """Qué fuente acierta frente a los trimestres de EDGAR (± 1 pp de margen)."""
    ref, rev = o.get("edgar_q_op"), o.get("revenue_ttm") or o.get("edgar_q_rev")
    if ref is None or not rev:
        return "sin trimestres de EDGAR"
    ok = {k: abs((o.get(k) or float("nan")) - ref) / rev <= 0.01 for k in ("shown_op", "yahoo_q_op")}
    if ok["shown_op"] and ok["yahoo_q_op"]:
        return "las dos"
    if ok["shown_op"]:
        return "nuestro EDGAR"
    if ok["yahoo_q_op"]:
        return "Yahoo trimestral"
    return "ninguna"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("symbols", nargs="+")
    ap.add_argument("--cache", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    tick = _get("https://www.sec.gov/files/company_tickers.json")
    ciks = {v["ticker"].upper(): int(v["cik_str"]) for v in tick.values()}
    res = []
    for s in args.symbols:
        try:
            o = analyze(s, args.cache, ciks)
        except Exception as e:  # noqa: BLE001
            o = {"symbol": s, "error": f"{type(e).__name__}: {e}"}
        o["verdict"] = verdict(o) if "error" not in o else o["error"]
        res.append(o)
        rev = o.get("revenue_ttm") or o.get("edgar_q_rev") or 0
        f = (lambda x: f"{x / rev:6.1%}" if (x is not None and rev) else "   —  ")
        print(f"{s:6} EDGAR-Q {f(o.get('edgar_q_op'))}  nuestro {f(o.get('shown_op'))}  Yahoo-Q {f(o.get('yahoo_q_op'))}"
              f"  → {o['verdict']}")
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
