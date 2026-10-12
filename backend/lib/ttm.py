"""
Datos TTM a partir de los estados TRIMESTRALES (etapa 7).

En prod el plan B usa estados anuales (RECON §7.1): flujos y márgenes pueden
llevar hasta 12 meses de retraso. Aquí se construye el TTM:
  · flujos y resultados: suma de los 4 últimos trimestres, solo si son
    CONSECUTIVOS (separación de un trimestre entre fechas) y todos tienen dato;
  · balance: el último trimestre.
Si no hay 4 trimestres consecutivos de un concepto, ese concepto se queda con el
valor anual y el motivo se registra (data_provenance.ttm).

Qué pasa a TTM y qué sigue anual (decisión de la etapa 7):
  TTM     ingresos, beneficio bruto/operativo/neto, EBITDA, intereses, D&A, OCF,
          capex, FCF, dividendos -> P/E, P/FCF, P/S, EV/EBITDA, FCF yield,
          márgenes, ROE/ROA/ROIC, cobertura de intereses, payout, FCF/beneficio.
  Último trimestre  activos, circulante, deuda, caja, patrimonio, pasivo,
          beneficios retenidos -> current ratio, D/E, deuda neta, DN/EBITDA, P/B.
  Anual   todo lo que se define sobre ejercicios: CAGR (ingresos, FCF, FFO por
          acción, valor en libros, acciones), Piotroski (FY frente a FY), Altman
          (estados del último FY), ROCE y su promedio de ciclo, el clasificador
          y las métricas normalizadas de ciclo y de FINANCIAL.
"""
from typing import Any, Dict, List, Optional

# info key -> (estado trimestral, fila de Yahoo, tipo)
FLOW_KEYS = {
    "totalRevenue": ("inc", "Total Revenue"),
    "grossProfits": ("inc", "Gross Profit"),
    "operatingIncome": ("inc", "Operating Income"),
    "netIncome": ("inc", "Net Income"),
    "ebitda": ("inc", "EBITDA"),
    "interestExpense": ("inc", "Interest Expense"),
    "depreciation": ("cf", "Depreciation And Amortization"),
    "operatingCashflow": ("cf", "Operating Cash Flow"),
    "capitalExpenditures": ("cf", "Capital Expenditure"),
    "freeCashflow": ("cf", "Free Cash Flow"),
    "dividendsPaid": ("cf", "Common Stock Dividend Paid"),
}
BALANCE_KEYS = {
    "totalAssets": "Total Assets",
    "totalCurrentAssets": "Current Assets",
    "totalCurrentLiabilities": "Current Liabilities",
    "totalDebt": "Total Debt",
    "longTermDebt": "Long Term Debt",
    "totalStockholderEquity": "Stockholders Equity",
    "totalLiab": "Total Liabilities Net Minority Interest",
    "retainedEarnings": "Retained Earnings",
    "inventory": "Inventory",
}
CASH_ROWS = ("Cash Cash Equivalents And Short Term Investments", "Cash And Cash Equivalents")

# Filas trimestrales que necesita la normalización (lib/normalize.py).
QUARTERLY_ROWS = (
    "Total Revenue", "Operating Income", "Pretax Income", "Tax Provision", "Net Income",
    "Diluted Average Shares", "Total Unusual Items", "Total Unusual Items Excluding Goodwill",
    "Special Income Charges", "Other Special Charges", "Restructuring And Mergern Acquisition",
    "Gain On Sale Of Security", "Gain On Sale Of Ppe", "Gain On Sale Of Business", "Write Off",
    "Asset Impairment Charge", "Impairment Of Capital Assets", "Tax Effect Of Unusual Items",
)

MIN_GAP_DAYS, MAX_GAP_DAYS = 80, 100     # un trimestre entre fechas consecutivas


def _num(v) -> Optional[float]:
    try:
        f = float(v)
        return f if f == f else None
    except (TypeError, ValueError):
        return None


def frame_series(df, row: str, n: int = 8) -> List[Optional[float]]:
    """Valores de una fila (más reciente primero); [] si la fila no existe."""
    if df is None or getattr(df, "empty", True) or row not in df.index:
        return []
    return [_num(v) for v in df.loc[row].tolist()[:n]]


def frame_dates(df, n: int = 8) -> List[str]:
    try:
        return [str(c.date()) for c in df.columns][:n] if df is not None and not df.empty else []
    except Exception:
        return []


def consecutive(dates: List[str], k: int = 4) -> bool:
    """¿Las k primeras fechas son trimestres consecutivos?"""
    import datetime as _dt
    if len(dates) < k:
        return False
    d = [_dt.date.fromisoformat(x) for x in dates[:k]]
    return all(MIN_GAP_DAYS <= (d[i] - d[i + 1]).days <= MAX_GAP_DAYS for i in range(k - 1))


def build_ttm(q_inc, q_cf, q_bs) -> Dict[str, Any]:
    """{values: {info_key: valor TTM}, missing: {info_key: motivo}, quarters, balance_date,
    quarterly: {fila: serie}} a partir de los tres estados trimestrales (o None)."""
    frames = {"inc": q_inc, "cf": q_cf}
    out: Dict[str, Any] = {"values": {}, "missing": {}, "quarters": {}, "balance_date": None, "quarterly": {}}
    for st, df in frames.items():
        dates = frame_dates(df)
        out["quarters"][st] = dates[:4]
        ok = consecutive(dates)
        for key, (src, row) in FLOW_KEYS.items():
            if src != st:
                continue
            vals = frame_series(df, row)[:4]
            if not dates:
                out["missing"][key] = "sin estados trimestrales"
            elif not ok:
                out["missing"][key] = "los 4 últimos trimestres no son consecutivos"
            elif len(vals) < 4 or any(v is None for v in vals):
                out["missing"][key] = f"'{row}' sin dato en alguno de los 4 últimos trimestres"
            else:
                out["values"][key] = sum(vals)
    bdates = frame_dates(q_bs)
    if bdates:
        out["balance_date"] = bdates[0]
        for key, row in BALANCE_KEYS.items():
            v = (frame_series(q_bs, row) or [None])[0]
            if v is not None:
                out["values"][key] = v
            else:
                out["missing"][key] = f"'{row}' sin dato en el último trimestre"
        cash = next((v for v in ((frame_series(q_bs, r) or [None])[0] for r in CASH_ROWS) if v is not None), None)
        if cash is not None:
            out["values"]["cash"] = cash
    else:
        for key in (*BALANCE_KEYS, "cash"):
            out["missing"][key] = "sin balance trimestral"
    inc_dates = frame_dates(q_inc)
    out["quarterly"] = {"dates": inc_dates, **{r: frame_series(q_inc, r) for r in QUARTERLY_ROWS
                                                 if frame_series(q_inc, r)}}
    return out
