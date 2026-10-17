"""
Fase 7 (PLAN §4, punto 3): fixtures POINT-IN-TIME para pasar el motor real por fechas pasadas. Sin red.

    cd finanzer_next/backend
    ../.venv313/bin/python tests/calibracion_generar.py --data ~/Downloads/finanzer_calibracion

Para cada empresa y ejercicio FY (2012–2021), la fecha D es el día siguiente a la presentación de su 10-K. El fixture
contiene solo lo que se sabía ese día:
  · estados anuales con forma de Yahoo (4 ejercicios hasta FY), construidos con los hechos XBRL de EDGAR presentados
    hasta D (el valor más reciente presentado hasta D para cada periodo: las reexpresiones posteriores no entran);
  · sin estados trimestrales (D es el cierre del ejercicio: el corte del análisis es el FY);
  · cotización: el cierre sin ajustar de D, las acciones de la portada del 10-K (dei) y la serie de 2 años hasta D de
    la empresa, del S&P 500 y del ETF de su sector;
  · EDGAR (companyfacts y la lista de filings) cortado en D por el replay (tests/f2b_fixtures.py), con una lista de
    filings periódicos reconstruida de los hechos (la de la SEC solo guarda los ~1000 últimos);
  · sector e industria de la búsqueda de Yahoo de hoy (no hay histórico: se declara).
Salida: <data>/fixtures/FY<año>/<TICKER>/ (formato de tests/fixtures/panel) y <data>/edgar_pit/ (para el replay).
"""
import argparse
import datetime as _dt
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fixture_backend as fb  # noqa: E402
import history_fixtures as hf  # noqa: E402

FYS = range(2012, 2022)
SECTOR_ETF = {"Technology": "XLK", "Financial Services": "XLF", "Real Estate": "VNQ", "Consumer Cyclical": "XLY",
              "Consumer Defensive": "XLP", "Energy": "XLE", "Utilities": "XLU", "Healthcare": "XLV",
              "Industrials": "XLI", "Basic Materials": "XLB", "Communication Services": "XLC"}

# Fila de Yahoo -> conceptos us-gaap (el primero que tenga el periodo manda). Signo: el de Yahoo.
FLOW = {
    "Total Revenue": ("Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax",
                      "RevenueFromContractWithCustomerIncludingAssessedTax", "SalesRevenueNet", "SalesRevenueGoodsNet",
                      "RevenuesNetOfInterestExpense", "RegulatedAndUnregulatedOperatingRevenue",
                      "OperatingLeasesIncomeStatementLeaseRevenue"),
    "Cost Of Revenue": ("CostOfRevenue", "CostOfGoodsAndServicesSold"),
    "Gross Profit": ("GrossProfit",),
    "Operating Income": ("OperatingIncomeLoss",),
    "Pretax Income": ("IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
                      "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments"),
    "Tax Provision": ("IncomeTaxExpenseBenefit",),
    "Net Income": ("NetIncomeLoss",),
    "Net Income Common Stockholders": ("NetIncomeLossAvailableToCommonStockholdersBasic", "NetIncomeLoss"),
    "Interest Expense": ("InterestExpense", "InterestExpenseNonoperating", "InterestExpenseDebt", "InterestAndDebtExpense"),
    "Selling General And Administration": ("SellingGeneralAndAdministrativeExpense",),
    "Net Non Operating Interest Income Expense": ("InterestIncomeExpenseNonoperatingNet",),
    "Diluted EPS": ("EarningsPerShareDiluted",),
    "Basic EPS": ("EarningsPerShareBasic",),
    "Diluted Average Shares": ("WeightedAverageNumberOfDilutedSharesOutstanding",),
    "Basic Average Shares": ("WeightedAverageNumberOfSharesOutstandingBasic",),
}
CASH_FLOW = {
    "Operating Cash Flow": (1, ("NetCashProvidedByUsedInOperatingActivities",
                                "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations")),
    "Capital Expenditure": (-1, ("PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsToAcquireProductiveAssets")),
    "Depreciation And Amortization": (1, ("DepreciationDepletionAndAmortization", "DepreciationAndAmortization",
                                          "DepreciationAmortizationAndAccretionNet", "Depreciation")),
    "Common Stock Dividend Paid": (-1, ("PaymentsOfDividendsCommonStock", "PaymentsOfDividends")),
    "Stock Based Compensation": (1, ("ShareBasedCompensation", "AllocatedShareBasedCompensationExpense")),
    "Repurchase Of Capital Stock": (-1, ("PaymentsForRepurchaseOfCommonStock",)),
}
STOCK = {
    "Total Assets": ("Assets",),
    "Current Assets": ("AssetsCurrent",),
    "Current Liabilities": ("LiabilitiesCurrent",),
    "Total Liabilities Net Minority Interest": ("Liabilities",),
    "Stockholders Equity": ("StockholdersEquity",),
    "Total Equity Gross Minority Interest": ("StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
                                             "StockholdersEquity"),
    "Retained Earnings": ("RetainedEarningsAccumulatedDeficit",),
    "Inventory": ("InventoryNet",),
    "Cash And Cash Equivalents": ("CashAndCashEquivalentsAtCarryingValue",
                                  "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"),
    "Goodwill": ("Goodwill",),
    "Other Intangible Assets": ("IntangibleAssetsNetExcludingGoodwill",),
    "Commercial Paper": ("CommercialPaper",),
}
ST_INVEST = ("ShortTermInvestments", "MarketableSecuritiesCurrent", "AvailableForSaleSecuritiesDebtSecuritiesCurrent")


def _d(s):
    return _dt.date.fromisoformat(s)


def _facts(facts, concept, unit_pred=None, tx="us-gaap"):
    node = ((facts.get("facts") or {}).get(tx) or {}).get(concept) or {}
    out = []
    for u, fs in (node.get("units") or {}).items():
        if unit_pred is None or unit_pred(u):
            out += fs
    return out


def _usd(u):
    return u == "USD"


def _pick(fs, end, until, flow):
    """El valor del periodo (flujo: ≈ 1 año que acaba en `end`; saldo: a `end`), del filing más reciente hasta `until`."""
    best = None
    for f in fs:
        if f.get("filed", "9999") > until or abs((_d(f["end"]) - end).days) > 7:
            continue
        if flow:
            if not f.get("start") or not 350 <= (_d(f["end"]) - _d(f["start"])).days <= 380:
                continue
        elif f.get("start"):
            continue
        if best is None or (f["filed"], f.get("accn", "")) > (best["filed"], best.get("accn", "")):
            best = f
    return None if best is None else float(best["val"])


def _row(facts, concepts, end, until, flow, unit=_usd):
    for c in concepts:
        v = _pick(_facts(facts, c, unit), end, until, flow)
        if v is not None:
            return v
    return None


ANNUAL_FLOW = ("NetIncomeLoss", "ProfitLoss", "NetCashProvidedByUsedInOperatingActivities",
               "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations") + FLOW["Total Revenue"]


def _annual_ends(facts, until=None):
    """{fin de ejercicio: primera presentación en 10-K} de flujos ANUALES (350–380 días) presentados en 10-K.
    Revisión de F7 (hallazgo 4): las fechas de Assets de un 10-K incluyen saldos trimestrales (BMY) y de apertura
    (CVS 2019-01-01), y los ejercicios de 52/53 semanas daban dos cierres del mismo año (CSCO 07-28/07-29)."""
    out = {}
    for c in ANNUAL_FLOW:
        for f in _facts(facts, c, _usd):
            if f.get("form") not in ("10-K", "10-K/A") or not f.get("start"):
                continue
            if not 350 <= (_d(f["end"]) - _d(f["start"])).days <= 380 or (until and f.get("filed", "9999") > until):
                continue
            if f["end"] not in out or f["filed"] < out[f["end"]]:
                out[f["end"]] = f["filed"]
    keep = {}
    for e in sorted(out, reverse=True):                 # un ejercicio = un cierre (± 20 días)
        if all(abs((_d(e) - _d(k)).days) > 20 for k in keep):
            keep[e] = out[e]
    return keep


def fiscal_years(facts, until):
    """Cierres de ejercicio presentados en 10-K hasta `until`, del más reciente al más viejo."""
    return sorted(_annual_ends(facts, until), reverse=True)


def tenk_filing(facts, fy):
    """(fin del ejercicio, fecha del 10-K que lo presentó por primera vez) del ejercicio que acaba en el año `fy`.
    Revisión de F7 (hallazgo 4): solo si ese 10-K llegó en los 120 días siguientes al cierre (si no, la fecha sería la
    de un 10-K posterior que solo lo repite como comparativo: DE 2015 con D en 2017)."""
    ends = {e: f for e, f in _annual_ends(facts).items() if e[:4] == str(fy)}
    for e in sorted(ends, reverse=True):
        if (_d(ends[e]) - _d(e)).days <= 120:
            return e, ends[e]
    return None


def statements(facts, fy_end, until, n=4, reit_debt=False):
    """(income_stmt, balance_sheet, cashflow) con forma de yfinance: filas de Yahoo, columnas = cierres de ejercicio."""
    import pandas as pd
    ends = [e for e in fiscal_years(facts, until) if e <= fy_end.isoformat()][:n]
    cols = [pd.Timestamp(e) for e in ends]
    inc, bs, cf = {}, {}, {}
    ebit_proxy = []
    for e, c in zip(ends, cols):
        end = _d(e)
        col = {}
        for row, concepts in FLOW.items():
            unit = (lambda u: u == "USD/shares") if row.endswith("EPS") else \
                ((lambda u: u == "shares") if row.endswith("Shares") else _usd)
            col[row] = _row(facts, concepts, end, until, True, unit)
        if col["Gross Profit"] is None and col["Total Revenue"] is not None and col["Cost Of Revenue"] is not None:
            col["Gross Profit"] = col["Total Revenue"] - col["Cost Of Revenue"]
        if col["Interest Expense"] is not None:
            col["Interest Expense"] = abs(col["Interest Expense"])
        # Muchos emisores no etiquetan OperatingIncomeLoss (IBM, MRK, NKE, ADP); Yahoo construye su "Operating Income".
        # Respaldo: EBIT ≈ beneficio antes de impuestos + gastos financieros (incluye lo no operativo; se registra).
        if col["Operating Income"] is None and col["Pretax Income"] is not None:
            col["Operating Income"] = col["Pretax Income"] + (col["Interest Expense"] or 0.0)
            ebit_proxy.append(e)
        inc[c] = col
        bcol = {row: _row(facts, concepts, end, until, False) for row, concepts in STOCK.items()}
        cash = bcol["Cash And Cash Equivalents"]
        sti = _row(facts, ST_INVEST, end, until, False)
        bcol["Cash Cash Equivalents And Short Term Investments"] = (cash + (sti or 0.0)) if cash is not None else None
        # Deuda: las etiquetas varían por emisor (CSX y WM dan el total con arrendamientos; ACN, la no corriente con
        # arrendamientos y la corriente; HPQ, la de largo plazo con su parte corriente).
        g = lambda *cs: _row(facts, cs, end, until, False)
        stb, cp = g("ShortTermBorrowings"), bcol["Commercial Paper"]
        lt_nc = g("LongTermDebtNoncurrent", "LongTermDebtAndCapitalLeaseObligations")
        cur = g("DebtCurrent")
        if cur is None:
            lc = g("LongTermDebtAndCapitalLeaseObligationsCurrent", "LongTermDebtCurrent")
            short = [x for x in (lc, stb, cp) if x is not None]
            cur = sum(short) if short else None
        total = g("DebtAndCapitalLeaseObligations")
        if total is None:
            ltd_all = g("LongTermDebt")
            if ltd_all is not None:
                total = ltd_all + (stb or 0.0) + (cp or 0.0)
            elif lt_nc is not None or cur is not None:
                total = (lt_nc or 0.0) + (cur or 0.0)
        if reit_debt:
            # Solo el estudio de bandas (calibracion_bandas.py): los REIT etiquetan su deuda como pagarés y préstamos
            # (O) o como importe de los instrumentos; el estudio principal no usa esta rama (sus fixtures no cambian).
            # Revisión de F7 (hallazgo 6): una etiqueta de total antes que sumar etiquetas que se solapan, y nunca
            # una deuda mayor que el pasivo total.
            liab = bcol["Total Liabilities Net Minority Interest"]
            cands = [g("DebtInstrumentCarryingAmount"), g("NotesPayable", "NotesAndLoansPayable")]
            if cands[1] is not None:
                cands[1] += (g("LoansPayable") or 0.0) + (g("LineOfCredit") or 0.0)
            for alt in cands:
                if alt is not None and (liab is None or alt <= liab) and (total is None or alt > total):
                    total = alt
                    break
        bcol["Long Term Debt"] = lt_nc
        bcol["Current Debt"] = cur
        bcol["Total Debt"] = total
        eq = bcol["Stockholders Equity"]
        bcol["Common Stock Equity"] = eq
        if eq is not None:
            bcol["Tangible Book Value"] = eq - (bcol["Goodwill"] or 0.0) - (bcol["Other Intangible Assets"] or 0.0)
        if bcol["Total Liabilities Net Minority Interest"] is None and bcol["Total Assets"] is not None \
                and bcol["Total Equity Gross Minority Interest"] is not None:
            bcol["Total Liabilities Net Minority Interest"] = (bcol["Total Assets"]
                                                               - bcol["Total Equity Gross Minority Interest"])
        sh = _row(facts, ("CommonStockSharesOutstanding",), end, until, False, lambda u: u == "shares")
        bcol["Ordinary Shares Number"] = bcol["Share Issued"] = sh
        bs[c] = bcol
        ccol = {}
        for row, (sign, concepts) in CASH_FLOW.items():
            v = _row(facts, concepts, end, until, True)
            ccol[row] = None if v is None else sign * abs(v) if sign < 0 else v
        if ccol["Operating Cash Flow"] is not None and ccol["Capital Expenditure"] is not None:
            ccol["Free Cash Flow"] = ccol["Operating Cash Flow"] + ccol["Capital Expenditure"]
        cf[c] = ccol
        oi, da = col["Operating Income"], ccol["Depreciation And Amortization"]
        inc[c]["EBITDA"] = (oi + da) if (oi is not None and da is not None) else None
        inc[c]["EBIT"] = oi

    def frame(d):
        df = pd.DataFrame(d).astype("float64")
        return df.dropna(how="all") if not df.empty else df
    statements.ebit_proxy = ebit_proxy
    return frame(inc), frame(bs), frame(cf), ends


def cover_shares(facts, until, fallback):
    """Acciones de la portada del último filing hasta `until` (dei; varias clases se suman). Si se apartan más de un
    30% de las diluidas medias del ejercicio (una clase duplicada o en otra base), las diluidas medias."""
    fs = [f for f in _facts(facts, "EntityCommonStockSharesOutstanding", tx="dei") if f.get("filed", "9999") <= until]
    if fs:
        last = max(f["filed"] for f in fs)
        acc = max(f.get("accn", "") for f in fs if f["filed"] == last)
        tot = sum(float(f["val"]) for f in fs if f["filed"] == last and f.get("accn", "") == acc)
        if fallback is None or 0.7 <= tot / fallback <= 1.3:
            return tot, "portada del 10-K (dei)"
    return fallback, "acciones diluidas medias del ejercicio"


def split_factor_after(series_obj, day):
    """Producto de los splits (y escisiones que Yahoo registra como split) POSTERIORES a `day`. La serie de yfinance
    viene ajustada por todos los splits hasta hoy, también con auto_adjust=False: el precio que se veía en `day` es el
    de la serie × este factor (revisión de F7, hallazgo 1: WMT salía a un tercio por el split de 2024)."""
    f = 1.0
    for d, r in (series_obj.get("split") or {}).items():
        if d > day and r and r > 0:
            f *= r
    return f


def window(series_obj, start, end):
    """Objeto de serie (history_fixtures) recortado a [start, end], como se veía en `end`: sin los splits posteriores."""
    dates = series_obj["dates"]
    keep = [i for i, d in enumerate(dates) if start <= d <= end]
    k = split_factor_after(series_obj, end)
    out = {"symbol": series_obj["symbol"], "tz": series_obj.get("tz", hf.TZ), "dates": [dates[i] for i in keep]}
    for _, c in hf.COLS:
        if c in ("dividend", "split"):
            ev = series_obj.get(c) or {}
            out[c] = {d: (v * k if c == "dividend" else v) for d, v in ev.items() if start <= d <= end}
        else:
            vals = [series_obj[c][i] for i in keep]
            if c == "volume":
                out[c] = [None if v is None else v / k for v in vals]
            else:
                out[c] = [None if v is None else v * k for v in vals]
    return out


def _series(data, sym):
    p = hf.series_file(sym, data)
    return json.load(open(p)) if os.path.isfile(p) else None


def pit_submissions(facts, sub):
    """Lista de filings: los periódicos reconstruidos de los hechos (forma, accn, fecha, periodo) más los de la SEC."""
    rows = {}
    for tx in ("us-gaap", "dei"):
        for node in ((facts.get("facts") or {}).get(tx) or {}).values():
            for fs in (node.get("units") or {}).values():
                for f in fs:
                    form, accn = f.get("form"), f.get("accn")
                    if form in ("10-K", "10-Q", "10-K/A", "10-Q/A") and accn:
                        r = rows.setdefault(accn, {"form": form, "filingDate": f["filed"], "reportDate": f["end"]})
                        if not f.get("start") and f["end"] > r["reportDate"]:
                            r["reportDate"] = f["end"]
    rec = (sub or {}).get("filings", {}).get("recent") or {}
    keys = ("accessionNumber", "filingDate", "reportDate", "form", "items", "isXBRL", "primaryDocument")
    have = set(rec.get("accessionNumber") or [])
    out = {k: list(rec.get(k) or []) for k in keys}
    n = len(out["accessionNumber"])
    for k in keys:
        out[k] += [""] * (n - len(out[k]))
    for accn, r in sorted(rows.items(), key=lambda kv: kv[1]["filingDate"], reverse=True):
        if accn in have:
            continue
        out["accessionNumber"].append(accn)
        out["filingDate"].append(r["filingDate"])
        out["reportDate"].append(r["reportDate"])
        out["form"].append(r["form"])
        out["items"].append("")
        out["isXBRL"].append(1)
        out["primaryDocument"].append("")
    obj = dict(sub or {})
    obj["filings"] = {"recent": out, "files": []}
    return obj


def generate(data):
    tick = json.load(open(os.path.join(data, "edgar", "company_tickers.json")))
    meta_all = json.load(open(os.path.join(data, "metadata.json")))
    tickers = [t for v in meta_all["universe"].values() for t in v]
    pit = os.path.join(data, "edgar_pit", "edgar")
    os.makedirs(os.path.join(pit, "companyfacts"), exist_ok=True)
    os.makedirs(os.path.join(pit, "submissions"), exist_ok=True)
    pit_tickers = {}
    log = []
    gspc = _series(data, "^GSPC")
    for t in tickers:
        cik = (tick.get(t) or {}).get("cik")
        if not cik:
            log.append((t, None, "sin CIK"))
            continue
        name = f"CIK{int(cik):010d}.json"
        facts = json.load(open(os.path.join(data, "edgar", "companyfacts", name)))
        sub = json.load(open(os.path.join(data, "edgar", "submissions", name)))
        pit_tickers[t] = {"cik": int(cik), "title": (tick.get(t) or {}).get("title")}
        with open(os.path.join(pit, "companyfacts", name), "w") as fh:
            json.dump(facts, fh, separators=(",", ":"))
        with open(os.path.join(pit, "submissions", name), "w") as fh:
            json.dump(pit_submissions(facts, sub), fh, separators=(",", ":"))
        srch = json.load(open(os.path.join(data, "search", f"{t}.json")))
        quote = next((q for q in (srch.get("body_json") or {}).get("quotes") or [] if q.get("symbol") == t), {})
        etf = SECTOR_ETF.get(quote.get("sector"))
        own = _series(data, t)
        etf_s = _series(data, etf) if etf else None
        for fy in FYS:
            tk = tenk_filing(facts, fy)
            if tk is None:
                log.append((t, fy, "sin 10-K de ese ejercicio"))
                continue
            fy_end, filed = tk
            D = (_d(filed) + _dt.timedelta(days=1)).isoformat()
            inc, bs, cf, ends = statements(facts, _d(fy_end), filed)
            if inc.empty or "Total Revenue" not in inc.index and "Net Income" not in inc.index:
                log.append((t, fy, "estados vacíos"))
                continue
            if own is None or not own["dates"] or own["dates"][0] > (_d(D) - _dt.timedelta(days=400)).isoformat():
                log.append((t, fy, "serie de precios corta"))
                continue
            start = (_d(D) - _dt.timedelta(days=730)).isoformat()
            ps = window(own, start, D)
            if not ps["dates"]:
                log.append((t, fy, "sin precio en D"))
                continue
            px = ps["close"][-1]
            dil = inc.loc["Diluted Average Shares"].iloc[0] if "Diluted Average Shares" in inc.index else None
            dil = None if dil is None or dil != dil else float(dil)
            shares, sh_src = cover_shares(facts, filed, dil)
            if not px or not shares:
                log.append((t, fy, "sin precio o acciones"))
                continue
            yr = window(own, (_d(D) - _dt.timedelta(days=365)).isoformat(), D)
            highs = [x for x in yr["high"] if x is not None]
            lows = [x for x in yr["low"] if x is not None]
            yfd = {"income_stmt": fb.df_to_obj(inc), "balance_sheet": fb.df_to_obj(bs), "cashflow": fb.df_to_obj(cf),
                   "fast_info": {"currency": "USD", "exchange": quote.get("exchange") or "NYQ",
                                 "lastPrice": px, "marketCap": px * shares, "quoteType": "EQUITY",
                                 "shares": shares, "yearHigh": max(highs) if highs else None,
                                 "yearLow": min(lows) if lows else None},
                   "info": {}, "price_history": ps,
                   "market_history": window(gspc, start, D)}
            if etf_s and etf_s["dates"] and etf_s["dates"][0] <= (_d(D) - _dt.timedelta(days=400)).isoformat():
                yfd["sector_history"] = window(etf_s, start, D)
            http = [{"url": f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{t}",
                     "params": {"modules": "financialData,defaultKeyStatistics,assetProfile,price,summaryDetail,"
                                           "incomeStatementHistory,balanceSheetHistory,cashflowStatementHistory,earnings"},
                     "status": 401, "body_json": {"finance": {"error": {"code": "Unauthorized",
                                                                        "description": "Invalid Crumb"}, "result": None}}}] * 2
            http.append({"url": f"https://query2.finance.yahoo.com/ws/fundamentals-timeseries/v1/finance/timeseries/{t}",
                         "params": {"symbol": t}, "status": 200,
                         "body_json": {"timeseries": {"error": None, "result": [
                             {"annualTotalRevenue": [{"asOfDate": fy_end, "currencyCode": "USD"}]}]}}})
            http.append({"url": "https://query2.finance.yahoo.com/v1/finance/search", "params": srch["params"],
                         "status": srch["status"], "body_json": srch["body_json"]})
            meta = {"captured_at_local": f"{D}T16:30:00", "environment": "calibracion", "ticker": t,
                    "finnhub": {"participated": False, "calls": 0, "key_present": False, "note": "sin Finnhub"},
                    "risk_free": {"source": "^TNX en D (calibración)"},
                    "calibracion": {"fy": fy, "fy_end": fy_end, "tenk_filed": filed, "D": D, "price": px,
                                    "shares": shares, "shares_source": sh_src, "fy_columns": ends,
                                    "ebit_proxy_years": list(statements.ebit_proxy),
                                    "sector": quote.get("sector"), "industry": quote.get("industry"),
                                    "sector_etf": etf if "sector_history" in yfd else None}}
            d = os.path.join(data, "fixtures", f"FY{fy}", t)
            os.makedirs(d, exist_ok=True)
            for fname, payload in (("metadata.json", meta), ("yahoo_http.json", http), ("yfinance.json", yfd),
                                   ("finnhub.json", [])):
                with open(os.path.join(d, fname), "w") as fh:
                    json.dump(payload, fh, separators=(",", ":"), default=float)
            log.append((t, fy, "ok"))
    with open(os.path.join(pit, "company_tickers.json"), "w") as fh:
        json.dump(pit_tickers, fh)
    with open(os.path.join(data, "generar.log.json"), "w") as fh:
        json.dump(log, fh)
    ok = sum(1 for x in log if x[2] == "ok")
    print(f"{ok} fixtures; {len(log) - ok} descartados", flush=True)
    from collections import Counter
    print(Counter(x[2] for x in log if x[2] != "ok"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    a = ap.parse_args()
    generate(os.path.expanduser(a.data))


if __name__ == "__main__":
    main()
