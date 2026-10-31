"""
Rendimiento (rama rendimiento/v4f8-memoria): dónde se va el tiempo de un análisis en frío. En un proceso nuevo, con las
fuentes reales, ejecuta main._compute_analysis de cada ticker (uno tras otro, o `--concurrent N` a la vez) y anota cada
petición de red (host, ruta sin la consulta, hilo, inicio y duración) y las fases del motor (Yahoo, Finnhub, serie de
precios, EDGAR y su espera, FFO). Las consultas no se anotan: llevan la clave de Finnhub.

    cd finanzer_next-perf/backend
    FINNHUB_API_KEY="$(security find-generic-password -s finanzer-finnhub -w)" \\
    SEC_EDGAR_USER_AGENT="$(security find-generic-password -s finanzer-sec-ua -w)" \\
        ../../finanzer_next/.venv313/bin/python tools/perf_frio.py NU AAPL JPM [--concurrent 3] [--mem] [--out x.json]
    (el «antes»: PERF_BACKEND=../../finanzer_next-v4f8/backend; su config/ es la de ese backend)
"""
import argparse
import functools
import json
import os
import statistics
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List
from urllib.parse import urlsplit

HERE = os.path.dirname(os.path.abspath(__file__))
# PERF_BACKEND: otro backend (p. ej. el worktree de 461e9266, para el «antes») con esta misma herramienta
BACKEND = os.path.abspath(os.environ.get("PERF_BACKEND") or os.path.dirname(HERE))
sys.path.insert(0, BACKEND)
sys.path.insert(0, os.path.join(BACKEND, "lib"))

T0 = time.monotonic()
EVENTS: List[Dict[str, Any]] = []
_lock = threading.Lock()


def _rec(kind: str, name: str, t: float, dur: float, **extra) -> None:
    with _lock:
        EVENTS.append({"kind": kind, "name": name, "t": round(t - T0, 3), "dur": round(dur, 3),
                       "thread": threading.current_thread().name, **extra})


def _url_name(url: str) -> str:
    u = urlsplit(str(url))
    return f"{u.netloc}{u.path}"          # sin la consulta (la clave de Finnhub va en ella)


def _wrap_net(obj, attr: str, url_of) -> None:
    real = getattr(obj, attr)

    @functools.wraps(real)
    def wrapped(*a, **k):
        t = time.monotonic()
        try:
            return real(*a, **k)
        finally:
            _rec("net", _url_name(url_of(a, k)), t, time.monotonic() - t)
    setattr(obj, attr, wrapped)


def _wrap_phase(mod, attr: str, label: str) -> None:
    real = getattr(mod, attr)

    @functools.wraps(real)
    def wrapped(*a, **k):
        t = time.monotonic()
        try:
            return real(*a, **k)
        finally:
            _rec("phase", label, t, time.monotonic() - t, arg=str(a[0]) if a and isinstance(a[0], str) else None)
    setattr(mod, attr, wrapped)


def instrument() -> None:
    import urllib.request
    from curl_cffi import requests as cffi_requests

    def req_url(a, k):
        r = a[0] if a else k.get("url")
        return getattr(r, "full_url", r)
    import finnhub_fallback                 # importa su `urlopen` antes de envolver el de urllib (no se cuenta dos veces)
    _wrap_net(finnhub_fallback, "urlopen", req_url)
    _wrap_net(urllib.request, "urlopen", req_url)
    _wrap_net(cffi_requests.Session, "request", lambda a, k: a[2] if len(a) > 2 else k.get("url"))

    import yf_adapter
    import sec_edgar
    import price_history
    _wrap_phase(yf_adapter, "_do_fetch", "yahoo._do_fetch")
    _wrap_phase(sec_edgar, "fetch", "edgar.fetch")
    _wrap_phase(sec_edgar, "collect", "edgar.collect (espera)")
    _wrap_phase(sec_edgar, "company_facts", "edgar.company_facts")
    _wrap_phase(sec_edgar, "submissions", "edgar.submissions")
    _wrap_phase(sec_edgar, "instance_facts", "edgar.instance_facts")
    _wrap_phase(sec_edgar, "_compact", "edgar._compact (parseo)")
    _wrap_phase(price_history, "collect", "price_history.collect (espera)")
    import finnhub_fallback as fh
    _wrap_phase(fh, "enrich_info", "finnhub.enrich_info")
    import importlib
    for mod, attr, label in (("reit_ffo", "resolve", "reit_ffo.resolve"), ("segments", "build", "segments.build")):
        try:                                # un backend anterior puede no tenerlos
            _wrap_phase(importlib.import_module(mod), attr, label)
        except ImportError:
            pass


def run_one(main, sym: str) -> Dict[str, Any]:
    t = time.monotonic()
    err = None
    try:
        main._compute_analysis(sym)
    except Exception as e:  # el informe dice qué falló; no corta los demás
        err = f"{type(e).__name__}: {e}"
    dur = time.monotonic() - t
    _rec("analysis", sym, t, dur, error=err)
    return {"symbol": sym, "s": round(dur, 3), "error": err}


def main_cli() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("symbols", nargs="+")
    ap.add_argument("--concurrent", type=int, default=1)
    ap.add_argument("--out")
    ap.add_argument("--mem", action="store_true", help="muestrea la memoria del proceso (máx. de RSS y huella física)")
    args = ap.parse_args()
    mem: List[float] = []
    stop = threading.Event()
    if args.mem:
        sys.path.insert(0, HERE)
        import load_test as LT          # noqa: E402 — solo sus medidas de memoria (ps y footprint)

        def sample():
            while not stop.is_set():
                r = LT.rss_mb(os.getpid())
                mem.append(max(r or 0.0, LT.footprint_mb(os.getpid()) or 0.0))
                stop.wait(0.25)
        threading.Thread(target=sample, daemon=True).start()
    import logging
    logging.disable(logging.WARNING)
    instrument()
    import main
    t = time.monotonic()
    with ThreadPoolExecutor(max_workers=args.concurrent) as ex:
        res = list(ex.map(lambda s: run_one(main, s), args.symbols))
    total = time.monotonic() - t
    stop.set()
    if mem:
        print(f"memoria: pico {max(mem):.0f} MB · al empezar {mem[0]:.0f} MB · al acabar {mem[-1]:.0f} MB")
    secs = [r["s"] for r in res]
    print(f"análisis: {', '.join(f'{r['symbol']} {r['s']:.2f}s' + (' ERR' if r['error'] else '') for r in res)}")
    print(f"p50 {statistics.median(secs):.2f}s · máx {max(secs):.2f}s · total {total:.2f}s")
    by: Dict[str, List[float]] = {}
    for e in EVENTS:
        if e["kind"] == "net":
            host = e["name"].split("/", 1)[0]
            by.setdefault(host, []).append(e["dur"])
    for host, ds in sorted(by.items(), key=lambda x: -sum(x[1])):
        print(f"  {host}: {len(ds)} peticiones, {sum(ds):.2f}s en total, máx {max(ds):.2f}s")
    ph: Dict[str, List[float]] = {}
    for e in EVENTS:
        if e["kind"] == "phase":
            ph.setdefault(e["name"], []).append(e["dur"])
    for name, ds in ph.items():
        print(f"  [{name}] n={len(ds)} total {sum(ds):.2f}s máx {max(ds):.2f}s")
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump({"results": res, "total_s": total, "events": sorted(EVENTS, key=lambda e: e["t"])}, fh,
                      ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main_cli()
