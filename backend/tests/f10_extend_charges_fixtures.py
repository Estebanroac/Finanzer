"""
F10 · margen operativo (Plan, 29-oct): amplía los companyfacts del juego f2b con los conceptos nuevos, como hizo
tests/f3_extend_history_fixtures.py con la historia larga.

Los companyfacts del juego (tests/fixtures/f2b/edgar/companyfacts) están reducidos a los conceptos que el motor leía al
capturarlos. N1/N1b ya solo recortan lo que se puede nombrar (las ganancias de inversiones de EDGAR,
CONCEPTS["investment_gains"]) y la normalización lee los cargos y las ventas con etiquetas estándar (CHARGES_US,
SALES_US y las IFRS). Sin esos hechos, el replay no podría nombrar el recorte de NVDA, que sí se nombra en vivo.

Este script los descarga de la SEC (companyfacts, ≤ 4 peticiones/s) y añade solo:
  · los hechos de esos conceptos que el juego no tiene;
  · presentados hasta la fecha de captura del juego (metadata.json), como el replay;
  · de filings que el juego ya tiene en companyfacts: un filing nuevo haría creer al replay que ya está incorporado y
    dejaría de leer su XBRL pendiente (KO: el semestre de 2026 viene del 10-Q de julio, pendiente en la captura).
El resto de los hechos no se toca.

    cd backend
    SEC_EDGAR_USER_AGENT="$(security find-generic-password -s finanzer-sec-ua -w)" \\
        ../../finanzer_next/.venv313/bin/python tests/f10_extend_charges_fixtures.py [--check]
"""
import gzip
import json
import os
import sys
import time
import urllib.request

import f2b_fixtures as ff
import sec_edgar as edgar

CF_DIR = os.path.join(ff.F2B_DIR, "edgar", "companyfacts")


def concepts():
    """Los conceptos nuevos de F10 y del EBITDA sin amortizaciones operativas (sec_edgar.DA_SPLIT, 30-oct), por
    taxonomía."""
    us = set(edgar.CONCEPTS["investment_gains"][2]) | set(edgar.SALES_US) | {
        c for umb, parts in edgar.CHARGES_US.values() for c in (*umb, *(x for p in parts for x in p))} | {
        c for v in edgar.DA_SPLIT["us-gaap"].values() for c in v}
    ifrs = set(edgar.SALES_IFRS) | {
        c for umb, parts in edgar.CHARGES_IFRS.values() for c in (*umb, *(x for p in parts for x in p))} | {
        c for v in edgar.DA_SPLIT["ifrs-full"].values() for c in v}
    return {"us-gaap": us, "ifrs-full": ifrs}


def _until():
    meta = json.load(open(os.path.join(ff.F2B_DIR, "metadata.json"), encoding="utf-8"))
    return str(meta.get("captured_at_utc") or "")[:10] or None


_last = [0.0]


def _get(cik):
    wait = _last[0] + 0.25 - time.monotonic()
    if wait > 0:
        time.sleep(wait)
    _last[0] = time.monotonic()
    req = urllib.request.Request(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json",
                                 headers={"User-Agent": os.environ["SEC_EDGAR_USER_AGENT"], "Accept-Encoding": "gzip"})
    with urllib.request.urlopen(req, timeout=60) as r:
        body = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            body = gzip.decompress(body)
    return json.loads(body)


def extend(fixture, raw, until, wanted):
    added = 0
    known = {f.get("accn") for cs in (fixture.get("facts") or {}).values() for node in cs.values()
             for fs in node.get("units", {}).values() for f in fs}
    for tx, names in wanted.items():
        for c in sorted(names):
            node = (raw.get("facts") or {}).get(tx, {}).get(c)
            if not node:
                continue
            dst = fixture.setdefault("facts", {}).setdefault(tx, {}).setdefault(c, {"units": {}})
            for u, fs in node["units"].items():
                lst = dst["units"].setdefault(u, [])
                keys = {(f.get("start"), f["end"], f.get("accn"), f.get("val")) for f in lst}
                for f in fs:
                    if (until and f.get("filed", "") > until) or f.get("accn") not in known:
                        continue
                    g = {k: f[k] for k in edgar._FACT_KEYS if f.get(k) is not None}
                    k = (g.get("start"), g["end"], g.get("accn"), g.get("val"))
                    if k not in keys:
                        lst.append(g)
                        keys.add(k)
                        added += 1
                lst.sort(key=lambda f: (f["end"], f.get("start") or "", f.get("filed") or ""))
    return added


def main(argv=None):
    check = "--check" in (argv or sys.argv[1:])
    until, wanted = _until(), concepts()
    total = 0
    for name in sorted(os.listdir(CF_DIR)):
        path = os.path.join(CF_DIR, name)
        try:
            fixture = json.load(open(path, encoding="utf-8"))
        except ValueError:
            continue                # «companyfacts: 404 en la captura»: el emisor sin hechos se queda así
        raw = _get(name.replace("CIK", "").replace(".json", ""))
        n = extend(fixture, raw, until, wanted)
        total += n
        print(f"{name}: {n} hechos nuevos", flush=True)
        if n and not check:
            ff._write(path, fixture)
    print(f"total: {total} hechos nuevos ({'solo cuenta' if check else 'escritos'}; hasta {until})")


if __name__ == "__main__":
    main()
