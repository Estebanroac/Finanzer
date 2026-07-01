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

from data_fetcher import FinancialDataService
from financial_ratios import (
    calculate_all_ratios, calculate_score_v2, aggregate_alerts,
    altman_z_score, piotroski_f_score, financial_health_score,
    graham_number, margin_of_safety, dcf_multi_stage_dynamic,
    dcf_sensitivity_analysis, calculate_wacc, classify_company_type,
    detect_growth_company
)
from stock_database import search_stocks, POPULAR_STOCKS, TOP_STOCKS
from sector_profiles import get_sector_profile, YAHOO_SECTOR_MAPPING
import config

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
        if f != f:  # NaN check
            return None
        return f
    except (TypeError, ValueError):
        return None


def financials_to_dict(fin) -> Dict[str, Any]:
    """Convert FinancialStatements dataclass to dict for ratio calculations."""
    if fin is None:
        return {}
    return {k: v for k, v in fin.__dict__.items() if v is not None}


def _get_sector_benchmarks(sector: str) -> dict:
    """Sector benchmark averages for PDF comparative section (mirrors frontend)."""
    defaults = {
        "pe": 22, "forward_pe": 18, "pb": 3.5, "ev_ebitda": 14, "pfcf": 25, "peg": 1.5,
        "roe": 0.15, "roa": 0.06, "roic": 0.10, "net_margin": 0.10, "operating_margin": 0.15, "gross_margin": 0.40,
        "current_ratio": 1.5, "de": 0.8, "interest_coverage": 8, "fcf_yield": 0.04,
        "revenue_growth": 0.08, "earnings_growth": 0.10,
    }
    sector_map = {
        "technology": {"pe": 30, "forward_pe": 25, "pb": 8, "ev_ebitda": 20, "roe": 0.25, "roa": 0.10, "roic": 0.18, "net_margin": 0.20, "operating_margin": 0.25, "gross_margin": 0.60, "revenue_growth": 0.15, "earnings_growth": 0.18},
        "healthcare": {"pe": 25, "forward_pe": 20, "pb": 4, "ev_ebitda": 16, "roe": 0.18, "net_margin": 0.15, "gross_margin": 0.55, "revenue_growth": 0.10},
        "financials": {"pe": 13, "forward_pe": 11, "pb": 1.5, "roe": 0.12, "roa": 0.01, "de": 2.5, "net_margin": 0.25, "current_ratio": 0, "interest_coverage": 0},
        "consumer_cyclical": {"pe": 20, "forward_pe": 17, "pb": 5, "ev_ebitda": 13, "roe": 0.20, "net_margin": 0.08, "gross_margin": 0.35, "revenue_growth": 0.08},
        "consumer_defensive": {"pe": 23, "forward_pe": 20, "pb": 6, "ev_ebitda": 16, "roe": 0.25, "net_margin": 0.08, "gross_margin": 0.35, "de": 1.2, "revenue_growth": 0.05, "earnings_growth": 0.06},
        "communication": {"pe": 18, "forward_pe": 16, "pb": 3, "ev_ebitda": 10, "roe": 0.12, "net_margin": 0.12, "gross_margin": 0.55},
        "energy": {"pe": 10, "forward_pe": 9, "pb": 1.8, "ev_ebitda": 6, "roe": 0.15, "net_margin": 0.08, "de": 0.5, "revenue_growth": 0.03},
        "industrials": {"pe": 20, "forward_pe": 18, "pb": 4, "ev_ebitda": 13, "roe": 0.18, "net_margin": 0.08, "gross_margin": 0.30, "revenue_growth": 0.06},
        "utilities": {"pe": 18, "forward_pe": 16, "pb": 1.8, "ev_ebitda": 12, "roe": 0.10, "de": 1.5, "net_margin": 0.12, "revenue_growth": 0.03},
        "real_estate": {"pe": 35, "forward_pe": 30, "pb": 2.0, "ev_ebitda": 20, "roe": 0.06, "de": 1.0, "net_margin": 0.20},
        "materials": {"pe": 14, "forward_pe": 12, "pb": 2, "ev_ebitda": 8, "roe": 0.12, "net_margin": 0.08, "de": 0.6},
    }
    import re
    key = re.sub(r'[\s-]+', '_', sector.lower())
    overrides = sector_map.get(key, {})
    return {**defaults, **overrides}


@app.get("/api/search")
async def search(q: str = Query("", min_length=1)):
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


def _compute_analysis(symbol: str) -> dict:
    """
    Shared analysis computation used by both API endpoint and PDF generator.
    Returns the full analysis dict or raises HTTPException.
    """
    symbol = symbol.upper().strip()
    if not symbol or len(symbol) > 15:
        raise HTTPException(status_code=400, detail="Invalid symbol")

    try:
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
                }

                for k, v in fallback_map.items():
                    if ratios.get(k) is None and v is not None:
                        ratios[k] = v
            except Exception as e:
                logger.debug(f"Yahoo ratio fallback error: {e}")

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
                nopat = oi_val * 0.79  # Approx 21% tax rate
                invested_capital = te_val + (td_val or 0) - (cash_val or 0)
                if invested_capital > 0:
                    roic = nopat / invested_capital

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
                "current_ratio": r("current_ratio"),
                "quick_ratio": r("quick_ratio"),
                "interest_coverage": safe_float(interest_cov),
                "debt_to_assets": safe_float(debt_to_assets),
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

            # Inject sector-median benchmarks so valuation scoring judges P/E and
            # EV/EBITDA against the stock's SECTOR (e.g. ~30x for tech, ~12x for
            # banks) instead of a fixed ~20x. Without this, high-P/E sectors look
            # overvalued and low-P/E sectors look cheap regardless of fundamentals.
            _sector_bench = _get_sector_benchmarks(mapped_sector)
            fin_dict["sector_pe"] = _sector_bench.get("pe")
            fin_dict["sector_ev_ebitda"] = _sector_bench.get("ev_ebitda")

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

            # NOTE: the 0-100 score is computed AFTER the institutional metrics
            # block below, so it can feed the Altman Z-Score and Piotroski
            # F-Score into the solidez/calidad categories (see "Score (0-100)").

            # Company type
            try:
                company_type = classify_company_type(ratios)
                is_growth = detect_growth_company(ratios)
                result["company_type"] = company_type
                result["is_growth"] = is_growth
            except Exception:
                result["company_type"] = "balanced"
                result["is_growth"] = False

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
                except Exception:
                    pass

                # Altman Z-Score — use best available data
                z_ta = ta_val  # total_assets already computed above
                z_re = safe_float(financials.retained_earnings)
                z_ebit = oi_val  # operating_income
                z_mcap = mcap
                z_tl = safe_float(financials.total_liabilities)
                z_rev = rev_val

                # Estimate total_liabilities if missing
                if z_tl is None and z_ta and te_val:
                    z_tl = z_ta - te_val

                # Working capital — only compute if both components are available
                ca_val = safe_float(financials.current_assets)
                cl_val = safe_float(financials.current_liabilities)
                wc = (ca_val - cl_val) if (ca_val is not None and cl_val is not None) else None

                z_val, z_zone, z_interp, z_details = altman_z_score(
                    working_capital=wc,
                    total_assets=z_ta,
                    retained_earnings=z_re,
                    ebit=z_ebit,
                    market_value_equity=z_mcap,
                    total_liabilities=z_tl,
                    sales=z_rev,
                    sector=sector,
                    book_value_equity=te_val,
                )
                result["altman_z"] = {
                    "z_score": z_val if z_val is not None else 0,
                    "zone": z_zone.lower() if z_zone else "grey",
                    "interpretation": z_interp,
                    "model": z_details.get("model", ""),
                    "details": z_details,
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

                f_score, f_details, f_interp = piotroski_f_score(
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
                f_level = "Fuerte" if f_score >= 7 else "Bueno" if f_score >= 5 else "Neutral" if f_score >= 4 else "Débil"

                # Convert detail strings to structured criteria for frontend
                criteria_labels = [
                    "roa_positive", "cfo_positive", "roa_improved", "earnings_quality",
                    "debt_reduced", "current_ratio_improved", "no_dilution",
                    "gross_margin_improved", "asset_turnover_improved"
                ]
                f_criteria = {}
                for i, detail_str in enumerate(f_details):
                    key = criteria_labels[i] if i < len(criteria_labels) else f"criterion_{i}"
                    passed = detail_str.startswith("✓")
                    # Remove ✓/✗ prefix
                    clean_detail = detail_str[2:].strip() if len(detail_str) > 2 else detail_str
                    f_criteria[key] = {"passed": passed, "detail": clean_detail}

                # Fiscal year label for Piotroski
                fy_label = ""
                if _has_yahoo:
                    fy_current = yinfo.get("_fiscal_year_current", "")
                    fy_prior = prior.get("_fiscal_year", "")
                    if fy_current and fy_prior:
                        fy_label = f"FY{fy_current} vs FY{fy_prior}"
                    elif fy_current:
                        fy_label = f"FY{fy_current}"

                result["piotroski_f"] = {
                    "score": f_score, "max_score": 9, "level": f_level,
                    "interpretation": f_interp,
                    "details": f_criteria,
                    "fiscal_year": fy_label,
                }

                # Financial health (for financial sector)
                if mapped_sector and "financ" in mapped_sector.lower():
                    fh_result = financial_health_score(fin_dict)
                    result["financial_health"] = fh_result
            except Exception as e:
                logger.error(f"Institutional metrics error: {e}")

            # Score (0-100) — normalize to standard format.
            # Computed here (after institutional metrics) so the Altman Z-Score
            # and Piotroski F-Score actually feed the solidez/calidad categories.
            try:
                score_result = calculate_score_v2(
                    ratios, fin_dict,
                    z_score_value=z_val,
                    z_score_level=z_zone,
                    f_score_value=f_score,
                    sector_key=mapped_sector,
                    real_sector=sector
                )
                # Normalize: the brain returns different structures, unify them
                raw_score = score_result.get("score", 0) if isinstance(score_result, dict) else 0
                raw_max = score_result.get("max_score", 100) if isinstance(score_result, dict) else 100
                raw_level = score_result.get("level", "N/A") if isinstance(score_result, dict) else "N/A"

                # Build category breakdown from categories array or category_scores dict
                breakdown = {}
                categories_list = score_result.get("categories", []) if isinstance(score_result, dict) else []
                for cat in categories_list:
                    key = cat.get("category", "unknown")
                    breakdown[key] = {
                        "score": cat.get("score", 0),
                        "max": cat.get("max_score", 20),
                        "details": [a.get("reason", "") for a in cat.get("adjustments", [])],
                        "adjustments": cat.get("adjustments", []),
                    }

                result["score"] = {
                    "total_score": raw_score,
                    "max_score": raw_max,
                    "level": raw_level,
                    "breakdown": breakdown,
                }
            except Exception as e:
                logger.error(f"Score calculation error: {e}")
                result["score"] = None

            # Valuation (Graham + DCF)
            try:
                price = financials.price
                eps = financials.eps
                bvps = financials.book_value_per_share

                # Graham number
                graham = graham_number(eps, bvps)
                result["graham_number"] = safe_float(graham)

                if graham and price:
                    result["graham_margin"] = safe_float(
                        margin_of_safety(price, graham)
                    )

                # DCF
                fcf = financials.free_cash_flow
                if fcf and fcf > 0 and price and financials.shares_outstanding:
                    beta = financials.beta if financials.beta is not None else 1.0
                    wacc = calculate_wacc(beta=beta)
                    growth = financials.revenue_growth_yoy or 0.10

                    dcf_result = dcf_multi_stage_dynamic(
                        fcf=fcf,
                        shares_outstanding=financials.shares_outstanding,
                        beta=beta,
                        revenue_growth_3y=min(growth, 0.50),
                    )
                    result["dcf"] = {
                        "fair_value": safe_float(dcf_result.get("fair_value_per_share")),
                        "wacc": safe_float(wacc),
                        "growth_rate": safe_float(growth),
                        "terminal_growth": safe_float(getattr(config, "DCF_TERMINAL_GROWTH", 0.025)),
                        "margin_of_safety": safe_float(dcf_result.get("margin_of_safety_value")),
                        "upside": safe_float(dcf_result.get("upside_pct")),
                        "value_composition": dcf_result.get("value_composition"),
                    }

                    # Sensitivity
                    try:
                        sens = dcf_sensitivity_analysis(
                            fcf=fcf,
                            shares_outstanding=financials.shares_outstanding,
                            current_price=price,
                            base_growth_rate=min(growth, 0.50),
                            base_discount_rate=wacc or 0.10,
                        )
                        result["sensitivity"] = sens
                    except Exception as e:
                        logger.error(f"Sensitivity error: {e}")
            except Exception as e:
                logger.error(f"Valuation error: {e}")

            # Alerts — normalize into red_flags/warnings/strengths
            try:
                raw_alerts = aggregate_alerts(
                    ratios, fin_dict,
                    sector=mapped_sector,
                    real_sector=sector,
                    precomputed_f_score=result.get("piotroski_f", {}).get("score"),
                )

                # The brain returns alerts grouped by category (valuation, leverage, etc.)
                # Each category has items with severity levels
                red_flags = []
                warnings = []
                strengths = []

                alert_categories = [
                    "valuation", "leverage", "liquidity", "profitability",
                    "cash_flow", "growth", "structural_deterioration", "volatility"
                ]

                for cat_key in alert_categories:
                    cat_alerts = raw_alerts.get(cat_key)
                    if not cat_alerts:
                        continue

                    items = []
                    if isinstance(cat_alerts, list):
                        items = cat_alerts
                    elif isinstance(cat_alerts, dict):
                        # Some categories return dicts with nested lists
                        for sub_key, sub_val in cat_alerts.items():
                            if isinstance(sub_val, list):
                                items.extend(sub_val)
                            elif isinstance(sub_val, dict) and "reason" in sub_val:
                                items.append(sub_val)

                    for item in items:
                        if not isinstance(item, dict):
                            continue
                        severity = item.get("severity", "").lower()
                        alert_obj = {
                            "category": cat_key.replace("_", " ").title(),
                            "reason": item.get("metric", item.get("reason", "")),
                            "detail": item.get("reason", item.get("detail", item.get("interpretation", ""))),
                        }
                        if severity in ("severe", "critical", "danger", "red"):
                            red_flags.append(alert_obj)
                        elif severity in ("moderate", "warning", "caution", "yellow"):
                            warnings.append(alert_obj)
                        elif severity in ("good", "excellent", "strong", "green", "positive"):
                            strengths.append(alert_obj)
                        elif severity:
                            warnings.append(alert_obj)

                # Also pull from score adjustments if we have them
                if result.get("score") and result["score"].get("breakdown"):
                    for cat_name, cat_data in result["score"]["breakdown"].items():
                        for adj in cat_data.get("adjustments", []):
                            sev = adj.get("severity", "").lower()
                            alert_obj = {
                                "category": cat_name,
                                "reason": adj.get("metric", ""),
                                "detail": adj.get("reason", ""),
                            }
                            if sev in ("severe", "critical", "danger"):
                                red_flags.append(alert_obj)
                            elif sev in ("moderate", "warning"):
                                warnings.append(alert_obj)
                            elif sev in ("good", "excellent"):
                                strengths.append(alert_obj)

                result["alerts"] = {
                    "red_flags": red_flags,
                    "warnings": warnings,
                    "strengths": strengths,
                }
            except Exception as e:
                logger.error(f"Alerts error: {e}")
                result["alerts"] = {"red_flags": [], "warnings": [], "strengths": []}

            # Historical price data for chart
            try:
                result["price_history"] = {
                    "52w_high": safe_float(financials.price_52w_high),
                    "52w_low": safe_float(financials.price_52w_low),
                    "beta": safe_float(financials.beta),
                }
            except Exception:
                pass

            # Yearly financials (for historical trends chart)
            try:
                yearly = yinfo.get("_yearly_financials", []) if _has_yahoo else []
                if yearly:
                    result["yearly_financials"] = [
                        {
                            "year": y.get("year"),
                            "revenue": safe_float(y.get("revenue")),
                            "earnings": safe_float(y.get("earnings")),
                        }
                        for y in yearly if y.get("year")
                    ]
            except Exception:
                pass

        return result

    except HTTPException:
        raise
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

        from reportlab.lib.pagesizes import letter
        from reportlab.lib.units import inch, cm
        from reportlab.lib import colors
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
            PageBreak, HRFlowable, KeepTogether
        )
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

        buf = io.BytesIO()
        doc = SimpleDocTemplate(
            buf, pagesize=letter,
            topMargin=0.6 * inch, bottomMargin=0.6 * inch,
            leftMargin=0.7 * inch, rightMargin=0.7 * inch,
        )

        # ── Color palette ──
        DARK = colors.HexColor('#1a1a2e')
        DARK2 = colors.HexColor('#16213e')
        ACCENT = colors.HexColor('#0f3460')
        GREEN = colors.HexColor('#00a86b')
        RED = colors.HexColor('#e63946')
        YELLOW = colors.HexColor('#d4a017')
        BLUE = colors.HexColor('#3b82f6')
        GRAY = colors.HexColor('#6b7280')
        LIGHT_GRAY = colors.HexColor('#f3f4f6')
        WHITE = colors.white
        BORDER = colors.HexColor('#d1d5db')

        # ── Styles ──
        styles = getSampleStyleSheet()
        s_title = ParagraphStyle('PDFTitle', parent=styles['Title'], fontSize=22, textColor=DARK, spaceAfter=4, fontName='Helvetica-Bold')
        s_subtitle = ParagraphStyle('PDFSubtitle', parent=styles['Normal'], fontSize=10, textColor=GRAY, spaceAfter=2)
        s_h1 = ParagraphStyle('PDFH1', parent=styles['Heading1'], fontSize=16, textColor=DARK, spaceBefore=16, spaceAfter=6, fontName='Helvetica-Bold')
        s_h2 = ParagraphStyle('PDFH2', parent=styles['Heading2'], fontSize=13, textColor=ACCENT, spaceBefore=12, spaceAfter=4, fontName='Helvetica-Bold')
        s_h3 = ParagraphStyle('PDFH3', parent=styles['Heading3'], fontSize=11, textColor=DARK2, spaceBefore=8, spaceAfter=3, fontName='Helvetica-Bold')
        s_body = ParagraphStyle('PDFBody', parent=styles['Normal'], fontSize=9.5, textColor=colors.HexColor('#374151'), leading=13)
        s_small = ParagraphStyle('PDFSmall', parent=styles['Normal'], fontSize=8, textColor=GRAY, leading=10)
        s_score = ParagraphStyle('PDFScore', parent=styles['Normal'], fontSize=36, textColor=DARK, fontName='Helvetica-Bold', alignment=TA_CENTER)
        s_verdict = ParagraphStyle('PDFVerdict', parent=styles['Normal'], fontSize=14, fontName='Helvetica-Bold', alignment=TA_CENTER)
        s_footer = ParagraphStyle('PDFFooter', parent=styles['Normal'], fontSize=7.5, textColor=GRAY, alignment=TA_CENTER)

        story = []
        profile = analysis.get("profile", {})
        km = analysis.get("key_metrics", {})
        price = analysis.get("price")
        score = analysis.get("score")
        dcf_data = analysis.get("dcf")
        graham = analysis.get("graham_number")
        altman = analysis.get("altman_z")
        piotroski = analysis.get("piotroski_f")
        alerts = analysis.get("alerts", {})
        sensitivity = analysis.get("sensitivity")
        yearly = analysis.get("yearly_financials", [])
        company_type = analysis.get("company_type", "balanced")

        # ── Helper formatters ──
        def fv(val, fmt="num"):
            if val is None: return "N/A"
            try:
                v = float(val)
                if fmt == "pct":
                    return f"{v * 100:.2f}%" if abs(v) < 5 else f"{v:.2f}%"
                if fmt == "mult": return f"{v:.2f}x"
                if fmt == "price": return f"${v:,.2f}"
                if fmt == "money":
                    if abs(v) >= 1e12: return f"${v / 1e12:.2f}T"
                    if abs(v) >= 1e9: return f"${v / 1e9:.2f}B"
                    if abs(v) >= 1e6: return f"${v / 1e6:.2f}M"
                    return f"${v:,.0f}"
                return f"{v:,.2f}"
            except (TypeError, ValueError):
                return "N/A"

        def score_color(pct):
            if pct >= 75: return GREEN
            if pct >= 50: return YELLOW
            return RED

        def make_section_table(data_rows, col_widths=None, header=True):
            """Create a styled metrics table."""
            if not col_widths:
                col_widths = [2.8 * inch, 1.5 * inch, 2.8 * inch, 1.5 * inch]
            t = Table(data_rows, colWidths=col_widths)
            style_cmds = [
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#374151')),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ('LINEBELOW', (0, 0), (-1, -2), 0.5, colors.HexColor('#e5e7eb')),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica-Bold'),
            ]
            if len(data_rows[0]) > 2:
                style_cmds.append(('ALIGN', (3, 0), (3, -1), 'RIGHT'))
                style_cmds.append(('FONTNAME', (3, 0), (3, -1), 'Helvetica-Bold'))
            if header:
                style_cmds.extend([
                    ('BACKGROUND', (0, 0), (-1, 0), DARK),
                    ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 8.5),
                ])
            style_cmds.append(('ROWBACKGROUNDS', (0, 1 if header else 0), (-1, -1), [WHITE, LIGHT_GRAY]))
            t.setStyle(TableStyle(style_cmds))
            return t

        def make_2col_table(rows, widths=None):
            """Two-column metric: label | value"""
            if not widths:
                widths = [4.5 * inch, 2.5 * inch]
            t = Table(rows, colWidths=widths)
            t.setStyle(TableStyle([
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#374151')),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ('LINEBELOW', (0, 0), (-1, -2), 0.5, colors.HexColor('#e5e7eb')),
                ('ROWBACKGROUNDS', (0, 0), (-1, -1), [WHITE, LIGHT_GRAY]),
            ]))
            return t

        # ══════════════════════════════════════════════════════════
        # PAGE 1: COVER — Company header + Score + Key Metrics
        # ══════════════════════════════════════════════════════════

        # Header bar
        header_data = [[
            Paragraph(f"<b>FINANZER</b>", ParagraphStyle('hdr', fontSize=10, textColor=WHITE, fontName='Helvetica-Bold')),
            Paragraph(f"Informe Financiero Completo", ParagraphStyle('hdr2', fontSize=9, textColor=colors.HexColor('#94a3b8'), alignment=TA_RIGHT)),
        ]]
        ht = Table(header_data, colWidths=[3.5 * inch, 3.5 * inch])
        ht.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), DARK),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 12),
            ('RIGHTPADDING', (0, 0), (-1, -1), 12),
            ('ROUNDEDCORNERS', [6, 6, 0, 0]),
        ]))
        story.append(ht)
        story.append(Spacer(1, 16))

        # Company name + info
        story.append(Paragraph(profile.get("name", symbol), s_title))
        story.append(Paragraph(
            f"{symbol}  ·  {profile.get('sector', 'N/A')}  ·  {profile.get('industry', 'N/A')}  ·  {profile.get('country', '')}",
            s_subtitle
        ))
        story.append(Paragraph(f"Fecha del informe: {datetime.now().strftime('%d %B %Y')}", s_small))
        story.append(Spacer(1, 6))
        story.append(HRFlowable(width="100%", thickness=1, color=BORDER))
        story.append(Spacer(1, 12))

        # Price + Market Cap row
        price_data = [[
            Paragraph(f"<b>Precio actual</b>", ParagraphStyle('pl', fontSize=9, textColor=GRAY)),
            Paragraph(f"<b>Market Cap</b>", ParagraphStyle('pl', fontSize=9, textColor=GRAY)),
            Paragraph(f"<b>Beta</b>", ParagraphStyle('pl', fontSize=9, textColor=GRAY)),
            Paragraph(f"<b>Tipo</b>", ParagraphStyle('pl', fontSize=9, textColor=GRAY)),
        ], [
            Paragraph(fv(price, "price"), ParagraphStyle('pv', fontSize=14, fontName='Helvetica-Bold', textColor=DARK)),
            Paragraph(fv(km.get("market_cap"), "money"), ParagraphStyle('pv', fontSize=14, fontName='Helvetica-Bold', textColor=DARK)),
            Paragraph(fv(km.get("beta")), ParagraphStyle('pv', fontSize=14, fontName='Helvetica-Bold', textColor=DARK)),
            Paragraph(company_type.replace("_", " ").title(), ParagraphStyle('pv', fontSize=12, fontName='Helvetica-Bold', textColor=BLUE)),
        ]]
        pt = Table(price_data, colWidths=[1.75 * inch] * 4)
        pt.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BACKGROUND', (0, 0), (-1, -1), LIGHT_GRAY),
            ('LINEBELOW', (0, 0), (-1, 0), 0.5, BORDER),
        ]))
        story.append(pt)
        story.append(Spacer(1, 16))

        # ── SCORE CARD ──
        if score:
            total = score.get("total_score", 0)
            max_s = score.get("max_score", 100)
            pct = (total / max_s * 100) if max_s > 0 else 0
            sc = score_color(pct)
            level = score.get("level", "N/A")

            story.append(Paragraph("PUNTUACIÓN FINANZER", s_h1))
            score_row = [[
                Paragraph(f"<font size='36' color='{sc.hexval()}'><b>{total}</b></font><font size='14' color='#9ca3af'>/{max_s}</font>",
                          ParagraphStyle('sc', alignment=TA_CENTER, leading=42)),
                Paragraph(f"<font size='14' color='{sc.hexval()}'><b>{level}</b></font><br/>"
                          f"<font size='9' color='#6b7280'>Puntuación global basada en valoración,<br/>rentabilidad, solidez financiera,<br/>crecimiento y estabilidad.</font>",
                          ParagraphStyle('sl', alignment=TA_LEFT, leading=13)),
            ]]
            st = Table(score_row, colWidths=[2.5 * inch, 4.5 * inch])
            st.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 12),
                ('BACKGROUND', (0, 0), (-1, -1), LIGHT_GRAY),
                ('ROUNDEDCORNERS', [8, 8, 8, 8]),
            ]))
            story.append(st)
            story.append(Spacer(1, 8))

            # Score breakdown
            breakdown = score.get("breakdown", {})
            if breakdown:
                bd_rows = [["Categoría", "Puntos", "Máximo", "% Logrado"]]
                for cat_name, cat_data in breakdown.items():
                    cs = cat_data.get("score", 0)
                    cm = cat_data.get("max", 20)
                    cp = f"{(cs / cm * 100):.0f}%" if cm > 0 else "N/A"
                    bd_rows.append([cat_name.replace("_", " ").title(), str(cs), str(cm), cp])
                bd_rows.append(["TOTAL", str(total), str(max_s), f"{pct:.0f}%"])

                bt = Table(bd_rows, colWidths=[3 * inch, 1.3 * inch, 1.3 * inch, 1.4 * inch])
                bt.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), DARK),
                    ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                    ('TOPPADDING', (0, 0), (-1, -1), 6),
                    ('LEFTPADDING', (0, 0), (-1, -1), 8),
                    ('LINEBELOW', (0, 0), (-1, -2), 0.5, colors.HexColor('#e5e7eb')),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -2), [WHITE, LIGHT_GRAY]),
                    ('BACKGROUND', (0, -1), (-1, -1), DARK2),
                    ('TEXTCOLOR', (0, -1), (-1, -1), WHITE),
                    ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ]))
                story.append(bt)
            story.append(Spacer(1, 8))

        # ── 8 KEY METRICS ──
        story.append(Paragraph("MÉTRICAS CLAVE", s_h1))
        key_data = [
            ["Métrica", "Valor", "Métrica", "Valor"],
            ["Market Cap", fv(km.get("market_cap"), "money"), "P/E (TTM)", fv(km.get("pe"), "mult")],
            ["ROE", fv(km.get("roe"), "pct"), "D/E", fv(km.get("de"), "mult")],
            ["Margen Neto", fv(km.get("net_margin"), "pct"), "FCF Yield", fv(km.get("fcf_yield"), "pct")],
            ["EV/EBITDA", fv(km.get("ev_ebitda"), "mult"), "Beta", fv(km.get("beta"))],
        ]
        story.append(make_section_table(key_data))

        # ══════════════════════════════════════════════════════════
        # PAGE 2: VALORACIÓN
        # ══════════════════════════════════════════════════════════
        story.append(PageBreak())
        story.append(Paragraph("1. VALORACIÓN", s_h1))
        story.append(Paragraph("Múltiplos de precio y valoración relativa.", s_small))
        story.append(Spacer(1, 6))

        val_rows = [
            ["P/E (TTM)", fv(km.get("pe"), "mult")],
            ["Forward P/E", fv(km.get("forward_pe"), "mult")],
            ["P/B (Precio / Valor en Libros)", fv(km.get("pb"), "mult")],
            ["P/S (Precio / Ventas)", fv(km.get("ps"), "mult")],
            ["PEG Ratio", fv(km.get("peg"), "mult")],
            ["EV/EBITDA", fv(km.get("ev_ebitda"), "mult")],
            ["EV/Revenue", fv(km.get("ev_revenue"), "mult")],
            ["P/FCF", fv(km.get("pfcf"), "mult")],
            ["FCF Yield", fv(km.get("fcf_yield"), "pct")],
            ["Earnings Yield", fv(km.get("earnings_yield"), "pct")],
            ["Dividend Yield", fv(km.get("dividend_yield"), "pct")],
        ]
        story.append(make_2col_table(val_rows))

        # ── VALOR INTRÍNSECO ──
        story.append(Spacer(1, 12))
        story.append(Paragraph("Valor Intrínseco", s_h2))

        # Verdict
        verdict = "Precio justo"
        v_color = YELLOW
        if dcf_data and dcf_data.get("fair_value") and price:
            upside = ((dcf_data["fair_value"] - price) / price) * 100
            if upside > 15:
                verdict = "Subvalorada"
                v_color = GREEN
            elif upside < -15:
                verdict = "Sobrevalorada"
                v_color = RED

        intrinsic_rows = [["Concepto", "Valor"]]
        intrinsic_rows.append(["Precio de Mercado", fv(price, "price")])
        intrinsic_rows.append(["Valor Graham", fv(graham, "price")])
        if dcf_data:
            intrinsic_rows.append(["Valor DCF (Fair Value)", fv(dcf_data.get("fair_value"), "price")])
            intrinsic_rows.append(["Upside DCF", fv(dcf_data.get("upside"), "pct") if dcf_data.get("upside") is not None else "N/A"])
            intrinsic_rows.append(["Margen de Seguridad (25%)", fv(dcf_data.get("margin_of_safety"), "price")])
        intrinsic_rows.append([Paragraph(f"<b>Veredicto: {verdict}</b>",
                               ParagraphStyle('vd', fontSize=10, textColor=v_color, fontName='Helvetica-Bold')), ""])

        it = Table(intrinsic_rows, colWidths=[4.5 * inch, 2.5 * inch])
        it.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), DARK),
            ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (1, 1), (1, -1), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('LINEBELOW', (0, 0), (-1, -2), 0.5, colors.HexColor('#e5e7eb')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [WHITE, LIGHT_GRAY]),
        ]))
        story.append(it)

        # DCF Parameters
        if dcf_data:
            story.append(Spacer(1, 8))
            story.append(Paragraph("Parámetros DCF", s_h3))
            dcf_params = [
                ["WACC (Tasa de descuento)", f"{dcf_data.get('wacc', 0) * 100:.1f}%" if dcf_data.get('wacc') else "N/A"],
                ["Tasa de Crecimiento", f"{dcf_data.get('growth_rate', 0) * 100:.1f}%" if dcf_data.get('growth_rate') else "N/A"],
                ["Crecimiento Terminal", f"{dcf_data.get('terminal_growth', 0) * 100:.1f}%" if dcf_data.get('terminal_growth') else "N/A"],
            ]
            story.append(make_2col_table(dcf_params))

        # Sensitivity Table
        if sensitivity and sensitivity.get("matrix"):
            story.append(Spacer(1, 10))
            story.append(Paragraph("Análisis de Sensibilidad DCF", s_h3))
            story.append(Paragraph("Valor justo estimado bajo diferentes escenarios de crecimiento (filas) y tasa de descuento (columnas).", s_small))
            story.append(Spacer(1, 4))

            matrix = sensitivity["matrix"]
            g_rates = sensitivity.get("growth_rates", [])
            d_rates = sensitivity.get("discount_rates", [])
            base_gi = sensitivity.get("base_growth_idx")
            base_di = sensitivity.get("base_discount_idx")

            # Build table
            sens_header = ["Crec \\ WACC"] + [f"{dr * 100:.1f}%" for dr in d_rates]
            sens_rows = [sens_header]
            for gi, row in enumerate(matrix):
                r = [f"{g_rates[gi] * 100:.1f}%"]
                for di, val in enumerate(row):
                    r.append(f"${val:.0f}")
                sens_rows.append(r)

            n_cols = len(sens_header)
            cw = [1.2 * inch] + [(5.8 * inch / (n_cols - 1))] * (n_cols - 1) if n_cols > 1 else [7 * inch]
            sens_t = Table(sens_rows, colWidths=cw)
            sens_style = [
                ('BACKGROUND', (0, 0), (-1, 0), DARK),
                ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
                ('BACKGROUND', (0, 1), (0, -1), DARK2),
                ('TEXTCOLOR', (0, 1), (0, -1), WHITE),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 7.5),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d1d5db')),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
            ]
            # Color-code cells based on price
            if price:
                for gi in range(len(matrix)):
                    for di in range(len(matrix[gi])):
                        val = matrix[gi][di]
                        diff = ((val - price) / price) * 100
                        if diff > 30:
                            bg = colors.HexColor('#dcfce7')  # strong green
                        elif diff > 10:
                            bg = colors.HexColor('#ecfdf5')  # light green
                        elif diff > -10:
                            bg = colors.HexColor('#fefce8')  # yellow
                        elif diff > -30:
                            bg = colors.HexColor('#fef2f2')  # light red
                        else:
                            bg = colors.HexColor('#fecaca')  # strong red
                        sens_style.append(('BACKGROUND', (di + 1, gi + 1), (di + 1, gi + 1), bg))
            # Highlight base case
            if base_gi is not None and base_di is not None:
                sens_style.append(('BOX', (base_di + 1, base_gi + 1), (base_di + 1, base_gi + 1), 2, GREEN))

            sens_t.setStyle(TableStyle(sens_style))
            story.append(sens_t)
            if price:
                story.append(Paragraph(f"Precio actual: ${price:.2f} — Verde = subvalorada, Amarillo = precio justo, Rojo = sobrevalorada", s_small))

        # ══════════════════════════════════════════════════════════
        # PAGE 3: RENTABILIDAD + SOLIDEZ FINANCIERA
        # ══════════════════════════════════════════════════════════
        story.append(PageBreak())
        story.append(Paragraph("2. RENTABILIDAD", s_h1))
        story.append(Paragraph("Retornos sobre capital y márgenes operativos.", s_small))
        story.append(Spacer(1, 6))

        profit_rows = [
            ["Return on Equity (ROE)", fv(km.get("roe"), "pct")],
            ["Return on Assets (ROA)", fv(km.get("roa"), "pct")],
            ["Return on Invested Capital (ROIC)", fv(km.get("roic"), "pct")],
            ["Earnings Per Share (EPS)", fv(km.get("eps"), "price")],
            ["Margen Bruto", fv(km.get("gross_margin"), "pct")],
            ["Margen Operativo", fv(km.get("operating_margin"), "pct")],
            ["Margen EBITDA", fv(km.get("ebitda_margin"), "pct")],
            ["Margen Neto", fv(km.get("net_margin"), "pct")],
        ]
        story.append(make_2col_table(profit_rows))

        # Income statement summary
        story.append(Spacer(1, 8))
        story.append(Paragraph("Estado de Resultados (resumen)", s_h3))
        income_rows = [
            ["Revenue (Ingresos)", fv(km.get("revenue"), "money")],
            ["Operating Income", fv(km.get("operating_income"), "money")],
            ["EBITDA", fv(km.get("ebitda"), "money")],
            ["Net Income (Utilidad Neta)", fv(km.get("net_income"), "money")],
            ["Free Cash Flow", fv(km.get("free_cash_flow"), "money")],
            ["Operating Cash Flow", fv(km.get("operating_cash_flow"), "money")],
        ]
        story.append(make_2col_table(income_rows))

        # ── SOLIDEZ FINANCIERA ──
        story.append(Spacer(1, 14))
        story.append(Paragraph("3. SOLIDEZ FINANCIERA", s_h1))
        story.append(Paragraph("Liquidez, apalancamiento y cobertura de la empresa.", s_small))
        story.append(Spacer(1, 6))

        story.append(Paragraph("Liquidez", s_h3))
        liq_rows = [
            ["Current Ratio", fv(km.get("current_ratio"), "mult")],
            ["Quick Ratio", fv(km.get("quick_ratio"), "mult")],
            ["Efectivo y Equivalentes", fv(km.get("cash"), "money")],
            ["Free Cash Flow", fv(km.get("free_cash_flow"), "money")],
        ]
        story.append(make_2col_table(liq_rows))

        story.append(Spacer(1, 6))
        story.append(Paragraph("Apalancamiento", s_h3))
        lev_rows = [
            ["Deuda / Equity (D/E)", fv(km.get("de"), "mult")],
            ["Deuda / Activos", fv(km.get("debt_to_assets"), "pct")],
            ["Deuda Total", fv(km.get("total_debt"), "money")],
            ["Total Equity", fv(km.get("total_equity"), "money")],
            ["Total Assets", fv(km.get("total_assets"), "money")],
        ]
        story.append(make_2col_table(lev_rows))

        story.append(Spacer(1, 6))
        story.append(Paragraph("Cobertura y Distribución", s_h3))
        cov_rows = [
            ["Cobertura de Intereses", fv(km.get("interest_coverage"), "mult")],
            ["Gasto por Intereses", fv(km.get("interest_expense"), "money")],
            ["Dividend Yield", fv(km.get("dividend_yield"), "pct")],
            ["Payout Ratio", fv(km.get("payout_ratio"), "pct")],
        ]
        story.append(make_2col_table(cov_rows))

        # ══════════════════════════════════════════════════════════
        # PAGE 4: CRECIMIENTO + COMPARATIVA SECTORIAL
        # ══════════════════════════════════════════════════════════
        story.append(PageBreak())
        story.append(Paragraph("4. CRECIMIENTO", s_h1))
        story.append(Paragraph("Tasas de crecimiento y datos por acción.", s_small))
        story.append(Spacer(1, 6))

        growth_rows = [
            ["Crecimiento Revenue (YoY)", fv(km.get("revenue_growth"), "pct")],
            ["Crecimiento Earnings", fv(km.get("earnings_growth"), "pct")],
            ["EPS", fv(km.get("eps"), "price")],
            ["Book Value / Share", fv(km.get("book_value_per_share"), "price")],
            ["Acciones en Circulación", fv(km.get("shares_outstanding"), "money")],
        ]
        story.append(make_2col_table(growth_rows))

        # Price range
        story.append(Spacer(1, 6))
        story.append(Paragraph("Rango de Precio 52 Semanas", s_h3))
        h52 = km.get("price_52w_high")
        l52 = km.get("price_52w_low")
        range_rows = [
            ["Mínimo 52 semanas", fv(l52, "price")],
            ["Máximo 52 semanas", fv(h52, "price")],
            ["Precio actual", fv(price, "price")],
        ]
        if h52 and l52 and price and (h52 - l52) > 0:
            pos_pct = ((price - l52) / (h52 - l52)) * 100
            range_rows.append(["Posición en rango", f"{pos_pct:.0f}%"])
        story.append(make_2col_table(range_rows))

        # Yearly financials
        if yearly and len(yearly) > 0:
            story.append(Spacer(1, 10))
            story.append(Paragraph("Evolución Histórica (Anual)", s_h3))
            yf_header = ["Año", "Revenue", "Earnings", "Crec. Revenue"]
            yf_rows = [yf_header]
            sorted_yearly = sorted(yearly, key=lambda x: x.get("year", 0))
            for i, y in enumerate(sorted_yearly):
                rev = y.get("revenue")
                earn = y.get("earnings")
                rev_g = ""
                if i > 0 and rev and sorted_yearly[i - 1].get("revenue"):
                    prev_rev = sorted_yearly[i - 1]["revenue"]
                    if prev_rev and prev_rev != 0:
                        rev_g = f"{((rev - prev_rev) / abs(prev_rev)) * 100:.1f}%"
                yf_rows.append([
                    str(y.get("year", "")),
                    fv(rev, "money"),
                    fv(earn, "money"),
                    rev_g or "—",
                ])
            yt = Table(yf_rows, colWidths=[1.2 * inch, 2 * inch, 2 * inch, 1.8 * inch])
            yt.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), DARK),
                ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('LINEBELOW', (0, 0), (-1, -2), 0.5, colors.HexColor('#e5e7eb')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, LIGHT_GRAY]),
            ]))
            story.append(yt)

        # ── COMPARATIVA SECTORIAL ──
        story.append(Spacer(1, 14))
        story.append(Paragraph("5. COMPARATIVA SECTORIAL", s_h1))
        sector_name = analysis.get("sector_info", {}).get("sector", profile.get("sector", "N/A"))
        mapped = analysis.get("sector_info", {}).get("mapped_sector", "default")
        story.append(Paragraph(f"Comparación de {profile.get('name', symbol)} vs promedio del sector: {sector_name}", s_small))
        story.append(Spacer(1, 6))

        # Get sector benchmarks (same logic as frontend)
        sector_benchmarks = _get_sector_benchmarks(mapped)

        comp_sections = [
            ("Valoración (menor es mejor)", [
                ("P/E", km.get("pe"), sector_benchmarks.get("pe"), False),
                ("Forward P/E", km.get("forward_pe"), sector_benchmarks.get("forward_pe"), False),
                ("P/B", km.get("pb"), sector_benchmarks.get("pb"), False),
                ("EV/EBITDA", km.get("ev_ebitda"), sector_benchmarks.get("ev_ebitda"), False),
                ("P/FCF", km.get("pfcf"), sector_benchmarks.get("pfcf"), False),
                ("PEG", km.get("peg"), sector_benchmarks.get("peg"), False),
            ]),
            ("Rentabilidad (mayor es mejor)", [
                ("ROE", km.get("roe"), sector_benchmarks.get("roe"), True),
                ("ROA", km.get("roa"), sector_benchmarks.get("roa"), True),
                ("ROIC", km.get("roic"), sector_benchmarks.get("roic"), True),
                ("Margen Neto", km.get("net_margin"), sector_benchmarks.get("net_margin"), True),
                ("Margen Operativo", km.get("operating_margin"), sector_benchmarks.get("operating_margin"), True),
                ("Margen Bruto", km.get("gross_margin"), sector_benchmarks.get("gross_margin"), True),
            ]),
            ("Solidez Financiera", [
                ("Current Ratio", km.get("current_ratio"), sector_benchmarks.get("current_ratio"), True),
                ("D/E", km.get("de"), sector_benchmarks.get("de"), False),
                ("Cobertura Intereses", km.get("interest_coverage"), sector_benchmarks.get("interest_coverage"), True),
                ("FCF Yield", km.get("fcf_yield"), sector_benchmarks.get("fcf_yield"), True),
            ]),
        ]

        for section_title, metrics in comp_sections:
            story.append(Paragraph(section_title, s_h3))
            comp_rows = [["Métrica", "Empresa", "Sector", "Relativo"]]
            for label, val, sect_avg, higher_better in metrics:
                # D/E is a ratio conventionally shown as a multiple (0.80x); the
                # magnitude heuristic below would mis-format a sub-1.0 D/E as "80%".
                if label == "D/E":
                    fmt = "mult"
                else:
                    fmt = "pct" if isinstance(sect_avg, float) and abs(sect_avg) < 1 else "mult"
                v_str = fv(val, fmt)
                s_str = fv(sect_avg, fmt)
                rel = "—"
                if val is not None and sect_avg is not None and sect_avg != 0:
                    diff = ((val - sect_avg) / abs(sect_avg)) * 100
                    rel = f"{'+' if diff > 0 else ''}{diff:.0f}%"
                comp_rows.append([label, v_str, s_str, rel])

            ct = Table(comp_rows, colWidths=[2.2 * inch, 1.5 * inch, 1.5 * inch, 1.8 * inch])
            ct.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), DARK),
                ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8.5),
                ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
                ('FONTNAME', (1, 1), (1, -1), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ('LINEBELOW', (0, 0), (-1, -2), 0.5, colors.HexColor('#e5e7eb')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, LIGHT_GRAY]),
            ]))
            # Color-code the "Relativo" column
            for i in range(1, len(comp_rows)):
                label, val, sect_avg, higher_better = metrics[i - 1]
                if val is not None and sect_avg is not None and sect_avg != 0:
                    diff = ((val - sect_avg) / abs(sect_avg)) * 100
                    is_better = (higher_better and diff > 5) or (not higher_better and diff < -5)
                    is_worse = (higher_better and diff < -5) or (not higher_better and diff > 5)
                    tc = GREEN if is_better else RED if is_worse else YELLOW
                    ct.setStyle(TableStyle([('TEXTCOLOR', (3, i), (3, i), tc), ('FONTNAME', (3, i), (3, i), 'Helvetica-Bold')]))

            story.append(ct)
            story.append(Spacer(1, 6))

        # ══════════════════════════════════════════════════════════
        # PAGE 5: EVALUACIÓN INSTITUCIONAL + ALERTAS
        # ══════════════════════════════════════════════════════════
        story.append(PageBreak())
        story.append(Paragraph("6. EVALUACIÓN INSTITUCIONAL", s_h1))

        # Altman Z-Score
        if altman:
            z_val = altman.get("z_score", 0)
            z_zone = altman.get("zone", "grey")
            z_interp = altman.get("interpretation", "")
            z_color = GREEN if z_zone == "safe" else YELLOW if z_zone == "grey" else RED
            z_label = "Zona Segura (Z > 2.99)" if z_zone == "safe" else "Zona Gris (1.81 < Z < 2.99)" if z_zone == "grey" else "Zona de Riesgo (Z < 1.81)"

            story.append(Paragraph("Altman Z-Score", s_h2))
            z_rows = [[
                Paragraph(f"<font size='28' color='{z_color.hexval()}'><b>{z_val:.2f}</b></font>",
                          ParagraphStyle('zs', alignment=TA_CENTER, leading=34)),
                Paragraph(f"<font size='11' color='{z_color.hexval()}'><b>{z_label}</b></font><br/><br/>"
                          f"<font size='8.5' color='#6b7280'>{z_interp}</font><br/><br/>"
                          f"<font size='8' color='#9ca3af'>El Z-Score de Altman mide la probabilidad de bancarrota de una empresa "
                          f"usando 5 ratios financieros ponderados. Un valor mayor a 2.99 indica solidez financiera.</font>",
                          ParagraphStyle('zi', alignment=TA_LEFT, leading=12)),
            ]]
            zt = Table(z_rows, colWidths=[2 * inch, 5 * inch])
            zt.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
                ('BACKGROUND', (0, 0), (-1, -1), LIGHT_GRAY),
                ('ROUNDEDCORNERS', [6, 6, 6, 6]),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                ('TOPPADDING', (0, 0), (-1, -1), 10),
            ]))
            story.append(zt)
            story.append(Spacer(1, 10))

        # Piotroski F-Score
        if piotroski:
            f_score = piotroski.get("score", 0)
            f_max = piotroski.get("max_score", 9)
            f_level = piotroski.get("level", "N/A")
            f_interp = piotroski.get("interpretation", "")
            f_color = GREEN if f_score >= 7 else YELLOW if f_score >= 4 else RED

            story.append(Paragraph("Piotroski F-Score", s_h2))
            f_header = [[
                Paragraph(f"<font size='28' color='{f_color.hexval()}'><b>{f_score}</b></font>"
                          f"<font size='12' color='#9ca3af'>/{f_max}</font>",
                          ParagraphStyle('fs', alignment=TA_CENTER, leading=34)),
                Paragraph(f"<font size='11' color='{f_color.hexval()}'><b>{f_level}</b></font><br/><br/>"
                          f"<font size='8.5' color='#6b7280'>{f_interp}</font><br/><br/>"
                          f"<font size='8' color='#9ca3af'>El F-Score de Piotroski evalúa 9 criterios de fortaleza financiera: "
                          f"rentabilidad, apalancamiento, liquidez y eficiencia operativa.</font>",
                          ParagraphStyle('fi', alignment=TA_LEFT, leading=12)),
            ]]
            ft = Table(f_header, colWidths=[2 * inch, 5 * inch])
            ft.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
                ('BACKGROUND', (0, 0), (-1, -1), LIGHT_GRAY),
                ('ROUNDEDCORNERS', [6, 6, 6, 6]),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                ('TOPPADDING', (0, 0), (-1, -1), 10),
            ]))
            story.append(ft)

            # F-Score criteria details
            f_details = piotroski.get("details", {})
            if f_details:
                story.append(Spacer(1, 6))
                fd_rows = [["Criterio", "Estado", "Detalle"]]
                for key, criterion in f_details.items():
                    passed = criterion.get("passed", False)
                    status = "PASA" if passed else "FALLA"
                    detail = criterion.get("detail", key)
                    fd_rows.append([key.replace("_", " ").title(), status, detail[:60]])

                fdt = Table(fd_rows, colWidths=[2 * inch, 1 * inch, 4 * inch])
                fdt.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), DARK),
                    ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 8),
                    ('ALIGN', (1, 0), (1, -1), 'CENTER'),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                    ('TOPPADDING', (0, 0), (-1, -1), 4),
                    ('LEFTPADDING', (0, 0), (-1, -1), 6),
                    ('LINEBELOW', (0, 0), (-1, -2), 0.5, colors.HexColor('#e5e7eb')),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, LIGHT_GRAY]),
                ]))
                # Color "PASA" / "FALLA"
                for i in range(1, len(fd_rows)):
                    tc = GREEN if fd_rows[i][1] == "PASA" else RED
                    fdt.setStyle(TableStyle([
                        ('TEXTCOLOR', (1, i), (1, i), tc),
                        ('FONTNAME', (1, i), (1, i), 'Helvetica-Bold'),
                    ]))
                story.append(fdt)

        # ── Score detailed breakdown with adjustments ──
        if score and score.get("breakdown"):
            story.append(Spacer(1, 14))
            story.append(Paragraph("Desglose del Score por Categoría", s_h2))

            for cat_name, cat_data in score["breakdown"].items():
                cs = cat_data.get("score", 0)
                cm = cat_data.get("max", 20)
                cp = f"{(cs / cm * 100):.0f}%" if cm > 0 else "N/A"
                sc_col = score_color((cs / cm * 100) if cm > 0 else 0)

                story.append(Paragraph(
                    f"<font color='{sc_col.hexval()}'><b>{cat_name.replace('_', ' ').title()}</b></font>"
                    f"  —  {cs}/{cm} pts ({cp})",
                    ParagraphStyle('cathead', fontSize=10, spaceBefore=8, spaceAfter=2, fontName='Helvetica-Bold', textColor=DARK)
                ))

                adjs = cat_data.get("adjustments", [])
                if adjs:
                    for adj in adjs:
                        metric = adj.get("metric", "")
                        reason = adj.get("reason", "")
                        adjustment = adj.get("adjustment", 0)
                        severity = adj.get("severity", "")
                        value_str = adj.get("value", "")

                        sev_color = GREEN if severity in ("excellent", "good") else RED if severity in ("severe", "critical") else YELLOW
                        sign = f"+{adjustment}" if adjustment > 0 else str(adjustment)

                        story.append(Paragraph(
                            f"<font color='{sev_color.hexval()}'><b>[{sign}]</b></font> "
                            f"<b>{metric}</b> {('(' + value_str + ')') if value_str else ''} — {reason}",
                            ParagraphStyle('adj', fontSize=8, textColor=colors.HexColor('#4b5563'), leading=11, leftIndent=12)
                        ))

        # ── ALERTAS ──
        story.append(Spacer(1, 14))
        story.append(Paragraph("7. ALERTAS Y SEÑALES", s_h1))

        red_flags = alerts.get("red_flags", [])
        warnings_list = alerts.get("warnings", [])
        strengths_list = alerts.get("strengths", [])

        # Summary
        story.append(Paragraph(
            f"<font color='#e63946'><b>{len(red_flags)} Riesgos</b></font>  ·  "
            f"<font color='#d4a017'><b>{len(warnings_list)} Advertencias</b></font>  ·  "
            f"<font color='#00a86b'><b>{len(strengths_list)} Fortalezas</b></font>",
            ParagraphStyle('alertsum', fontSize=11, spaceBefore=4, spaceAfter=8)
        ))

        def render_alerts(title, items, color):
            if not items:
                return
            story.append(Paragraph(f"<font color='{color.hexval()}'><b>{title}</b></font>",
                                   ParagraphStyle('at', fontSize=10, spaceBefore=6, spaceAfter=3)))
            for a in items:
                cat = a.get("category", "")
                reason = a.get("reason", "")
                detail = a.get("detail", "")
                story.append(Paragraph(
                    f"<font color='{color.hexval()}'>●</font> <b>{cat}: {reason}</b>",
                    ParagraphStyle('ar', fontSize=9, textColor=DARK, leftIndent=8, leading=12)
                ))
                if detail and detail != reason:
                    story.append(Paragraph(
                        detail,
                        ParagraphStyle('ad', fontSize=8, textColor=GRAY, leftIndent=18, leading=10, spaceAfter=2)
                    ))

        render_alerts("Riesgos", red_flags, RED)
        render_alerts("Advertencias", warnings_list, YELLOW)
        render_alerts("Fortalezas", strengths_list, GREEN)

        if not red_flags and not warnings_list and not strengths_list:
            story.append(Paragraph("No se detectaron alertas significativas.", s_body))

        # ══════════════════════════════════════════════════════════
        # FOOTER
        # ══════════════════════════════════════════════════════════
        story.append(Spacer(1, 30))
        story.append(HRFlowable(width="100%", thickness=1, color=BORDER))
        story.append(Spacer(1, 8))
        story.append(Paragraph(
            f"Informe generado por <b>Finanzer</b> · {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            s_footer
        ))
        story.append(Paragraph(
            "Este informe es de carácter informativo y educativo. No constituye asesoría financiera, "
            "recomendación de inversión ni oferta de compra/venta de valores. Los datos provienen de fuentes "
            "públicas y pueden contener inexactitudes. Consulte a un asesor financiero profesional antes de "
            "tomar decisiones de inversión.",
            ParagraphStyle('disclaimer', fontSize=7, textColor=GRAY, alignment=TA_CENTER, leading=9, spaceBefore=4)
        ))

        doc.build(story)
        buf.seek(0)

        return StreamingResponse(
            buf,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=Finanzer_{symbol}_{datetime.now().strftime('%Y%m%d')}.pdf"}
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
        # Try the exact path first
        stock_index = os.path.join(_frontend_dir, "stock", "index.html")
        if os.path.isfile(stock_index):
            return FileResponse(stock_index, media_type="text/html")
        # Fallback to root index
        index_path = os.path.join(_frontend_dir, "index.html")
        return FileResponse(index_path, media_type="text/html")

    # Serve other static files (favicon, svgs, etc.)
    @app.get("/{filepath:path}")
    async def serve_static(filepath: str):
        # Try exact file
        full_path = os.path.join(_frontend_dir, filepath)
        if os.path.isfile(full_path):
            return FileResponse(full_path)
        # Try with index.html (for directory paths)
        index_path = os.path.join(full_path, "index.html")
        if os.path.isfile(index_path):
            return FileResponse(index_path, media_type="text/html")
        # Fallback to root index (SPA)
        root_index = os.path.join(_frontend_dir, "index.html")
        if os.path.isfile(root_index):
            return FileResponse(root_index, media_type="text/html")
        raise HTTPException(status_code=404, detail="Not found")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
