"""
Rediseño E2b (Task 3; spec §4, dato 7): rivales de la empresa, analizados con el motor completo (decisión del
usuario: "Análisis completo"), de modo que sus cifras coinciden con las del resto de la página.

  · Industria: la que ya resolvió el análisis de la propia empresa para su referencia sectorial (benchmark.industry:
    por símbolo, por nombre legal y país de un ADR o por el mapa de Yahoo; desviación de la spec, que decía SIC,
    decidida por el PM). La empresa se analiza en el hilo de fondo si su resumen no está en caché. Sin industria de
    referencia: ningún rival automático (se añaden a mano), nunca candidatos de una industria vacía.
  · Candidatos: primero los del universo (S&P 500 + ADR principales, lib/universe.py), después el resto de Damodaran de
    la misma región y, si no llegan a `peers_count`, de las demás; sin la propia empresa ni sus otras clases.
  · Orden: por cercanía de capitalización (|log(cap_r / cap_s)|, 7 días en caché); los `peers_count` primeros. PDF
    rápido: las de todos los candidatos en una sola petición a Yahoo (`CAPS_BATCH`, en dólares; las cotizadas en otra
    moneda, sin capitalización); Finnhub profile2 (de una en una, con su pausa: ≤ 60/min) solo para las que Yahoo no
    trae. Antes eran todas de Finnhub: 12 capitalizaciones de HD tardaban 16,7 s y 20 de NVDA, 31 s; con Yahoo,
    0,1–0,5 s. Además, Finnhub da la de un ADR extranjero en la moneda de su país, no en dólares (MUFG 38.010 miles de
    millones, en yenes; IBN y HDB, en rupias; RY y TD, en dólares canadienses; HSBC, en libras), así que esos rivales se
    ordenaban mal: con Yahoo cambian los de JPM y NU. La primera consulta de una empresa responde "calculando".
  · Análisis: en la cola compartida de lib/analysis_queue.py (rediseño E4: un único hilo de fondo para rivales y
    tendencias), con prioridad `user`: un rival pedido adelanta a todo el precalentado de tendencias pendiente. Allí
    viven el resumen compacto (`summary`), su caché LRU y la espera mientras haya usuarios esperando turno.

El endpoint responde enseguida con el estado de cada rival (en_cola, analizando, listo, fallo) y el cliente vuelve a
preguntar cada `poll_s`. CAPS_FETCHER es inyectable aquí; ANALYZE y BUSY, en analysis_queue (main los conecta; los
tests y el replay los sustituyen).
"""
import logging
import math
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

import analysis_queue as AQ
import bounded
import industry_bench as IB
import universe
from settings import cfg

logger = logging.getLogger(__name__)

NOTE_FEW = "menos de 3 comparables en su industria"
NOTE_FEW_CHOSEN = "menos de 3 comparables elegidos"
NOTE_NO_INDUSTRY = "sin industria de referencia para proponer rivales (puedes añadirlos a mano)"
summary, reference = AQ.summary, AQ.reference                   # el resumen compacto vive en la cola compartida

_lock = threading.Lock()
_limits: Dict[str, Any] = {}             # copia de market.peers
# V6 (B3/B10): (hora, valor, caducidad): un fallo caduca a los `fail_ttl_s`; con tope (`caps_cache_max`,
# `rankings_cache_max`). _ranking_pending no crece más que la cola compartida (si AQ.submit no lo admite, sale).
_caps: Dict[str, Tuple[float, Optional[float], float]] = {}
_rankings: Dict[str, Tuple[float, Dict[str, Any], float]] = {}
_ranking_pending: set = set()
_last_finnhub = [0.0]


def reset() -> None:
    """Olvida cachés y estado, también los de la cola compartida, y detiene su hilo (tests)."""
    AQ.reset()
    with _lock:
        _caps.clear()
        _rankings.clear()
        _ranking_pending.clear()
        _limits.clear()
        _limits.update(cfg("market.peers"))


reset()


# ───────────────────────── candidatos y orden ─────────────────────────

def _root(sym: str) -> str:
    return sym.split("-")[0]


def candidates(symbol: str, industry: Optional[str], region: Optional[str]) -> List[str]:
    """Misma industria: primero el universo; después el resto de Damodaran de la misma región (orden alfabético) y, si
    con eso no llega a `peers_count`, el de las demás regiones. Sin el propio símbolo ni otras clases de la misma
    empresa (mismo CIK en el universo o misma raíz: BRK-A/BRK-B). Sin industria: ninguno (nunca una industria vacía)."""
    if not industry:
        return []
    sym = universe.norm_symbol(symbol)
    own = universe.get(sym) or {}

    def same_company(c: str) -> bool:
        row = universe.get(c) or {}
        return c == sym or _root(c) == _root(sym) or bool(own.get("cik") and row.get("cik") == own.get("cik"))
    out = [c for c in universe.by_industry(industry) if not same_company(c)]
    seen = set(out)
    firms = IB._load_firms()["symbol"]
    same = sorted(s for s, (ind, reg) in firms.items() if ind == industry and reg == region and s not in seen
                  and not same_company(s)) if region else []
    out += same
    if len(out) < _limits["peers_count"]:
        seen |= set(same)
        out += sorted((s for s, (ind, reg) in firms.items() if ind == industry and s not in seen
                       and not same_company(s)), key=lambda s: (firms[s][1], s))
    return out


def region_of(symbol: str) -> Optional[str]:
    """Región de Damodaran del candidato: la del universo o la de su fila en Damodaran."""
    row = universe.get(symbol) or {}
    if row.get("damodaran_region"):
        return row["damodaran_region"]
    hit = IB._load_firms()["symbol"].get(symbol)
    return hit[1] if hit else None


def lookup_order(cands: List[str], own_region: Optional[str]) -> List[str]:
    """Orden de las capitalizaciones que se piden (hay un tope): los del universo primero (Finnhub da su
    capitalización), con los de la región de la empresa delante; después el resto, también con su región delante."""
    return sorted(cands, key=lambda c: (universe.get(c) is None, region_of(c) != own_region))


def rank(symbol: str, cands: List[str], caps: Dict[str, Optional[float]],
         own_region: Optional[str] = None) -> Dict[str, Any]:
    """Los `peers_count` candidatos por cercanía de capitalización (|log(cap_r / cap_s)|), con los de la región de la
    empresa primero dentro de la banda de tamaño (`size_band_low`–`size_band_high` veces su capitalización). Los que no
    tienen capitalización no entran. Sin la de la empresa: el orden de los candidatos."""
    P = _limits
    own = caps.get(symbol)
    if own and own > 0:
        known = [c for c in cands if (caps.get(c) or 0) > 0]
        known.sort(key=lambda c: (abs(math.log(caps[c] / own)), c))
        # Sin capitalización no entran: no se sabe si se parecen en tamaño y pueden ser la cotización local de la
        # propia empresa (BARC.L para BCS: Finnhub gratuito no da las de fuera de EE. UU.).
        first = [c for c in known if own_region and region_of(c) == own_region
                 and P["size_band_low"] <= caps[c] / own <= P["size_band_high"]]
        ordered = first + [c for c in known if c not in first]
    else:
        ordered = list(cands)
    rivals = ordered[:P["peers_count"]]
    # V2 (decisión del PM): los siguientes del ranking, por si un rival ya no existe en Yahoo (se sustituye al consultar)
    reserve = ordered[P["peers_count"]:P["peers_count"] + P["max_substitutions"]]
    return {"rivals": rivals, "reserve": reserve, "note": NOTE_FEW if len(rivals) < P["min_peers"] else None}


def finnhub_cap(symbol: str) -> Optional[float]:
    """Capitalización en dólares de Finnhub profile2 (marketCapitalization viene en millones), con la pausa de
    `finnhub_min_interval_s` entre peticiones."""
    import finnhub_fallback
    with _lock:
        wait = _last_finnhub[0] + _limits["finnhub_min_interval_s"] - time.monotonic()
        _last_finnhub[0] = time.monotonic() + max(wait, 0.0)
    if wait > 0:
        time.sleep(wait)
    data = finnhub_fallback._get("/stock/profile2", {"symbol": symbol}) or {}
    cap = data.get("marketCapitalization")
    return float(cap) * 1e6 if isinstance(cap, (int, float)) and cap > 0 else None


CAPS_FETCHER: Callable[[str], Optional[float]] = finnhub_cap


def caps_from_quote(resp: Dict[str, Any]) -> Dict[str, Optional[float]]:
    """Las capitalizaciones de una respuesta de Yahoo v7/finance/quote: en dólares, la cifra; cotizado en otra moneda
    (KER.PA, en euros), None: no se compara con las de EE. UU. y queda sin capitalización, como con Finnhub, que no da
    las de fuera de EE. UU. (medido: MC.PA, KER.PA, RMS.PA, CFR.SW y ADS.DE, ninguna); preguntarle solo costaba su pausa.
    Uno que Yahoo no trae, o sin capitalización, no sale: se pregunta a Finnhub."""
    out: Dict[str, Optional[float]] = {}
    for q in ((resp or {}).get("quoteResponse") or {}).get("result") or []:
        cap, sym = q.get("marketCap"), q.get("symbol")
        if not sym or not isinstance(cap, (int, float)) or cap <= 0:
            continue
        out[sym] = float(cap) if q.get("currency") == "USD" else None
    return out


def yahoo_caps(symbols: List[str]) -> Dict[str, Optional[float]]:
    """Las capitalizaciones de varios símbolos en una sola petición a Yahoo (v7/finance/quote, con la sesión y el
    crumb de yfinance)."""
    from yfinance.data import YfData
    resp = YfData().get_raw_json(_limits["yahoo_quote_url"], params={"symbols": ",".join(symbols),
                                                                       "fields": "marketCap,currency"},
                                 timeout=_limits["yahoo_quote_timeout_s"])
    return caps_from_quote(resp)


CAPS_BATCH: Optional[Callable[[List[str]], Dict[str, Optional[float]]]] = yahoo_caps


def _caps_for(symbols: List[str]) -> Dict[str, Optional[float]]:
    """Las capitalizaciones de `symbols`: las de la caché; de las demás, una petición a Yahoo para todas y Finnhub
    para las que Yahoo no trae (o todas, si Yahoo falla)."""
    now = time.time()
    out: Dict[str, Optional[float]] = {}
    with _lock:
        for s in symbols:
            hit = _caps.get(s)
            if hit and now - hit[0] < hit[2]:
                out[s] = hit[1]
    todo = [s for s in symbols if s not in out]
    if todo and CAPS_BATCH is not None:
        try:
            got = CAPS_BATCH(todo)
        except Exception as e:  # Yahoo falla de muchas maneras: Finnhub, de uno en uno, como antes
            logger.warning("[PEERS] capitalizaciones de Yahoo: %s", type(e).__name__)
            got = {}
        with _lock:
            for s, cap in got.items():
                if s in todo:
                    bounded.put(_caps, s, (now, cap, _limits["caps_ttl_s"]), _limits["caps_cache_max"])
                    out[s] = cap
    for s in symbols:
        if s not in out:
            out[s] = _cap(s)
    return out


def _cap(symbol: str) -> Optional[float]:
    now = time.time()
    with _lock:
        hit = _caps.get(symbol)
        if hit and now - hit[0] < hit[2]:
            return hit[1]
    try:
        val = CAPS_FETCHER(symbol)
    except Exception as e:  # una capitalización que falla no rompe el orden: va al final
        logger.warning("[PEERS] capitalización de %s: %s", symbol, type(e).__name__)
        val = None
    ttl = _limits["caps_ttl_s"] if val is not None else _limits["fail_ttl_s"]
    with _lock:
        bounded.put(_caps, symbol, (now, val, ttl), _limits["caps_cache_max"])
    return val


def _do_rank(symbol: str, stop: threading.Event, client: Optional[str] = None) -> None:
    """Analiza la propia empresa (o usa su resumen en caché) para leer la industria que resolvió su referencia, y
    ordena por tamaño los candidatos de esa industria. Corre en el hilo de la cola compartida, con prioridad `user`.
    F10 · N5: con el ranking hecho, sus rivales van a la cola enseguida (antes esperaban a la siguiente consulta de la
    página Rivales; sin ella, el PDF no los tenía nunca)."""
    try:
        _rank_now(symbol, stop)
    finally:
        with _lock:
            _ranking_pending.discard(symbol)
    ranked = _ranked(symbol)
    if ranked and ranked["rivals"] and not stop.is_set():
        request(symbol, _substitute(ranked)[0], client=client)


def _rank_now(symbol: str, stop: threading.Event) -> None:
    own, why = AQ.summary_for(symbol, stop)
    ref = (own or {}).get("reference")
    # V6 (B3): un ranking hecho sobre un fallo pasajero (el análisis de la empresa no salió o no hay su capitalización)
    # se recuerda `fail_ttl_s`, no los 7 días de uno bueno.
    failed = own is None
    if ref is None:
        res = {"rivals": [], "industry": None,
               "note": NOTE_NO_INDUSTRY if own else f"{NOTE_NO_INDUSTRY} (no se pudo analizar {symbol}: {why})"}
    else:
        cands = lookup_order(candidates(symbol, ref["industry"], ref["region"]),
                             ref["region"])[:_limits["max_cap_lookups"]]
        caps = _caps_for([symbol] + cands)
        res = {**rank(symbol, cands, caps, ref["region"]), "industry": ref["industry"]}
        failed = failed or caps.get(symbol) is None
    ttl = _limits["fail_ttl_s"] if failed else _limits["caps_ttl_s"]
    with _lock:
        bounded.put(_rankings, symbol, (time.time(), res, ttl), _limits["rankings_cache_max"])


# ───────────────────────── estado de los rivales ─────────────────────────

def request(symbol: str, rivals: List[str], note: Optional[str] = None,
            client: Optional[str] = None) -> Dict[str, Any]:
    """Estado de cada rival en la cola compartida, con prioridad `user` (adelanta al precalentado de tendencias);
    encola los que no están ni hechos ni en marcha. Responde enseguida. `client` (V6, B7): quien pide, para su cupo de
    la cola; por empresa, como mucho `peers_count` rivales (lo valida el endpoint)."""
    out = [AQ.request(sym, AQ.USER, client) for sym in rivals]
    done = all(r["status"] in ("listo", "fallo") for r in out)
    return {"status": "listo" if done else "calculando", "symbol": symbol, "rivals": out, "note": note,
            "poll_s": _limits["poll_s"], "max_symbols": _limits["peers_count"]}


def _company(sym: str) -> Optional[Dict[str, Any]]:
    return AQ.cached(sym)


def _ranked(sym: str) -> Optional[Dict[str, Any]]:
    """El ranking en caché de `sym` si no ha caducado (cada uno con su plazo: V6, B3)."""
    now = time.time()
    with _lock:
        hit = _rankings.get(sym)
        return hit[1] if hit and now - hit[0] < hit[2] else None


def cached_for(symbol: str) -> Optional[Dict[str, Any]]:
    """Los rivales automáticos tal como están en la caché compartida, sin encolar nada. None si la clasificación por
    tamaño aún no está hecha; los rivales sin resumen fresco salen con su estado ("en_cola", "analizando", "fallo",
    con su motivo) o "sin_dato", y el PDF solo pinta los "listo"."""
    sym = universe.norm_symbol(symbol)
    ranked = _ranked(sym)
    if ranked is None:
        return None
    # los mismos rivales que la web: con las sustituciones de un símbolo que la fuente ya no tiene (V2)
    names, note = _substitute(ranked) if ranked["rivals"] else ([], ranked.get("note"))
    rivals = []
    for r in names:
        st = AQ.peek(r) or {"symbol": r, "status": "sin_dato"}
        rivals.append({**st, "symbol": r})
    return {"symbol": sym, "rivals": rivals, "note": note, "industry": ranked.get("industry"),
            "source": "automaticos"}


def _gone(sym: str) -> bool:
    """El análisis del rival falló porque la fuente ya no tiene el símbolo (`no_data_markers`), no por otro motivo."""
    st = AQ.peek(sym)
    return bool(st and st["status"] == "fallo"
                and any(m.lower() in str(st.get("reason") or "").lower() for m in _limits["no_data_markers"]))


def _substitute(ranked: Dict[str, Any]) -> Tuple[List[str], Optional[str]]:
    """V2 (decisión del PM): en la lista automática, un rival que Yahoo ya no tiene (ACLX) se cambia por el siguiente
    del ranking, como mucho `max_substitutions`, y la nota lo dice. La lista elegida a mano no pasa por aquí."""
    reserve = list(ranked.get("reserve") or [])
    out, swapped = [], []
    for r in ranked["rivals"]:
        cur = r
        while _gone(cur) and reserve and len(swapped) < _limits["max_substitutions"]:
            nxt = reserve.pop(0)
            swapped.append((cur, nxt))
            cur = nxt
        out.append(cur)
    if not swapped:
        return out, ranked["note"]
    txt = "; ".join(f"{a} → {b}" for a, b in swapped)
    extra = f"sustituidos (la fuente ya no los tiene): {txt}"
    return out, f"{ranked['note']}; {extra}" if ranked["note"] else extra


def peers_for(symbol: str, chosen: Optional[List[str]] = None, client: Optional[str] = None) -> Dict[str, Any]:
    """El endpoint: los rivales elegidos (`chosen`) o los automáticos. Los automáticos salen de la industria que
    resolvió el análisis de la propia empresa (se analiza en el hilo de fondo si no está en caché) y se ordenan por
    tamaño allí mismo: la primera consulta responde "calculando". `company`: el resumen de la propia empresa (la fila
    de arriba de la tabla de rivales) cuando ya está."""
    sym = universe.norm_symbol(symbol)
    if chosen:
        company = _company(sym)
        few = NOTE_FEW_CHOSEN if len(chosen) < _limits["min_peers"] else None
        return {**request(sym, chosen, few, client), "industry": ((company or {}).get("reference") or {}).get("industry"),
                "source": "elegidos", "company": company}
    base = {"symbol": sym, "source": "automaticos", "poll_s": _limits["poll_s"], "max_symbols": _limits["peers_count"]}
    now = time.time()
    # V6 (B11): mirar la caché y marcar "en marcha" en una sola sección con el lock: dos consultas a la vez ya no
    # encolan dos rankings de la misma empresa.
    with _lock:
        hit = _rankings.get(sym)
        ranked = hit[1] if hit and now - hit[0] < hit[2] else None
        launch = ranked is None and sym not in _ranking_pending
        if launch:
            _ranking_pending.add(sym)
    if ranked is None:
        note = None
        if launch:
            if not AQ.submit(sym, lambda stop: _do_rank(sym, stop, client), AQ.USER, client):
                with _lock:
                    _ranking_pending.discard(sym)
                note = "cola llena: vuelve a intentarlo"
        return {**base, "status": "calculando", "industry": None, "rivals": [], "note": note, "company": None}
    if not ranked["rivals"]:
        return {**base, "status": "sin_dato", "industry": ranked["industry"], "rivals": [], "note": ranked["note"],
                "company": _company(sym)}
    rivals, note = _substitute(ranked)
    return {**request(sym, rivals, note, client), "industry": ranked["industry"],
            "source": "automaticos", "company": _company(sym)}


# ───────────────────────── F10 · N5: con el análisis y en el PDF ─────────────────────────

def start(symbol: str, analysis: Dict[str, Any], client: Optional[str] = None) -> None:
    """Al servir el análisis de una empresa a un usuario (`start_with_analysis`): su resumen queda en la cola
    compartida y sus rivales automáticos se ponen en marcha con prioridad `user` (antes que el precalentado de
    tendencias), sin esperar a que abra la página Rivales. Lo que ya está hecho o en marcha no se repite."""
    if not _limits["start_with_analysis"]:
        return
    sym = universe.norm_symbol(symbol)
    AQ.store(sym, analysis)
    peers_for(sym, None, client)


def for_pdf(symbol: str, client: Optional[str] = None,
            sleep: Callable[[float], None] = time.sleep) -> Dict[str, Any]:
    """Los rivales para el PDF: pone en marcha lo que falte (como la web) y espera como mucho `pdf_wait_s` a los que
    estén en marcha; después, los de la caché, cada uno con su estado. `ranked`: si la clasificación por tamaño estaba
    hecha; `waited_s`: cuánto esperó (el informe dice los que faltan y por qué)."""
    sym = universe.norm_symbol(symbol)
    t0 = time.monotonic()
    while True:
        r = peers_for(sym, None, client)
        left = _limits["pdf_wait_s"] - (time.monotonic() - t0)
        if r["status"] != "calculando" or left <= 0:
            break
        sleep(min(_limits["pdf_poll_s"], left))
    waited = round(time.monotonic() - t0)
    c = cached_for(sym)
    if c is None:
        return {"symbol": sym, "rivals": [], "note": r.get("note"), "industry": None, "source": "automaticos",
                "ranked": False, "waited_s": waited}
    return {**c, "ranked": True, "waited_s": waited}
