"""
Endpoint TEMPORAL de captura de inputs crudos (etapa 2.1 del rediseño).

    GET /api/_capture/{symbol}      cabecera: X-Capture-Token: <CAPTURE_TOKEN>

Desactivado por defecto: responde 404 salvo que exista la variable de entorno
CAPTURE_TOKEN en el servidor Y la petición envíe exactamente ese valor en la
cabecera X-Capture-Token. Así es indistinguible de una ruta inexistente.

Devuelve los INPUTS que recibe el pipeline para ese ticker, no el análisis:
  - yahoo_http: respuesta cruda de v10/finance/quoteSummary
  - yfinance:   income_stmt / balance_sheet / cashflow (y fast_info/info si
                se activó el fallback de yfinance)
  - finnhub:    respuestas de /stock/metric (si Finnhub participó)
  - metadata:   fecha, entorno, versiones, si Yahoo vino degradado, si Finnhub
                participó (solo booleano: la clave nunca se expone)

Cómo: ejecuta yf_adapter.get_ticker_info(symbol) EN FRÍO (invalida solo las
cachés de ese ticker) con envoltorios temporales que registran cada llamada a
las fuentes y las reenvían sin modificar. No toca la lógica del análisis: es
el mismo camino que recorre /api/analysis. Tras la captura, la caché queda
con exactamente esos inputs, así que un /api/analysis inmediato (antes de
60-300 s) devuelve el análisis que corresponde a ellos.

Redacción: los parámetros token/crumb/apikey nunca se registran y, por
defensa en profundidad, el JSON final se filtra con una regex `token=...` y
se reemplazan los valores de FINNHUB_API_KEY y CAPTURE_TOKEN si aparecieran.

Retirada: borrar este archivo y las 2 líneas que lo registran en main.py, o
simplemente quitar CAPTURE_TOKEN en Render (el endpoint vuelve a dar 404).
"""
import datetime as _dt
import hmac
import json
import math
import os
import platform
import re
import threading

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import Response

router = APIRouter()

_LOCK = threading.Lock()
_SYMBOL_RE = re.compile(r"^[A-Z0-9.\-^=]{1,15}$")
_SECRET_PARAMS = {"token", "crumb", "apikey", "api_key"}
_SECRET_RE = re.compile(r"(?i)\b((?:token|crumb|apikey|api_key)=)[^&\s\"'\\]+")
_SESSION_URLS = ("https://finance.yahoo.com", "/v1/test/getcrumb")
_FRAMES = ("income_stmt", "balance_sheet", "cashflow")


def _scalar(v):
    if v is None:
        return None
    if hasattr(v, "item") and not isinstance(v, (str, bytes)):
        try:
            v = v.item()
        except Exception:
            pass
    if isinstance(v, float) and math.isnan(v):
        return None
    if isinstance(v, (bool, int, float, str)):
        return v
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return str(v)


def _df(df):
    if df is None:
        return None
    cols = list(df.columns)
    dates = bool(cols) and all(hasattr(c, "isoformat") for c in cols)
    return {
        "__type__": "DataFrame",
        "dtypes": sorted({str(t) for t in df.dtypes}),
        "columns_are_dates": dates,
        "columns": [c.isoformat() if dates else str(c) for c in cols],
        "index": [str(i) for i in df.index],
        "data": [[_scalar(v) for v in row] for row in df.to_numpy(dtype=object).tolist()],
    }


def _clean(params):
    return {k: v for k, v in (params or {}).items() if str(k).lower() not in _SECRET_PARAMS}


def _redact(text):
    text = _SECRET_RE.sub(r"\1REDACTED", text)
    for var in ("FINNHUB_API_KEY", "CAPTURE_TOKEN"):
        val = (os.environ.get(var) or "").strip()
        if len(val) >= 6:
            text = text.replace(val, "REDACTED")
    return text


class _Recorder:
    def __init__(self, sym):
        self.sym = sym
        self.http, self.yf, self.finnhub, self.unrecorded = [], {}, [], []
        self._lock = threading.Lock()


class _RecordingSession:
    def __init__(self, real, rec):
        self._real, self._rec = real, rec

    def get(self, url, params=None, **kw):
        r = self._real.get(url, params=params, **kw)
        if not any(u in url for u in _SESSION_URLS) and url.rstrip("/").rsplit("/", 1)[-1].upper() == self._rec.sym:
            entry = {"url": url, "params": _clean(params), "status": r.status_code}
            try:
                entry["body_json"] = json.loads(r.text)
            except Exception:
                entry["body_text"] = r.text
            with self._rec._lock:
                self._rec.http.append(entry)
        return r

    def __getattr__(self, name):
        return getattr(self._real, name)


class _RecordingMapping:
    def __init__(self, real, on_get):
        self._real, self._on_get = real, on_get

    def get(self, key, default=None):
        try:
            v = self._real.get(key, default)
        except Exception:
            v = default
        self._on_get(key, v)
        return v

    def __getitem__(self, key):
        v = self._real[key]
        self._on_get(key, v)
        return v


class _RecordingTicker:
    def __init__(self, real_cls, rec, symbol, *a, **kw):
        self._real = real_cls(symbol, *a, **kw)
        self._rec = rec
        self._mine = str(symbol).upper() == rec.sym

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        val = getattr(self._real, name)
        if not self._mine:
            return val
        with self._rec._lock:
            if name in _FRAMES:
                self._rec.yf[name] = _df(val)
            elif name == "info":
                self._rec.yf["info"] = {k: _scalar(v) for k, v in (val or {}).items()}
            elif name == "fast_info":
                fast = self._rec.yf.setdefault("fast_info", {})
                return _RecordingMapping(val, lambda k, v: fast.__setitem__(k, _scalar(v)))
            else:
                self._rec.unrecorded.append(name)
        return val


def _capture(sym):
    import curl_cffi
    import data_fetcher
    import finnhub_fallback
    import pandas
    import yf_adapter
    import yfinance

    rec = _Recorder(sym)

    # En frío SOLO para este ticker (incluye el último-bueno-conocido, para que
    # la captura sea reproducible desde cero).
    yf_adapter._cache.pop(sym, None)
    yf_adapter._best_cache.pop(sym, None)
    finnhub_fallback._cache.pop(sym, None)
    for prefix in ("profile", "financials"):
        data_fetcher._data_cache._cache.pop(data_fetcher._data_cache._make_key(prefix, sym), None)

    orig_ensure = yf_adapter._ensure_session
    orig_ticker = yfinance.Ticker
    orig_get = finnhub_fallback._get

    def _rec_ensure_session():
        orig_ensure()
        if not isinstance(yf_adapter._session, _RecordingSession):
            yf_adapter._session = _RecordingSession(yf_adapter._session, rec)

    def _rec_finnhub_get(path, params):
        resp = orig_get(path, params)
        if str((params or {}).get("symbol", "")).upper() == sym:
            with rec._lock:
                rec.finnhub.append({"path": path, "params": _clean(params), "response": resp})
        return resp

    started = _dt.datetime.now(_dt.timezone.utc)
    yf_adapter._ensure_session = _rec_ensure_session
    yfinance.Ticker = lambda s, *a, **kw: _RecordingTicker(orig_ticker, rec, s, *a, **kw)
    finnhub_fallback._get = _rec_finnhub_get
    try:
        yf_adapter.get_ticker_info(sym)
        entry = yf_adapter._cache.get(sym)
        degraded = bool(entry[2]) if entry else None
    finally:
        yf_adapter._ensure_session = orig_ensure
        yfinance.Ticker = orig_ticker
        finnhub_fallback._get = orig_get
        if isinstance(yf_adapter._session, _RecordingSession):
            yf_adapter._session = yf_adapter._session._real

    return {
        "metadata": {
            "ticker": sym,
            "environment": "prod",
            "captured_at_utc": started.isoformat(timespec="seconds"),
            "server": {
                "render_service": os.environ.get("RENDER_SERVICE_NAME"),
                "git_commit": os.environ.get("RENDER_GIT_COMMIT"),
            },
            "versions": {
                "python": platform.python_version(),
                "yfinance": yfinance.__version__,
                "curl_cffi": curl_cffi.__version__,
                "pandas": pandas.__version__,
            },
            "finnhub": {
                "key_present": bool((os.environ.get("FINNHUB_API_KEY") or "").strip()),
                "participated": bool(rec.finnhub),
                "calls": len(rec.finnhub),
            },
            "yahoo": {
                "http_calls": len(rec.http),
                "degraded": degraded,
                "fallback_yfinance_used": "fast_info" in rec.yf,
                "yfinance_attributes": sorted(rec.yf.keys()),
            },
            "cold_capture": True,
            "unrecorded_yfinance_access": rec.unrecorded,
        },
        "yahoo_http": rec.http,
        "yfinance": rec.yf,
        "finnhub": rec.finnhub,
    }


@router.get("/api/_capture/{symbol}", include_in_schema=False)
def capture_inputs(symbol: str, x_capture_token: str = Header(default="")):
    expected = (os.environ.get("CAPTURE_TOKEN") or "").strip()
    if not expected or not x_capture_token or not hmac.compare_digest(x_capture_token.encode(), expected.encode()):
        raise HTTPException(status_code=404, detail="Not Found")
    sym = symbol.upper().strip()
    if not _SYMBOL_RE.match(sym):
        raise HTTPException(status_code=404, detail="Not Found")
    with _LOCK:
        payload = _capture(sym)
    body = _redact(json.dumps(payload, ensure_ascii=False, default=str))
    return Response(body, media_type="application/json", headers={"Cache-Control": "no-store"})
