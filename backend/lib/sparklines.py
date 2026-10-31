"""
P8 (portada con cintillo): mini-gráficas de los valores del cintillo, GET /api/v2/sparklines?symbols=A,B&period=1D.

Por símbolo y periodo, la serie de Yahoo (chart) con el intervalo y el rango de `market.sparklines.periods`:
1D, barras de 5 min de la última sesión; 1S, de 30 min de 5 sesiones; 1M y 6M, diarias. Cada serie sale:

  · reducida en el backend a `max_points` puntos con LTTB (Steinarsson, 2013: «Largest-Triangle-Three-Buckets»;
    conserva la forma, los extremos y el primer y el último punto), como [índice original, cierre] con `n`, el número
    de barras, para que el cliente sitúe cada punto en su sitio;
  · con su referencia (`ref`): el cierre anterior en 1D (descarga diaria de 5 días) y el primer cierre en 1S, 1M y
    6M, la línea punteada de la gráfica;
  · P8b: con la variación del periodo (`change_pct`) de las listas del cintillo, la misma función
    (lib/period_change.py, por lib/trending.change_of): el % de la tarjeta es exactamente el que ordena su lista. Sin
    listas o sin variación del valor en el periodo, `change_pct` es null y `change_reason` dice por qué;
  · con la fecha del primer y del último punto, o `sin_dato` y su motivo. Nunca un 5xx: si Yahoo no responde, cada
    valor sale sin gráfica y con el motivo, y la portada sigue.

Solo admite símbolos del universo (lib/universe.py), como mucho `max_symbols` por petición. Caché por (símbolo, periodo) acotada (`cache_max`, lib/bounded.py) con vida `ttl_s` del periodo (5 min en 1D, 1 h en
los demás). Las descargas pasan por la puerta de las descargas perezosas de /v2 (la de la gráfica:
price_history._chart_gate, `chart_concurrency` a la vez, una por clave y el fallo recordado). FETCH es inyectable
(tests y replay).

Portada rápida: pasado el TTL, la mini-gráfica de antes se sirve al momento, marcada `stale`, y se refresca en
segundo plano (una sola descarga por tanda aunque lleguen varias visitas); solo lo que nunca se descargó espera a
Yahoo. Al publicar las listas, lib/trending.py descarga las de la vista inicial (`get` como la web) y las guarda en su
archivo con `dump`; tras un reinicio vuelven con `load`, con su hora (caducan igual).
"""
import datetime as _dt
import re
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import bounded
from settings import cfg

_SYMBOL = re.compile(r"^[A-Z0-9.\-]{1,10}$")     # la misma regla que el resto de /v2 (main._V2_SYMBOL)

Series = List[Tuple[str, float]]                # [(fecha u hora ISO, cierre)] de la más antigua a la más reciente


class InvalidRequest(ValueError):
    """Petición fuera de lo admitido: su mensaje (corto, sin eco del valor) va en el 422."""


def _frame_to_series(df, symbols: Sequence[str]) -> Dict[str, Series]:
    out: Dict[str, Series] = {}
    if df is None or not len(df.columns):
        return out
    multi = getattr(df.columns, "nlevels", 1) > 1
    have = set(df.columns.get_level_values(0)) if multi else set()
    for sym in symbols:
        if multi and sym not in have:
            continue
        sub = (df[sym] if multi else df)["Close"].dropna()
        intraday = any(getattr(t, "hour", 0) or getattr(t, "minute", 0) for t in sub.index[:3])
        out[sym] = [((t.isoformat() if intraday else t.strftime("%Y-%m-%d")), float(v)) for t, v in sub.items()]
    return out


def yf_fetch(symbols: List[str], rng: str, interval: str) -> Dict[str, Series]:
    """Descarga real por lotes (yf.download, sin ajustar: el cierre que muestra Yahoo, como las tendencias)."""
    import yfinance as yf
    df = yf.download(symbols, period=rng, interval=interval, group_by="ticker", threads=True, auto_adjust=False,
                     prepost=False, progress=False)
    return _frame_to_series(df, symbols)


FETCH: Callable[[List[str], str, str], Dict[str, Series]] = yf_fetch

_lock = threading.Lock()
_cache: Dict[Tuple[str, str], Tuple[float, Dict[str, Any]]] = {}
_refreshing: Dict[Tuple[str, Tuple[str, ...]], threading.Thread] = {}     # (periodo, tanda) caducada en descarga


def reset() -> None:
    with _lock:
        _cache.clear()


def peek(symbol: str, period: str) -> Optional[Dict[str, Any]]:
    """La mini-gráfica en caché (vigente o caducada), sin descargar."""
    with _lock:
        hit = _cache.get((symbol, period))
    return hit[1] if hit else None


def dump(period: str, symbols: Sequence[str]) -> Dict[str, Dict[str, list]]:
    """{periodo: {símbolo: [hora, mini-gráfica]}} de los que están en caché (para el archivo de la portada)."""
    with _lock:
        return {period: {s: [_cache[(s, period)][0], _cache[(s, period)][1]] for s in symbols if (s, period) in _cache}}


def load(snapshot: Dict[str, Dict[str, list]]) -> None:
    """Vuelve a poner en caché lo de `dump`, con su hora."""
    cap = cfg("market.sparklines.cache_max")
    with _lock:
        for period, items in (snapshot or {}).items():
            for s, (ts, it) in items.items():
                bounded.put(_cache, (s, period), (float(ts), it), cap)


def wait_refreshes(timeout: float = 30.0) -> None:
    """Espera a los refrescos en segundo plano (tests y herramientas)."""
    with _lock:
        threads = list(_refreshing.values())
    for t in threads:
        t.join(timeout)


# ─────────────────────────── validación ───────────────────────────
def parse(symbols: Optional[str], period: Optional[str]) -> Tuple[List[str], str]:
    """Símbolos (en mayúsculas, sin repetir, en su orden) y periodo; InvalidRequest si algo no cumple."""
    S = cfg("market.sparklines")
    p = (period or "1D").strip().upper()
    if p not in S["periods"]:
        raise InvalidRequest(f"periodo no válido (admitidos: {', '.join(S['periods'])})")
    raw = [s.strip().upper() for s in (symbols or "").split(",") if s.strip()]
    if not raw:
        raise InvalidRequest("faltan los símbolos")
    if len(raw) > S["max_symbols"]:
        raise InvalidRequest(f"como mucho {S['max_symbols']} símbolos por petición")
    if any(not _SYMBOL.match(s) for s in raw):
        raise InvalidRequest("símbolo no válido")
    import universe
    out: List[str] = []
    for s in raw:
        n = universe.norm_symbol(s)
        if n not in out:
            out.append(n)
    # V6b: solo los valores del universo del cintillo (los únicos que la portada muestra): una lista de símbolos
    # inventados no puede convertir cada petición en descargas nuevas de Yahoo.
    if any(not _in_universe(s) for s in out):
        raise InvalidRequest("símbolo fuera del universo de la portada")
    return out, p


def _in_universe(symbol: str) -> bool:
    import universe
    return universe.get(symbol) is not None


# ─────────────────────────── reducción LTTB ───────────────────────────
def lttb(values: Sequence[float], threshold: int) -> List[int]:
    """Índices de los puntos que conserva LTTB (Largest-Triangle-Three-Buckets): el primero, el último y, en cada uno
    de los `threshold − 2` tramos intermedios, el que forma el triángulo de más área con el elegido antes y la media
    del tramo siguiente. Con menos puntos que el umbral, todos."""
    n = len(values)
    if threshold >= n or threshold < 3:
        return list(range(n))
    keep = [0]
    every = (n - 2) / (threshold - 2)
    a = 0
    for i in range(threshold - 2):
        s0, s1 = int(i * every) + 1, int((i + 1) * every) + 1
        n0, n1 = s1, min(int((i + 2) * every) + 1, n)
        if n0 >= n1:                                  # el último tramo: la media es el último punto
            n0, n1 = n - 1, n
        ax, ay = a, values[a]
        cx = sum(range(n0, n1)) / (n1 - n0)
        cy = sum(values[n0:n1]) / (n1 - n0)
        best, area = s0, -1.0
        for j in range(s0, min(s1, n - 1)):
            ar = abs((ax - cx) * (values[j] - ay) - (ax - j) * (cy - ay))
            if ar > area:
                best, area = j, ar
        keep.append(best)
        a = best
    keep.append(n - 1)
    return keep


def _round(v: float) -> float:
    return round(v, 2) if abs(v) >= 1 else round(v, 4)


# ─────────────────────────── una serie ───────────────────────────
def build_item(series: Optional[Series], period: str, ref: Optional[float] = None,
               why: Optional[str] = None) -> Dict[str, Any]:
    """La mini-gráfica de un símbolo: puntos reducidos, referencia, variación y fechas; o sin dato con su motivo."""
    if not series or len(series) < 2:
        return {"status": "sin_dato", "reason": why or ("Yahoo no devolvió la serie del periodo" if not series else
                                                        "una sola cotización en el periodo")}
    vals = [v for _, v in series]
    base = vals[0] if ref is None else ref
    if not base or base <= 0:
        return {"status": "sin_dato", "reason": "sin precio de partida del periodo"}
    keep = lttb(vals, cfg("market.sparklines.max_points"))
    return {"status": "ok", "n": len(vals), "points": [[i, _round(vals[i])] for i in keep],
            "ref": _round(base), "ref_basis": "cierre anterior" if ref is not None else "primer cierre",
            "last": _round(vals[-1]), "first_t": series[0][0], "last_t": series[-1][0], "reason": None}


def _previous_close(daily: Optional[Series], session_day: str) -> Optional[float]:
    """1D: el cierre de la sesión anterior a la de las barras de 5 min (la última diaria antes de ese día)."""
    prev = [v for d, v in (daily or []) if d[:10] < session_day]
    return prev[-1] if prev else None


def _last_session(series: Optional[Series]) -> Optional[Series]:
    """Las barras intradía de la última sesión de la descarga (el rango de 1 día puede traer el final de otra)."""
    if not series:
        return series
    day = series[-1][0][:10]
    return [x for x in series if x[0][:10] == day]


# ─────────────────────────── descarga con la puerta de /v2 ───────────────────────────
def _download(symbols: List[str], period: str) -> Dict[str, Dict[str, Any]]:
    P = cfg("market.sparklines.periods")[period]
    import price_history
    gate = price_history._chart_gate()

    def fetch(rng, interval):
        def make():
            try:
                return FETCH(symbols, rng, interval)
            except Exception as e:  # la fuente falla de muchas maneras: sin gráfica y se dice, nunca un 5xx
                return {"__error__": f"Yahoo no respondió ({type(e).__name__})"}
        return gate.run(("sparklines", period, rng, interval, tuple(symbols)), make, lambda r: "__error__" in r)
    # Portada rápida: en 1D, las barras y la diaria de la referencia a la vez (las mismas dos descargas, solapadas).
    daily: Dict[str, Any] = {}
    side = None
    if period == "1D":
        side = threading.Thread(target=lambda: daily.update(fetch("5d", "1d")), name="sparklines-ref", daemon=True)
        side.start()
    bars = fetch(P["range"], P["interval"])
    if side is not None:
        side.join()
    if "__error__" in bars or "__error__" in daily:
        daily = {}
    err = bars.get("__error__")
    out = {}
    for s in symbols:
        if err:
            out[s] = build_item(None, period, why=err)
        elif period == "1D":
            ses = _last_session(bars.get(s))
            ref = _previous_close(daily.get(s), ses[-1][0][:10]) if ses else None
            out[s] = (build_item(ses, period, ref=ref) if ref is not None or not ses else
                      build_item(ses, period, why="sin el cierre de la sesión anterior"))
        else:
            out[s] = build_item(bars.get(s), period)
    return out


def _fetch_into(chunk: List[str], period: str) -> Dict[str, Dict[str, Any]]:
    """Descarga una tanda y guarda en caché lo bueno (el fallo lo recuerda la puerta)."""
    got = _download(chunk, period)
    now = time.time()
    with _lock:
        for s, it in got.items():
            if it["status"] == "ok":
                bounded.put(_cache, (s, period), (now, it), cfg("market.sparklines.cache_max"))
    return got


def _refresh_later(symbols: List[str], period: str) -> None:
    """Refresca en segundo plano las caducadas, por tandas; una tanda que ya se refresca no se vuelve a pedir."""
    size = cfg("market.sparklines.batch_size")
    for i in range(0, len(symbols), size):
        key = (period, tuple(symbols[i:i + size]))

        def run(key=key):
            try:
                _fetch_into(list(key[1]), key[0])
            finally:
                with _lock:
                    _refreshing.pop(key, None)
        with _lock:
            if key in _refreshing:
                continue
            t = threading.Thread(target=run, name="sparklines-refresh", daemon=True)
            _refreshing[key] = t
        t.start()


def get(symbols: List[str], period: str) -> Dict[str, Any]:
    """{period, label, interval, as_of, items: {símbolo: mini-gráfica}} en el orden pedido. Nunca lanza. Las
    caducadas salen al momento con `stale` y se refrescan en segundo plano."""
    S = cfg("market.sparklines")
    P = S["periods"][period]
    now = time.time()
    items: Dict[str, Dict[str, Any]] = {}
    expired: List[str] = []
    with _lock:
        for s in symbols:
            hit = _cache.get((s, period))
            if hit and now - hit[0] < P["ttl_s"]:
                items[s] = hit[1]
            elif hit:
                items[s] = {**hit[1], "stale": True}
                expired.append(s)
    if expired:
        _refresh_later(expired, period)
    missing = [s for s in symbols if s not in items]
    for i in range(0, len(missing), S["batch_size"]):
        items.update(_fetch_into(missing[i:i + S["batch_size"]], period))
    lasts = [it["last_t"] for it in items.values() if it.get("status") == "ok"]
    import trending
    for s in symbols:            # P8b: la variación de las listas (no se guarda en caché: las listas se renuevan)
        if items[s].get("status") == "ok":
            ch = trending.change_of(s, period)
            items[s] = {**items[s], "change_pct": ch,
                        "change_reason": None if ch is not None else "sin variación del periodo en las listas"}
    return {"period": period, "label": P["label"], "interval": P["interval"],
            "as_of": max(lasts) if lasts else None,
            "generated": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "items": {s: items[s] for s in symbols}}
