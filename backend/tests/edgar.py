"""
Fase 2a del plan de fiabilidad: acceso a SEC EDGAR (API XBRL companyfacts) para MEDIR los datos del motor.

Herramienta de diagnóstico y verificación: vive en tests/ y nunca entra en el camino del análisis (decisión D2:
EDGAR no alimenta el motor en la 2a).

- User-Agent: lo exige la SEC (nombre y correo). Se lee del Llavero (`finanzer-sec-ua`) y nunca se escribe en el
  repo, en los fixtures ni en la salida.
- Límite de la SEC: ≤ 10 peticiones/s. Aquí, una petición cada MIN_INTERVAL s (≈ 6/s), en serie.
- Caché en disco: las descargas crudas van a tests/fixtures/edgar/raw/ (fuera de git) o a $FINANZER_EDGAR_CACHE;
  junto a cada JSON, un .meta.json con la fecha, la latencia y el tamaño de la descarga.

La tabla de conceptos (CONCEPTS) traduce cada campo que consume el motor a sus etiquetas XBRL posibles, en orden de
preferencia, por taxonomía (us-gaap para 10-K/10-Q, ifrs-full para 20-F).
"""
import datetime as dt
import gzip
import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

HERE = Path(__file__).resolve().parent
EDGAR_DIR = HERE / "fixtures" / "edgar"
CACHE = Path(os.environ.get("FINANZER_EDGAR_CACHE") or EDGAR_DIR / "raw")
MIN_INTERVAL = 0.15            # s entre peticiones: ≈ 6.7/s, por debajo del máximo de 10/s de la SEC
TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
ANNUAL_FORMS = {"10-K", "10-K/A", "20-F", "20-F/A", "40-F", "40-F/A", "10-KT"}
QUARTERLY_FORMS = {"10-Q", "10-Q/A"}

# ───────────────────────────── tabla de conceptos ─────────────────────────────
# campo → tipo de hecho, signo en XBRL frente al motor (Yahoo), dónde lo consume el motor y alternativas ordenadas.
# kind: "flow" (periodo con inicio y fin), "stock" (saldo a una fecha), "per_share" (moneda/acción), "shares".
# sign: "+" mismo signo que Yahoo; "pago+" XBRL lo da positivo (pago) y Yahoo negativo (salida de caja).
CONCEPTS: Dict[str, Dict[str, Any]] = {
    # Cuenta de resultados
    "revenue": dict(kind="flow", sign="+", engine="FS.revenue · ttm totalRevenue · FY revenue", us=[
        "Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax",
        "RevenueFromContractWithCustomerIncludingAssessedTax", "SalesRevenueNet", "SalesRevenueGoodsNet",
        "RevenuesNetOfInterestExpense", "RegulatedAndUnregulatedOperatingRevenue", "OperatingLeasesIncomeStatementLeaseRevenue",
        "PremiumsEarnedNet"], ifrs=["Revenue", "RevenueFromContractsWithCustomers"]),
    "gross_profit": dict(kind="flow", sign="+", engine="FS.gross_profit · ttm grossProfits · FY gross_profit",
                         us=["GrossProfit"], ifrs=["GrossProfit"]),
    "operating_income": dict(kind="flow", sign="+", engine="FS.operating_income · ttm · FY operating_income/ebit",
                             us=["OperatingIncomeLoss"], ifrs=["ProfitLossFromOperatingActivities"]),
    "pretax_income": dict(kind="flow", sign="+", engine="normalize (Pretax Income) · tasa efectiva WACC", us=[
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesDomestic"], ifrs=["ProfitLossBeforeTax"]),
    "tax_provision": dict(kind="flow", sign="+", engine="normalize (Tax Provision) · tasa efectiva WACC",
                          us=["IncomeTaxExpenseBenefit"], ifrs=["IncomeTaxExpenseContinuingOperations"]),
    "net_income": dict(kind="flow", sign="+", engine="FS.net_income · ttm netIncome · Piotroski · FY net_income",
                       us=["NetIncomeLoss", "NetIncomeLossAvailableToCommonStockholdersBasic",
                           "NetIncomeLossAvailableToCommonStockholdersDiluted"],
                       ifrs=["ProfitLossAttributableToOwnersOfParent", "ProfitLoss"]),
    "net_income_minorities": dict(kind="flow", sign="+", engine="(definición: ROE del accionista ordinario)",
                                  us=["NetIncomeLossAttributableToNoncontrollingInterest"],
                                  ifrs=["ProfitLossAttributableToNoncontrollingInterests"]),
    "discontinued_ops": dict(kind="flow", sign="+", engine="(perímetro: escisiones y ventas)", us=[
        "IncomeLossFromDiscontinuedOperationsNetOfTax",
        "IncomeLossFromDiscontinuedOperationsNetOfTaxAttributableToReportingEntity"],
        ifrs=["ProfitLossFromDiscontinuedOperations"]),
    "interest_expense": dict(kind="flow", sign="+", engine="FS.interest_expense · cobertura · Kd del WACC", us=[
        "InterestExpense", "InterestExpenseNonoperating", "InterestExpenseDebt", "InterestAndDebtExpense",
        "InterestExpenseNet"], ifrs=["FinanceCosts", "InterestExpense"]),
    "net_interest_income": dict(kind="flow", sign="+", engine="FS.net_interest_income (estado de la cobertura; bancos)",
                                us=["InterestIncomeExpenseNet", "InterestIncomeExpenseAfterProvisionForLoanLoss",
                                    "InterestIncomeExpenseNonoperatingNet"],
                                ifrs=["InterestRevenueExpense", "NetInterestIncomeExpense"]),
    "non_interest_expense": dict(kind="flow", sign="+", engine="FY non_interest_expense (eficiencia bancaria)",
                                 us=["NoninterestExpense"], ifrs=["OperatingExpense"]),
    "depreciation": dict(kind="flow", sign="+", engine="FS.depreciation · ttm · capex de mantenimiento (CYCLICAL)", us=[
        "DepreciationDepletionAndAmortization", "DepreciationAndAmortization", "DepreciationAmortizationAndAccretionNet",
        "Depreciation", "DepreciationAmortizationAndOther"], ifrs=[
        "DepreciationAndAmortisationExpense", "AdjustmentsForDepreciationAndAmortisationExpense",
        "DepreciationPropertyPlantAndEquipmentIncludingRightofuseAssets", "DepreciationExpense",
        "DepreciationAmortisationAndImpairmentLossReversalOfImpairmentLossRecognisedInProfitOrLoss",
        "AdjustmentsForDepreciationAmortisationAndImpairmentLossReversalOfImpairmentLossRecognisedInProfitOrLoss",
        "AdjustmentsForDepreciationAndAmortisationExpenseAndImpairmentLossReversalOfImpairmentLossRecognisedInProfitOrLoss"]),
    "diluted_eps": dict(kind="per_share", sign="+", engine="FS.eps · FY diluted_eps (CAGR del BPA) · P/E",
                        us=["EarningsPerShareDiluted", "EarningsPerShareBasicAndDiluted", "EarningsPerShareBasic"],
                        ifrs=["DilutedEarningsLossPerShare", "BasicAndDilutedEarningsLossPerShare",
                              "BasicEarningsLossPerShare", "DilutedEarningsLossPerShareFromContinuingOperations"]),
    "diluted_shares": dict(kind="shares", sign="+", engine="normalize (Diluted Average Shares)",
                           us=["WeightedAverageNumberOfDilutedSharesOutstanding"],
                           ifrs=["AdjustedWeightedAverageShares", "WeightedAverageShares"]),
    # Balance
    "total_assets": dict(kind="stock", sign="+", engine="FS.total_assets · ttm · Altman · Piotroski (ROA, rotación)",
                         us=["Assets"], ifrs=["Assets"]),
    "current_assets": dict(kind="stock", sign="+", engine="FS.current_assets · Altman X1 · liquidez",
                           us=["AssetsCurrent"], ifrs=["CurrentAssets"]),
    "cash": dict(kind="stock", sign="+", engine="FS.cash · deuda neta", us=[
        "CashAndCashEquivalentsAtCarryingValue", "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
        "Cash", "CashAndDueFromBanks"], ifrs=["CashAndCashEquivalents", "Cash"]),
    "short_term_investments": dict(kind="stock", sign="+", engine="FS.cash (fila Yahoo 'Cash … And Short Term Investments')",
                                   us=["ShortTermInvestments", "MarketableSecuritiesCurrent",
                                       "AvailableForSaleSecuritiesDebtSecuritiesCurrent"],
                                   ifrs=["CurrentInvestments", "OtherCurrentFinancialAssets"]),
    "inventories": dict(kind="stock", sign="+", engine="FS.inventories · rotación de inventario · prueba ácida",
                        us=["InventoryNet", "InventoryFinishedGoodsNetOfReserves"], ifrs=["Inventories"]),
    "total_liabilities": dict(kind="stock", sign="+", engine="FS.total_liabilities · Altman X4",
                              us=["Liabilities"], ifrs=["Liabilities"]),
    "liabilities_and_equity": dict(kind="stock", sign="+", engine="(pasivo total derivado = esto − patrimonio total)",
                                   us=["LiabilitiesAndStockholdersEquity"], ifrs=["EquityAndLiabilities"]),
    "current_liabilities": dict(kind="stock", sign="+", engine="FS.current_liabilities · Altman X1 · ROCE · Piotroski",
                                us=["LiabilitiesCurrent"], ifrs=["CurrentLiabilities"]),
    "long_term_debt": dict(kind="stock", sign="+", engine="FS.long_term_debt · Piotroski (apalancamiento)", us=[
        "LongTermDebtNoncurrent", "LongTermDebtAndCapitalLeaseObligations", "LongTermDebt",
        "LongTermDebtAndCapitalLeaseObligationsIncludingCurrentMaturities"],
        ifrs=["NoncurrentPortionOfNoncurrentBorrowings", "LongtermBorrowings", "NoncurrentFinancialLiabilities"]),
    "short_term_debt": dict(kind="stock", sign="+", engine="FS.total_debt (componente corto plazo)", us=[
        "LongTermDebtCurrent", "DebtCurrent", "ShortTermBorrowings", "CommercialPaper",
        "LongTermDebtAndCapitalLeaseObligationsCurrent"], ifrs=[
        "CurrentBorrowingsAndCurrentPortionOfNoncurrentBorrowings", "CurrentPortionOfNoncurrentBorrowings",
        "ShorttermBorrowings", "CurrentFinancialLiabilities"]),
    "total_debt_reported": dict(kind="stock", sign="+", engine="FS.total_debt (si la empresa lo etiqueta entero)",
                                us=["DebtInstrumentCarryingAmount", "LongTermDebt", "DebtAndCapitalLeaseObligations"],
                                ifrs=["Borrowings", "DebtSecuritiesInIssue", "DebtSecurities",
                                      "DebtInstrumentsIssuedAtAmortisedCost"]),
    "equity_parent": dict(kind="stock", sign="+", engine="FS.total_equity · ROE · P/B · Altman Z'' X4", us=[
        "StockholdersEquity",
        "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"],
        ifrs=["EquityAttributableToOwnersOfParent", "Equity"]),
    "minority_interest": dict(kind="stock", sign="+", engine="(definición: patrimonio del accionista ordinario)",
                              us=["MinorityInterest"], ifrs=["NoncontrollingInterests"]),
    "at1_equity": dict(kind="stock", sign="+", engine="(definición: ROE/ROTE ordinario de bancos con AT1)",
                       us=["PreferredStockValue"], ifrs=["OtherEquityInterest", "OtherEquityInstruments"]),
    "at1_coupons": dict(kind="flow", sign="pago+", engine="(definición: beneficio del accionista ordinario)",
                        us=["PaymentsOfDividendsPreferredStockAndPreferenceStock", "DividendsPreferredStockCash",
                            "PreferredStockDividendsIncomeStatementImpact"],
                        ifrs=["PaymentsOfOtherEquityInstruments"]),
    "retained_earnings": dict(kind="stock", sign="+", engine="FS.retained_earnings · Altman X2",
                              us=["RetainedEarningsAccumulatedDeficit"], ifrs=["RetainedEarnings"]),
    "goodwill": dict(kind="stock", sign="+", engine="(valor contable tangible: ROTE, P/TBV)",
                     us=["Goodwill"], ifrs=["Goodwill"]),
    "intangibles": dict(kind="stock", sign="+", engine="(valor contable tangible: ROTE, P/TBV)",
                        us=["IntangibleAssetsNetExcludingGoodwill", "FiniteLivedIntangibleAssetsNet"],
                        ifrs=["IntangibleAssetsOtherThanGoodwill"]),
    "goodwill_and_intangibles": dict(kind="stock", sign="+", engine="(valor contable tangible si no se separan)",
                                     us=["IntangibleAssetsNetIncludingGoodwill"], ifrs=["IntangibleAssetsAndGoodwill"]),
    "shares_outstanding": dict(kind="shares", sign="+", engine="FS.shares_outstanding · FY ordinary_shares · Piotroski",
                               us=["CommonStockSharesOutstanding"], ifrs=["NumberOfSharesOutstanding"],
                               dei=["EntityCommonStockSharesOutstanding"]),
    # Flujos de caja
    "operating_cash_flow": dict(kind="flow", sign="+", engine="FS.operating_cash_flow · ttm · Piotroski · FCF", us=[
        "NetCashProvidedByUsedInOperatingActivities", "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"],
        ifrs=["CashFlowsFromUsedInOperatingActivities", "CashFlowsFromUsedInOperations"]),
    "capex": dict(kind="flow", sign="pago+", engine="FS.capex · ttm capitalExpenditures · FCF", us=[
        "PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsToAcquireProductiveAssets",
        "PaymentsForCapitalImprovements", "PaymentsToAcquireRealEstate"], ifrs=[
        "PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities",
        "PurchaseOfPropertyPlantAndEquipmentIntangibleAssetsOtherThanGoodwillInvestmentPropertyAndOtherNoncurrentAssets",
        "PurchaseOfPropertyPlantAndEquipment", "PurchaseOfOtherLongtermAssetsClassifiedAsInvestingActivities"]),
    "dividends_paid": dict(kind="flow", sign="pago+", engine="FS.dividends_paid · ttm dividendsPaid · payout", us=[
        "PaymentsOfDividendsCommonStock", "PaymentsOfDividends", "PaymentsOfOrdinaryDividends"], ifrs=[
        "DividendsPaidClassifiedAsFinancingActivities", "DividendsPaidToEquityHoldersOfParentClassifiedAsFinancingActivities",
        "DividendsPaid"]),
    "dividend_per_share": dict(kind="per_share", sign="+", engine="FS.dividend_per_share · rentabilidad por dividendo",
                               us=["CommonStockDividendsPerShareDeclared", "CommonStockDividendsPerShareCashPaid"],
                               ifrs=["DividendsRecognisedAsDistributionsToOwnersPerShare",
                                     "DividendsPaidOrdinarySharesPerShare"]),
    "buybacks": dict(kind="flow", sign="pago+", engine="shareholder yield (recompras)",
                     us=["PaymentsForRepurchaseOfCommonStock"],
                     ifrs=["PaymentsToAcquireOrRedeemEntitysShares"]),
    "stock_based_compensation": dict(kind="flow", sign="+", engine="ttm stockBasedCompensation · FCF − SBC",
                                     us=["ShareBasedCompensation", "AllocatedShareBasedCompensationExpense"],
                                     ifrs=["AdjustmentsForSharebasedPayments",
                                           "ExpenseFromSharebasedPaymentTransactionsWithEmployees"]),
}

# Conceptos que no son un campo del motor pero que T3 necesita para explicar diferencias de definición (deuda con
# papel comercial y arrendamientos, capex con intangibles, beneficio del accionista ordinario sin cupones AT1,
# beneficio de las operaciones continuadas). Van en los extractos; no en la tabla de cobertura.
EXTRACT_EXTRA = {
    "us": ["OtherShortTermBorrowings", "OperatingLeaseLiability", "OperatingLeaseLiabilityCurrent",
           "OperatingLeaseLiabilityNoncurrent", "FinanceLeaseLiability", "FinanceLeaseLiabilityCurrent",
           "FinanceLeaseLiabilityNoncurrent", "PaymentsToAcquireIntangibleAssets",
           "NetIncomeLossAvailableToCommonStockholdersDiluted", "IncomeLossFromContinuingOperations",
           "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest", "CommonStockDividendsPerShareDeclared",
           "LongTermDebtCurrent", "LongTermDebtNoncurrent", "LongTermDebt", "CommercialPaper", "ShortTermBorrowings",
           "CashCashEquivalentsAndShortTermInvestments", "PaymentsToAcquireEquipmentOnLease", "PaymentsToDevelopSoftware",
           "PaymentsForSoftware", "NotesPayable", "LoansPayable", "SeniorNotes", "UnsecuredDebt", "SecuredDebt",
           "LongTermDebtAndCapitalLeaseObligations", "LongTermDebtAndCapitalLeaseObligationsCurrent"],
    "ifrs": ["LeaseLiabilities", "CurrentLeaseLiabilities", "NoncurrentLeaseLiabilities",
             "PurchaseOfIntangibleAssetsClassifiedAsInvestingActivities",
             "ProfitLossAttributableToOrdinaryEquityHoldersOfParentEntity", "ProfitLossFromContinuingOperations",
             "Equity", "CurrentBorrowingsAndCurrentPortionOfNoncurrentBorrowings",
             "NoncurrentPortionOfNoncurrentBorrowings", "ShorttermBorrowings", "LongtermBorrowings", "Borrowings",
             "SubordinatedLiabilities", "CapitalReserve"],
}

# Campos del motor que NO salen de unos estados con XBRL: se derivan de otros o son de mercado.
DERIVED = {
    "ebitda": "operating_income + depreciation (Yahoo da su propia fila 'EBITDA'; XBRL no la etiqueta)",
    "ebit": "operating_income (o pretax_income + interest_expense)",
    "free_cash_flow": "operating_cash_flow − capex (lo mismo que recalcula validate.py)",
    "total_debt": "long_term_debt + short_term_debt (o total_debt_reported si existe)",
    "tangible_book_value": "equity_parent − goodwill − intangibles",
    "book_value_per_share": "equity_parent / shares_outstanding (en acciones ordinarias, no ADR)",
    "ffo (REIT)": "net_income + depreciation inmobiliaria − plusvalías por ventas (NAREIT; sin etiqueta estándar)",
}
MARKET = {
    "price": "cotización (Yahoo/Finnhub)", "52w high/low": "cotización", "beta": "serie de precios (Finnhub/Yahoo)",
    "forward_eps": "estimación de analistas", "market_cap": "precio × acciones (ADR: × factor)",
}


# ───────────────────────────── descarga con caché ─────────────────────────────

_last = [0.0]


def user_agent() -> str:
    try:
        ua = subprocess.run(["security", "find-generic-password", "-s", "finanzer-sec-ua", "-w"],
                            capture_output=True, text=True, check=True).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        raise RuntimeError("Falta el User-Agent de la SEC en el Llavero (finanzer-sec-ua)") from e
    if "@" not in ua:
        raise RuntimeError("El User-Agent de la SEC del Llavero no lleva correo de contacto")
    return ua


def _get(url: str) -> Tuple[Optional[bytes], int, float]:
    wait = MIN_INTERVAL - (time.monotonic() - _last[0])
    if wait > 0:
        time.sleep(wait)
    req = urllib.request.Request(url, headers={"User-Agent": user_agent(), "Accept-Encoding": "gzip"})
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            raw = r.read()
            body = gzip.decompress(raw) if r.headers.get("Content-Encoding") == "gzip" else raw
            status = r.status
    except urllib.error.HTTPError as e:
        body, status = None, e.code
    finally:
        _last[0] = time.monotonic()
    return body, status, time.monotonic() - t0


def fetch_json(url: str, name: str, refresh: bool = False) -> Tuple[Optional[dict], Dict[str, Any]]:
    """JSON de la SEC con caché en disco; meta = {status, seconds, bytes, fetched_at, cached}."""
    CACHE.mkdir(parents=True, exist_ok=True)
    path, mpath = CACHE / f"{name}.json", CACHE / f"{name}.meta.json"
    if path.exists() and mpath.exists() and not refresh:
        return json.loads(path.read_bytes()), {**json.loads(mpath.read_text()), "cached": True}
    if mpath.exists() and not refresh and json.loads(mpath.read_text()).get("status") == 404:
        return None, {**json.loads(mpath.read_text()), "cached": True}
    body, status, secs = _get(url)
    meta = {"url": url, "status": status, "seconds": round(secs, 3), "bytes": len(body or b""),
            "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
    mpath.write_text(json.dumps(meta, indent=1))
    if body is None or status != 200:
        return None, {**meta, "cached": False}
    path.write_bytes(body)
    return json.loads(body), {**meta, "cached": False}


def cik_map(refresh: bool = False) -> Dict[str, Dict[str, Any]]:
    data, _ = fetch_json(TICKERS_URL, "company_tickers", refresh)
    return {v["ticker"]: v for v in (data or {}).values()}


def company_facts(cik: int, refresh: bool = False):
    return fetch_json(FACTS_URL.format(cik=cik), f"CIK{cik:010d}.facts", refresh)


def submissions(cik: int, refresh: bool = False):
    return fetch_json(SUBMISSIONS_URL.format(cik=cik), f"CIK{cik:010d}.submissions", refresh)


# ───────────────────────────── lectura de hechos ─────────────────────────────

def days(f: Dict[str, Any]) -> Optional[int]:
    if not f.get("start"):
        return None
    return (dt.date.fromisoformat(f["end"]) - dt.date.fromisoformat(f["start"])).days


def span(f: Dict[str, Any]) -> str:
    """Tipo de periodo de un hecho: FY, Q (3 meses), 6M, 9M, instant u otro."""
    d = days(f)
    if d is None:
        return "instant"
    if 350 <= d <= 380:
        return "FY"
    if 80 <= d <= 100:
        return "Q"
    if 170 <= d <= 195:
        return "6M"
    if 260 <= d <= 285:
        return "9M"
    return f"{d}d"


def taxonomy(facts: Dict[str, Any]) -> str:
    """Taxonomía de los estados VIGENTES: la que trae el `Assets` más reciente (TM pasó de us-gaap a ifrs-full en el
    20-F de 2021; contar conceptos elegiría la histórica). Sin `Assets`, la que tenga más conceptos."""
    f = facts.get("facts", {})
    last = {tx: max((x["end"] for fs in f.get(tx, {}).get("Assets", {}).get("units", {}).values() for x in fs),
                    default="") for tx in ("us-gaap", "ifrs-full")}
    n = {tx: len(f.get(tx, {})) for tx in ("us-gaap", "ifrs-full")}
    best = max(("us-gaap", "ifrs-full"), key=lambda tx: (last[tx], n[tx]))
    return best if n[best] else "—"


# Sucesiones de emisor: el ticker apunta al CIK nuevo, pero la historia XBRL sigue en el anterior.
# XOM: reorganización en holding (8-K12B de ExxonMobil Holdings Corp, CIK 2115436, del 2026-07-01); los estados
# hasta el 1T-2026 están en Exxon Mobil Corp (CIK 34088), que sigue presentando 10-Q.
PREDECESSORS: Dict[str, List[int]] = {"XOM": [34088]}


def merge_facts(newer: Dict[str, Any], older: Dict[str, Any]) -> Dict[str, Any]:
    """companyfacts del sucesor con la historia del predecesor (mismo periodo: los dos filings quedan y manda el
    más reciente por `filed`, como en una reexpresión)."""
    out = {"cik": newer.get("cik"), "entityName": newer.get("entityName"), "facts": {},
           "predecessor": {"cik": older.get("cik"), "entityName": older.get("entityName")}}
    for src in (older, newer):
        for tx, cs in src.get("facts", {}).items():
            for c, node in cs.items():
                dst = out["facts"].setdefault(tx, {}).setdefault(c, {"label": node.get("label"), "units": {}})
                for u, fs in node.get("units", {}).items():
                    dst["units"].setdefault(u, []).extend(fs)
    return out


def reporting_unit(facts: Dict[str, Any], tax: str) -> Optional[str]:
    """Moneda de los estados: la unidad de `Assets` con hechos más recientes."""
    units = facts.get("facts", {}).get(tax, {}).get("Assets", {}).get("units", {})
    best = max(units.items(), key=lambda kv: max((x["end"] for x in kv[1]), default=""), default=None)
    return best[0] if best else None


def concept_facts(facts: Dict[str, Any], tax: str, concept: str, unit: Optional[str]) -> List[Dict[str, Any]]:
    units = facts.get("facts", {}).get(tax, {}).get(concept, {}).get("units", {})
    if not units:
        return []
    if unit in units:
        return units[unit]
    # por acción ("USD/shares") o acciones ("shares"): la unidad que contenga la moneda o, si no, la única que haya
    for u, v in units.items():
        if unit and u.startswith(unit + "/"):
            return v
    return next(iter(units.values())) if len(units) == 1 else []


def unit_of(facts: Dict[str, Any], tax: str, concept: str, unit: Optional[str]) -> Optional[str]:
    units = facts.get("facts", {}).get(tax, {}).get(concept, {}).get("units", {})
    if unit in units:
        return unit
    for u in units:
        if unit and u.startswith(unit + "/"):
            return u
    return next(iter(units)) if len(units) == 1 else None


def periods(fs: List[Dict[str, Any]], forms=None) -> Dict[Tuple[Optional[str], str], List[Dict[str, Any]]]:
    """Hechos agrupados por (start, end): cada grupo, los filings que traen ese periodo (comparativos incluidos)."""
    out: Dict[Tuple[Optional[str], str], List[Dict[str, Any]]] = {}
    for f in fs:
        if forms and f.get("form") not in forms:
            continue
        out.setdefault((f.get("start"), f["end"]), []).append(f)
    return out


def current(group: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Valor vigente de un periodo: el del filing más reciente (reexpresiones)."""
    return max(group, key=lambda f: (f.get("filed", ""), f.get("accn", "")))


def original(group: List[Dict[str, Any]]) -> Dict[str, Any]:
    return min(group, key=lambda f: (f.get("filed", ""), f.get("accn", "")))


def restated(group: List[Dict[str, Any]], rel: float = 0.001) -> Optional[float]:
    """Cambio relativo entre el valor original y el vigente de un periodo (None si no cambia)."""
    a, b = original(group)["val"], current(group)["val"]
    if a == b:
        return None
    base = abs(a) or abs(b)
    ch = abs(b - a) / base if base else 1.0
    return ch if ch > rel else None


def resolve(facts: Dict[str, Any], field: str, tax: str, unit: Optional[str]) -> Dict[str, Any]:
    """Para un campo: alternativas presentes, la elegida (la que trae el ejercicio más reciente; empate → orden de
    la tabla), su unidad, signo y periodos."""
    spec = CONCEPTS[field]
    alts = list(spec.get("us" if tax == "us-gaap" else "ifrs", []))
    cands = [(tax, c) for c in alts] + [("dei", c) for c in spec.get("dei", [])]
    present = []
    for i, (tx, c) in enumerate(cands):
        u = unit if spec["kind"] in ("flow", "stock", "per_share") else None
        fs = concept_facts(facts, tx, c, u) if spec["kind"] != "shares" else \
            facts.get("facts", {}).get(tx, {}).get(c, {}).get("units", {}).get("shares", [])
        if not fs:
            continue
        ann = [f for f in fs if f.get("form") in ANNUAL_FORMS and (spec["kind"] in ("stock", "shares") or span(f) == "FY")]
        last = max((f["end"] for f in (ann or fs)), default="")
        present.append(dict(tax=tx, concept=c, order=i, facts=fs, last_end=last,
                            unit=unit_of(facts, tx, c, u) if spec["kind"] != "shares" else "shares"))
    if not present:
        return {"field": field, "concept": None, "present": []}
    best = max(present, key=lambda p: (p["last_end"], -p["order"]))
    latest_fy = max((x["end"] for x in concept_facts(facts, tax, "Assets", unit) if x.get("form") in ANNUAL_FORMS),
                    default="")
    fs = best["facts"]
    by_span: Dict[str, int] = {}
    for (s, e), g in periods(fs).items():
        k = "instant" if s is None else span(g[0])
        by_span[k] = by_span.get(k, 0) + 1
    fy = periods([f for f in fs if f.get("form") in ANNUAL_FORMS and (f.get("start") is None or span(f) == "FY")])
    re_list = [(e, restated(g)) for (s, e), g in fy.items() if restated(g)]
    return {
        "field": field, "concept": f"{best['tax']}:{best['concept']}", "unit": best["unit"],
        "present": [f"{p['tax']}:{p['concept']}" for p in present], "last_end": best["last_end"],
        "periods": by_span, "fy_periods": len(fy), "restated_fy": sorted(re_list, reverse=True),
        "forms": sorted({f.get("form") for f in fs}),
        # el concepto existe pero no llega al último ejercicio con balance: dejó de etiquetarse (o cambió de nombre)
        "stale": bool(latest_fy and best["last_end"] < latest_fy),
    }


# ───────────────────── filings con XBRL que companyfacts no trae ─────────────────────
# Medido el 2026-10-15 (F2_EDGAR_DIAGNOSTICO §6.2): companyfacts no incorpora el 20-F FY2025 de TSM, el 20-F FY2026
# de TM ni los 6-K semestrales de 2026 de BCS, HSBC, SHEL y UL, aunque llevan XBRL. Se leen de la instancia del filing
# (`<x>_htm.xml`), solo los hechos sin dimensiones (como companyfacts).

SUPPLEMENT_FORMS = ANNUAL_FORMS | QUARTERLY_FORMS | {"6-K", "6-K/A"}
_NS_TAX = {"fasb.org/us-gaap/": "us-gaap", "xbrl.ifrs.org/taxonomy/": "ifrs-full", "xbrl.sec.gov/dei/": "dei"}


def _tax_of(ns: str) -> Optional[str]:
    ns = ns.split("://", 1)[-1]          # IFRS usa https, la FASB http
    return next((t for pre, t in _NS_TAX.items() if ns.startswith(pre)), None)


def parse_instance(xml: bytes, form: str, filed: str, accn: str) -> Dict[str, Any]:
    """Hechos no dimensionales de una instancia XBRL, con la forma de companyfacts ({tax: {concepto: {units}}})."""
    import xml.etree.ElementTree as ET
    root = ET.fromstring(xml)
    X = "{http://www.xbrl.org/2003/instance}"
    ctx: Dict[str, Dict[str, str]] = {}
    for c in root.iter(X + "context"):
        if c.find(f"{X}entity/{X}segment") is not None or c.find(X + "scenario") is not None:
            continue
        p = c.find(X + "period")
        inst, st, en = p.find(X + "instant"), p.find(X + "startDate"), p.find(X + "endDate")
        ctx[c.get("id")] = ({"end": inst.text.strip()[:10]} if inst is not None else
                            {"start": st.text.strip()[:10], "end": en.text.strip()[:10]})
    units: Dict[str, str] = {}
    for u in root.iter(X + "unit"):
        meas = [m.text.split(":")[-1] for m in u.iter(X + "measure")]
        div = u.find(X + "divide")
        units[u.get("id")] = "/".join(meas) if div is not None else (meas[0] if meas else "")
    out: Dict[str, Any] = {}
    for el in root:
        if not el.tag.startswith("{") or el.get("contextRef") not in ctx or el.text is None:
            continue
        ns, name = el.tag[1:].split("}")
        tx = _tax_of(ns)
        if not tx or el.get("unitRef") is None:
            continue
        try:
            val = float(el.text.strip())
        except ValueError:
            continue
        val = int(val) if val.is_integer() else val
        f = {**ctx[el.get("contextRef")], "val": val, "form": form, "filed": filed, "accn": accn}
        out.setdefault(tx, {}).setdefault(name, {"units": {}})["units"].setdefault(units[el.get("unitRef")], [])
        lst = out[tx][name]["units"][units[el.get("unitRef")]]
        if f not in lst:
            lst.append(f)
    return out


def missing_filings(cik: int, facts: Dict[str, Any], since: str = "2025-01-01") -> List[Dict[str, str]]:
    """Filings con XBRL (formularios de estados) presentados desde `since` cuyo número no aparece en companyfacts."""
    sub, _ = submissions(cik)
    rec = (sub or {}).get("filings", {}).get("recent", {})
    have = {x.get("accn") for cs in facts.get("facts", {}).values() for node in cs.values()
            for fs in node.get("units", {}).values() for x in fs if x.get("form") != "dei"}
    have_fin = {x.get("accn") for tx, cs in facts.get("facts", {}).items() if tx != "dei" and tx != "srt"
                for node in cs.values() for fs in node.get("units", {}).values() for x in fs}
    out = []
    for i, form in enumerate(rec.get("form", [])):
        if form in SUPPLEMENT_FORMS and rec["isXBRL"][i] and rec["filingDate"][i] >= since \
                and rec["accessionNumber"][i] not in have_fin:
            out.append({"form": form, "filed": rec["filingDate"][i], "accn": rec["accessionNumber"][i],
                        "report": rec["reportDate"][i], "in_companyfacts_dei_only": rec["accessionNumber"][i] in have})
    return out


def filing_facts(cik: int, filing: Dict[str, str], refresh: bool = False) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Hechos de la instancia XBRL de un filing (caché en disco) y su meta (fichero, segundos, bytes)."""
    acc = filing["accn"].replace("-", "")
    idx, _ = fetch_json(f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/index.json", f"idx-{acc}", refresh)
    names = [i["name"] for i in (idx or {}).get("directory", {}).get("item", [])]
    inst = next((n for n in names if n.endswith("_htm.xml")), None)
    if not inst:
        return {}, {"file": None}
    path = CACHE / f"inst-{acc}-{inst}"
    meta = {"file": inst}
    if path.exists() and not refresh:
        body = path.read_bytes()
    else:
        body, status, secs = _get(f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/{inst}")
        meta.update(status=status, seconds=round(secs, 3))
        if body is None:
            return {}, meta
        path.write_bytes(body)
    meta["bytes"] = len(body)
    return parse_instance(body, filing["form"], filing["filed"], filing["accn"]), meta


def supplement(cik: int, facts: Dict[str, Any], refresh: bool = False) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """companyfacts + los filings con XBRL que le faltan (leídos de su instancia)."""
    added = []
    for fl in missing_filings(cik, facts):
        extra, meta = filing_facts(cik, fl, refresh)
        if not extra:
            continue
        pred = facts.get("predecessor")
        facts = merge_facts(facts, {"facts": extra})
        facts.pop("predecessor", None)
        if pred:
            facts["predecessor"] = pred
        added.append({**fl, **meta})
    return facts, added
