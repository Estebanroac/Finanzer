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

logger = logging.getLogger(__name__)

_BASE = "https://finnhub.io/api/v1"
_TIMEOUT = 8

# Cache interno (symbol -> (ts, payload)) para no repetir la llamada dentro del
# TTL del adaptador de Yahoo y respetar el rate limit del free tier (60/min).
_cache: Dict[str, tuple] = {}
_CACHE_TTL = 300
_lock = threading.Lock()

# Campos cuyo None dispara la consulta a Finnhub (casi siempre presentes en una
# respuesta sana de Yahoo; su ausencia es la firma de la degradación de Render).
_GAP_FIELDS = ("beta", "forwardPE", "revenueGrowth")


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
    """
    ttm = _num(ttm)
    c3 = _num(cagr3)
    c5 = _num(cagr5)
    lt = c5 if c5 is not None else c3
    if ttm is not None:
        if abs(ttm) <= 60 or (lt is not None and abs(ttm) <= 3 * abs(lt)):
            return ttm / 100.0
    if c3 is not None:
        return c3 / 100.0
    return None


def _series_val(series: dict, key: str, idx: int) -> Optional[float]:
    """Valor del punto `idx` (0 = año fiscal más reciente) de una serie anual."""
    arr = series.get(key) or []
    if len(arr) > idx and isinstance(arr[idx], dict):
        return _num(arr[idx].get("v"))
    return None


def enrich_info(info: Dict[str, Any], symbol: str, degraded: bool = False) -> Dict[str, Any]:
    """Rellena los None de `info` con Finnhub. No-op si la key no está.

    `degraded`: cuando la respuesta de Yahoo vino degradada, sus cifras POR ACCIÓN
    (trailingEps) pueden ser un valor anual obsoleto arrastrado por el
    'último bueno conocido'; en ese caso el epsTTM de Finnhub (TTM diluido) SÍ se
    impone sobre lo existente. Fuera de degradación se respeta el dato de Yahoo.
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

    # ── Tier 1: métricas de mercado (nivel superior de info) ──
    set_top("beta", _num(m.get("beta")))
    set_top("forwardPE", _num(m.get("forwardPE")))
    set_top("trailingPE", _num(m.get("peTTM")))
    # trailingEps: cuando consultamos Finnhub (Yahoo vino incompleto), su epsTTM
    # (TTM diluido) es la fuente fiable. Se IMPONE sobre el trailingEps existente
    # si falta o difiere >2% — el de Yahoo/LKG puede ser un EPS ANUAL obsoleto
    # que infla el P/E (AAPL 7.46 anual vs 8.27 TTM). Diferencias pequeñas se
    # respetan (sin churn). No depende del flag 'degraded' estricto: el estado
    # 'gappy pero no degradado' también trae EPS anual obsoleto.
    _eps_ttm = _num(m.get("epsTTM"))
    if _eps_ttm is not None and _eps_ttm != 0:
        _cur_eps = _num(info.get("trailingEps"))
        if _cur_eps is None or abs(_cur_eps - _eps_ttm) / abs(_eps_ttm) > 0.02:
            if info.get("trailingEps") != _eps_ttm:
                info["trailingEps"] = _eps_ttm
                filled.append("trailingEps~")
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
