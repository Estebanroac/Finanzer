"""
Rediseño E2b (Task 4; spec §4, dato 10): tendencias del día de la portada sobre el universo (S&P 500 + ADR
principales, lib/universe.py): más negociadas (volumen en dólares: cierre × volumen de la última sesión), mayores
subidas y mayores caídas (frente a la sesión anterior). Misma fuente de precios que ya funciona en Render (Yahoo), en
descargas por lotes de `batch_size` símbolos (yf.download, 5 días).

Cálculo perezoso: `get()` devuelve enseguida la última lista buena (memoria del proceso) y, si es de una sesión
anterior a la última cerrada (16:00 de Nueva York + `refresh_after_close_min`) o no hay, lanza el cálculo en un hilo
(uno a la vez). Tras un reinicio de Render el primer pedido responde "calculando" y el cliente repite. Sin calendario
de festivos: si Yahoo no trae una sesión nueva, la lista sigue con su fecha y no se vuelve a descargar hasta la
siguiente sesión esperada. En Render se precalienta al arrancar (`warm`). FETCH_BATCH es inyectable (tests y replay).

P8 (cintillo de la portada): además, `sectors`: por sector GICS (clave estable en inglés; la etiqueta en español va en
`sector_labels`), los `top_n` valores de más volumen en dólares, de la misma descarga (sin llamadas nuevas). Cada fila
lleva su `sector`. Un sector con menos de `min_sector_items` valores con cotización sale en `sector_status` como no
disponible, con su motivo: la portada muestra el chip deshabilitado, no lo oculta.

Rediseño E4 (Task 1): cada tarjeta lleva la calidad y el precio del motor (`engine`; con `fallo`, su motivo), para distinguir negocio de ruido.
Salen del resumen compacto de la cola compartida (lib/analysis_queue.py): tras calcular las listas, y en cada consulta
mientras falten, sus símbolos sin resumen se encolan con prioridad `prewarm` (de uno en uno, solo sin usuarios
esperando, por detrás de cualquier rival pedido), como mucho `prewarm_max` al día. `engine` es null si el símbolo no
está ni analizado ni en marcha (se agotó el cupo del día, la cola está llena o el análisis caducó).

P8b: las listas se calculan en el periodo elegido en la portada (1D, 1S, 1M, 6M; el mismo de las mini-gráficas), no
en la sesión del día: `lists[periodo]`, `sectors[periodo]`, `sector_status[periodo]` y `periods[periodo]` (sesiones y
fechas de partida y final). La descarga es diaria de `history_days` días naturales y sin ajustar («Close», el precio
que se muestra) con su «Adj Close» (la rentabilidad del periodo, lib/period_change.py: la misma función que la
variación de /api/v2/sparklines). «Suben más» solo trae valores que suben y «Bajan más» solo los que bajan: si no
llegan a `top_n`, la lista es más corta y `list_notes` lo dice. «Más negociadas» y los sectores ordenan por el volumen
medio diario en dólares de las sesiones del periodo.

Portada rápida: la descarga del universo tarda ~27 s (una petición a Yahoo por valor, 543 valores; no depende de los
días pedidos ni mejora con más hilos), así que el servidor:
  · empieza el cálculo al arrancar (`warm`, evento startup de main; también en local), salvo FINANZER_TRENDING_WARM=0;
  · guarda la última lista buena en `SNAPSHOT` (el archivo de `snapshot_file`) con las mini-gráficas de la vista
    inicial, y tras un reinicio la sirve al momento (`restore`): si es de la misma sesión y del mismo universo no se
    recalcula (dentro de una sesión la lista no cambia); si no, se sirve mientras se recalcula, como un servidor
    caliente. Un archivo de otra config o ilegible se ignora;
  · al publicar las listas descarga las mini-gráficas de la vista inicial (1D, «Más negociadas»), con la misma petición
    que hará la web (la descarga en marcha se comparte en la puerta de lib/sparklines.py).
"""
import contextlib
import datetime as _dt
import hashlib
import json
import logging
import os
import threading
import time
from collections.abc import Mapping
from typing import Any, Callable, Dict, List, Optional
from zoneinfo import ZoneInfo

import analysis_queue as AQ
import period_change as PC
import universe
from settings import cfg

logger = logging.getLogger(__name__)
NY = ZoneInfo("America/New_York")
_FRIDAY = 4


def yf_batch(symbols: List[str]):
    """Descarga real por lotes: diaria de `history_days` días naturales, sin ajustar («Close» y «Volume», lo que muestra
    Yahoo) y con «Adj Close» (la rentabilidad del periodo)."""
    import yfinance as yf
    start = (_dt.date.today() - _dt.timedelta(days=cfg("market.trending.history_days"))).isoformat()
    return yf.download(symbols, start=start, interval="1d", group_by="ticker", threads=True, auto_adjust=False,
                       progress=False)


FETCH_BATCH: Callable[[List[str]], Any] = yf_batch
# Verificación de la v4 (V4 · memoria): cada lote se descarga dentro de un turno de fondo de los análisis (main lo
# inyecta: _slot(user=False), que espera mientras haya usuarios esperando). Así la descarga del universo no coincide
# con `max_concurrent_analyses` análisis a la vez. Por defecto (tests, herramientas), sin turno.
SLOT: Callable[[], Any] = contextlib.nullcontext
# Portada rápida: los pone `warm` al arrancar el servidor. Sin ellos (tests, herramientas), ni archivo ni descarga de
# mini-gráficas.
SNAPSHOT: Optional[str] = None
WARM_SPARKLINES = False
_SNAPSHOT_VERSION = 1

_lock = threading.Lock()
_limits: Dict[str, Any] = {}
_state: Dict[str, Any] = {}
_generation = [0]                        # reset() la sube: un cálculo en marcha de antes no escribe ni precalienta


def reset() -> None:
    with _lock:
        _generation[0] += 1
        _limits.clear()
        _limits.update(cfg("market.trending"))
        _state.clear()
        _state.update(data=None, checked_for=None, computing=False, error=None, failed_at=None,
                      prewarm_day=None, prewarmed=set())


reset()


def _universe_symbols() -> List[str]:
    return universe.symbols()


def last_closed_session(now: Optional[_dt.datetime] = None) -> str:
    """Fecha (Nueva York) de la última sesión regular cerrada: hoy si es día laborable y ya pasó el cierre más
    `refresh_after_close_min`; si no, el día laborable anterior. Sin festivos."""
    T = _limits
    now = (now or _dt.datetime.now(NY)).astimezone(NY)
    close = now.replace(hour=T["close_hour_et"], minute=0, second=0, microsecond=0) + \
        _dt.timedelta(minutes=T["refresh_after_close_min"])
    day = now.date() if now >= close else now.date() - _dt.timedelta(days=1)
    while day.weekday() > _FRIDAY:
        day -= _dt.timedelta(days=1)
    return day.isoformat()


def _rows(df, chunk: List[str], session: Optional[str]) -> Dict[str, Dict[str, list]]:
    """Por símbolo, listas compactas (fechas ISO, cierre, cierre ajustado y volumen): el lote crudo no se guarda."""
    out = {}
    tickers = set(df.columns.get_level_values(0)) if df is not None and len(df.columns) else set()
    for sym in chunk:
        if sym not in tickers:
            continue
        sub = df[sym]
        cols = set(sub.columns)
        if session:
            sub = sub[sub.index.strftime("%Y-%m-%d") <= session]
        sub = sub.dropna(subset=["Close"])
        if not len(sub):
            continue
        close = [float(v) for v in sub["Close"]]
        # sin «Adj Close» (o vacío en una fila), el cierre: sin dividendos ni splits que ajustar en esa fila
        adj = ([float(a) if a == a else c for a, c in zip(sub["Adj Close"], close)] if "Adj Close" in cols else close)
        vol = [float(v) if v == v else None for v in sub["Volume"]] if "Volume" in cols else [None] * len(close)
        out[sym] = {"dates": [d.strftime("%Y-%m-%d") for d in sub.index], "close": close, "adj": adj, "vol": vol}
    return out


class TrendingUnavailable(RuntimeError):
    """Sin cotizaciones del universo: su mensaje ya es el motivo que se muestra."""


def compute(fetch_batch: Callable[[List[str]], Any], session: Optional[str] = None) -> Dict[str, Any]:
    """Las tres listas y las de sector de cada periodo, hasta la última sesión de la descarga (o `session`, recortando
    la fila parcial de hoy). `changes`: la variación de cada valor en cada periodo (la de las mini-gráficas)."""
    T = _limits
    syms = _universe_symbols()
    frames: Dict[str, Any] = {}
    failed = 0
    for i in range(0, len(syms), T["batch_size"]):
        chunk = syms[i:i + T["batch_size"]]
        try:
            with SLOT():
                raw = fetch_batch(chunk)
            frames.update(_rows(raw, chunk, session))
            del raw                         # el lote crudo (yf.download) no espera al siguiente
        except Exception as e:  # un lote que falla no tira los demás; se cuenta
            failed += 1
            logger.warning("[TRENDING] lote %d: %s", i // T["batch_size"], type(e).__name__)
            last_error = e
    if not frames:
        # Verificación de la v4 (V3): el motivo se muestra en la portada: en lenguaje claro; el error técnico, al log.
        if failed:
            logger.warning("[TRENDING] último error: %s: %s", type(last_error).__name__, last_error)
        raise TrendingUnavailable(f"Yahoo no devolvió cotizaciones del universo ({failed} de "
                                  f"{-(-len(syms) // T['batch_size'])} lotes fallidos)")
    last = max(f["dates"][-1] for f in frames.values())
    calendar = sorted({d for f in frames.values() for d in f["dates"] if d <= last})
    per: Dict[str, List[Dict[str, Any]]] = {p: [] for p in PC.periods()}
    changes: Dict[str, Dict[str, Optional[float]]] = {}
    for sym, f in frames.items():
        if f["dates"][-1] != last or f["close"][-1] < T["min_price"]:
            continue
        row = universe.get(sym) or {}
        base = {"symbol": sym, "name": row.get("display_name") or row.get("name"), "price": f["close"][-1],
                "sector": row.get("gics_sector")}
        changes[sym] = {}
        for p in per:
            ch = PC.change(f["dates"], f["adj"], calendar, p)
            changes[sym][p] = ch
            if ch is None:
                continue
            ref = PC.reference_date(calendar, p)
            dv = [c * v for d, c, v in zip(f["dates"], f["close"], f["vol"]) if d > ref and v is not None]
            per[p].append({**base, "change_pct": ch, "dollar_volume": sum(dv) / len(dv) if dv else None})
    if not any(per.values()):
        raise TrendingUnavailable("Yahoo no devolvió dos sesiones de cotización del universo")
    n = T["top_n"]
    meta = universe.meta()
    stale = (meta.get("date") is None or (_dt.date.today() - _dt.date.fromisoformat(meta["date"])).days
             > cfg("market.universe.max_age_days"))
    lists, notes, sectors, status, periods = {}, {}, {}, {}, {}
    for p, items in per.items():
        label = cfg("market.sparklines.periods")[p]["label"]
        traded = [x for x in items if x["dollar_volume"] is not None]
        by_volume = sorted(traded, key=lambda x: (-x["dollar_volume"], x["symbol"]))   # empates: por símbolo
        up = sorted((x for x in items if x["change_pct"] > 0), key=lambda x: (-x["change_pct"], x["symbol"]))
        down = sorted((x for x in items if x["change_pct"] < 0), key=lambda x: (x["change_pct"], x["symbol"]))
        lists[p] = {"most_traded": by_volume[:n], "gainers": up[:n], "losers": down[:n]}
        notes[p] = {"gainers": _short_note(len(up), n, "suben", label),
                    "losers": _short_note(len(down), n, "bajan", label)}
        sec = _sectors(by_volume, n)
        sectors[p], status[p] = sec["sectors"], sec["sector_status"]
        periods[p] = {"label": label, "sessions": PC.sessions(p), "from": PC.reference_date(calendar, p),
                      "to": last, "count": len(items)}
    return {"session": last, "as_of": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "periods": periods, "lists": lists, "list_notes": notes, "sectors": sectors, "sector_status": status,
            "changes": changes,
            # `count`: valores con variación de 1 día (los que entran en las listas del día)
            "universe_date": meta.get("date"), "count": len(per[PC.periods()[0]]), "failed_batches": failed,
            "note": f"universo del {meta.get('date')}" if stale else None}


def _short_note(found: int, n: int, verb: str, label: str) -> Optional[str]:
    """«Suben más» solo con valores que suben (y «Bajan más» con los que bajan): si no llegan a `n`, se dice."""
    one = {"suben": "sube", "bajan": "baja"}[verb]
    if found >= n:
        return None
    if not found:
        return f"ningún valor del universo {one} en {label}"
    return f"solo {found} valor{'es' if found != 1 else ''} del universo {verb if found != 1 else one} en {label}"


def _sectors(by_volume: List[Dict[str, Any]], n: int) -> Dict[str, Any]:
    """P8: los `n` de más volumen en dólares de cada sector (en el orden de `sectors` de config) y su estado: con menos
    de `min_sector_items` valores con cotización, no disponible y por qué."""
    T = _limits
    out, status = {}, {}
    for key in T["sectors"]:
        rows = [x for x in by_volume if x.get("sector") == key]
        out[key] = rows[:n]
        ok = len(rows) >= T["min_sector_items"]
        status[key] = {"label": T["sector_labels"].get(key, key), "count": len(rows), "available": ok,
                       "reason": None if ok else (f"solo {len(rows)} valor{'es' if len(rows) != 1 else ''} del sector "
                                                  f"con cotización en el periodo (mínimo {T['min_sector_items']})")}
    return {"sectors": out, "sector_status": status}


def _symbols(data: Dict[str, Any]) -> List[str]:
    """Los símbolos de las tres listas de 1 día, sin repetir, en el orden de la portada (más negociadas, subidas,
    caídas)."""
    out: List[str] = []
    day = data["lists"][PC.periods()[0]]      # P8b: el precalentado sigue siendo el de las listas de 1 día
    for k in ("most_traded", "gainers", "losers"):
        out += [x["symbol"] for x in day[k] if x["symbol"] not in out]
    return out


def prewarm(data: Dict[str, Any], today: Optional[str] = None) -> int:
    """Encola con prioridad `prewarm` los símbolos de las listas que no están ni analizados ni en marcha, como mucho
    `prewarm_max` distintos al día (fecha de Nueva York) y cada uno una sola vez al día. Devuelve cuántos encoló."""
    today = today or _dt.datetime.now(NY).date().isoformat()
    queued = 0
    AQ.pin(_symbols(data)[:_limits["prewarm_max"]])   # las que puntúa el precalentado: sin expulsar
    for sym in _symbols(data):
        if AQ.peek(sym) is not None:
            continue
        with _lock:
            if _state["prewarm_day"] != today:
                _state.update(prewarm_day=today, prewarmed=set())
            if sym in _state["prewarmed"]:
                continue                    # una vez al día: un análisis que falló no se repite cada 10 min
            if len(_state["prewarmed"]) >= _limits["prewarm_max"]:
                break
            _state["prewarmed"].add(sym)
        r = AQ.request(sym, AQ.PREWARM)
        if r["status"] == "en_cola" and not r.get("retry"):
            queued += 1
    return queued


def _engine(sym: str) -> Optional[Dict[str, Any]]:
    """La calidad y el precio del motor de una tarjeta, desde la caché de la cola (None: sin análisis ni en marcha)."""
    st = AQ.peek(sym)
    if st is None:
        return None
    s = st.get("summary") or {}
    return {"status": st["status"], "quality": s.get("quality"), "price_score": s.get("price_score"),
            "as_of": s.get("as_of"), "reason": st.get("reason") if st["status"] == "fallo" else None}


def with_engine(data: Dict[str, Any]) -> Dict[str, Any]:
    """Copia de las listas (y de las de sector, P8) con `engine` en cada tarjeta (la lista guardada no cambia). El
    precalentado sigue siendo el de las tres listas del día (`_symbols`); los sectores muestran el resumen si ya está."""
    engines: Dict[str, Any] = {}

    def eng(sym):
        if sym not in engines:
            engines[sym] = _engine(sym)
        return engines[sym]
    def cards(groups):        # P8b: {periodo: {lista o sector: [tarjetas]}}
        return {p: {k: [{**x, "engine": eng(x["symbol"])} for x in v] for k, v in g.items()} for p, g in groups.items()}
    out = {k: v for k, v in data.items() if k != "changes"}      # las variaciones van a las mini-gráficas, no aquí
    out["lists"] = cards(data["lists"])
    if "sectors" in data:
        out["sectors"] = cards(data["sectors"])
    return out


def change_of(symbol: str, period: str) -> Optional[float]:
    """P8b: la variación del periodo con la que se ordenan las listas (la de la tarjeta y la de su mini-gráfica). None
    si aún no hay listas o el valor no tiene variación en ese periodo."""
    with _lock:
        data = _state["data"]
    return ((data or {}).get("changes") or {}).get(symbol, {}).get(period)


def _first_view(data: Dict[str, Any]) -> List[str]:
    """Los símbolos de la vista inicial de la portada (1D, «Más negociadas»), en su orden: los que pide la web."""
    return [x["symbol"] for x in data["lists"][PC.periods()[0]]["most_traded"]]


def _plain(o: Any) -> Any:
    return dict(o) if isinstance(o, Mapping) else list(o)


def _fingerprint() -> str:
    """La config de la que depende la forma del archivo (listas y mini-gráficas): otra, y el archivo no vale."""
    raw = json.dumps({"trending": cfg("market.trending"), "sparklines": cfg("market.sparklines")}, sort_keys=True,
                     default=_plain)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _save() -> None:
    """La última lista buena y las mini-gráficas de su vista inicial, en `SNAPSHOT` (escritura atómica)."""
    path = SNAPSHOT
    with _lock:
        data, checked = _state["data"], _state["checked_for"]
    if not path or data is None:
        return
    import sparklines
    snap = {"version": _SNAPSHOT_VERSION, "fingerprint": _fingerprint(), "checked_for": checked, "data": data,
            "sparklines": sparklines.dump(PC.periods()[0], _first_view(data))}
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        tmp = f"{path}.tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(snap, fh, ensure_ascii=False, separators=(",", ":"))
        os.replace(tmp, path)
    except OSError as e:                     # sin disco: la portada sigue, solo sin archivo
        logger.warning("[TRENDING] no se pudo guardar %s: %s", path, type(e).__name__)


def restore() -> bool:
    """Tras un reinicio: la última lista buena del archivo, si es de esta config y no hay otra en memoria. De la misma
    sesión y universo no se recalcula; si no, se sirve mientras se recalcula. Sus mini-gráficas vuelven con su hora."""
    if not SNAPSHOT:
        return False
    try:
        with open(SNAPSHOT, encoding="utf-8") as fh:
            snap = json.load(fh)
        data = snap["data"]
        _first_view(data)
        ok = snap.get("version") == _SNAPSHOT_VERSION and snap.get("fingerprint") == _fingerprint()
    except FileNotFoundError:
        return False
    except Exception as e:  # noqa: BLE001 — archivo a medias o de otra versión: se ignora y se calcula
        logger.warning("[TRENDING] archivo de la portada ilegible (%s): se calcula", type(e).__name__)
        return False
    if not ok:
        return False
    same_universe = data.get("universe_date") == universe.meta().get("date")
    with _lock:
        if _state["data"] is not None:
            return False
        _state.update(data=data, checked_for=snap.get("checked_for") if same_universe else None)
    import sparklines
    sparklines.load(snap.get("sparklines") or {})
    return True


def _after_lists(data: Dict[str, Any]) -> None:
    """Con las listas publicadas: las mini-gráficas de la vista inicial (si las descarga el servidor) y el archivo."""
    if WARM_SPARKLINES:
        try:
            import sparklines
            sparklines.get(_first_view(data), PC.periods()[0])
            sparklines.wait_refreshes()
        except Exception as e:  # noqa: BLE001 — la web las pedirá igual
            logger.warning("[TRENDING] mini-gráficas de la vista inicial: %s", type(e).__name__)
    _save()


def _run(expected: str, generation: int) -> None:
    try:
        data = compute(FETCH_BATCH, session=expected)
        with _lock:
            if generation != _generation[0]:
                return
            _state.update(data=data, checked_for=expected, error=None, failed_at=None, computing=False)
        prewarm(data)
        _after_lists(data)
    except Exception as e:
        with _lock:
            if generation == _generation[0]:
                msg = str(e) if isinstance(e, TrendingUnavailable) else f"{type(e).__name__}: {e}"
                _state.update(error=msg[:300], failed_at=time.monotonic())
    finally:
        with _lock:
            if generation == _generation[0]:
                _state["computing"] = False


_BY_PERIOD = ("lists", "list_notes", "sectors", "sector_status")


def only_period(data: Dict[str, Any], period: str) -> Dict[str, Any]:
    """V6b: las listas, notas y sectores de un solo periodo (`periods` va entero): la portada pide el que muestra y la
    respuesta, que se repite cada `poll_s` mientras se analizan tarjetas, pesa una cuarta parte."""
    return {k: ({period: v.get(period)} if k in _BY_PERIOD and isinstance(v, dict) else v) for k, v in data.items()}


def get(period: Optional[str] = None) -> Dict[str, Any]:
    """{status: listo | calculando | sin_dato, data, refreshing, reason, poll_s}. Nunca bloquea. Con `data`, cada
    tarjeta lleva `engine` y los símbolos que aún no tienen resumen se encolan (dentro del cupo del día). Con
    `period` (uno de `periods`, validado por el endpoint), solo las listas de ese periodo."""
    expected = last_closed_session()
    with _lock:
        s = _state
        recent_fail = s["failed_at"] is not None and time.monotonic() - s["failed_at"] < _limits["retry_after_s"]
        if s["checked_for"] != expected and not s["computing"] and not recent_fail:
            s["computing"] = True
            threading.Thread(target=_run, args=(expected, _generation[0]), name="trending", daemon=True).start()
        data, computing, error = s["data"], s["computing"], s["error"]
    poll = {"poll_s": _limits["poll_s"]}
    if data is not None:
        prewarm(data)
        out = with_engine(only_period(data, period) if period else data)
        return {"status": "listo", "data": out, "refreshing": computing, "reason": None, **poll}
    if computing:
        return {"status": "calculando", "data": None, "refreshing": True, "reason": None, **poll}
    return {"status": "sin_dato", "data": None, "refreshing": False,
            "reason": f"no se pudieron calcular las tendencias: {error}" if error else "sin cálculo", **poll}


def warm(env, snapshot: Optional[str] = None) -> bool:
    """Al arrancar el servidor (main, evento startup): la última lista buena del archivo `snapshot` si la hay y el
    cálculo, en su hilo; el primer visitante no espera la descarga. FINANZER_TRENDING_WARM=0 lo apaga (tests)."""
    global SNAPSHOT, WARM_SPARKLINES
    if env.get("FINANZER_TRENDING_WARM") == "0":
        return False
    SNAPSHOT, WARM_SPARKLINES = snapshot, True
    if restore():
        with _lock:
            data = _state["data"]
        threading.Thread(target=_after_lists, args=(data,), name="trending-restore", daemon=True).start()
    get()
    return True
