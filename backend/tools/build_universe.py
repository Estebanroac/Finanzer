"""
Rediseño E2b (Task 1): genera config/universe.tsv, el universo de la portada (tendencias) y de los rivales preferentes.

    cd finanzer_next/backend
    SEC_EDGAR_USER_AGENT="…" ../.venv313/bin/python tools/build_universe.py [--out config/universe.tsv]

  · S&P 500: la tabla pública de constituyentes (`market.universe.sp500_source`; pandas.read_html), con su sector GICS
    y su CIK. Símbolos en formato Yahoo (BRK.B -> BRK-B).
  · ADR principales: `market.universe.adrs`, con el nombre legal y el país de EDGAR (company_tickers y submissions), y
    su sector GICS de `market.universe.adr_sectors` (P8: la tabla pública solo lo da para el S&P 500).
  · Industria de Damodaran: industry_bench.firm (sin red; la misma función que el motor): por símbolo; un ADR, por su
    nombre legal y su país (y, si no empareja, por el nombre tolerante, solo con coincidencia única); una clase de
    acciones que no figura (GOOG), la de otra clase del mismo CIK (GOOGL).

    ../.venv313/bin/python tools/build_universe.py --sectors-only   # sin red: reaplica los sectores de los ADR al
                                                                    # archivo actual (mismos valores y fecha)

Herramienta local con red (no corre en Render). Si la descarga falla o sale una tabla rara, termina con error y NO
sobrescribe el archivo. Imprime las empresas sin industria de Damodaran.
"""
import argparse
import datetime as dt
import io
import os
import sys
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))

import industry_bench as IB  # noqa: E402
import sec_edgar as edgar  # noqa: E402
import universe  # noqa: E402
from settings import cfg  # noqa: E402

MIN_SP500 = 495       # la tabla trae ~503 líneas (algunas empresas con dos clases); menos: tabla rara, no se escribe


def sp500(url):
    import pandas as pd
    req = urllib.request.Request(url, headers={"User-Agent": "finanzer-build-universe/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        html = r.read().decode("utf-8")
    tables = pd.read_html(io.StringIO(html))
    t = next(t for t in tables if {"Symbol", "Security", "GICS Sector"} <= set(t.columns))
    out = []
    for _, r in t.iterrows():
        cik = r.get("CIK")
        out.append({"symbol": universe.norm_symbol(r["Symbol"]), "name": str(r["Security"]).strip(),
                    "origin": "sp500", "gics_sector": str(r["GICS Sector"]).strip(),
                    "cik": str(int(cik)) if cik == cik and cik is not None else ""})
    return out


def adrs(symbols):
    budget = edgar.Budget(600.0)
    out = []
    for s in symbols:
        hit = edgar.cik_for(s, budget)
        if hit is None:
            raise SystemExit(f"{s}: no está en company_tickers de la SEC")
        country = edgar.submissions(hit["cik"], budget).get("country")
        out.append({"symbol": universe.norm_symbol(s), "name": hit["title"], "origin": "adr",
                    "gics_sector": adr_sector(s), "cik": str(hit["cik"]), "_country": country})
    return out


def adr_sector(symbol):
    """P8: el sector GICS del ADR, de la tabla explícita de config (`market.universe.adr_sectors`). Sin entrada, error:
    ningún valor del universo queda sin sector (la portada lista por sector)."""
    sec = cfg("market.universe.adr_sectors").get(universe.norm_symbol(symbol))
    if not sec:
        raise SystemExit(f"{symbol}: sin sector en market.universe.adr_sectors")
    return sec


def write(rows, out, header):
    tmp = out + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(header + "\n")
        fh.write("\t".join(universe.COLUMNS) + "\n")
        for r in rows:
            fh.write("\t".join(str(r.get(c) or "").replace("\t", " ") for c in universe.COLUMNS) + "\n")
    os.replace(tmp, out)


def sectors_only(out):
    """P8: reaplica los sectores de los ADR al archivo actual sin red (mismos valores, misma cabecera y fecha)."""
    with open(out, encoding="utf-8") as fh:
        header = fh.readline().rstrip("\n")
    universe.UNIVERSE_FILE = out
    universe.reset()
    rows = universe.load()
    for r in rows:
        if r["origin"] == "adr":
            r["gics_sector"] = adr_sector(r["symbol"])
    write(rows, out, header)
    universe.reset()
    miss = [r["symbol"] for r in universe.load() if not r.get("gics_sector")]
    print(f"{len(rows)} valores; sin sector: {' '.join(miss) or 'ninguno'}")


def classify(rows):
    by_cik = {}
    for r in rows:
        f = IB.firm(r["symbol"], r["name"], r.get("_country"))
        r["damodaran_industry"] = f["industry"] if f else ""
        r["damodaran_region"] = f["region"] if f else ("us" if r["origin"] == "sp500" else "")
        if f and r["cik"]:
            by_cik.setdefault(r["cik"], f["industry"])
    for r in rows:               # otra clase de la misma empresa (mismo CIK)
        if not r["damodaran_industry"] and r["cik"] in by_cik:
            r["damodaran_industry"] = by_cik[r["cik"]]
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=universe.UNIVERSE_FILE)
    ap.add_argument("--sectors-only", action="store_true", help="sin red: reaplica los sectores de los ADR")
    a = ap.parse_args()
    if a.sectors_only:
        return sectors_only(a.out)
    U = cfg("market.universe")
    if not edgar.user_agent():
        raise SystemExit("falta SEC_EDGAR_USER_AGENT (nombre y correo) para los ADR")
    try:
        sp = sp500(U["sp500_source"])
    except Exception as e:
        raise SystemExit(f"descarga del S&P 500 fallida ({type(e).__name__}: {e}); no se toca {a.out}")
    if len(sp) < MIN_SP500:
        raise SystemExit(f"la tabla del S&P 500 trae {len(sp)} filas (< {MIN_SP500}); no se toca {a.out}")
    have = {r["symbol"] for r in sp}
    rows = classify(sp + adrs([s for s in U["adrs"] if universe.norm_symbol(s) not in have]))
    rows.sort(key=lambda r: (r["origin"] != "sp500", r["symbol"]))
    write(rows, a.out, f"# GENERADO por tools/build_universe.py el {dt.date.today().isoformat()} desde "
                       f"{U['sp500_source']} (S&P 500) + market.universe.adrs (ADR; nombre de EDGAR; sector de "
                       "market.universe.adr_sectors). Industria: industry_bench.firm")
    miss = [r["symbol"] for r in rows if not r["damodaran_industry"]]
    n = len(rows)
    print(f"{n} valores ({len(sp)} del S&P 500, {n - len(sp)} ADR); con industria de Damodaran: {n - len(miss)} "
          f"({(n - len(miss)) / n:.1%})")
    print("sin industria:", " ".join(miss) or "ninguno")


if __name__ == "__main__":
    main()
