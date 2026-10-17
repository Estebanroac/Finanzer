"""
Yahoo Finance Adapter — DIRECT API version
Uses Yahoo v10/quoteSummary API directly via curl_cffi (ONE call for everything)
~4 seconds vs ~40 seconds with yfinance wrapper
"""
import logging
import time
import threading
from typing import Dict, Any

from settings import cfg

_D = cfg("data.yahoo")

logger = logging.getLogger(__name__)

# ── Session management (crumb auth, reusable) ──
_session = None
_crumb = None
_session_lock = threading.Lock()

# ── In-memory cache ──
_cache: Dict[str, tuple] = {}   # symbol -> (ts, info, degraded)
_locks: Dict[str, threading.Lock] = {}
_global_lock = threading.Lock()
CACHE_TTL = _D["cache_ttl_s"]  # 5 minutos
# Un snapshot DEGRADADO caduca rápido para auto-repararse en el siguiente fetch
CACHE_TTL_DEGRADED = _D["cache_ttl_degraded_s"]

# ── Resiliencia ante respuestas degradadas de Yahoo ──
# Desde IPs de datacenter (Render), Yahoo devuelve intermitentemente respuestas
# con la mitad de los campos (rate limit suave). Tres defensas:
#   1) detectar el snapshot degradado y REINTENTAR con sesión/crumb frescos y
#      otro perfil de navegador;
#   2) cachearlo poco tiempo (CACHE_TTL_DEGRADED);
#   3) rellenar los huecos con el último snapshot BUENO conocido (los
#      fundamentales cambian trimestralmente: un dato de hace una hora es
#      infinitamente mejor que un null).
_IMPERSONATE_PROFILES = _D["impersonate_profiles"]
_profile_idx = 0
_best_cache: Dict[str, tuple] = {}   # symbol -> (ts, info) último snapshot bueno
_BEST_MAX_AGE = _D["last_known_good_max_age_s"]
_NESTED_KEYS = ("_yahoo_ratios", "_prior_year", "_current_derived", "_piotroski_current")

# ── Etapa 11b: moneda y clase de los estados (lib/currency.py) ──
# Un StatementContext por símbolo mientras dura su fetch: los estados de yfinance se
# leen a través de _stmt_ticker(), que los devuelve en la moneda y la clase de la
# cotización. Se crea en _do_fetch / _fallback_yfinance y se retira en get_ticker_info.
_STMT_CTX: Dict[str, Any] = {}
# Etapa 11b (velocidad): hasta cuándo se da por bloqueado quoteSummary (401) y se va directo
# al plan B. 0 = no bloqueado. Lo vacía el reset de los tests.
_qs_blocked_until = 0.0
_QS_BLOCK_TTL = _D["quotesummary_block_ttl_s"]
_TIMESERIES_URL = "https://query2.finance.yahoo.com/ws/fundamentals-timeseries/v1/finance/timeseries/{sym}"
_TIMESERIES_PERIOD1 = "473385600"   # 1985: todos los ejercicios disponibles (Yahoo da ~4)


class _StatementsTicker:
    """yf.Ticker cuyos estados llegan en la moneda y la clase de la cotización."""

    def __init__(self, ticker, ctx):
        self._t = ticker
        self._ctx = ctx

    def __getattr__(self, name):
        from currency import STATEMENT_ATTRS, add_row_aliases
        val = getattr(self._t, name)
        if name in STATEMENT_ATTRS:
            ctx = self._ctx
            # Etapa 11b: filas con nombre IFRS -> nombre canónico (antes de convertir).
            val, used = add_row_aliases(val)
            if used:
                ctx.row_aliases[name] = used
            if not ctx._class_done:
                try:
                    raw_bs = val if name == "balance_sheet" else self._t.balance_sheet
                except Exception:
                    raw_bs = None
                ctx.prepare_class(raw_bs)
            val = ctx.convert(name, val)
        return val


def _stmt_ticker(symbol: str):
    """yf.Ticker de `symbol`, envuelto si su fetch tiene contexto de moneda/clase."""
    import yfinance as yf
    t = yf.Ticker(symbol)
    ctx = _STMT_CTX.get(symbol.upper())
    return _StatementsTicker(t, ctx) if ctx is not None else t


def _statement_currency(symbol: str):
    """Moneda de los estados según fundamentals-timeseries (currencyCode), el mismo
    endpoint del que yfinance saca los estados y que responde sin crumb (también en
    Render, donde quoteSummary da 401). None si no hay respuesta o es ambigua."""
    try:
        _ensure_session()
        r = _session.get(_TIMESERIES_URL.format(sym=symbol),
                         params={"symbol": symbol, "type": "annualTotalRevenue,annualNetIncome",
                                 # period2 en el futuro devuelve un resultado vacío: hasta hoy.
                                 "period1": _TIMESERIES_PERIOD1, "period2": str(int(time.time()))},
                         timeout=_D["search_timeout_s"])
        if r.status_code != 200:
            return None
        codes = set()
        for item in ((r.json() or {}).get("timeseries") or {}).get("result") or []:
            for v in item.values():
                if isinstance(v, list):
                    codes |= {x.get("currencyCode") for x in v if isinstance(x, dict) and x.get("currencyCode")}
        return codes.pop() if len(codes) == 1 else None
    except Exception as e:
        logger.warning(f"[CURRENCY] moneda de los estados de {symbol} no disponible: {e}")
        return None


def _new_statement_context(symbol: str, price_currency, statement_currency, source: str,
                           market_cap, price, shares):
    """Crea el contexto, descarga el tipo de cambio si hace falta y lo registra."""
    import yfinance as yf
    from currency import StatementContext
    px_shares = (market_cap / price) if (market_cap and price and price > 0) else shares
    ctx = StatementContext(symbol, price_currency, statement_currency, source, px_shares, yf.Ticker)
    import sec_edgar
    ctx.cover_lookup = lambda: sec_edgar.cover_factor_for(symbol)    # fase 2b (T4): regla B del factor ADR
    ctx.prepare_fx()   # CurrencyConversionError si no hay tipo de cambio: no se mezcla
    _STMT_CTX[symbol.upper()] = ctx
    return ctx


# ── Trazabilidad de fuente (etapa 3) ──
# info["_provenance"] = {"campo" | "bloque.campo": {"source": ..., "detail": ...}}
# Vocabulario de source: yahoo_quotesummary | yfinance_statements | finnhub |
# derivado | recalculado_por_validacion | sin_dato.
def _tag_provenance(info: Dict[str, Any], source: str, detail: str,
                    paths=None, overwrite: bool = False) -> None:
    """Marca la procedencia de `paths` (o de todos los campos con valor que aún
    no tengan procedencia). Los campos internos (prefijo "_") no anidados se
    ignoran; los bloques de _NESTED_KEYS se recorren campo a campo."""
    prov = info.setdefault("_provenance", {})
    if paths is None:
        paths = []
        for k, v in info.items():
            if k in _NESTED_KEYS and isinstance(v, dict):
                paths += [f"{k}.{sk}" for sk, sv in v.items()
                          if sv is not None and not str(sk).startswith("_")]
            elif not str(k).startswith("_") and v is not None:
                paths.append(k)
    for p in paths:
        if overwrite or p not in prov:
            prov[p] = {"source": source, "detail": detail}

# Campos que prácticamente toda empresa cotizada tiene; si faltan varios, la
# respuesta vino degradada (no confundir con ausencias legítimas: dividendos,
# forward P/E, etc. NO están en esta lista).
_COMPLETENESS_FIELDS = _D["completeness_fields"]

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

        # Fase 2b: la serie diaria de precios (dividendos del propio título, rango de 52 semanas y beta) se
        # descarga en un hilo, en paralelo con los estados; se recoge después de Finnhub.
        import sec_edgar as edgar
        import price_history
        _hist_future = price_history.start(symbol)
        _edgar_future = edgar.start(symbol)
        try:
            info = _do_fetch(symbol)
            _ctx = _STMT_CTX.get(symbol)
            if _ctx is not None:
                info["_currency"] = _ctx.summary()
        finally:
            _STMT_CTX.pop(symbol, None)
        _info_ctx = _ctx        # fase 2b (T4): el respaldo de EDGAR convierte con el mismo contexto que los estados

        # ── Defensa 1: reintento ante respuesta degradada ──
        # Etapa 11b: no en el plan B. Ahí faltan por construcción beta, forward, dividendo y
        # crecimientos (fast_info no los trae y info está bloqueado): siempre parecía
        # "degradado" y se repetía todo dos veces más (+2.4 s de espera). Esos huecos los cubre
        # Finnhub (defensa 4).
        attempts = 0
        while _is_degraded(info) and attempts < 2 and info.get("_data_path") != "plan_b_yfinance":
            attempts += 1
            logger.warning(
                f"[DEGRADED] {symbol}: {_completeness(info)}/{len(_COMPLETENESS_FIELDS)} "
                f"campos clave; reintento {attempts} con sesión fresca")
            _reset_session(rotate_profile=True)
            time.sleep(_D["degraded_retry_sleep_step_s"] * attempts)
            try:
                retry_info = _do_fetch(symbol)
                _ctx = _STMT_CTX.get(symbol)
                if _ctx is not None:
                    retry_info["_currency"] = _ctx.summary()
            except Exception as e:
                logger.warning(f"[DEGRADED] reintento falló para {symbol}: {e}")
                break
            finally:
                _STMT_CTX.pop(symbol, None)
            if _quality(retry_info) > _quality(info):
                info = retry_info
                _info_ctx = _ctx

        degraded = _is_degraded(info)

        # ── Defensa 3: rellenar huecos con el último snapshot bueno ──
        info = _merge_last_known_good(symbol, info, degraded)

        # ── Defensa 4: fuente secundaria (Finnhub) para lo que Yahoo bloquea
        # persistentemente desde IPs de datacenter (beta/forward/dividendo/growth
        # y los estados históricos para Piotroski). Inerte si no hay API key.
        try:
            from finnhub_fallback import enrich_info, is_enabled, should_fill
            if is_enabled() and (degraded or should_fill(info)):
                info = enrich_info(info, symbol, degraded=degraded)
                degraded = _is_degraded(info)  # recomputar tras el relleno
        except Exception as e:
            logger.warning(f"[FINNHUB] enrich falló para {symbol}: {e}")

        # ── Fase 2b: serie diaria de precios y lo que el motor toma de ella (D5) ──
        _hist = price_history.collect(_hist_future)
        info["_price_history"] = price_history.summary(_hist)
        try:
            _apply_beta_and_range(info, _hist)
        except Exception as e:
            logger.error(f"[BETA] {symbol}: {e}")
            info["_beta"] = {"source": "error", "reason": f"{type(e).__name__}: {e}"}
        _apply_split_events(info, _hist)

        # ── Fase 2b (T3–T4): EDGAR: respaldo del mismo corte, fuente oficial (D7) y resultados publicados y aún no
        # incorporados (F2_PRECEDENCIA §1.1). Antes del dividendo: lo pagado del corte entra en su identidad. ──
        try:
            _apply_edgar(symbol, info, edgar.collect(_edgar_future, symbol), _hist, _info_ctx)
        except Exception as e:
            logger.error(f"[EDGAR] {symbol}: {e}")
            info["_edgar"] = {"status": "no_disponible", "reason": f"{type(e).__name__}: {e}"}
            info["_official_source"] = {"registered": None, "status": "no_disponible", "cik": None,
                                        "reason": f"{type(e).__name__}: {e}", "fy": None,
                                        "note": "verificación oficial no disponible"}

        try:
            import ordinary
            ordinary.apply(info)
        except Exception as e:
            logger.error(f"[ORDINARY] {symbol}: {e}")
            info["_ordinary"] = {"notes": [f"error: {type(e).__name__}: {e}"]}

        try:
            _apply_dividend(info, _hist)
        except Exception as e:
            logger.error(f"[DIVIDEND] {symbol}: {e}")
            info["_dividend"] = {"rate": None, "reason": f"error al calcular el dividendo: {type(e).__name__}: {e}"}
            info["dividendRate"] = info["dividendYield"] = None
            (info.get("_yahoo_ratios") or {})["dividendYield"] = None

        # ── Validación de entrada (lib/validate.py): después de toda la ingesta
        # y antes de cualquier cálculo del motor. Nunca corrige en silencio:
        # deja info["_validation"] y actualiza info["_provenance"].
        try:
            from validate import validate_info
            info = validate_info(info, symbol)
        except Exception as e:
            logger.error(f"[VALIDATE] validación de entrada falló para {symbol}: {e}")
            info["_validation"] = [{"field": "*", "rule": "validacion", "action": "aviso",
                                    "old": None, "new": None,
                                    "reason": f"la validación de entrada no se ejecutó: {e}"}]

        # ── Defensa 2: los snapshots degradados caducan rápido ──
        _cache[symbol] = (time.time(), info, degraded)
        return info


def _apply_edgar(symbol: str, info: Dict[str, Any], ed: Dict[str, Any], hist: Dict[str, Any], ctx=None) -> None:
    """Fase 2b: lo que el análisis toma de EDGAR (D2: verificación y respaldo).
      · T4: respaldo de lo que Yahoo no da del mismo corte (lib/edgar_backup.py) y fuente oficial del emisor (D7,
        info["_official_source"]);
      · T3: aviso de resultados publicados después del corte (info["_pending_results"]): por los filings de EDGAR o,
        sin 8-K (20-F) o sin EDGAR, por el calendario de resultados del proveedor. No mezcla periodos ni baja la
        confianza: solo avisa.
    Resumen en info["_edgar"] (sin los hechos)."""
    import datetime as _dt
    import edgar_backup
    import sec_edgar as edgar
    frame = (hist or {}).get("frame")
    today = frame.index[-1].date() if frame is not None else _dt.date.today()
    info["_edgar"] = edgar.summary(ed)
    info["_edgar"]["backup"] = edgar_backup.apply(info, ed, ctx)
    info["_ebit"] = edgar_backup.ebit_check(info, ed, ctx)     # F2_PRECEDENCIA §2.1: EBIT "estimado por la fuente"
    import debt
    info["_debt"] = debt.apply(info, ed, ctx)          # T5: deuda coherente con el EBITDA
    import perimeter
    from settings import cfg as _cfg
    info["_perimeter"] = perimeter.detect(info, ed, ctx, _cfg("data.edgar.report_date_tolerance_days"))   # T7
    info["_official_source"] = edgar_backup.official_source(ed, today)
    cut = (info.get("_as_of") or {}).get("date")
    pend = edgar.pending_results(ed.get("filings"), cut) if ed.get("status") == "ok" else None
    if pend is None and cut and (ed.get("status") != "ok" or edgar.foreign_filer(ed.get("filings"))):
        from finnhub_fallback import earnings_calendar, is_enabled
        if is_enabled():
            start = (_dt.date.fromisoformat(cut) + _dt.timedelta(days=1)).isoformat()
            pend = edgar.pending_from_calendar(earnings_calendar(symbol, start, today.isoformat()), cut, today)
    info["_pending_results"] = pend


def _apply_beta_and_range(info: Dict[str, Any], hist: Dict[str, Any]) -> None:
    """Fase 2b (T6, D5): la beta y el rango de 52 semanas salen de la serie de precios (lib/beta.py). La beta de la
    fuente queda como contraste (o como respaldo, con aviso, si no hay serie); el rango de la fuente no se usa: sin
    serie, sin dato."""
    import beta as beta_mod
    frame = (hist or {}).get("frame")
    src = info.get("beta")
    src_name = ((info.get("_provenance") or {}).get("beta") or {}).get("source")
    ch = beta_mod.choose(beta_mod.own_beta(frame, (hist or {}).get("market")), src, src_name,
                         info.get("sector"), info.get("industry"))
    info["_beta"] = ch
    info["beta"] = ch["value"]
    if ch["source"] in ("propia", "sector"):
        _tag_provenance(info, "derivado", ch["reason"], paths=["beta"], overwrite=True)
    elif ch["source"] == "sin_dato":
        _tag_provenance(info, "sin_dato", ch["reason"], paths=["beta"], overwrite=True)
    else:
        _tag_provenance(info, src_name or "finnhub", ch["reason"], paths=["beta"], overwrite=True)
    price = info.get("currentPrice") or info.get("regularMarketPrice")
    rg = beta_mod.range_52w(frame, price)
    info["_range52"] = rg
    info["fiftyTwoWeekHigh"], info["fiftyTwoWeekLow"] = rg["high"], rg["low"]
    if rg["status"] == "ok":
        _tag_provenance(info, "derivado",
                        f"máximo y mínimo diarios de las {rg['sessions']} sesiones de la serie ({rg['first_session']} a "
                        f"{rg['last_session']}, Yahoo history)", paths=["fiftyTwoWeekHigh", "fiftyTwoWeekLow"],
                        overwrite=True)
    else:
        _tag_provenance(info, "sin_dato", rg["reason"], paths=["fiftyTwoWeekHigh", "fiftyTwoWeekLow"], overwrite=True)


def _apply_split_events(info: Dict[str, Any], hist: Dict[str, Any]) -> None:
    """Fase 2b (T7): el plan B (sin quoteSummary) no trae `lastSplitFactor`, que la regla de base de splits de validate
    necesita para llevar las acciones del año previo a la base actual. Sale del último evento de split de la serie de
    precios (un evento societario, como los pagos de dividendo de T2; no una señal técnica). Solo si la fuente no lo
    da. Una escisión aparece como split no entero (UL 0.888 el 2025-12-09) y se declara igual: la regla solo lo
    aplica si casa con el salto de acciones."""
    if info.get("lastSplitFactor"):
        return
    frame = (hist or {}).get("frame")
    if frame is None or "split" not in frame:
        return
    ev = frame["split"][frame["split"] > 0]
    if ev.empty:
        return
    from fractions import Fraction
    day, v = ev.index[-1], float(ev.iloc[-1])
    fr = Fraction(v).limit_denominator(1000)
    info["lastSplitFactor"] = f"{fr.numerator}:{fr.denominator}"
    info["lastSplitDate"] = int(day.timestamp())
    _tag_provenance(info, "derivado", f"último evento de split de la serie de precios ({day.date()}, ×{v:g}; Yahoo "
                    "history): la fuente no lo da", paths=["lastSplitFactor", "lastSplitDate"], overwrite=True)


def _foreign_line(cur: Dict[str, Any]) -> bool:
    """Fase 2b: la cotización no es la línea local del emisor (ADR u otra moneda en los estados). Finnhub da entonces
    el dividendo de la línea local, en su moneda y por acción ordinaria, en una unidad que no declara."""
    from currency import is_adr
    sc = cur.get("share_class") or {}
    return bool(cur.get("converted")) or bool(sc.get("applied") and sc.get("basis") != "oficial") \
        or is_adr(sc.get("official") if sc.get("basis") == "oficial" else None)


def _apply_dividend(info: Dict[str, Any], hist: Dict[str, Any]) -> None:
    """Fase 2b (T2): el dividendo indicado en la moneda y la clase del precio (lib/dividends.py) sustituye al de la
    fuente; el dividend yield sale de él y del precio. Deja info["_dividend"] (-> data_provenance.dividend)."""
    import datetime as _dt
    import dividends
    import price_history
    cur = info.get("_currency") or {}
    sc = cur.get("share_class") or {}
    foreign = _foreign_line(cur)
    price = info.get("currentPrice") or info.get("regularMarketPrice")
    mcap = info.get("marketCap")
    units = (mcap / price) if (mcap and price) else info.get("sharesOutstanding")
    paid = info.get("dividendsPaid")
    _ao = info.get("_as_of") or {}
    _pp = ((_ao.get("fields") or {}).get("dividendsPaid") or {}).get("period_end")
    if _ao.get("date") and _pp not in (None, _ao.get("date")):
        paid = None                      # fase 2b (T3): lo pagado de otro periodo no se compara (se descarta)
    paid_per_unit = (abs(paid) / units) if (paid and units) else None
    src_rate = info.get("dividendRate")
    src_name = ((info.get("_provenance") or {}).get("dividendRate") or {}).get("source")
    frame = hist.get("frame")
    as_of = frame.index[-1].date() if frame is not None else _dt.date.today()
    events = price_history.dividend_events(frame) if frame is not None else None
    candidates = []
    spot = (cur.get("spot_rate") or {}).get("rate")
    factor = sc.get("factor") if sc.get("applied") else 1.0
    if foreign and src_rate and spot and factor:
        fin, px = cur.get("statements"), cur.get("price")
        candidates = [(src_rate * factor * spot,
                       f"{src_rate:g} {fin} por acción × {factor:g} acciones por título × {spot:.4g} {px}/{fin}"),
                      (src_rate / 100.0 * factor * spot,
                       f"{src_rate:g} céntimos de {fin} por acción × {factor:g} acciones por título × {spot:.4g} "
                       f"{px}/{fin}")]
    from currency import is_adr
    unit = "ADR" if (foreign and (sc.get("applied") and sc.get("basis") != "oficial"
                                  or is_adr(sc.get("official") if sc.get("basis") == "oficial" else None))) \
        else "título"
    res = dividends.assess(events, as_of, src_rate, src_name, foreign, paid_per_unit, candidates,
                           currency=info.get("currency") or "USD", unit=unit)
    res["as_of"] = as_of.isoformat()
    rate = res.get("rate")
    dy = (rate / price) if (rate is not None and price) else None
    info["dividendRate"] = rate
    info["dividendYield"] = dy
    yr = info.get("_yahoo_ratios")
    if isinstance(yr, dict):
        yr["dividendYield"] = dy
    info["_dividend"] = res
    detail = {"pagos": "pagos del propio título en la serie de precios (Yahoo)",
              "fuente_local_convertida": "dividendo de la línea local convertido a la clase y la moneda del precio",
              "sin_dividendo": "no paga dividendos: sin pagos en 2 años ni dividendos en los estados"}.get(res.get("source"), f"{res.get('source')}: indicado declarado, verificado con los pagos")
    if rate is None:
        _tag_provenance(info, "sin_dato", res.get("reason") or "sin dividendo",
                        paths=["dividendRate", "dividendYield", "_yahoo_ratios.dividendYield"], overwrite=True)
    else:
        _tag_provenance(info, res.get("source") if res.get("source") in ("finnhub", "yahoo_quotesummary")
                        else "derivado", detail, paths=["dividendRate"], overwrite=True)
        _tag_provenance(info, "derivado", "dividendo indicado / precio",
                        paths=["dividendYield", "_yahoo_ratios.dividendYield"], overwrite=True)


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
        filled = []
        for k, v in best.items():
            if k in _NESTED_KEYS:
                continue
            if merged.get(k) is None and v is not None:
                merged[k] = v
                filled.append(k)
        for nk in _NESTED_KEYS:
            bsub = best.get(nk)
            if not isinstance(bsub, dict):
                continue
            msub = dict(merged.get(nk) or {})
            for k, v in bsub.items():
                if msub.get(k) is None and v is not None:
                    msub[k] = v
                    filled.append(f"{nk}.{k}")
            merged[nk] = msub
        if filled:
            merged["_provenance"] = dict(merged.get("_provenance") or {})
            _tag_provenance(merged, "derivado",
                            f"último snapshot bueno conocido (hace {int(now - ts_best)} s)",
                            paths=[p for p in filled if not p.startswith("_") or "." in p],
                            overwrite=True)
            logger.info(f"[LKG] {symbol}: {len(filled)} campos rellenados del último snapshot bueno")

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

    global _qs_blocked_until
    if time.time() < _qs_blocked_until:
        logger.info(f"[PLAN B] quoteSummary bloqueado (401 reciente): {symbol} va directo al plan B")
        return _fallback_yfinance(symbol)

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
        r = _session.get(url, params=params, timeout=_D["http_timeout_s"])
    except Exception as e:
        logger.error(f"Yahoo API request failed for {symbol}: {e}")
        return _fallback_yfinance(symbol)

    if r.status_code != 200:
        logger.warning(f"Yahoo API {r.status_code} for {symbol}, refreshing crumb...")
        _refresh_crumb()
        params["crumb"] = _crumb
        try:
            r = _session.get(url, params=params, timeout=_D["http_timeout_s"])
        except Exception:
            pass

        if r.status_code != 200:
            logger.error(f"Yahoo API failed for {symbol}: {r.status_code}")
            if r.status_code == 401:   # crumb rechazado aun refrescado: bloqueo de la IP, no del símbolo
                _qs_blocked_until = time.time() + _QS_BLOCK_TTL
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

    # Etapa 11b: moneda de los estados (financialData) frente a la de la cotización.
    _fin_cur = fd.get("financialCurrency") or (data.get("earnings") or {}).get("financialCurrency")
    ctx = _new_statement_context(symbol, price_data.get("currency"), _fin_cur,
                                 "financialData.financialCurrency" if _fin_cur
                                 else "no verificada (se asume la de la cotización)",
                                 market_cap, current_price, shares)

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
        # Etapa 11b: tipo de instrumento (EQUITY, ETF, MUTUALFUND…); main rechaza lo que no es acción.
        "quoteType": price_data.get("quoteType"),
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

        # Último split (para la regla de base de splits de lib/validate.py)
        "lastSplitFactor": _raw(kstat.get("lastSplitFactor")),
        "lastSplitDate": _raw(kstat.get("lastSplitDate")),

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
            # PEG de mercado de Yahoo (usa crecimiento FORWARD de consenso); se
            # prefiere en main.py sobre el PEG trailing que calcula el motor.
            "pegRatio": _raw(kstat.get("pegRatio")),
        },
    }

    if ctx.convert_currency:
        _restate_quote_summary(info, ctx)
    # Etapa 11b: beneficio de la MISMA fuente y ventana que trailingEps (defaultKeyStatistics),
    # para la regla BPA × acciones ≈ beneficio (el TTM de los estados puede ir un trimestre atrás).
    info["_eps_net_income"] = info.get("netIncome")

    # ── Enrich prior-year data with yfinance (historical statements) ──
    from currency import CurrencyConversionError
    try:
        info = _enrich_prior_year_data(symbol, info)
        info = _apply_ttm(symbol, info, plan_b=False)
    except CurrencyConversionError:
        raise
    except Exception as e:
        logger.warning(f"[ENRICH] Prior-year enrichment failed for {symbol}: {e}")
        _tag_provenance(info, "sin_dato", f"estados anuales de yfinance: {e}",
                        paths=["_prior_year", "_piotroski_current"], overwrite=True)
    if ctx.class_applied:
        _restate_share_class(info, ctx)
    info["_data_path"] = "yahoo_quotesummary"
    _tag_provenance(info, "yahoo_quotesummary", "quoteSummary v10 (con crumb)")

    elapsed = time.time() - t0
    logger.info(f"[FAST API] get_ticker_info({symbol}) in {elapsed:.2f}s")

    # Sin escribir _cache aquí: solo get_ticker_info cachea, DESPUÉS de LKG,
    # Finnhub y la validación de entrada. Una escritura aquí exponía el dict sin
    # validar al hilo paralelo de perfil (lee la caché fuera del lock).
    return info


# Filas de partidas no recurrentes de Yahoo (lib/normalize.py).
_UNUSUAL_ROWS = (
    "Total Unusual Items", "Total Unusual Items Excluding Goodwill", "Special Income Charges",
    "Other Special Charges", "Restructuring And Mergern Acquisition", "Gain On Sale Of Security",
    "Gain On Sale Of Ppe", "Gain On Sale Of Business", "Write Off", "Asset Impairment Charge",
    "Impairment Of Capital Assets", "Tax Effect Of Unusual Items",
)


# Importes de financialData / *History de quoteSummary (moneda de los estados).
_QS_FLOW_KEYS = ("totalRevenue", "grossProfits", "operatingIncome", "netIncome", "ebitda", "interestExpense",
                 "depreciation", "operatingCashflow", "capitalExpenditures", "freeCashflow", "dividendsPaid")
_QS_BALANCE_KEYS = ("totalAssets", "totalCurrentAssets", "totalCurrentLiabilities", "totalDebt", "longTermDebt",
                    "totalStockholderEquity", "totalLiab", "cash", "retainedEarnings", "inventory")
# Ratios que Yahoo calcula mezclando la capitalización (cotización) con los estados.
_QS_MIXED_RATIOS = ("enterpriseValue", "enterpriseToEbitda", "enterpriseToRevenue", "priceToBook")


def _restate_quote_summary(info: Dict[str, Any], ctx) -> None:
    """Etapa 11b, ruta quoteSummary: los importes de financialData y de los módulos
    *History vienen en la moneda de los estados. Flujos (TTM) al promedio de los 12
    meses; balance al último cierre; año previo al del ejercicio anterior. Los estados
    de yfinance (ya convertidos por período) y el TTM trimestral los sustituyen
    después donde haya dato. Los ratios mixtos de Yahoo se descartan (el motor los
    recalcula con cifras en una sola moneda)."""
    import pandas as pd
    for k in _QS_FLOW_KEYS:
        info[k] = ctx.convert_amount(info.get(k), "flow")
    for k in _QS_BALANCE_KEYS:
        info[k] = ctx.convert_amount(info.get(k), "balance")
    py = info.get("_prior_year") or {}
    end_prev = (ctx.fx.closes.index[-1] - pd.DateOffset(years=1)) if ctx.fx is not None else None
    for k in ("net_income", "operating_cash_flow", "revenue"):
        py[k] = ctx.convert_amount(py.get(k), "flow", end_prev)
    for k in ("total_assets", "long_term_debt", "equity"):
        py[k] = ctx.convert_amount(py.get(k), "balance", end_prev)
    yr = info.get("_yahoo_ratios") or {}
    for k in _QS_MIXED_RATIOS:
        yr[k] = None
    info["priceToBook"] = None
    eq, sh = info.get("totalStockholderEquity"), ctx.price_shares or info.get("sharesOutstanding")
    info["bookValue"] = (eq / sh) if (eq is not None and sh) else None
    info["_yearly_financials"] = []
    _tag_provenance(info, "derivado",
                    f"convertido de {ctx.statement_currency} a {ctx.price_currency} (tipo de cambio de Yahoo)",
                    paths=[k for k in _QS_FLOW_KEYS + _QS_BALANCE_KEYS + ("bookValue",) if info.get(k) is not None],
                    overwrite=True)


def _restate_share_class(info: Dict[str, Any], ctx) -> None:
    """Etapa 11b, ruta quoteSummary con los estados en otra clase de acciones (BRK-B):
    el valor en libros por acción y los ratios de Yahoo por acción vienen en la clase
    de los estados; se rehacen con las acciones de la clase que cotiza."""
    eq, sh = info.get("totalStockholderEquity"), ctx.price_shares or info.get("sharesOutstanding")
    info["bookValue"] = (eq / sh) if (eq is not None and sh) else None
    info["priceToBook"] = None
    yr = info.get("_yahoo_ratios") or {}
    for k in _QS_MIXED_RATIOS:
        yr[k] = None
    _tag_provenance(info, "derivado", "patrimonio / acciones de la clase que cotiza (los estados usan otra clase)",
                    paths=["bookValue"], overwrite=True)


def _as_of(info: Dict[str, Any], t: Dict[str, Any], plan_b: bool) -> Dict[str, Any]:
    """Fase 2b (T3, F2_PRECEDENCIA §1): el corte del análisis y el periodo de cada campo de los estados.

    Con corte trimestral, los flujos del corte son TTM (4 trimestres que acaban en él) y el balance es el de esa
    fecha; un campo que no llega al corte conserva el valor de la fuente con SU periodo (el ejercicio en el plan B),
    y validate (periodo_incoherente) lo descarta. Sin corte trimestral, el corte es el último ejercicio."""
    from ttm import BALANCE_KEYS, FLOW_KEYS
    fy = info.get("_fy_dates") or {}
    cut = t.get("cut")
    fields: Dict[str, Dict[str, Any]] = {}
    for key, (st, _row) in FLOW_KEYS.items():
        if key in t["values"]:
            fields[key] = {"period_end": cut, "period_type": "ttm"}
        elif info.get(key) is not None:
            fields[key] = ({"period_end": fy.get(st), "period_type": "fy"} if plan_b
                           else {"period_end": None, "period_type": "fuente"})
    for key in (*BALANCE_KEYS, "cash"):
        if key in t["values"]:
            fields[key] = {"period_end": cut, "period_type": "balance"}
        elif info.get(key) is not None:
            fields[key] = ({"period_end": fy.get("bs"), "period_type": "fy_balance"} if plan_b
                           else {"period_end": None, "period_type": "fuente"})
    if cut:
        return {"type": "ttm", "date": cut, "fields": fields}
    return {"type": "fy" if plan_b else "fuente", "date": fy.get("inc") if plan_b else None, "fields": fields,
            "reason": "sin corte trimestral: ingresos y beneficio de 4 trimestres consecutivos con balance"}


def _apply_ttm(symbol: str, info: Dict[str, Any], plan_b: bool) -> Dict[str, Any]:
    """Etapa 7: TTM desde los estados TRIMESTRALES de yfinance (lib/ttm.py).

    Flujos = suma de 4 trimestres consecutivos; balance = último trimestre. Lo
    que no tenga 4 trimestres consecutivos conserva el valor de la fuente (anual
    en el plan B) y queda registrado en info["_ttm"] (-> data_provenance.ttm).
    En el plan B el BPA anual pasa a BPA TTM = beneficio TTM / acciones diluidas
    medias del último trimestre (en la ruta quoteSummary el BPA ya es TTM)."""
    from ttm import build_ttm, FLOW_KEYS
    frames, errors = {}, []
    try:
        from currency import CurrencyConversionError
        ticker = _stmt_ticker(symbol)
        for attr in ("quarterly_income_stmt", "quarterly_cashflow", "quarterly_balance_sheet"):
            try:
                frames[attr] = getattr(ticker, attr)
            except CurrencyConversionError:
                raise
            except Exception as e:
                frames[attr] = None
                errors.append(f"{attr}: {type(e).__name__}")
    except Exception as e:
        if type(e).__name__ == "CurrencyConversionError":
            raise
        errors.append(f"yfinance: {type(e).__name__}")
    t = build_ttm(frames.get("quarterly_income_stmt"), frames.get("quarterly_cashflow"),
                  frames.get("quarterly_balance_sheet"))
    info["_as_of"] = _as_of(info, t, plan_b)
    if t.get("ordinary"):
        info["_ordinary_src"] = {**t["ordinary"], "period_type": "ttm"}   # fase 2b (T7): lib/ordinary.py
    flows = [k for k in t["values"] if k in FLOW_KEYS]
    balance = [k for k in t["values"] if k not in FLOW_KEYS]
    for k, v in t["values"].items():
        info[k] = v
    if "netInterestIncome" in t.get("quarter_min", {}):   # fase 1: signo estable del resultado financiero
        info["_netInterestIncomeMinQ"] = t["quarter_min"]["netInterestIncome"]
    if flows:
        _tag_provenance(info, "yfinance_statements",
                        f"TTM: suma de los 4 trimestres {', '.join(t['quarters'].get('inc') or t['quarters'].get('cf') or [])}",
                        paths=flows, overwrite=True)
    if balance:
        _tag_provenance(info, "yfinance_statements", f"balance del último trimestre ({t['balance_date']})",
                        paths=balance, overwrite=True)
    eps_basis = "fuente"
    q = t["quarterly"]
    _eps = t.get("eps")
    if plan_b and "netIncome" in t["values"] and _eps:
        info["trailingEps"] = _eps["value"]
        info["_eps_net_income"] = t["values"]["netIncome"]   # etapa 11b: por construcción
        eps_basis = "ttm"
        _tag_provenance(info, "derivado",
                        "BPA TTM = suma de los BPA diluidos de los 4 trimestres del corte"
                        if _eps["basis"] == "suma_bpa_trimestral" else
                        "BPA TTM = beneficio neto TTM / media de las acciones diluidas de los 4 trimestres del corte",
                        paths=["trailingEps"], overwrite=True)
    shares = info.get("sharesOutstanding")
    if plan_b and "totalStockholderEquity" in t["values"] and shares:
        info["bookValue"] = t["values"]["totalStockholderEquity"] / shares
    info["_quarterly"] = q
    info["_ttm"] = {
        "basis": "ttm" if flows else ("anual" if plan_b else "fuente"),
        "cut": t.get("cut"), "quarters": t["quarters"], "balance_date": t["balance_date"],
        "ttm_fields": sorted(flows), "last_quarter_fields": sorted(balance),
        "annual_fields": ({k: v for k, v in t["missing"].items()} if plan_b else {}),
        "source_fields": ({} if plan_b else {k: v for k, v in t["missing"].items()}),
        "eps": eps_basis, "errors": errors,
    }
    return info


def _enrich_prior_year_data(symbol: str, info: Dict[str, Any], ticker=None) -> Dict[str, Any]:
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
    # Etapa 11b: estados en la moneda y la clase de la cotización. El plan B pasa su propio
    # Ticker (ya descargó los anuales): con uno nuevo se volvían a bajar los tres.
    ticker = ticker if ticker is not None else _stmt_ticker(symbol)

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
    from currency import CurrencyConversionError
    try:
        inc = ticker.income_stmt
        bs = ticker.balance_sheet
        cf = ticker.cashflow
    except CurrencyConversionError:
        raise
    except Exception as e:
        logger.debug(f"[ENRICH] yfinance statement fetch failed: {e}")
        return info

    # Fase 2b: Yahoo mete a veces en los estados ANUALES columnas interinas sin las cifras del ejercicio (TM: 2025-09-30
    # y 2025-06-30 entre el FY2026 y el FY2025, con solo acciones medias y BPA). No son ejercicios: se descartan las
    # columnas sin las filas núcleo del estado (las del corte trimestral, lib/ttm.py), y el FY1 vuelve a ser el
    # ejercicio anterior (Piotroski, CAGR, Altman).
    from ttm import CORE_ROWS, CF_CORE_ROW

    def _drop_empty(df, name, core):
        if df is None or getattr(df, "empty", True):
            return df
        rows = [r for r in core if r in df.index]
        empty = [c for c in df.columns if not rows or not df.loc[rows, c].notna().any()]
        if empty and len(empty) < len(df.columns):
            logger.info(f"[ENRICH] {symbol}: columnas anuales sin {', '.join(core)} en {name}: "
                        f"{', '.join(str(getattr(c, 'date', lambda: c)()) for c in empty)}")
            df = df.drop(columns=empty)
        return df
    inc = _drop_empty(inc, "resultados", CORE_ROWS)
    bs = _drop_empty(bs, "balance", ("Total Assets",))
    cf = _drop_empty(cf, "flujos", (CF_CORE_ROW,))

    has_inc = inc is not None and not inc.empty and len(inc.columns) >= 2
    has_bs = bs is not None and not bs.empty and len(bs.columns) >= 2
    has_cf = cf is not None and not cf.empty and len(cf.columns) >= 2

    # Fase 2b (T3): fecha de cierre del último ejercicio de cada estado (periodo de los campos anuales del plan B).
    def _last_date(df):
        try:
            return str(df.columns[0].date()) if df is not None and not df.empty else None
        except Exception:
            return None
    info["_fy_dates"] = {"inc": _last_date(inc), "bs": _last_date(bs), "cf": _last_date(cf)}

    if not (has_inc or has_bs or has_cf):
        return info

    # Series anuales (más reciente primero) para la capa de validación
    # (lib/validate.py): recalcular "por definición desde los estados" (FCF =
    # OCF − capex), comprobar saltos interanuales, base de splits y CAGR.
    def _row(df, key, n=5):
        if df is None or df.empty or key not in df.index:
            return []
        out = []
        for v in df.loc[key].tolist()[:n]:
            try:
                f = float(v)
                out.append(f if f == f else None)
            except (TypeError, ValueError):
                out.append(None)
        return out

    def _years(df):
        try:
            return [str(c.year) for c in df.columns][:5] if df is not None and not df.empty else []
        except Exception:
            return []

    def _ends(df):
        try:
            return [str(c.date()) for c in df.columns][:5] if df is not None and not df.empty else []
        except Exception:
            return []

    info["_statements_fy"] = {
        "inc_years": _years(inc), "bs_years": _years(bs), "cf_years": _years(cf),
        # Fase 2b (T4): fecha de cierre de cada ejercicio (el respaldo de EDGAR casa por fecha, no por año)
        "inc_ends": _ends(inc), "bs_ends": _ends(bs), "cf_ends": _ends(cf),
        "revenue": _row(inc, "Total Revenue"),
        "gross_profit": _row(inc, "Gross Profit"),   # etapa 9b: margen bruto en el histórico
        "net_income": _row(inc, "Net Income"),
        "diluted_eps": _row(inc, "Diluted EPS"),   # etapa 9a: CAGR 3 años del BPA
        "ordinary_shares": _row(bs, "Ordinary Shares Number"),
        "total_assets": _row(bs, "Total Assets"),
        "operating_cash_flow": _row(cf, "Operating Cash Flow"),
        "capital_expenditure": _row(cf, "Capital Expenditure"),
        # Etapa 8: D&A (o DD&A en extractivas) para el capex de mantenimiento de CYCLICAL.
        "depreciation_amortization": next((x for x in (_row(cf, r) for r in (
            "Depreciation And Amortization", "Depreciation Amortization Depletion", "Depreciation")) if x), []),
        "free_cash_flow": _row(cf, "Free Cash Flow"),
        "stock_based_compensation": _row(cf, "Stock Based Compensation"),   # etapa 9a: FCF − SBC
        # Etapa 6 (clasificador, ramas por arquetipo y ROCE): series anuales
        # adicionales; una fila ausente queda como lista vacía (sin dato).
        "operating_income": _row(inc, "Operating Income"),
        "ebit": _row(inc, "EBIT"),
        "ebitda": _row(inc, "EBITDA"),
        "current_liabilities": _row(bs, "Current Liabilities"),
        "stockholders_equity": _row(bs, "Stockholders Equity"),
        "tangible_book_value": _row(bs, "Tangible Book Value"),
        # Fase 2b (T7): desglose del accionista ordinario por ejercicio (ROTE ajustado por AT1, fase 3).
        "net_income_common": _row(inc, "Net Income Common Stockholders"),
        "common_stock_equity": _row(bs, "Common Stock Equity"),
        "other_equity_interest": _row(bs, "Other Equity Interest"),
        # Fase 2b (T7): operaciones discontinuadas por ejercicio (lib/perimeter.py).
        "net_income_discontinued": _row(inc, "Net Income Discontinuous Operations"),
        # gastos no financieros de un banco (ratio de eficiencia aproximado)
        "non_interest_expense": _row(inc, "Non Interest Expense"),
        "sga": _row(inc, "Selling General And Administration"),
        "occupancy": _row(inc, "Occupancy And Equipment"),
        "professional_services": _row(inc, "Professional Expense And Contract Services Expense"),
        "other_non_interest_expense": _row(inc, "Other Non Interest Expense"),
        # Etapa 7: Altman con el último FY (se define sobre ejercicios, no TTM) y
        # partidas no recurrentes del FY para normalizar sin trimestrales.
        "current_assets": _row(bs, "Current Assets"),
        "total_liabilities": _row(bs, "Total Liabilities Net Minority Interest"),
        "retained_earnings": _row(bs, "Retained Earnings"),
        "pretax_income": _row(inc, "Pretax Income"),
        "tax_provision": _row(inc, "Tax Provision"),
        "unusual_fy0": {r: (_row(inc, r) or [None])[0] for r in _UNUSUAL_ROWS if _row(inc, r)},
        "unusual_fy": {r: _row(inc, r) for r in _UNUSUAL_ROWS if _row(inc, r)},   # recurrencia (etapa 7)
    }

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
        # Acciones EN CIRCULACIÓN (Ordinary Shares Number) antes que emitidas
        # (Share Issued incluye autocartera: NFLX 4.53->4.57B emitidas mientras
        # las en circulación bajaban 4.28->4.22B por recompras).
        cur_shares = _sf(cur_bs, "Ordinary Shares Number") or _sf(cur_bs, "Share Issued")

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

        # Inventory para inventory_turnover: el v10 balanceSheetHistory casi
        # nunca lo trae, pero yfinance sí. Retail/consumo lo necesitan (COGS ya
        # se deriva de revenue-gross_profit). En producción (yfinance bloqueado)
        # el hueco lo cubre el inventoryTurnover de Finnhub vía el fallback_map.
        if info.get("inventory") is None:
            _cur_inv = _sf(cur_bs, "Inventory")
            if _cur_inv is not None:
                info["inventory"] = _cur_inv

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
        prev_shares = _sf(prev_bs, "Ordinary Shares Number") or _sf(prev_bs, "Share Issued")
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
    _tag_provenance(info, "yfinance_statements",
                    f"estados anuales de yfinance (FY{fy_current} / FY{fy_prior})",
                    paths=[f"{blk}.{k}" for blk, d in (("_prior_year", prior),
                                                       ("_current_derived", derived),
                                                       ("_piotroski_current", piotroski_current))
                           for k, v in d.items() if v is not None and not str(k).startswith("_")],
                    overwrite=True)

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

    # Etapa 11b: moneda de los estados (fundamentals-timeseries; quoteSummary da 401 en
    # Render) y clase de acciones: los estados se leen ya reexpresados a la cotización.
    _fin_cur = _statement_currency(symbol)
    _ctx = _new_statement_context(symbol, fi.get("currency"), _fin_cur,
                                  "fundamentals-timeseries (currencyCode)" if _fin_cur
                                  else "no verificada (se asume la de la cotización)",
                                  fi.get("marketCap"), fi.get("lastPrice"), fi.get("shares"))
    ticker = _StatementsTicker(ticker, _ctx)
    # El factor de clase necesita el balance anual: se lee ya (el mismo Ticker lo cachea para
    # _get_bs). Si lo calculara el primer hilo que convierte, el balance se bajaría dos veces.
    try:
        _ctx.prepare_class(ticker._t.balance_sheet)
    except Exception:
        _ctx.prepare_class(None)

    info: Dict[str, Any] = {
        "symbol": symbol,
        "regularMarketPrice": fi.get("lastPrice"),
        "currentPrice": fi.get("lastPrice"),
        "marketCap": fi.get("marketCap"),
        "currency": fi.get("currency", "USD"),
        "quoteType": fi.get("quoteType"),   # etapa 11b (ver _do_fetch)
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

    # Sector/industria DE LA FUENTE: en prod quoteSummary (assetProfile) da 401,
    # pero la búsqueda de Yahoo no exige crumb y sí trae sector e industria.
    # KNOWN_SECTORS queda solo como respaldo marcado si la búsqueda falla.
    prof = _search_profile(symbol)
    if prof and prof.get("sector"):
        info["sector"] = prof["sector"]
        info["industry"] = prof.get("industry") or "Unknown"
        info["_profile_source"] = "yahoo_search"
        _tag_provenance(info, "yahoo_quotesummary",
                        "búsqueda de Yahoo /v1/finance/search (sin crumb; no es quoteSummary)",
                        paths=["sector", "industry"])
    else:
        sd = KNOWN_SECTORS.get(symbol)
        info["sector"] = sd[0] if sd else "Unknown"
        info["industry"] = sd[1] if sd else "Unknown"
        info["_profile_source"] = "known_sectors" if sd else "sin_dato"
        if sd:
            _tag_provenance(info, "derivado", "lista fija KNOWN_SECTORS (búsqueda no disponible)",
                            paths=["sector", "industry"])
        else:
            _tag_provenance(info, "sin_dato", "búsqueda no disponible y ticker fuera de KNOWN_SECTORS",
                            paths=["sector", "industry"])

    try:
        from stock_database import POPULAR_STOCKS
        info["longName"] = (POPULAR_STOCKS.get(symbol)
                            or (prof or {}).get("name") or symbol)
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
                "Depreciation And Amortization", "Net Non Operating Interest Income Expense",
                "Net Income Common Stockholders"
            ]}
        return {}

    def _get_bs():
        bs = ticker.balance_sheet
        if bs is not None and not bs.empty:
            latest = bs.iloc[:, 0]
            result = {k: _sg(latest, k) for k in [
                "Total Assets", "Current Assets", "Current Liabilities",
                "Total Debt", "Long Term Debt", "Stockholders Equity", "Capital Lease Obligations", "Commercial Paper",
                "Common Stock Equity", "Other Equity Interest",
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
        from currency import CurrencyConversionError
        for f in as_completed(futs, timeout=_D["statements_timeout_s"]):
            key = futs[f]
            try:
                results[key] = f.result()
            except CurrencyConversionError:
                raise
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
    info["_eps_net_income"] = inc.get("Net Income")   # etapa 11b: mismo ejercicio que el BPA
    info["interestExpense"] = inc.get("Interest Expense")
    info["netInterestIncome"] = inc.get("Net Non Operating Interest Income Expense")   # fase 1
    info["depreciation"] = inc.get("Depreciation And Amortization")

    bs = results.get("balance", {})
    info["totalAssets"] = bs.get("Total Assets")
    info["totalCurrentAssets"] = bs.get("Current Assets")
    info["totalCurrentLiabilities"] = bs.get("Current Liabilities")
    info["totalDebt"] = bs.get("Total Debt")
    info["capitalLeaseObligations"] = bs.get("Capital Lease Obligations")   # fase 2b (T5): lib/debt.py
    info["commercialPaper"] = bs.get("Commercial Paper")
    info["longTermDebt"] = bs.get("Long Term Debt")
    info["totalStockholderEquity"] = bs.get("Stockholders Equity")
    info["totalLiab"] = bs.get("Total Liabilities Net Minority Interest")
    info["cash"] = bs.get("Cash And Cash Equivalents")
    info["retainedEarnings"] = bs.get("Retained Earnings")
    info["inventory"] = bs.get("Inventory")  # _get_bs ya lo recolecta (inventory_turnover)
    # Fase 2b (T7): desglose del accionista ordinario del ejercicio (lib/ordinary.py); el TTM lo sustituye si hay corte.
    info["_ordinary_src"] = {"period_type": "fy", "netIncomeToCommon": inc.get("Net Income Common Stockholders"),
                             "commonStockEquity": bs.get("Common Stock Equity"),
                             "otherEquityInterest": bs.get("Other Equity Interest")}

    cf = results.get("cashflow", {})
    info["operatingCashflow"] = cf.get("Operating Cash Flow")
    info["capitalExpenditures"] = cf.get("Capital Expenditure")
    info["freeCashflow"] = cf.get("Free Cash Flow")
    info["dividendsPaid"] = cf.get("Common Stock Dividend Paid")

    if not info.get("freeCashflow") and info.get("operatingCashflow") and info.get("capitalExpenditures"):
        info["freeCashflow"] = info["operatingCashflow"] + info["capitalExpenditures"]
        _tag_provenance(info, "derivado", "OCF + capex (FY) por falta de 'Free Cash Flow'",
                        paths=["freeCashflow"])

    shares = info.get("sharesOutstanding")
    equity = info.get("totalStockholderEquity")
    if shares and equity and shares > 0:
        info["bookValue"] = equity / shares
        _tag_provenance(info, "derivado", "patrimonio (FY) / acciones de fast_info", paths=["bookValue"])

    # Año previo para Piotroski/buyback: en el plan B (camino permanente de prod)
    # no se ejecutaba y _prior_year solo tenía lo que aportaba Finnhub, sin
    # acciones. Los estados anuales de yfinance (sin crumb) sí están disponibles.
    try:
        info = _enrich_prior_year_data(symbol, info, ticker=ticker)
        info = _apply_ttm(symbol, info, plan_b=True)
    except CurrencyConversionError:
        raise
    except Exception as e:
        logger.warning(f"[ENRICH] Prior-year enrichment (fallback) failed for {symbol}: {e}")
        _tag_provenance(info, "sin_dato", f"estados anuales de yfinance: {e}",
                        paths=["_prior_year", "_piotroski_current"], overwrite=True)
    info["_data_path"] = "plan_b_yfinance"
    _tag_provenance(info, "yfinance_statements", "plan B: yfinance fast_info (sin crumb)",
                    paths=[k for k in ("regularMarketPrice", "currentPrice", "marketCap", "currency",
                                       "exchange", "fiftyTwoWeekHigh", "fiftyTwoWeekLow", "shares",
                                       "sharesOutstanding") if info.get(k) is not None])
    _tag_provenance(info, "derivado", "símbolo pedido; nombre de stock_database o de la búsqueda",
                    paths=["symbol", "longName", "shortName"])
    _tag_provenance(info, "yfinance_statements", "plan B: estados anuales de yfinance (último FY)")

    elapsed = time.time() - t0
    logger.info(f"[FALLBACK] get_ticker_info({symbol}) in {elapsed:.2f}s")
    # Sin escribir _cache aquí (ver _do_fetch): solo get_ticker_info cachea.
    return info


_SEARCH_URL = "https://query2.finance.yahoo.com/v1/finance/search"


def _search_profile(symbol: str):
    """Sector, industria y nombre desde la búsqueda de Yahoo (endpoint SIN crumb).

    Se usa en el plan B: desde IPs de datacenter quoteSummary responde 401
    ('Invalid Crumb') pero la búsqueda funciona (RECON §7.5). Solo acepta la
    cotización cuyo símbolo coincide exactamente. Devuelve None si no hay
    coincidencia o falla la llamada.
    """
    try:
        _ensure_session()
        r = _session.get(_SEARCH_URL, params={"q": symbol, "quotesCount": 5, "newsCount": 0,
                                              "listsCount": 0}, timeout=_D["search_timeout_s"])
        if r.status_code != 200:
            return None
        for q in (r.json() or {}).get("quotes", []):
            if str(q.get("symbol", "")).upper() == symbol.upper():
                return {"sector": q.get("sector") or q.get("sectorDisp"),
                        "industry": q.get("industry") or q.get("industryDisp"),
                        "name": q.get("longname") or q.get("shortname")}
    except Exception as e:
        logger.warning(f"[SEARCH] perfil de {symbol} no disponible: {e}")
    return None


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
