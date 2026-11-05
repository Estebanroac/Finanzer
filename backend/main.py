"""
Finanzer API - FastAPI backend that exposes the financial brain
"""
import sys
import mimetypes
import os
import asyncio
import contextlib
import io
import logging
import re
import threading
import time
from typing import Annotated, Optional, Dict, Any
from starlette.concurrency import run_in_threadpool
from fastapi import Body, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

# Add lib to path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))

from data_fetcher import FinancialDataService, InvalidSymbolError
from financial_ratios import (
    calculate_all_ratios, calculate_score_v2,
    altman_z_score, altman_excluded, altman_model_basis, piotroski_evaluate, piotroski_level, interest_coverage_state, net_debt_ebitda_state,
    graham_number, margin_of_safety, dcf_multi_stage_dynamic, roic_significant,
    dcf_sensitivity_analysis, peg_not_significant
)
from stock_database import search_stocks, POPULAR_STOCKS, TOP_STOCKS
from sector_profiles import get_sector_profile, YAHOO_SECTOR_MAPPING
from alert_interpretations import build_signals
from settings import cfg
from historical_metrics import (mean as hm_mean, fcf_cagr, growth_rate, is_sustained_negative, on_statement, per_share,
                                per_share_basis, robust_growth, backing_base, edgar_fcf, is_anomalous_not_significant,
                                bound_decides)
from classify import (ARCHETYPE_GROUP, CYCLICAL, FINANCIAL, GROWTH_PRE_PROFIT, REIT, archetype_label, classify,
                      not_applicable, not_applicable_text, subtype_not_applicable)
from normalize import normalize as normalize_earnings, pieces_operating_income
from yf_adapter import _UNUSUAL_ROWS
from ttm import TTM_QUARTERS
from verdict import price as verdict_price, verdict as build_verdict
from cost_of_capital import (adjusted_beta, capm_rates, cost_of_debt, effective_tax_rate, equity_cost,
                             wacc as compute_wacc)
from valuation_confidence import (convergence, coverage_dimension, dcf_reliability, dcf_wacc_flips, signal_from_upside,
                                  official_dimension,
                                  source_dimension, stability_dimension, verdict_confidence,
                                  fragility_dimension)
import archetype_metrics
import sec_edgar as edgar
import growth_currency
import numfmt
import exchanges
from currency import CurrencyConversionError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Finanzer API", version="2.0")

# V6 (revisión de seguridad, B16): un 500 dice esto; el detalle (excepción y traza) va solo al registro.
INTERNAL_ERROR = "Error interno del servidor. Inténtalo de nuevo en unos minutos."


def _on_render(env=os.environ) -> bool:
    return bool((env.get("RENDER_EXTERNAL_URL") or "").strip())


if not _on_render():
    # `next dev` en local, en cualquier puerto (rediseño: dos sesiones prueban a la vez en 3000 y 3001). V6 (B15): solo
    # fuera de Render; en producción la web y la API son del mismo origen y no hace falta CORS.
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# V6 (revisión de seguridad, B5): ningún cuerpo de petición de más de `max_body_bytes` (413 sin leer el resto).
import web_guard as _web_guard  # noqa: E402
app.add_middleware(_web_guard.BodyLimit, max_bytes=cfg("data.server.max_body_bytes"))
# V6 (hallazgo F23): política de contenido, nosniff y Referrer-Policy en cada respuesta; en el HTML, los hashes de sus
# scripts en línea.
app.add_middleware(_web_guard.SecurityHeaders, directives=cfg("data.server.csp"),
                   referrer_policy=cfg("data.server.referrer_policy"))
# V4 (encargo del PM): compresión gzip de las respuestas, la capa más externa (después de calcular la CSP).
app.add_middleware(_web_guard.Compress, minimum_size=cfg("data.server.gzip_minimum_bytes"),
                   level=cfg("data.server.gzip_level"), exclude_paths=cfg("data.server.gzip_exclude_paths"))

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
        if v is None or k == "snapshot":
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


def _select_benchmark(mapped_sector: str, archetype: Optional[str], sector: Optional[str] = None,
                      industry: Optional[str] = None, country: Optional[str] = None, symbol: Optional[str] = None,
                      title: Optional[str] = None, company: Optional[dict] = None, name: Optional[str] = None) -> dict:
    """Benchmark de valoración relativa: la industria de la empresa en su región (Damodaran, lib/industry_bench.py)
    o, si el arquetipo contradice al sector de Yahoo, el mercado amplio (perfil market).

    Devuelve {profile, sector, values, reason, sources, industry, provisional, ...}: `values` alimenta el score (P/E y
    EV/EBITDA frente a la referencia) y las tablas comparativas. Fase 4/7 (F4_PARADA §5): solo entra en `values` lo que
    tiene fuente; una métrica sin referencia con fuente se muestra sin referencia (no con una cifra fijada a mano).
    F10 · N2: la referencia nunca incluye a la propia empresa (`company`: sus cifras a la fecha del conjunto,
    lib/self_exclusion.py); cada fuente lo declara."""
    import re
    import industry_bench
    import names
    key = re.sub(r'[\s-]+', '_', (mapped_sector or "default").lower())
    expected = cfg("sectors.benchmarks.sector_archetype").get(key)
    from financial_ratios import SECTOR_THRESHOLDS, ThresholdConfig
    _th_keys = ("roe_high", "roe_low", "roa_high", "roa_low", "debt_equity_high", "operating_margin_low",
                "net_margin_low", "interest_coverage_low", "current_ratio_low")

    def _th(k):
        t = SECTOR_THRESHOLDS.get(k, ThresholdConfig())
        return {n: getattr(t, n) for n in _th_keys}

    def _src(ib, col=None):
        # V7 (nombres en español): la industria en español; el original, en el anexo del informe
        where = (f"industria «{names.damodaran(ib['damodaran'])}»" if isinstance(ib["damodaran"], str) else
                 "industrias de su sector (media ponderada por empresas)")
        base = f"{ib['source']}, {ib['as_of']}: {where}, {ib['region_label']}, {ib['firms']} empresas"
        se = ib.get("self_exclusion")
        if not se:
            return base
        how = ((se.get("columns") or {}).get(col) or {}).get("how")
        if how == "mediana_pares" and se["method"] == "sin_empresa":
            n = se["columns"][col].get("n")
            return f"{base}; mediana de {n} pares del universo (sin las cifras de la empresa para esta columna)"
        if how == "no_entra":
            return f"{base} (la empresa no entra en este agregado: Damodaran lo calcula sin las empresas en pérdidas)"
        if se["method"] == "mediana_pares":
            return f"{se['declaration']} (Yahoo Finance, {se.get('peers_date')})"
        return f"{base}; {se['declaration']}"

    mk = industry_bench.market(country, symbol, title, company, name)
    if expected and archetype and archetype != expected:
        values = dict(mk["values"])
        sources = {k: _src(mk, k) for k in values}
        if mk["region"] == "us":
            # P/E, Forward P/E y EV/EBITDA del S&P 500 (medianas y agregado del índice con su fuente)
            market = dict(cfg("sectors.benchmarks.market"))
            values.update(market)
            sources.update({k: v for k, v in cfg("sectors.benchmarks.market_source").items() if k in market})
        return {"profile": "market", "sector": key, "thresholds_key": "market", "thresholds": _th("market"),
                "values": values,
                # Etapa 9b: etiquetas en español (el código queda en el detalle técnico).
                "reason": (f"empresa clasificada como {archetype_label(archetype)} dentro del sector {key}, "
                           f"cuyas medianas y umbrales suponen {ARCHETYPE_GROUP.get(expected, expected)}: se usan "
                           "los del mercado amplio"),
                "sources": sources, "industry": {k: v for k, v in mk.items() if k != "values"},
                "ref": "del mercado (S&P 500)" if mk["region"] == "us" else f"del mercado ({mk['region_label']})",
                "short": "mercado", "provisional": False}
    ib = industry_bench.industry(sector, industry, country, symbol, title, company, name)
    if ib is None:
        # sin industria ni sector en el mapa: la referencia PROVISIONAL de siempre, dicho
        return {"profile": "sector", "sector": key, "thresholds_key": mapped_sector, "thresholds": _th(mapped_sector),
                "values": _get_sector_benchmarks(mapped_sector), "reason": None, "sources": None, "industry": None,
                "ref": "del sector", "short": "sector", "provisional": True}
    values = dict(ib["values"])
    sources = {k: _src(ib, k) for k in values}
    for k in ("pe", "ev_ebitda"):     # los dos que puntúan: sin dato de la industria, el mercado de su región
        if k not in values and k in mk["values"]:
            values[k] = mk["values"][k]
            sources[k] = _src(mk, k) + " (la industria no tiene dato)"
    # F11 · T1 (revisión de NFLX): una referencia de rentabilidad casi nula no es representativa (Entretenimiento de
    # EE. UU. sin Netflix: ROE 0,63 %, margen neto 0,48 %; brechas de +7.870 %). La columna sale de la referencia, con su
    # motivo: ni lectura ni alerta frente a ella, como cualquier columna sin referencia.
    _R = cfg("sectors.benchmarks.industry")
    not_repr = {}
    for k in _R["profit_columns"]:
        v = values.get(k)
        if v is not None and abs(v) < _R["min_profit_ratio"]:
            not_repr[k] = v
            values.pop(k)
            sources.pop(k, None)
    # F10 · N2: la lectura dice qué referencia es («frente a 53x de su industria sin ella»; el nombre y el peso, en la
    # nota de la referencia)
    _se = ib.get("self_exclusion") or {}
    ref = {"sin_empresa": "de su industria sin ella",
           "mediana_pares": "de sus pares del universo"}.get(_se.get("method"), "de su industria")
    if _se.get("degraded"):     # F10 (PM, 29-oct): la fila dice que la referencia está degradada
        ref += " (referencia degradada: EDGAR no respondió)"
    return {"profile": "sector", "sector": key, "thresholds_key": mapped_sector, "thresholds": _th(mapped_sector),
            "values": values, "reason": None, "sources": sources,
            "industry": {k: v for k, v in ib.items() if k != "values"}, "ref": ref,
            "short": "pares" if _se.get("method") == "mediana_pares" else "industria", "provisional": False,
            **({"not_representative": not_repr} if not_repr else {})}


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
            # Fase 6: la petición a Yahoo es bloqueante: fuera del bucle de eventos.
            yahoo_results = await run_in_threadpool(_yahoo_search, q, 8 - len(results))
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
        # El módulo, no el nombre: `from yf_adapter import _session` copiaba el valor de antes de crear la sesión (None
        # en un proceso recién arrancado) y la búsqueda en Yahoo fallaba en silencio hasta el primer análisis.
        import yf_adapter as _ya
        _session = _ya._live_session()
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
        # Fase 2b (T3): corte coherente: fecha y tipo del corte y periodo de cada campo de los estados.
        "as_of": yinfo.get("_as_of"),
        "pending_results": yinfo.get("_pending_results"),
        # F8 · E6: frescura de los estados frente a EDGAR.
        "staleness": yinfo.get("_staleness"),
        "edgar": yinfo.get("_edgar"),
        # Fase 2b (T4, D7): emisor con estados en la SEC, sin ellos (aviso y techo "baja") o sin verificación.
        "official_source": yinfo.get("_official_source"),
        # Fase 2b (T5): deuda coherente con el EBITDA y sus componentes (F2_PRECEDENCIA §2.3).
        "debt": yinfo.get("_debt"),
        # Fase 2b (T7): beneficio y patrimonio del accionista ordinario (AT1 y preferentes separados).
        "ordinary": yinfo.get("_ordinary"),
        # Fase 2b (T7): cambio de perímetro (operaciones discontinuadas y ejercicios reexpresados), solo declarado.
        "perimeter": yinfo.get("_perimeter"),
        # F2_PRECEDENCIA §2.1 (escenario B): beneficio operativo de Yahoo frente al de EDGAR; "estimado" si difiere > 2%.
        "ebit": yinfo.get("_ebit"),
        # Fase 2b: serie diaria de precios y dividendo indicado en la moneda y la clase del precio (T2).
        "price_history": yinfo.get("_price_history"),
        "dividend": yinfo.get("_dividend"),
        # Fase 2b (T6): beta (propia, del sector o de la fuente) y rango de 52 semanas de la serie.
        "beta": yinfo.get("_beta"),
        "range52": yinfo.get("_range52"),
    }


# Etapa 11b: tipo de instrumento de Yahoo (quoteType) -> cómo se nombra en el mensaje.
_INSTRUMENT_NAMES = {"ETF": "un ETF", "MUTUALFUND": "un fondo de inversión", "INDEX": "un índice",
                     "CRYPTOCURRENCY": "una criptomoneda", "CURRENCY": "una divisa", "FUTURE": "un futuro",
                     "OPTION": "una opción", "MONEYMARKET": "un fondo monetario"}


def _revenue_usd(revenue: Optional[float], price_currency: Optional[str]) -> Optional[float]:
    """Ventas en USD para el tramo de tamaño de las tasas base (revisión de código F3, hallazgo 4): los importes van
    en la moneda de la cotización (EUR en MC.PA, KRW en 005930.KS). Sin moneda o sin tipo de cambio, None: la lectura
    del inverso queda sin tasa base y lo dice; nunca se lee otra moneda como USD."""
    from currency import base_currency, fetch_fx
    cur, unit = base_currency(price_currency)
    if revenue is None or cur is None:
        return None
    if cur == "USD":
        return revenue * unit
    try:
        import datetime as _dt
        import yfinance as yf
        return revenue * unit * fetch_fx(cur, "USD", yf.Ticker).close_at(_dt.date.today())
    except Exception as e:
        logger.info(f"sin tipo de cambio {cur}→USD para las tasas base: {e}")
        return None


def source_unavailable_message(symbol: str) -> str:
    """Sin perfil porque la fuente de datos de mercado no respondió (conexión o tiempo agotado)."""
    return (f"No se pudieron obtener los datos de {symbol}: la fuente de datos de mercado no responde ahora mismo. "
            "Vuelve a intentarlo en unos minutos.")


def not_a_stock_message(symbol: str, quote_type: str) -> str:
    what = _INSTRUMENT_NAMES.get(str(quote_type).upper(), "un instrumento que no es una acción")
    return (f"Finanzer analiza acciones individuales: {symbol} es {what}, así que no se analiza "
            "(sus estados, ratios y valoración no tienen sentido como los de una empresa).")


def _base_rate_for_confidence(rev: Optional[dict]) -> Optional[dict]:
    """F10 · N4: la tasa base del DCF inverso principal (la que cita el informe), si la regla es la de las tasas base y
    la lectura es válida; None si no la hay."""
    m = (rev or {}).get("main") or {}
    br = m.get("base_rate") or {}
    if m.get("state") != "ok" or m.get("rule") != "tasa_base" or br.get("share") is None or br.get("reason"):
        return None
    return {"share": br["share"], "g10": m.get("g10"), "horizon_years": br.get("horizon_years")}


def _compute_analysis(symbol: str) -> dict:
    """
    Shared analysis computation used by both API endpoint and PDF generator.
    Returns the full analysis dict or raises HTTPException.
    Fiabilidad (V4 · moneda): los importes de los textos van en la moneda del precio (numfmt.currency); al salir, la
    moneda vuelve a la de antes (el hilo de la cola de fondo formatea después otros resúmenes).
    """
    with numfmt.currency(None):
        return _compute_analysis_body(symbol)


def _compute_analysis_body(symbol: str) -> dict:
    # V2 (fuentes reales): la clase con punto (BRK.B, BF.B) es la de Yahoo con guion; antes daba 404 "No data found".
    # Solo las clases de market.universe.share_classes: BARC.L o MC.PA son bolsas y no se tocan.
    import universe as _universe
    symbol = _universe.norm_symbol(symbol)
    ic_state_inferred = False   # fase 1: estado de la cobertura inferido (sin resultado financiero en los estados)
    _id_flags: list = []        # fase 1: identidades de datos que no cuadran (data_validation)
    dy_invalid = False
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
            if (data or {}).get("source_unavailable"):
                # Verificación de la v4 (V3): la fuente no respondió; no es que el símbolo no exista. Mismo código (404)
                # para que la web actual no cambie; el motivo lo dice.
                raise HTTPException(status_code=404, detail=source_unavailable_message(symbol))
            raise HTTPException(status_code=404, detail=f"No data found for {symbol}")

        profile = data["profile"]
        financials = data.get("financials")
        historical = data.get("historical", {})
        # Fase 2b (T6): el rango de 52 semanas sale de la serie de precios de la misma sesión que la cotización
        # (lib/beta.py); ya no se ensancha con el precio (protección 2 de la fase 1, retirada).
        # Build response
        result = {
            "symbol": symbol,
            "profile": {
                "name": profile.name,
                "sector": profile.sector,
                "industry": profile.industry,
                "country": profile.country,
                "currency": profile.currency,
                "exchange": exchanges.name(profile.exchange),     # E2a (T2): "Nasdaq", no "NMS"
                "exchange_code": profile.exchange,
                "market_cap": safe_float(profile.market_cap),
                "description": profile.description,
            },
            "price": safe_float(financials.price) if financials else None,
            "errors": data.get("errors", []),
        }
        numfmt.set_currency(profile.currency)      # V4 · moneda: los importes de los textos, en la del precio
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
                # Fase 7: el mismo snapshot del que salen los estados (otro, si caducó entre medias, mezclaría periodos)
                yinfo = getattr(financials, "snapshot", None) or get_ticker_info(symbol)
                # V7 (M2): los ratios son TTM o del último ejercicio; los textos lo dicen con la cifra.
                fin_dict["ttm_basis"] = (yinfo.get("_ttm") or {}).get("basis")
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

                # Fase 2b (T3, F2_PRECEDENCIA §1, paso 3): una ratio TTM de Finnhub solo entra si casa con el corte, y
                # aquí solo llegaría cuando el motor no la tiene del corte: no hay con qué casarla, así que no entra
                # y se anota (es de su propio periodo; JNJ, MU).
                _fprov = yinfo.get("_provenance") or {}
                _yr_key = {"current_ratio": "currentRatio", "quick_ratio": "quickRatio", "payout_ratio": "payoutRatio",
                           "interest_coverage": "interestCoverage", "inventory_turnover": "inventoryTurnover"}
                for k, v in fallback_map.items():
                    if ratios.get(k) is None and v is not None:
                        if k in _yr_key and (_fprov.get(f"_yahoo_ratios.{_yr_key[k]}") or {}).get("source") == "finnhub":
                            _id_flags.append({"field": f"ratios.{k}", "rule": "periodo_incoherente", "action": "aviso",
                                              "old": v, "new": None,
                                              "reason": (f"{k} de Finnhub ({v:.4g}) sin dato del corte de los estados "
                                                         "con que casarlo: es de otro periodo y no entra")})
                            continue
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
            # F8 · E4 (auditoría del 26-oct, VZ): en una telecom, el FCF de la valoración (P/FCF, FCF yield y DCF)
            # resta la media de 5 años de las compras de espectro (EDGAR); sin ese dato, sin ajuste y declarado.
            _spectrum = None
            try:
                import telecom_spectrum as _tsp
                _spectrum = _tsp.adjustment(yinfo.get("_history_fy") if _has_yahoo else None, profile.industry)
            except Exception as e:
                _sin_dato("espectro_telecom", e)
            result["spectrum_adjustment"] = _spectrum
            _spec_avg = _spectrum["average"] if (_spectrum or {}).get("status") == "ok" else None
            if _spec_avg is not None and fcf_val is not None:
                _fcf_val_adj = fcf_val - _spec_avg
                _spectrum.update({"fcf": fcf_val, "fcf_adjusted": _fcf_val_adj})
                fcf_yield = _fcf_val_adj / mcap if mcap and mcap > 0 else None
                pfcf = mcap / _fcf_val_adj if mcap and _fcf_val_adj > 0 else None

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
            # Fase 1 del plan de fiabilidad: el estado de la cobertura se decide UNA vez, con el signo del EBIT de
            # los estados y el del resultado financiero neto, y lo leen el score, las alertas, el WACC y el texto.
            nii_val = safe_float(getattr(financials, "net_interest_income", None))
            # "Sin carga" exige el signo en el TTM y en cada trimestre: un trimestre atípico (NFLX 2026-03,
            # +2.85 B de ingresos financieros) no convierte en acreedora neta a una empresa que paga intereses.
            nii_q = safe_float(getattr(financials, "net_interest_income_min_q", None))
            nii_sign = min(v for v in (nii_val, nii_q) if v is not None) if nii_val is not None else None
            ic_state = interest_coverage_state(safe_float(interest_cov), r("net_debt"), ebit=oi_val,
                                               net_interest_income=nii_sign)
            ic_state_inferred = ic_state == "sin_carga" and nii_val is None
            fin_dict["interest_coverage_state"] = ic_state

            # Payout Ratio — from Yahoo
            payout = r("payout_ratio")
            if payout is None:
                pr_yahoo = yr.get("payoutRatio") if _has_yahoo else None
                # Fase 2b (T3): el payout TTM de Finnhub no entra sin dato del corte con que casarlo (ver arriba).
                if pr_yahoo is not None and ((yinfo.get("_provenance") or {}).get("_yahoo_ratios.payoutRatio")
                                             or {}).get("source") != "finnhub":
                    payout = pr_yahoo

            # Dividend yield from Yahoo — check _yahoo_ratios AND main info dict
            div_yield = r("dividend_yield")
            if div_yield is None and _has_yahoo:
                dy_yahoo = yr.get("dividendYield") or yinfo.get("dividendYield")
                if dy_yahoo is not None and dy_yahoo != 0:
                    div_yield = dy_yahoo
            # Fase 2b (T2): el dividendo indicado ya llega en la moneda y la clase del precio (yf_adapter.
            # _apply_dividend, lib/dividends.py), verificado con los pagos del propio título en los dos sentidos. Se
            # retira la protección de la fase 1 (yield > 2 × lo pagado → sin dato), que comparaba ventanas distintas
            # (anulaba la subida de NVDA) y tapaba un dato mal unido en origen (BCS en peniques). "Sin dato" queda solo
            # si la empresa paga dividendos y ninguna fuente da uno que cuadre, con el motivo.
            _div = yinfo.get("_dividend") or {}
            if _div.get("rate") is None and (_div.get("paid_per_unit_statements") or 0) > 0:
                _id_flags.append({"field": "key_metrics.dividend_yield", "rule": "dividendo_sin_fuente",
                                  "action": "sin_dato", "old": None, "new": None,
                                  "reason": ("la empresa paga dividendos, pero ninguna fuente da un dividendo indicado "
                                             f"que cuadre ({_div.get('reason')}); sin dato, no puntúa")})
                div_yield = None
                dy_invalid = True
                ratios["dividend_yield"] = None

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

            # F10 · margen operativo con una sola verdad (verificación de «Modelo general», regla 4): sin corte
            # trimestral (ruta quoteSummary), el margen operativo que se enseña y puntúa es el del último ejercicio de
            # los estados (el EBIT que presenta el emisor si EDGAR lo tiene), el mismo de las piezas de la
            # normalización; el operatingIncome de quoteSummary es otra definición o periodo (CRL, FDXF).
            _om_fy = None
            if _has_yahoo and ((yinfo.get("_as_of") or {}).get("type")) == "fuente":
                from normalize import fy_operating
                _om_fy = fy_operating(yinfo.get("_statements_fy"))
                if _om_fy is not None:
                    _om_fy["replaced"] = safe_float(ratios.get("operating_margin"))
                    ratios["operating_margin"] = _om_fy["value"]
                    from yf_adapter import _tag_provenance
                    _tag_provenance(yinfo, "estados_fy", (
                        f"margen operativo del ejercicio FY{_om_fy['year']} de los estados (EBIT del emisor / ingresos "
                        f"del ejercicio): sin corte trimestral; quoteSummary daba "
                        + (f"{_om_fy['replaced']:.1%}" if _om_fy["replaced"] is not None else "otra cifra")
                        + ", otra definición o periodo"), paths=["key_metrics.operating_margin", "key_metrics.operating_income"], overwrite=True)

            numfmt.set_ebitda_margin(safe_float(r("ebitda_margin")))   # el motivo de un EV/EBITDA acotado
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
                "interest_coverage_state": ic_state,
                "net_interest_income": nii_val,
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
                "operating_income": _om_fy["operating_income"] if _om_fy is not None else oi_val,   # regla 4
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
            # Fase 3 (T1b): el crecimiento se mide en la moneda de los estados (sin el tipo de cambio); la
            # valoración sigue en la del precio. Sin conversión, son las mismas filas.
            _cur_info = (yinfo.get("_currency") or {}) if _has_yahoo else {}
            _stmts_g = growth_currency.local(_stmts, _cur_info)
            # Etapa 9a: FCF − SBC en el periodo del FCF (informativo en todos los arquetipos;
            # en GROWTH_PRE_PROFIT es la base del margen FCF, la regla de 40 y el crecimiento del FCF).
            # Fase 3 (T2): se calcula antes de clasificar porque el crecimiento rentable lo admite como margen.
            _ttm_i = (yinfo.get("_ttm") or {}) if _has_yahoo else {}
            sbc_info = archetype_metrics.sbc_adjustment(
                fcf=safe_float(financials.free_cash_flow), revenue=safe_float(financials.revenue),
                fcf_is_ttm="freeCashflow" in (_ttm_i.get("ttm_fields") or []),
                sbc_ttm=safe_float(yinfo.get("stockBasedCompensation")) if _has_yahoo else None, st=_stmts)
            # Fase 3 (T2, D4): la ciclicidad y el crecimiento rentable se miden con la historia anual de EDGAR.
            classification = classify(sector=sector, industry=profile.industry, eps_ttm=eps_val,
                                      net_margin_ttm=r("net_margin"), statements_fy=_stmts_g,
                                      history=(yinfo.get("_history_fy") if _has_yahoo else None),
                                      operating_margin_ttm=r("operating_margin"),
                                      fcf_sbc_margin=sbc_info.get("fcf_margin_adjusted"))
            archetype = classification["archetype"]
            fin_dict["subtype"] = classification.get("subtype")   # F9 · R4: score y alertas (margen neto de un banco)
            # Etapa 11b: aviso por filas clave del arquetipo ausentes en los estados.
            from validate import missing_key_rows
            _row_flags = missing_key_rows(_stmts, archetype) if _has_yahoo else []
            result["classification"] = classification
            # F8 · E3: el FFO de un REIT es el de Nareit (− ventas de inmuebles + deterioros, del estado de flujos que
            # presentó el emisor), no beneficio neto + D&A. Antes de todo lo que lo lee (cobertura, payout, score).
            _reit_ffo_res = None
            if archetype == REIT:
                import reit_ffo
                _reit_ffo_res = (yinfo.get("_reit_ffo") if _has_yahoo else None) or reit_ffo.no_data(
                    "no se leyeron los ajustes del emisor")
                result["reit_ffo"] = reit_ffo.apply(ratios, result["key_metrics"], fin_dict, _reit_ffo_res)
            # Fase 2b (T5, F2_PRECEDENCIA §2.3): en un banco la deuda (subordinada, depósitos y emisiones de la
            # actividad bancaria) no entra en ninguna ratio de apalancamiento de empresa: su apalancamiento se mide
            # con capital (fase 3). Antes salían D/E, deuda neta y EV con toda la deuda emitida (BCS: EV negativo).
            _bank_leverage_na = []
            if classification.get("rule") == "industria_banco":
                for _k in ("de", "debt_to_assets", "net_debt", "net_debt_to_ebitda", "net_debt_to_ebitda_state",
                           "enterprise_value", "ev_ebitda", "ev_revenue"):
                    if result["key_metrics"].get(_k) is not None:
                        result["key_metrics"][_k] = None
                        _bank_leverage_na.append(_k)
            # Rf (etapa 8; F8 · E1): el del par Rf–ERP de la misma fecha (Damodaran); el ^TNX del día, de referencia.
            # Uno por análisis: el mismo en Ke (P/B justificado de FINANCIAL), Kd y WACC.
            rf_info = capm_rates()
            # F8 · E1: beta (propia si pasa los filtros; si no, de abajo hacia arriba reapalancada con la D/E de mercado y
            # la t de la empresa; lib/beta.py) y UN solo Ke con sus pisos (Rf + 0,5 × ERP; Kd + 1 pp con deuda): el del
            # WACC, el del P/B justificado (FINANCIAL, UTILITY) y el del DCF del REIT.
            # F9 · R1: prima de riesgo país por dónde opera (geografía de los ingresos del XBRL; si no, la sede operativa
            # de EDGAR o de la ficha; nunca el domicilio legal). Los segmentos quedan en caché por filing (la cautiva
            # de E10 los reutiliza).
            import country_risk as _crisk
            _geo_segs = None
            if _has_yahoo and (yinfo.get("_edgar") or {}).get("country"):
                try:
                    import segments as _segments
                    _geo_segs = _segments.build(symbol)
                except Exception as e:  # noqa: BLE001 — sin geografía: la sede, declarado
                    logger.warning(f"{symbol}: segmentos para la prima de riesgo país: {e}")
            _hq = ((yinfo.get("_edgar") or {}).get("country") if _has_yahoo else None) or profile.country
            crp_info = _crisk.exposure(_geo_segs, _hq)
            result["country_risk"] = crp_info
            # F9 · R2b: con la beta de abajo hacia arriba, la tabla de Damodaran de la región donde opera (la misma
            # exposición).
            import beta as _beta_mod
            _beta_info = (yinfo.get("_beta") or {}) if _has_yahoo else {}
            _beta_info = _beta_mod.regionalize(_beta_info, _crisk.beta_region(crp_info),
                                               yinfo.get("sector") if _has_yahoo else None,
                                               yinfo.get("industry") if _has_yahoo else None)
            _beta_info = _beta_mod.relever(_beta_info, td_val, mcap, tax_info["rate"], archetype == FINANCIAL)
            _beta_pre = bool(_beta_info.get("adjusted"))
            _beta_val = safe_float(_beta_info["value"]) if _beta_info.get("bottom_up") else safe_float(financials.beta)
            result["key_metrics"]["beta"] = _beta_val
            # F9 · R2 (revisión externa de NU): una sola beta en todas las capas, la que entra en el Ke (la propia con
            # Blume; la de la industria tal cual). Antes las alertas leían la de Yahoo de `ratios`, anterior a la tabla
            # regional y al reapalancamiento (NU «Perfil defensivo — Beta 0.40» con un Ke de β 0,60). `beta` sigue
            # siendo la entrada del CAPM (bruta si es la propia).
            _beta_ke = safe_float(adjusted_beta(_beta_val, _beta_pre)) if _beta_val is not None else None
            result["key_metrics"]["beta_ke"] = ratios["beta"] = result["ratios"]["beta"] = fin_dict["beta"] = _beta_ke
            fin_dict["beta_source"] = result["key_metrics"]["beta_source"] = _beta_info.get("source")
            fin_dict["beta_r2"] = result["key_metrics"]["beta_r2"] = (
                safe_float((_beta_info.get("own") or {}).get("r2")) if _beta_info.get("source") == "propia" else None)
            # ── F13 · paso 2: normalización de ganancias ANTES del coste de capital ──
            # Ítems del MISMO periodo que el beneficio: TTM (suma de 4 trimestres) si el beneficio es TTM; si no, el
            # último FY. El rating sintético usa el EBIT normalizado (sin los cargos que la normalización quita del
            # operativo); el bloque de la etapa 7 (más abajo) usa este mismo `_norm`.
            _norm, _norm_err, _rating_ebit = None, None, None
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
                elif _tinfo.get("basis") == "ttm_edgar":
                    # Fase 6: beneficio de doce meses de SEC EDGAR (corte posterior al ejercicio). Las partidas
                    # inusuales de los estados son del ejercicio: de otro periodo, no se aplican.
                    _rows = {}
                    _basis = f"TTM a {_tinfo.get('cut')} (SEC EDGAR; sin desglose de partidas inusuales del periodo)"
                    _qn = None
                else:
                    _rows = dict(_stmts.get("unusual_fy0") or {})
                    _basis = f"FY{(_stmts.get('inc_years') or ['?'])[0]} (sin TTM)"
                    _qn = None
                _pt, _tx = (_stmts.get("pretax_income") or [None])[0], (_stmts.get("tax_provision") or [None])[0]
                _t_fy = (_tx / _pt) if (_pt and _tx is not None and _pt > 0) else None
                # F10 · N1: piezas de la coherencia del beneficio con la operación, del mismo periodo que el beneficio
                # (TTM: los 4 trimestres; si no, el último ejercicio). Sin ellas (TTM de EDGAR sin desglose) o donde el
                # margen operativo no aplica (bancos, aseguradoras, REIT), no se mira.
                _coh = None
                if not not_applicable(archetype, "operating_margin"):
                    if _qn is not None:
                        def _q4(row, required=True):
                            v = (_q.get(row) or [])[:TTM_QUARTERS]
                            if len(v) == TTM_QUARTERS and all(x is not None for x in v):
                                return sum(v)
                            return None if required else (sum(x for x in v if x is not None) if any(
                                x is not None for x in v) else None)
                        # F10 · margen operativo con una sola verdad: el operativo de las piezas es el del corte (el
                        # que se enseña y puntúa: el EBIT que presenta el emisor en EDGAR); la fila trimestral de Yahoo,
                        # solo de respaldo declarado (FIX: 0,99 B$ de EDGAR frente a 2,09 B$ de Yahoo)
                        _opp = pieces_operating_income(
                            oi_val, ((yinfo.get("_as_of") or {}).get("fields") or {}).get("operatingIncome"),
                            (_q.get("dates") or [None])[0], _q4("Operating Income"))
                        _coh = {"operating_income": _opp["value"], "revenue": _q4("Total Revenue"),
                                "pretax": _q4("Pretax Income"), "tax": _q4("Tax Provision"),
                                "net_interest": _q4("Net Non Operating Interest Income Expense", False),
                                "equity_income": _q4("Earnings From Equity Interest", False),
                                "equity_income_net_of_tax": _q4("Earnings From Equity Interest Net Of Tax", False),
                                "minority_interests": _q4("Minority Interests", False),
                                "operating_income_source": _opp["source"],
                                "named_gains": safe_float((yinfo.get("_named_gains") or {}).get("value")),
                                "operating_income_yahoo_quarterly": _opp["yahoo_quarterly"]}
                    elif _tinfo.get("basis") != "ttm_edgar":
                        def _fy0(key):
                            return safe_float((_stmts.get(key) or [None])[0])
                        _coh = {"operating_income": _fy0("operating_income"), "revenue": _fy0("revenue"),
                                "pretax": _fy0("pretax_income"), "tax": _fy0("tax_provision"),
                                "net_interest": _fy0("nonop_interest"), "equity_income": _fy0("equity_interest"),
                                "equity_income_net_of_tax": _fy0("equity_interest_net_of_tax"),
                                "minority_interests": _fy0("minority_interests"),
                                "operating_income_source": "último ejercicio (el EBIT que presenta el emisor si EDGAR "
                                                           "lo tiene)",
                                "named_gains": safe_float((yinfo.get("_named_gains") or {}).get("value"))}
                    # F10 · N1b: el tipo normalizado mira también los últimos ejercicios (los del periodo, si es el
                    # ejercicio, no se repiten)
                    if _coh is not None:
                        _hist = list(zip(_stmts.get("pretax_income") or [], _stmts.get("tax_provision") or []))
                        _coh["tax_history"] = _hist if _qn is not None else _hist[1:]
                # F10 · N1b: discontinuadas del mismo periodo que el beneficio (el normalizado parte del continuado),
                # con el total del periodo (beneficio con discontinuadas) para saber si el beneficio usado las lleva: el
                # de Yahoo no siempre es el del estado del periodo (UL en vivo: 6,48 B frente a 9,47 B del FY2025, de
                # los que 3,80 B son discontinuadas): restarlas otra vez las contaría dos veces.
                if _qn is not None:
                    _dq = [x for x in (_q.get("Net Income Discontinuous Operations") or [])[:TTM_QUARTERS]
                           if x is not None]
                    _tq = (_q.get("Net Income") or [])[:TTM_QUARTERS]
                    _disc = {"value": sum(_dq), "source": "Yahoo: Net Income Discontinuous Operations (4 trimestres)",
                             "period_total": (sum(_tq) if len(_tq) == TTM_QUARTERS and None not in _tq else None)} \
                        if _dq else None
                elif _tinfo.get("basis") == "ttm_edgar":
                    _de = _tinfo.get("discontinued")
                    # el beneficio del corte es el de EDGAR (NetIncomeLoss y equivalentes): lleva las discontinuadas
                    _disc = {"value": _de["value"], "source": f"SEC EDGAR ({_de['concept']}): {_de['how']}",
                             "period_total": _ni} if _de else None
                else:
                    _dfy = safe_float((_stmts.get("net_income_discontinued") or [None])[0])
                    _disc = {"value": _dfy, "source": "Yahoo: Net Income Discontinuous Operations (ejercicio)",
                             "period_total": safe_float((_stmts.get("net_income_common") or [None])[0])} \
                        if _dfy else None
                _norm = normalize_earnings(net_income=_ni, explicit_rows=_rows, quarterly=_qn, basis=_basis,
                                           tax_rate_fallback=_t_fy, annual_rows=_stmts.get("unusual_fy") or {},
                                           investment_gains=(yinfo.get("_investment_gains") if _has_yahoo else None),
                                           coherence_parts=_coh, discontinued=_disc,
                                           edgar_charges=(yinfo.get("_edgar_charges") if _has_yahoo else None))
                if _coh is not None and not (_norm.get("structural_net") or 0.0):
                    from normalize import operating as _operating_pre
                    _oi_r, _rev_r_ = ((_om_fy["operating_income"], _om_fy["revenue"]) if _om_fy is not None
                                      else (oi_val, safe_float(rev_val)))
                    if _oi_r is not None:
                        _rating_ebit = _operating_pre(
                            _oi_r, _rev_r_, _norm["items"], pretax=_coh.get("pretax"),
                            net_interest=_coh.get("net_interest"), equity_income=_coh.get("equity_income"),
                            known_inside=((yinfo.get("_edgar_charges") or {}).get("charges") or 0.0)
                            if _has_yahoo else 0.0).get("normalized")
            except Exception as e:
                _norm_err = e
            # F13 · paso 2: la cobertura con la que se busca el rating sintético (Kd y, por su piso, el Ke)
            from cost_of_capital import rating_coverage as _rating_coverage
            _rcov = _rating_coverage(
                coverage=safe_float(interest_cov), state=ic_state, ebit=oi_val, ebit_normalized=safe_float(_rating_ebit),
                interest=ie_val, reit=archetype == REIT, ebitda=safe_float(ratios.get("ebitda")),
                operating_cash_flow=safe_float(getattr(financials, "operating_cash_flow", None)),
                depreciation=safe_float(getattr(financials, "depreciation", None)), market_cap=mcap,
                state_fn=lambda c, e: interest_coverage_state(c, r("net_debt"), ebit=e, net_interest_income=nii_sign))
            _kd_info = None if archetype == FINANCIAL else cost_of_debt(
                rf_info["value"], mcap, td_val, safe_float(_rcov["coverage"]), _rcov["state"])
            ke_info = equity_cost(_beta_val if _beta_val is not None else cfg("valuation.capm.default_beta"),
                                  rf_info["value"], _kd_info and _kd_info["value"], _beta_pre and _beta_val is not None,
                                  crp=crp_info["crp"])
            result["cost_of_equity"] = {"value": safe_float(ke_info["value"]), "capm": safe_float(ke_info["capm"]),
                                        "crp": safe_float(ke_info.get("crp")),
                                        "floor": ke_info["floor"], "floors": ke_info["floors"],
                                        "kd": safe_float(_kd_info["value"]) if _kd_info else None,
                                        "rf": rf_info["value"], "erp": rf_info["erp"], "as_of": rf_info["as_of"],
                                        "shift": ke_info.get("shift")}
            # Métricas de la rama (P/B justificado, EV/Ventas, normalizados de ciclo…)
            result["sbc"] = {k: (safe_float(v) if isinstance(v, float) else v) for k, v in sbc_info.items()}
            # Fase 3 (T6): lecturas de calidad que informan (no puntúan): DuPont, margen FCF con tendencia, regla de
            # 40 (GROWTH_PROFITABLE), SBC como coste y cobertura de intereses ampliada (lib/quality_readings).
            try:
                import quality_readings as qr
                _qr = {}
                if archetype not in (FINANCIAL, REIT):
                    _qr["dupont"] = qr.dupont(_stmts_g)
                    _qr["fcf_margin"] = qr.fcf_margin_trend(_stmts_g)
                    _qr["sbc_cost"] = qr.sbc_cost(sbc_info)
                if archetype != FINANCIAL:
                    _qr["coverage"] = qr.interest_coverage(
                        _stmts_g, safe_float(financials.operating_income),
                        safe_float(result["key_metrics"].get("ebitda")), safe_float(financials.interest_expense),
                        ffo_ttm=safe_float(result["key_metrics"].get("ffo")) if archetype == REIT else None,
                        period=numfmt.period(fin_dict.get("ttm_basis")))
                result["quality_readings"] = {k: v for k, v in _qr.items() if v}
                fin_dict["dupont"] = _qr.get("dupont")      # F10 · N6: de dónde sale el ROE (alertas)
            except Exception as e:
                _sin_dato("lecturas_calidad", e)
            # Etapa 9b: histórico anual (dato bruto, pestaña Histórico de la web).
            result["yearly_financials"] = [{k: (safe_float(v) if isinstance(v, float) else v) for k, v in r_.items()}
                                           for r_ in archetype_metrics.yearly_financials(_stmts, archetype)]
            # Fase 2b (T6): la beta del sector (Damodaran) entra ya ajustada; la propia y la de la fuente, con Blume.
            archetype_values = archetype_metrics.compute(
                archetype, _stmts, result["key_metrics"], beta=_beta_val,
                revenue_cagr_3y=classification["inputs"].get("revenue_cagr_3y"), rf=rf_info["value"],
                revenue_cagr_3y_reason=classification["inputs"].get("revenue_cagr_3y_reason"),
                revenue_cagr_3y_bound=classification["inputs"].get("revenue_cagr_3y_bound"),
                sbc=sbc_info, beta_preadjusted=_beta_pre, subtype=classification.get("subtype"),
                history_fy=(yinfo.get("_history_fy") if _has_yahoo else None),
                reit_ffo=_reit_ffo_res, ke=ke_info["value"],
                ordinary=yinfo.get("_ordinary") if _has_yahoo else None)   # F9 · R3: balance del corte (P/B y P/TBV)
            if growth_currency.converted(_cur_info):
                archetype_values.update(archetype_metrics.growth_values(archetype, _stmts_g))
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
            import names as _names
            import industry_bench as _ibench
            _bench_sel = _select_benchmark(mapped_sector, archetype, profile.sector, profile.industry,
                                           profile.country, symbol,
                                           ((yinfo.get("_edgar") or {}).get("title") if _has_yahoo else None),
                                           # F10 · N2: sus cifras a la fecha del conjunto, para quitarla de su referencia
                                           # F11 · T1: con la capitalización de hoy, para estimar su peso sin ellas
                                           dict(yinfo.get("_at_dataset_date") or {},
                                                market_cap_now=safe_float(result["key_metrics"].get("market_cap")))
                                           if _has_yahoo else None,
                                           _names.company(profile.name) or symbol)
            # Un solo benchmark por análisis (etapa 9a): medianas de múltiplos, umbrales del
            # score (ROE, ROA, D/E, márgenes), alertas y PDF leen la misma clave.
            result["benchmark"] = _bench_sel
            score_sector = _bench_sel["thresholds_key"]
            _sector_bench = _bench_sel["values"]
            # F9 · R1b: P/B justificado en dos etapas si el valor en libros crece muy por encima de g. F10 · N2b
            # (decisión del PM): el ROE estable converge a la industria GLOBAL sin la empresa; sin ella, al de su
            # referencia regional, declarado.
            if archetype == FINANCIAL and result.get("archetype_metrics"):
                _ind_name = ((_bench_sel.get("industry") or {}).get("damodaran"))
                _groe = _ibench.global_roe(_ind_name, symbol,
                                           ((yinfo.get("_edgar") or {}).get("title") if _has_yahoo else None),
                                           profile.country,
                                           dict(yinfo.get("_at_dataset_date") or {},     # F11 · T1, como arriba
                                                market_cap_now=safe_float(result["key_metrics"].get("market_cap")))
                                           if _has_yahoo else None,
                                           _names.company(profile.name) or symbol)
                _ts = archetype_metrics.apply_two_stage(
                    result["archetype_metrics"], _groe["value"] if _groe else _sector_bench.get("roe"),
                    safe_float(_km.get("payout_ratio")), safe_float(_km.get("dividend_yield")),
                    roe_source=_groe["text"] if _groe else "su industria de referencia regional (sin la global)",
                    # F11 · T2: de qué conjunto sale el ROE estable (para la independencia de la convergencia)
                    roe_anchor=(_groe or {}).get("anchor") or _ibench.reference_anchor(
                        (_bench_sel.get("industry") or {}).get("damodaran"),
                        (_bench_sel.get("industry") or {}).get("region"),
                        (_bench_sel.get("industry") or {}).get("self_exclusion")))
                result["archetype_metrics"].update(_ts)
                archetype_values.update(_ts)          # el score lee archetype_values: el mismo justificado
            fin_dict["sector_pe"] = _sector_bench.get("pe")
            # Etapa 11b: referencia del Forward P/E (la del sector; si no hay, la del P/E).
            fin_dict["sector_forward_pe"] = _sector_bench.get("forward_pe") or _sector_bench.get("pe")
            fin_dict["sector_ev_ebitda"] = _sector_bench.get("ev_ebitda")
            # F8 · E9: márgenes de la referencia (la industria de Damodaran) para leer los de la empresa frente a ellos.
            fin_dict["industry_operating_margin"] = _sector_bench.get("operating_margin")
            fin_dict["industry_net_margin"] = _sector_bench.get("net_margin")
            # F10 · B3: las alertas de ROE y margen bruto leen la misma referencia que su fila
            fin_dict["industry_roe"] = _sector_bench.get("roe")
            fin_dict["industry_gross_margin"] = _sector_bench.get("gross_margin")
            fin_dict["benchmark_profile"] = _bench_sel["profile"]
            fin_dict["benchmark_ref"] = _bench_sel["ref"]     # fase 4/7: "de su industria", "del mercado (…)"…
            fin_dict["benchmark_short"] = _bench_sel["short"]

            # Fase 3 (T6, F3_DISENO §5): lecturas por modelo de negocio (circulante estructural, Altman referencial,
            # avisos del Piotroski); las leen el score, las alertas y el informe.
            import business_model as _bmod
            # F8 · E10: SIC del emisor en SEC EDGAR (modelo de Altman y exclusiones).
            _edgar_profile = (((yinfo.get("_edgar") or {}).get("profile") or {}) if _has_yahoo else {})
            _alt_excl = altman_excluded(_edgar_profile.get("sic"))
            # F8 · E10 (decisión del PM): financiera cautiva consolidada → Altman referencial. Una sola detección con la
            # deuda de la cautiva del XBRL (lib/debt.py) y, si no la hay, los segmentos de negocio del último informe
            # anual (lib/segments.build, en caché por filing). Solo si el Altman aplica.
            _captive = None
            if _has_yahoo and not (not_applicable(archetype, "altman") or _alt_excl):
                _ed_cap = (yinfo.get("_edgar") or {}).get("captive")
                _segs = None
                if (_ed_cap or {}).get("status") != "ok":
                    try:
                        import segments as _segments
                        _segs = _segments.build(symbol)
                    except Exception as e:  # noqa: BLE001 — sin segmentos: opción (a), con el límite declarado
                        logger.warning(f"{symbol}: segmentos para la cautiva: {e}")
                _captive = _bmod.captive_finance(_segs, _ed_cap)
            _ind_ref = _bmod.altman_referential(profile.industry)
            _cap_ref = bool(_captive and _captive["detected"])
            _cr_now = safe_float(result["key_metrics"].get("current_ratio"))
            _cr_ctx = _bmod.current_ratio_context(profile.industry, _stmts, _cr_now)
            _bm_ctx = {"current_ratio": _cr_ctx,
                       "altman_referential": _ind_ref or _cap_ref,
                       "altman_referential_reason": (_bmod.ALTMAN_REF_CAPTIVE if _cap_ref else
                                                     _bmod.ALTMAN_REF_INDUSTRY if _ind_ref else None),
                       "captive_finance": _captive,
                       "piotroski_caveat": _bmod.piotroski_caveat(_cr_ctx, _cr_now),
                       "sic": _edgar_profile.get("sic"),
                       "altman_excluded": _alt_excl}
            fin_dict["business_model"] = _bm_ctx
            result["business_model"] = _bm_ctx
            # F9 · R6: riesgo de crédito de un banco (lib/credit_risk.py, del XBRL de la SEC). Informa; no puntúa.
            if archetype == FINANCIAL and classification.get("subtype") == "banco":
                import credit_risk as _credit
                result["credit_risk"] = ((yinfo.get("_credit") if _has_yahoo else None)
                                         or _credit.measure(None))
                fin_dict["credit_risk"] = result["credit_risk"]       # la alerta de crédito no medido

            # Crecimiento a 3 años para Crecimiento (etapa 9a): CAGR real de los 4
            # ejercicios anuales de los estados (historical_metrics.growth_rate, con la
            # regla de base anómala), no el interanual de Yahoo (revenueGrowth /
            # earningsGrowth, que comparan un trimestre con el del año anterior). Sin 4
            # ejercicios o con valores <= 0 en los extremos: sin dato con motivo, nunca
            # el interanual con la etiqueta de 3 años.
            # F10 · crecimiento desde una base anómala (regla general, historical_metrics.robust_growth): con año base
            # anómalo y una regresión que solo tiene los ejercicios de la ventana, la serie larga de EDGAR (≥
            # thresholds.growth.long_years ejercicios hasta el último) o, sin ella, no significativo con su motivo.
            _hfy = (yinfo.get("_history_fy") if _has_yahoo else None) or {}
            # F10 (PM, 29-oct): la cota de cada tasa no significativa (growth_rate: desde una base anómala baja, cota
            # superior), por su motivo: la usa una puntuación solo si el motivo que le llega es el de esa tasa.
            _bounds: dict = {}

            def _rg(*a, **k):
                r = robust_growth(*a, **k)
                if r.get("not_significant") and r.get("bound"):
                    _bounds[r["reason"]] = r["bound"]
                return r
            _g_end = (_stmts_g.get("inc_ends") or [None])[0]
            _GM = ("method", "anomalous_base", "note", "robust", "not_significant", "source", "window", "years_used",
                   "bound", "capped", "value_uncapped")
            _rev_r = _rg(_stmts_g.get("revenue") or [], 3, what="ingresos", strict_ends_only=True,
                         long=_hfy.get("revenue"), end=_g_end)
            fin_dict["revenue_cagr_3y"] = _rev_r["value"]
            fin_dict["revenue_growth_reason"] = _rev_r["reason"]
            # F9 · R3: con año base anómalo es la regresión log-lineal, no el CAGR de punta a punta: el informe lo dice
            fin_dict["revenue_cagr_3y_method"] = {k: _rev_r.get(k) for k in _GM}
            # Revisión F3 (hallazgo 6): ingresos por acción a 3 años para el retorno total de la madura de dividendo alto.
            # Acciones del balance casadas con los ejercicios de resultados por fecha (revisión F4, hallazgo 5).
            _sh_inc = on_statement(_stmts_g, "ordinary_shares", "bs", "inc")
            fin_dict["revenue_ps_cagr_3y"] = _rg(per_share(_stmts_g.get("revenue") or [], _sh_inc), 3,
                                                 what="ingresos por acción", strict_ends_only=True)["value"]
            _eps_series = _stmts_g.get("diluted_eps") or per_share(_stmts_g.get("net_income") or [],
                                                                    _stmts_g.get("ordinary_shares") or [])
            # La serie larga del BPA es la del beneficio neto de EDGAR, solo con las acciones estables (el BPA crece como
            # el beneficio): el BPA de EDGAR de ejercicios antiguos no está ajustado por los splits posteriores.
            _eps_long_ok = per_share_basis(_stmts.get("ordinary_shares") or [])["basis"] == "agregado"
            _eps_r = _rg(_eps_series, 3, what="BPA", long=_hfy.get("net_income") if _eps_long_ok else None,
                         end=_g_end)
            if _eps_r.get("method") == "log_lineal_edgar":
                _eps_r["note"] += " (beneficio neto, con las acciones estables: el BPA crece como el beneficio)"
            elif _eps_r.get("not_significant") and not _eps_long_ok:
                _eps_r["reason"] = _eps_r["reason"].replace(
                    "sin serie larga de EDGAR", "las acciones cambian y EDGAR no trae un BPA comparable de más ejercicios")
            fin_dict["eps_cagr_3y"] = _eps_r["value"]
            fin_dict["eps_growth_reason"] = _eps_r["reason"]
            fin_dict["eps_cagr_3y_method"] = {k: _eps_r.get(k) for k in _GM}
            # F12 · D2: ¿el año base de esa ventana está deprimido frente a la historia larga? Entonces no respalda el
            # forward. `for_value`: solo vale para esta tasa (el perímetro o el ciclo medio la sustituyen más abajo).
            fin_dict["eps_growth_backing"] = {**backing_base(_eps_series, 3, long=_hfy.get("net_income") if _eps_long_ok
                                                             else None, end=_g_end), "for_value": _eps_r["value"]}
            # F11 · F3: el crecimiento del BPA del último ejercicio, para el tope de credibilidad del forward.
            _e0, _e1 = (list(_eps_series) + [None, None])[:2]
            fin_dict["eps_growth_last_fy"] = ((_e0 / _e1 - 1) if (_e0 is not None and _e1 is not None and _e0 > 0
                                                                 and _e1 > 0) else None)
            # F10: con la serie larga de EDGAR, la cifra dice de qué ejercicios sale (no son los 3 años de la ventana)
            if _rev_r.get("method") == "log_lineal_edgar":
                fin_dict["revenue_growth_note"] = _rev_r["note"]
            if _eps_r.get("method") == "log_lineal_edgar":
                fin_dict["eps_growth_note"] = _eps_r["note"]
                fin_dict["eps_cagr_window"] = _eps_r["window"]
            # Fase 3 (T5, F3_DISENO §4): cambio de perímetro dentro de la ventana del CAGR (UL: escisión de los
            # helados). El crecimiento se mide sobre el perímetro homogéneo: los ejercicios del perímetro vigente
            # (reexpresados) y, en el BPA, el beneficio de las operaciones continuadas. Con menos de 2 años
            # homogéneos, "no comparable" y no puntúa.
            _per = (yinfo.get("_perimeter") or {}) if _has_yahoo else {}
            if _per.get("mixed_cagr"):
                # Revisión de código F3 (hallazgo 7): se casa por la fecha de cierre, no por la posición: la serie del
                # perímetro se salta los ejercicios sin grupo en EDGAR. Un ejercicio sin casar no prueba el perímetro
                # vigente y cierra el tramo homogéneo.
                _basis_by_end = {x.get("fy_end"): x.get("basis") for x in _per.get("series") or []}
                _ends = _stmts_g.get("inc_ends") or []
                _n = 0
                while _n < len(_ends) and _basis_by_end.get(_ends[_n]) == "vigente":
                    _n += 1
                _yrs = _n - 1
                if _yrs >= cfg("thresholds.growth.perimeter_min_years"):
                    _rev_r = _rg((_stmts_g.get("revenue") or [])[:_n], _yrs, what="ingresos",
                               strict_ends_only=True)
                    # Revisión F4 (hallazgo 2): el retorno total por acción, en el mismo perímetro homogéneo.
                    fin_dict["revenue_ps_cagr_3y"] = _rg(
                        per_share((_stmts_g.get("revenue") or [])[:_n], _sh_inc[:_n]), _yrs,
                        what="ingresos por acción", strict_ends_only=True)["value"]
                    fin_dict["revenue_ps_cagr_years"] = _yrs
                    _ni = _stmts_g.get("net_income") or []
                    _disc = _stmts_g.get("net_income_discontinued") or []
                    _cont = [(n - (_disc[i] if i < len(_disc) and _disc[i] else 0.0)) if n is not None else None
                             for i, n in enumerate(_ni[:_n])]
                    _eps_r = _rg(per_share(_cont, (_stmts_g.get("ordinary_shares") or [])[:_n]), _yrs,
                               what="BPA de operaciones continuadas")
                    _why = (f"perímetro homogéneo: {_yrs} años en el perímetro vigente (ejercicios reexpresados tras "
                            "el cambio de perímetro), no el CAGR a 3 años que cruza el cambio")
                    fin_dict["revenue_growth_note"] = _why
                    fin_dict["eps_growth_note"] = _why + "; BPA de operaciones continuadas"
                else:
                    fin_dict["revenue_ps_cagr_3y"] = None
                    _rev_r = {"value": None, "reason": "no comparable: el cambio de perímetro deja menos de 2 años "
                                                         "homogéneos; no puntúa"}
                    _eps_r = {"value": None, "reason": _rev_r["reason"]}
                fin_dict["revenue_cagr_3y"] = _rev_r["value"]
                fin_dict["revenue_growth_reason"] = _rev_r["reason"]
                fin_dict["eps_cagr_3y"] = _eps_r["value"]
                fin_dict["eps_growth_reason"] = _eps_r["reason"]
                result["growth_perimeter"] = {"homogeneous_years": max(_yrs, 0), "applied": True,
                                              "note": fin_dict.get("revenue_growth_note") or _rev_r["reason"]}
            # V7 (M2): la ventana de los CAGR a 3 años, para que cada texto diga su periodo ("FY2022–FY2025").
            _gy = _stmts_g.get("inc_years") or []
            _gn_y = fin_dict.get("revenue_ps_cagr_years") or 3
            # F11 · T4: acotada por la tasa de punta a punta, la cifra que puntúa ES el CAGR de la ventana de 3 años.
            _regr = _rev_r.get("method") == "log_lineal_edgar" and not _rev_r.get("capped")
            fin_dict["revenue_cagr_window"] = (_rev_r.get("window") if _regr else
                                               f"FY{_gy[_gn_y]}–FY{_gy[0]}"
                                               if len(_gy) > _gn_y and fin_dict.get("revenue_cagr_3y") is not None
                                               else None)
            # F11 · T4: el rótulo de la puntuación dice la ventana real cuando no es la de 3 años.
            if _regr and fin_dict.get("revenue_cagr_3y") is not None:
                fin_dict["revenue_cagr_window_label"] = f"regresión {_rev_r.get('window')}"
            if _rev_r.get("note") or _eps_r.get("note"):
                fin_dict["growth_cagr_notes"] = {k: r["note"] for k, r in (("ingresos", _rev_r), ("BPA", _eps_r))
                                                 if r.get("note")}
            # CAGR del FCF a 3 años con los 4 ejercicios anuales de los estados
            # (etapa 5). Indefinido -> sin dato con motivo, nunca un número.
            if fin_dict.get("fcf_cagr_3y") is None:
                _fcf_series = _stmts_g.get("free_cash_flow") if _has_yahoo else None
                _fcf_r = _rg(_fcf_series, 3, what="FCF", long=edgar_fcf(_hfy), end=_g_end)   # F10
                fin_dict["fcf_cagr_3y"] = _fcf_r["value"]
                fin_dict["fcf_cagr_3y_reason"] = _fcf_r["reason"]
                fin_dict["fcf_cagr_3y_method"] = {k: _fcf_r.get(k) for k in _GM}

            # Crecimiento por rama (etapa 6).
            # Fase 3 (T5, F3_DISENO §4): con 10+ ejercicios de EDGAR, ciclo medio de pico a pico (sustituye a la cota).
            _mc = None
            if archetype == CYCLICAL and _has_yahoo and yinfo.get("_history_fy"):
                import cyclicality as _cyc
                _mc = _cyc.mid_cycle_growth(yinfo["_history_fy"])
                result["mid_cycle"] = _mc
            if archetype == CYCLICAL and _mc is not None:
                _span = f"{_mc['from'][:4]}–{_mc['to'][:4]}, {_mc['years']} años"
                fin_dict["revenue_cagr_3y"] = _mc["cagr"]
                fin_dict["revenue_growth_note"] = (
                    f"ciclo medio de pico a pico ({_span}; historia de EDGAR"
                    + (", por acción" if _mc["basis"] == "por_accion" else "") + "): la tendencia del ciclo completo")
                fin_dict["eps_cagr_3y"] = _mc["eps_cagr"]
                fin_dict["eps_growth_reason"] = _mc["eps_reason"] if _mc["eps_cagr"] is None else None
                if _mc["eps_cagr"] is not None:
                    # F8: entre las medias de las dos mitades del ciclo, no en los picos de ingresos
                    _hv = _mc["eps_halves"]
                    fin_dict["eps_growth_note"] = (f"BPA de ciclo medio: media de {_hv['first'][0][:4]}–"
                                                   f"{_hv['first'][1][:4]} frente a la de {_hv['second'][0][:4]}–"
                                                   f"{_hv['second'][1][:4]}, pérdidas incluidas")
                fin_dict["fcf_cagr_3y"] = None
            elif archetype == CYCLICAL:
                # Crecimiento normalizado de ciclo medio (promedio interanual de los
                # ejercicios disponibles, acotado) en lugar del interanual de un solo
                # tramo; la tendencia del FCF de un tramo no aplica (RECON §7.9, §7.10).
                # Fase 3 (T5): solo con historia corta (sin dos picos del ciclo en EDGAR), y dicho.
                _gn = archetype_values.get("revenue_growth_normalized")
                if _gn is not None:
                    fin_dict["revenue_cagr_3y"] = _gn
                    _lo, _hi = cfg("valuation.archetypes.cyclical_growth_bounds")
                    fin_dict["revenue_growth_note"] = (
                        f"normalizado de ciclo medio: promedio interanual de {archetype_values['cycle_years']} "
                        f"ejercicios, acotado a [{_lo:.0%}, {_hi:.0%}] (salvaguarda de historia corta: sin dos picos "
                        "del ciclo en EDGAR)"
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
                    "FFO por acción (FFO según Nareit = beneficio neto + D&A − ventas de inmuebles + deterioros; acciones en "
                    "circulación de cada ejercicio)"
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
                                fcf_cagr=fin_dict.get("fcf_cagr_3y_method"),
                                revenue_cagr=fin_dict.get("revenue_cagr_3y_method"),
                                eps_cagr=fin_dict.get("eps_cagr_3y_method"))   # F10: el método del BPA, a la vista
            if archetype == REIT:
                _fps = _rg(per_share(_stmts_g.get("free_cash_flow") or [],
                                     _stmts_g.get("ordinary_shares") or []), 3, what="FCF por acción")
                growth_basis["fcf_cagr"] = {k: _fps.get(k) for k in _GM}
                growth_basis.update(basis="por_accion", applied_to=["FFO", "FCF"],
                                    reason="REIT: crecimiento por acción siempre (FFO y FCF por acción); "
                                           + _gb["reason"])
            elif _gb["basis"] == "por_accion":
                _s = _gb["shares_cagr_3y"]
                _g = fin_dict.get("revenue_cagr_3y")
                # El ciclo medio ya decide su base con las acciones de EDGAR de su propia ventana de pico a pico
                # (lib/cyclicality.mid_cycle_growth): no se vuelve a dividir por las de Yahoo a 3 años.
                if _g is not None and _mc is None:
                    fin_dict["revenue_cagr_3y"] = (1 + _g) / (1 + _s) - 1
                    fin_dict["revenue_cagr_per_share"] = True
                    fin_dict["revenue_growth_note"] = "; ".join(filter(None, [
                        fin_dict.get("revenue_growth_note"),
                        f"por acción: {_g:+.1%} agregado ajustado por las acciones ({_s:+.1%} anual)"]))
                    growth_basis["applied_to"].append("ingresos")
                if fin_dict.get("fcf_cagr_3y") is not None or fin_dict.get("fcf_cagr_3y_reason"):
                    _fps = _rg(per_share(_stmts_g.get("free_cash_flow") or [],
                                         _stmts_g.get("ordinary_shares") or []), 3, what="FCF por acción")
                    fin_dict["fcf_cagr_3y"] = _fps["value"]
                    fin_dict["fcf_cagr_3y_reason"] = _fps["reason"]
                    growth_basis["fcf_cagr"] = {k: _fps.get(k) for k in _GM}
                    growth_basis["applied_to"].append("FCF")
            if _mc is not None and _mc["basis"] == "por_accion" and "ingresos" not in growth_basis["applied_to"]:
                growth_basis["applied_to"].append("ingresos")
            # Etapa 9a: en GROWTH_PRE_PROFIT el crecimiento del FCF es el de FCF − SBC (misma base
            # por acción si aplica). Sin la serie de SBC: sin dato con motivo, no el FCF bruto.
            if archetype == GROWTH_PRE_PROFIT:
                _f, _s = _stmts_g.get("free_cash_flow") or [], _stmts_g.get("stock_based_compensation") or []
                if not _s:
                    fin_dict["fcf_cagr_3y"] = None
                    fin_dict["fcf_cagr_3y_reason"] = ("sin fila Stock Based Compensation: el crecimiento del FCF se "
                                                      "mide sobre FCF − SBC")
                else:
                    _adj = [(a - b) if (a is not None and b is not None) else None for a, b in zip(_f, _s)]
                    if "FCF" in growth_basis["applied_to"]:
                        _adj = per_share(_adj, _stmts_g.get("ordinary_shares") or [])
                    _ar = _rg(_adj, 3, what="FCF − SBC")
                    fin_dict["fcf_cagr_3y"] = _ar["value"]
                    fin_dict["fcf_cagr_3y_reason"] = _ar["reason"]
                    growth_basis["fcf_cagr"] = dict({k: _ar.get(k) for k in _GM},
                                                    basis="FCF − SBC")
            # Etapa 9a (regla general): negativo sostenido -> peor tramo, no "sin dato".
            fin_dict["fcf_cagr_3y_sustained_negative"] = is_sustained_negative(fin_dict.get("fcf_cagr_3y_reason"))
            # V7 (M2): ciclo medio, normalizada o FFO del REIT no son la ventana de los estados a 3 años.
            if _mc is not None or archetype == REIT or (
                    archetype == CYCLICAL and archetype_values.get("revenue_growth_normalized") is not None):
                fin_dict["revenue_cagr_window"] = None
                fin_dict["eps_cagr_window"] = None
            if archetype == CYCLICAL:     # el BPA de ciclo medio no es el de la serie larga
                fin_dict["eps_cagr_window"] = None
            if fin_dict.get("revenue_cagr_window"):
                growth_basis["revenue_window"] = fin_dict["revenue_cagr_window"]
            if fin_dict.get("eps_cagr_window"):
                growth_basis["eps_window"] = fin_dict["eps_cagr_window"]     # F10: la serie larga del BPA
            result["growth_basis"] = {k: (safe_float(v) if isinstance(v, float) else v)
                                      for k, v in growth_basis.items()}
            for _k, _rk in (("revenue_cagr_3y", "revenue_growth_reason"), ("eps_cagr_3y", "eps_growth_reason"),
                            ("fcf_cagr_3y", "fcf_cagr_3y_reason")):
                fin_dict[f"{_k}_bound"] = (_bounds.get(fin_dict.get(_rk)) if fin_dict.get(_k) is None else None)
            # Fase 3 (T6, §1.3): PEG de GROWTH_PROFITABLE a varios años: P/E ÷ CAGR del BPA a 3 años (por acción), no
            # el crecimiento de un año ni el de consenso. Lo leen el score, la tabla y el informe.
            # Revisión de COST (hallazgo 2, regla general): en todos los arquetipos en que aplica, el PEG usa el crecimiento
            # del BPA que el informe muestra y nombra (su fila de Crecimiento); sin él, no significativo con su motivo.
            # COST: el PEG de Yahoo (4,99) suponía un crecimiento de consenso que el informe no mostraba.
            if not not_applicable(archetype, "peg"):
                _pe_g = safe_float(ratios.get("pe"))
                _e3 = safe_float(fin_dict.get("eps_cagr_3y"))
                # el ciclo medio o el normalizado del cíclico no son la serie a 3 años del método
                _em = (fin_dict.get("eps_cagr_3y_method") or {}) if archetype != CYCLICAL else {}
                # F10 · N3 (revisión del informe de NVIDIA): el PEG usa el crecimiento del BPA con el mismo método que los
                # ingresos (historical_metrics.growth_rate: regresión log-lineal con año base anómalo). Si el año base es
                # anómalo y la regresión no tiene ejercicios fuera de la ventana con los que diluirlo, no hay una
                # alternativa robusta: PEG no significativo, con su motivo (NVDA: 198 % desde FY2023, PEG 0,14).
                if _em.get("anomalous_base") and not _em.get("robust"):
                    # F10 (regla general, historical_metrics.robust_growth): sin regresión robusta ni serie larga, el BPA
                    # ya es no significativo; el PEG, con él y con el mismo motivo.
                    _peg_ns_base = ("el crecimiento del BPA parte de un año base anómalo ("
                                    + str(_em.get("note") or "").split(";")[0].split(")")[0].split(": ", 1)[-1]
                                    .removeprefix("base anómala (")
                                    + ") y no hay ejercicios fuera de la ventana ni una serie larga con los que "
                                      "estimarlo de forma robusta")
                    ratios["peg"] = result["key_metrics"]["peg"] = None
                    fin_dict["peg_not_significant"] = _peg_ns_base
                    result["peg_basis"] = {"pe": _pe_g, "eps_cagr_3y": _e3,
                                           "note": f"PEG a 3 años no significativo: {_peg_ns_base}"}
                    _peg_would = (_pe_g / (_e3 * cfg("valuation.peg.growth_pct_scale"))
                                  if (_pe_g is not None and _pe_g > 0 and _e3 is not None and _e3 > 0) else None)
                    _id_flags.append({"field": "key_metrics.peg", "rule": "multiplo_no_significativo",
                                      "action": "sin_dato", "old": safe_float(_peg_would), "new": None,
                                      "reason": f"PEG: {_peg_ns_base}"})
                    # F10 (PM, 29-oct): la cota superior del crecimiento da una cota inferior del PEG; puntúa solo si
                    # ya está en el peor tramo, y lo declara.
                    _gb_ = (_em.get("bound") or {}).get("value")
                    if _pe_g is not None and _pe_g > 0 and _gb_ is not None and _gb_ > 0:
                        _pl = _pe_g / (_gb_ * cfg("valuation.peg.growth_pct_scale"))
                        if bound_decides({"value": _pl, "direction": "inferior"},
                                         cfg("thresholds.score.valoracion.peg_bounds"), higher_is_better=False):
                            ratios["peg"] = result["key_metrics"]["peg"] = _pl
                            fin_dict.pop("peg_not_significant", None)
                            result["peg_basis"] = {"pe": _pe_g, "eps_cagr_3y": None, "own": True,
                                                   "bound": {"value": _pl, "direction": "inferior"},
                                                   "note": (f"PEG ≥ {_pl:.2f}: el crecimiento del BPA no es "
                                                            f"significativo, pero su techo ({_gb_:.0%}, la tasa desde "
                                                            "el año anómalo) ya deja el PEG en el tramo más caro")}
                elif _pe_g is not None and _pe_g > 0 and _e3 is not None and _e3 > 0:
                    ratios["peg"] = _pe_g / (_e3 * cfg("valuation.peg.growth_pct_scale"))
                    result["key_metrics"]["peg"] = safe_float(ratios["peg"])
                    result["peg_basis"] = {"pe": _pe_g, "eps_cagr_3y": _e3, "own": True,
                                           "years": (_em.get("years_used") if _em.get("method") == "log_lineal_edgar"
                                                     else None),
                                           "note": (f"PEG: P/E ÷ crecimiento del BPA por regresión log-lineal sobre "
                                                    f"los {_em.get('years_used')} últimos ejercicios de EDGAR "
                                                    f"({_em.get('window')}; el año inicial de la ventana de 3 años es "
                                                    "anómalo)" if _em.get("method") == "log_lineal_edgar" else
                                                    f"PEG: P/E ÷ crecimiento del BPA del informe "
                                                    f"({fin_dict['eps_growth_note']})"
                                                    if archetype == CYCLICAL and fin_dict.get("eps_growth_note") else
                                                    "PEG a 3 años: P/E ÷ CAGR del BPA por acción a 3 años")}
                    if archetype == CYCLICAL:
                        result["peg_basis"]["label"] = "PEG (BPA de ciclo medio)"
                else:
                    _peg_src = safe_float(result["key_metrics"].get("peg"))
                    ratios["peg"] = result["key_metrics"]["peg"] = None
                    if _pe_g is None:
                        result["peg_basis"] = {"pe": _pe_g, "eps_cagr_3y": _e3, "note": "PEG sin dato: sin P/E"}
                    else:
                        # un P/E ≤ 0 (pérdidas) o un crecimiento ≤ 0 o sin dato: no significativo, no «sin dato» (no
                        # cuenta como componente ausente; ECHO perdía el precio por cobertura)
                        _peg_ns_g = ("el P/E es ≤ 0 (pérdidas): el PEG no tiene sentido" if _pe_g <= 0 else
                                     (f"el crecimiento del BPA del informe es ≤ 0 ({_e3:.1%} anual): el PEG no tiene "
                                      "sentido").replace("-", "−") if _e3 is not None else
                                     "el informe no muestra un crecimiento del BPA con el que calcularlo ("
                                     + (fin_dict.get("eps_growth_reason") or "sin dato") + ")")
                        fin_dict["peg_not_significant"] = _peg_ns_g
                        result["peg_basis"] = {"pe": _pe_g, "eps_cagr_3y": _e3,
                                               "note": f"PEG no significativo: {_peg_ns_g}"}
                        _id_flags.append({"field": "key_metrics.peg", "rule": "multiplo_no_significativo",
                                          "action": "sin_dato", "old": _peg_src, "new": None,
                                          "reason": f"PEG: {_peg_ns_g}"})
            # F8 · E4 (auditoría del 26-oct, VZ): el PEG tiene que cuadrar con el crecimiento del BPA que muestra el
            # informe; si no, no es significativo (no puntúa ni se lee) y el motivo queda en la validación de salida.
            _peg_v = safe_float(ratios.get("peg"))
            _peg_bound = bool((result.get("peg_basis") or {}).get("bound"))   # F10: la cota ya decide el tramo
            _peg_ns = None if _peg_bound else peg_not_significant(
                safe_float(ratios.get("pe")), _peg_v, safe_float(fin_dict.get("eps_cagr_3y")),
                from_source=not ((result.get("peg_basis") or {}).get("own")
                                 or (result.get("peg_basis") or {}).get("note", "").startswith("PEG a 3 años")))
            if not _peg_ns and not _peg_bound and _peg_v is not None \
                    and is_anomalous_not_significant(fin_dict.get("eps_growth_reason")):
                # F10: sin un crecimiento del BPA significativo no hay con qué contrastar el PEG de la fuente
                _peg_ns = f"el crecimiento del BPA del informe es {fin_dict['eps_growth_reason']}"
            if _peg_ns:
                ratios["peg"] = result["key_metrics"]["peg"] = None
                fin_dict["peg_not_significant"] = _peg_ns
                _id_flags.append({"field": "key_metrics.peg", "rule": "multiplo_no_significativo",
                                  "action": "sin_dato", "old": _peg_v, "new": None,
                                  "reason": f"PEG de {_peg_v:.2f}: {_peg_ns}"})
            # Fase 3 (T6, §1.3): regla de 40 de GROWTH_PROFITABLE con el crecimiento que puntúa (por acción si aplica).
            if archetype == "GROWTH_PROFITABLE" and isinstance(result.get("quality_readings"), dict):
                import quality_readings as qr
                _r40 = qr.rule_of_40(safe_float(fin_dict.get("revenue_cagr_3y")),
                                     safe_float(sbc_info.get("fcf_margin_adjusted")),
                                     per_share=bool(fin_dict.get("revenue_cagr_per_share")),
                                     window=fin_dict.get("revenue_cagr_window"), margin_basis=sbc_info.get("basis"))
                if _r40:
                    result["quality_readings"]["rule_of_40"] = _r40
            # Fase 3 (T1b): crecimiento en la moneda de los estados, con el efecto divisa declarado aparte.
            if growth_currency.converted(_cur_info):
                _rev_usd = _rg(_stmts.get("revenue") or [], 3, what="ingresos", strict_ends_only=True,
                               long=_hfy.get("revenue"), end=_g_end)["value"]
                _yoy = growth_currency.yoy(_stmts_g.get("revenue"))
                _yoy_usd = growth_currency.yoy(_stmts.get("revenue"))
                if _yoy is not None:
                    result["key_metrics"]["revenue_growth"] = _yoy
                result["growth_currency"] = {
                    "statements": _cur_info.get("statements"), "price": _cur_info.get("price"),
                    "revenue_growth_yoy": {"statements": _yoy, "price": _yoy_usd,
                                           "fx_effect": growth_currency.fx_effect(_yoy_usd, _yoy)},
                    "revenue_cagr_3y": {"statements": _rev_r["value"], "price": _rev_usd,
                                        "fx_effect": growth_currency.fx_effect(_rev_usd, _rev_r["value"])},
                    "note": "crecimiento medido en la moneda de los estados; el efecto del tipo de cambio va aparte",
                    # F9 · R3: los mismos ejercicios en la moneda de los estados, para que el gráfico histórico mida su
                    # crecimiento como el resto del informe (TM: 7.0% en USD en el gráfico frente al 10.9% en JPY)
                    "yearly": [{k: (safe_float(v) if isinstance(v, float) else v) for k, v in r_.items()
                                if k in ("year", "revenue", "net_income", "free_cash_flow", "fcf_minus_sbc")}
                               for r_ in archetype_metrics.yearly_financials(_stmts_g, archetype)]}

            # ── Fase C: creación de valor (ROIC-WACC) y retorno al accionista ──
            # ── Etapa 8: un solo WACC (DCF, grid, spread y lo que se muestra) ──
            # E/(D+E)·Ke + D/(D+E)·Kd·(1−t); FINANCIAL no usa WACC (P/B justificado con Ke).
            if archetype == FINANCIAL:
                wacc_info = {"value": None, "applicable": False,
                             "reason": not_applicable(archetype, "roic_wacc") or not_applicable_text(FINANCIAL)}
            else:
                wacc_info = compute_wacc(
                    beta=_beta_val, beta_preadjusted=_beta_pre, rf=rf_info, market_cap=mcap,
                    total_debt=td_val,
                    interest_coverage=safe_float(_rcov["coverage"]),
                    coverage_state=_rcov["state"],
                    tax=tax_info, ke=ke_info)
                wacc_info["applicable"] = True
                wacc_info["rating_coverage"] = {k: (safe_float(v) if isinstance(v, float) else v)
                                                for k, v in _rcov.items()}
            wacc_est = wacc_info["value"]
            # Beta (fase 2b, T6: propia, del sector o de la fuente; lib/beta.py) y la ajustada que usa el Ke (también
            # en FINANCIAL): Blume sobre la propia y la de la fuente; la del sector ya es una media de industria.
            _braw = _beta_val
            result["beta"] = {"raw": None if _beta_pre else _braw, "adjusted": safe_float(adjusted_beta(_braw, _beta_pre)),
                              "method": "beta de abajo hacia arriba (sin Blume)" if _beta_pre else "Blume",
                              "default": _braw is None, "source": _beta_info.get("source"),
                              "reason": _beta_info.get("reason"), "own": _beta_info.get("own"),
                              "rule": _beta_info.get("rule"), "bottom_up": _beta_info.get("bottom_up"),
                              "relevered": _beta_info.get("relevered"), "discarded": _beta_info.get("discarded"),
                              "source_beta": _beta_info.get("source_beta"),
                              "discrepancy": _beta_info.get("discrepancy"),
                              # F9 · R2b: la tabla regional de la de abajo hacia arriba (None: la de EE. UU.)
                              "region": _beta_info.get("region"),
                              "coefficients": [cfg("valuation.capm.blume_weight"), cfg("valuation.capm.blume_prior")]}
            # F11 · T5: la beta sustituta frente a la propia descartada (se declara; baja la confianza)
            import beta as _beta_mod
            result["beta"]["contrast"] = _beta_mod.contrast(result["beta"]["source"], result["beta"]["adjusted"],
                                                            result["beta"]["own"])
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
            # Fase 1: sin dividend yield de una empresa que paga dividendos (fase 2b: ninguna fuente cuadra), el
            # shareholder yield tampoco tiene dato (antes sumaba 0 y quedaba igual a las recompras).
            if not dy_invalid and (div_yield is not None or buyback_yield is not None):
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
            if (_spectrum or {}).get("fcf_adjusted") is not None:
                # F8 · E4: el score lee el P/FCF y el FCF yield con el espectro restado, los mismos que la tabla.
                ratios["p_fcf"], ratios["fcf_yield"] = pfcf, fcf_yield
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
                # Fase 2b (T5, F2_PRECEDENCIA §2.3): en US GAAP el pasivo por arrendamiento operativo sale del pasivo de
                # X4 (su alquiler ya está restado en el EBIT de X3); en IFRS 16 se queda.
                _ol_fy = None
                if _has_yahoo and (yinfo.get("_debt") or {}).get("applied") \
                        and safe_float(((_stmts.get("total_liabilities") or [None]) or [None])[0]) is not None:
                    _ol_fy = safe_float(((_stmts.get("operating_lease_liabilities") or [None]) or [None])[0])
                    if _ol_fy and z_tl is not None:
                        z_tl = z_tl - _ol_fy

                # Working capital — only compute if both components are available
                ca_val = _fy("current_assets", safe_float(financials.current_assets))
                cl_val = _fy("current_liabilities", safe_float(financials.current_liabilities))
                wc = (ca_val - cl_val) if (ca_val is not None and cl_val is not None) else None

                _bmx = result.get("business_model") or {}
                _alt_na = not_applicable(archetype, "altman") or _bmx.get("altman_excluded")
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
                    not_applicable_reason=_alt_na, sic=_bmx.get("sic"),
                )
                result["altman_z"] = {
                    # Etapa 9b: null sin dato o cuando no aplica (nunca un z = 0).
                    "z_score": z_val if (z_val is not None and not _alt_na) else None,
                    "zone": z_zone.lower() if z_zone else "grey",
                    "interpretation": z_interp,
                    "model": z_details.get("model", ""),
                    "details": z_details,
                    # available=False indica "sin dato" (motivo en details.missing).
                    "available": z_val is not None,
                    "applicable": not _alt_na,
                    # F8 · E10: de dónde sale el modelo (SIC de EDGAR o sector) y, si se excluye por el SIC, el
                    # sustituto informativo (sin puntos): deuda neta/EBITDA y cobertura de intereses.
                    "model_basis": altman_model_basis(_bmx.get("sic")),
                    "excluded_by_sic": _bmx.get("altman_excluded"),
                    "substitute": ({"net_debt_to_ebitda": result["key_metrics"].get("net_debt_to_ebitda"),
                                    "net_debt_to_ebitda_state": result["key_metrics"].get("net_debt_to_ebitda_state"),
                                    "interest_coverage": result["key_metrics"].get("interest_coverage"),
                                    "interest_coverage_state": result["key_metrics"].get("interest_coverage_state")}
                                   if (_bmx.get("altman_excluded") and not not_applicable(archetype, "altman"))
                                   or (_bmx.get("captive_finance") or {}).get("detected") else None),
                    # Fase 2b (T5): pasivo de X4 sin el arrendamiento operativo (US GAAP), o None.
                    "operating_leases_excluded": _ol_fy if _ol_fy else None,
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
                                         "detail": c["detail"],
                                         # rediseño E2a (T6): los valores comparados (aditivo)
                                         "cur": c.get("cur"), "prev": c.get("prev"), "unit": c.get("unit"),
                                         "compare": c.get("compare")}
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
                # F13 · paso 2: el beneficio normalizado (`_norm`) y sus piezas (`_coh`, `_qn`…) ya se calcularon antes
                # del coste de capital (el rating sintético usa el EBIT normalizado); aquí se usan, no se recalculan.
                if _norm_err is not None:
                    raise _norm_err
                _ni = safe_float(financials.net_income)     # (entre medias, `_ni` se reutiliza para otras series)
                # Fase 7 (registro #36; revisión, hallazgos A y D): una aseguradora o un conglomerado se valora sobre su
                # beneficio OPERATIVO. Su P/E (y el E/P) pasa a ser capitalización / beneficio operativo en todo el
                # análisis (tabla, portada, alertas, score), con el reportado aparte. Beneficio operativo ≤ 0: sin P/E
                # (aunque el reportado sea positivo por las ganancias de la cartera).
                _struct = _norm.get("structural_net") or 0.0
                _ni_base = _ni
                if _struct and _ni is not None:
                    from normalize import operating_pe
                    _op = operating_pe(_ni, _struct, safe_float(result["key_metrics"].get("market_cap")))
                    _ni_base, _pe_op, _ey_op = _op["net_income_operating"], _op["pe"], _op["earnings_yield"]
                    result["key_metrics"]["pe_reported"] = result["key_metrics"].get("pe")
                    result["key_metrics"]["pe_basis"] = _op["basis"]
                    for _d in (ratios, result["key_metrics"], result.get("ratios") or {}):
                        _d["pe"] = safe_float(_pe_op)
                        _d["earnings_yield"] = safe_float(_ey_op)
                    _norm["pe_operating"] = safe_float(_pe_op)
                    _norm["net_income_operating"] = safe_float(_ni_base)
                _pe_rep = r("pe") if (r("pe") or 0) > 0 else None   # P/E <= 0 no es un múltiplo
                _nin = _norm["normalized_net_income"]
                # Lo demás (partidas inusuales) se normaliza sobre esa base: el P/E operativo no se escala dos veces.
                _other = any(i["applied"] and i["type"] != "estructural" for i in _norm["items"])
                _scale = ((_ni_base / _nin) if (_other and _ni_base and _nin and _nin > 0 and _ni_base > 0)
                          else None)
                _norm["pe_reported"] = safe_float(_pe_rep)
                _norm["pe_normalized"] = safe_float(_pe_rep * _scale) if (_pe_rep and _scale) else None
                # F10 · N1b: con discontinuadas, el BPA de Yahoo del P/E reportado no tiene una base fija (MLM: ya es el
                # continuado; JCI: ni el total ni el continuado): escalarlo las restaría dos veces o ninguna. El P/E
                # normalizado es entonces capitalización / beneficio normalizado (continuado), sin el BPA de Yahoo.
                _mc = safe_float(result["key_metrics"].get("market_cap"))
                if (any(i["applied"] and i["type"] == "discontinuadas" for i in _norm["items"]) and _mc
                        and _nin and _nin > 0 and not _struct):
                    _norm["pe_normalized"] = safe_float(_mc / _nin)
                    _norm["pe_normalized_basis"] = "capitalización / beneficio normalizado de operaciones continuadas"
                _norm["used_in_score"] = bool(_norm["applied"] and _nin is not None)
                # Etapa 9a: la etiqueta "normalizado" solo si difiere del reportado (> label_min_diff).
                _norm["differs"] = bool(_norm["used_in_score"] and _ni and _nin is not None
                                        and abs(_nin / _ni - 1) > cfg("thresholds.normalization.label_min_diff"))
                result["earnings_normalization"] = {k: (safe_float(v) if isinstance(v, float) else v)
                                                    for k, v in _norm.items()}
                result["key_metrics"]["pe_normalized"] = _norm["pe_normalized"]
                result["key_metrics"]["net_income_normalized"] = safe_float(_nin)
                if _norm["used_in_score"] and _ni:
                    # Fase 7 (registro #36): las ganancias de inversiones de una aseguradora o un conglomerado salen del
                    # beneficio con el que se VALORA (P/E operativo, convención del mercado), no del de la RENTABILIDAD:
                    # su patrimonio ya incluye la cartera a valor razonable e invertir el float es parte del negocio.
                    _struct = sum(i["net"] for i in _norm["items"] if i.get("type") == "estructural" and i["applied"])
                    _nin_q = _nin + _struct
                    _k = _nin_q / _ni
                    ratios_score = dict(ratios)
                    if _scale and _norm["differs"]:      # F10 · B2: ídem para el P/E sin etiqueta
                        ratios_score["pe"] = _norm["pe_normalized"]
                        ratios_score["earnings_yield"] = (1 / _norm["pe_normalized"]) if _norm["pe_normalized"] else None
                        # F11 · F3: el PEG con el mismo P/E que puntúa (el normalizado), no con el reportado.
                        _pb = result.get("peg_basis") or {}
                        if ratios.get("peg") is not None and _pb.get("own") and _pb.get("eps_cagr_3y") and \
                                _norm["pe_normalized"]:
                            ratios["peg"] = ratios_score["peg"] = _norm["pe_normalized"] / (
                                _pb["eps_cagr_3y"] * cfg("valuation.peg.growth_pct_scale"))
                            result["key_metrics"]["peg"] = safe_float(ratios["peg"])
                            result["peg_basis"] = dict(_pb, pe=_norm["pe_normalized"], pe_basis="normalizado")
                    # F10 · B2 (IDXX: ROE 70.6% en la puntuación frente a 70.67% en la página): por debajo de
                    # `label_min_diff` el normalizado no se distingue del reportado y la página no lo etiqueta: la
                    # puntuación usa el reportado, una sola cifra.
                    _q_differs = abs(_k - 1) > cfg("thresholds.normalization.label_min_diff")
                    if not _q_differs:
                        _k, _nin_q = 1.0, _ni
                    for _key in ("net_margin", "roe", "roa"):
                        if ratios.get(_key) is not None:
                            ratios_score[_key] = ratios[_key] * _k
                    ratios_score["net_income"] = _nin_q
                    if ratios.get("fcf") is not None and _nin_q:
                        ratios_score["fcf_to_net_income"] = ratios["fcf"] / _nin_q
                    _norm["quality_differs"] = _q_differs
                    result["earnings_normalization"]["quality_differs"] = _q_differs
                    # Etapa 9a: qué ratios del score y de las alertas salen del beneficio
                    # normalizado, para que el texto lo diga ("ROE normalizado 55.9%").
                    fin_dict["normalized_metrics"] = (
                        (([k for k in ("net_margin", "roe", "roa") if ratios.get(k) is not None]
                          + (["fcf_to_net_income"] if ratios.get("fcf") is not None else [])) if _q_differs else [])
                        + (["pe", "earnings_yield"] if _scale else [])
                        if _norm["differs"] else [])
                # F10 · margen operativo con una sola verdad: puntúa sin los cargos operativos que la normalización ya
                # quita del beneficio (como el margen neto); se enseñan las dos cifras (key_metrics y la nota).
                # Sobre las cifras del corte (las que se enseñan), con las mismas partidas que el beneficio normalizado.
                _opn = {}
                # (sin corte trimestral: las del ejercicio, las mismas del margen enseñado; regla 4)
                _oi_c, _rev_c = ((_om_fy["operating_income"], _om_fy["revenue"]) if _om_fy is not None
                                 else (oi_val, safe_float(rev_val)))
                if _coh is not None and not _struct and _oi_c is not None:
                    from normalize import operating as _operating
                    _opn = {**_operating(_oi_c, _rev_c, _norm["items"], pretax=_coh.get("pretax"),
                                         net_interest=_coh.get("net_interest"),
                                         equity_income=_coh.get("equity_income"),
                                         known_inside=((yinfo.get("_edgar_charges") or {}).get("charges") or 0.0)
                                         if _has_yahoo else 0.0),
                            "pieces_source": _coh.get("operating_income_source"),
                            "yahoo_quarterly": _coh.get("operating_income_yahoo_quarterly")}
                    result["earnings_normalization"]["operating"] = {
                        k: (safe_float(v) if isinstance(v, float) else v) for k, v in _opn.items()}
                if _opn.get("differs") and _opn.get("margin_normalized") is not None \
                        and ratios.get("operating_margin") is not None:
                    ratios_score = dict(ratios_score)
                    ratios_score["operating_margin"] = _opn["margin_normalized"]
                    result["key_metrics"]["operating_margin_normalized"] = safe_float(_opn["margin_normalized"])
                    result["key_metrics"]["operating_income_normalized"] = safe_float(_opn["normalized"])
                    fin_dict["normalized_metrics"] = list(fin_dict.get("normalized_metrics") or []) + ["operating_margin"]
            except Exception as e:
                _sin_dato("normalizacion_ganancias", e)

            # F8 · E2 (auditoría del 26-oct, NEE): bandera de pico de beneficio. Con ella, el P/E del score sale de la
            # mediana de 3 ejercicios (y del forward, si es coherente), no del TTM atípico.
            result["earnings_peak"] = None
            try:
                import earnings_peak as _epk
                _en = result.get("earnings_normalization") or {}
                _ni_rep = safe_float(financials.net_income)
                _peak = None if not_applicable(archetype, "pe") else _epk.detect(
                    ni_ttm=(safe_float(_en.get("normalized_net_income")) if _en.get("used_in_score") else _ni_rep),
                    ni_reported=_ni_rep, fy_net_income=[safe_float(v) for v in (_stmts.get("net_income") or [])],
                    pe_score=safe_float(ratios_score.get("pe")), pe_reported=safe_float(ratios.get("pe")),
                    forward_pe=safe_float(ratios.get("forward_pe")), period=numfmt.period(fin_dict.get("ttm_basis")))
                result["earnings_peak"] = _peak
                if _peak and _peak["flag"]:
                    ratios_score = dict(ratios_score)
                    ratios_score["pe"] = _peak["pe_score"]
                    ratios_score["earnings_yield"] = 1 / _peak["pe_score"]
                    fin_dict["earnings_peak"] = _peak
            except Exception as e:
                _sin_dato("pico_beneficio", e)

            # Valuation (Graham + DCF) — etapa 8: ANTES del score, porque el DCF es un
            # componente de Valoración con aporte acotado por su fiabilidad.
            dcf_for_score = None
            _multiples_signal = None
            _quality_part = _price_part = None
            _scenario_inputs = None   # rediseño E2a (T7)
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
                _growth_basis = (("ciclo medio de los ingresos de pico a pico" if result.get("mid_cycle")
                                  else "ciclo medio de los ingresos (acotado: historia corta)")
                                 if archetype == CYCLICAL
                                 else "CAGR de ingresos por acción a 3 años"
                                 if "ingresos" in (growth_basis.get("applied_to") or [])
                                 else "CAGR de ingresos a 3 años")
                _rgm = fin_dict.get("revenue_cagr_3y_method") or {}
                if archetype != CYCLICAL and _rgm.get("method") == "log_lineal_edgar":   # F10: serie larga de EDGAR
                    _ps_txt = " por acción" if "ingresos" in (growth_basis.get("applied_to") or []) else ""
                    _growth_basis = (f"crecimiento de ingresos{_ps_txt} "
                                     f"por regresión log-lineal sobre los {_rgm.get('years_used')} últimos ejercicios "
                                     f"de EDGAR ({_rgm.get('window')}; el año inicial de la ventana de 3 años es "
                                     "anómalo)")
                if (result.get("growth_perimeter") or {}).get("applied") and archetype != CYCLICAL:
                    _growth_basis = (f"CAGR de ingresos de {result['growth_perimeter']['homogeneous_years']} años en "
                                     "el perímetro homogéneo")
                # Fase 3 (T5, F3_DISENO §4): si el interanual y el CAGR a 3 años difieren más de `yoy_vs_3y_pp`, el DCF
                # usa una mezcla declarada (media de los dos), nunca uno de ellos en silencio. No en CYCLICAL (ciclo
                # medio) ni con el perímetro corregido (el interanual también cruza el cambio).
                _yoy_g = safe_float(result["key_metrics"].get("revenue_growth"))
                result["dcf_growth_blend"] = None
                if (growth is not None and _yoy_g is not None and archetype != CYCLICAL
                        and not (result.get("growth_perimeter") or {}).get("applied")
                        and abs(_yoy_g - growth) > cfg("valuation.dcf.yoy_vs_3y_pp")):
                    _blend = hm_mean([_yoy_g, growth])
                    result["dcf_growth_blend"] = {"yoy": _yoy_g, "cagr_3y": growth, "used": _blend}
                    _pp = f"{cfg('valuation.dcf.yoy_vs_3y_pp'):.0%}".replace("%", " pp")
                    _growth_basis = (f"media del interanual ({_yoy_g:+.1%}) y del {_growth_basis} ({growth:+.1%}): "
                                     f"difieren más de {_pp}")
                    growth = _blend
                if growth is None:
                    _rns = fin_dict.get("revenue_growth_reason")
                    growth, _growth_basis = cfg("valuation.dcf.default_growth"), (
                        f"valor por defecto: el crecimiento de los ingresos es {_rns}"      # F10: no se inventa una tasa
                        if is_anomalous_not_significant(_rns) else "valor por defecto (sin CAGR de los estados)")
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
                _fcf_gross = fcf
                if archetype == CYCLICAL:
                    # Etapa 8: FCF de MANTENIMIENTO (OCF − D&A como capex de mantenimiento,
                    # promedio de los ejercicios): el normalizado (margen FCF medio ×
                    # ingresos) incluye el capex de expansión. Se muestran los dos.
                    _fcf_gross = safe_float(archetype_values.get("fcf_maintenance"))
                    _fcf_net = safe_float(archetype_values.get("fcf_maintenance_minus_sbc"))
                else:
                    # Fase 3 (T3, §8.4): FCF − SBC en el periodo del FCF (sbc_info, el mismo de la etapa 9a).
                    _fcf_net = safe_float(sbc_info.get("value"))
                # FCF − SBC siempre que haya SBC del mismo periodo; si no, el FCF con el motivo declarado.
                fcf = _fcf_net if _fcf_net is not None else _fcf_gross
                _fcf_basis = ("FCF − SBC" if _fcf_net is not None
                              else "FCF sin restar la SBC (sin SBC del mismo periodo)")
                if _spec_avg is not None and fcf is not None:
                    # F8 · E4: telecom, menos la media de 5 años de las compras de espectro (EDGAR).
                    fcf, _fcf_gross = fcf - _spec_avg, (_fcf_gross - _spec_avg if _fcf_gross is not None else None)
                    _fcf_basis += (f" − media de {len(_spectrum['years'])} años de las compras de espectro "
                                   f"({numfmt.money(_spec_avg)})")
                _dcf_missing = None
                # Etapa 11b: FCF base <= 0 (ya normalizado por el arquetipo: el de mantenimiento en
                # CYCLICAL) no es un dato ausente: el DCF "no es significativo" y no da valor razonable.
                _dcf_not_sig = None
                if _dcf_na:
                    pass
                elif fcf is None:
                    _dcf_missing = "sin FCF de entrada: no hay flujo que descontar"
                elif fcf <= 0:
                    _dcf_not_sig = (f"{'FCF − SBC' if _fcf_net is not None else 'FCF'} base {numfmt.money(fcf)} "
                                    "(≤ 0): no hay flujo positivo que descontar, así que el DCF no es significativo")
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
                    _decay = dcf_result.get("decay_type") or "step"
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
                    # Rediseño E2a (T7): los argumentos exactos con los que el motor llamó a dcf_multi_stage, para el
                    # escenario del usuario (lib/scenario.py; con ellos reproduce `fair_value`). Aditivo.
                    if _fv is not None and not _dcf_not_sig:
                        _mi, _mst = _dcf_model.get("inputs") or {}, _dcf_model.get("stages") or {}
                        _scenario_inputs = {
                            "status": "ok", "reason": None, "fcf": _mi.get("fcf"),
                            "shares_outstanding": financials.shares_outstanding,
                            "net_debt": dcf_result.get("net_debt"),
                            "base": {"high_growth_rate": _mi.get("high_growth_rate"),
                                     "high_growth_years": (_mst.get("high_growth") or {}).get("years"),
                                     "transition_years": (_mst.get("transition") or {}).get("years"),
                                     "terminal_growth": _mi.get("terminal_growth"),
                                     "discount_rate": _mi.get("discount_rate"), "decay_type": _mi.get("decay_type")},
                            "price": price, "currency": result["profile"].get("currency")}
                        # Rediseño E3 (Task 7): ingresos base, margen de caja, arquetipo, límites y preajustes. Aditivo.
                        import scenario as _scn
                        _scenario_inputs = _scn.extend(_scenario_inputs, safe_float(financials.revenue), archetype)
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
                        "fcf_basis": _fcf_basis,
                        "fcf_gross": safe_float(_fcf_gross),
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
                        fcf_flags=_fcf_flags, fcf_source=_fcf_source,
                        history_fy=(yinfo.get("_history_fy") if _has_yahoo else None),
                        # F8 · E8 (4): banderas de datos que restan fiabilidad a los insumos del DCF.
                        data_flags=[f for f in (
                            ("beta sin verificar (la de la fuente, sin regresión propia ni industria)"
                             if (result.get("beta") or {}).get("source") == "fuente" else None),
                            ("sin beta propia, de industria ni de la fuente"
                             if (result.get("beta") or {}).get("source") == "sin_dato" else None),
                            ("beneficio con pico (bandera de pico de beneficio)"
                             if (result.get("earnings_peak") or {}).get("flag") else None)) if f],
                        current_margins={k: safe_float(result["key_metrics"].get(k))
                                         for k in ("operating_margin", "net_margin")})
                    result["dcf"]["reliability"] = _rel
                    if _dcf_not_sig:
                        pass
                    elif _rel:
                        dcf_for_score = {"upside": _dcf_upside / 100.0 if _dcf_upside is not None else None,
                                         "reliability": _rel["level"], "reasons": _rel["reasons"],
                                         "grid_contains_price": _rel["grid_contains_price"],
                                         # F11 · F1: la dirección no puede depender de ±1 escalón de WACC
                                         "wacc_flips": dcf_wacc_flips(result.get("sensitivity"))}
                        result["dcf"]["wacc_flips"] = dcf_for_score["wacc_flips"]
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
                result["scenario_inputs"] = _scenario_inputs or {
                    "status": "sin_dato", "reason": result["dcf_status"]["reason"] or "el DCF no da valor razonable"}
            except Exception as e:
                logger.error(f"Valuation error: {e}")
                _sin_dato("graham/dcf", e)

            # ── Fase 3 (T3, D3): DCF inverso (lib/reverse_reading). Qué crecimiento exige el precio, frente a las
            # tasas base y a la historia propia. Es el método intrínseco cuando el directo tiene fiabilidad baja.
            try:
                import reverse_reading as rr
                _price_r = safe_float(financials.price)
                _sh_r = safe_float(financials.shares_outstanding)
                _nd_r = ((td_val or 0.0) - (cash_val or 0.0)) if (td_val is not None or cash_val is not None) else 0.0
                _own_r = rr.own_growth(yinfo.get("_history_fy") if _has_yahoo else None,
                                       safe_float(fin_dict.get("revenue_cagr_3y")))
                _rv_args = dict(price=_price_r, shares=_sh_r, revenue_usd=_revenue_usd(safe_float(financials.revenue),
                                                                         profile.currency), sector=sector)
                _rv = {"applicable": False, "reason": None, "main": None, "ttm": None}
                if archetype == FINANCIAL:
                    _rv["reason"] = "no aplica a bancos y aseguradoras: su método intrínseco es el P/B justificado"
                elif archetype == REIT:
                    # §8.7: sobre el FFO por acción, flujo del accionista: al coste del capital propio, sin deuda.
                    _own_ffo = {"cagr": safe_float(archetype_values.get("ffo_per_share_cagr_3y")), "years": 3,
                                "basis": "ffo_por_accion", "source": "estados (3 años)", "label": "su FFO por acción"}
                    _rv.update(applicable=True, main=rr.reading(
                        flow=safe_float(archetype_values.get("ffo_ttm")), rate=wacc_info.get("ke"), net_debt=0.0,
                        own=_own_ffo, flow_label="FFO", **_rv_args))
                elif result.get("not_applicable", {}).get("dcf"):
                    _rv["reason"] = result["not_applicable"]["dcf"]
                else:
                    _lab = ("FCF de mantenimiento" if archetype == CYCLICAL else "FCF") + \
                        (" − SBC" if _fcf_net is not None else "")
                    _rv.update(applicable=True, main=rr.reading(flow=fcf, rate=wacc_est, net_debt=_nd_r, own=_own_r,
                                                                flow_label=_lab, **_rv_args))
                    if (_rv["main"] or {}).get("state") == "no_aplica" and archetype != GROWTH_PRE_PROFIT:
                        # T7 (§2.1): con FCF − SBC <= 0 por la inversión de crecimiento (AMZN) o por la cartera de una
                        # financiera (TM), el flujo de mantenimiento: flujo operativo − D&A (capex de mantenimiento)
                        # − SBC, el "owner earnings" estándar, declarado.
                        _ocf = safe_float(financials.operating_cash_flow)
                        _da = safe_float(financials.depreciation)
                        _sbc_t = safe_float(sbc_info.get("sbc"))
                        if _ocf is not None and _da is not None:
                            _own_fl = _ocf - abs(_da) - (_sbc_t or 0.0)
                            _alt = rr.reading(flow=_own_fl, rate=wacc_est, net_debt=_nd_r, own=_own_r,
                                              flow_label=("flujo de mantenimiento (flujo operativo − D&A − SBC)"
                                                          if _sbc_t is not None else
                                                          "flujo de mantenimiento (flujo operativo − D&A)"),
                                              **_rv_args)
                            if _alt.get("state") in ("ok", "fuera_de_rango"):
                                _alt["replaces"] = (_rv["main"] or {}).get("reason")
                                _rv["main"] = _alt
                    if archetype == CYCLICAL:
                        # §8.5: segunda lectura con el flujo del periodo ("si el nivel actual se mantiene").
                        _ttm_net = safe_float(sbc_info.get("value"))
                        _rv["ttm"] = rr.reading(
                            flow=_ttm_net if _ttm_net is not None else safe_float(financials.free_cash_flow),
                            rate=wacc_est, net_debt=_nd_r, own=_own_r,
                            flow_label="FCF − SBC del periodo" if _ttm_net is not None else "FCF del periodo",
                            **_rv_args)
                result["reverse_dcf"] = _rv
                _m = _rv.get("main") or {}
                # Rediseño E3 (Task 7): el flujo, la deuda y la tasa del inverso, para "qué exige el precio" con los
                # supuestos del usuario en el escenario (lib/scenario.py). Aditivo.
                _si = result.get("scenario_inputs") or {}
                if _si.get("status") == "ok" and _m.get("flow_per_share") is not None:
                    _si["reverse"] = {k: _m.get(k) for k in ("flow_per_share", "net_debt_per_share", "rate",
                                                             "terminal_growth")}
                # T7: utility regulada, su método intrínseco puntúa como el del inverso (P/B frente al ROE regulado).
                _uimp = (archetype_values.get("implied") or {}) if archetype == "UTILITY" else {}
                if _uimp.get("band") and isinstance(dcf_for_score, dict) and dcf_for_score.get("na"):
                    _pts = cfg("valuation.reverse_dcf.band_points").get(_uimp["band"])
                    dcf_for_score["reverse"] = {"band": _uimp["band"], "points": _pts,
                                                "metric": "P/B frente al ROE regulado",
                                                "text": (f"El precio descuenta un ROE sostenido del "
                                                         f"{_uimp['implied'] * 100:.1f}%; la utility obtuvo un "
                                                         f"{_uimp['own'] * 100:.1f}% de media en "
                                                         f"{_uimp['own_years']} ejercicios.")}
                # §2.3: el inverso puntúa en Valoración cuando el directo no se usa (fiabilidad baja; REIT sin DCF).
                if _m.get("points") is not None and isinstance(dcf_for_score, dict) and (
                        dcf_for_score.get("reliability") == "baja" or (archetype == REIT and dcf_for_score.get("na"))
                        or dcf_for_score.get("not_significant")):
                    # Revisión de código F3 (hallazgo 5): el rótulo dice sobre qué flujo resuelve el inverso; el de
                    # mantenimiento solo cuando lo sustituye (FCF − SBC <= 0), no cuando el directo deja de ser
                    # significativo por la deuda.
                    dcf_for_score["reverse"] = {
                        "band": _m["band"], "points": _m["points"], "text": _m["text"],
                        "metric": ("DCF inverso (flujo de mantenimiento)" if _m.get("replaces")
                                   else f"DCF inverso ({_m.get('flow_label') or 'FCF − SBC'})")}
            except Exception as e:
                logger.error(f"Reverse DCF error: {e}")
                _sin_dato("dcf_inverso", e)

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
                # Fase 4 (T1): persistencia del tramo alto con la historia de EDGAR (o, sin ella, la de los estados).
                _persist = None
                try:
                    import persistence as _pers
                    _hfy = yinfo.get("_history_fy") if _has_yahoo else None
                    # F11 · T7: un subtipo sin margen neto (banco) ancla la Rentabilidad en su ROE de cada ejercicio.
                    _pkw = {"not_applicable": subtype_not_applicable(classification.get("subtype")),
                            "roe_by_year": (result.get("archetype_metrics") or {}).get("roe_by_year")}
                    _persist = (_pers.measure(_pers.merge_history(_hfy, _stmts_g), archetype, "edgar", **_pkw) if _hfy
                                else _pers.measure(_pers.history_from_statements(_stmts_g), archetype, "estados",
                                                   **_pkw))
                except Exception as e:
                    _sin_dato("persistencia", e)
                # F12 · D2: el P/E reportado, para ver si el forward y el P/E que puntúa (normalizado) comparten base
                fin_dict["pe_reported"] = safe_float(ratios.get("pe"))
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
                    persistence=_persist,
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
            _alert_args = None
            try:
                # F11 · T3: los argumentos se guardan para rehacer las alertas con la caída del año, que llega con el
                # contexto de mercado (después del veredicto, D5).
                _alert_args = ((ratios_score, fin_dict), dict(
                    sector=score_sector, real_sector=sector,
                    roic_wacc_spread=roic_wacc_spread,
                    altman=result.get("altman_z"),
                    piotroski=result.get("piotroski_f"),
                    dcf=result.get("dcf"),
                    archetype=archetype,
                    archetype_values=archetype_values,
                ))
                result["alerts"] = build_signals(*_alert_args[0], **_alert_args[1])
            except Exception as e:
                _alert_args = None      # F11 · T3: sin alertas, no se rehacen con la caída (un solo «sin dato»)
                logger.error(f"Alerts error: {e}")
                result["alerts"] = {"red_flags": [], "warnings": [], "strengths": []}
                _sin_dato("alerts", e)

            # Historical price data for chart
            try:
                result["price_history"] = {
                    "52w_high": safe_float(financials.price_52w_high),
                    "52w_low": safe_float(financials.price_52w_low),
                    "beta": _beta_ke,
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
        result["data_validation"] = list(yinfo.get("_validation") or []) + _row_flags + _id_flags + _out_flags
        result["data_provenance"] = _build_provenance(yinfo, _out_flags, _block_errors)
        for _k in _bank_leverage_na:
            result["data_provenance"].setdefault("fields", {})[f"key_metrics.{_k}"] = {
                "source": "politica_arquetipo",
                "detail": ("banco: la deuda (subordinada, depósitos y emisiones de la actividad) no entra en las ratios "
                           "de apalancamiento de empresa; su apalancamiento se mide con capital (F2_PRECEDENCIA §2.3)")}
        if ic_state_inferred:
            result["data_provenance"].setdefault("fields", {})["key_metrics.interest_coverage_state"] = {
                "source": "derivado",
                "detail": ("inferido: EBIT > 0 y cobertura negativa sin fila de resultado financiero en los estados "
                           "⇒ ingresos financieros netos (sin carga financiera neta)")}

        # ── Etapa 8: confianza del veredicto (spec Sección 3) ──
        # Se calcula y se muestra (JSON, PDF); NO limita el score: el techo
        # condicionado por la confianza es de la etapa 9.
        if financials and result.get("score"):
            try:
                _price = safe_float(financials.price)
                _d = result.get("dcf") or {}
                _arch = (result.get("classification") or {}).get("archetype")
                _methods = []
                if _arch == "UTILITY":
                    # T7: utility regulada, P/B justificado por el ROE medio (método intrínseco) y múltiplos.
                    _xm = result.get("archetype_metrics") or {}
                    if _xm.get("pb") and _xm.get("pb_justified"):
                        _methods.append({"method": "P/B justificado (ROE regulado)", "kind": "intrínseco",
                                         "upside": _xm["pb_justified"] / _xm["pb"] - 1})
                    if _multiples_signal:
                        _methods.append({"method": "múltiplos frente al sector", "kind": "relativo",
                                         "signal": _multiples_signal["value"],
                                         "components": _multiples_signal["components"],
                                         "readings": _multiples_signal.get("readings")})
                elif _arch == FINANCIAL:
                    # FINANCIAL: dos métodos sobre el P/B. Intrínseco: P/B justificado por
                    # Gordon ((ROE − g)/(Ke − g)); relativo: P/B frente a la mediana del sector.
                    _xm = result.get("archetype_metrics") or {}
                    _pb = _xm.get("pb")
                    # F11 · T2: cada método dice de qué referencia depende su insumo dominante (el ROE estable del
                    # justificado en dos etapas; el P/B de la referencia del relativo).
                    import industry_bench as _ibench
                    _ts_ = _xm.get("two_stage") or {}
                    if _pb and _xm.get("pb_justified"):
                        _methods.append({"method": "P/B justificado (Gordon)", "kind": "intrínseco",
                                         "upside": _xm["pb_justified"] / _pb - 1,
                                         **({"anchor": _ts_["industry_roe_anchor"]}
                                            if _ts_.get("applied") and _ts_.get("industry_roe_anchor") else {})})
                    _spb = ((result.get("benchmark") or {}).get("values") or {}).get("pb")
                    if _pb and _spb:
                        _bi_ = (result.get("benchmark") or {}).get("industry") or {}
                        _methods.append({"method": "P/B frente al sector", "kind": "relativo",
                                         "upside": _spb / _pb - 1, "benchmark": _spb,
                                         **({"anchor": _ibench.reference_anchor(
                                             _bi_.get("damodaran"), _bi_.get("region"), _bi_.get("self_exclusion"))}
                                            if (result.get("benchmark") or {}).get("profile") != "market" else {})})
                else:
                    if _d.get("upside") is not None:
                        # F11 · F1: si ±1 escalón de WACC cruza el precio, el DCF lo ve «en precio» (sin dirección).
                        _methods.append({"method": "DCF", "kind": "intrínseco",
                                         "upside": 0.0 if _d.get("wacc_flips") else _d["upside"] / 100.0,
                                         "reliability": (_d.get("reliability") or {}).get("level"),
                                         **({"wacc_sensitive": True} if _d.get("wacc_flips") else {})})
                    # Fase 3 (T3, §2.3): el DCF inverso es el método intrínseco cuando el directo no es evaluable
                    # (fiabilidad baja, no significativo o REIT sin DCF): la convergencia vuelve a tener dos métodos.
                    _rvm = ((result.get("reverse_dcf") or {}).get("main") or {})
                    _direct_ok = (_d.get("upside") is not None
                                  and (_d.get("reliability") or {}).get("level") != "baja")
                    if _rvm.get("signal") is not None and not _direct_ok:
                        _methods.append({"method": "DCF inverso", "kind": "intrínseco", "signal": _rvm["signal"],
                                         "band": _rvm["band"]})
                    if _multiples_signal:
                        _methods.append({"method": "múltiplos frente al sector", "kind": "relativo",
                                         "signal": _multiples_signal["value"],
                                         "components": _multiples_signal["components"],
                                         "readings": _multiples_signal.get("readings")})
                # Graham no vota: es la referencia del inversor defensivo (P/E 15 × P/B 1.5).
                for _m in _methods:
                    if "upside" in _m:
                        _m["signal"] = signal_from_upside(_m["upside"])
                _cls = result.get("classification") or {}
                result["confidence"] = verdict_confidence({
                    "convergence": convergence(_methods),
                    "coverage": coverage_dimension(result.get("score_coverage"),
                                                   (result["score"] or {}).get("excluded_categories") or [],
                                                   staleness=yinfo.get("_staleness"),
                                                   unmeasured_critical=(
                                                       ["el riesgo de crédito"] if (result.get("credit_risk") or {})
                                                       .get("status") == "no_medido" else None)),
                    "source": source_dimension(
                        input_flags=list(yinfo.get("_validation") or []) + _row_flags,
                        normalization=result.get("earnings_normalization"),
                        ttm=yinfo.get("_ttm"), provenance_fields=(yinfo.get("_provenance") or {}),
                        self_exclusion=((result.get("benchmark") or {}).get("industry") or {}).get("self_exclusion"),
                        beta_contrast=(result.get("beta") or {}).get("contrast")),
                    "stability": stability_dimension(_cls.get("archetype"), _cls),
                    # Fase 2b (D7): emisor sin estados en la SEC -> techo "baja"
                    "fuente_oficial": official_dimension(yinfo.get("_official_source") if _has_yahoo else None),
                    # F13 · paso 3: base frágil (caja negativa por inversión, Altman en peligro, normalizado frente a
                    # forward): techo «media», no pondera
                    "base": fragility_dimension(_cls.get("archetype"), result.get("key_metrics") or {},
                                                result.get("altman_z"),
                                                bool((result.get("business_model") or {}).get("altman_referential"))),
                }, base_rate=_base_rate_for_confidence(result.get("reverse_dcf")))
            except Exception as e:
                _sin_dato("confianza", e)
            # ── Etapa 9a: calidad del negocio y atractivo del precio (lib/verdict.py) ──
            # El precio se contrae hacia 50 según la confianza del veredicto de valoración.
            try:
                if _quality_part is not None:
                    # F8 · E11: con confianza baja la calidad también se contrae hacia 50.
                    from verdict import contract_quality
                    # F10 · N4: la contracción usa la confianza previa al escalón de las tasas base (contraction_basis),
                    # salvo si el escalón contradice el veredicto (revisión de COST: verdict.price_contraction_basis).
                    from verdict import price_contraction_basis
                    _cats = score_result.get("categories") or []
                    _cbasis = price_contraction_basis(result.get("confidence"), _cats)
                    if result.get("confidence") and _cbasis != result["confidence"].get("contraction_basis"):
                        result["confidence"]["contraction_basis"] = _cbasis
                        result["confidence"]["base_rate_step"]["contracts"] = True
                    result["quality"] = contract_quality(_quality_part, _cbasis)
                    # `price` ya es el precio de la acción: la puntuación va en price_attractiveness.
                    result["price_attractiveness"] = verdict_price(_cats, _cbasis)
                    result["verdict"] = build_verdict(result["quality"], result["price_attractiveness"],
                                                      result.get("confidence"))
            except Exception as e:
                _sin_dato("veredicto", e)
            # F8 · E1: prueba de sensibilidad del veredicto a Ke ± 1 pp (lib/ke_sensitivity.py). Las repeticiones solo
            # llegan hasta aquí (los datos ya están en caché): de ellas sale el nivel de precio.
            import cost_of_capital as _coc
            if _coc.KE_SHIFT.get():
                return result
            try:
                import ke_sensitivity as _kes
                _kes.apply(result, lambda: _compute_analysis_body(symbol))
            except Exception as e:
                _sin_dato("sensibilidad_ke", e)

        # ── Fase 4 (T3): pre-mortem, "Esta lectura sería errónea si…" (lib/premortem.py) ──
        try:
            import premortem as _pm
            import persistence as _pers
            _hpm = yinfo.get("_history_fy") if _has_yahoo else None
            result["premortem"] = _pm.build(result, _pers.merge_history(_hpm, _stmts_g) if _hpm else None)
        except Exception as e:
            _sin_dato("premortem", e)

        # ── Fase 5 (D5: solo contexto): señales de mercado y lectura conductual (lib/market_context.py) ──
        try:
            if _has_yahoo:
                import market_context as _mctx
                import price_history as _ph
                import sector_profiles as _sp
                _etf = _sp.get_sector_profile(sector or "").sector_etf
                result["market_context"] = _mctx.build(symbol, _ph.peek(symbol), _ph.peek_market(), _etf, result,
                                                       yinfo.get("_edgar_filings"))
        except Exception as e:
            _sin_dato("contexto_mercado", e)
        # F11 · T3 (revisión de NU y NFLX): la alerta «Caída pronunciada» leía `max_drawdown_1y`, que nada rellenaba
        # desde que la caída vive en el contexto de mercado. Se rehacen las alertas con ella; no puntúa (D5).
        try:
            _dd1 = ((((result.get("market_context") or {}).get("signals") or {}).get("max_drawdown") or {}).get("1")
                    or {})
            if _dd1.get("status") == "ok" and _dd1.get("value") is not None and locals().get("_alert_args"):
                _ra, _rc = _alert_args[0]
                # F12 · D1: con la volatilidad anual realizada de la misma serie, que gradúa el peso de la caída
                _vol = (((result.get("market_context") or {}).get("signals") or {}).get("realized_volatility") or {})
                result["alerts"] = build_signals(_ra, {**(_rc or {}), "max_drawdown_1y": _dd1["value"],
                                                       "realized_volatility_1y": (_vol.get("value") if
                                                                                  _vol.get("status") == "ok" else None)},
                                                 **_alert_args[1])
        except Exception as e:
            _sin_dato("alerts", e)

        # ── Rediseño E2a: datos nuevos aditivos (no cambian ninguna cifra ni veredicto) ──
        try:   # T3: ficha de la empresa desde EDGAR submissions (sin red adicional)
            import company_profile as _cprof
            _edp = yinfo.get("_edgar") or {}
            result["company_profile"] = _cprof.build(_edp.get("profile"), result["profile"], _edp.get("status"),
                                                     _edp.get("reason"))
        except Exception as e:
            _sin_dato("company_profile", e)
        try:   # T4: variación del día frente al cierre anterior (la serie de la misma sesión que el precio)
            import price_history as _ph
            result["price_change"] = _ph.day_change((_ph.peek(symbol) or {}).get("frame"), result.get("price"))
        except Exception as e:
            _sin_dato("price_change", e)
        try:   # T5: historia de 10 ejercicios desde la historia anual de EDGAR que ya trae el análisis
            import history_10y as _h10
            _edp = yinfo.get("_edgar") or {}
            _hmiss = ("el emisor no presenta en la SEC" if _edp.get("status") in (None, "sin_cik")
                      else _edp.get("facts_reason") or _edp.get("reason"))
            result["history_10y"] = _h10.build(yinfo.get("_history_fy"), cfg("market.history.years_v2"), _hmiss)
        except Exception as e:
            _sin_dato("history_10y", e)

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
        raise HTTPException(status_code=500, detail=INTERNAL_ERROR)


# Fase 6 (F6_DIAGNOSTICO §2, D6 sin plan de pago): el análisis y el PDF son bloqueantes (red de Yahoo, SEC y Finnhub;
# reportlab). En un `async def` congelaban el bucle de eventos: producción atendía en serie y /api/health esperaba a
# que terminara el análisis en curso. Ahora corren en el pool de hilos (`run_in_threadpool`) y, como mucho,
# `max_concurrent_analyses` a la vez (memoria de la instancia y respeto a las fuentes); el resto espera su turno sin
# bloquear el bucle. El estado compartido ya era seguro entre hilos: sesión de Yahoo y cachés con locks, afirmaciones
# del guardián en un ContextVar.
_ANALYSIS_SLOTS = threading.BoundedSemaphore(cfg("data.server.max_concurrent_analyses"))
# Rediseño E2b: usuarios esperando turno (análisis o PDF). Los rivales (lib/peers.py) comparten los turnos con prioridad
# baja: su hilo no pide turno mientras haya usuarios esperando.
_waiting = [0]
_waiting_lock = threading.Lock()
# Cola v4 (decisión del PM, 30-oct): mientras haya usuarios esperando o activos, el trabajo de fondo (rivales,
# precalentado y la descarga de las tendencias) toma como mucho un turno a la vez, sin cambiar su prioridad. Con la
# máquina tranquila, hasta los hilos de la cola (los rivales, de dos en dos: PDF rápido). La carga corta de la
# integración (V4_CIERRE §2.6) dio un pico de 440 MB y una espera de usuario de 6,0 s, las dos en el minuto con más turnos
# de fondo. Un usuario «activo» tiene turno o lo soltó hace menos de `_user_active_s()`.
_turns = threading.Condition(_waiting_lock)
_user_turns = [0]                        # turnos de usuario en uso
_bg_turns = [0]                          # turnos de fondo en uso
_last_user = [float("-inf")]             # cuándo soltó su turno el último usuario (time.monotonic)


def _users_waiting() -> int:
    with _waiting_lock:
        return _waiting[0]


def _user_active_s() -> float:
    """La ventana de «usuario activo»: el p95 medido de un análisis sin caché (la pantalla de carga, data.web
    loading_expected_s). Un análisis de fondo que empezara dentro de ella seguiría con su turno cuando llega el
    siguiente usuario."""
    return float(cfg("data.web.loading_expected_s"))


def _users_active() -> bool:
    """Con el lock tomado."""
    return (_waiting[0] > 0 or _user_turns[0] > 0
            or time.monotonic() - _last_user[0] < _user_active_s())


def _reset_turns() -> None:
    """Tests."""
    with _turns:
        _waiting[0] = _user_turns[0] = _bg_turns[0] = 0
        _last_user[0] = float("-inf")


@contextlib.contextmanager
def _slot(user: bool = True):
    """Un turno de _ANALYSIS_SLOTS; si es de un usuario, cuenta como "esperando" hasta conseguirlo. Uno de fondo, con
    usuarios esperando o activos, espera a que no haya otro de fondo en marcha (mira otra vez cada `busy_wait_s`: la
    ventana de «activo» caduca sin aviso)."""
    if user:
        with _turns:
            _waiting[0] += 1
    else:
        with _turns:
            while _bg_turns[0] >= 1 and _users_active():
                _turns.wait(cfg("market.analysis_queue.busy_wait_s"))
            _bg_turns[0] += 1
    try:
        _ANALYSIS_SLOTS.acquire()
    except BaseException:
        if not user:
            with _turns:
                _bg_turns[0] -= 1
                _turns.notify_all()
        raise
    finally:
        if user:
            with _turns:
                _waiting[0] -= 1
    if user:
        with _turns:
            _user_turns[0] += 1
    try:
        yield
    finally:
        _ANALYSIS_SLOTS.release()
        with _turns:
            if user:
                _user_turns[0] -= 1
                _last_user[0] = time.monotonic()
            else:
                _bg_turns[0] -= 1
            _turns.notify_all()


@contextlib.contextmanager
def _background_slot():
    """Turno de fondo para trabajo que no es un análisis (descarga de las tendencias): como la cola de fondo, no lo
    pide mientras haya usuarios esperando turno."""
    while _users_waiting() > 0:
        time.sleep(cfg("market.analysis_queue.busy_wait_s"))
    with _slot(user=False):
        yield


def _compute_limited(symbol: str, user: bool = True) -> dict:
    with _slot(user):
        return _compute_analysis(symbol)


@app.get("/api/analysis/{symbol}")
async def analyze_stock(symbol: str, request: Request = None):
    """Complete stock analysis - the main endpoint."""
    _logo_prefetch(symbol)
    res = await run_in_threadpool(_compute_limited, symbol)
    await run_in_threadpool(_start_peers, symbol, res, _client_id(request))
    return await run_in_threadpool(_with_logo, res)


def _logo_prefetch(symbol: str) -> None:
    """Logotipos: la descarga empieza con el análisis y va en paralelo (lib/logos.py); nunca lo rompe."""
    try:
        import universe as _universe
        _logos.prefetch(_universe.norm_symbol(symbol))
    except Exception as e:
        logger.warning(f"logotipo de {symbol} no pedido: {type(e).__name__}")


def _with_logo(res: dict) -> dict:
    """El análisis con `logo` ({url, source} o null): se añade aquí y no en _compute_analysis, que comparten el PDF y
    los golden (el PDF no lleva logotipo). Copia superficial: el análisis en caché no cambia."""
    try:
        return {**res, "logo": _logos.meta(res["symbol"])}
    except Exception as e:
        logger.warning(f"logotipo de {res.get('symbol')} sin resolver: {type(e).__name__}")
        return res


def _start_peers(symbol: str, analysis: dict, client: Optional[str]) -> None:
    """F10 · N5: los rivales de la empresa que el usuario está viendo se ponen en marcha con su análisis (lib/peers.py,
    `start_with_analysis`); nunca rompen el análisis."""
    try:
        import peers as _p
        _p.start(symbol, analysis, client)
    except Exception as e:
        logger.warning(f"rivales de {symbol} no puestos en marcha: {type(e).__name__}")


@app.get("/api/pdf/{symbol}")
async def download_pdf(symbol: str):
    """Generate a comprehensive PDF financial report mirroring the app."""
    return await run_in_threadpool(_pdf_response, symbol)


def _pdf_response(symbol: str):
    import universe as _universe
    symbol = _universe.norm_symbol(symbol)        # V2: BF.B → BF-B, como el análisis

    try:
        # Revisión de F6 (hallazgo 7): el análisis Y el PDF (CPU de reportlab) dentro del mismo turno del semáforo; un
        # solo turno por petición (anidarlos agotaría los turnos con 4 PDF a la vez).
        with _slot():
            return _pdf_build(symbol, _compute_analysis(symbol))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"PDF generation error for {symbol}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=INTERNAL_ERROR)


def _pdf_build(symbol: str, analysis: dict):
    """El PDF del análisis ya hecho (dentro del turno del semáforo de _pdf_response)."""
    from datetime import datetime

    # El informe completo (identidad Finanzer, narrativa adaptativa por
    # bandas, logo, layout editorial) vive en lib/pdf_report.py.
    from pdf_report import build_report

    logo_path = None
    _base = os.path.dirname(os.path.abspath(__file__))
    for _cand in (
        # la marca: el logo en PNG que genera marca/exportar.mjs (reportlab no dibuja SVG)
        os.path.join(_base, "..", "frontend", "public", "brand", "finanzer-logo.png"),
        os.path.join(_base, "..", "frontend", "out", "brand", "finanzer-logo.png"),
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
    # Bytes ya hechos: el envío no ocupa un hilo del pool (la respuesta en streaming iteraba el buffer en uno).
    return Response(
        content=buf.getvalue(),
        media_type="application/pdf",
        # Nombre con espacios -> entre comillas (RFC 6266) para que el
        # navegador no lo trunque en el primer espacio.
        headers={"Content-Disposition": f'attachment; filename="Informe Finanzer {symbol} {datetime.now().strftime("%Y-%m-%d")}.pdf"'}
    )


@app.get("/api/v2/prices/{symbol}")
def prices_v2_endpoint(symbol: str, sector: Annotated[Optional[str], Query(max_length=64)] = None):
    """Rediseño /v2: serie diaria de la empresa, del S&P 500 y del ETF de su sector para la gráfica. Aditivo: la web
    actual no lo usa. El sector llega del análisis (profile.sector) para no repetir el análisis aquí; el ETF sale del
    registro de sectores (lib/sector_profiles.py), así que nunca se descarga un símbolo arbitrario.
    E2a (T9): `chart_period` (5 años, caché propia; la serie de 2 años del motor no cambia), cierre sin ajustar y
    ajustado, y los eventos de la empresa: dividendos y splits de la serie y resultados (8-K 2.02 de EDGAR, con su
    propio presupuesto; si EDGAR no responde, sin esas marcas y `events_reason`)."""
    return _prices_v2_payload(_v2_symbol(symbol), sector)      # V6 (B8): símbolo validado como el resto de /v2


def _prices_v2_payload(sym: str, sector: Optional[str]):
    """Cuerpo de /api/v2/prices (lo reutiliza el PDF nuevo de /api/v2/pdf)."""
    import price_history
    import prices_v2
    comp = price_history.chart(sym)
    mkt = price_history.chart_market()
    etf = get_sector_profile(sector or "").sector_etf if sector else None
    market_syms = {cfg("market.price_series.market_symbol"), cfg("market.price_series.market_fallback_symbol")}
    if etf and etf.upper() not in market_syms:
        sec = price_history.chart(etf)
    else:   # sector desconocido: el perfil neutro es el propio mercado (SPY), que ya va como referencia
        etf, sec = None, {"symbol": None, "frame": None, "reason": "sin ETF de sector"}
    company = prices_v2.serialize(comp, sym)
    as_of = company["points"][-1]["t"] if company["points"] else None
    if company["points"]:
        ev, why = prices_v2.earnings_events(sym, company["points"][0]["t"])
        company["events"] = sorted(company["events"] + ev, key=lambda e: e["t"])
        company["events_reason"] = why
    # V7 (M7): la rentabilidad con dividendos del mercado, de una serie que los incluye (config), y dicho.
    _trs = cfg("market.history.market_total_return_symbol")
    market = prices_v2.serialize(mkt, (mkt or {}).get("symbol"))
    if market["status"] == "ok" and (market["symbol"] or "").upper() != _trs.upper():
        market = prices_v2.with_total_return(market, prices_v2.serialize(price_history.chart(_trs), _trs), _trs)
    else:
        market = prices_v2.with_total_return(market, {}, _trs)
    # Revisión V6 (F1): rentabilidades por periodo, base 100 y marcas, aquí (lib/price_returns): la web solo pinta.
    import price_returns
    return price_returns.for_web({"symbol": sym, "as_of": as_of, "company": company, "market": market,
                                  "sector": prices_v2.serialize(sec, etf),
                                  "source": prices_v2.source_text(company, cfg("market.history.chart_period"))})


# V6 (revisión de seguridad, B1): turno propio de los escenarios (milisegundos de CPU cada uno; no esperan detrás de
# los análisis, pero tampoco se acumulan sin límite).
_SCENARIO_SLOTS = threading.BoundedSemaphore(cfg("data.server.scenario_concurrency"))


@app.post("/api/v2/scenario")
def scenario_v2(body: Any = Body(...)):
    """Rediseño E2a: escenario del usuario (sin estado; no toca el análisis ni el veredicto). Cuerpo:
    {"inputs": <scenario_inputs del análisis>, "assumptions": {supuestos que el usuario cambia}}.
    V6 (B1/B4): el cuerpo se valida antes de calcular (lib/scenario.parse_request): claves de más, tipos, valores no
    finitos o fuera de [scenario] input_* → 422."""
    import scenario as _sc
    try:
        si, assumptions = _sc.parse_request(body)
    except _sc.InvalidRequest as e:
        raise HTTPException(status_code=422, detail=str(e))
    with _SCENARIO_SLOTS:
        return _sc.run(si, assumptions)


# ── Rediseño E2b: datos nuevos en endpoints perezosos, fuera del camino de /api/analysis (no gastan su presupuesto ni
# sus turnos de _ANALYSIS_SLOTS, salvo los análisis de los rivales, que compiten como uno más con prioridad baja) ──
_V2_SYMBOL = re.compile(r"^[A-Z0-9.\-]{1,10}$")


def _v2_symbol(symbol: str) -> str:
    import universe as _universe
    sym = symbol.upper().strip()
    if not _V2_SYMBOL.match(sym):
        raise HTTPException(status_code=422, detail="símbolo no válido")
    return _universe.norm_symbol(sym)        # V2: BF.B → BF-B, como el análisis


@app.get("/api/v2/segments/{symbol}")
async def segments_v2_endpoint(symbol: str):
    """Ingresos por segmento del último 10-K/20-F/40-F (lib/segments.py): {status, segments, reconciles, …}."""
    import segments as _segments
    res = await run_in_threadpool(_segments.build, _v2_symbol(symbol))
    # V7 · P2, P4: los hechos que pintan la historia y Riesgos (sin calcular en el navegador)
    return {**res, "summary": _segments.summary(res)}


import analysis_queue as _analysis_queue
import peers as _peers
# Rediseño E4: rivales (prioridad user) y tarjetas de tendencias (prewarm) comparten la cola de lib/analysis_queue.py.
_analysis_queue.ANALYZE = lambda s: _compute_limited(s, user=False)
_analysis_queue.BUSY = lambda: _users_waiting() > 0


def _client_id(request: Optional[Request]) -> Optional[str]:
    """V6 (B7): quién pide, para su cupo de la cola de fondo: la IP del cliente que pone el proxy de producción en una
    de `client_ip_headers` (Cloudflare la sobrescribe: el cliente no la elige) o, sin ella, la del socket."""
    if request is None:
        return None
    for h in cfg("data.server.client_ip_headers"):
        v = (request.headers.get(h) or "").strip()
        if v:
            return v[:64]
    return request.client.host if request.client else None


@app.get("/api/v2/peers/{symbol}")
async def peers_v2_endpoint(symbol: str, symbols: Optional[str] = None, request: Request = None):
    """Rivales analizados con el motor completo (lib/peers.py). `?symbols=A,B,C` (como mucho market.peers.peers_count)
    sustituye a los automáticos. Responde enseguida con el estado de cada rival; el cliente repite cada `poll_s`."""
    sym = _v2_symbol(symbol)
    chosen = None
    if symbols is not None:
        chosen = list(dict.fromkeys(s.strip().upper() for s in symbols.split(",")))
        if (not chosen or len(chosen) > cfg("market.peers.peers_count")
                or any(not _V2_SYMBOL.match(s) for s in chosen)):
            raise HTTPException(status_code=422, detail="lista de rivales no válida")
    return await run_in_threadpool(_peers.peers_for, sym, chosen, _client_id(request))


@app.get("/api/v2/search")
async def search_v2_endpoint(q: str = Query("", min_length=1, max_length=100)):
    """Buscador de /v2 (lib/search_v2.py): {results: [{ticker, name, exchange}]}, solo acciones y con su bolsa."""
    import search_v2 as _search_v2
    return await run_in_threadpool(_search_v2.search, q)


import trending as _trending
# Verificación de la v4 (V4 · memoria): la descarga del universo de las tendencias, lote a lote, en un turno de fondo.
_trending.SLOT = lambda: _background_slot()


def _trending_at_boot() -> None:
    """Portada rápida: al arrancar el servidor (también en local), la última lista buena del archivo y el cálculo de
    las tendencias, en su hilo (lib/trending.py, `warm`). Evento startup, no al importar: el replay instala antes sus
    descargas. FINANZER_TRENDING_WARM=0 lo apaga (tests); FINANZER_PORTADA_SNAPSHOT=0, el archivo (o da otra ruta)."""
    env = os.environ.get("FINANZER_PORTADA_SNAPSHOT")
    snapshot = None if env == "0" else (env or os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                            cfg("market.trending.snapshot_file")))
    _trending.warm(os.environ, snapshot)


app.add_event_handler("startup", _trending_at_boot)


@app.get("/api/v2/sparklines")
def sparklines_v2_endpoint(symbols: Annotated[Optional[str], Query(max_length=600)] = None,
                           period: Annotated[Optional[str], Query(max_length=8)] = "1D"):
    """P8: mini-gráficas del cintillo de la portada (lib/sparklines.py): por símbolo, los puntos reducidos (LTTB, como
    mucho `max_points`), la referencia, la variación del periodo y sus fechas, o `sin_dato` con su motivo. Como mucho
    `max_symbols` símbolos válidos y un periodo de config: si no, 422. Si Yahoo no responde, cada valor sale sin
    gráfica y con el motivo: nunca un 5xx."""
    import sparklines as _sp
    try:
        syms, p = _sp.parse(symbols, period)
    except _sp.InvalidRequest as e:
        raise HTTPException(status_code=422, detail=str(e))
    return _sp.get(syms, p)


import logos as _logos


@app.get("/api/v2/logo/{symbol}")
async def logo_v2_endpoint(symbol: str, request: Request, v: Annotated[Optional[str], Query(max_length=32)] = None):
    """Logotipo de la empresa (lib/logos.py): PNG cuadrado de Parqet o, si no lo tiene, de Finnhub, servido desde aquí
    (el navegador no habla con terceros). Sin logotipo, 204 (sin contenido): la imagen no carga y la web pone la placa
    con las iniciales, sin el error de consola de un 404 en cada empresa sin logotipo. Con ?v= igual a la versión del
    contenido, caché inmutable; si no, `browser_max_age_s`. ETag y 304.
    La descarga va en su hilo y aquí se espera sin ocupar uno del grupo de los análisis (una portada fría pide 30
    logotipos a la vez); pasado `endpoint_wait_s` sin respuesta de la fuente, 204 sin caché (la siguiente lo tendrá)."""
    sym = _v2_symbol(symbol)
    L = cfg("data.logos")
    done, logo = _logos.get(sym, wait_s=0, background=True)
    deadline = time.monotonic() + L["endpoint_wait_s"]
    while not done and time.monotonic() < deadline:
        await asyncio.sleep(L["endpoint_poll_s"])
        done, logo = _logos.get(sym, wait_s=0, background=True)
    if logo is None:
        cache = f"public, max-age={L['fail_ttl_s']}" if done else "no-store"
        return Response(status_code=204, headers={"Cache-Control": cache})
    etag = f'"{logo.version}"'
    cache = ("public, max-age=31536000, immutable" if v == logo.version
             else f"public, max-age={L['browser_max_age_s']}")
    headers = {"Cache-Control": cache, "ETag": etag, "X-Logo-Source": logo.source}
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers=headers)
    return Response(content=logo.data, media_type="image/png", headers=headers)


@app.get("/api/v2/trending")
async def trending_v2_endpoint(period: Annotated[Optional[str], Query(max_length=8)] = None):
    """Tendencias del día sobre el universo (lib/trending.py): la última lista buena o "calculando". Cada tarjeta trae
    el estado del análisis del motor (`engine`: listo, analizando, en_cola o fallo; null si no hay ni está en marcha).
    V6b: con `period` (1D, 1S, 1M o 6M), solo las listas de ese periodo; otro valor, 422."""
    if period is not None and period not in cfg("market.trending.periods"):
        raise HTTPException(status_code=422, detail=f"periodo no válido (admitidos: {', '.join(cfg('market.trending.periods'))})")
    return _trending.get(period)


@app.get("/api/v2/pdf/{symbol}")
async def download_pdf_v2(symbol: str, request: Request = None):
    """Rediseño E5: el informe PDF nuevo (lib/pdf_v2), con el mismo semáforo y el mismo nombre de archivo que
    /api/pdf. Aditivo: /api/pdf y su informe no cambian."""
    return await run_in_threadpool(_pdf_v2_response, symbol, _client_id(request))


def _pdf_v2_response(symbol: str, client: Optional[str] = None):
    import universe as _universe
    symbol = _universe.norm_symbol(symbol)        # V2: BF.B → BF-B, como el análisis
    try:
        # Como /api/pdf: el análisis y el PDF en turnos del semáforo, y como turnos de un usuario (_slot): mientras
        # espera, la cola de fondo (rivales y precalentado) no toma turnos (verificación de la v4, V4).
        with _slot():
            analysis = _compute_analysis(symbol)
        # F10 · N5: entre los dos turnos, sus rivales (en marcha o los que falten) con la espera acotada de
        # market.peers.pdf_wait_s: fuera del semáforo, para que la cola los pueda analizar mientras tanto.
        _start_peers(symbol, analysis, client)
        rivals = _pdf_v2_rivals(symbol, client)
        with _slot():
            return _pdf_v2_build(symbol, analysis, rivals)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"PDF v2 generation error for {symbol}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=INTERNAL_ERROR)


def _pdf_v2_rivals(symbol: str, client: Optional[str] = None):
    try:
        import peers as _peers
        return _peers.for_pdf(symbol, client)
    except Exception as e:
        logger.warning(f"PDF v2: sin rivales para {symbol}: {e}")
        return None


def _pdf_v2_build(symbol: str, analysis: dict, rivals: Optional[dict] = None):
    """El PDF nuevo del análisis ya hecho: la serie de precios es la de /api/v2/prices (la misma descarga que hizo el
    análisis, en caché); si falla, el informe sale sin gráfica y lo dice. Los segmentos son los de /api/v2/segments;
    los rivales, los que trae `rivals` (_pdf_v2_rivals)."""
    from datetime import datetime
    import pdf_v2
    try:
        prices = _prices_v2_payload(symbol, (analysis.get("profile") or {}).get("sector"))
    except Exception as e:      # el informe nunca cae por la serie: la portada dice el motivo en su hueco
        logger.warning(f"PDF v2: sin serie de precios para {symbol}: {e}")
        prices = {"company": {"symbol": symbol, "status": "sin_dato", "points": [],
                              "reason": "la serie de precios no respondió"}}
    try:    # V6 (B9): los segmentos de /api/v2/segments solo si ya están en caché: dentro del turno no se descarga
        import segments as _segments
        segs = _segments.cached(symbol)
    except Exception as e:
        logger.warning(f"PDF v2: sin segmentos para {symbol}: {e}")
        segs = None
    # Rivales (F10 · N5): los que dejó _pdf_v2_rivals tras su espera acotada, cada uno con su estado; el informe pinta
    # los listos y dice los que faltan y por qué.
    pdf = pdf_v2.build_pdf(analysis, prices, segments=segs, peers=rivals)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="Informe Finanzer {symbol} {datetime.now().strftime("%Y-%m-%d")}.pdf"'}
    )


import keepalive as _keepalive
_keepalive.start()      # fase 6 (D6): solo en Render (RENDER_EXTERNAL_URL); en local y en los tests no arranca


_PROC_STATUS = "/proc/self/status"


def _process_memory() -> dict:
    """E6 (31-oct): la memoria del proceso, en MB, porque el plan gratuito de Render no la enseña. RSS actual y pico
    (VmRSS y VmHWM de /proc en Linux; sin /proc, el pico de getrusage y el actual sin dato) y el MALLOC_ARENA_MAX que
    ve el proceso."""
    kb = {}
    try:
        with open(_PROC_STATUS, encoding="ascii") as fh:
            for line in fh:
                key, _, rest = line.partition(":")
                if key in ("VmRSS", "VmHWM"):
                    kb[key] = int(rest.split()[0])
    except (OSError, ValueError, IndexError):
        pass
    if "VmHWM" not in kb:
        import resource
        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        kb["VmHWM"] = peak // 1024 if sys.platform == "darwin" else peak       # macOS: bytes; Linux: kB
    mb = lambda k: round(kb[k] / 1024, 1) if k in kb else None                  # noqa: E731
    return {"rss_mb": mb("VmRSS"), "peak_mb": mb("VmHWM"), "malloc_arena_max": os.environ.get("MALLOC_ARENA_MAX")}


@app.get("/api/health")
async def health():
    # Fase 2a: el commit desplegado (Render define RENDER_GIT_COMMIT; en local, null).
    # Fase 7: si EDGAR está activo y, si no, por qué (sin el valor de la variable).
    return {"status": "ok", "commit": os.environ.get("RENDER_GIT_COMMIT") or None, "edgar": edgar.env_check(),
            "keepalive": _keepalive.state(), "memory": _process_memory()}


# ── Serve frontend static files ──
# The frontend is built as a static export in ../frontend/out
_frontend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend", "out")
_frontend_dir = os.path.abspath(_frontend_dir)
# Marca: el manifiesto de la web (iconos al instalarla). mimetypes no conoce .webmanifest y, con nosniff, el tipo
# tiene que ser el bueno.
mimetypes.add_type("application/manifest+json", ".webmanifest")

# Rediseño E4 (Task 5): la v4 en /v2, servida como la exporta Next (frontend/src/app/v2/[[...symbol]]/page.tsx):
# out/v2/index.html es la portada y out/v2/{_V2_SHELL}/index.html, la historia y las páginas de profundidad (leen el
# símbolo de la URL). Los archivos reales bajo out/v2 (las cargas RSC .txt de la navegación de Next) se sirven tal
# cual; cualquier otra ruta /v2/{T}[/{capítulo}] recibe la historia. Se registra siempre (antes del comodín de abajo)
# y lee _frontend_dir al responder.
_V2_SHELL = "_"
# E6 · paso 2: un símbolo en la raíz (/AAPL, /BRK-B, /MC.PA) se redirige a /v2/{T}; la misma regla que el resto de /v2
# (main._V2_SYMBOL: letras, cifras, punto y guion, hasta 10), sin barras: /algo/raro no es un símbolo.
_ROOT_TICKER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.\-]{0,9}$")


def _v2_file(front_dir: str, path: str) -> Optional[str]:
    """El archivo que responde a /v2/{path}: un archivo real dentro de out/v2, la portada para /v2 y /v2/, y la
    historia para todo lo demás. None (404) sin build y ante cualquier intento de salir de out/v2 (verificación de la
    v4, V5: `..`, también codificado como %2e%2e o ..%2f, que uvicorn decodifica): ni un archivo ni la historia."""
    base = os.path.join(front_dir, "v2")
    home = os.path.join(base, "index.html")
    shell = os.path.join(base, _V2_SHELL, "index.html")
    path = (path or "").strip("/")
    if not path:
        return home if os.path.isfile(home) else None
    full = os.path.abspath(os.path.join(base, path))
    if ".." in path.replace("\\", "/").split("/") or not full.startswith(base + os.sep):
        return None
    if os.path.isfile(full):
        return full
    for f in (shell, home):
        if os.path.isfile(f):
            return f
    return None


@app.api_route("/v2", methods=["GET", "HEAD"])
@app.api_route("/v2/{path:path}", methods=["GET", "HEAD"])
async def serve_v2(path: str = ""):
    # HEAD: el enrutador de Next comprueba la URL canónica (/v2/) con un HEAD antes de navegar.
    f = _v2_file(_frontend_dir, path)
    if f is None:
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(f, media_type="text/html" if f.endswith(".html") else None)


if os.path.isdir(_frontend_dir):
    # Serve _next static assets
    _next_dir = os.path.join(_frontend_dir, "_next")
    if os.path.isdir(_next_dir):
        app.mount("/_next", StaticFiles(directory=_next_dir), name="next_static")

    # E6 · paso 2 (rutas de transición, docs/superpowers/plans/2026-10-18-rediseno-e6-migracion.md): la v4 es la web
    # principal y la actual queda de respaldo durante la observación. `/` sirve la portada de la v4 en la misma URL
    # (la portada no lleva símbolo); `/{T}` redirige (307: temporal) a `/v2/{T}`, porque la historia lee el símbolo de
    # esa ruta; `/clasica` es la portada actual y `/stock/{T}`, la web actual (con el aviso «Prueba la nueva versión
    # →»); `/api/pdf/{T}` se mantiene. Vuelta atrás: revertir este commit.
    def _v4_home() -> FileResponse:
        f = _v2_file(_frontend_dir, "")
        if f is None:
            raise HTTPException(status_code=404, detail="Not found")
        return FileResponse(f, media_type="text/html")

    @app.api_route("/", methods=["GET", "HEAD"])
    async def serve_index():
        return _v4_home()

    @app.get("/clasica")
    @app.get("/clasica/")
    async def serve_classic():
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
            # E6 · paso 2: un símbolo en la raíz (/AAPL) va a su historia de la v4
            if _ROOT_TICKER.match(filepath):
                return RedirectResponse(f"/v2/{filepath}", status_code=307)
        # Lo demás (y los intentos de recorrido): la portada de la v4, que ya es la principal
        return _v4_home()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
