"""
Rediseño E4 (Task 1): cola de análisis en segundo plano compartida, generalizada desde la de los rivales de E2b
(lib/peers.py). Un único hilo (se arranca con la primera petición, nunca al importar) atiende dos prioridades:

  · `USER`: lo que un usuario está mirando (los rivales de una empresa y el orden de sus candidatos).
  · `PREWARM`: el precalentado de las tarjetas de tendencias de la portada (lib/trending.py).

Un trabajo `USER` adelanta a todo el precalentado pendiente; dentro de una prioridad, por orden de llegada. Si un
símbolo ya espera como `PREWARM` y un usuario lo pide, se vuelve a encolar como `USER` (la entrada antigua se descarta
al salir: ya está en caché). PDF rápido: `workers` hilos; el primero toma todo y los demás solo trabajos `USER` (los
rivales de una empresa se analizan de dos en dos; el precalentado sigue de uno en uno). Nunca hay dos análisis del mismo
símbolo a la vez: cada símbolo se encola una sola vez mientras está en cola o analizándose, y la entrada antigua de uno
que adelantó un usuario se descarta al salir. Uno ya hecho no se repite. Cada análisis corre con el mismo turno que los de los usuarios (main._compute_limited comparte
_ANALYSIS_SLOTS) y con prioridad baja: mientras haya usuarios esperando turno, el hilo espera.

De cada análisis solo se guarda un resumen compacto (`summary`; Render tiene 512 MB) en una caché LRU con caducidad,
la misma para rivales y tendencias. Estados de un símbolo: en_cola, analizando, listo, fallo. ANALYZE y BUSY son
inyectables (main los conecta; los tests y el replay los sustituyen).
"""
import datetime as _dt
import heapq
import itertools
import logging
import threading
import time
from collections import OrderedDict
from typing import Any, Callable, Dict, List, Optional, Tuple

import numfmt
from settings import cfg

logger = logging.getLogger(__name__)

ANALYZE: Optional[Callable[[str], Dict[str, Any]]] = None      # main: _compute_limited(symbol, user=False)
BUSY: Callable[[], bool] = lambda: False                        # main: hay usuarios esperando turno de análisis
USER, PREWARM = 0, 1
_PRIORITY_NAMES = {USER: "user", PREWARM: "prewarm"}
FULL = "cola llena"

_lock = threading.Lock()
_wake = threading.Condition(_lock)
_limits: Dict[str, Any] = {}             # copia de market.analysis_queue (los tests ajustan límites y esperas)
_summaries: "OrderedDict[str, Tuple[float, Dict[str, Any]]]" = OrderedDict()
_state: Dict[str, Dict[str, Any]] = {}   # símbolo -> {status: en_cola|analizando|fallo, t, reason}
_heap: List[Tuple[int, int, str, Optional[Callable], Optional[str]]] = []
_pending: Dict[int, int] = {USER: 0, PREWARM: 0}                # trabajos en cola por prioridad
_by_client: Dict[str, int] = {}          # V6 (B7): trabajos en cola por cliente (IP), como mucho `max_per_client`
_queued: Dict[str, int] = {}             # símbolo -> mejor prioridad con la que espera su análisis
_workers: List[threading.Thread] = []
_stop: Optional[threading.Event] = None
_seq = itertools.count()


def reset() -> None:
    """Olvida cachés, cola y estado y detiene el hilo (tests)."""
    global _stop
    with _lock:
        if _stop is not None:
            _stop.set()
            _wake.notify_all()
        _workers.clear()
        _stop = None
        _heap.clear()
        _pending.update({USER: 0, PREWARM: 0})
        _by_client.clear()
        _queued.clear()
        _summaries.clear()
        _state.clear()
        _limits.clear()
        _limits.update(cfg("market.analysis_queue"))


reset()


# ───────────────────────── resumen compacto de un análisis ─────────────────────────

def reference(analysis: Dict[str, Any]) -> Optional[Dict[str, str]]:
    """La industria de Damodaran que el análisis ya resolvió para su referencia sectorial (benchmark.industry: por
    símbolo, por nombre legal y país de un ADR, o por el mapa de la industria de Yahoo), con su región. None si la
    referencia no es una industria (mercado amplio, media de sector o provisional)."""
    ind = ((analysis or {}).get("benchmark") or {}).get("industry") or {}
    if ind.get("basis") not in ("industria", "industria_global") or not isinstance(ind.get("damodaran"), str):
        return None
    return {"industry": ind["damodaran"], "region": ind.get("home_region") or ind.get("region"),
            "basis": ind["basis"]}


def _cap_txt(value: Optional[float], currency: Optional[str]) -> str:
    """La capitalización en su moneda, con el mismo estilo que el motor y la cabecera de /v2 ("EUR 195.71B")."""
    return numfmt.money(value, currency or "USD")


def _lower_first(t: Optional[str]) -> str:
    t = str(t or "").strip()
    return t[:1].lower() + t[1:]


def _clean(t: Optional[str]) -> str:
    return str(t or "").strip().rstrip(".").strip()


def _from_row(row: Dict[str, Any], value: Any) -> Dict[str, Any]:
    """V4b: una columna de la tabla de rivales desde la fila de la página: con dato, la cifra y su texto; sin él, una
    palabra corta y el motivo en la nota (la tabla la pone en el `title` y para lectores de pantalla)."""
    state, reading, text = row.get("state"), _clean(row.get("reading")), _clean(row.get("text"))
    if state == "con_dato" and row.get("value") not in (None, "", "—"):
        return {"value": value if isinstance(value, (int, float)) else None, "value_txt": row["value"]}
    if state == "no_aplica":
        reason = reading if reading.startswith("No aplica") else "No aplica"
        return {"value": None, "value_txt": "No aplica",
                "note": f"{reason}: {_lower_first(text)}" if text and text.lower() not in reason.lower() else reason}
    if state == "no_significativo":
        return {"value": None, "value_txt": "n. s.", "note": (text[:1].upper() + text[1:]) if text else reading}
    out = {"value": None, "value_txt": "Sin dato"}
    if text:
        out["note"] = text[:1].upper() + text[1:]
    return out


def summary(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Lo que comparan la tabla de rivales y las tarjetas de tendencias, con las mismas cifras y textos que la página
    (display.charts.comparison), más la capitalización: no el análisis entero (memoria)."""
    a = analysis
    prof = a.get("profile") or {}
    comp = ((a.get("display") or {}).get("charts") or {}).get("comparison") or {}
    metrics = {i["key"]: {"value": i.get("value"), "value_txt": i.get("value_txt")}
               for g in comp.get("groups") or [] for i in g.get("items") or []}
    # V4b (auditoría de datos): el comparador solo trae lo que tiene referencia de industria; una columna de la tabla de
    # rivales que no está sale de su fila de la página, con la cifra o con el motivo (no aplica, no significativa).
    sections = (a.get("display") or {}).get("sections") or {}
    rows = {r.get("key"): r for s in ("valuation", "profitability", "solvency", "growth")
            for r in (sections.get(s) or {}).get("rows") or []}
    km = a.get("key_metrics") or {}
    for key in cfg("market.peers.summary_columns"):
        if key not in metrics and key != "revenue_growth" and key in rows:
            metrics[key] = _from_row(rows[key], km.get(key))
    # V7 · P5: un P/E fuera de rango (beneficio casi nulo) no es significativo: «n. s.», con la cifra en la nota
    pe = metrics.get("pe")
    pe_max = cfg("market.peers.pe_meaningful_max")
    if pe and pe.get("value") is not None and pe["value"] > pe_max:
        metrics["pe"] = {**pe, "value_txt": "n. s.",
                         "note": f"P/E de {pe.get('value_txt')}: con un beneficio casi nulo no es significativo "
                                 f"(por encima de {pe_max:g}x)"}
    metrics["market_cap"] = {"value": prof.get("market_cap"), "value_txt": _cap_txt(prof.get("market_cap"),
                                                                                    prof.get("currency"))}
    # E3 (página Rivales): crecimiento de ingresos (CAGR 3 años): el texto de la fila de la página; sin dato, el estado
    # de esa fila
    row = rows.get("revenue_growth")
    if row is not None:
        # V4b: la cifra de la fila es la que puntúa (desglose del score: ciclo medio en una cíclica, por acción si hay
        # emisión); la CAGR agregada solo si el desglose no la trae
        from display_charts import _growth_raw, revenue_cagr
        raw = revenue_cagr(_growth_raw(a)["revenue"])
        cagr = raw if raw is not None else ((a.get("classification") or {}).get("inputs") or {}).get("revenue_cagr_3y")
        metrics["revenue_growth"] = _from_row(row, cagr)
    elif "total_return" in rows:
        # V4b: en un REIT el crecimiento que puntúa es el retorno total por acción, no los ingresos
        tr = rows["total_return"]
        metrics["revenue_growth"] = {"value": None, "value_txt": "No aplica",
                                     "note": f"En un REIT el crecimiento se mide por el {_lower_first(tr.get('label'))}"
                                             + (f": {tr['value']}" if tr.get("state") == "con_dato" else "")}
    q, pa = a.get("quality") or {}, a.get("price_attractiveness") or {}
    return {"symbol": a.get("symbol"), "name": prof.get("name"), "price": a.get("price"),
            "currency": prof.get("currency"), "quality": {"score": q.get("score"), "level": q.get("level")},
            "price_score": {"score": pa.get("score"), "level": pa.get("level")},
            "confidence": (a.get("verdict") or {}).get("confidence"), "metrics": metrics,
            "reference": reference(a)}


# ───────────────────────── la cola ─────────────────────────

def _ensure_worker() -> None:
    """Con el lock tomado."""
    global _stop
    if not _workers:
        _stop = threading.Event()
        for i in range(max(1, int(_limits["workers"]))):
            t = threading.Thread(target=_loop, args=(_stop, i > 0), name=f"analysis-queue-{i}", daemon=True)
            _workers.append(t)
            t.start()


def _cap_of(priority: int) -> int:
    return _limits["max_queue"] if priority == USER else _limits["max_prewarm_queue"]


def _push(priority: int, key: str, job: Optional[Callable], client: Optional[str] = None) -> bool:
    """Encola (con el lock tomado). False si la cola de esa prioridad está llena o el cliente ya tiene
    `max_per_client` trabajos esperando (V6, B7: un cliente no llena la cola de todos)."""
    if _pending[priority] >= _cap_of(priority):
        return False
    if client is not None and _by_client.get(client, 0) >= _limits["max_per_client"]:
        return False
    _ensure_worker()
    heapq.heappush(_heap, (priority, next(_seq), key, job, client))
    _pending[priority] += 1
    if client is not None:
        _by_client[client] = _by_client.get(client, 0) + 1
    _wake.notify_all()                # el hilo que solo toma `USER` no debe quedarse con el aviso de un `PREWARM`
    return True


def _popped(priority: int, client: Optional[str]) -> None:
    """Con el lock tomado: un trabajo sale de la cola."""
    _pending[priority] -= 1
    if client is not None:
        left = _by_client.get(client, 1) - 1
        if left > 0:
            _by_client[client] = left
        else:
            _by_client.pop(client, None)


def submit(key: str, job: Callable[[threading.Event], None], priority: int = USER,
           client: Optional[str] = None) -> bool:
    """Un trabajo arbitrario en la cola (peers: ordenar los candidatos de una empresa). False si la cola está llena."""
    with _lock:
        return _push(priority, key, job, client)


def _loop(stop: threading.Event, user_only: bool = False) -> None:
    while True:
        with _lock:
            while not (_heap and (not user_only or _heap[0][0] == USER)) and not stop.is_set():
                _wake.wait()
            if stop.is_set():
                return
            priority, _n, key, job, client = heapq.heappop(_heap)
            _popped(priority, client)
            if job is None:
                if _queued.get(key) != priority:
                    continue                # entrada antigua de un símbolo que un usuario adelantó: ya se atendió
                del _queued[key]
        try:
            if job is not None:
                job(stop)
            else:
                summary_for(key, stop)
        except Exception as e:  # el hilo nunca muere por un trabajo
            logger.warning("[ANALYSIS_QUEUE] %s %s: %s", _PRIORITY_NAMES[priority], key, type(e).__name__)


def _fresh(sym: str, now: float) -> Optional[Dict[str, Any]]:
    """Con el lock tomado: el resumen en caché si no ha caducado."""
    hit = _summaries.get(sym)
    if hit and now - hit[0] < _limits["summary_ttl_s"]:
        return hit[1]
    return None


def summary_for(sym: str, stop: Optional[threading.Event] = None) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """El resumen del análisis de `sym` (desde el hilo de la cola): el de la caché o uno nuevo (prioridad baja: espera
    mientras haya usuarios esperando turno). Devuelve (resumen, None) o (None, motivo del fallo)."""
    with _lock:
        hit = _fresh(sym, time.time())
        if hit is not None:
            _state.pop(sym, None)
            return hit, None
    while BUSY() and not (stop is not None and stop.is_set()):    # los usuarios que esperan turno van antes
        time.sleep(_limits["busy_wait_s"])
    with _lock:
        _state[sym] = {"status": "analizando", "t": time.time(), "reason": None}
    try:
        if ANALYZE is None:
            raise RuntimeError("motor no conectado")
        s = _stamped(ANALYZE(sym))
    except Exception as e:
        reason = str(getattr(e, "detail", None) or str(e) or type(e).__name__)
        with _lock:
            if stop is None or not stop.is_set():
                _state[sym] = {"status": "fallo", "t": time.time(), "reason": reason}
        return None, reason
    with _lock:
        if stop is not None and stop.is_set():
            return s, None                  # la cola se reinició mientras analizaba: no escribe en la nueva caché
        _put(sym, s)
    return s, None


def _put(sym: str, s: Dict[str, Any]) -> None:
    """Con el lock tomado: guarda el resumen (LRU con tope `summary_cache_max`) y olvida el estado en marcha."""
    _summaries[sym] = (time.time(), s)
    _summaries.move_to_end(sym)
    while len(_summaries) > _limits["summary_cache_max"]:
        _summaries.popitem(last=False)
    _state.pop(sym, None)


def _stamped(analysis: Dict[str, Any]) -> Dict[str, Any]:
    # V6 (B13): cuándo se hizo el análisis del resumen (la tabla de rivales y las tarjetas pueden decir de cuándo es)
    return {**summary(analysis), "as_of": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}


def store(sym: str, analysis: Dict[str, Any]) -> None:
    """F10 · N5: el resumen del análisis que acaba de servirse a un usuario (el mismo motor que ANALYZE): la
    clasificación de sus rivales lo lee de aquí en lugar de repetir el análisis."""
    s = _stamped(analysis)
    with _lock:
        _put(sym, s)


def _status_of(sym: str, now: float) -> Optional[Dict[str, Any]]:
    """Estado conocido de un símbolo (con el lock tomado), o None si no está ni hecho ni en marcha."""
    hit = _fresh(sym, now)
    if hit is not None:
        _summaries.move_to_end(sym)
        return {"symbol": sym, "status": "listo", "summary": hit}
    st = _state.get(sym)
    if st and (st["status"] != "fallo" or now - st["t"] < _limits["fail_ttl_s"]):
        out = {"symbol": sym, "status": st["status"]}
        if st["status"] == "fallo":
            out["reason"] = st["reason"]
        return out
    return None


def _purge(now: float) -> None:
    """Con el lock tomado. V6 (B10): los fallos caducados salen de `_state` (antes se quedaban para siempre: uno por
    símbolo que falló alguna vez). Los en_cola y analizando siguen: su trabajo está en marcha."""
    old = [k for k, v in _state.items() if v["status"] == "fallo" and now - v["t"] >= _limits["fail_ttl_s"]]
    for k in old:
        del _state[k]


def request(sym: str, priority: int = USER, client: Optional[str] = None) -> Dict[str, Any]:
    """Estado del análisis de `sym`; lo encola si no está ni hecho ni en marcha. Si ya espera con menos prioridad, lo
    adelanta. Responde enseguida. V6 (B7): con la cola llena (o el cupo del cliente agotado) no es un fallo: "en_cola"
    con `retry`, sin guardar estado, y la próxima consulta lo vuelve a intentar (antes, "fallo": la tabla quedaba
    "lista" y el cliente dejaba de preguntar)."""
    now = time.time()
    with _lock:
        _purge(now)
        st = _status_of(sym, now)
        if st is not None and not (st["status"] == "en_cola" and _queued.get(sym, priority) > priority):
            return st
        if not _push(priority, sym, None, client):
            return st or {"symbol": sym, "status": "en_cola", "reason": FULL, "retry": True}
        _queued[sym] = priority
        _state[sym] = {"status": "en_cola", "t": now, "reason": None}
        return {"symbol": sym, "status": "en_cola"}


def peek(sym: str) -> Optional[Dict[str, Any]]:
    """Estado conocido de `sym` sin encolar nada (None: ni hecho ni en marcha)."""
    with _lock:
        return _status_of(sym, time.time())


def cached(sym: str) -> Optional[Dict[str, Any]]:
    """El resumen en caché de `sym`, si no ha caducado."""
    with _lock:
        return _fresh(sym, time.time())


def stats() -> Dict[str, Any]:
    """Para los tests y el registro: trabajos en cola por prioridad y si el hilo está arrancado."""
    with _lock:
        return {"user": _pending[USER], "prewarm": _pending[PREWARM], "running": bool(_workers)}
