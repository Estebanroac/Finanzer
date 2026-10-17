"""F3 · T1: profundidad de la historia anual en companyfacts (caché local de la 2a) por campo y ticker.

Para cada ejercicio (duración 350–380 días, formularios anuales; saldos: fin de ejercicio) toma el primer concepto
de la lista que lo tenga (las etiquetas cambian con los años: ASC 606 en 2018). Cuenta ejercicios distintos.
uso: python3 tests/f3_t1_depth.py  → tabla markdown en stdout
"""
import json
import sys
from datetime import date
from pathlib import Path

B = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(B))
RAW = B / "tests/fixtures/edgar/raw"
EXT = B / "tests/fixtures/edgar"
ANNUAL = {"10-K", "10-K/A", "20-F", "20-F/A", "40-F", "10-KT"}

US = {
    "ingresos": ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax",
                 "RevenueFromContractWithCustomerIncludingAssessedTax", "SalesRevenueNet", "SalesRevenueGoodsNet",
                 "RevenuesNetOfInterestExpense", "RegulatedAndUnregulatedOperatingRevenue"],
    "ebit": ["OperatingIncomeLoss"],
    "bpa_dil": ["EarningsPerShareDiluted", "EarningsPerShareBasicAndDiluted"],
    "acciones_dil": ["WeightedAverageNumberOfDilutedSharesOutstanding"],
    "ocf": ["NetCashProvidedByUsedInOperatingActivities",
            "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"],
    "capex": ["PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsToAcquireProductiveAssets"],
}
IFRS = {
    "ingresos": ["Revenue", "RevenueFromContractsWithCustomers", "RevenueAndOperatingIncome"],
    "ebit": ["ProfitLossFromOperatingActivities"],
    "bpa_dil": ["DilutedEarningsLossPerShare", "DilutedEarningsLossPerShareFromContinuingOperations"],
    "acciones_dil": ["AdjustedWeightedAverageShares", "WeightedAverageShares"],
    "ocf": ["CashFlowsFromUsedInOperatingActivities", "CashFlowsFromUsedInOperations"],
    "capex": ["PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities", "PurchaseOfPropertyPlantAndEquipment"],
}
PRED = {"XOM": [34088]}


def days(f):
    if "start" not in f:
        return 0
    return (date.fromisoformat(f["end"]) - date.fromisoformat(f["start"])).days


def years(facts, tax, concepts):
    ends = {}
    for c in concepts:
        node = (facts.get(tax) or {}).get(c)
        if not node:
            continue
        for u, fs in node["units"].items():
            for f in fs:
                if f.get("form") in ANNUAL and 350 <= days(f) <= 380:
                    y = f["end"][:7]
                    ends.setdefault(y, c)
    return sorted(ends)


def main():
    tickers = sorted(p.stem for p in EXT.glob("*.json") if p.stem not in ("SPY",))
    hdr = ["ticker", "tax", "desde"] + list(US)
    print("| " + " | ".join(hdr) + " |")
    print("|" + "---|" * len(hdr))
    for t in tickers:
        ext = json.loads((EXT / f"{t}.json").read_text())
        if not isinstance(ext, dict):
            continue
        ciks = [int(ext["cik"])] + PRED.get(t, [])
        facts = {}
        for cik in ciks:
            p = RAW / f"CIK{cik:010d}.facts.json"
            if not p.exists():
                continue
            for tx, cs in json.loads(p.read_text())["facts"].items():
                for c, node in cs.items():
                    dst = facts.setdefault(tx, {}).setdefault(c, {"units": {}})
                    for u, fs in node["units"].items():
                        dst["units"].setdefault(u, []).extend(fs)
        def last_assets(tx):
            n = (facts.get(tx) or {}).get("Assets")
            return max((f["end"] for fs in (n or {"units": {}})["units"].values() for f in fs), default="")
        tax = "ifrs-full" if last_assets("ifrs-full") > last_assets("us-gaap") else "us-gaap"
        M = IFRS if tax == "ifrs-full" else US
        cells, first = [], None
        for k, cs in M.items():
            ys = years(facts, tax, cs)
            cells.append(str(len(ys)))
            if k == "ingresos" and ys:
                first = ys[0][:4]
        print(f"| {t} | {tax.split('-')[0]} | {first or '—'} | " + " | ".join(cells) + " |")


if __name__ == "__main__":
    main()
