"""
Prueba hacia atrás · modo «fecha de corte» (docs/fiabilidad/PRUEBA_HACIA_ATRAS_2025_PREREGISTRO.md §1).

`install()` se llama ANTES de que corra cualquier capturador (tests/capture_*.py) y deja todas las fuentes del motor
como estaban el 5-nov-2025 tras el cierre de Nueva York:

  reloj      time_machine: datetime.now, date.today y time.time = 2025-11-05 18:00 (America/New_York), avanzando.
  EDGAR      sec_edgar.urllib_fetcher: submissions sin los filings presentados después; companyfacts sin los hechos
             con `filed` posterior; documentos de Archives solo de filings presentados ≤ corte; frames, bloqueado.
  yfinance   Ticker: estados sin las columnas presentadas después (fecha de presentación del 10-K/10-Q/20-F/40-F/6-K
             del mismo periodo; sin informe que case, fuera si el periodo cierra después de corte − 100 días);
             history con fechas explícitas que terminan en el corte, sin los splits ni los dividendos posteriores;
             fast_info recalculado; info vacío (como en Render).
  Yahoo HTTP fundamentals-timeseries con la misma regla; quoteSummary 401 (como en Render); otras rutas, bloqueadas.
  Finnhub    /stock/metric solo con series presentadas ≤ corte (lo actual, sin dato); /stock/earnings solo trimestres
             publicados ≤ corte (8-K 2.02 o informe periódico); /stock/financials-reported por filedDate; calendario
             sin estimaciones ni cifras posteriores; noticias vacías; rutas desconocidas, sin dato.

Todo lo que se filtra o se bloquea queda en el registro (HACIA_ATRAS_LOG, una línea JSON por evento). Las consultas
auxiliares a EDGAR (mapa de presentaciones) usan la caché de disco HACIA_ATRAS_CACHE.
"""
import datetime as dt
import json
import math
import os
import sys
import threading
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(os.path.dirname(HERE))
for _p in (BACKEND, os.path.join(BACKEND, "lib"), os.path.join(BACKEND, "tests")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

NY = ZoneInfo("America/New_York")
# Segundo corte (pre-registro de 2024): la fecha se elige con HACIA_ATRAS_CORTE (AAAA-MM-DD); por defecto, 2025-11-05.
CUTOFF = dt.date.fromisoformat(os.environ.get("HACIA_ATRAS_CORTE") or "2025-11-05")
CLOCK = dt.datetime(CUTOFF.year, CUTOFF.month, CUTOFF.day, 18, 0, tzinfo=NY)
CUT = CUTOFF.isoformat()
FALLBACK_LAG_DAYS = 100
PERIODIC = ("10-K", "10-Q", "20-F", "40-F", "10-KT", "10-QT", "6-K", "20-F/A", "10-K/A", "10-Q/A", "40-F/A")
EVIDENCE = f"/Users/joseestebanroa/Downloads/Finanzer/archivo-historico/evidencias-de-pruebas/hacia_atras_{CUT}"
CACHE = os.environ.get("HACIA_ATRAS_CACHE") or os.path.join(EVIDENCE, "cache_corte")
LOG = os.environ.get("HACIA_ATRAS_LOG") or os.path.join(EVIDENCE, "registro_corte.jsonl")
_lock = threading.Lock()
_ORIG = {}


def log(kind, **kw):
    rec = {"kind": kind, **kw}
    with _lock:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")


def _d(x):
    """Fecha de un valor (str 'YYYY-MM-DD…', date, datetime, Timestamp) o None."""
    if x is None:
        return None
    if isinstance(x, dt.datetime):
        return x.date()
    if isinstance(x, dt.date):
        return x
    if hasattr(x, "date") and callable(x.date):
        try:
            return x.date()
        except Exception:
            pass
    try:
        return dt.date.fromisoformat(str(x)[:10])
    except ValueError:
        return None


# ═══════════════════════════ reloj ═══════════════════════════

def freeze_clock():
    import time_machine
    trav = time_machine.travel(CLOCK, tick=True)
    trav.start()
    return trav


# ═══════════════════════════ EDGAR ═══════════════════════════

def _raw_sec(url):
    """Descarga real (sin filtro) con la caché de disco; solo para el mapa de presentaciones."""
    import hashlib
    import sec_edgar
    key = hashlib.sha256(url.encode()).hexdigest()[:24]
    path = os.path.join(CACHE, "sec", key + ".json")
    if os.path.isfile(path):
        with open(path, "rb") as fh:
            return fh.read()
    body, code = _ORIG["urllib_fetcher"](url, 60.0)
    if code != 200 or body is None:
        return None
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path + ".part", "wb") as fh:
        fh.write(body)
    os.replace(path + ".part", path)
    return body


_tickers = None
_filings = {}


def cik_of(symbol):
    global _tickers
    import sec_edgar
    if _tickers is None:
        body = _raw_sec(sec_edgar.TICKERS_URL)
        _tickers = {}
        for v in (json.loads(body) if body else {}).values():
            _tickers.setdefault(str(v["ticker"]).upper().replace(".", "-"), int(v["cik_str"]))
    return _tickers.get(str(symbol).upper().replace(".", "-"))


def _columns(block):
    keys = ("accessionNumber", "filingDate", "reportDate", "form", "items")
    n = len(block.get("filingDate") or [])
    return [{k: (block.get(k) or [None] * n)[i] for k in keys} for i in range(n)]


def filings_of_cik(cik):
    """Todos los filings del CIK (recent + páginas antiguas), sin filtrar."""
    if cik in _filings:
        return _filings[cik]
    body = _raw_sec(f"https://data.sec.gov/submissions/CIK{int(cik):010d}.json")
    out = []
    if body:
        sub = json.loads(body)
        out = _columns(sub.get("filings", {}).get("recent", {}))
        for f in sub.get("filings", {}).get("files", []) or []:
            page = _raw_sec(f"https://data.sec.gov/submissions/{f['name']}")
            if page:
                out += _columns(json.loads(page))
    _filings[cik] = out
    return out


def filings_of(symbol):
    cik = cik_of(symbol)
    return filings_of_cik(cik) if cik else []


def known_by_cut(symbol, period_end, kind="estado"):
    """¿Se conocía el periodo que cierra en `period_end` el día del corte?
    estado: fecha de presentación del informe periódico del periodo (±10 días; 52/53 semanas).
    publicado: la primera de (8-K con el ítem 2.02 en los 120 días siguientes al cierre, informe periódico).
    Sin informe que case: fuera si el periodo cierra después de corte − FALLBACK_LAG_DAYS."""
    pe = _d(period_end)
    if pe is None:
        return False
    if pe > CUTOFF:
        return False
    fl = filings_of(symbol)
    dates = [_d(f["filingDate"]) for f in fl
             if f.get("form") in PERIODIC and f.get("reportDate")
             and abs((_d(f["reportDate"]) - pe).days) <= 10 and _d(f["filingDate"]) >= pe]
    if kind == "publicado":
        dates += [_d(f["filingDate"]) for f in fl
                  if f.get("form") in ("8-K", "6-K") and "2.02" in str(f.get("items") or "")
                  and 0 <= (_d(f["filingDate"]) - pe).days <= 120]
    if dates:
        return min(dates) <= CUTOFF
    return (CUTOFF - pe).days >= FALLBACK_LAG_DAYS


def _filter_submissions(obj):
    if "filings" in obj:
        r = obj["filings"].get("recent") or {}
        keep = [i for i, d in enumerate(r.get("filingDate") or []) if d <= CUT]
        obj["filings"]["recent"] = {k: [v[i] for i in keep] if isinstance(v, list) else v for k, v in r.items()}
        files = obj["filings"].get("files") or []
        obj["filings"]["files"] = [f for f in files if str(f.get("filingFrom", ""))[:10] <= CUT]
        return obj
    if "filingDate" in obj:                 # página antigua (columnar)
        keep = [i for i, d in enumerate(obj.get("filingDate") or []) if d <= CUT]
        return {k: [v[i] for i in keep] if isinstance(v, list) else v for k, v in obj.items()}
    return obj


def _filter_facts(obj):
    dropped = 0
    for cs in (obj.get("facts") or {}).values():
        for node in cs.values():
            units = {}
            for u, fs in (node.get("units") or {}).items():
                keep = [f for f in fs if str(f.get("filed", "")) <= CUT]
                dropped += len(fs) - len(keep)
                units[u] = keep
            node["units"] = units
    return obj, dropped


def edgar_fetcher(url, timeout):
    """sec_edgar.urllib_fetcher al corte."""
    import sec_edgar
    if "/api/xbrl/frames/" in url:
        log("edgar_bloqueado", url=url, motivo="frames (todo el universo, sin fecha de presentación)")
        return None, 404
    if "/Archives/edgar/data/" in url:
        parts = url.split("/Archives/edgar/data/", 1)[1].split("/")
        cik, acc = int(parts[0]), parts[1]
        accn = f"{acc[:10]}-{acc[10:12]}-{acc[12:]}" if "-" not in acc else acc
        f = next((f for f in filings_of_cik(cik) if f["accessionNumber"] == accn), None)
        if f is None or f["filingDate"] > CUT:
            log("edgar_bloqueado", url=url, motivo="documento de un filing posterior al corte o desconocido",
                filed=f and f["filingDate"])
            return None, 404
        return _ORIG["urllib_fetcher"](url, timeout)
    body, code = _ORIG["urllib_fetcher"](url, timeout)
    if code != 200 or body is None or url == sec_edgar.TICKERS_URL:
        return body, code
    if "/api/xbrl/companyfacts/" in url:
        obj, n = _filter_facts(json.loads(body))
        log("edgar_hechos", url=url, quitados=n)
        return json.dumps(obj).encode(), 200
    if "/submissions/" in url:
        return json.dumps(_filter_submissions(json.loads(body))).encode(), 200
    log("edgar_bloqueado", url=url, motivo="ruta sin regla de corte")
    return None, 404


# ═══════════════════════════ yfinance ═══════════════════════════

_FRAMES = ("income_stmt", "balance_sheet", "cashflow", "quarterly_income_stmt", "quarterly_balance_sheet",
           "quarterly_cashflow", "financials", "quarterly_financials", "balancesheet", "quarterly_balancesheet",
           "get_income_stmt", "get_balance_sheet", "get_cash_flow")
_PERIODS = {"1d": dict(days=1), "5d": dict(days=7), "1mo": dict(months=1), "3mo": dict(months=3),
            "6mo": dict(months=6), "1y": dict(years=1), "2y": dict(years=2), "5y": dict(years=5),
            "10y": dict(years=10)}


def _span(period):
    """'7y', '18mo', '10d', '3wk' → argumentos de _minus; otro texto → None."""
    import re
    m = re.fullmatch(r"(\d+)(y|mo|wk|d)", str(period or ""))
    if not m:
        return None
    n, u = int(m.group(1)), m.group(2)
    return {"y": dict(years=n), "mo": dict(months=n), "wk": dict(days=7 * n), "d": dict(days=n)}[u]


def _minus(d, months=0, years=0, days=0):
    m = d.month - 1 - months - 12 * years
    y, m = d.year + m // 12, m % 12 + 1
    import calendar
    day = min(d.day, calendar.monthrange(y, m)[1])
    return dt.date(y, m, day) - dt.timedelta(days=days)


def filter_frame(symbol, df, attr):
    if df is None or not hasattr(df, "columns") or len(df.columns) == 0:
        return df
    keep = [c for c in df.columns if known_by_cut(symbol, c)]
    gone = [str(c)[:10] for c in df.columns if c not in keep]
    if gone:
        log("yf_columnas_quitadas", symbol=symbol, attr=attr, periodos=gone)
    return df[keep]


_split_cache = {}


def _post_cut_split_factor(raw_ticker):
    """Producto de los splits POSTERIORES al corte. Yahoo da los precios de antes ya divididos por ellos; con el reloj
    congelado yfinance no los ve (`.splits` llega hasta «hoy» = el corte), así que se piden con el reloj real."""
    sym = str(getattr(raw_ticker, "ticker", "")).upper()
    if sym in _split_cache:
        return _split_cache[sym]
    from time_machine import escape_hatch
    real_end = escape_hatch.datetime.datetime.now().date() + dt.timedelta(days=2)
    f = 1.0
    try:
        h = raw_ticker.history(start=(CUTOFF + dt.timedelta(days=1)).isoformat(), end=real_end.isoformat(),
                               actions=True, auto_adjust=False)
        s = h["Stock Splits"] if h is not None and "Stock Splits" in h else None
        for d, r in (s.items() if s is not None else []):
            if r and r > 0 and _d(d) and _d(d) > CUTOFF:
                f *= float(r)
    except Exception as e:
        log("splits_posteriores_sin_dato", symbol=sym, error=repr(e)[:200])
    _split_cache[sym] = f
    return f


def asof_history(raw_ticker, symbol, period=None, interval="1d", start=None, end=None, auto_adjust=True, **kw):
    import pandas as pd
    if start is None:
        if period in (None, "max"):
            start = None
        elif period == "ytd":
            start = dt.date(CUTOFF.year, 1, 1)
        elif period in _PERIODS:
            start = _minus(CUTOFF, **_PERIODS[period])
        elif _span(period):
            start = _minus(CUTOFF, **_span(period))
        else:
            log("yf_periodo_desconocido", symbol=symbol, period=period)
            start = _minus(CUTOFF, years=2)
    endd = min(_d(end) or (CUTOFF + dt.timedelta(days=1)), CUTOFF + dt.timedelta(days=1))
    kw.pop("period", None)
    args = dict(interval=interval, end=endd.isoformat(), auto_adjust=False, **kw)
    if start is not None:
        args["start"] = _d(start).isoformat()
    else:
        args["period"] = "max"
    df = raw_ticker.history(**args)
    if df is None or len(df) == 0:
        return df
    df = df[[(_d(i) or CUTOFF) <= CUTOFF for i in df.index]].copy()
    f = _post_cut_split_factor(raw_ticker)
    if f != 1.0:
        for c in ("Open", "High", "Low", "Close", "Adj Close", "Dividends"):
            if c in df:
                df[c] = df[c] * f
        if "Volume" in df:
            df["Volume"] = df["Volume"] / f
        log("yf_split_posterior_deshecho", symbol=symbol, factor=f)
    if "Adj Close" in df and len(df) and df["Adj Close"].iloc[-1]:
        k = float(df["Close"].iloc[-1]) / float(df["Adj Close"].iloc[-1])
        df["Adj Close"] = df["Adj Close"] * k          # sin el ajuste por dividendos posteriores al corte
    if auto_adjust and "Adj Close" in df:
        ratio = df["Adj Close"] / df["Close"]
        for c in ("Open", "High", "Low"):
            if c in df:
                df[c] = df[c] * ratio
        df["Close"] = df["Adj Close"]
        df = df.drop(columns=["Adj Close"])
    return df


class _FastInfo(dict):
    def __getattr__(self, k):
        try:
            return self[_CAMEL.get(k, k)]
        except KeyError:
            raise AttributeError(k)


_CAMEL = {"last_price": "lastPrice", "market_cap": "marketCap", "year_high": "yearHigh", "year_low": "yearLow",
          "quote_type": "quoteType"}


def _dei_shares(symbol, asof=True):
    cik = cik_of(symbol)
    if not cik:
        return None
    body = _raw_sec(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{int(cik):010d}.json")
    if not body:
        return None
    node = ((json.loads(body).get("facts") or {}).get("dei") or {}).get("EntityCommonStockSharesOutstanding") or {}
    fs = [f for f in (node.get("units") or {}).get("shares", []) if not asof or str(f.get("filed")) <= CUT]
    if not fs:
        return None
    last = max(str(f.get("end")) for f in fs)
    by_filed = {}
    for f in fs:
        if str(f.get("end")) == last:
            by_filed.setdefault(f.get("accn"), []).append(float(f["val"]))
    vals = max(by_filed.values(), key=lambda v: (len(v), sum(v)))
    return sum(vals)


def asof_fast_info(raw_ticker, symbol):
    real = raw_ticker.fast_info
    out = _FastInfo()
    for k in ("currency", "exchange", "quoteType"):
        try:
            out[k] = real[k]
        except Exception:
            out[k] = None
    h = asof_history(raw_ticker, symbol, period="1y", auto_adjust=False)
    if h is None or len(h) == 0:
        log("fast_info_sin_serie", symbol=symbol)
        out.update(lastPrice=None, yearHigh=None, yearLow=None, shares=None, marketCap=None)
        return out
    out["lastPrice"] = float(h["Close"].iloc[-1])
    out["yearHigh"], out["yearLow"] = float(h["High"].max()), float(h["Low"].min())
    # Con el reloj congelado, yfinance pide la serie de acciones de Yahoo hasta «hoy» = el corte: son las de esa fecha
    # (comprobado: AAPL, NFLX antes del split, JPM = portada de EDGAR al corte; TSM en ADR). Si Yahoo no da o da menos
    # del 10 % de la portada de EDGAR al corte (BNY: 24 M frente a 697 M tras el cambio de símbolo), la portada.
    try:
        y_sh = real["shares"]
    except Exception:
        y_sh = None
    d_cut = _dei_shares(symbol, True)
    # un ADR con factor oficial (config/adr.toml): Yahoo da acciones equivalentes al ADR y EDGAR las ordinarias (TM,
    # factor 10): no se comparan. Una portada con menos de un millón de acciones no es la de la empresa cotizada (SKYD:
    # 1.000 acciones de la entidad recién creada): no sirve.
    try:
        import currency
        adr = bool(currency.official_factor(symbol))
    except Exception:
        adr = False
    if d_cut is not None and d_cut < 1e6:
        log("acciones_edgar_descartadas", symbol=symbol, edgar=d_cut)
        d_cut = None
    if y_sh and (adr or not (d_cut and float(y_sh) < 0.1 * d_cut)):
        sh, how = float(y_sh), "Yahoo con el reloj en el corte"
        if d_cut and not 0.5 <= float(y_sh) / d_cut <= 2:
            log("acciones_discrepan", symbol=symbol, yahoo=y_sh, edgar=d_cut)
    elif d_cut:
        sh, how = d_cut, "portada de EDGAR al corte"
        log("acciones_de_edgar", symbol=symbol, yahoo=y_sh, edgar=d_cut)
    else:
        sh, how = None, "sin dato"
        log("acciones_sin_dato", symbol=symbol)
    out["shares"] = int(round(sh)) if sh else None
    out["marketCap"] = out["lastPrice"] * sh if sh else None
    log("fast_info", symbol=symbol, price=out["lastPrice"], shares=out["shares"], como=how)
    return out


class AsOfTicker:
    def __init__(self, symbol, *a, **kw):
        self._t = _ORIG["Ticker"](symbol, *a, **kw)
        self._sym = str(symbol).upper()
        self.ticker = getattr(self._t, "ticker", symbol)

    def history(self, *a, **kw):
        if a:
            kw["period"] = a[0]
        return asof_history(self._t, self._sym, **kw)

    def __getattr__(self, name):
        if name in _FRAMES:
            v = getattr(self._t, name)
            v = v() if callable(v) else v
            return filter_frame(self._sym, v, name)
        if name == "fast_info":
            return asof_fast_info(self._t, self._sym)
        if name == "info":
            log("yf_info_vacio", symbol=self._sym)
            return {}
        if name in ("dividends", "splits", "actions"):
            s = getattr(self._t, name)
            return s[[(_d(i) or CUTOFF) <= CUTOFF for i in s.index]] if s is not None and len(s) else s
        log("yf_atributo_bloqueado", symbol=self._sym, attr=name)
        raise AttributeError(f"{name}: sin regla de corte (prueba hacia atrás)")


# ═══════════════════════════ Yahoo HTTP ═══════════════════════════

class _Resp:
    def __init__(self, status_code, text):
        self.status_code, self.text = status_code, text
        self.content = text.encode()
        self.ok = status_code == 200
        self.headers = {}

    def json(self):
        return json.loads(self.text)


_QS_401 = '{"finance":{"result":null,"error":{"code":"Unauthorized","description":"Invalid Crumb"}}}'


class AsOfSession:
    def __init__(self, real):
        self._real = real

    def __getattr__(self, n):
        return getattr(self._real, n)

    def get(self, url, params=None, **kw):
        if "finance.yahoo.com" in url and ("getcrumb" in url or url.rstrip("/").endswith("finance.yahoo.com")):
            return self._real.get(url, params=params, **kw)
        if "/v1/finance/search" in url:
            return self._real.get(url, params=params, **kw)
        if "/v10/finance/quoteSummary/" in url:
            return _Resp(401, _QS_401)
        if "/fundamentals-timeseries/" in url:
            p = dict(params or {})
            p["period2"] = str(int(CLOCK.timestamp()))
            r = self._real.get(url, params=p, **kw)
            if r.status_code != 200:
                return r
            sym = url.rstrip("/").rsplit("/", 1)[-1]
            obj = r.json()
            for res in ((obj.get("timeseries") or {}).get("result") or []):
                for k, v in list(res.items()):
                    if k in ("meta", "timestamp") or not isinstance(v, list):
                        continue
                    keep = [e for e in v if e is None or known_by_cut(sym, e.get("asOfDate"))]
                    if len(keep) != len(v):
                        log("yf_timeseries_quitados", symbol=sym, tipo=k, n=len(v) - len(keep))
                    res[k] = keep
                    if "timestamp" in res:
                        res["timestamp"] = [int(dt.datetime.combine(_d(e["asOfDate"]), dt.time(),
                                                                   tzinfo=dt.timezone.utc).timestamp())
                                            for e in keep if e]
            # nota: con `params` cambiados el recorder graba los originales (period2 de hoy): el replay casa igual
            return _Resp(200, json.dumps(obj))
        log("yahoo_bloqueado", url=url)
        return _Resp(404, '{"error":"bloqueado por la prueba hacia atrás"}')


# ═══════════════════════════ Finnhub ═══════════════════════════

_SUFFIX = (("Annual", "annual", ""), ("Quarterly", "quarterly", ""), ("TTM", "quarterly", "TTM"))


def _latest(series, kind, name):
    arr = ((series.get(kind) or {}).get(name)) or []
    vals = sorted((e for e in arr if e.get("v") is not None), key=lambda e: e.get("period", ""), reverse=True)
    return vals[0]["v"] if vals else None


def finnhub_metric(sym, data):
    series = data.get("series") or {}
    cut = {}
    for kind, block in series.items():
        cut[kind] = {}
        for name, arr in (block or {}).items():
            cut[kind][name] = [e for e in arr or [] if known_by_cut(sym, e.get("period"))]
    metric = {}
    for k in (data.get("metric") or {}):
        v = None
        for suf, kind, extra in _SUFFIX:
            if k.endswith(suf):
                base = k[: -len(suf)]
                v = _latest(cut, kind, base + extra)
                if v is None and extra:
                    v = _latest(cut, kind, base)
                break
        metric[k] = v
    log("finnhub_metric", symbol=sym, con_valor=sorted(k for k, v in metric.items() if v is not None))
    return {"metric": metric, "metricType": data.get("metricType"), "series": cut, "symbol": data.get("symbol")}


def finnhub_get(path, params):
    sym = str((params or {}).get("symbol", "")).upper().replace(".", "-")
    if path == "/company-news":
        log("finnhub_noticias_vacias", symbol=sym)
        return []
    if path == "/calendar/earnings":
        data = _ORIG["finnhub_get"](path, params)
        if isinstance(data, dict):
            for e in data.get("earningsCalendar") or []:
                if str(e.get("date", "")) > CUT:
                    for k in ("epsEstimate", "revenueEstimate", "epsActual", "revenueActual"):
                        e[k] = None
        return data
    if path == "/stock/metric":
        data = _ORIG["finnhub_get"](path, params)
        return finnhub_metric(sym, data) if isinstance(data, dict) else data
    if path == "/stock/earnings":
        data = _ORIG["finnhub_get"](path, params)
        if isinstance(data, list):
            data = [e for e in data if known_by_cut(sym, e.get("period"), "publicado")]
        return data
    if path == "/stock/financials-reported":
        data = _ORIG["finnhub_get"](path, params)
        if isinstance(data, dict):
            data["data"] = [f for f in data.get("data") or [] if str(f.get("filedDate", ""))[:10] <= CUT]
        return data
    log("finnhub_bloqueado", path=path, symbol=sym)
    return None


# ═══════════════════════════ instalación ═══════════════════════════

def install(clock=True, sources=True):
    trav = freeze_clock() if clock else None
    if not sources:
        return trav
    import finnhub_fallback
    import sec_edgar
    import yf_adapter
    import yfinance
    _ORIG["urllib_fetcher"] = sec_edgar.urllib_fetcher
    _ORIG["Ticker"] = yfinance.Ticker
    _ORIG["finnhub_get"] = finnhub_fallback._get
    _ORIG["ensure"] = yf_adapter._ensure_session
    # Dos objetos distintos a propósito: con FETCHER «is» urllib_fetcher, sec_edgar._get_to_file descarga en streaming
    # con urllib directamente (sin pasar por ninguno de los dos); así siempre pasa por _get y por el filtro.
    sec_edgar.urllib_fetcher = lambda url, timeout: edgar_fetcher(url, timeout)
    sec_edgar.FETCHER = edgar_fetcher
    yfinance.Ticker = AsOfTicker
    finnhub_fallback._get = finnhub_get

    def _ensure():
        _ORIG["ensure"]()
        if yf_adapter._session is not None and not isinstance(yf_adapter._session, AsOfSession):
            yf_adapter._session = AsOfSession(yf_adapter._session)
    yf_adapter._ensure_session = _ensure
    # El companyfacts grabado se reduce a los hechos que acaban desde FACTS_SINCE (2019-01-01, pensado para hoy). Al
    # corte, el motor mira los mismos años hacia atrás desde la fecha de corte: un ejercicio antes por cada año de
    # adelanto (2024: la recurrencia de cargos y las ganancias de cartera leen 2018). Con 2025-11-05 sigue en 2019.
    import f2b_fixtures
    f2b_fixtures.FACTS_SINCE = f"{CUTOFF.year - 6}-01-01"
    import price_history
    if getattr(price_history.FETCHER, "__name__", "") == "yfinance_fetcher":
        pass                                    # llama a yf.Ticker dentro: ya pasa por AsOfTicker
    log("instalado", clock=str(CLOCK), pid=os.getpid(), argv=sys.argv)
    return trav
