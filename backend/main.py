"""
Finanzer API - FastAPI backend that exposes the financial brain
"""
import sys
import os
import io
import logging
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

# Add lib to path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))

from data_fetcher import FinancialDataService, InvalidSymbolError
from financial_ratios import (
    calculate_all_ratios, calculate_score_v2,
    altman_z_score, piotroski_evaluate, piotroski_level, interest_coverage_state, net_debt_ebitda_state,
    graham_number, margin_of_safety, dcf_multi_stage_dynamic, roic_significant,
    dcf_sensitivity_analysis
)
from stock_database import search_stocks, POPULAR_STOCKS, TOP_STOCKS
from sector_profiles import get_sector_profile, YAHOO_SECTOR_MAPPING
from alert_interpretations import build_signals
from settings import cfg
from historical_metrics import fcf_cagr, growth_rate, is_sustained_negative, per_share, per_share_basis
from classify import (ARCHETYPE_GROUP, CYCLICAL, FINANCIAL, GROWTH_PRE_PROFIT, REIT, archetype_label, classify,
                      not_applicable, not_applicable_text)
from normalize import normalize as normalize_earnings
from yf_adapter import _UNUSUAL_ROWS
from ttm import TTM_QUARTERS
from verdict import price as verdict_price, verdict as build_verdict
from cost_of_capital import adjusted_beta, effective_tax_rate, risk_free, wacc as compute_wacc
from valuation_confidence import (convergence, coverage_dimension, dcf_reliability, signal_from_upside,
                                  source_dimension, stability_dimension, verdict_confidence)
import archetype_metrics
import numfmt
from currency import CurrencyConversionError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Finanzer API", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Shared service instance (has caching built in)
data_service = FinancialDataService()


def safe_float(val) -> Optional[float]:
    """Convert value to float, return None if not possible."""
    if val is None:
        return None
    try:
        f = float(val)
        if f != f or f in (float("inf"), float("-inf")):  # NaN or Infinity
            # Non-finite values are invalid JSON and render as "$InfinityT" etc.
            return None
        return f
    except (TypeError, ValueError):
        return None


def financials_to_dict(fin) -> Dict[str, Any]:
    """Convert FinancialStatements dataclass to dict for ratio calculations.

    Numeric fields are sanitized through safe_float so only finite numbers
    reach the ratio engine: NaN/Infinity (which pandas/yfinance emit for
    missing cells) and any stray non-numeric value become None and are
    dropped. This stops a NaN from silently poisoning downstream ratios and
    scores, and a stray string from raising a TypeError inside
    calculate_all_ratios (e.g. 'str' / 'str'). The two string metadata fields
    are passed through unchanged.
    """
    if fin is None:
        return {}
    _str_meta = {"fiscal_year_end", "last_updated"}
    out: Dict[str, Any] = {}
    for k, v in fin.__dict__.items():
        if v is None:
            continue
        if k in _str_meta:
            out[k] = v
            continue
        sv = safe_float(v)
        if sv is not None:
            out[k] = sv
    return out


def _check_sector_benchmarks():
    """Cada sector solo puede sobrescribir métricas que existen en el default."""
    from settings import SettingsError
    known = set(cfg("sectors.benchmarks.default"))
    for sector, values in cfg("sectors.benchmarks.sectors").items():
        extra = set(values) - known
        if extra:
            raise SettingsError(f"sectors.benchmarks.sectors.{sector}: métricas desconocidas {sorted(extra)}")


_check_sector_benchmarks()


def _get_sector_benchmarks(sector: str) -> dict:
    """Sector benchmark averages for PDF comparative section (mirrors frontend)."""
    # Medianas PROVISIONALES (no vienen de comparables reales): sectors.toml.
    defaults = dict(cfg("sectors.benchmarks.default"))
    sector_map = cfg("sectors.benchmarks.sectors")
    import re
    key = re.sub(r'[\s-]+', '_', sector.lower())
    overrides = dict(sector_map.get(key, {}))
    return {**defaults, **overrides}


def _select_benchmark(mapped_sector: str, archetype: Optional[str]) -> dict:
    """Benchmark de valoración relativa: medianas del sector o, si el arquetipo
    contradice al sector de Yahoo, las del mercado amplio (perfil market).

    Devuelve {profile, sector, values, reason, sources}: `values` alimenta el score
    (P/E y EV/EBITDA frente a la mediana) y las tablas comparativas del PDF."""
    import re
    key = re.sub(r'[\s-]+', '_', (mapped_sector or "default").lower())
    expected = cfg("sectors.benchmarks.sector_archetype").get(key)
    from financial_ratios import SECTOR_THRESHOLDS, ThresholdConfig
    _th_keys = ("roe_high", "roe_low", "roa_high", "roa_low", "debt_equity_high", "operating_margin_low",
                "net_margin_low", "interest_coverage_low", "current_ratio_low")

    def _th(k):
        t = SECTOR_THRESHOLDS.get(k, ThresholdConfig())
        return {n: getattr(t, n) for n in _th_keys}
    if expected and archetype and archetype != expected:
        market = dict(cfg("sectors.benchmarks.market"))
        return {"profile": "market", "sector": key, "thresholds_key": "market", "thresholds": _th("market"),
                "values": {**dict(cfg("sectors.benchmarks.default")), **market},
                # Etapa 9b: etiquetas en español (el código queda en el detalle técnico).
                "reason": (f"empresa clasificada como {archetype_label(archetype)} dentro del sector {key}, "
                           f"cuyas medianas y umbrales suponen {ARCHETYPE_GROUP.get(expected, expected)}: se usan "
                           "los del mercado amplio (S&P 500)"),
                "sources": {k: v for k, v in cfg("sectors.benchmarks.market_source").items() if k in market},
                "provisional": True}
    return {"profile": "sector", "sector": key, "thresholds_key": mapped_sector, "thresholds": _th(mapped_sector),
            "values": _get_sector_benchmarks(mapped_sector), "reason": None, "sources": None, "provisional": True}


def _pdf_benchmark(analysis: dict) -> dict:
    """Benchmark del PDF: el mismo que usó el score (sector o market)."""
    sel = (analysis.get("benchmark") or {}).get("values")
    return sel or _get_sector_benchmarks((analysis.get("sector_info") or {}).get("mapped_sector", "default"))


@app.get("/api/search")
async def search(q: str = Query("", min_length=1, max_length=100)):
    """Search for stocks by ticker or company name.
    Uses local database first, then Yahoo Finance autocomplete for broader coverage."""
    # Local database search
    local_results = search_stocks(q, limit=5)
    results = [
        {"ticker": ticker, "name": name, "score": score}
        for ticker, name, score in local_results
    ]

    # If fewer than 5 local results, supplement with Yahoo search
    if len(results) < 5:
        try:
            yahoo_results = _yahoo_search(q, limit=8 - len(results))
            # Deduplicate
            existing_tickers = {r["ticker"] for r in results}
            for yr in yahoo_results:
                if yr["ticker"] not in existing_tickers:
                    results.append(yr)
                    existing_tickers.add(yr["ticker"])
        except Exception as e:
            logger.debug(f"Yahoo search error: {e}")

    return results[:8]


def _yahoo_search(query: str, limit: int = 5) -> list:
    """Search Yahoo Finance autocomplete API for stocks."""
    try:
        from yf_adapter import _ensure_session, _session
        _ensure_session()
        url = "https://query2.finance.yahoo.com/v1/finance/search"
        params = {
            "q": query,
            "lang": "en-US",
            "region": "US",
            "quotesCount": limit,
            "newsCount": 0,
            "listsCount": 0,
            "enableFuzzyQuery": True,
            "quotesQueryId": "tss_match_phrase_query",
        }
        r = _session.get(url, params=params, timeout=5)
        if r.status_code != 200:
            return []

        data = r.json()
        quotes = data.get("quotes", [])
        results = []
        for q in quotes:
            # Only include stocks (not crypto, futures, etc.)
            qtype = q.get("quoteType", "")
            if qtype not in ("EQUITY", "ETF"):
                continue
            ticker = q.get("symbol", "")
            name = q.get("shortname") or q.get("longname") or ticker
            exchange = q.get("exchange", "")
            results.append({
                "ticker": ticker,
                "name": f"{name}",
                "score": 50,
            })
        return results
    except Exception as e:
        logger.debug(f"Yahoo search failed: {e}")
        return []


@app.get("/api/stocks/popular")
async def popular_stocks():
    """Return popular stocks for home page."""
    return [
        {"ticker": t, "name": POPULAR_STOCKS.get(t, t)}
        for t in TOP_STOCKS
    ]


# Campos de ingesta que el motor consume; si quedan None sin procedencia se
# exponen como "sin_dato" (la fuente no los devolvió).
_PROVENANCE_KEY_FIELDS = (
    "currentPrice", "marketCap", "sharesOutstanding", "beta", "sector", "industry",
    "totalRevenue", "grossProfits", "operatingIncome", "netIncome", "ebitda",
    "trailingEps", "forwardEps", "totalAssets", "totalDebt", "totalCash",
    "totalStockholderEquity", "operatingCashflow", "freeCashflow",
    "revenueGrowth", "earningsGrowth", "dividendYield", "payoutRatio",
)


def _build_provenance(yinfo: dict, out_flags: list, block_errors: list) -> dict:
    """Bloque data_provenance (campo nuevo del contrato; no toca los existentes)."""
    fields = {k: dict(v) for k, v in (yinfo.get("_provenance") or {}).items()}
    for k in _PROVENANCE_KEY_FIELDS:
        if k not in fields and yinfo.get(k) is None:
            fields[k] = {"source": "sin_dato", "detail": "la fuente no lo devolvió"}
    for f in out_flags:
        fields[f["field"]] = {"source": "sin_dato", "rule": f["rule"], "detail": f["reason"]}
    return {
        "path": yinfo.get("_data_path") or ("sin_dato" if not yinfo else "desconocido"),
        "fields": dict(sorted(fields.items())),
        "errors": block_errors,
        # Etapa 7: qué campos son TTM (4 trimestres), del último trimestre o del
        # anual (sin 4 trimestres consecutivos), con el motivo.
        "ttm": yinfo.get("_ttm"),
        # Etapa 11b: moneda y clase de los estados frente a la cotización, y la conversión aplicada.
        "currency": yinfo.get("_currency"),
    }


# Etapa 11b: tipo de instrumento de Yahoo (quoteType) -> cómo se nombra en el mensaje.
_INSTRUMENT_NAMES = {"ETF": "un ETF", "MUTUALFUND": "un fondo de inversión", "INDEX": "un índice",
                     "CRYPTOCURRENCY": "una criptomoneda", "CURRENCY": "una divisa", "FUTURE": "un futuro",
                     "OPTION": "una opción", "MONEYMARKET": "un fondo monetario"}


def not_a_stock_message(symbol: str, quote_type: str) -> str:
    what = _INSTRUMENT_NAMES.get(str(quote_type).upper(), "un instrumento que no es una acción")
    return (f"Finanzer analiza acciones individuales: {symbol} es {what}, así que no se analiza "
            "(sus estados, ratios y valoración no tienen sentido como los de una empresa).")


def _compute_analysis(symbol: str) -> dict:
    """
    Shared analysis computation used by both API endpoint and PDF generator.
    Returns the full analysis dict or raises HTTPException.
    """
    symbol = symbol.upper().strip()
    # Validate ticker characters (letters/digits and . - ^ = as used by real
    # tickers, e.g. BRK.B, BRK-B, ^GSPC, EURUSD=X). Reject anything else with a
    # clean 400 instead of letting it crash deep in the data fetch (500).
    if (not symbol or len(symbol) > 15
            or not all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-^=" for c in symbol)
            or not any(c.isalnum() for c in symbol)):
        # Must be short, use only real-ticker characters, AND contain at least one
        # letter/digit — punctuation-only garbage like "^^^^" or "=====" still
        # reaches (and crashes) the data fetch otherwise.
        raise HTTPException(status_code=400, detail="Invalid symbol")

    try:
        # Etapa 11b: Finanzer analiza acciones individuales. Un ETF, un fondo o un índice
        # se rechaza con un mensaje claro y sin análisis (antes salía como empresa "Madura"
        # con todo sin dato). get_ticker_info es la primera descarga del pipeline (cacheada).
        from yf_adapter import get_ticker_info as _gti
        try:
            _qt = (_gti(symbol) or {}).get("quoteType")
        except CurrencyConversionError:
            raise
        except Exception as e:
            # Símbolo inexistente u otro fallo de la fuente: lo trata el camino normal (404),
            # como antes de esta comprobación.
            logger.info(f"[{symbol}] sin tipo de instrumento: {type(e).__name__}: {e}")
            _qt = None
        if _qt and str(_qt).upper() != "EQUITY":
            raise HTTPException(status_code=422, detail=not_a_stock_message(symbol, _qt))

        # Fetch all data using the financial brain
        data = data_service.get_complete_analysis_data(symbol)

        if not data or not data.get("profile"):
            raise HTTPException(status_code=404, detail=f"No data found for {symbol}")

        profile = data["profile"]
        financials = data.get("financials")
        historical = data.get("historical", {})

        # Build response
        result = {
            "symbol": symbol,
            "profile": {
                "name": profile.name,
                "sector": profile.sector,
                "industry": profile.industry,
                "country": profile.country,
                "currency": profile.currency,
                "exchange": profile.exchange,
                "market_cap": safe_float(profile.market_cap),
                "description": profile.description,
            },
            "price": safe_float(financials.price) if financials else None,
            "errors": data.get("errors", []),
        }
        # Trazabilidad (etapa 3): bloques que un except amplio dejó sin calcular.
        # No cambia el flujo de control: solo registra y marca "sin_dato".
        _block_errors = []

        def _sin_dato(block, exc):
            logger.error(f"[{symbol}] bloque '{block}' sin calcular: {type(exc).__name__}: {exc}")
            _block_errors.append({"block": block, "source": "sin_dato",
                                  "reason": f"{type(exc).__name__}: {exc}"})

        yinfo = {}
        _row_flags = []

        # Calculate ratios
        if financials:
            fin_dict = financials_to_dict(financials)
            ratios = calculate_all_ratios(fin_dict)

            # Enrich ratios with Yahoo pre-computed values as fallbacks
            yr = {}
            yinfo = {}
            _has_yahoo = False
            try:
                from yf_adapter import get_ticker_info
                yinfo = get_ticker_info(symbol)  # cached, instant
                yr = yinfo.get("_yahoo_ratios", {})
                _has_yahoo = True

                fallback_map = {
                    "current_ratio": yr.get("currentRatio"),
                    "quick_ratio": yr.get("quickRatio"),
                    "debt_to_equity": yr.get("debtToEquity", 0) and yr.get("debtToEquity", 0) / 100,  # Yahoo returns as %
                    "roe": yr.get("returnOnEquity"),
                    "roa": yr.get("returnOnAssets"),
                    "gross_margin": yr.get("grossMargins"),
                    "operating_margin": yr.get("operatingMargins"),
                    "ebitda_margin": yr.get("ebitdaMargins"),
                    "net_margin": yr.get("profitMargins"),
                    "ev_ebitda": yr.get("enterpriseToEbitda"),
                    "ev_revenue": yr.get("enterpriseToRevenue"),
                    "pb": yr.get("priceToBook"),
                    "enterprise_value": yr.get("enterpriseValue"),
                    "forward_pe": yr.get("forwardPE"),
                    "dividend_yield": yr.get("dividendYield"),
                    # Aportados por la fuente secundaria (Finnhub) cuando Yahoo
                    # los bloquea; ya vienen en la unidad del motor (decimal).
                    "payout_ratio": yr.get("payoutRatio"),
                    "interest_coverage": yr.get("interestCoverage"),
                    "inventory_turnover": yr.get("inventoryTurnover"),
                }

                for k, v in fallback_map.items():
                    if ratios.get(k) is None and v is not None:
                        ratios[k] = v

                # PEG de MERCADO (Yahoo defaultKeyStatistics.pegRatio o forwardPEG
                # de Finnhub): usa crecimiento FORWARD de consenso, la convención
                # de stockanalysis/Yahoo. Se PREFIERE sobre el PEG trailing del
                # motor (P/E ÷ crecimiento TTM), que con un crecimiento TTM
                # inflado por one-time items subestima (AAPL 1.2 vs ~2.5 real).
                # El PEG trailing queda solo si no hay PEG de mercado.
                _mkt_peg = safe_float(yr.get("pegRatio"))
                if _mkt_peg is not None and _mkt_peg > 0:
                    ratios["peg"] = _mkt_peg
            except Exception as e:
                logger.debug(f"Yahoo ratio fallback error: {e}")
                _sin_dato("ratios_fallback_yahoo", e)

            # ── Etapa 8: tasa efectiva por empresa (la misma t en el WACC y el ROIC) ──
            # Mismo periodo que el beneficio: TTM (4 trimestres) si el beneficio es
            # TTM; si no, el último FY. BAI <= 0 o sin dato: tipo legal (marcado).
            _st8 = (yinfo.get("_statements_fy") or {}) if _has_yahoo else {}
            _q8 = (yinfo.get("_quarterly") or {}) if _has_yahoo else {}
            _pt_q = (_q8.get("Pretax Income") or [])[:4]
            _tx_q = (_q8.get("Tax Provision") or [])[:4]
            if ("netIncome" in (((yinfo.get("_ttm") or {}) if _has_yahoo else {}).get("ttm_fields") or [])
                    and len(_pt_q) == len(_tx_q) == TTM_QUARTERS and None not in _pt_q + _tx_q):
                tax_info = effective_tax_rate(sum(_pt_q), sum(_tx_q), "TTM")
            else:
                tax_info = effective_tax_rate((_st8.get("pretax_income") or [None])[0],
                                              (_st8.get("tax_provision") or [None])[0],
                                              f"FY{(_st8.get('inc_years') or ['?'])[0]}")
            fin_dict["tax_rate"] = tax_info["rate"]
            ratios["roic"] = calculate_all_ratios(fin_dict).get("roic")

            result["ratios"] = {k: safe_float(v) for k, v in ratios.items()}

            # Key metrics — try ratios first, fallback to alternate keys
            def r(key, *alts):
                """Get ratio by key, trying alternates."""
                v = safe_float(ratios.get(key))
                if v is not None:
                    return v
                for alt in alts:
                    v = safe_float(ratios.get(alt))
                    if v is not None:
                        return v
                return None

            # ── Compute derived metrics that are often null ──
            price_val = safe_float(financials.price)
            mcap = safe_float(profile.market_cap)
            fcf_val = safe_float(financials.free_cash_flow) or safe_float(ratios.get("fcf"))
            shares_val = safe_float(financials.shares_outstanding)
            oi_val = safe_float(financials.operating_income)
            ie_val = safe_float(financials.interest_expense)
            td_val = safe_float(financials.total_debt)
            te_val = safe_float(financials.total_equity)
            cash_val = safe_float(financials.cash)

            # FCF Yield = FCF / Market Cap
            fcf_yield = r("fcf_yield")
            if fcf_yield is None and fcf_val and mcap and mcap > 0:
                fcf_yield = fcf_val / mcap

            # P/FCF = Market Cap / FCF
            pfcf = r("pfcf", "price_to_fcf", "p_fcf")
            if pfcf is None and fcf_val and fcf_val > 0 and mcap:
                pfcf = mcap / fcf_val

            # ROIC = NOPAT / Invested Capital
            roic = r("roic")
            if roic is None and oi_val and te_val:
                nopat = oi_val * (1 - tax_info["rate"])  # misma t que calculate_all_ratios y el WACC
                invested_capital = te_val + (td_val or 0) - (cash_val or 0)
                if roic_significant(invested_capital, safe_float(financials.total_assets)):
                    roic = nopat / invested_capital
            # Regla M (etapa 9a): motivo cuando el capital invertido es demasiado pequeño.
            roic_reason = None
            _ta_m = safe_float(financials.total_assets)
            if roic is None and te_val is not None and _ta_m:
                _ic_m = te_val + (td_val or 0) - (cash_val or 0)
                if not roic_significant(_ic_m, _ta_m):
                    roic_reason = (f"capital invertido {_ic_m / _ta_m:.0%} de los activos (< "
                                   f"{cfg('thresholds.score.rentabilidad.roic_min_invested_capital_share'):.0%}): "
                                   "ROIC no significativo")
            fin_dict["roic_reason"] = roic_reason

            # Interest Coverage = Operating Income / |Interest Expense|
            interest_cov = r("interest_coverage")
            if interest_cov is None and oi_val and ie_val and ie_val != 0:
                interest_cov = oi_val / abs(ie_val)

            # Payout Ratio — from Yahoo
            payout = r("payout_ratio")
            if payout is None:
                pr_yahoo = yr.get("payoutRatio") if _has_yahoo else None
                if pr_yahoo is not None:
                    payout = pr_yahoo

            # Dividend yield from Yahoo — check _yahoo_ratios AND main info dict
            div_yield = r("dividend_yield")
            if div_yield is None and _has_yahoo:
                dy_yahoo = yr.get("dividendYield") or yinfo.get("dividendYield")
                if dy_yahoo is not None and dy_yahoo != 0:
                    div_yield = dy_yahoo

            # Debt to Assets
            debt_to_assets = r("debt_to_assets")
            ta_val = safe_float(financials.total_assets)
            if debt_to_assets is None and td_val and ta_val and ta_val > 0:
                debt_to_assets = td_val / ta_val

            # Asset Turnover
            asset_turn = r("asset_turnover")
            rev_val = safe_float(financials.revenue)
            if asset_turn is None and rev_val and ta_val and ta_val > 0:
                asset_turn = rev_val / ta_val

            # Earnings Yield = EPS / Price
            earnings_yield = r("earnings_yield")
            eps_val = safe_float(financials.eps)
            if earnings_yield is None and eps_val and price_val and price_val > 0:
                earnings_yield = eps_val / price_val

            # EV/EBITDA — compute from components if ratio is missing
            ev_ebitda = r("ev_ebitda")
            if ev_ebitda is None and _has_yahoo:
                ev = safe_float(yr.get("enterpriseValue")) or safe_float(ratios.get("enterprise_value"))
                ebitda_v = safe_float(financials.ebitda) or safe_float(ratios.get("ebitda"))
                if ev and ebitda_v and ebitda_v > 0:
                    ev_ebitda = ev / ebitda_v

            # Forward P/E — compute from forward EPS if ratio is missing
            fwd_pe = r("forward_pe")
            if fwd_pe is None and price_val and financials.forward_eps:
                feps = safe_float(financials.forward_eps)
                if feps and feps > 0:
                    fwd_pe = price_val / feps

            result["key_metrics"] = {
                "market_cap": mcap,
                "pe": r("pe"),
                "roe": r("roe"),
                "de": r("debt_to_equity"),
                "net_margin": r("net_margin"),
                "fcf_yield": safe_float(fcf_yield),
                "ev_ebitda": safe_float(ev_ebitda),
                "beta": safe_float(financials.beta),
                "forward_pe": safe_float(fwd_pe),
                "pb": r("pb", "price_to_book"),
                "ps": r("ps", "price_to_sales", "p_s"),
                "peg": r("peg", "peg_ratio"),
                "pfcf": safe_float(pfcf),
                "gross_margin": r("gross_margin"),
                "operating_margin": r("operating_margin"),
                "ebitda_margin": r("ebitda_margin"),
                "roa": r("roa"),
                "roic": safe_float(roic),
                "roic_reason": roic_reason,
                "current_ratio": r("current_ratio"),
                "quick_ratio": r("quick_ratio"),
                "interest_coverage": safe_float(interest_cov),
                # Etapa 5: "no_significativo" (EBIT < 0 con caja neta), "negativa"
                # (EBIT < 0 con deuda neta) u "ok".
                "interest_coverage_state": interest_coverage_state(safe_float(interest_cov), r("net_debt")),
                "debt_to_assets": safe_float(debt_to_assets),
                # Métricas que se calculaban en calculate_all_ratios pero nunca se
                # exponían (el frontend solo lee key_metrics), así que se
                # descartaban. net_debt_to_ebitda y cash_ratio son señales de
                # solvencia/liquidez útiles; inventory_turnover ahora sí se calcula
                # (COGS derivado). (Mostrarlas en la UI queda como follow-up de
                # frontend; aquí quedan disponibles en el API.)
                "net_debt_to_ebitda": r("net_debt_to_ebitda"),
                # Etapa 5: "no_significativo" (EBITDA <= 0), "caja_neta" u "ok".
                "net_debt_to_ebitda_state": net_debt_ebitda_state(r("ebitda"), r("net_debt")),
                "cash_ratio": r("cash_ratio"),
                "net_debt": r("net_debt"),
                "inventory_turnover": r("inventory_turnover"),
                # Métricas FFO (REITs): p_ffo alimenta la banda de valoración
                # REIT del score; se exponen para la UI.
                "p_ffo": r("p_ffo"),
                "ffo": r("ffo"),
                "ffo_payout": r("ffo_payout"),
                "dividend_yield": safe_float(div_yield),
                "payout_ratio": safe_float(payout),
                "eps": eps_val or r("eps"),
                "revenue": rev_val,
                "net_income": safe_float(financials.net_income),
                "ebitda": safe_float(financials.ebitda) or r("ebitda"),
                "free_cash_flow": fcf_val,
                "total_debt": td_val,
                "total_equity": te_val,
                "cash": cash_val,
                "book_value_per_share": safe_float(financials.book_value_per_share),
                "shares_outstanding": shares_val,
                "revenue_growth": safe_float(financials.revenue_growth_yoy),
                "earnings_growth": safe_float(financials.earnings_growth_rate),
                "price_52w_high": safe_float(financials.price_52w_high),
                "price_52w_low": safe_float(financials.price_52w_low),
                "operating_cash_flow": safe_float(financials.operating_cash_flow),
                "operating_income": oi_val,
                "interest_expense": ie_val,
                "total_assets": ta_val,
                "asset_turnover": safe_float(asset_turn),
                "earnings_yield": safe_float(earnings_yield),
                "ev_revenue": r("ev_revenue"),
                "enterprise_value": r("enterprise_value"),
            }

            # Sector info
            sector = profile.sector or ""
            mapped_sector = YAHOO_SECTOR_MAPPING.get(sector.lower(), sector)
            sector_profile = get_sector_profile(mapped_sector)

            result["sector_info"] = {
                "sector": sector,
                "mapped_sector": mapped_sector,
                "sector_etf": sector_profile.sector_etf if sector_profile else "SPY",
            }

            # Arquetipo (etapa 6): una sola decisión, antes de puntuar, que leen
            # el score, la valoración, las alertas, el PDF y el frontend.
            _stmts = (yinfo.get("_statements_fy") or {}) if _has_yahoo else {}
            classification = classify(sector=sector, industry=profile.industry, eps_ttm=eps_val,
                                      net_margin_ttm=r("net_margin"), statements_fy=_stmts)
            archetype = classification["archetype"]
            # Etapa 11b: aviso por filas clave del arquetipo ausentes en los estados.
            from validate import missing_key_rows
            _row_flags = missing_key_rows(_stmts, archetype) if _has_yahoo else []
            result["classification"] = classification
            # Rf (etapa 8): ^TNX con caché de 24 h o el de config, marcado. Uno por
            # análisis: el mismo en Ke (P/B justificado de FINANCIAL), Kd y WACC.
            rf_info = risk_free()
            # Métricas de la rama (P/B justificado, EV/Ventas, normalizados de ciclo…)
            # Etapa 9a: FCF − SBC en el periodo del FCF (informativo en todos los arquetipos;
            # en GROWTH_PRE_PROFIT es la base del margen FCF, la regla de 40 y el crecimiento del FCF).
            _ttm_i = (yinfo.get("_ttm") or {}) if _has_yahoo else {}
            sbc_info = archetype_metrics.sbc_adjustment(
                fcf=safe_float(financials.free_cash_flow), revenue=safe_float(financials.revenue),
                fcf_is_ttm="freeCashflow" in (_ttm_i.get("ttm_fields") or []),
                sbc_ttm=safe_float(yinfo.get("stockBasedCompensation")) if _has_yahoo else None, st=_stmts)
            result["sbc"] = {k: (safe_float(v) if isinstance(v, float) else v) for k, v in sbc_info.items()}
            # Etapa 9b: histórico anual (dato bruto, pestaña Histórico de la web).
            result["yearly_financials"] = [{k: (safe_float(v) if isinstance(v, float) else v) for k, v in r_.items()}
                                           for r_ in archetype_metrics.yearly_financials(_stmts, archetype)]
            archetype_values = archetype_metrics.compute(
                archetype, _stmts, result["key_metrics"], beta=safe_float(financials.beta),
                revenue_cagr_3y=classification["inputs"].get("revenue_cagr_3y"), rf=rf_info["value"],
                sbc=sbc_info)
            result["archetype_metrics"] = {k: (safe_float(v) if isinstance(v, float) else v)
                                           for k, v in archetype_values.items()}
            # ROCE (etapa 6): contraste con el ROIC en MATURE y CYCLICAL; "no aplica"
            # en FINANCIAL y REIT; sin dato (nunca 0%) con capital empleado <= 0.
            _roce = archetype_metrics.roce(archetype, _stmts, result["key_metrics"])
            _km = result["key_metrics"]
            _km["roce"] = safe_float(_roce.get("roce"))
            _km["roce_state"] = _roce["state"]
            _km["roce_reason"] = _roce.get("reason")
            if "roce_avg" in _roce:
                _km["roce_avg"] = safe_float(_roce["roce_avg"])
                _km["roce_years"] = _roce["years"]
                _km["roce_cycle_incomplete"] = _roce["cycle_incomplete"]
            _km["roce_roic_divergence"] = ({"diverges": _roce["diverges"], "gap": safe_float(_roce["gap"]),
                                            "causes": _roce.get("causes", [])}
                                           if "diverges" in _roce else None)
            # Payout (etapa 7): en REIT el dividendo se cubre con el FFO, no con el beneficio
            # neto (deprimido por la depreciación inmobiliaria): payout_ratio = dividendos / FFO.
            # El de beneficio neto se conserva aparte, solo como referencia.
            if archetype == REIT:
                _km["payout_ratio_net_income"] = _km.get("payout_ratio")
                _km["payout_ratio"] = _km.get("ffo_payout")
                _km["payout_basis"] = "ffo"
            else:
                _km["payout_basis"] = "beneficio_neto"
            # Qué no aplica al arquetipo fuera de las categorías del score.
            result["not_applicable"] = {k: not_applicable(archetype, k)
                                        for k in ("dcf", "graham", "altman", "piotroski", "roce")
                                        if not_applicable(archetype, k)}

            # Inject sector-median benchmarks so valuation scoring judges P/E and
            # EV/EBITDA against the stock's SECTOR (e.g. ~30x for tech, ~12x for
            # banks) instead of a fixed ~20x. Without this, high-P/E sectors look
            # overvalued and low-P/E sectors look cheap regardless of fundamentals.
            _bench_sel = _select_benchmark(mapped_sector, archetype)
            # Un solo benchmark por análisis (etapa 9a): medianas de múltiplos, umbrales del
            # score (ROE, ROA, D/E, márgenes), alertas y PDF leen la misma clave.
            result["benchmark"] = _bench_sel
            score_sector = _bench_sel["thresholds_key"]
            _sector_bench = _bench_sel["values"]
            fin_dict["sector_pe"] = _sector_bench.get("pe")
            # Etapa 11b: referencia del Forward P/E (la del sector; si no hay, la del P/E).
            fin_dict["sector_forward_pe"] = _sector_bench.get("forward_pe") or _sector_bench.get("pe")
            fin_dict["sector_ev_ebitda"] = _sector_bench.get("ev_ebitda")
            fin_dict["benchmark_profile"] = _bench_sel["profile"]

            # Crecimiento a 3 años para Crecimiento (etapa 9a): CAGR real de los 4
            # ejercicios anuales de los estados (historical_metrics.growth_rate, con la
            # regla de base anómala), no el interanual de Yahoo (revenueGrowth /
            # earningsGrowth, que comparan un trimestre con el del año anterior). Sin 4
            # ejercicios o con valores <= 0 en los extremos: sin dato con motivo, nunca
            # el interanual con la etiqueta de 3 años.
            _rev_r = growth_rate(_stmts.get("revenue") or [], 3, what="ingresos", strict_ends_only=True)
            fin_dict["revenue_cagr_3y"] = _rev_r["value"]
            fin_dict["revenue_growth_reason"] = _rev_r["reason"]
            _eps_series = _stmts.get("diluted_eps") or per_share(_stmts.get("net_income") or [],
                                                                  _stmts.get("ordinary_shares") or [])
            _eps_r = growth_rate(_eps_series, 3, what="BPA")
            fin_dict["eps_cagr_3y"] = _eps_r["value"]
            fin_dict["eps_growth_reason"] = _eps_r["reason"]
            if _rev_r.get("note") or _eps_r.get("note"):
                fin_dict["growth_cagr_notes"] = {k: r["note"] for k, r in (("ingresos", _rev_r), ("BPA", _eps_r))
                                                 if r.get("note")}
            # CAGR del FCF a 3 años con los 4 ejercicios anuales de los estados
            # (etapa 5). Indefinido -> sin dato con motivo, nunca un número.
            if fin_dict.get("fcf_cagr_3y") is None:
                _fcf_series = ((yinfo.get("_statements_fy") or {}).get("free_cash_flow")
                               if _has_yahoo else None)
                _fcf_r = growth_rate(_fcf_series, 3, what="FCF")   # con la regla de base anómala (etapa 7)
                fin_dict["fcf_cagr_3y"] = _fcf_r["value"]
                fin_dict["fcf_cagr_3y_reason"] = _fcf_r["reason"]
                fin_dict["fcf_cagr_3y_method"] = {k: _fcf_r.get(k) for k in ("method", "anomalous_base", "note")}

            # Crecimiento por rama (etapa 6).
            if archetype == CYCLICAL:
                # Crecimiento normalizado de ciclo medio (promedio interanual de los
                # ejercicios disponibles, acotado) en lugar del interanual de un solo
                # tramo; la tendencia del FCF de un tramo no aplica (RECON §7.9, §7.10).
                _gn = archetype_values.get("revenue_growth_normalized")
                if _gn is not None:
                    fin_dict["revenue_cagr_3y"] = _gn
                    _lo, _hi = cfg("valuation.archetypes.cyclical_growth_bounds")
                    fin_dict["revenue_growth_note"] = (
                        f"normalizado de ciclo medio: promedio interanual de {archetype_values['cycle_years']} "
                        f"ejercicios, acotado a [{_lo:.0%}, {_hi:.0%}]"
                        + ("; ciclo incompleto" if archetype_values.get("cycle_incomplete") else ""))
                # Etapa 9a: el BPA con la misma regla de ciclo medio que los ingresos.
                _ge = archetype_values.get("eps_growth_normalized")
                fin_dict["eps_cagr_3y"] = _ge
                fin_dict["eps_growth_reason"] = (None if _ge is not None else
                                                 "sin BPA positivo en ejercicios consecutivos para el promedio de ciclo")
                if _ge is not None:
                    _lo, _hi = cfg("valuation.archetypes.cyclical_growth_bounds")
                    fin_dict["eps_growth_note"] = (
                        f"normalizado de ciclo medio: promedio interanual del BPA de "
                        f"{archetype_values['eps_cycle_years']} ejercicios, acotado a [{_lo:.0%}, {_hi:.0%}]"
                        + ("; ciclo incompleto" if archetype_values.get("cycle_incomplete") else ""))
                fin_dict["fcf_cagr_3y"] = None
            elif archetype == REIT:
                # REIT: crecimiento POR ACCIÓN (FFO y FCF por acción); el agregado lo
                # infla la emisión estructural de acciones.
                fin_dict["revenue_cagr_3y"] = archetype_values.get("ffo_per_share_cagr_3y")
                fin_dict["revenue_growth_reason"] = archetype_values.get("ffo_per_share_cagr_3y_reason")
                _sh = archetype_values.get("shares_cagr_3y")
                _ffo = archetype_values.get("ffo_cagr_3y")
                fin_dict["revenue_growth_note"] = (
                    "FFO por acción (FFO = beneficio neto + D&A; acciones en circulación de cada ejercicio)"
                    + (f"; FFO agregado {_ffo:+.1%}" if _ffo is not None else "")
                    + (f", acciones {_sh:+.1%} anual" if _sh is not None else ""))
                fin_dict["fcf_cagr_3y"] = archetype_values.get("fcf_per_share_cagr_3y")
                fin_dict["fcf_cagr_3y_reason"] = archetype_values.get("fcf_per_share_cagr_3y_reason")

            # ── Etapa 7: crecimiento por acción en todos los arquetipos ──
            # Si las acciones en circulación (balance anual, base ajustada por
            # splits) crecen más del umbral, ingresos y FCF se evalúan por acción.
            # El BPA ya es por acción. El REIT lo hace siempre (FFO y FCF por acción).
            _gb = per_share_basis(_stmts.get("ordinary_shares") or [])
            growth_basis = dict(_gb, applied_to=[], eps="el BPA ya es por acción",
                                fcf_cagr=fin_dict.get("fcf_cagr_3y_method"))
            if archetype == REIT:
                _fps = growth_rate(per_share(_stmts.get("free_cash_flow") or [],
                                             _stmts.get("ordinary_shares") or []), 3, what="FCF por acción")
                growth_basis["fcf_cagr"] = {k: _fps.get(k) for k in ("method", "anomalous_base", "note")}
                growth_basis.update(basis="por_accion", applied_to=["FFO", "FCF"],
                                    reason="REIT: crecimiento por acción siempre (FFO y FCF por acción); "
                                           + _gb["reason"])
            elif _gb["basis"] == "por_accion":
                _s = _gb["shares_cagr_3y"]
                _g = fin_dict.get("revenue_cagr_3y")
                if _g is not None:
                    fin_dict["revenue_cagr_3y"] = (1 + _g) / (1 + _s) - 1
                    fin_dict["revenue_growth_note"] = "; ".join(filter(None, [
                        fin_dict.get("revenue_growth_note"),
                        f"por acción: {_g:+.1%} agregado ajustado por las acciones ({_s:+.1%} anual)"]))
                    growth_basis["applied_to"].append("ingresos")
                if fin_dict.get("fcf_cagr_3y") is not None or fin_dict.get("fcf_cagr_3y_reason"):
                    _fps = growth_rate(per_share(_stmts.get("free_cash_flow") or [],
                                                 _stmts.get("ordinary_shares") or []), 3, what="FCF por acción")
                    fin_dict["fcf_cagr_3y"] = _fps["value"]
                    fin_dict["fcf_cagr_3y_reason"] = _fps["reason"]
                    growth_basis["fcf_cagr"] = {k: _fps.get(k) for k in ("method", "anomalous_base", "note")}
                    growth_basis["applied_to"].append("FCF")
            # Etapa 9a: en GROWTH_PRE_PROFIT el crecimiento del FCF es el de FCF − SBC (misma base
            # por acción si aplica). Sin la serie de SBC: sin dato con motivo, no el FCF bruto.
            if archetype == GROWTH_PRE_PROFIT:
                _f, _s = _stmts.get("free_cash_flow") or [], _stmts.get("stock_based_compensation") or []
                if not _s:
                    fin_dict["fcf_cagr_3y"] = None
                    fin_dict["fcf_cagr_3y_reason"] = ("sin fila Stock Based Compensation: el crecimiento del FCF se "
                                                      "mide sobre FCF − SBC")
                else:
                    _adj = [(a - b) if (a is not None and b is not None) else None for a, b in zip(_f, _s)]
                    if "FCF" in growth_basis["applied_to"]:
                        _adj = per_share(_adj, _stmts.get("ordinary_shares") or [])
                    _ar = growth_rate(_adj, 3, what="FCF − SBC")
                    fin_dict["fcf_cagr_3y"] = _ar["value"]
                    fin_dict["fcf_cagr_3y_reason"] = _ar["reason"]
                    growth_basis["fcf_cagr"] = dict({k: _ar.get(k) for k in ("method", "anomalous_base", "note")},
                                                    basis="FCF − SBC")
            # Etapa 9a (regla general): negativo sostenido -> peor tramo, no "sin dato".
            fin_dict["fcf_cagr_3y_sustained_negative"] = is_sustained_negative(fin_dict.get("fcf_cagr_3y_reason"))
            result["growth_basis"] = {k: (safe_float(v) if isinstance(v, float) else v)
                                      for k, v in growth_basis.items()}

            # ── Fase C: creación de valor (ROIC-WACC) y retorno al accionista ──
            # ── Etapa 8: un solo WACC (DCF, grid, spread y lo que se muestra) ──
            # E/(D+E)·Ke + D/(D+E)·Kd·(1−t); FINANCIAL no usa WACC (P/B justificado con Ke).
            if archetype == FINANCIAL:
                wacc_info = {"value": None, "applicable": False,
                             "reason": not_applicable(archetype, "roic_wacc") or not_applicable_text(FINANCIAL)}
            else:
                wacc_info = compute_wacc(
                    beta=safe_float(financials.beta), rf=rf_info, market_cap=mcap, total_debt=td_val,
                    interest_coverage=safe_float(interest_cov),
                    coverage_state=interest_coverage_state(safe_float(interest_cov), r("net_debt")),
                    tax=tax_info)
                wacc_info["applicable"] = True
            wacc_est = wacc_info["value"]
            # Beta bruta (la de la fuente) y ajustada de Blume (la del Ke, también en FINANCIAL).
            _braw = safe_float(financials.beta)
            result["beta"] = {"raw": _braw, "adjusted": safe_float(adjusted_beta(_braw)), "method": "Blume",
                              "default": _braw is None,
                              "coefficients": [cfg("valuation.capm.blume_weight"), cfg("valuation.capm.blume_prior")]}
            result["wacc"] = {k: (safe_float(v) if isinstance(v, float) else v) for k, v in wacc_info.items()}
            result["tax_rate"] = {k: (safe_float(v) if isinstance(v, float) else v) for k, v in tax_info.items()}
            result["risk_free"] = dict(rf_info)
            # Spread ROIC-WACC: mide si la empresa genera retornos por ENCIMA de su
            # costo de capital (crea valor) o por debajo (lo destruye). No aplica a
            # financieras (WACC no interpretable), igual que el DCF/Altman.
            roic_wacc_spread = None
            if roic is not None and wacc_est is not None and not not_applicable(archetype, "roic_wacc"):
                roic_wacc_spread = roic - wacc_est
            # Buyback yield: reducción NETA de acciones vs el año previo (shares del
            # _prior_year de Yahoo, ya usadas para Piotroski). Una emisión (dilución)
            # da yield negativo, que es la señal correcta.
            _prior_shares = safe_float((yinfo.get("_prior_year") or {}).get("shares")) if _has_yahoo else None
            # Misma base que el año previo: acciones en circulación del ÚLTIMO
            # ejercicio fiscal (estados), no las acciones "en vivo" de la
            # cotización, que mezclan definición y periodo (no anualizado).
            _fy_shares = safe_float((yinfo.get("_piotroski_current") or {}).get("shares")) if _has_yahoo else None
            _cur_shares_bb = _fy_shares or shares_val
            buyback_yield = None
            if _prior_shares and _cur_shares_bb and _prior_shares > 0:
                buyback_yield = (_prior_shares - _cur_shares_bb) / _prior_shares
                # Guard de sanidad: un cambio anual de acciones fuera de ±25% casi
                # siempre es un desajuste de fuente (las shares actuales y las del
                # _prior_year de Yahoo pueden venir con definiciones distintas para
                # algunos tickers, ej. JPM ~35%). Mejor None que un yield falso.
                if abs(buyback_yield) > cfg("valuation.shareholder.buyback_yield_guard"):
                    buyback_yield = None
            # Shareholder yield = dividendos + recompras netas.
            shareholder_yield = None
            if div_yield is not None or buyback_yield is not None:
                shareholder_yield = (div_yield or 0.0) + (buyback_yield or 0.0)
            result["key_metrics"]["wacc"] = safe_float(wacc_est)
            result["key_metrics"]["roic_wacc_spread"] = safe_float(roic_wacc_spread)
            result["key_metrics"]["buyback_yield"] = safe_float(buyback_yield)
            result["key_metrics"]["shareholder_yield"] = safe_float(shareholder_yield)

            # v2.4: Inject derived metrics into ratios for scoring
            if earnings_yield is not None and ratios.get("earnings_yield") is None:
                ratios["earnings_yield"] = earnings_yield
            if pfcf is not None and ratios.get("p_fcf") is None:
                ratios["p_fcf"] = pfcf
            if fcf_yield is not None and ratios.get("fcf_yield") is None:
                ratios["fcf_yield"] = fcf_yield
            if roic is not None and ratios.get("roic") is None:
                ratios["roic"] = roic
            if div_yield is not None and ratios.get("dividend_yield") is None:
                ratios["dividend_yield"] = div_yield
            # FCF para Calidad (etapa 5): el FCF que ya existe (financials, validado
            # en la etapa 3 con FCF <= OCF) en lugar de OCF − capex con una capex que
            # a menudo no llega. "Sin dato" solo si no hay ninguno de los dos.
            if fcf_val is not None:
                ratios["fcf"] = fcf_val
                _ni = safe_float(financials.net_income)
                ratios["fcf_to_net_income"] = (fcf_val / _ni) if _ni else None

            # NOTE: the 0-100 score is computed AFTER the institutional metrics
            # block below, so it can feed the Altman Z-Score and Piotroski
            # F-Score into the solidez/calidad categories (see "Score (0-100)").


            # Institutional metrics — use prior-year data from Yahoo API
            # Defaults so the score block below can reference these even if the
            # institutional try fails partway through.
            z_val, z_zone, f_score = None, "N/A", None
            try:
                # Get prior-year data from Yahoo cached info
                prior = {}
                current_derived = {}
                try:
                    prior = yinfo.get("_prior_year", {}) if _has_yahoo else {}
                    current_derived = yinfo.get("_current_derived", {}) if _has_yahoo else {}
                    piotroski_fy = yinfo.get("_piotroski_current", {}) if _has_yahoo else {}
                except Exception as e:
                    _sin_dato("prior_year", e)

                # Altman Z-Score — se define sobre EJERCICIOS (etapa 7): estados del
                # último FY; los datos TTM/último trimestre solo si falta la fila anual.
                def _fy(key, fallback):
                    v = safe_float(((_stmts.get(key) or [None]) or [None])[0])
                    return v if v is not None else fallback
                z_ta = _fy("total_assets", ta_val)
                z_re = _fy("retained_earnings", safe_float(financials.retained_earnings))
                z_ebit = _fy("operating_income", oi_val)  # resultado operativo como EBIT
                z_mcap = mcap
                z_tl = _fy("total_liabilities", safe_float(financials.total_liabilities))
                z_rev = _fy("revenue", rev_val)
                z_te = _fy("stockholders_equity", te_val)

                # Estimate total_liabilities if missing
                if z_tl is None and z_ta and z_te:
                    z_tl = z_ta - z_te

                # Working capital — only compute if both components are available
                ca_val = _fy("current_assets", safe_float(financials.current_assets))
                cl_val = _fy("current_liabilities", safe_float(financials.current_liabilities))
                wc = (ca_val - cl_val) if (ca_val is not None and cl_val is not None) else None

                z_val, z_zone, z_interp, z_details = altman_z_score(
                    working_capital=wc,
                    total_assets=z_ta,
                    retained_earnings=z_re,
                    ebit=z_ebit,
                    market_value_equity=z_mcap,
                    total_liabilities=z_tl,
                    sales=z_rev,
                    sector=sector, industry=profile.industry or "",
                    book_value_equity=z_te,
                    not_applicable_reason=not_applicable(archetype, "altman"),
                )
                result["altman_z"] = {
                    # Etapa 9b: null sin dato o cuando no aplica (nunca un z = 0).
                    "z_score": z_val if (z_val is not None and not not_applicable(archetype, "altman")) else None,
                    "zone": z_zone.lower() if z_zone else "grey",
                    "interpretation": z_interp,
                    "model": z_details.get("model", ""),
                    "details": z_details,
                    # available=False indica "sin dato" (motivo en details.missing).
                    "available": z_val is not None,
                    "applicable": not not_applicable(archetype, "altman"),
                }

                # Piotroski F-Score — uses PURE fiscal year data (no TTM mixing)
                # piotroski_fy has FY current (e.g. FY2025), prior has FY prior (e.g. FY2024)
                # Fallback to TTM data only if yfinance enrichment didn't run
                pio_roa = safe_float(piotroski_fy.get("roa"))
                if pio_roa is None:
                    pio_roa = safe_float(ratios.get("roa"))
                    if pio_roa is None and safe_float(financials.net_income) and z_ta and z_ta > 0:
                        pio_roa = safe_float(financials.net_income) / z_ta

                pio_ni = safe_float(piotroski_fy.get("net_income")) or safe_float(financials.net_income)
                pio_ocf = safe_float(piotroski_fy.get("operating_cash_flow")) or safe_float(financials.operating_cash_flow)
                pio_ltd = safe_float(piotroski_fy.get("long_term_debt")) or safe_float(financials.long_term_debt)
                pio_cr = safe_float(piotroski_fy.get("current_ratio")) or safe_float(ratios.get("current_ratio"))
                pio_shares = safe_float(piotroski_fy.get("shares")) or shares_val
                pio_gm = safe_float(piotroski_fy.get("gross_margin")) or safe_float(current_derived.get("gross_margin")) or safe_float(ratios.get("gross_margin"))
                pio_at = safe_float(piotroski_fy.get("asset_turnover")) or safe_float(current_derived.get("asset_turnover")) or safe_float(ratios.get("asset_turnover"))
                pio_ta = safe_float(piotroski_fy.get("total_assets")) or z_ta

                _pio = piotroski_evaluate(
                    net_income=pio_ni,
                    roa_current=pio_roa,
                    roa_prior=safe_float(prior.get("roa")),
                    operating_cash_flow=pio_ocf,
                    long_term_debt_current=pio_ltd,
                    long_term_debt_prior=safe_float(prior.get("long_term_debt")),
                    current_ratio_current=pio_cr,
                    current_ratio_prior=safe_float(prior.get("current_ratio")),
                    shares_current=pio_shares,
                    shares_prior=safe_float(prior.get("shares")),
                    gross_margin_current=pio_gm,
                    gross_margin_prior=safe_float(prior.get("gross_margin")),
                    asset_turnover_current=pio_at,
                    asset_turnover_prior=safe_float(prior.get("asset_turnover")),
                    total_assets=pio_ta,
                )
                # Estado ESTRUCTURADO de cada criterio (cumple/no_cumple/sin_dato):
                # ya no se adivina por el símbolo ✓/✗ del texto (etapa 5).
                f_criteria = {c["key"]: {"passed": c["state"] == "cumple", "state": c["state"],
                                         "detail": c["detail"]}
                              for c in _pio["criteria"]}
                f_interp = _pio["interpretation"]
                f_level = piotroski_level(_pio["scaled_score"], _pio["conclusive"])
                # Lo que entra a Calidad: el escalado a base 9, o nada si no concluyente.
                f_score = _pio["scaled_score"] if _pio["conclusive"] else None

                # Fiscal year label for Piotroski
                fy_label = ""
                if _has_yahoo:
                    fy_current = yinfo.get("_fiscal_year_current", "")
                    fy_prior = prior.get("_fiscal_year", "")
                    if fy_current and fy_prior:
                        fy_label = f"FY{fy_current} vs FY{fy_prior}"
                    elif fy_current:
                        fy_label = f"FY{fy_current}"

                # Etapa 6: no aplica a FINANCIAL ni REIT (CFO, current ratio, margen
                # bruto y rotación no tienen sentido en esos balances).
                _pio_na = not_applicable(archetype, "piotroski")
                if _pio_na:
                    f_level, f_interp, f_score = "No aplica", _pio_na, None
                result["piotroski_f"] = {
                    # Etapa 9b: null cuando no aplica (FINANCIAL, REIT).
                    "score": None if _pio_na else _pio["score"], "max_score": _pio["max_score"], "level": f_level,
                    "interpretation": f_interp,
                    "applicable": not _pio_na,
                    "details": f_criteria,
                    "fiscal_year": fy_label,
                    # Cobertura (etapa 5): "X/N evaluados" y el escalado a base 9.
                    "evaluated": _pio["evaluated"],
                    "scaled_score": None if _pio_na else safe_float(_pio["scaled_score"]),
                    "conclusive": _pio["conclusive"],
                }

                # Financial health (sector financiero): NO se llama aquí.
                # financial_health_score requiere 5+ argumentos (roa, roe,
                # total_equity, total_assets, book_value, ...); pasarle un solo
                # dict lanzaba TypeError (tragado por este except) y el campo
                # quedaba null para todo banco/aseguradora. calculate_score_v2 ya
                # lo calcula correctamente para financieras y lo expone como
                # score_result["financial_health"], que se copia tras el bloque de
                # score (más abajo).
            except Exception as e:
                logger.error(f"Institutional metrics error: {e}")
                _sin_dato("altman_z/piotroski_f", e)

            # ── Etapa 7: normalización de ganancias (lib/normalize.py) ──
            # Ítems del MISMO periodo que el beneficio: TTM (suma de 4 trimestres)
            # si el beneficio es TTM; si no, el último FY. Con ítems explícitos (o
            # inferidos sobre el umbral) el score y las alertas usan el beneficio
            # normalizado; el informe muestra reportado y normalizado.
            ratios_score = ratios
            try:
                _tinfo = (yinfo.get("_ttm") or {}) if _has_yahoo else {}
                _q = (yinfo.get("_quarterly") or {}) if _has_yahoo else {}
                _ni = safe_float(financials.net_income)
                if "netIncome" in (_tinfo.get("ttm_fields") or []):
                    _rows = {}
                    for _r in _UNUSUAL_ROWS:
                        _v = [x for x in (_q.get(_r) or [])[:4] if x is not None]
                        if _v:
                            _rows[_r] = sum(_v)
                    _basis = "TTM (4 trimestres)"
                    _qn = _q
                else:
                    _rows = dict(_stmts.get("unusual_fy0") or {})
                    _basis = f"FY{(_stmts.get('inc_years') or ['?'])[0]} (sin TTM)"
                    _qn = None
                _pt, _tx = (_stmts.get("pretax_income") or [None])[0], (_stmts.get("tax_provision") or [None])[0]
                _t_fy = (_tx / _pt) if (_pt and _tx is not None and _pt > 0) else None
                _norm = normalize_earnings(net_income=_ni, explicit_rows=_rows, quarterly=_qn, basis=_basis,
                                           tax_rate_fallback=_t_fy, annual_rows=_stmts.get("unusual_fy") or {})
                _pe_rep = r("pe") if (r("pe") or 0) > 0 else None   # P/E <= 0 no es un múltiplo
                _nin = _norm["normalized_net_income"]
                _scale = (_ni / _nin) if (_norm["applied"] and _ni and _nin and _nin > 0 and _ni > 0) else None
                _norm["pe_reported"] = safe_float(_pe_rep)
                _norm["pe_normalized"] = safe_float(_pe_rep * _scale) if (_pe_rep and _scale) else None
                _norm["used_in_score"] = bool(_norm["applied"] and _nin is not None)
                # Etapa 9a: la etiqueta "normalizado" solo si difiere del reportado (> label_min_diff).
                _norm["differs"] = bool(_norm["used_in_score"] and _ni and _nin is not None
                                        and abs(_nin / _ni - 1) > cfg("thresholds.normalization.label_min_diff"))
                result["earnings_normalization"] = {k: (safe_float(v) if isinstance(v, float) else v)
                                                    for k, v in _norm.items()}
                result["key_metrics"]["pe_normalized"] = _norm["pe_normalized"]
                result["key_metrics"]["net_income_normalized"] = safe_float(_nin)
                if _norm["used_in_score"] and _ni:
                    _k = _nin / _ni
                    ratios_score = dict(ratios)
                    if _scale:
                        ratios_score["pe"] = _norm["pe_normalized"]
                        ratios_score["earnings_yield"] = (1 / _norm["pe_normalized"]) if _norm["pe_normalized"] else None
                    for _key in ("net_margin", "roe", "roa"):
                        if ratios.get(_key) is not None:
                            ratios_score[_key] = ratios[_key] * _k
                    ratios_score["net_income"] = _nin
                    if ratios.get("fcf") is not None and _nin:
                        ratios_score["fcf_to_net_income"] = ratios["fcf"] / _nin
                    # Etapa 9a: qué ratios del score y de las alertas salen del beneficio
                    # normalizado, para que el texto lo diga ("ROE normalizado 55.9%").
                    fin_dict["normalized_metrics"] = (
                        ([k for k in ("net_margin", "roe", "roa") if ratios.get(k) is not None]
                         + (["fcf_to_net_income"] if ratios.get("fcf") is not None else [])
                         + (["pe", "earnings_yield"] if _scale else []))
                        if _norm["differs"] else [])
            except Exception as e:
                _sin_dato("normalizacion_ganancias", e)

            # Valuation (Graham + DCF) — etapa 8: ANTES del score, porque el DCF es un
            # componente de Valoración con aporte acotado por su fiabilidad.
            dcf_for_score = None
            _multiples_signal = None
            _quality_part = _price_part = None
            try:
                price = financials.price
                eps = financials.eps
                bvps = financials.book_value_per_share

                # Graham number (no aplica a FINANCIAL ni a GROWTH_PRE_PROFIT)
                graham = None if not_applicable(archetype, "graham") else graham_number(eps, bvps)
                result["graham_number"] = safe_float(graham)

                if graham and price:
                    # margin_of_safety(intrinsic_value, current_price): el Graham
                    # Number ES el valor intrínseco y price el precio de mercado.
                    result["graham_margin"] = safe_float(
                        margin_of_safety(graham, price)
                    )

                # DCF-FCFF: el arquetipo decide si aplica (no en FINANCIAL ni REIT; en
                # GROWTH_PRE_PROFIT solo con FCF positivo) y con qué inputs. Sanitizado
                # (safe_float): un NaN o +Inf crudo no puede llegar al grid.
                fcf = safe_float(financials.free_cash_flow)
                # Etapa 9b (opción b): el crecimiento de entrada del DCF es SIEMPRE el de los estados,
                # el mismo que puntúa Crecimiento (fin_dict["revenue_cagr_3y"]): CAGR de ingresos a 3
                # años con la regla de base anómala, por acción si aplica la regla de dilución, ciclo
                # medio en CYCLICAL. El revenueGrowth de la fuente (interanual) ya no entra en el DCF.
                growth = safe_float(fin_dict.get("revenue_cagr_3y"))
                _growth_basis = ("ciclo medio de los ingresos" if archetype == CYCLICAL
                                 else "CAGR de ingresos por acción a 3 años"
                                 if "ingresos" in (growth_basis.get("applied_to") or [])
                                 else "CAGR de ingresos a 3 años")
                if growth is None:
                    growth, _growth_basis = cfg("valuation.dcf.default_growth"), "valor por defecto (sin CAGR de los estados)"
                _dcf_na = not_applicable(archetype, "dcf")
                if not _dcf_na and archetype == GROWTH_PRE_PROFIT and not (fcf and fcf > 0):
                    _dcf_na = (f"{not_applicable_text(GROWTH_PRE_PROFIT)} con FCF negativo: no hay flujo que "
                               "descontar")
                if _dcf_na:
                    result["not_applicable"]["dcf"] = _dcf_na
                _fcf_source = ((yinfo.get("_provenance") or {}).get("freeCashflow") or {}).get("source") \
                    if _has_yahoo else None
                _fcf_fields = cfg("thresholds.dcf_reliability.fcf_fields")
                _fcf_flags = [f"{f.get('field')}: {f.get('rule')}" for f in (yinfo.get("_validation") or [])
                              if f.get("field") in _fcf_fields] if _has_yahoo else []
                if archetype == CYCLICAL:
                    # Etapa 8: FCF de MANTENIMIENTO (OCF − D&A como capex de mantenimiento,
                    # promedio de los ejercicios): el normalizado (margen FCF medio ×
                    # ingresos) incluye el capex de expansión. Se muestran los dos.
                    fcf = safe_float(archetype_values.get("fcf_maintenance"))
                _dcf_missing = None
                # Etapa 11b: FCF base <= 0 (ya normalizado por el arquetipo: el de mantenimiento en
                # CYCLICAL) no es un dato ausente: el DCF "no es significativo" y no da valor razonable.
                _dcf_not_sig = None
                if _dcf_na:
                    pass
                elif fcf is None:
                    _dcf_missing = "sin FCF de entrada: no hay flujo que descontar"
                elif fcf <= 0:
                    _dcf_not_sig = (f"FCF base {numfmt.money(fcf)} (≤ 0): no hay flujo positivo que descontar, "
                                    "así que el DCF no es significativo")
                elif wacc_est is None:
                    _dcf_missing = wacc_info.get("reason") or "sin WACC"
                if not _dcf_na and not _dcf_missing and not _dcf_not_sig and price and financials.shares_outstanding:
                    # Deuda neta para el puente Enterprise Value -> Equity Value.
                    _net_debt = None
                    if td_val is not None or cash_val is not None:
                        _net_debt = (td_val or 0.0) - (cash_val or 0.0)

                    dcf_result = dcf_multi_stage_dynamic(
                        fcf=fcf,
                        shares_outstanding=financials.shares_outstanding,
                        wacc=wacc_est,   # el WACC único (cost_of_capital), ya acotado
                        total_debt=td_val,
                        cash=cash_val,
                        revenue_growth_3y=growth,  # el DCF aplica el tope (30%); sin suelo en el terminal
                    )
                    # DCF y grid comparten supuestos: el crecimiento USADO, su decaimiento y el WACC.
                    _g_used = dcf_result.get("growth_estimated")
                    if _g_used is None:
                        _g_used = growth
                    _decay = dcf_result.get("decay_type") or "linear"
                    _fv = safe_float(dcf_result.get("fair_value_per_share"))
                    if _fv is not None and _fv <= 0:
                        # Etapa 11b: nunca un valor razonable negativo. Si la deuda neta se come todo el
                        # valor de la empresa, el DCF tampoco es significativo.
                        _dcf_not_sig = (f"el valor de la empresa por DCF no cubre la deuda neta (valor del "
                                        f"capital {numfmt.price(_fv)} por acción, ≤ 0): el DCF no es significativo")
                        _fv = None
                    _dcf_upside = ((_fv - price) / price * 100.0) if (_fv is not None and price and price > 0) else None
                    _dcf_mos = ((_fv - price) / _fv) if (_fv not in (None, 0)) else None
                    _dcf_model = dcf_result.get("model_result") or {}
                    result["dcf"] = {
                        "fair_value": _fv,
                        "wacc": safe_float(wacc_est),   # el mismo que key_metrics.wacc y el grid
                        "growth_rate": safe_float(_g_used),  # el usado, no el bruto
                        "growth_source": dcf_result.get("growth_source"),
                        # Etapa 9b: de dónde sale el crecimiento usado (los estados, como Crecimiento).
                        "growth_basis": (_growth_basis if dcf_result.get("growth_source") == "revenue_growth_3y"
                                         else "valor por defecto (crecimiento de los estados no positivo o "
                                              "sin dato)"),
                        "terminal_growth": safe_float(cfg("valuation.dcf.terminal_growth")),
                        "margin_of_safety": safe_float(_dcf_mos),
                        "upside": safe_float(_dcf_upside),
                        "value_composition": _dcf_model.get("value_composition"),
                        "fcf_input": safe_float(fcf),
                        "available": _fv is not None,
                        "reason": dcf_result.get("invalid_reason"),
                        "warnings": dcf_result.get("warnings") or [],
                    }
                    if archetype == CYCLICAL:
                        result["dcf"]["normalized"] = {
                            "fcf": safe_float(archetype_values.get("fcf_normalized")),
                            "fcf_margin_avg": safe_float(archetype_values.get("fcf_margin_avg")),
                            "fcf_maintenance": safe_float(archetype_values.get("fcf_maintenance")),
                            "fcf_maintenance_years": archetype_values.get("fcf_maintenance_years"),
                            "fcf_used": "mantenimiento",
                            "years": archetype_values.get("cycle_years"),
                            "cycle_incomplete": archetype_values.get("cycle_incomplete"),
                        }

                    # Sensitivity: centrado en el WACC y el crecimiento usados.
                    sens = None
                    if _fv is not None and not _dcf_not_sig:
                        try:
                            sens = dcf_sensitivity_analysis(
                                fcf=fcf,
                                shares_outstanding=financials.shares_outstanding,
                                current_price=price,
                                base_growth_rate=_g_used,
                                base_discount_rate=wacc_est,
                                net_debt=_net_debt or 0.0,
                                decay_type=_decay,
                            )
                            result["sensitivity"] = sens
                        except Exception as e:
                            logger.error(f"Sensitivity error: {e}")
                            _sin_dato("sensitivity", e)
                    if _dcf_not_sig:
                        result["dcf"].update({"available": False, "reason": _dcf_not_sig, "not_significant": True,
                                              "margin_of_safety": None, "upside": None})
                    _rel = None if _dcf_not_sig else dcf_reliability(
                        dcf=result["dcf"], sensitivity=sens, price=price, archetype=archetype,
                        possible_cyclical=any(a.get("code") == "posible_ciclica"
                                              for a in classification.get("alerts") or []),
                        fcf_flags=_fcf_flags, fcf_source=_fcf_source)
                    result["dcf"]["reliability"] = _rel
                    if _dcf_not_sig:
                        pass
                    elif _rel:
                        dcf_for_score = {"upside": _dcf_upside / 100.0 if _dcf_upside is not None else None,
                                         "reliability": _rel["level"], "reasons": _rel["reasons"],
                                         "grid_contains_price": _rel["grid_contains_price"]}
                    else:
                        _dcf_missing = result["dcf"]["reason"] or "DCF sin valor"
                if _dcf_na:
                    dcf_for_score = {"na": _dcf_na}
                elif _dcf_not_sig:
                    dcf_for_score = {"not_significant": _dcf_not_sig}
                elif dcf_for_score is None:
                    dcf_for_score = {"missing_reason": _dcf_missing or "sin precio o acciones en circulación"}
                result["dcf_status"] = {"state": "no_aplica" if _dcf_na else "no_significativo" if _dcf_not_sig
                                        else ("ok" if dcf_for_score.get("reliability") else "sin_dato"),
                                        "reason": _dcf_na or _dcf_not_sig or dcf_for_score.get("missing_reason")}
            except Exception as e:
                logger.error(f"Valuation error: {e}")
                _sin_dato("graham/dcf", e)

            # Score (0-100) — normalize to standard format.
            # Computed here (after institutional metrics) so the Altman Z-Score
            # and Piotroski F-Score actually feed the solidez/calidad categories.
            try:
                # If the F-Score is inconclusive (a low value driven by missing
                # historical data, e.g. recent IPOs), don't let it penalize the
                # calidad category — pass None so that component is treated as
                # neutral. The displayed F-Score is unaffected.
                # Piotroski no concluyente (cobertura < min_evaluated) -> None:
                # no aporta a Calidad, que se reescala sobre el resto (etapa 5).
                _f_for_score = f_score
                score_result = calculate_score_v2(
                    ratios_score, fin_dict,
                    z_score_value=z_val,
                    z_score_level=z_zone,
                    f_score_value=_f_for_score,
                    sector_key=score_sector,
                    real_sector=sector,
                    wacc=wacc_est,  # Fase C: spread ROIC-WACC en rentabilidad
                    archetype=archetype,
                    archetype_values=archetype_values,
                    dcf=dcf_for_score,
                )

                # Build category breakdown from categories array or category_scores dict
                breakdown = {}
                categories_list = score_result.get("categories", []) if isinstance(score_result, dict) else []
                _multiples_signal = next((c.get("multiples_signal") for c in categories_list
                                          if c.get("category") == "Valoración"), None)
                for cat in categories_list:
                    key = cat.get("category", "unknown")
                    breakdown[key] = {
                        # Etapa 5: categoría no concluyente (excluida del total) y su cobertura.
                        "conclusive": cat.get("conclusive", True),
                        "applicable": cat.get("applicable", True),
                        "coverage": (cat.get("coverage") or {}).get("coverage"),
                        "score": cat.get("score", 0),
                        "max": cat.get("max_score", cfg("thresholds.score.category.max")),
                        "details": [a.get("reason", "") for a in cat.get("adjustments", [])],
                        "adjustments": cat.get("adjustments", []),
                    }

                # Etapa 9a: `score` ya no tiene total único (total_score / max_score /
                # level): conserva el desglose por categoría. Las dos puntuaciones
                # van en `quality` y `price_attractiveness` (veredicto en `verdict`).
                result["score"] = {
                    "breakdown": breakdown,
                    # Etapa 5: categorías excluidas del total por cobertura < 50%.
                    "excluded_categories": (score_result.get("excluded_categories", [])
                                            if isinstance(score_result, dict) else []),
                    "not_applicable_categories": (score_result.get("not_applicable_categories", [])
                                                  if isinstance(score_result, dict) else []),
                }
                _quality_part = score_result.get("quality")
                _price_part = score_result.get("price_raw")
                result["eps_vs_revenue_growth"] = score_result.get("eps_vs_revenue_growth")

                # Financial health (sector financiero): calculate_score_v2 ya lo
                # computó correctamente con los argumentos correctos; exponerlo
                # como {score, level, interpretation, details} para el frontend.
                # Cobertura por categoría (bloque nuevo del contrato, etapa 5). La
                # baja confianza no cambia el score: la usará la etapa 8.
                if isinstance(score_result, dict) and score_result.get("coverage"):
                    result["score_coverage"] = score_result["coverage"]

                if isinstance(score_result, dict) and score_result.get("financial_health"):
                    result["financial_health"] = score_result["financial_health"]

            except Exception as e:
                logger.error(f"Score calculation error: {e}")
                result["score"] = None
                _sin_dato("score", e)

            # Alerts — motor de interpretación de señales (el "cerebro"): convierte
            # los ratios crudos en fortalezas/advertencias/riesgos con una lectura
            # ADAPTATIVA de 1-2 líneas por ítem (lib/alert_interpretations.py),
            # graduada por magnitud y sector. Reemplaza el ensamblado disperso
            # anterior (condiciones crudas con detail vacío).
            try:
                result["alerts"] = build_signals(
                    ratios_score, fin_dict,
                    sector=score_sector, real_sector=sector,
                    roic_wacc_spread=roic_wacc_spread,
                    altman=result.get("altman_z"),
                    piotroski=result.get("piotroski_f"),
                    dcf=result.get("dcf"),
                    archetype=archetype,
                    archetype_values=archetype_values,
                )
            except Exception as e:
                logger.error(f"Alerts error: {e}")
                result["alerts"] = {"red_flags": [], "warnings": [], "strengths": []}
                _sin_dato("alerts", e)

            # Historical price data for chart
            try:
                result["price_history"] = {
                    "52w_high": safe_float(financials.price_52w_high),
                    "52w_low": safe_float(financials.price_52w_low),
                    "beta": safe_float(financials.beta),
                }
            except Exception as e:
                _sin_dato("price_history", e)

            # Etapa 9b: yearly_financials sale de los estados anuales (archetype_metrics.yearly_financials),
            # los mismos de los CAGR; ya no del módulo earnings de quoteSummary (solo local).

        # Validación de salida: múltiplos <= 0 -> "no significativo". Va al
        # final para no alterar las entradas del score ni de las alertas.
        _out_flags = []
        try:
            from validate import validate_outputs
            _out_flags = validate_outputs(result)
        except Exception as e:
            _sin_dato("validacion_salida", e)
        result["data_validation"] = list(yinfo.get("_validation") or []) + _row_flags + _out_flags
        result["data_provenance"] = _build_provenance(yinfo, _out_flags, _block_errors)

        # ── Etapa 8: confianza del veredicto (spec Sección 3) ──
        # Se calcula y se muestra (JSON, PDF); NO limita el score: el techo
        # condicionado por la confianza es de la etapa 9.
        if financials and result.get("score"):
            try:
                _price = safe_float(financials.price)
                _d = result.get("dcf") or {}
                _arch = (result.get("classification") or {}).get("archetype")
                _methods = []
                if _arch == FINANCIAL:
                    # FINANCIAL: dos métodos sobre el P/B. Intrínseco: P/B justificado por
                    # Gordon ((ROE − g)/(Ke − g)); relativo: P/B frente a la mediana del sector.
                    _xm = result.get("archetype_metrics") or {}
                    _pb = _xm.get("pb")
                    if _pb and _xm.get("pb_justified"):
                        _methods.append({"method": "P/B justificado (Gordon)", "kind": "intrínseco",
                                         "upside": _xm["pb_justified"] / _pb - 1})
                    _spb = _get_sector_benchmarks(mapped_sector).get("pb")
                    if _pb and _spb:
                        _methods.append({"method": "P/B frente al sector", "kind": "relativo",
                                         "upside": _spb / _pb - 1, "benchmark": _spb})
                else:
                    if _d.get("upside") is not None:
                        _methods.append({"method": "DCF", "kind": "intrínseco", "upside": _d["upside"] / 100.0,
                                         "reliability": (_d.get("reliability") or {}).get("level")})
                    if _multiples_signal:
                        _methods.append({"method": "múltiplos frente al sector", "kind": "relativo",
                                         "signal": _multiples_signal["value"],
                                         "components": _multiples_signal["components"]})
                # Graham no vota: es la referencia del inversor defensivo (P/E 15 × P/B 1.5).
                for _m in _methods:
                    if "upside" in _m:
                        _m["signal"] = signal_from_upside(_m["upside"])
                _cls = result.get("classification") or {}
                result["confidence"] = verdict_confidence({
                    "convergence": convergence(_methods),
                    "coverage": coverage_dimension(result.get("score_coverage"),
                                                   (result["score"] or {}).get("excluded_categories") or []),
                    "source": source_dimension(
                        input_flags=list(yinfo.get("_validation") or []) + _row_flags,
                        normalization=result.get("earnings_normalization"),
                        ttm=yinfo.get("_ttm"), provenance_fields=(yinfo.get("_provenance") or {})),
                    "stability": stability_dimension(_cls.get("archetype"), _cls),
                })
            except Exception as e:
                _sin_dato("confianza", e)
            # ── Etapa 9a: calidad del negocio y atractivo del precio (lib/verdict.py) ──
            # El precio se contrae hacia 50 según la confianza del veredicto de valoración.
            try:
                if _quality_part is not None:
                    result["quality"] = _quality_part
                    _cats = score_result.get("categories") or []
                    # `price` ya es el precio de la acción: la puntuación va en price_attractiveness.
                    result["price_attractiveness"] = verdict_price(_cats, (result.get("confidence") or {}).get("level"))
                    result["verdict"] = build_verdict(result["quality"], result["price_attractiveness"],
                                                      result.get("confidence"))
            except Exception as e:
                _sin_dato("veredicto", e)

        # ── Etapa 9b: capa de presentación compartida (lib/display.py) ──
        # Lo que se LEE de cada métrica se calcula una vez aquí; el PDF y la web lo consumen.
        try:
            from display import build_display
            result["display"] = build_display(result, _pdf_benchmark(result))
        except Exception as e:
            _sin_dato("display", e)

        return result

    except HTTPException:
        raise
    except CurrencyConversionError as e:
        # Etapa 11b: estados en otra moneda sin tipo de cambio: no se analiza (nunca se mezclan monedas).
        raise HTTPException(status_code=422, detail=(
            f"No se puede analizar {symbol}: sus estados financieros están en otra moneda que su cotización y "
            f"no hay tipo de cambio para convertirlos ({e}). Finanzer no mezcla monedas."))
    except InvalidSymbolError:
        # The data layer applies a stricter symbol regex than this endpoint's
        # own validation (it rejects ^ and =, so indices/forex such as ^GSPC or
        # EURUSD=X pass the API check but are rejected here). A rejected symbol
        # is a client error — return a clean 400 instead of a 500 that leaks the
        # internal error string.
        raise HTTPException(status_code=400, detail="Invalid symbol")
    except Exception as e:
        logger.error(f"Analysis error for {symbol}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/analysis/{symbol}")
async def analyze_stock(symbol: str):
    """Complete stock analysis - the main endpoint."""
    return _compute_analysis(symbol)


@app.get("/api/pdf/{symbol}")
async def download_pdf(symbol: str):
    """Generate a comprehensive PDF financial report mirroring the app."""
    from datetime import datetime

    symbol = symbol.upper().strip()

    try:
        # Re-use the same analysis logic as the API endpoint
        analysis = _compute_analysis(symbol)

        # El informe completo (identidad Finanzer, narrativa adaptativa por
        # bandas, logo, layout editorial) vive en lib/pdf_report.py.
        from pdf_report import build_report

        logo_path = None
        _base = os.path.dirname(os.path.abspath(__file__))
        for _cand in (
            os.path.join(_base, "..", "frontend", "public", "logo.png"),
            os.path.join(_base, "..", "frontend", "out", "logo.png"),
        ):
            if os.path.isfile(_cand):
                logo_path = os.path.abspath(_cand)
                break

        buf = io.BytesIO()
        build_report(
            buf, analysis,
            sector_bench=_pdf_benchmark(analysis),
            logo_path=logo_path,
        )
        buf.seek(0)

        return StreamingResponse(
            buf,
            media_type="application/pdf",
            # Nombre con espacios -> entre comillas (RFC 6266) para que el
            # navegador no lo trunque en el primer espacio.
            headers={"Content-Disposition": f'attachment; filename="Informe Finanzer {symbol} {datetime.now().strftime("%Y-%m-%d")}.pdf"'}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"PDF generation error for {symbol}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health")
async def health():
    return {"status": "ok"}


# ── Serve frontend static files ──
# The frontend is built as a static export in ../frontend/out
_frontend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend", "out")
_frontend_dir = os.path.abspath(_frontend_dir)

if os.path.isdir(_frontend_dir):
    # Serve _next static assets
    _next_dir = os.path.join(_frontend_dir, "_next")
    if os.path.isdir(_next_dir):
        app.mount("/_next", StaticFiles(directory=_next_dir), name="next_static")

    @app.get("/")
    async def serve_index():
        index_path = os.path.join(_frontend_dir, "index.html")
        if os.path.isfile(index_path):
            return FileResponse(index_path, media_type="text/html")
        return HTMLResponse("<h1>Finanzer</h1><p>Frontend not built.</p>")

    # Serve stock pages — SPA fallback using the stock page HTML
    @app.get("/stock/{symbol:path}")
    async def serve_stock_page(symbol: str):
        # Serve real files under stock/ — e.g. the Next.js RSC .txt payloads used
        # for client-side (soft) navigation. Without this they'd hit the SPA HTML
        # fallback below and navigation would degrade to full page reloads.
        # Guard against path traversal; real tickers (AAPL, BRK.B) aren't files
        # and fall through to the SPA HTML.
        if "/" not in symbol and ".." not in symbol:
            candidate = os.path.join(_frontend_dir, "stock", symbol)
            if os.path.isfile(candidate):
                return FileResponse(candidate)
        # Otherwise it's a ticker route → serve the stock page HTML (SPA)
        stock_index = os.path.join(_frontend_dir, "stock", "index.html")
        if os.path.isfile(stock_index):
            return FileResponse(stock_index, media_type="text/html")
        # Fallback to root index
        index_path = os.path.join(_frontend_dir, "index.html")
        return FileResponse(index_path, media_type="text/html")

    # Serve other static files (favicon, svgs, etc.)
    @app.get("/{filepath:path}")
    async def serve_static(filepath: str):
        # Confine to the frontend dir. A `:path` param accepts slashes and `..`,
        # so without this an encoded request like /%2e%2e/%2e%2e/backend/main.py
        # (uvicorn decodes %2e%2e%2f -> ../) would escape _frontend_dir and serve
        # arbitrary files (source code, /etc/passwd). Resolve then verify the
        # real path stays inside the served directory before touching disk.
        full_path = os.path.abspath(os.path.join(_frontend_dir, filepath))
        if full_path == _frontend_dir or full_path.startswith(_frontend_dir + os.sep):
            # Try exact file
            if os.path.isfile(full_path):
                return FileResponse(full_path)
            # Try with index.html (for directory paths)
            index_path = os.path.join(full_path, "index.html")
            if os.path.isfile(index_path):
                return FileResponse(index_path, media_type="text/html")
        # Fallback to root index (SPA) — also the response for traversal attempts
        root_index = os.path.join(_frontend_dir, "index.html")
        if os.path.isfile(root_index):
            return FileResponse(root_index, media_type="text/html")
        raise HTTPException(status_code=404, detail="Not found")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
