"""
EBITDA con el D&A de EDGAR: qué conceptos de D&A usa cada emisor (sondeo para decidir la regla).

    SEC_EDGAR_USER_AGENT=… python tools/v4_ebitda_da_probe.py CACHE_DESPUES SIMBOLOS > sondeo.json

Por empresa, en el corte del análisis guardado: el D&A TTM de la fuente (Yahoo, flujo de caja trimestral: total,
«Depreciation» y «Amortization Of Intangibles») y el de EDGAR de cada concepto (us-gaap): el paraguas
(DepreciationDepletionAndAmortization, DepreciationAndAmortization, DepreciationAmortizationAndAccretionNet), la
depreciación sola y la amortización de intangibles adquiridos.
"""
import datetime as dt
import gzip
import json
import os
import sys
import time
import urllib.request

sys.path[:0] = [os.path.join(os.path.dirname(__file__), "..", "lib"), os.path.join(os.path.dirname(__file__), "..")]
import sec_edgar as edgar  # noqa: E402

CONCEPTS = ("DepreciationDepletionAndAmortization", "DepreciationAndAmortization",
            "DepreciationAmortizationAndAccretionNet", "Depreciation", "AmortizationOfIntangibleAssets",
            "DepreciationAmortizationAndOther")


def _cf(sym):
    import yfinance as yf
    q = yf.Ticker(sym).quarterly_cashflow
    out = {}
    for r in ("Depreciation And Amortization", "Depreciation", "Amortization Of Intangibles"):
        if r in q.index:
            v = [x for x in q.loc[r].tolist()[:4]]
            out[r] = sum(v) if len(v) == 4 and all(x == x for x in v) else None
    return out


def main():
    cache, syms = sys.argv[1], sys.argv[2].split(",")
    tickers = None
    out = {}
    for s in syms:
        a = json.load(gzip.open(os.path.join(cache, f"{s}.analysis.json.gz")))["analysis"]
        prim = a["data_provenance"]["edgar"]["primary"]
        cut = next((x["period_end"] for x in prim.get("cut") or []), None) or (a.get("data_provenance") or {}).get(
            "as_of", {}).get("date")
        cik = (a.get("data_provenance") or {}).get("edgar", {}).get("cik")
        rec = {"cut": cut, "revenue": (a.get("key_metrics") or {}).get("revenue"),
               "gross_margin": (a.get("key_metrics") or {}).get("gross_margin"),
               "operating_income": (a.get("key_metrics") or {}).get("operating_income"), "edgar": {}}
        try:
            rec["yahoo"] = _cf(s)
        except Exception as e:
            rec["yahoo"] = {"error": str(e)}
        if cik and cut:
            time.sleep(0.3)
            req = urllib.request.Request(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{int(cik):010d}.json",
                                         headers={"User-Agent": os.environ["SEC_EDGAR_USER_AGENT"],
                                                  "Accept-Encoding": "gzip"})
            body = urllib.request.urlopen(req, timeout=60).read()
            try:
                body = gzip.decompress(body)
            except OSError:
                pass
            f = json.loads(body)["facts"].get("us-gaap", {})
            for c in CONCEPTS:
                fs = [x for u in (f.get(c) or {}).get("units", {}).values() for x in u]
                r = edgar.flow_ttm(fs, dt.date.fromisoformat(cut), 14) if fs else None
                rec["edgar"][c] = r["value"] if r else None
        out[s] = rec
        print(s, file=sys.stderr, flush=True)
    json.dump(out, sys.stdout, indent=1)


if __name__ == "__main__":
    main()
