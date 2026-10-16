"""
SEC EDGAR en el camino del análisis (fase 2b; D2: verificación y respaldo, nunca fuente principal en la 2b).

Lo que da hoy (T3): el emisor (ticker → CIK, `company_tickers.json`) y su lista de filings (`submissions`), con la que
se detecta un resultado publicado y aún no incorporado al análisis (F2_PRECEDENCIA §1.1). T4 añade los hechos XBRL
(`companyfacts` y las instancias que aún no trae) para el respaldo y D7.

Reglas de la SEC: `User-Agent` con nombre y correo de contacto y ≤ 10 peticiones por segundo. El User-Agent llega SOLO
por la variable de entorno `data.edgar.user_agent_env` (en Render la pone el usuario en el panel; aquí nunca se
escribe ni se registra). Sin ella el cliente se desactiva y lo declara.

Nunca bloquea el análisis: todo lo de EDGAR de un análisis corre en un hilo (`start`), con un presupuesto de tiempo
(`budget_s`); si se agota o la SEC falla, el análisis sigue sin EDGAR y lo dice (`status`, `reason`). Cachés por
proceso: company_tickers un día, submissions unas horas.

El descargador es inyectable (`FETCHER`): en producción, urllib; en los tests, el replay de los fixtures.
"""
import datetime as _dt
import gzip
import json
import logging
import os
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, List, Optional, Tuple

from settings import cfg

logger = logging.getLogger(__name__)

TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
PERIODIC_FORMS = {"10-Q", "10-Q/A", "10-K", "10-K/A", "10-KT", "20-F", "20-F/A", "40-F", "40-F/A", "6-K", "6-K/A"}
ANNUAL_OR_QUARTERLY = PERIODIC_FORMS - {"6-K", "6-K/A"}

_cache: Dict[str, Tuple[float, Any]] = {}
_lock = threading.Lock()
_rate_lock = threading.Lock()
_last = [0.0]
_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="edgar")


class Unavailable(RuntimeError):
    """EDGAR no disponible para este análisis (sin User-Agent, presupuesto agotado o la SEC falla)."""


def user_agent() -> Optional[str]:
    ua = (os.environ.get(cfg("data.edgar.user_agent_env")) or "").strip()
    return ua if "@" in ua else None


def status() -> Dict[str, Any]:
    if user_agent():
        return {"enabled": True, "reason": None}
    return {"enabled": False,
            "reason": (f"sin User-Agent de la SEC (variable {cfg('data.edgar.user_agent_env')}): verificación oficial "
                       "no disponible")}


def urllib_fetcher(url: str, timeout: float) -> Tuple[Optional[bytes], int]:
    """Descarga real con el User-Agent de la SEC (nunca se registra)."""
    req = urllib.request.Request(url, headers={"User-Agent": user_agent() or "", "Accept-Encoding": "gzip"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
            body = gzip.decompress(raw) if r.headers.get("Content-Encoding") == "gzip" else raw
            return body, r.status
    except urllib.error.HTTPError as e:
        return None, e.code


FETCHER: Callable[[str, float], Tuple[Optional[bytes], int]] = urllib_fetcher


class Budget:
    """Tiempo de EDGAR que le queda a un análisis."""

    def __init__(self, seconds: Optional[float] = None):
        self.deadline = time.monotonic() + (cfg("data.edgar.budget_s") if seconds is None else seconds)

    def left(self) -> float:
        return self.deadline - time.monotonic()


def _get_json(url: str, budget: Budget) -> Any:
    E = cfg("data.edgar")
    if not user_agent():
        raise Unavailable(status()["reason"])
    with _rate_lock:
        wait = _last[0] + E["min_interval_s"] - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        _last[0] = time.monotonic()
    left = budget.left()
    if left <= 0:
        raise Unavailable(f"presupuesto de EDGAR agotado ({E['budget_s']:g} s)")
    try:
        body, code = FETCHER(url, min(E["timeout_s"], left))
    except Exception as e:  # red, tiempo de espera, TLS…: se registra el tipo
        raise Unavailable(f"EDGAR no respondió ({type(e).__name__})") from e
    if body is None or code != 200:
        raise Unavailable(f"EDGAR respondió {code}")
    return json.loads(body)


def _cached(key: str, ttl: float, make: Callable[[], Any]) -> Any:
    now = time.time()
    with _lock:
        ent = _cache.get(key)
        if ent and now - ent[0] < ttl:
            return ent[1]
    val = make()
    with _lock:
        _cache[key] = (now, val)
    return val


def cik_for(ticker: str, budget: Budget) -> Optional[Dict[str, Any]]:
    """{cik, title} del ticker en company_tickers.json de la SEC, o None si no está registrado."""
    E = cfg("data.edgar")
    table = _cached("tickers", E["tickers_ttl_s"], lambda: {
        str(v["ticker"]).upper(): {"cik": int(v["cik_str"]), "title": v.get("title")}
        for v in (_get_json(TICKERS_URL, budget) or {}).values()})
    return table.get(ticker.upper().replace(".", "-"))


def filings(cik: int, budget: Budget) -> List[Dict[str, Any]]:
    """Filings recientes del CIK (desde `since`), del más reciente al más antiguo."""
    E = cfg("data.edgar")

    def make():
        r = (_get_json(SUBMISSIONS_URL.format(cik=cik), budget).get("filings") or {}).get("recent") or {}
        out = []
        for i, form in enumerate(r.get("form") or []):
            fd = r["filingDate"][i]
            if fd < E["since"]:
                continue
            out.append({"form": form, "filingDate": fd, "reportDate": (r.get("reportDate") or [""] * (i + 1))[i] or None,
                        "items": (r.get("items") or [""] * (i + 1))[i] or "",
                        "accessionNumber": r["accessionNumber"][i],
                        "isXBRL": bool((r.get("isXBRL") or [0] * (i + 1))[i])})
        return sorted(out, key=lambda f: (f["filingDate"], f["accessionNumber"]), reverse=True)
    return _cached(f"sub:{cik}", E["submissions_ttl_s"], make)


def fetch(ticker: str) -> Dict[str, Any]:
    """Todo lo de EDGAR de un análisis, dentro del presupuesto: {status, reason, cik, title, filings, latency_s}."""
    t0 = time.monotonic()
    st = status()
    if not st["enabled"]:
        return {"status": "desactivado", "reason": st["reason"], "cik": None, "filings": None}
    budget = Budget()
    try:
        ent = cik_for(ticker, budget)
        if ent is None:
            return {"status": "sin_cik", "reason": "el ticker no figura en la lista de emisores de la SEC",
                    "cik": None, "filings": None, "latency_s": time.monotonic() - t0}
        fl = filings(ent["cik"], budget)
        lat = time.monotonic() - t0
        logger.info(f"[EDGAR] {ticker}: CIK {ent['cik']}, {len(fl)} filings en {lat:.2f}s")
        return {"status": "ok", "reason": None, "cik": ent["cik"], "title": ent.get("title"), "filings": fl,
                "latency_s": lat}
    except Unavailable as e:
        return {"status": "no_disponible", "reason": str(e), "cik": None, "filings": None,
                "latency_s": time.monotonic() - t0}
    except Exception as e:  # una respuesta inesperada de la SEC no rompe el análisis
        logger.warning(f"[EDGAR] {ticker}: {type(e).__name__}: {e}")
        return {"status": "no_disponible", "reason": f"respuesta inesperada de EDGAR ({type(e).__name__})",
                "cik": None, "filings": None, "latency_s": time.monotonic() - t0}


def start(ticker: str):
    return _pool.submit(fetch, ticker)


def collect(future) -> Dict[str, Any]:
    if future is None:
        return {"status": "no_disponible", "reason": "no se lanzó la consulta", "cik": None, "filings": None}
    try:
        return future.result(timeout=cfg("data.edgar.budget_s") + cfg("data.edgar.timeout_s"))
    except Exception as e:  # tiempo agotado u otro fallo del hilo
        return {"status": "no_disponible", "reason": f"{type(e).__name__}: {e}", "cik": None, "filings": None}


def pending_results(fl: Optional[List[Dict[str, Any]]], cut: Optional[str]) -> Optional[Dict[str, Any]]:
    """F2_PRECEDENCIA §1.1: resultados publicados después del corte y aún no incorporados.

    Un 10-Q/10-K/20-F/40-F (o un 6-K con XBRL) cuyo periodo es posterior al corte, o un 8-K del apartado 2.02
    (Results of Operations) presentado después del filing periódico que cubre el corte (sin ese filing, después del
    corte). Un 8-K no avanza el corte: solo se avisa. Devuelve el más reciente o None."""
    if not fl or not cut:
        return None
    tol = _dt.timedelta(days=cfg("data.edgar.report_date_tolerance_days"))
    c = _dt.date.fromisoformat(cut)

    def rd(f):
        try:
            return _dt.date.fromisoformat(f["reportDate"]) if f.get("reportDate") else None
        except ValueError:
            return None
    covering = [f for f in fl if (f["form"] in ANNUAL_OR_QUARTERLY or (f["form"].startswith("6-K") and f["isXBRL"]))
                and rd(f) and abs(rd(f) - c) <= tol]
    base = max([f["filingDate"] for f in covering] + [cut])
    newer = [f for f in fl if (f["form"] in ANNUAL_OR_QUARTERLY or (f["form"].startswith("6-K") and f["isXBRL"]))
             and rd(f) and rd(f) > c + tol]
    results_8k = [f for f in fl if f["form"] in ("8-K", "8-K/A") and "2.02" in (f.get("items") or "")
                  and f["filingDate"] > base]
    cands = newer + results_8k
    if not cands:
        return None
    f = max(cands, key=lambda x: (x["filingDate"], x["accessionNumber"]))
    return {"date": f["filingDate"], "form": f["form"], "items": f.get("items") or None,
            "accn": f["accessionNumber"], "report_date": f.get("reportDate"), "as_of": cut, "source": "SEC EDGAR"}


def foreign_filer(fl: Optional[List[Dict[str, Any]]]) -> bool:
    """El emisor presenta 20-F/40-F (sus resultados van por 6-K, sin el apartado 2.02 de un 8-K)."""
    return any(f["form"] in ("20-F", "20-F/A", "40-F", "40-F/A") for f in fl or [])


def pending_from_calendar(entries: Optional[List[Dict[str, Any]]], cut: Optional[str],
                          today: _dt.date) -> Optional[Dict[str, Any]]:
    """F2_PRECEDENCIA §1.1, paso 2: sin 8-K, la fecha de resultados del proveedor. Una publicación con resultados
    (`epsActual`) más de `calendar_min_lag_days` días después del corte y no posterior a hoy es de un periodo que el
    análisis aún no tiene."""
    if not entries or not cut:
        return None
    c = _dt.date.fromisoformat(cut)
    lag = _dt.timedelta(days=cfg("data.edgar.calendar_min_lag_days"))
    hits = []
    for e in entries:
        try:
            d = _dt.date.fromisoformat(str(e.get("date")))
        except ValueError:
            continue
        if c + lag < d <= today and e.get("epsActual") is not None:
            hits.append(d)
    if not hits:
        return None
    return {"date": max(hits).isoformat(), "form": None, "items": None, "accn": None, "as_of": cut,
            "source": "calendario de resultados del proveedor (Finnhub)"}


def reset() -> None:
    """Vacía las cachés (tests)."""
    with _lock:
        _cache.clear()
