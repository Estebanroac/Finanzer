"""
Fase 7 (PLAN §4, punto 3): datos del estudio de calibración histórica. CON RED: SEC EDGAR y Yahoo.

    cd finanzer_next/backend
    SEC_EDGAR_USER_AGENT="<nombre correo>" ../.venv313/bin/python tests/calibracion_datos.py --out ~/Downloads/finanzer_calibracion

Qué baja (una vez; lo ya bajado no se repite):
  · SEC EDGAR: la tabla de tickers, y por emisor `companyfacts` (reducido a los conceptos que usan el motor y el
    generador de estados) y `submissions` (filings). ≤ 6.7 peticiones/s (la SEC admite 10/s), User-Agent del entorno.
  · Yahoo: la serie diaria desde 2009 (sin ajustar, con el cierre ajustado, dividendos y splits) de cada empresa, del
    S&P 500, de SPY, de los ETF de sector y de ^TNX; y la respuesta de la búsqueda (sector e industria).
Formato: el de los fixtures (tests/f2b_fixtures.py y tests/history_fixtures.py), para que el replay del motor los lea.
"""
import argparse
import json
import os
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fixture_backend  # noqa: E402,F401  (rutas de lib)
import history_fixtures as hf  # noqa: E402

# 100 empresas de EE. UU. fuera del panel, con 10-K en XBRL desde 2011 y sin cambio de CIK (se excluyen sucesiones:
# GOOGL, MDT, RTX, LIN, ABBV, KHC, PYPL). Sesgo de supervivencia: son las que existen hoy (se declara en el informe).
UNIVERSE = {
    "tecnologia": ["ORCL", "IBM", "CSCO", "INTC", "TXN", "QCOM", "ADBE", "CRM", "INTU", "ADP", "ACN", "HPQ", "AMAT",
                   "ADI"],
    "consumo_defensivo": ["PEP", "COST", "WMT", "MDLZ", "CL", "KMB", "GIS", "HSY", "KR", "SYY", "MO"],
    "consumo_ciclico": ["HD", "LOW", "MCD", "YUM", "NKE", "SBUX", "TGT", "TJX", "ROST", "BKNG", "EBAY"],
    "salud": ["UNH", "CVS", "PFE", "MRK", "ABT", "AMGN", "GILD", "BMY", "LLY", "SYK", "TMO", "DHR"],
    "industriales": ["HON", "MMM", "GE", "UNP", "CSX", "UPS", "LMT", "DE", "ITW", "EMR", "WM", "FDX"],
    "energia": ["CVX", "COP", "SLB", "EOG", "OXY", "VLO", "HAL"],
    "materiales": ["APD", "ECL", "NEM", "SHW", "NUE"],
    "utilities": ["SO", "D", "AEP", "EXC", "XEL", "SRE"],
    "inmobiliario": ["SPG", "PSA", "EQR", "AVB", "WELL"],
    "financiero": ["WFC", "C", "USB", "PNC", "GS", "MS", "AXP", "MET", "PRU", "AFL", "TRV", "ALL"],
    "comunicacion": ["T", "VZ", "CMCSA", "DIS", "META"],
}
TICKERS = [t for v in UNIVERSE.values() for t in v]
REFERENCE = ["^GSPC", "SPY", "XLK", "XLF", "VNQ", "XLY", "XLP", "XLE", "XLU", "XLV", "XLI", "XLB", "XLC", "^TNX"]
START = "2009-01-01"

# Conceptos que guarda el reducido: los del motor (sec_edgar._WANTED) y los que el generador necesita para los
# estados con forma de Yahoo (tests/calibracion_generar.py).
EXTRA = {"us-gaap": {
    "EarningsPerShareDiluted", "EarningsPerShareBasic", "WeightedAverageNumberOfDilutedSharesOutstanding",
    "WeightedAverageNumberOfSharesOutstandingBasic", "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
    "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments",
    "IncomeTaxExpenseBenefit", "SellingGeneralAndAdministrativeExpense", "CostOfRevenue", "CostOfGoodsAndServicesSold",
    "CashAndCashEquivalentsAtCarryingValue", "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
    "ShortTermInvestments", "AvailableForSaleSecuritiesDebtSecuritiesCurrent", "MarketableSecuritiesCurrent",
    "LongTermDebt", "LongTermDebtNoncurrent", "LongTermDebtCurrent", "DebtCurrent", "ShortTermBorrowings",
    "CommercialPaper", "LongTermDebtAndCapitalLeaseObligations", "Goodwill", "IntangibleAssetsNetExcludingGoodwill",
    "ShareBasedCompensation", "AllocatedShareBasedCompensationExpense", "CommonStockSharesOutstanding",
    "PaymentsForRepurchaseOfCommonStock", "NetIncomeLossAvailableToCommonStockholdersBasic",
    "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest", "InterestExpense",
    "DepreciationDepletionAndAmortization", "InterestIncomeExpenseNonoperatingNet", "InvestmentIncomeInterest",
    "NoninterestIncome", "InterestIncomeExpenseNet", "Revenues",
    # deuda de los REIT (calibracion_bandas.py): O da NotesPayable + LoansPayable; otros, DebtInstrumentCarryingAmount
    "NotesPayable", "LoansPayable", "NotesAndLoansPayable", "DebtInstrumentCarryingAmount", "LineOfCredit",
    "UnsecuredDebt", "SecuredDebt", "SeniorNotes"},
    "dei": {"EntityCommonStockSharesOutstanding"}}

_last = [0.0]


def _sec_get(url, ua, min_interval=0.15):
    wait = _last[0] + min_interval - time.monotonic()
    if wait > 0:
        time.sleep(wait)
    _last[0] = time.monotonic()
    req = urllib.request.Request(url, headers={"User-Agent": ua, "Accept-Encoding": "identity"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def _reduce(raw):
    import sec_edgar as edgar
    keep = {tx: set(names) | EXTRA.get(tx, set()) for tx, names in edgar._WANTED.items()}
    keep["dei"] = EXTRA["dei"]
    out = {"cik": raw.get("cik"), "entityName": raw.get("entityName"), "facts": {}}
    for tx, names in keep.items():
        cs = (raw.get("facts") or {}).get(tx) or {}
        for c in sorted(names):
            node = cs.get(c)
            if node:
                out["facts"].setdefault(tx, {})[c] = {"units": {
                    u: [{k: f[k] for k in edgar._FACT_KEYS if f.get(k) is not None} for f in fs]
                    for u, fs in (node.get("units") or {}).items()}}
    return out


def _write(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, separators=(",", ":"))


def fetch_edgar(out, ua, tickers, force=False):
    import sec_edgar as edgar
    tpath = os.path.join(out, "edgar", "company_tickers.json")
    if not os.path.isfile(tpath):
        raw = _sec_get(edgar.TICKERS_URL, ua)
        table = {v["ticker"].upper(): {"cik": v["cik_str"], "title": v.get("title")} for v in raw.values()}
        _write(tpath, table)
    table = json.load(open(tpath))
    for i, t in enumerate(tickers):
        cik = (table.get(t) or {}).get("cik")
        if not cik:
            print(f"  {t}: sin CIK", flush=True)
            continue
        name = f"CIK{int(cik):010d}.json"
        fpath = os.path.join(out, "edgar", "companyfacts", name)
        if force or not os.path.isfile(fpath):
            raw = _sec_get(f"https://data.sec.gov/api/xbrl/companyfacts/{name}", ua)
            _write(fpath, _reduce(raw) if raw else {"facts": {}})
        spath = os.path.join(out, "edgar", "submissions", name)
        if not os.path.isfile(spath):
            sub = _sec_get(f"https://data.sec.gov/submissions/{name}", ua)
            _write(spath, sub or {"filings": {"recent": {}}})
        print(f"  EDGAR {i + 1}/{len(tickers)} {t}", flush=True)


def fetch_yahoo(out, symbols):
    import price_history
    import yfinance as yf
    for i, s in enumerate(symbols):
        path = hf.series_file(s, out)
        if not os.path.isfile(path):
            raw = yf.Ticker(s).history(start=START, interval="1d", auto_adjust=False, actions=True)
            frame = price_history.normalize(raw)
            if frame is None:
                print(f"  Yahoo {s}: sin serie", flush=True)
                continue
            hf.save(s, frame, out)
            time.sleep(0.4)
        print(f"  Yahoo {i + 1}/{len(symbols)} {s}", flush=True)


def fetch_search(out, tickers):
    import yf_adapter as ya
    for t in tickers:
        path = os.path.join(out, "search", f"{t}.json")
        if os.path.isfile(path):
            continue
        ya._ensure_session()
        params = {"q": t, "quotesCount": 5, "newsCount": 0, "listsCount": 0}
        r = ya._session.get("https://query2.finance.yahoo.com/v1/finance/search", params=params, timeout=10)
        _write(path, {"params": params, "status": r.status_code, "body_json": r.json() if r.status_code == 200 else None})
        time.sleep(0.4)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = os.path.expanduser(a.out)
    ua = os.environ.get("SEC_EDGAR_USER_AGENT", "").strip()
    if not ua:
        sys.exit("falta SEC_EDGAR_USER_AGENT en el entorno")
    fetch_edgar(out, ua, TICKERS)
    fetch_search(out, TICKERS)
    fetch_yahoo(out, TICKERS + REFERENCE)
    _write(os.path.join(out, "metadata.json"), {"universe": UNIVERSE, "reference": REFERENCE, "start": START,
                                                "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%S")})
    print("hecho", flush=True)


if __name__ == "__main__":
    main()
