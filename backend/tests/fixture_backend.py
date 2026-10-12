"""
Capa de inyección de datos para la línea base (etapa 2 del rediseño).

Congela las respuestas CRUDAS de las fuentes que consume `_compute_analysis`
y las sirve en modo test, sin red. No modifica ningún archivo de producción:
engancha por monkeypatch (con save/restore explícito) en estos puntos:

  H1  yf_adapter._ensure_session  -> instala una sesión falsa (replay) o
                                     envuelve la sesión curl_cffi real (record).
                                     Cubre la llamada v10/quoteSummary de
                                     _do_fetch y el refresco de crumb.
  H2  yfinance.Ticker             -> ticker falso (replay) o envoltorio que
                                     registra lo leído (record). Cubre
                                     _enrich_prior_year_data (income_stmt,
                                     balance_sheet, cashflow) y
                                     _fallback_yfinance (fast_info, info).
                                     yf_adapter hace `import yfinance as yf`
                                     DENTRO de las funciones, así que reemplazar
                                     el atributo del módulo basta.
  H3  finnhub_fallback._get       -> respuestas grabadas de Finnhub (replay) o
                                     envoltorio que las graba (record). El
                                     parámetro `token` NUNCA se guarda.
  H4  red                         -> en replay, socket.connect/create_connection
                                     lanzan error: cualquier llamada no grabada
                                     falla en vez de ir a internet. (curl_cffi no
                                     usa `socket`, pero H1 reemplaza su sesión.)

Además: reset_state() vacía las cachés en memoria del pipeline
(yf_adapter._cache/_best_cache, data_fetcher._data_cache,
finnhub_fallback._cache) para que cada corrida empiece en frío, y en replay
time.sleep es no-op (reintentos ante respuesta degradada).

Si un nombre enganchado cambia en producción, `check_seams()` falla en los
tests en vez de que la capa deje de interceptar en silencio.
"""
import contextlib
import copy
import datetime as _dt
import hashlib
import io
import json
import math
import os
import platform
import socket
import subprocess
import sys
import threading
import time

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(TESTS_DIR)
LIB_DIR = os.path.join(BACKEND_DIR, "lib")
REPO_DIR = os.path.dirname(BACKEND_DIR)
for _p in (BACKEND_DIR, LIB_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

FIXTURES_ROOT = os.path.join(TESTS_DIR, "fixtures")
GOLDEN_ROOT = os.path.join(TESTS_DIR, "golden")
TICKERS = ["NFLX", "JPM", "O", "FCX", "SNOW", "V"]
# Juegos de datos: "local" (captura en desarrollo) y "prod" (inputs que recibió
# el pipeline en Render). Cada uno tiene sus fixtures y sus golden.
ENVS = ("local", "prod")
DEFAULT_ENV = "local"


def fixtures_dir(env=DEFAULT_ENV):
    if env not in ENVS:
        raise ValueError(f"entorno desconocido: {env!r} (válidos: {ENVS})")
    return os.path.join(FIXTURES_ROOT, env)


def golden_dir(env=DEFAULT_ENV):
    if env not in ENVS:
        raise ValueError(f"entorno desconocido: {env!r} (válidos: {ENVS})")
    return os.path.join(GOLDEN_ROOT, env)


def available_envs():
    """Entornos con fixtures capturados para los 6 tickers."""
    return [e for e in ENVS
            if all(os.path.isfile(os.path.join(fixtures_dir(e), t, "metadata.json")) for t in TICKERS)]


# Compatibilidad: rutas por defecto = entorno local.
FIXTURES_DIR = fixtures_dir(DEFAULT_ENV)
GOLDEN_DIR = golden_dir(DEFAULT_ENV)

# URLs de arranque de sesión: no aportan datos al análisis, no se graban.
_SESSION_URLS = ("https://finance.yahoo.com", "/v1/test/getcrumb")
_FAKE_CRUMB = "FIXTURECRUMB"
_YF_FRAMES = ("income_stmt", "balance_sheet", "cashflow")
_SECRET_PARAMS = ("token", "crumb", "apikey", "api_key")


class FixtureMiss(RuntimeError):
    """El pipeline pidió algo que no está en los fixtures."""


# ═══════════════════════════ serialización ═══════════════════════════

def _scalar(v):
    """Valor de celda/JSON estable: NaN -> None, numpy -> Python."""
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


def df_to_obj(df):
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


def obj_to_df(obj):
    import numpy as np
    import pandas as pd
    if obj is None:
        return None
    cols = pd.to_datetime(obj["columns"]) if obj["columns_are_dates"] else obj["columns"]
    data = [[np.nan if v is None else v for v in row] for row in obj["data"]]
    df = pd.DataFrame(data, index=obj["index"], columns=cols)
    if all(t.startswith("float") for t in obj.get("dtypes", [])):
        df = df.astype("float64")
    return df


def _clean_params(params):
    return {k: v for k, v in (params or {}).items() if k.lower() not in _SECRET_PARAMS}


def _key(a, params):
    return a + "?" + json.dumps(_clean_params(params), sort_keys=True)


def _norm(o, sig):
    if o is None or isinstance(o, (bool, str)):
        return o
    if isinstance(o, int):
        return o
    if isinstance(o, float):
        if math.isnan(o):
            return "NaN"
        if math.isinf(o):
            return "Infinity" if o > 0 else "-Infinity"
        v = float(f"{o:.{sig}g}")
        return 0.0 if v == 0 else v
    if isinstance(o, dict):
        return {str(k): _norm(v, sig) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_norm(v, sig) for v in o]
    if hasattr(o, "item"):
        try:
            return _norm(o.item(), sig)
        except Exception:
            pass
    return str(o)


def stable_json(obj, sig=12):
    """Serialización estable para golden: claves ordenadas, floats a `sig`
    cifras significativas, NaN/Inf como texto, -0.0 -> 0.0."""
    return json.dumps(_norm(obj, sig), sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def raw_json(obj):
    """Serialización SIN redondeo (repr exacto de floats) para comprobar
    determinismo byte a byte."""
    return json.dumps(obj, sort_keys=True, default=repr, ensure_ascii=False, allow_nan=True)


def sha256(data):
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


# ═══════════════════════════ almacén de fixtures ═══════════════════════════

class FixtureStore:
    """Respuestas crudas por ticker. En record se llena; en replay se lee."""

    def __init__(self, base_dir=FIXTURES_DIR, mode="replay"):
        self.base_dir = base_dir
        self.mode = mode
        self.http = {}      # sym -> [ {url, params, status, body_json|body_text} ]
        self.yf = {}        # sym -> {attr: obj}
        self.finnhub = {}   # sym -> [ {path, params, response} ]
        self.meta = {}      # sym -> dict
        self.misses = []    # accesos no satisfechos en replay
        self.unrecorded = {}  # sym -> [attr] accesos a yfinance no soportados en record
        self._cursor = {}
        self._lock = threading.Lock()

    # ---- disco ----
    def dir_for(self, sym):
        return os.path.join(self.base_dir, sym.upper())

    def load(self, sym):
        sym = sym.upper()
        if sym in self.meta:
            return
        d = self.dir_for(sym)
        if not os.path.isdir(d):
            raise FixtureMiss(f"No hay fixtures para {sym} en {d}")
        with open(os.path.join(d, "metadata.json"), encoding="utf-8") as fh:
            self.meta[sym] = json.load(fh)
        with open(os.path.join(d, "yahoo_http.json"), encoding="utf-8") as fh:
            self.http[sym] = json.load(fh)
        with open(os.path.join(d, "yfinance.json"), encoding="utf-8") as fh:
            self.yf[sym] = json.load(fh)
        with open(os.path.join(d, "finnhub.json"), encoding="utf-8") as fh:
            self.finnhub[sym] = json.load(fh)

    def save(self, sym, meta):
        sym = sym.upper()
        d = self.dir_for(sym)
        os.makedirs(d, exist_ok=True)
        files = {
            "metadata.json": meta,
            "yahoo_http.json": self.http.get(sym, []),
            "yfinance.json": self.yf.get(sym, {}),
            "finnhub.json": self.finnhub.get(sym, []),
        }
        for name, payload in files.items():
            with open(os.path.join(d, name), "w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=1, sort_keys=True, ensure_ascii=False)
                fh.write("\n")

    # ---- record ----
    def record_http(self, sym, url, params, status, text):
        entry = {"url": url, "params": _clean_params(params), "status": status}
        try:
            entry["body_json"] = json.loads(text)
        except Exception:
            entry["body_text"] = text
        with self._lock:
            self.http.setdefault(sym, []).append(entry)

    def record_yf(self, sym, attr, obj):
        with self._lock:
            self.yf.setdefault(sym, {})[attr] = obj

    def record_fast(self, sym, key, value):
        with self._lock:
            self.yf.setdefault(sym, {}).setdefault("fast_info", {})[key] = _scalar(value)

    def record_finnhub(self, sym, path, params, response):
        with self._lock:
            self.finnhub.setdefault(sym, []).append(
                {"path": path, "params": _clean_params(params), "response": response})

    # ---- replay ----
    def _next(self, bucket, sym, key, match):
        """Siguiente respuesta grabada para `key` (en orden; repite la última)."""
        entries = [e for e in bucket.get(sym, []) if match(e) == key]
        if not entries:
            return None
        with self._lock:
            i = self._cursor.get((sym, key), 0)
            self._cursor[(sym, key)] = i + 1
        return entries[min(i, len(entries) - 1)]

    def replay_http(self, url, params):
        sym = _symbol_from_url(url, params)
        self.load(sym)
        e = self._next(self.http, sym, _key(url, params), lambda x: _key(x["url"], x["params"]))
        if e is None:
            self.misses.append(f"http {sym} {_key(url, params)}")
            raise FixtureMiss(f"HTTP no grabado: {url}")
        body = json.dumps(e["body_json"]) if "body_json" in e else e.get("body_text", "")
        return _FakeResponse(e["status"], body)

    def replay_yf(self, sym, attr):
        self.load(sym)
        data = self.yf.get(sym, {})
        if attr not in data:
            self.misses.append(f"yfinance {sym}.{attr}")
            raise FixtureMiss(f"yfinance {sym}.{attr} no grabado")
        obj = data[attr]
        if attr in _YF_FRAMES:
            return obj_to_df(obj)
        if attr == "fast_info":
            return dict(obj)
        return copy.deepcopy(obj)

    def replay_finnhub(self, sym, path, params):
        self.load(sym)
        e = self._next(self.finnhub, sym, _key(path, params), lambda x: _key(x["path"], x["params"]))
        if e is None:
            self.misses.append(f"finnhub {sym} {_key(path, params)}")
            return None
        return copy.deepcopy(e["response"])


def _symbol_from_url(url, params=None):
    # .../v10/finance/quoteSummary/{SYMBOL}  |  .../v1/finance/search?q={SYMBOL}
    if "/finance/search" in url:
        return str((params or {}).get("q", "")).upper()
    return url.rstrip("/").rsplit("/", 1)[-1].upper()


class _FakeResponse:
    def __init__(self, status_code, text):
        self.status_code = status_code
        self.text = text

    def json(self):
        return json.loads(self.text)


class _FixtureSession:
    def __init__(self, store):
        self._store = store

    def get(self, url, params=None, **_kw):
        if any(u in url for u in _SESSION_URLS):
            return _FakeResponse(200, _FAKE_CRUMB if "getcrumb" in url else "")
        return self._store.replay_http(url, params)


class _RecordingSession:
    def __init__(self, real, store):
        self._real = real
        self._store = store

    def get(self, url, params=None, **kw):
        r = self._real.get(url, params=params, **kw)
        if not any(u in url for u in _SESSION_URLS):
            self._store.record_http(_symbol_from_url(url, params), url, params, r.status_code, r.text)
        return r

    def __getattr__(self, name):
        return getattr(self._real, name)


class _FixtureTicker:
    def __init__(self, store, symbol, *_a, **_kw):
        self._store = store
        self._sym = str(symbol).upper()

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        return self._store.replay_yf(self._sym, name)


class _RecordingMapping:
    def __init__(self, real, on_get):
        self._real = real
        self._on_get = on_get

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
    def __init__(self, real_cls, store, symbol, *a, **kw):
        self._real = real_cls(symbol, *a, **kw)
        self._store = store
        self._sym = str(symbol).upper()

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        val = getattr(self._real, name)
        if name in _YF_FRAMES:
            self._store.record_yf(self._sym, name, df_to_obj(val))
        elif name == "info":
            self._store.record_yf(self._sym, "info", {k: _scalar(v) for k, v in (val or {}).items()})
        elif name == "fast_info":
            return _RecordingMapping(val, lambda k, v: self._store.record_fast(self._sym, k, v))
        else:
            self._store.unrecorded.setdefault(self._sym, []).append(name)
        return val


# ═══════════════════════════ enganche (patching) ═══════════════════════════

class _Patcher:
    def __init__(self):
        self._saved = []
        self._env = []

    def set(self, obj, name, value):
        self._saved.append((obj, name, getattr(obj, name)))
        setattr(obj, name, value)

    def env(self, key, value):
        self._env.append((key, os.environ.get(key)))
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value

    def undo(self):
        for obj, name, old in reversed(self._saved):
            setattr(obj, name, old)
        for key, old in reversed(self._env):
            if old is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old
        self._saved, self._env = [], []


SEAMS = {
    "yf_adapter": ("_ensure_session", "_session", "_crumb", "_cache", "_best_cache",
                   "_profile_idx", "_do_fetch", "_enrich_prior_year_data", "_fallback_yfinance"),
    "finnhub_fallback": ("_get", "_cache", "is_enabled"),
    "data_fetcher": ("_data_cache",),
}


def check_seams():
    """Lista de puntos de enganche que ya no existen en producción."""
    import importlib
    missing = []
    for mod, names in SEAMS.items():
        m = importlib.import_module(mod)
        missing += [f"{mod}.{n}" for n in names if not hasattr(m, n)]
    return missing


def reset_state():
    """Vacía cachés en memoria del pipeline: cada corrida empieza en frío."""
    import data_fetcher
    import finnhub_fallback
    import yf_adapter
    yf_adapter._cache.clear()
    yf_adapter._best_cache.clear()
    yf_adapter._session = None
    yf_adapter._crumb = None
    yf_adapter._profile_idx = 0
    data_fetcher._data_cache.clear()
    finnhub_fallback._cache.clear()


def _block_network(*_a, **_kw):
    raise RuntimeError("Red bloqueada en modo replay: el pipeline intentó una llamada no grabada")


@contextlib.contextmanager
def replay(base_dir=FIXTURES_DIR):
    """Modo test: el pipeline lee de los fixtures y no puede salir a la red."""
    import finnhub_fallback
    import yf_adapter
    import yfinance

    store = FixtureStore(base_dir)
    p = _Patcher()

    def _fake_ensure_session():
        if yf_adapter._session is None or yf_adapter._crumb is None:
            yf_adapter._session = _FixtureSession(store)
            yf_adapter._crumb = _FAKE_CRUMB

    def _fake_finnhub_get(path, params):
        sym = str((params or {}).get("symbol", "")).upper()
        return store.replay_finnhub(sym, path, params)

    p.set(yf_adapter, "_ensure_session", _fake_ensure_session)
    p.set(yfinance, "Ticker", lambda symbol, *a, **kw: _FixtureTicker(store, symbol, *a, **kw))
    p.set(finnhub_fallback, "_get", _fake_finnhub_get)
    p.set(time, "sleep", lambda *_a, **_kw: None)
    p.set(socket.socket, "connect", _block_network)
    p.set(socket.socket, "connect_ex", _block_network)
    p.set(socket, "create_connection", _block_network)
    p.env("FINNHUB_API_KEY", None)
    try:
        reset_state()
        yield store
    finally:
        reset_state()
        p.undo()


@contextlib.contextmanager
def record(base_dir=FIXTURES_DIR):
    """Captura: llamadas reales, registrando lo que consume el pipeline."""
    import finnhub_fallback
    import yf_adapter
    import yfinance

    store = FixtureStore(base_dir, mode="record")
    p = _Patcher()
    orig_ensure = yf_adapter._ensure_session
    orig_ticker = yfinance.Ticker
    orig_get = finnhub_fallback._get

    def _rec_ensure_session():
        orig_ensure()
        if not isinstance(yf_adapter._session, _RecordingSession):
            yf_adapter._session = _RecordingSession(yf_adapter._session, store)

    def _rec_finnhub_get(path, params):
        resp = orig_get(path, params)
        store.record_finnhub(str((params or {}).get("symbol", "")).upper(), path, params, resp)
        return resp

    p.set(yf_adapter, "_ensure_session", _rec_ensure_session)
    p.set(yfinance, "Ticker", lambda symbol, *a, **kw: _RecordingTicker(orig_ticker, store, symbol, *a, **kw))
    p.set(finnhub_fallback, "_get", _rec_finnhub_get)
    try:
        reset_state()
        yield store
    finally:
        reset_state()
        p.undo()


# ═══════════════════════════ ejecución ═══════════════════════════

def run_analysis(symbol, store):
    """_compute_analysis(symbol) en frío, dentro de un contexto replay/record.

    En replay, Finnhub solo se activa si el fixture lo grabó (clave ficticia:
    ninguna clave real entra al proceso de test)."""
    import main
    sym = symbol.upper()
    if store.mode == "replay":
        store.load(sym)
        if store.meta[sym].get("finnhub", {}).get("participated"):
            os.environ["FINNHUB_API_KEY"] = "fixture-replay"
        else:
            os.environ.pop("FINNHUB_API_KEY", None)
    reset_state()
    return copy.deepcopy(main._compute_analysis(sym))


def capture_date(meta):
    """Fecha local de captura: fija la fecha impresa en el PDF."""
    return _dt.datetime.fromisoformat(meta["captured_at_local"])


def _frozen_datetime(frozen):
    class _Frozen(_dt.datetime):
        @classmethod
        def now(cls, tz=None):
            return frozen
    return _Frozen


def _logo_path():
    # Misma búsqueda que main.download_pdf (main.py:899-905).
    for cand in (os.path.join(REPO_DIR, "frontend", "public", "logo.png"),
                 os.path.join(REPO_DIR, "frontend", "out", "logo.png")):
        if os.path.isfile(cand):
            return cand
    return None


def build_pdf_bytes(analysis, frozen_now, table_style_cls=None):
    """PDF como lo arma main.download_pdf, pero determinista: reportlab en
    modo `invariant` (sin fecha/ID variables) y datetime.now congelado a la
    fecha de captura. No altera producción: todo se restaura al salir."""
    import main
    import pdf_report
    from reportlab import rl_config

    p = _Patcher()
    p.set(rl_config, "invariant", 1)
    p.set(pdf_report, "datetime", _frozen_datetime(frozen_now))
    if table_style_cls is not None:
        p.set(pdf_report, "TableStyle", table_style_cls)
    try:
        buf = io.BytesIO()
        mapped = (analysis.get("sector_info") or {}).get("mapped_sector", "default")
        pdf_report.build_report(buf, analysis, sector_bench=main._get_sector_benchmarks(mapped),
                                logo_path=_logo_path())
        return buf.getvalue()
    finally:
        p.undo()


def pdf_text(pdf_bytes):
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(pdf_bytes))
    pages = []
    for i, page in enumerate(reader.pages, 1):
        txt = "\n".join(line.rstrip() for line in (page.extract_text() or "").splitlines())
        pages.append(f"===== página {i} =====\n{txt.strip()}\n")
    return "\n".join(pages)


def golden_paths(sym, base_dir=GOLDEN_DIR):
    return (os.path.join(base_dir, f"{sym.upper()}.json"),
            os.path.join(base_dir, f"{sym.upper()}.pdf.txt"))


def compute_outputs(symbols=None, fixtures_path=FIXTURES_DIR):
    """{sym: (analysis, pdf_bytes)} desde los fixtures de `fixtures_path`."""
    out = {}
    with replay(fixtures_path) as store:
        for sym in symbols or TICKERS:
            a = run_analysis(sym, store)
            pdf = build_pdf_bytes(a, capture_date(store.meta[sym.upper()]))
            out[sym.upper()] = (a, pdf)
        if store.misses:
            raise FixtureMiss("Accesos no grabados: " + "; ".join(store.misses))
    return out


def git_commit():
    try:
        return subprocess.check_output(["git", "-C", REPO_DIR, "rev-parse", "HEAD"],
                                       text=True).strip()
    except Exception:
        return None


def environment_info():
    import curl_cffi
    import pandas
    import yfinance
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "yfinance": yfinance.__version__,
        "curl_cffi": curl_cffi.__version__,
        "pandas": pandas.__version__,
    }


if __name__ == "__main__":
    # Huella determinista de todas las salidas (la usa test_determinism en
    # subprocesos con distintos PYTHONHASHSEED). Uso: fixture_backend.py [env] [TICKERS...]
    import logging
    logging.disable(logging.CRITICAL)
    args = sys.argv[1:]
    env = args.pop(0) if args and args[0] in ENVS else DEFAULT_ENV
    res = compute_outputs(args or None, fixtures_dir(env))
    print(json.dumps({s: [sha256(raw_json(a)), sha256(pdf)] for s, (a, pdf) in res.items()},
                     sort_keys=True))
