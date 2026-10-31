"""
F10 · margen operativo: clasificación de los residuos grandes sin cargos identificados (Plan, 29-oct). Solo lectura.

Para cada empresa, contra sus propios estados en SEC EDGAR (companyfacts, crudo), en el corte del análisis guardado:
  · el TTM de nuestro constructor (`sec_edgar.flow_ttm`, con las reglas de fc5b79f7) y la suma de los 4 trimestres
    presentados (3 meses; Q4 = ejercicio − 9 meses). Si no cuadran (> 1 pp de los ingresos): error del constructor (b);
  · el TTM de las etiquetas de cargos y de ventas que la normalización no identifica (deterioros de fondo de comercio e
    intangibles, de activos, reestructuración, litigios, I+D en proceso adquirida, ventas de negocios o activos). Si
    explican la diferencia con la fila trimestral de Yahoo: cargos reales no identificados (a).

    cd backend
    SEC_EDGAR_USER_AGENT="$(security find-generic-password -s finanzer-sec-ua -w)" \\
        ../../finanzer_next/.venv313/bin/python tools/f10_margen_op_residuos.py --cache <caché del escaneo> SYM...

Ritmo ≤ 4 peticiones/s a la SEC.
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

import sec_edgar as edgar  # noqa: E402

# (etiqueta, signo sobre el operativo: +1 = cargo que lo reduce, −1 = ganancia que lo sube)
CHARGE_TAGS = [
    ("GoodwillImpairmentLoss", 1), ("ImpairmentOfIntangibleAssetsExcludingGoodwill", 1),
    ("ImpairmentOfIntangibleAssetsIndefinitelivedExcludingGoodwill", 1),
    ("ImpairmentOfIntangibleAssetsFinitelived", 1), ("GoodwillAndIntangibleAssetImpairment", 1),
    ("AssetImpairmentCharges", 1), ("ImpairmentOfLongLivedAssetsHeldForUse", 1),
    ("ImpairmentOfLongLivedAssetsToBeDisposedOf", 1), ("OtherAssetImpairmentCharges", 1),
    ("ImpairmentOfOilAndGasProperties", 1),
    ("RestructuringCharges", 1), ("RestructuringCosts", 1), ("RestructuringSettlementAndImpairmentProvisions", 1),
    ("BusinessCombinationIntegrationRelatedCosts", 1),
    ("LitigationSettlementExpense", 1), ("LossContingencyLossInPeriod", 1),
    ("ResearchAndDevelopmentInProcess", 1), ("ResearchAndDevelopmentAssetAcquiredOtherThanThroughBusinessCombinationWrittenOff", 1),
    ("GainLossOnSaleOfBusiness", -1), ("GainLossOnDispositionOfAssets", -1),
    ("GainLossOnSaleOfPropertyPlantEquipment", -1), ("DisposalGroupNotDiscontinuedOperationGainLossOnDisposal", -1),
]
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


def _fs(cf, tax, tag, unit):
    return (((cf.get("facts") or {}).get(tax) or {}).get(tag, {}).get("units") or {}).get(unit) or []


def _quarters(fs, cut):
    """Σ de los 4 trimestres que acaban en el corte (3 meses; Q4 = ejercicio − 9 meses), con los ejercicios solo de
    informes anuales y, por periodo, el último presentado."""
    best = {}
    for f in fs:
        if not f.get("start") or (_days(f) > 330 and f.get("form") not in edgar.ANNUAL_FORMS):
            continue
        k = (f["start"], f["end"])
        if k not in best or (f.get("filed") or "") > (best[k].get("filed") or ""):
            best[k] = f
    fs = list(best.values())
    tot, how = 0.0, []
    end = cut
    for _ in range(4):
        q = [f for f in fs if 80 <= _days(f) <= 100 and abs((_d(f["end"]) - end).days) <= 14]
        if q:
            tot += q[0]["val"]
            how.append("3m")
            end = _d(q[0]["start"]) - dt.timedelta(days=1)
            continue
        got = None
        for lg in sorted((f for f in fs if _days(f) > 100 and abs((_d(f["end"]) - end).days) <= 14), key=_days):
            sh = [f for f in fs if f["start"] == lg["start"] and 80 <= _days(lg) - _days(f) <= 100]
            if sh:
                s = max(sh, key=_days)
                got = (lg["val"] - s["val"], _d(s["end"]))
                break
        if got is None:
            return None, how + ["falta"]
        tot += got[0]
        how.append("derivado")
        end = got[1]
    return tot, how


def classify(sym, a, cik_map):
    km = a.get("key_metrics") or {}
    op = (a.get("earnings_normalization") or {}).get("operating") or {}
    cut = ((a.get("data_provenance") or {}).get("as_of") or {}).get("date")
    rev = km.get("revenue")
    out = {"symbol": sym, "cut": cut, "shown": km.get("operating_margin"),
           "yahoo": (op.get("yahoo_quarterly") / rev) if (op.get("yahoo_quarterly") is not None and rev) else None,
           "ttm_type": ((a.get("data_provenance") or {}).get("as_of") or {}).get("type")}
    cik = cik_map.get(sym.replace(".", "-"))
    if not cik or not cut or not rev:
        out["class"] = "sin datos (CIK, corte o ingresos)"
        return out
    cf = _get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json")
    tax = "us-gaap" if "us-gaap" in (cf.get("facts") or {}) and _fs(cf, "us-gaap", "OperatingIncomeLoss", "USD") \
        else "ifrs-full"
    unit = edgar.reporting_unit(cf, edgar.taxonomy(cf)) or "USD"
    oi_tag = "OperatingIncomeLoss" if tax == "us-gaap" else "ProfitLossFromOperatingActivities"
    fs = _fs(cf, tax, oi_tag, unit)
    end = _d(cut)
    b = edgar.flow_ttm(fs, end, 14) if fs else None
    q, how = _quarters(fs, end) if fs else (None, ["sin hechos"])
    out.update(builder=(b or {}).get("value"), builder_how=(b or {}).get("how"), quarters=q, quarters_how=how,
               unit=unit)
    charges = []
    for tag, sign in CHARGE_TAGS:
        cfs = _fs(cf, "us-gaap", tag, unit)
        if not cfs:
            continue
        t = edgar.flow_ttm(cfs, end, 14)
        if t and t["value"]:
            charges.append({"tag": tag, "value": t["value"], "effect": -sign * t["value"]})
    out["charges"] = charges
    yq = op.get("yahoo_quarterly")
    edg = b["value"] if b else None
    out["gap"] = (yq - edg) if (yq is not None and edg is not None) else None
    out["explained"] = -sum(c["effect"] for c in charges)
    if edg is None:
        out["class"] = "sin TTM de EDGAR del corte (el enseñado sale de otra fuente)"
    elif q is not None and abs(edg - q) > 0.01 * rev:
        out["class"] = "(b) error del constructor: TTM ≠ Σ trimestres"
    elif out["gap"] is not None and charges and abs(out["gap"] - out["explained"]) <= 0.03 * rev:
        out["class"] = "(a) cargos reales que la normalización no identifica (las etiquetas los cubren)"
    elif charges:
        out["class"] = "(a) cargos reales, parcialmente cubiertos por las etiquetas"
    else:
        out["class"] = "(a?) EDGAR cuadra con sus trimestres; sin etiquetas de cargos: Yahoo reclasifica"
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("symbols", nargs="+")
    ap.add_argument("--cache", required=True)
    ap.add_argument("--out")
    o = ap.parse_args(argv)
    tick = _get("https://www.sec.gov/files/company_tickers.json")
    cik_map = {v["ticker"].upper(): int(v["cik_str"]) for v in tick.values()}
    res = []
    for s in o.symbols:
        with gzip.open(os.path.join(o.cache, f"{s}.analysis.json.gz")) as fh:
            a = json.load(fh)["analysis"]
        try:
            r = classify(s, a, cik_map)
        except Exception as e:      # una empresa sin companyfacts no para las demás
            r = {"symbol": s, "class": f"error: {type(e).__name__}: {e}"}
        res.append(r)
        rev = (a.get("key_metrics") or {}).get("revenue") or 1
        print(f"{s}: {r.get('class')} | enseñado {r.get('shown')} Yahoo {r.get('yahoo')} | constructor "
              f"{(r.get('builder') or 0) / rev:.3f} Σtrim {((r.get('quarters') or 0) / rev):.3f} {r.get('quarters_how')}"
              f" | etiquetas {[(c['tag'], round(c['value'] / 1e6)) for c in r.get('charges') or []]}", flush=True)
    if o.out:
        with open(o.out, "w", encoding="utf-8") as fh:
            json.dump(res, fh, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
