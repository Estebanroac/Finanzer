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
    # Fase 1: resultado financiero neto (ingresos − gastos financieros) para el estado de la cobertura.
    "netInterestIncome": ("inc", "Net Non Operating Interest Income Expense"),
    "depreciation": ("cf", "Depreciation And Amortization"),
    "operatingCashflow": ("cf", "Operating Cash Flow"),
    "capitalExpenditures": ("cf", "Capital Expenditure"),
    "freeCashflow": ("cf", "Free Cash Flow"),
    "dividendsPaid": ("cf", "Common Stock Dividend Paid"),
    # Etapa 9a: compensación en acciones (FCF − SBC en GROWTH_PRE_PROFIT).
    "stockBasedCompensation": ("cf", "Stock Based Compensation"),
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
TTM_QUARTERS = 4                          # doce meses = cuatro trimestres (definición)


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


# Fase 2b (T3, F2_PRECEDENCIA §1): el corte es el último trimestre con estas filas en 4 trimestres consecutivos que
# acaban en él y con balance a esa fecha. Todo lo de los estados se toma a ese corte ("avanzan todos o ninguno").
CORE_ROWS = ("Total Revenue", "Net Income")
CF_CORE_ROW = "Operating Cash Flow"


def _window(df, dates: List[str], end: str, row: str) -> Optional[List[float]]:
    """Los 4 valores de `row` en los trimestres consecutivos que acaban en `end` (None si falta alguno)."""
    if end not in dates:
        return None
    i = dates.index(end)
    if not consecutive(dates[i:], TTM_QUARTERS):
        return None
    vals = frame_series(df, row, n=len(dates))[i:i + TTM_QUARTERS]
    return vals if len(vals) == TTM_QUARTERS and all(v is not None for v in vals) else None


def find_cut(q_inc, q_bs, q_cf=None) -> Optional[str]:
    """Fecha del corte trimestral, o None (corte anual): el último trimestre con los estados completos (ingresos y
    beneficio de 4 trimestres consecutivos que acaban en él, balance a esa fecha y, si el emisor presenta flujos
    trimestrales, el flujo de operaciones de esos mismos 4 trimestres). ASML, AMZN y BAC: los flujos o el balance
    llegan a marzo y los resultados a junio → el corte es marzo."""
    inc_dates, bs_dates, cf_dates = frame_dates(q_inc), frame_dates(q_bs), frame_dates(q_cf)
    cf_core = bool(cf_dates) and q_cf is not None and CF_CORE_ROW in q_cf.index
    for d in inc_dates:
        if all(_window(q_inc, inc_dates, d, r) is not None for r in CORE_ROWS) and d in bs_dates \
                and frame_series(q_bs, "Total Assets", n=len(bs_dates))[bs_dates.index(d)] is not None \
                and (not cf_core or _window(q_cf, cf_dates, d, CF_CORE_ROW) is not None):
            return d
    return None


def build_ttm(q_inc, q_cf, q_bs) -> Dict[str, Any]:
    """{cut, values: {info_key: valor del corte}, missing: {info_key: motivo}, quarters, balance_date,
    quarterly: {fila: serie desde el corte}} a partir de los tres estados trimestrales (o None).

    Fase 2b: un solo corte para todo (find_cut). Sin corte trimestral no se toma nada de los trimestrales: el
    análisis va entero en el ejercicio (flujos y balance del último FY)."""
    frames = {"inc": q_inc, "cf": q_cf}
    out: Dict[str, Any] = {"cut": None, "values": {}, "missing": {}, "quarters": {}, "balance_date": None,
                           "quarterly": {}, "quarter_min": {}}
    cut = find_cut(q_inc, q_bs, q_cf)
    out["cut"] = cut
    for st, df in frames.items():
        dates = frame_dates(df)
        out["quarters"][st] = (dates[dates.index(cut):dates.index(cut) + TTM_QUARTERS]
                               if cut and cut in dates else [])
        for key, (src, row) in FLOW_KEYS.items():
            if src != st:
                continue
            if not dates:
                out["missing"][key] = "sin estados trimestrales"
                continue
            if cut is None:
                out["missing"][key] = ("sin corte trimestral (ingresos y beneficio de 4 trimestres consecutivos con "
                                       "balance): el dato es el del ejercicio")
                continue
            vals = _window(df, dates, cut, row)
            if vals is None:
                out["missing"][key] = (f"'{row}' sin dato en alguno de los 4 trimestres del corte ({cut})"
                                       if cut in dates and row in df.index else
                                       f"'{row}' no llega al corte ({cut})")
                continue
            out["values"][key] = sum(vals)
            out["quarter_min"][key] = min(vals)   # fase 1: el signo de un flujo no lo decide un trimestre atípico
    bdates = frame_dates(q_bs)
    if cut and cut in bdates:
        i = bdates.index(cut)
        out["balance_date"] = cut
        for key, row in BALANCE_KEYS.items():
            v = (frame_series(q_bs, row, n=len(bdates))[i:i + 1] or [None])[0]
            if v is not None:
                out["values"][key] = v
            else:
                out["missing"][key] = f"'{row}' sin dato en el balance del corte ({cut})"
        cash = next((v for v in ((frame_series(q_bs, r, n=len(bdates))[i:i + 1] or [None])[0] for r in CASH_ROWS)
                     if v is not None), None)
        if cash is not None:
            out["values"]["cash"] = cash
    else:
        why = "sin balance trimestral" if not bdates else "sin corte trimestral: el balance es el del ejercicio"
        for key in (*BALANCE_KEYS, "cash"):
            out["missing"][key] = why
    inc_dates = frame_dates(q_inc)
    k = inc_dates.index(cut) if cut and cut in inc_dates else len(inc_dates)
    out["quarterly"] = {"dates": inc_dates[k:], **{r: frame_series(q_inc, r)[k:] for r in QUARTERLY_ROWS
                                                   if frame_series(q_inc, r)[k:]}}
    return out
