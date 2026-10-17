"""
Finnhub secondary-source fallback.

Desde IPs de datacenter (Render), Yahoo devuelve intermitentemente respuestas
degradadas: el cluster summaryDetail/defaultKeyStatistics vacío (beta, forward
P/E, dividendos, growth null) y los estados financieros históricos bloqueados
(F-Score de Piotroski deprimido, CAGR muertos).

Este módulo rellena esos huecos con Finnhub (free tier) COMO ÚLTIMO recurso,
después de las tres defensas internas del adaptador de Yahoo. Solo se activa si
la variable de entorno FINNHUB_API_KEY está definida, y SOLO rellena campos que
ya vienen en None — nunca sobrescribe un dato bueno de Yahoo. Sin la key el
módulo es completamente inerte.

Diseño de unidades (verificado contra la API real):
- Finnhub da yields/growth/payout en PORCENTAJE (12.76 = 12.76%); el motor los
  espera en DECIMAL igual que Yahoo (0.1276) → se dividen entre 100.
- beta, P/E, PEG, current/quick ratio, coberturas y turnovers son ratios puros
  y van tal cual.

Piotroski prior-year: las series anuales de Finnhub (`series.annual`) dan roa,
currentRatio, grossMargin, netMargin y longtermDebtTotalAsset ya estandarizados.
Como los criterios 3/5/6/8/9 solo comparan la DIRECCIÓN (¿mejoró vs el año
previo?), alimentar ambos años desde la MISMA serie es consistente por
construcción; el asset turnover se reconstruye por DuPont (ROA = margen neto ×
rotación de activos). La deuda LP se pasa como ratio LTD/Activos SOLO cuando
Yahoo no trajo el valor absoluto, para no mezclar unidades en la comparación.
"""
import os
import json
import time
import logging
import threading
from urllib.request import urlopen, Request
from urllib.parse import urlencode
from typing import Dict, Any, Optional

from settings import cfg

logger = logging.getLogger(__name__)

_CUT_MATCH_REL_TOL = cfg("data.finnhub.cut_match_rel_tol")

_BASE = "https://finnhub.io/api/v1"
_TIMEOUT = cfg("data.finnhub.timeout_s")

# Cache interno (symbol -> (ts, payload)) para no repetir la llamada dentro del
# TTL del adaptador de Yahoo y respetar el rate limit del free tier (60/min).
_cache: Dict[str, tuple] = {}
_CACHE_TTL = cfg("data.finnhub.cache_ttl_s")
_lock = threading.Lock()

# Campos cuyo None dispara la consulta a Finnhub (casi siempre presentes en una
# respuesta sana de Yahoo; su ausencia es la firma de la degradación de Render).
_GAP_FIELDS = cfg("data.finnhub.gap_fields")


def _api_key() -> str:
    return (os.environ.get("FINNHUB_API_KEY") or "").strip()


def is_enabled() -> bool:
    return bool(_api_key())


def should_fill(info: Dict[str, Any]) -> bool:
    """True si a `info` le faltan datos que Finnhub puede aportar."""
    if not isinstance(info, dict):
        return False
    if any(info.get(f) is None for f in _GAP_FIELDS):
        return True
    prior = info.get("_prior_year") or {}
    if prior.get("roa") is None:
        return True
    return False


def _get(path: str, params: Dict[str, Any]) -> Optional[dict]:
    key = _api_key()
    if not key:
        return None
    q = dict(params)
    q["token"] = key
    url = f"{_BASE}{path}?{urlencode(q)}"
    try:
        req = Request(url, headers={"User-Agent": "finanzer/1.0"})
        with urlopen(req, timeout=_TIMEOUT) as r:
            if getattr(r, "status", 200) != 200:
                return None
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        logger.warning(f"[FINNHUB] {path} failed: {e}")
        return None


def _basic_financials(symbol: str) -> Optional[dict]:
    now = time.time()
    with _lock:
        ent = _cache.get(symbol)
        if ent and now - ent[0] < _CACHE_TTL:
            return ent[1]
    data = _get("/stock/metric", {"symbol": symbol, "metric": "all"})
    with _lock:
        _cache[symbol] = (now, data)
    return data


def earnings_calendar(symbol: str, start: str, end: str) -> Optional[list]:
    """Fase 2b (T3): publicaciones de resultados del símbolo entre `start` y `end` (calendario de Finnhub), para el
    aviso de resultados publicados de los emisores sin 8-K. None sin clave o si falla."""
    key = f"cal:{symbol}:{start}:{end}"
    now = time.time()
    with _lock:
        ent = _cache.get(key)
        if ent and now - ent[0] < _CACHE_TTL:
            return ent[1]
    data = _get("/calendar/earnings", {"symbol": symbol, "from": start, "to": end})
    out = (data or {}).get("earningsCalendar") if isinstance(data, dict) else None
    with _lock:
        _cache[key] = (now, out)
    return out


def earnings_surprises(symbol: str) -> Optional[list]:
    """Fase 5 (PEAD; bitácora, fila "fecha de resultados"): BPA real frente al consenso de los últimos trimestres
    (`/stock/earnings`, plan gratuito: {period, actual, estimate, surprise, surprisePercent}). Sin fecha de anuncio: la
    pone el 8-K de resultados de EDGAR (lib/market_context.pead). None sin clave o si falla."""
    key = f"surp:{symbol}"
    now = time.time()
    with _lock:
        ent = _cache.get(key)
        if ent and now - ent[0] < _CACHE_TTL:
            return ent[1]
    data = _get("/stock/earnings", {"symbol": symbol})
    out = data if isinstance(data, list) else None
    with _lock:
        _cache[key] = (now, out)
    return out


def company_news(symbol: str, start: str, end: str) -> Optional[list]:
    """Fase 5 (PLAN §4, fase 5): titulares de la empresa entre `start` y `end` (`/company-news`, gratuito en el plan
    actual: comprobado el 2026-10-17). None sin clave o si falla. Contexto: no puntúa ni se interpreta."""
    key = f"news:{symbol}:{start}:{end}"
    now = time.time()
    with _lock:
        ent = _cache.get(key)
        if ent and now - ent[0] < _CACHE_TTL:
            return ent[1]
    data = _get("/company-news", {"symbol": symbol, "from": start, "to": end})
    out = data if isinstance(data, list) else None
    with _lock:
        _cache[key] = (now, out)
    return out


def _num(v) -> Optional[float]:
    try:
        if v is None:
            return None
        f = float(v)
        return f if f == f else None  # descarta NaN
    except (TypeError, ValueError):
        return None


def _pct(v) -> Optional[float]:
    """Porcentaje de Finnhub (12.76) -> decimal del motor (0.1276)."""
    n = _num(v)
    return n / 100.0 if n is not None else None


def _growth(ttm, cagr3, cagr5) -> Optional[float]:
    """Crecimiento YoY en DECIMAL, con guard anti-artefacto.

    Bancos y financieras reportan un "revenue" cuya definición cambia entre
    períodos y produce un YoY absurdo (JPM: 108.98% con CAGR-5Y de 7.7%). Un
    hipergrowth REAL muestra un CAGR multi-año comparablemente alto; un artefacto
    no. Si el YoY es un pico implausible frente a la tendencia, se usa el CAGR-3Y
    suavizado en su lugar (para JPM ~3.4%, razonable) en vez de un dato roto.

    Desde la etapa 3 la regla vive en validate.growth_guard (umbrales en
    validate.THRESHOLDS) y se aplica también a las rutas Yahoo y plan B.
    """
    from validate import growth_guard
    return growth_guard(ttm, cagr3, cagr5)


def _series_val(series: dict, key: str, idx: int) -> Optional[float]:
    """Valor del punto `idx` (0 = año fiscal más reciente) de una serie anual."""
    arr = series.get(key) or []
    if len(arr) > idx and isinstance(arr[idx], dict):
        return _num(arr[idx].get("v"))
    return None


def enrich_info(info: Dict[str, Any], symbol: str, degraded: bool = False) -> Dict[str, Any]:
    """Rellena los None de `info` con Finnhub. No-op si la key no está.

    Fase 2b: nada de Finnhub se impone sobre los estados. Sus métricas TTM por acción (BPA, P/E) solo entran si
    casan con el corte de los estados; si no, se anotan (info["_period_rejected"] → validate). `degraded` se
    conserva en la firma por compatibilidad: ya no cambia la regla.
    """
    if not is_enabled() or not isinstance(info, dict):
        return info

    data = _basic_financials(symbol.upper())
    if not data:
        return info

    m = data.get("metric") or {}
    series = (data.get("series") or {}).get("annual") or {}
    filled = []

    def set_top(key, val):
        if val is not None and info.get(key) is None:
            info[key] = val
            filled.append(key)

    # Etapa 11b: si los estados se reexpresaron a la moneda o la clase de la cotización
    # (ADR, BRK-B), las cifras por acción de Finnhub pueden venir en la otra unidad (BRK-B:
    # BPA de la clase A): no se imponen ni se usan para rellenar.
    _cur = info.get("_currency") or {}
    _restated = bool(_cur.get("converted") or (_cur.get("share_class") or {}).get("applied"))

    # ── Tier 1: métricas de mercado (nivel superior de info) ──
    set_top("beta", _num(m.get("beta")))
    set_top("forwardPE", _num(m.get("forwardPE")))
    # Fase 2b (T3, F2_PRECEDENCIA §1, paso 3): las métricas TTM de Finnhub solo entran si casan con el corte de los
    # estados (±cut_match_rel_tol). Antes era al revés: su epsTTM se IMPONÍA si difería más de un 2%, y en JNJ
    # mezclaba un BPA a septiembre (con el trimestre del 8-K) con estados a junio (P/E 30.1x → 39.4x). Si no casa,
    # no entra y se anota (validate: periodo_incoherente). Sin BPA del corte no hay con qué casarlo: no entra.
    _eps_ttm = None if _restated else _num(m.get("epsTTM"))
    _cur_eps = _num(info.get("trailingEps"))
    if _eps_ttm is not None and _eps_ttm != 0:
        _cut = (info.get("_as_of") or {}).get("date")
        if _cur_eps is None or abs(_cur_eps - _eps_ttm) / abs(_eps_ttm) > _CUT_MATCH_REL_TOL:
            info.setdefault("_period_rejected", []).append({
                "field": "trailingEps", "value": _eps_ttm,
                "reason": (f"BPA TTM de Finnhub {_eps_ttm:g} no casa con el del corte de los estados "
                           + (f"({_cur_eps:.4g} a {_cut})" if _cur_eps is not None else "(sin BPA del corte)")
                           + ": es de otro periodo y no entra")})
    # El P/E TTM de Finnhub no se trae: el motor lo calcula con el precio y el BPA del corte (un P/E de la fuente
    # sería de su propio periodo).
    # OJO: NO mapear forwardEps desde epsTTM/epsExclExtraItemsTTM — esos son
    # TRAILING, no estimados forward. Usarlos haría forward_pe = price/eps_TTM
    # (≈ el trailing P/E otra vez), anulando la señal de compresión. Se deja
    # forwardEps en None y el forward P/E cae a m["forwardPE"] de Finnhub (que
    # sí usa estimados de consenso) vía el fallback_map de main.py.

    dy = _pct(m.get("dividendYieldIndicatedAnnual"))
    if dy is None:
        dy = _pct(m.get("currentDividendYieldTTM"))
    set_top("dividendYield", dy)
    set_top("dividendRate", _num(m.get("dividendIndicatedAnnual")))
    set_top("payoutRatio", _pct(m.get("payoutRatioTTM")))

    set_top("revenueGrowth", _growth(m.get("revenueGrowthTTMYoy"), m.get("revenueGrowth3Y"), m.get("revenueGrowth5Y")))
    set_top("earningsGrowth", _growth(m.get("epsGrowthTTMYoy"), m.get("epsGrowth3Y"), m.get("epsGrowth5Y")))

    # ── _yahoo_ratios: fluyen a `ratios` vía el fallback_map de main.py ──
    yr = info.get("_yahoo_ratios")
    if not isinstance(yr, dict):
        yr = {}
        info["_yahoo_ratios"] = yr

    def set_yr(key, val):
        if val is not None and yr.get(key) is None:
            yr[key] = val
            filled.append("yr." + key)

    set_yr("forwardPE", _num(m.get("forwardPE")))
    set_yr("dividendYield", dy)
    set_yr("currentRatio", _num(m.get("currentRatioQuarterly")) or _num(m.get("currentRatioAnnual")))
    set_yr("quickRatio", _num(m.get("quickRatioQuarterly")) or _num(m.get("quickRatioAnnual")))
    set_yr("payoutRatio", _pct(m.get("payoutRatioTTM")))
    # PEG de mercado: preferir el FORWARD (crecimiento de consenso) sobre el TTM;
    # ambos ≈ al PEG que reportan stockanalysis/Yahoo, a diferencia del PEG
    # trailing del motor (que con el crecimiento TTM inflado subestima).
    set_yr("pegRatio", _num(m.get("forwardPEG")) or _num(m.get("pegTTM")))
    set_yr("interestCoverage", _num(m.get("netInterestCoverageTTM")) or _num(m.get("netInterestCoverageAnnual")))
    set_yr("inventoryTurnover", _num(m.get("inventoryTurnoverTTM")) or _num(m.get("inventoryTurnoverAnnual")))

    # ── Tier 2: prior-year de Piotroski desde las series anuales ──
    try:
        _fill_piotroski(info, series, filled)
    except Exception as e:
        logger.warning(f"[FINNHUB] piotroski fill for {symbol}: {e}")

    # Procedencia: cada campo rellenado (o impuesto) desde Finnhub.
    _tag_map = {"pio.roa": "_piotroski_current.roa", "prior.roa": "_prior_year.roa",
                "pio.cr": "_piotroski_current.current_ratio", "prior.cr": "_prior_year.current_ratio",
                "pio.gm": "_piotroski_current.gross_margin", "prior.gm": "_prior_year.gross_margin",
                "pio.at": "_piotroski_current.asset_turnover", "prior.at": "_prior_year.asset_turnover",
                "der.gm": "_current_derived.gross_margin", "der.at": "_current_derived.asset_turnover"}
    prov = info.setdefault("_provenance", {})
    for tag in filled:
        path = _tag_map.get(tag) or (("_yahoo_ratios." + tag[3:]) if tag.startswith("yr.") else tag.rstrip("~"))
        detail = "/stock/metric" + (" (impuesto: difería >2% del existente)" if tag.endswith("~") else "")
        if path.endswith("forwardPE"):
            # Fase 2b (T7): estimación de consenso del proveedor, horizonte no documentado. Contrastada en vivo con
            # Yahoo el 2026-10-16 (TSM 18.9 frente a 17.9; AAPL 35.3/35.9; KO 25.6/26.6; BCS 7.6/7.0; NVO 11.5/11.4;
            # TM 9.3/12.3 y ASML 30.6/26.2 difieren, probablemente por el horizonte). El P/E no depende de la
            # moneda ni del factor ADR: no hay error de unidad.
            detail += " (forwardPE: estimación de consenso del proveedor, horizonte no documentado)"
        prov[path] = {"source": "finnhub", "detail": detail}

    if filled:
        head = ", ".join(filled[:12])
        tail = "..." if len(filled) > 12 else ""
        logger.info(f"[FINNHUB] {symbol}: rellenados {len(filled)} campos ({head}{tail})")
    return info


def _fill_piotroski(info: Dict[str, Any], series: dict, filled: list) -> None:
    if not series:
        return

    roa0 = _series_val(series, "roa", 0)
    roa1 = _series_val(series, "roa", 1)
    nm0 = _series_val(series, "netMargin", 0)
    nm1 = _series_val(series, "netMargin", 1)
    cr0 = _series_val(series, "currentRatio", 0)
    cr1 = _series_val(series, "currentRatio", 1)
    gm0 = _series_val(series, "grossMargin", 0)
    gm1 = _series_val(series, "grossMargin", 1)
    ltd0 = _series_val(series, "longtermDebtTotalAsset", 0)
    ltd1 = _series_val(series, "longtermDebtTotalAsset", 1)

    # Asset turnover por DuPont: ROA = margen neto × rotación de activos.
    at0 = (roa0 / nm0) if (roa0 is not None and nm0) else None
    at1 = (roa1 / nm1) if (roa1 is not None and nm1) else None

    cur = info.get("_piotroski_current")
    if not isinstance(cur, dict):
        cur = {}
        info["_piotroski_current"] = cur
    prior = info.get("_prior_year")
    if not isinstance(prior, dict):
        prior = {}
        info["_prior_year"] = prior
    der = info.get("_current_derived")
    if not isinstance(der, dict):
        der = {}
        info["_current_derived"] = der

    def setk(d, k, v, tag):
        if v is not None and d.get(k) is None:
            d[k] = v
            filled.append(tag)

    setk(cur, "roa", roa0, "pio.roa")
    setk(prior, "roa", roa1, "prior.roa")
    setk(cur, "current_ratio", cr0, "pio.cr")
    setk(prior, "current_ratio", cr1, "prior.cr")
    setk(cur, "gross_margin", gm0, "pio.gm")
    setk(prior, "gross_margin", gm1, "prior.gm")
    setk(cur, "asset_turnover", at0, "pio.at")
    setk(prior, "asset_turnover", at1, "prior.at")
    setk(der, "gross_margin", gm0, "der.gm")
    setk(der, "asset_turnover", at0, "der.at")

    # Deuda LP: se rellena como ratio LTD/Activos en AMBOS años solo cuando el
    # dato del AÑO FISCAL (el que Piotroski compara) falta en los dos lados —
    # que es el escenario de bloqueo de históricos. main.py prioriza
    # _piotroski_current["long_term_debt"] sobre el absoluto de financials, así
    # que el par de ratios se usa de forma consistente (current <= prior) sin
    # mezclar unidades. Si el año fiscal actual ya trae un absoluto (enrich local
    # parcial), no se toca, para no comparar ratio contra dólar.
    if cur.get("long_term_debt") is None and prior.get("long_term_debt") is None:
        setk(cur, "long_term_debt", ltd0, "pio.ltd")
        setk(prior, "long_term_debt", ltd1, "prior.ltd")
