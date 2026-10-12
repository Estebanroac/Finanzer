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
    graham_number, margin_of_safety, dcf_multi_stage_dynamic,
    dcf_sensitivity_analysis, calculate_wacc
)
from stock_database import search_stocks, POPULAR_STOCKS, TOP_STOCKS
from sector_profiles import get_sector_profile, YAHOO_SECTOR_MAPPING
from alert_interpretations import build_signals
from settings import cfg
from historical_metrics import fcf_cagr
from classify import CYCLICAL, FINANCIAL, GROWTH_PRE_PROFIT, classify, not_applicable
import archetype_metrics

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
    }


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
                nopat = oi_val * (1 - cfg("valuation.roic.tax_rate"))  # mismo impuesto que calculate_all_ratios
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
            result["classification"] = classification
            # Métricas de la rama (P/B justificado, EV/Ventas, normalizados de ciclo…)
            archetype_values = archetype_metrics.compute(
                archetype, _stmts, result["key_metrics"], beta=safe_float(financials.beta),
                revenue_cagr_3y=classification["inputs"].get("revenue_cagr_3y"))
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
            # Qué no aplica al arquetipo fuera de las categorías del score.
            result["not_applicable"] = {k: not_applicable(archetype, k)
                                        for k in ("dcf", "graham", "altman", "piotroski", "roce")
                                        if not_applicable(archetype, k)}

            # Inject sector-median benchmarks so valuation scoring judges P/E and
            # EV/EBITDA against the stock's SECTOR (e.g. ~30x for tech, ~12x for
            # banks) instead of a fixed ~20x. Without this, high-P/E sectors look
            # overvalued and low-P/E sectors look cheap regardless of fundamentals.
            _sector_bench = _get_sector_benchmarks(mapped_sector)
            fin_dict["sector_pe"] = _sector_bench.get("pe")
            fin_dict["sector_ev_ebitda"] = _sector_bench.get("ev_ebitda")

            # Señal de crecimiento para el scorer (categoría Crecimiento de 20 pts +
            # is_growth + bonos GARP/growth-quality de valoración). El CAGR histórico
            # a 3 años NO está en el critical path (el fetch de históricos se removió
            # por latencia), así que revenue_cagr_3y/eps_cagr_3y llegaban SIEMPRE en
            # None y toda la categoría corría inerte (is_growth siempre False). Usamos
            # el crecimiento YoY de Yahoo (revenueGrowth/earningsGrowth, ya disponibles
            # y en decimal) como proxy para activar el motor de crecimiento.
            # TODO(fase C): CAGR 3Y real re-habilitando el fetch histórico.
            if fin_dict.get("revenue_cagr_3y") is None:
                _rev_g = safe_float(financials.revenue_growth_yoy)
                if _rev_g is not None:
                    fin_dict["revenue_cagr_3y"] = _rev_g
            if fin_dict.get("eps_cagr_3y") is None:
                _eps_g = safe_float(financials.earnings_growth_rate)
                if _eps_g is not None:
                    fin_dict["eps_cagr_3y"] = _eps_g
            # CAGR del FCF a 3 años con los 4 ejercicios anuales de los estados
            # (etapa 5). Indefinido -> sin dato con motivo, nunca un número.
            if fin_dict.get("fcf_cagr_3y") is None:
                _fcf_series = ((yinfo.get("_statements_fy") or {}).get("free_cash_flow")
                               if _has_yahoo else None)
                _fcf_g, _fcf_why = fcf_cagr(_fcf_series)
                fin_dict["fcf_cagr_3y"] = _fcf_g
                fin_dict["fcf_cagr_3y_reason"] = _fcf_why

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
                fin_dict["fcf_cagr_3y"] = None
            elif archetype == FINANCIAL:
                fin_dict["revenue_growth_note"] = "YoY de los estados anuales (arquetipo FINANCIAL)"

            # ── Fase C: creación de valor (ROIC-WACC) y retorno al accionista ──
            _beta_est = financials.beta if financials.beta is not None else cfg("valuation.capm.default_beta")
            wacc_est = calculate_wacc(beta=_beta_est)
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

            # Company type: NO se calcula aquí. classify_company_type y
            # detect_growth_company requieren múltiples argumentos posicionales;
            # llamarlas con un solo dict lanzaba TypeError (tragado por el
            # except), dejando company_type='balanced' e is_growth=False para
            # TODA empresa. calculate_score_v2 ya computa ambos correctamente y
            # se copian tras el bloque de score (ver "Score (0-100)").
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
                except Exception as e:
                    _sin_dato("prior_year", e)

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
                    not_applicable_reason=not_applicable(archetype, "altman"),
                )
                result["altman_z"] = {
                    "z_score": z_val if z_val is not None else 0,
                    "zone": z_zone.lower() if z_zone else "grey",
                    "interpretation": z_interp,
                    "model": z_details.get("model", ""),
                    "details": z_details,
                    # Etapa 5: z_score 0 se conserva por contrato, pero NO es un dato:
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
                    "score": _pio["score"], "max_score": _pio["max_score"], "level": f_level,
                    "interpretation": f_interp,
                    "applicable": not _pio_na,
                    "details": f_criteria,
                    "fiscal_year": fy_label,
                    # Cobertura (etapa 5): "X/N evaluados" y el escalado a base 9.
                    "evaluated": _pio["evaluated"],
                    "scaled_score": safe_float(_pio["scaled_score"]),
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
                    ratios, fin_dict,
                    z_score_value=z_val,
                    z_score_level=z_zone,
                    f_score_value=_f_for_score,
                    sector_key=mapped_sector,
                    real_sector=sector,
                    wacc=wacc_est,  # Fase C: spread ROIC-WACC en rentabilidad
                    archetype=archetype,
                    archetype_values=archetype_values,
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
                        # Etapa 5: categoría no concluyente (excluida del total) y su cobertura.
                        "conclusive": cat.get("conclusive", True),
                        "applicable": cat.get("applicable", True),
                        "coverage": (cat.get("coverage") or {}).get("coverage"),
                        "score": cat.get("score", 0),
                        "max": cat.get("max_score", cfg("thresholds.score.category.max")),
                        "details": [a.get("reason", "") for a in cat.get("adjustments", [])],
                        "adjustments": cat.get("adjustments", []),
                    }

                result["score"] = {
                    "total_score": raw_score,
                    "max_score": raw_max,
                    "level": raw_level,
                    "breakdown": breakdown,
                    # Etapa 5: categorías excluidas del total por cobertura < 50%.
                    "excluded_categories": (score_result.get("excluded_categories", [])
                                            if isinstance(score_result, dict) else []),
                    "not_applicable_categories": (score_result.get("not_applicable_categories", [])
                                                  if isinstance(score_result, dict) else []),
                }
                # Un total parcial no puede leerse igual que uno completo: se
                # declara sobre cuántas categorías se calculó.
                _n_inc = score_result.get("categories_included") if isinstance(score_result, dict) else None
                _n_tot = score_result.get("categories_total") if isinstance(score_result, dict) else None
                if _n_inc is not None and _n_tot:
                    result["score"]["categories_included"] = _n_inc
                    result["score"]["categories_total"] = _n_tot
                    result["score"]["partial"] = _n_inc < _n_tot
                    result["score"]["basis"] = (f"calculado sobre {_n_inc} de {_n_tot} categorías"
                                                if _n_inc < _n_tot else None)

                # Financial health (sector financiero): calculate_score_v2 ya lo
                # computó correctamente con los argumentos correctos; exponerlo
                # como {score, level, interpretation, details} para el frontend.
                # Cobertura por categoría (bloque nuevo del contrato, etapa 5). La
                # baja confianza no cambia el score: la usará la etapa 8.
                if isinstance(score_result, dict) and score_result.get("coverage"):
                    result["score_coverage"] = score_result["coverage"]

                if isinstance(score_result, dict) and score_result.get("financial_health"):
                    result["financial_health"] = score_result["financial_health"]

                # Perfil de empresa: única fuente de verdad = el score v2 (los
                # helpers directos lanzaban TypeError, ver "Company type" arriba).
                if isinstance(score_result, dict):
                    result["company_type"] = score_result.get("company_type", "balanced")
                    result["is_growth"] = bool(score_result.get("is_growth_company", False))
            except Exception as e:
                logger.error(f"Score calculation error: {e}")
                result["score"] = None
                _sin_dato("score", e)

            # Valuation (Graham + DCF)
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
                    # Antes los argumentos estaban invertidos, dando el signo al
                    # revés (una acción sobrevalorada mostraba margen positivo).
                    result["graham_margin"] = safe_float(
                        margin_of_safety(graham, price)
                    )

                # DCF — skip for financials: FCF is ill-defined for banks/insurers
                # (no traditional capex/working-capital cycle), so an FCF-DCF fair
                # value is misleading. They are valued on book value / ROE instead —
                # same rationale as the Altman Z-Score exclusion.
                # Sanitize like the metrics path (see fcf_val above): a raw NaN
                # is truthy and only skipped here by the `> 0` check, and a raw
                # +Inf would pass it and land un-sanitized in the sensitivity
                # matrix (stored raw below) → non-finite tokens → invalid JSON.
                fcf = safe_float(financials.free_cash_flow)
                growth = financials.revenue_growth_yoy or cfg("valuation.dcf.default_growth")
                # Etapa 6: el arquetipo decide si hay DCF-FCFF (no en FINANCIAL ni
                # REIT; en GROWTH_PRE_PROFIT solo con FCF positivo) y con qué inputs
                # (CYCLICAL: FCF normalizado = margen FCF promedio × ingresos
                # actuales, y crecimiento normalizado de ciclo medio).
                _dcf_na = not_applicable(archetype, "dcf")
                if not _dcf_na and archetype == GROWTH_PRE_PROFIT and not (fcf and fcf > 0):
                    _dcf_na = "No aplica a GROWTH_PRE_PROFIT con FCF negativo: no hay flujo que descontar"
                if _dcf_na:
                    result["not_applicable"]["dcf"] = _dcf_na
                if archetype == CYCLICAL:
                    fcf = safe_float(archetype_values.get("fcf_normalized"))
                    if archetype_values.get("revenue_growth_normalized") is not None:
                        growth = archetype_values["revenue_growth_normalized"]
                if fcf and fcf > 0 and price and financials.shares_outstanding and not _dcf_na:
                    beta = financials.beta if financials.beta is not None else cfg("valuation.capm.default_beta")
                    wacc = calculate_wacc(beta=beta)

                    # Deuda neta para el puente Enterprise Value -> Equity Value.
                    # Sin esto, el DCF dividía el enterprise value entre acciones sin
                    # descontar la deuda, sobrevalorando a las empresas apalancadas.
                    _net_debt = None
                    if td_val is not None or cash_val is not None:
                        _net_debt = (td_val or 0.0) - (cash_val or 0.0)

                    dcf_result = dcf_multi_stage_dynamic(
                        fcf=fcf,
                        shares_outstanding=financials.shares_outstanding,
                        beta=beta,
                        total_debt=td_val,
                        cash=cash_val,
                        revenue_growth_3y=growth,  # el DCF aplica el tope (30%) y el suelo (<= -20% -> 8%)
                    )
                    # DCF y grid comparten supuestos (etapa 4): el crecimiento USADO por el
                    # DCF (tras tope y suelo) y su mismo tipo de decaimiento.
                    _g_used = dcf_result.get("growth_estimated")
                    if _g_used is None:
                        _g_used = growth
                    _decay = dcf_result.get("decay_type") or "linear"
                    # upside y margin_of_safety se calculan aquí (price está en
                    # scope). El dict del DCF nunca tuvo claves 'upside_pct' ni
                    # 'margin_of_safety_value', así que antes ambos quedaban None.
                    # value_composition vive dentro de model_result, no en el nivel
                    # superior. Con el fair_value ya corregido (equity value), el
                    # upside es real.
                    _fv = safe_float(dcf_result.get("fair_value_per_share"))
                    _dcf_upside = ((_fv - price) / price * 100.0) if (_fv is not None and price and price > 0) else None
                    _dcf_mos = ((_fv - price) / _fv) if (_fv not in (None, 0)) else None
                    _dcf_model = dcf_result.get("model_result") or {}
                    result["dcf"] = {
                        "fair_value": _fv,
                        "wacc": safe_float(wacc),
                        "growth_rate": safe_float(_g_used),  # el usado, no el bruto
                        "terminal_growth": safe_float(cfg("valuation.dcf.terminal_growth")),
                        "margin_of_safety": safe_float(_dcf_mos),
                        "upside": safe_float(_dcf_upside),
                        "value_composition": _dcf_model.get("value_composition"),
                    }
                    if archetype == CYCLICAL:
                        result["dcf"]["normalized"] = {
                            "fcf": safe_float(fcf), "fcf_margin_avg": safe_float(archetype_values.get("fcf_margin_avg")),
                            "years": archetype_values.get("cycle_years"),
                            "cycle_incomplete": archetype_values.get("cycle_incomplete"),
                        }

                    # Sensitivity
                    try:
                        sens = dcf_sensitivity_analysis(
                            fcf=fcf,
                            shares_outstanding=financials.shares_outstanding,
                            current_price=price,
                            base_growth_rate=_g_used,
                            base_discount_rate=wacc or cfg("valuation.wacc.default"),
                            net_debt=_net_debt or 0.0,
                            decay_type=_decay,
                        )
                        result["sensitivity"] = sens
                    except Exception as e:
                        logger.error(f"Sensitivity error: {e}")
                        _sin_dato("sensitivity", e)
            except Exception as e:
                logger.error(f"Valuation error: {e}")
                _sin_dato("graham/dcf", e)

            # Alerts — motor de interpretación de señales (el "cerebro"): convierte
            # los ratios crudos en fortalezas/advertencias/riesgos con una lectura
            # ADAPTATIVA de 1-2 líneas por ítem (lib/alert_interpretations.py),
            # graduada por magnitud y sector. Reemplaza el ensamblado disperso
            # anterior (condiciones crudas con detail vacío).
            try:
                result["alerts"] = build_signals(
                    ratios, fin_dict,
                    sector=mapped_sector, real_sector=sector,
                    roic_wacc_spread=roic_wacc_spread,
                    altman=result.get("altman_z"),
                    piotroski=result.get("piotroski_f"),
                    dcf=result.get("dcf"),
                    is_growth=result.get("is_growth", False),
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
            except Exception as e:
                _sin_dato("yearly_financials", e)

        # Validación de salida: múltiplos <= 0 -> "no significativo". Va al
        # final para no alterar las entradas del score ni de las alertas.
        _out_flags = []
        try:
            from validate import validate_outputs
            _out_flags = validate_outputs(result)
        except Exception as e:
            _sin_dato("validacion_salida", e)
        result["data_validation"] = list(yinfo.get("_validation") or []) + _out_flags
        result["data_provenance"] = _build_provenance(yinfo, _out_flags, _block_errors)

        return result

    except HTTPException:
        raise
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

        _mapped = (analysis.get("sector_info") or {}).get("mapped_sector", "default")
        buf = io.BytesIO()
        build_report(
            buf, analysis,
            sector_bench=_get_sector_benchmarks(_mapped),
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
