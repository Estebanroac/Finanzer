"""
Yahoo Finance Adapter — DIRECT API version
Uses Yahoo v10/quoteSummary API directly via curl_cffi (ONE call for everything)
~4 seconds vs ~40 seconds with yfinance wrapper
"""
import logging
import time
import threading
from typing import Dict, Any

logger = logging.getLogger(__name__)

# ── Session management (crumb auth, reusable) ──
_session = None
_crumb = None
_session_lock = threading.Lock()

# ── In-memory cache ──
_cache: Dict[str, tuple] = {}   # symbol -> (ts, info, degraded)
_locks: Dict[str, threading.Lock] = {}
_global_lock = threading.Lock()
CACHE_TTL = 300  # 5 minutes
# Un snapshot DEGRADADO caduca rápido para auto-repararse en el siguiente fetch
CACHE_TTL_DEGRADED = 60

# ── Resiliencia ante respuestas degradadas de Yahoo ──
# Desde IPs de datacenter (Render), Yahoo devuelve intermitentemente respuestas
# con la mitad de los campos (rate limit suave). Tres defensas:
#   1) detectar el snapshot degradado y REINTENTAR con sesión/crumb frescos y
#      otro perfil de navegador;
#   2) cachearlo poco tiempo (CACHE_TTL_DEGRADED);
#   3) rellenar los huecos con el último snapshot BUENO conocido (los
#      fundamentales cambian trimestralmente: un dato de hace una hora es
#      infinitamente mejor que un null).
_IMPERSONATE_PROFILES = ["chrome", "safari15_5", "edge101"]
_profile_idx = 0
_best_cache: Dict[str, tuple] = {}   # symbol -> (ts, info) último snapshot bueno
_BEST_MAX_AGE = 24 * 3600
_NESTED_KEYS = ("_yahoo_ratios", "_prior_year", "_current_derived", "_piotroski_current")

# Campos que prácticamente toda empresa cotizada tiene; si faltan varios, la
# respuesta vino degradada (no confundir con ausencias legítimas: dividendos,
# forward P/E, etc. NO están en esta lista).
_COMPLETENESS_FIELDS = ("beta", "sharesOutstanding", "marketCap",
                        "totalRevenue", "operatingCashflow", "totalCash")

# Firma del modo de degradación REAL observado en producción (Render): Yahoo
# devuelve 200 con financialData intacto pero el cluster summaryDetail/
# defaultKeyStatistics vacío → beta, forwardEps/PE, dividendRate y growth
# llegan null A LA VEZ. Un ticker legítimo casi nunca tiene TODOS estos null
# (beta existe para toda cotizada con >1 año de historia).
_MODULE_B_FIELDS = ("beta", "forwardEps", "forwardPE", "dividendRate",
                    "revenueGrowth", "earningsGrowth")


def _completeness(info) -> int:
    if not isinstance(info, dict) or not info:
        return 0
    return sum(1 for f in _COMPLETENESS_FIELDS if info.get(f) is not None)


def _is_degraded(info) -> bool:
    if not isinstance(info, dict) or not info:
        return True
    # modo 1: media respuesta perdida
    if _completeness(info) < 4:
        return True
    # modo 2: cluster de módulos caído (todos los campos del cluster en null)
    if all(info.get(f) is None for f in _MODULE_B_FIELDS):
        return True
    return False


def _quality(info) -> int:
    """Puntaje total para comparar snapshots en los reintentos (cubre ambos
    modos de degradación: completitud base + presencia del cluster B)."""
    if not isinstance(info, dict) or not info:
        return 0
    return _completeness(info) + sum(1 for f in _MODULE_B_FIELDS if info.get(f) is not None)

# ── Known sectors ──
KNOWN_SECTORS = {
    "AAPL": ("Technology", "Consumer Electronics"),
    "MSFT": ("Technology", "Software—Infrastructure"),
    "GOOGL": ("Communication Services", "Internet Content & Information"),
    "GOOG": ("Communication Services", "Internet Content & Information"),
    "AMZN": ("Consumer Cyclical", "Internet Retail"),
    "NVDA": ("Technology", "Semiconductors"),
    "TSLA": ("Consumer Cyclical", "Auto Manufacturers"),
    "META": ("Communication Services", "Internet Content & Information"),
    "JPM": ("Financial Services", "Banks—Diversified"),
    "V": ("Financial Services", "Credit Services"),
    "TSM": ("Technology", "Semiconductors"),
    "BRK-B": ("Financial Services", "Insurance—Diversified"),
    "JNJ": ("Healthcare", "Drug Manufacturers—General"),
    "PG": ("Consumer Defensive", "Household & Personal Products"),
    "KO": ("Consumer Defensive", "Beverages—Non-Alcoholic"),
    "PFE": ("Healthcare", "Drug Manufacturers—General"),
    "VZ": ("Communication Services", "Telecom Services"),
    "INTC": ("Technology", "Semiconductors"),
    "BMY": ("Healthcare", "Drug Manufacturers—General"),
    "AMD": ("Technology", "Semiconductors"),
    "CRM": ("Technology", "Software—Application"),
    "SHOP": ("Technology", "Software—Application"),
    "SQ": ("Technology", "Software—Infrastructure"),
    "DDOG": ("Technology", "Software—Application"),
    "NET": ("Technology", "Software—Infrastructure"),
    "PEP": ("Consumer Defensive", "Beverages—Non-Alcoholic"),
    "T": ("Communication Services", "Telecom Services"),
    "XOM": ("Energy", "Oil & Gas Integrated"),
    "CVX": ("Energy", "Oil & Gas Integrated"),
    "UNH": ("Healthcare", "Healthcare Plans"),
    "MA": ("Financial Services", "Credit Services"),
    "HD": ("Consumer Cyclical", "Home Improvement Retail"),
    "DIS": ("Communication Services", "Entertainment"),
    "NFLX": ("Communication Services", "Entertainment"),
    "BA": ("Industrials", "Aerospace & Defense"),
    "WMT": ("Consumer Defensive", "Discount Stores"),
    "COST": ("Consumer Defensive", "Discount Stores"),
    "ABBV": ("Healthcare", "Drug Manufacturers—General"),
    "MRK": ("Healthcare", "Drug Manufacturers—General"),
    "LLY": ("Healthcare", "Drug Manufacturers—General"),
    "AVGO": ("Technology", "Semiconductors"),
    "ADBE": ("Technology", "Software—Application"),
    "ORCL": ("Technology", "Software—Infrastructure"),
    "CSCO": ("Technology", "Communication Equipment"),
    "ACN": ("Technology", "Information Technology Services"),
    "TXN": ("Technology", "Semiconductors"),
    "QCOM": ("Technology", "Semiconductors"),
    "IBM": ("Technology", "Information Technology Services"),
    "GS": ("Financial Services", "Capital Markets"),
    "MS": ("Financial Services", "Capital Markets"),
    "BAC": ("Financial Services", "Banks—Diversified"),
    "C": ("Financial Services", "Banks—Diversified"),
    "WFC": ("Financial Services", "Banks—Diversified"),
    "PYPL": ("Financial Services", "Credit Services"),
    "NKE": ("Consumer Cyclical", "Footwear & Accessories"),
    "SBUX": ("Consumer Cyclical", "Restaurants"),
    "MCD": ("Consumer Cyclical", "Restaurants"),
    "F": ("Consumer Cyclical", "Auto Manufacturers"),
    "GM": ("Consumer Cyclical", "Auto Manufacturers"),
    "PLTR": ("Technology", "Software—Application"),
    "SNOW": ("Technology", "Software—Application"),
    "UBER": ("Technology", "Software—Application"),
    "ABNB": ("Consumer Cyclical", "Travel Services"),
    "COIN": ("Financial Services", "Capital Markets"),
    "SOFI": ("Financial Services", "Banks—Diversified"),
    "ARM": ("Technology", "Semiconductors"),
    "SMCI": ("Technology", "Computer Hardware"),
}


def _get_symbol_lock(symbol: str) -> threading.Lock:
    with _global_lock:
        if symbol not in _locks:
            _locks[symbol] = threading.Lock()
        return _locks[symbol]


def _ensure_session():
    """Initialize curl_cffi session with Yahoo auth crumb (once)."""
    global _session, _crumb
    if _session is not None and _crumb is not None:
        return

    with _session_lock:
        if _session is not None and _crumb is not None:
            return

        from curl_cffi import requests as cffi_requests
        profile = _IMPERSONATE_PROFILES[_profile_idx % len(_IMPERSONATE_PROFILES)]
        try:
            _session = cffi_requests.Session(impersonate=profile)
        except Exception:
            # perfil no soportado por esta versión de curl_cffi -> el estándar
            _session = cffi_requests.Session(impersonate="chrome")
            profile = "chrome"

        # Get cookies
        _session.get("https://finance.yahoo.com")

        # Get crumb
        r = _session.get("https://query2.finance.yahoo.com/v1/test/getcrumb")
        _crumb = r.text
        logger.info(f"[AUTH] Yahoo session initialized ({profile}), crumb={_crumb[:8]}...")


def _reset_session(rotate_profile: bool = False):
    """Fuerza una sesión/crumb nuevos en el próximo _ensure_session.

    rotate_profile: cambia el navegador imitado (chrome -> safari -> edge) —
    ante un rate limit suave, un fingerprint distinto suele recibir la
    respuesta completa.
    """
    global _session, _crumb, _profile_idx
    with _session_lock:
        _session = None
        _crumb = None
        if rotate_profile:
            _profile_idx += 1


def _raw(obj, default=None):
    """Extract 'raw' value from Yahoo API response object."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get("raw", default)
    return obj


def get_ticker_info(symbol: str) -> Dict[str, Any]:
    """
    FAST replacement for ticker.info — uses Yahoo v10 API directly.
    Single HTTP call returns ALL financial data.
    """
    symbol = symbol.upper()

    def _cache_fresh():
        entry = _cache.get(symbol)
        if not entry:
            return None
        ts, cached_data, degraded = entry
        ttl = CACHE_TTL_DEGRADED if degraded else CACHE_TTL
        if time.time() - ts < ttl:
            return cached_data
        return None

    # Check cache
    cached = _cache_fresh()
    if cached is not None:
        logger.info(f"[CACHE HIT] {symbol}")
        return cached

    # Per-symbol lock
    lock = _get_symbol_lock(symbol)
    with lock:
        # Double-check
        cached = _cache_fresh()
        if cached is not None:
            logger.info(f"[CACHE HIT after lock] {symbol}")
            return cached

        info = _do_fetch(symbol)

        # ── Defensa 1: reintento ante respuesta degradada ──
        attempts = 0
        while _is_degraded(info) and attempts < 2:
            attempts += 1
            logger.warning(
                f"[DEGRADED] {symbol}: {_completeness(info)}/{len(_COMPLETENESS_FIELDS)} "
                f"campos clave; reintento {attempts} con sesión fresca")
            _reset_session(rotate_profile=True)
            time.sleep(0.8 * attempts)
            try:
                retry_info = _do_fetch(symbol)
            except Exception as e:
                logger.warning(f"[DEGRADED] reintento falló para {symbol}: {e}")
                break
            if _quality(retry_info) > _quality(info):
                info = retry_info

        degraded = _is_degraded(info)

        # ── Defensa 3: rellenar huecos con el último snapshot bueno ──
        info = _merge_last_known_good(symbol, info, degraded)

        # ── Defensa 4: fuente secundaria (Finnhub) para lo que Yahoo bloquea
        # persistentemente desde IPs de datacenter (beta/forward/dividendo/growth
        # y los estados históricos para Piotroski). Inerte si no hay API key.
        try:
            from finnhub_fallback import enrich_info, is_enabled, should_fill
            if is_enabled() and (degraded or should_fill(info)):
                info = enrich_info(info, symbol)
                degraded = _is_degraded(info)  # recomputar tras el relleno
        except Exception as e:
            logger.warning(f"[FINNHUB] enrich falló para {symbol}: {e}")

        # ── Defensa 2: los snapshots degradados caducan rápido ──
        _cache[symbol] = (time.time(), info, degraded)
        return info


def _merge_last_known_good(symbol: str, fresh: Dict[str, Any], fresh_degraded: bool) -> Dict[str, Any]:
    """Rellena los None del fetch fresco con el último snapshot bueno (<24h).

    La edad del 'mejor conocido' solo se renueva cuando el fetch fue COMPLETO;
    si solo llegan fetches degradados, el relleno caduca a las 24h en vez de
    perpetuarse con datos viejos.
    """
    now = time.time()
    ts_best, best = _best_cache.get(symbol, (0.0, None))
    merged = dict(fresh)

    if best and (now - ts_best) < _BEST_MAX_AGE:
        filled = 0
        for k, v in best.items():
            if k in _NESTED_KEYS:
                continue
            if merged.get(k) is None and v is not None:
                merged[k] = v
                filled += 1
        for nk in _NESTED_KEYS:
            bsub = best.get(nk)
            if not isinstance(bsub, dict):
                continue
            msub = dict(merged.get(nk) or {})
            for k, v in bsub.items():
                if msub.get(k) is None and v is not None:
                    msub[k] = v
                    filled += 1
            merged[nk] = msub
        if filled:
            logger.info(f"[LKG] {symbol}: {filled} campos rellenados del último snapshot bueno")

    if not fresh_degraded:
        _best_cache[symbol] = (now, merged)
    elif best is not None:
        _best_cache[symbol] = (ts_best, merged)
    else:
        _best_cache[symbol] = (now, merged)
    return merged


def _refresh_crumb():
    """Refresh the Yahoo auth crumb."""
    global _crumb
    try:
        r = _session.get("https://query2.finance.yahoo.com/v1/test/getcrumb")
        _crumb = r.text
        logger.info(f"[AUTH] Crumb refreshed: {_crumb[:8]}...")
    except Exception as e:
        logger.error(f"Crumb refresh failed: {e}")


def _do_fetch(symbol: str) -> Dict[str, Any]:
    """Fetch all data from Yahoo v10 API in ONE call."""
    t0 = time.time()

    _ensure_session()

    modules = [
        "financialData", "defaultKeyStatistics", "assetProfile",
        "price", "summaryDetail",
        "incomeStatementHistory", "balanceSheetHistory",
        "cashflowStatementHistory",
        "earnings",  # yearly revenue + earnings for prior-year comparisons
    ]

    url = f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{symbol}"
    params = {"modules": ",".join(modules), "crumb": _crumb}

    try:
        r = _session.get(url, params=params, timeout=15)
    except Exception as e:
        logger.error(f"Yahoo API request failed for {symbol}: {e}")
        return _fallback_yfinance(symbol)

    if r.status_code != 200:
        logger.warning(f"Yahoo API {r.status_code} for {symbol}, refreshing crumb...")
        _refresh_crumb()
        params["crumb"] = _crumb
        try:
            r = _session.get(url, params=params, timeout=15)
        except Exception:
            pass

        if r.status_code != 200:
            logger.error(f"Yahoo API failed for {symbol}: {r.status_code}")
            return _fallback_yfinance(symbol)

    try:
        data = r.json()["quoteSummary"]["result"][0]
    except (KeyError, IndexError, TypeError):
        logger.error(f"Invalid response structure for {symbol}")
        return _fallback_yfinance(symbol)

    # Extract all modules
    fd = data.get("financialData", {})
    kstat = data.get("defaultKeyStatistics", {})
    profile = data.get("assetProfile", {})
    price_data = data.get("price", {})
    summary = data.get("summaryDetail", {})

    # Income statement history
    inc_stmts = data.get("incomeStatementHistory", {}).get("incomeStatementHistory", [])
    latest_inc = inc_stmts[0] if inc_stmts else {}
    prev_inc = inc_stmts[1] if len(inc_stmts) > 1 else {}

    # Balance sheet
    bs_stmts = data.get("balanceSheetHistory", {}).get("balanceSheetStatements", [])
    latest_bs = bs_stmts[0] if bs_stmts else {}

    # Cash flow
    cf_stmts = data.get("cashflowStatementHistory", {}).get("cashflowStatements", [])
    latest_cf = cf_stmts[0] if cf_stmts else {}

    # Sector from API or known list
    sector = profile.get("sector")
    industry = profile.get("industry")
    if not sector:
        sd = KNOWN_SECTORS.get(symbol)
        sector = sd[0] if sd else "Unknown"
        industry = sd[1] if sd else "Unknown"

    # Company name
    long_name = price_data.get("longName") or price_data.get("shortName", symbol)
    # Try stock_database for better names
    try:
        from stock_database import POPULAR_STOCKS
        db_name = POPULAR_STOCKS.get(symbol)
        if db_name:
            long_name = db_name
    except Exception:
        pass

    # Build info dict
    current_price = _raw(price_data.get("regularMarketPrice"))
    market_cap = _raw(price_data.get("marketCap")) or _raw(summary.get("marketCap"))
    shares = _raw(kstat.get("impliedSharesOutstanding")) or _raw(kstat.get("sharesOutstanding"))

    # ── Income statement: financialData is primary, incomeStatementHistory is backup ──
    revenue = _raw(fd.get("totalRevenue")) or _raw(latest_inc.get("totalRevenue"))
    gross_profit = _raw(fd.get("grossProfits")) or _raw(latest_inc.get("grossProfit"))
    operating_income = _raw(latest_inc.get("operatingIncome")) or _raw(fd.get("operatingIncome"))
    net_income = _raw(kstat.get("netIncomeToCommon")) or _raw(latest_inc.get("netIncome"))
    ebitda = _raw(fd.get("ebitda")) or _raw(latest_inc.get("ebitda"))
    interest_expense = _raw(latest_inc.get("interestExpense"))

    # Estimate operating_income if missing: EBITDA - Depreciation, or Revenue * operating_margin
    if operating_income is None and ebitda:
        dep = _raw(latest_cf.get("depreciation")) if cf_stmts else None
        if dep:
            operating_income = ebitda - abs(dep)
        elif _raw(fd.get("operatingMargins")) and revenue:
            operating_income = revenue * _raw(fd.get("operatingMargins"))
    elif operating_income is None and _raw(fd.get("operatingMargins")) and revenue:
        operating_income = revenue * _raw(fd.get("operatingMargins"))

    # ── Balance sheet: use financialData (always available) + balanceSheetHistory as backup ──
    total_assets = _raw(latest_bs.get("totalAssets"))
    current_assets = _raw(latest_bs.get("totalCurrentAssets"))
    current_liab = _raw(latest_bs.get("totalCurrentLiabilities"))
    total_debt = _raw(fd.get("totalDebt")) or _raw(latest_bs.get("longTermDebt"))
    long_term_debt = _raw(latest_bs.get("longTermDebt"))
    total_equity = _raw(latest_bs.get("totalStockholderEquity"))
    total_liab = _raw(latest_bs.get("totalLiab"))
    cash = (_raw(fd.get("totalCash"))
            or _raw(latest_bs.get("cashAndShortTermInvestments"))
            or _raw(latest_bs.get("cashCashEquivalentsAndShortTermInvestments"))
            or _raw(latest_bs.get("cash")))
    retained_earnings = _raw(latest_bs.get("retainedEarnings"))
    inventory = _raw(latest_bs.get("inventory"))

    # Estimate interest_expense from total_debt (approx 4% rate)
    if interest_expense is None and total_debt:
        interest_expense = -(total_debt * 0.04)  # negative convention

    # Estimate total_assets from market cap / ROA if not available
    roa = _raw(fd.get("returnOnAssets"))
    if total_assets is None and roa and net_income and roa != 0:
        total_assets = net_income / roa

    # Estimate equity from ROE
    roe_raw = _raw(fd.get("returnOnEquity"))
    if total_equity is None and roe_raw and net_income and roe_raw != 0:
        total_equity = net_income / roe_raw

    # Estimate current_assets/liabilities from currentRatio
    current_ratio_raw = _raw(fd.get("currentRatio"))
    if current_liab is None and current_ratio_raw and cash and total_debt:
        # crude estimate
        current_liab = cash / current_ratio_raw if current_ratio_raw > 0 else None
    if current_assets is None and current_ratio_raw and current_liab:
        current_assets = current_ratio_raw * current_liab

    # Estimate total_liab
    if total_liab is None and total_assets and total_equity:
        total_liab = total_assets - total_equity

    # ── Cash flow ──
    operating_cf = _raw(fd.get("operatingCashflow")) or _raw(latest_cf.get("totalCashFromOperatingActivities"))
    capex = _raw(latest_cf.get("capitalExpenditures"))
    fcf = _raw(fd.get("freeCashflow")) or _raw(latest_cf.get("totalCashFromFinancingActivities"))
    if fcf is None and operating_cf and capex:
        fcf = operating_cf + capex
    dividends_paid = _raw(latest_cf.get("dividendsPaid"))
    depreciation = _raw(latest_cf.get("depreciation"))

    # ── Earnings module (yearly revenue + net income for up to 4 years) ──
    earnings_data = data.get("earnings", {})
    yearly_financials = earnings_data.get("financialsChart", {}).get("yearly", [])

    # Sort by date descending, the last entry is most recent
    yearly_financials.sort(key=lambda x: x.get("date", 0), reverse=True)
    current_year_earn = yearly_financials[0] if len(yearly_financials) > 0 else {}
    prior_year_earn = yearly_financials[1] if len(yearly_financials) > 1 else {}

    # Prior-year revenue and earnings from earnings module (most reliable)
    earn_prev_rev = _raw(prior_year_earn.get("revenue"))
    earn_prev_ni = _raw(prior_year_earn.get("earnings"))

    # ── Prior-year balance sheet (for Piotroski, Z-Score comparison) ──
    prev_bs = bs_stmts[1] if len(bs_stmts) > 1 else {}
    prev_cf = cf_stmts[1] if len(cf_stmts) > 1 else {}

    prev_total_assets = _raw(prev_bs.get("totalAssets"))
    prev_current_assets = _raw(prev_bs.get("totalCurrentAssets"))
    prev_current_liab = _raw(prev_bs.get("totalCurrentLiabilities"))
    prev_long_term_debt = _raw(prev_bs.get("longTermDebt"))
    prev_equity = _raw(prev_bs.get("totalStockholderEquity"))
    prev_shares = _raw(prev_bs.get("commonStockSharesOutstanding")) or shares
    prev_inventory = _raw(prev_bs.get("inventory"))
    prev_gross_profit = _raw(prev_inc.get("grossProfit"))
    prev_operating_cf = _raw(prev_cf.get("totalCashFromOperatingActivities"))

    # Use earnings module as fallback for prior-year data
    prev_ni = _raw(prev_inc.get("netIncome")) or earn_prev_ni
    prev_rev = _raw(prev_inc.get("totalRevenue")) or earn_prev_rev

    # Estimate prior total_assets from current total_assets ratio (if we have earnings module data)
    if prev_total_assets is None and total_assets and earn_prev_ni and net_income and net_income > 0:
        # Assume similar ROA → prior assets ≈ current assets * (prior_NI / current_NI)
        # But simpler: assume assets grew proportionally to revenue
        if prev_rev and revenue and revenue > 0:
            prev_total_assets = total_assets * (prev_rev / revenue)

    # Prior-year ratios
    prev_roa = None
    if prev_ni and prev_total_assets and prev_total_assets > 0:
        prev_roa = prev_ni / prev_total_assets

    prev_current_ratio = None
    if prev_current_assets and prev_current_liab and prev_current_liab > 0:
        prev_current_ratio = prev_current_assets / prev_current_liab
    elif current_ratio_raw:
        # Assume prior current ratio was similar (conservative estimate)
        prev_current_ratio = current_ratio_raw

    prev_gross_margin = None
    if prev_gross_profit and prev_rev and prev_rev > 0:
        prev_gross_margin = prev_gross_profit / prev_rev
    elif prev_rev and earn_prev_ni and prev_rev > 0:
        # Estimate: assume gross margin was proportional to net margin ratio
        if revenue and net_income and gross_profit:
            gross_to_net_ratio = gross_profit / net_income if net_income > 0 else 2.5
            prev_gross_margin = (earn_prev_ni * gross_to_net_ratio) / prev_rev

    # Current gross margin
    current_gross_margin = None
    if gross_profit and revenue and revenue > 0:
        current_gross_margin = gross_profit / revenue
    elif _raw(fd.get("grossMargins")):
        current_gross_margin = _raw(fd.get("grossMargins"))

    # Asset turnover
    current_asset_turnover = None
    if revenue and total_assets and total_assets > 0:
        current_asset_turnover = revenue / total_assets

    prev_asset_turnover = None
    if prev_rev and prev_total_assets and prev_total_assets > 0:
        prev_asset_turnover = prev_rev / prev_total_assets

    # Growth rates
    revenue_growth = None
    earnings_growth = None
    if revenue and prev_rev and prev_rev > 0:
        revenue_growth = (revenue - prev_rev) / prev_rev
    if net_income and prev_ni and prev_ni > 0:
        earnings_growth = (net_income - prev_ni) / prev_ni

    # Also try from financialData
    if revenue_growth is None:
        revenue_growth = _raw(fd.get("revenueGrowth"))
    if earnings_growth is None:
        earnings_growth = _raw(fd.get("earningsGrowth"))

    info: Dict[str, Any] = {
        "symbol": symbol,
        "longName": long_name,
        "shortName": price_data.get("shortName", symbol),
        "regularMarketPrice": current_price,
        "currentPrice": current_price,
        "previousClose": _raw(summary.get("previousClose")),
        "marketCap": market_cap,
        "currency": price_data.get("currency", "USD"),
        "exchange": price_data.get("exchangeName", price_data.get("exchange", "Unknown")),
        "fiftyTwoWeekHigh": _raw(summary.get("fiftyTwoWeekHigh")),
        "fiftyTwoWeekLow": _raw(summary.get("fiftyTwoWeekLow")),
        "fiftyDayAverage": _raw(summary.get("fiftyDayAverage")),
        "twoHundredDayAverage": _raw(summary.get("twoHundredDayAverage")),
        "volume": _raw(summary.get("volume")),
        "averageVolume": _raw(summary.get("averageVolume")),
        "shares": shares,
        "sharesOutstanding": shares,
        "sector": sector,
        "industry": industry,
        "country": profile.get("country", "Unknown"),
        "longBusinessSummary": profile.get("longBusinessSummary", "")[:500],

        # Income statement
        "totalRevenue": revenue,
        "grossProfits": gross_profit,
        "operatingIncome": operating_income,
        "netIncome": net_income,
        "ebitda": ebitda,
        "trailingEps": _raw(kstat.get("trailingEps")) or _raw(summary.get("trailingEps")),
        "forwardEps": _raw(kstat.get("forwardEps")),
        "interestExpense": interest_expense,
        "depreciation": depreciation,

        # Balance sheet
        "totalAssets": total_assets,
        "totalCurrentAssets": current_assets,
        "totalCurrentLiabilities": current_liab,
        "totalDebt": total_debt,
        "longTermDebt": long_term_debt,
        "totalStockholderEquity": total_equity,
        "totalLiab": total_liab,
        "cash": cash,
        "retainedEarnings": retained_earnings,
        "inventory": inventory,

        # Cash flow
        "operatingCashflow": operating_cf,
        "capitalExpenditures": capex,
        "freeCashflow": fcf,
        "dividendsPaid": dividends_paid,

        # Market data
        "beta": _raw(kstat.get("beta")) or _raw(summary.get("beta")),  # None if unavailable; fallback in main.py
        "trailingPE": _raw(summary.get("trailingPE")),
        "forwardPE": _raw(summary.get("forwardPE")) or _raw(kstat.get("forwardPE")),
        "priceToBook": _raw(kstat.get("priceToBook")),
        "dividendYield": _raw(summary.get("dividendYield")),
        "dividendRate": _raw(summary.get("dividendRate")),
        "payoutRatio": _raw(summary.get("payoutRatio")),

        # Growth
        "revenueGrowth": revenue_growth,
        "earningsGrowth": earnings_growth,

        # Book value
        "bookValue": _raw(kstat.get("bookValue")),

        # ── Prior-year data (for Piotroski F-Score, comparisons) ──
        "_prior_year": {
            "roa": prev_roa,
            "net_income": prev_ni,
            "total_assets": prev_total_assets,
            "long_term_debt": prev_long_term_debt,
            "current_ratio": prev_current_ratio,
            "shares": prev_shares,
            "gross_margin": prev_gross_margin,
            "asset_turnover": prev_asset_turnover,
            "operating_cash_flow": prev_operating_cf,
            "equity": prev_equity,
            "revenue": prev_rev,
        },
        "_current_derived": {
            "gross_margin": current_gross_margin,
            "asset_turnover": current_asset_turnover,
        },
        # ── Yearly earnings chart (for historical trends) ──
        "_yearly_financials": [
            {"year": y.get("date"), "revenue": _raw(y.get("revenue")), "earnings": _raw(y.get("earnings"))}
            for y in yearly_financials
        ],

        # ── Pre-computed ratios from Yahoo (used as fallbacks if calculate_all_ratios misses them) ──
        "_yahoo_ratios": {
            "currentRatio": _raw(fd.get("currentRatio")),
            "quickRatio": _raw(fd.get("quickRatio")),
            "debtToEquity": _raw(fd.get("debtToEquity")),
            "returnOnEquity": _raw(fd.get("returnOnEquity")),
            "returnOnAssets": _raw(fd.get("returnOnAssets")),
            "grossMargins": _raw(fd.get("grossMargins")),
            "operatingMargins": _raw(fd.get("operatingMargins")),
            "ebitdaMargins": _raw(fd.get("ebitdaMargins")),
            "profitMargins": _raw(fd.get("profitMargins")),
            "enterpriseValue": _raw(kstat.get("enterpriseValue")),
            "enterpriseToEbitda": _raw(kstat.get("enterpriseToEbitda")),
            "enterpriseToRevenue": _raw(kstat.get("enterpriseToRevenue")),
            "priceToBook": _raw(kstat.get("priceToBook")),
            "forwardPE": _raw(summary.get("forwardPE")) or _raw(kstat.get("forwardPE")),
            "dividendYield": _raw(summary.get("dividendYield")),
        },
    }

    # ── Enrich prior-year data with yfinance (historical statements) ──
    try:
        info = _enrich_prior_year_data(symbol, info)
    except Exception as e:
        logger.warning(f"[ENRICH] Prior-year enrichment failed for {symbol}: {e}")

    elapsed = time.time() - t0
    logger.info(f"[FAST API] get_ticker_info({symbol}) in {elapsed:.2f}s")

    # Cache
    _cache[symbol] = (time.time(), info, _is_degraded(info))
    return info


def _enrich_prior_year_data(symbol: str, info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enrich prior-year data using yfinance historical statements.

    The Yahoo v10 API returns almost no historical balance sheet / cash flow data.
    yfinance (via its own API) returns full multi-year statements, so we use it
    specifically to fill in the _prior_year dict for Piotroski F-Score accuracy.
    """
    try:
        import yfinance as yf
    except ImportError:
        logger.debug("[ENRICH] yfinance not installed, skipping enrichment")
        return info

    t0 = time.time()
    ticker = yf.Ticker(symbol)

    prior = info.get("_prior_year", {})
    derived = info.get("_current_derived", {})

    # Helper to safely extract float from pandas
    def _sf(series, key):
        try:
            val = series.get(key)
            if val is not None:
                f = float(val)
                if f == f and f != 0:  # not NaN and not zero-as-missing
                    return f
        except (TypeError, ValueError, KeyError):
            pass
        return None

    # ── Fetch statements (yfinance caches internally) ──
    try:
        inc = ticker.income_stmt
        bs = ticker.balance_sheet
        cf = ticker.cashflow
    except Exception as e:
        logger.debug(f"[ENRICH] yfinance statement fetch failed: {e}")
        return info

    has_inc = inc is not None and not inc.empty and len(inc.columns) >= 2
    has_bs = bs is not None and not bs.empty and len(bs.columns) >= 2
    has_cf = cf is not None and not cf.empty and len(cf.columns) >= 2

    if not (has_inc or has_bs or has_cf):
        return info

    # Columns: [0] = most recent (current), [1] = prior year
    # ── Determine fiscal year labels ──
    fy_current = str(inc.columns[0].year) if has_inc else ""
    fy_prior = str(inc.columns[1].year) if has_inc else ""

    # ── CURRENT YEAR — fix derived metrics with real data ──
    # Also build _piotroski_current with ONLY FY data (no TTM mixing)
    piotroski_current = {}

    if has_inc:
        cur_inc = inc.iloc[:, 0]
        gp = _sf(cur_inc, "Gross Profit")
        rev = _sf(cur_inc, "Total Revenue")
        cur_ni = _sf(cur_inc, "Net Income")
        if gp and rev and rev > 0:
            derived["gross_margin"] = gp / rev
            piotroski_current["gross_margin"] = gp / rev
        if cur_ni is not None:
            piotroski_current["net_income"] = cur_ni

    if has_bs:
        cur_bs = bs.iloc[:, 0]
        cur_ta = _sf(cur_bs, "Total Assets")
        cur_rev = _sf(inc.iloc[:, 0], "Total Revenue") if has_inc else None
        cur_ltd = _sf(cur_bs, "Long Term Debt")
        cur_ca = _sf(cur_bs, "Current Assets")
        cur_cl = _sf(cur_bs, "Current Liabilities")
        cur_shares = _sf(cur_bs, "Share Issued") or _sf(cur_bs, "Ordinary Shares Number")

        if cur_ta and cur_rev and cur_ta > 0:
            derived["asset_turnover"] = cur_rev / cur_ta
            piotroski_current["asset_turnover"] = cur_rev / cur_ta
        if cur_ta is not None:
            piotroski_current["total_assets"] = cur_ta
        if cur_ltd is not None:
            piotroski_current["long_term_debt"] = cur_ltd
        if cur_ca and cur_cl and cur_cl > 0:
            piotroski_current["current_ratio"] = cur_ca / cur_cl
        if cur_shares:
            piotroski_current["shares"] = cur_shares

        # ROA from FY data
        cur_ni_for_roa = piotroski_current.get("net_income")
        if cur_ni_for_roa and cur_ta and cur_ta > 0:
            piotroski_current["roa"] = cur_ni_for_roa / cur_ta

        # Also fix current longTermDebt if missing
        if info.get("longTermDebt") is None:
            info["longTermDebt"] = cur_ltd

    if has_cf:
        cur_cf = cf.iloc[:, 0]
        cur_ocf = _sf(cur_cf, "Operating Cash Flow")
        if cur_ocf is not None:
            piotroski_current["operating_cash_flow"] = cur_ocf

    # ── PRIOR YEAR — replace estimated data with real data ──
    if has_inc and len(inc.columns) >= 2:
        prev_inc = inc.iloc[:, 1]
        prev_rev = _sf(prev_inc, "Total Revenue")
        prev_ni = _sf(prev_inc, "Net Income")
        prev_gp = _sf(prev_inc, "Gross Profit")

        if prev_rev is not None:
            prior["revenue"] = prev_rev
        if prev_ni is not None:
            prior["net_income"] = prev_ni
        if prev_gp and prev_rev and prev_rev > 0:
            prior["gross_margin"] = prev_gp / prev_rev

    if has_bs and len(bs.columns) >= 2:
        prev_bs = bs.iloc[:, 1]
        prev_ta = _sf(prev_bs, "Total Assets")
        prev_ca = _sf(prev_bs, "Current Assets")
        prev_cl = _sf(prev_bs, "Current Liabilities")
        prev_ltd = _sf(prev_bs, "Long Term Debt")
        prev_eq = _sf(prev_bs, "Stockholders Equity")

        if prev_ta is not None:
            prior["total_assets"] = prev_ta
        if prev_ltd is not None:
            prior["long_term_debt"] = prev_ltd
        if prev_eq is not None:
            prior["equity"] = prev_eq
        if prev_ca and prev_cl and prev_cl > 0:
            prior["current_ratio"] = prev_ca / prev_cl

        # Prior-year asset turnover
        prev_rev_for_at = prior.get("revenue")
        if prev_ta and prev_rev_for_at and prev_ta > 0:
            prior["asset_turnover"] = prev_rev_for_at / prev_ta

        # Prior-year ROA
        prev_ni_for_roa = prior.get("net_income")
        if prev_ni_for_roa and prev_ta and prev_ta > 0:
            prior["roa"] = prev_ni_for_roa / prev_ta

        # Prior-year shares
        prev_shares = _sf(prev_bs, "Share Issued") or _sf(prev_bs, "Ordinary Shares Number")
        if prev_shares:
            prior["shares"] = prev_shares

    if has_cf and len(cf.columns) >= 2:
        prev_cf = cf.iloc[:, 1]
        prev_ocf = _sf(prev_cf, "Operating Cash Flow")
        if prev_ocf is not None:
            prior["operating_cash_flow"] = prev_ocf

    # Store fiscal year info for display
    prior["_fiscal_year"] = fy_prior
    info["_fiscal_year_current"] = fy_current

    info["_prior_year"] = prior
    info["_current_derived"] = derived
    info["_piotroski_current"] = piotroski_current

    elapsed = time.time() - t0
    logger.info(f"[ENRICH] Prior-year data enriched for {symbol} (FY{fy_prior}) in {elapsed:.2f}s")
    return info


def _fallback_yfinance(symbol: str) -> Dict[str, Any]:
    """Fallback to yfinance if direct API fails."""
    logger.warning(f"[FALLBACK] Using yfinance for {symbol}")
    import yfinance as yf
    from concurrent.futures import ThreadPoolExecutor, as_completed

    t0 = time.time()
    ticker = yf.Ticker(symbol)

    try:
        fi = ticker.fast_info
    except Exception:
        return {}

    info: Dict[str, Any] = {
        "symbol": symbol,
        "regularMarketPrice": fi.get("lastPrice"),
        "currentPrice": fi.get("lastPrice"),
        "marketCap": fi.get("marketCap"),
        "currency": fi.get("currency", "USD"),
        "exchange": fi.get("exchange", "Unknown"),
        "fiftyTwoWeekHigh": fi.get("yearHigh"),
        "fiftyTwoWeekLow": fi.get("yearLow"),
        "shares": fi.get("shares"),
        "sharesOutstanding": fi.get("shares"),
        "beta": None,  # Will be populated from ticker.info if available
    }

    # Try to get beta from ticker.info (fast_info doesn't have it)
    try:
        _info = ticker.info
        if _info.get("beta"):
            info["beta"] = _info["beta"]
    except Exception:
        pass

    sd = KNOWN_SECTORS.get(symbol)
    info["sector"] = sd[0] if sd else "Unknown"
    info["industry"] = sd[1] if sd else "Unknown"

    try:
        from stock_database import POPULAR_STOCKS
        info["longName"] = POPULAR_STOCKS.get(symbol, symbol)
        info["shortName"] = info["longName"]
    except Exception:
        info["longName"] = symbol
        info["shortName"] = symbol

    # Parallel statement fetch
    def _get_inc():
        inc = ticker.income_stmt
        if inc is not None and not inc.empty:
            latest = inc.iloc[:, 0]
            return {k: _sg(latest, k) for k in [
                "Total Revenue", "Gross Profit", "Operating Income",
                "Net Income", "EBITDA", "Diluted EPS", "Interest Expense",
                "Depreciation And Amortization"
            ]}
        return {}

    def _get_bs():
        bs = ticker.balance_sheet
        if bs is not None and not bs.empty:
            latest = bs.iloc[:, 0]
            result = {k: _sg(latest, k) for k in [
                "Total Assets", "Current Assets", "Current Liabilities",
                "Total Debt", "Long Term Debt", "Stockholders Equity",
                "Total Liabilities Net Minority Interest",
                "Cash Cash Equivalents And Short Term Investments",
                "Cash And Cash Equivalents",
                "Retained Earnings", "Inventory"
            ]}
            # Prefer broader cash field
            if result.get("Cash Cash Equivalents And Short Term Investments"):
                result["Cash And Cash Equivalents"] = result["Cash Cash Equivalents And Short Term Investments"]
            return result
        return {}

    def _get_cf():
        cf = ticker.cashflow
        if cf is not None and not cf.empty:
            latest = cf.iloc[:, 0]
            return {k: _sg(latest, k) for k in [
                "Operating Cash Flow", "Capital Expenditure",
                "Free Cash Flow", "Common Stock Dividend Paid"
            ]}
        return {}

    results = {}
    with ThreadPoolExecutor(max_workers=3) as ex:
        futs = {
            ex.submit(_get_inc): "income",
            ex.submit(_get_bs): "balance",
            ex.submit(_get_cf): "cashflow",
        }
        for f in as_completed(futs, timeout=30):
            key = futs[f]
            try:
                results[key] = f.result()
            except Exception:
                results[key] = {}

    # Map statement data to info dict
    inc = results.get("income", {})
    info["totalRevenue"] = inc.get("Total Revenue")
    info["grossProfits"] = inc.get("Gross Profit")
    info["operatingIncome"] = inc.get("Operating Income")
    info["netIncome"] = inc.get("Net Income")
    info["ebitda"] = inc.get("EBITDA")
    info["trailingEps"] = inc.get("Diluted EPS")
    info["interestExpense"] = inc.get("Interest Expense")
    info["depreciation"] = inc.get("Depreciation And Amortization")

    bs = results.get("balance", {})
    info["totalAssets"] = bs.get("Total Assets")
    info["totalCurrentAssets"] = bs.get("Current Assets")
    info["totalCurrentLiabilities"] = bs.get("Current Liabilities")
    info["totalDebt"] = bs.get("Total Debt")
    info["longTermDebt"] = bs.get("Long Term Debt")
    info["totalStockholderEquity"] = bs.get("Stockholders Equity")
    info["totalLiab"] = bs.get("Total Liabilities Net Minority Interest")
    info["cash"] = bs.get("Cash And Cash Equivalents")
    info["retainedEarnings"] = bs.get("Retained Earnings")

    cf = results.get("cashflow", {})
    info["operatingCashflow"] = cf.get("Operating Cash Flow")
    info["capitalExpenditures"] = cf.get("Capital Expenditure")
    info["freeCashflow"] = cf.get("Free Cash Flow")
    info["dividendsPaid"] = cf.get("Common Stock Dividend Paid")

    if not info.get("freeCashflow") and info.get("operatingCashflow") and info.get("capitalExpenditures"):
        info["freeCashflow"] = info["operatingCashflow"] + info["capitalExpenditures"]

    shares = info.get("sharesOutstanding")
    equity = info.get("totalStockholderEquity")
    if shares and equity and shares > 0:
        info["bookValue"] = equity / shares

    elapsed = time.time() - t0
    logger.info(f"[FALLBACK] get_ticker_info({symbol}) in {elapsed:.2f}s")
    _cache[symbol] = (time.time(), info, _is_degraded(info))
    return info


def _sg(series, key):
    """Safe get from pandas Series"""
    try:
        val = series.get(key)
        if val is not None:
            f = float(val)
            if f == f:
                return f
    except (TypeError, ValueError, KeyError):
        pass
    return None
