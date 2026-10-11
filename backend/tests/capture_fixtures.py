"""
Captura (con red) los inputs crudos que consume _compute_analysis y los
congela en tests/fixtures/<env>/<TICKER>/. Uso EXPLÍCITO, nunca automático:

    cd finanzer_next/backend
    python3 tests/capture_fixtures.py                 # los 6 tickers, si no existen
    python3 tests/capture_fixtures.py NFLX --force    # recapturar uno
    python3 tests/capture_fixtures.py --env local     # juego de datos (local por defecto)

El juego "prod" no se captura aquí: viene de /api/_capture en Render (ver
import_prod_capture.py).

Tras grabar, reproduce el análisis desde los fixtures y exige que sea
idéntico (byte a byte) al de la corrida en vivo: si el pipeline consumió algo
que no se grabó, la captura falla.

Finnhub participa solo si FINNHUB_API_KEY está exportada en la terminal. La
clave nunca se escribe: los parámetros `token` se eliminan antes de guardar.
"""
import argparse
import datetime as _dt
import logging
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fixture_backend as fb  # noqa: E402


def capture(sym, fixtures_dir, force, env="local"):
    import yf_adapter
    d = os.path.join(fixtures_dir, sym)
    if os.path.isdir(d) and not force:
        print(f"[{sym}] ya existe ({d}); usa --force para recapturar")
        return True

    key_present = bool(os.environ.get("FINNHUB_API_KEY", "").strip())
    now_local = _dt.datetime.now().astimezone()
    with fb.record(fixtures_dir) as store:
        live = fb.run_analysis(sym, store)
        entry = yf_adapter._cache.get(sym)
        degraded = bool(entry[2]) if entry else None

    yfd = store.yf.get(sym, {})
    meta = {
        "ticker": sym,
        "environment": env,
        "captured_at_utc": now_local.astimezone(_dt.timezone.utc).isoformat(timespec="seconds"),
        "captured_at_local": now_local.replace(tzinfo=None).isoformat(timespec="seconds"),
        "timezone": str(now_local.tzinfo),
        "versions": fb.environment_info(),
        "git_commit": fb.git_commit(),
        "finnhub": {
            "key_present": key_present,
            "participated": bool(store.finnhub.get(sym)),
            "calls": len(store.finnhub.get(sym, [])),
            "note": ("Sin FINNHUB_API_KEY en el entorno local: la segunda fuente no participó "
                     "(en producción sí participa)") if not key_present else "",
        },
        "yahoo": {
            "http_calls": len(store.http.get(sym, [])),
            "degraded": degraded,
            "fallback_yfinance_used": "fast_info" in yfd,
            "yfinance_attributes": sorted(yfd.keys()),
        },
        "unrecorded_yfinance_access": store.unrecorded.get(sym, []),
    }

    tmp = d + ".tmp"
    shutil.rmtree(tmp, ignore_errors=True)
    store.base_dir = fixtures_dir
    os.makedirs(tmp)
    store.dir_for = lambda _s: tmp  # escribir primero en .tmp
    store.save(sym, meta)

    # Verificación: replay desde .tmp == corrida en vivo
    with fb.replay(fixtures_dir) as rstore:
        rstore.dir_for = lambda _s: tmp
        replayed = fb.run_analysis(sym, rstore)
        misses = list(rstore.misses)
    ok = fb.raw_json(live) == fb.raw_json(replayed) and not misses
    if not ok:
        print(f"[{sym}] ERROR: el replay no reproduce la corrida en vivo. misses={misses}")
        print(f"        fixtures parciales en {tmp} para inspección")
        return False

    shutil.rmtree(d, ignore_errors=True)
    os.replace(tmp, d)
    print(f"[{sym}] OK  http={meta['yahoo']['http_calls']} yf={meta['yahoo']['yfinance_attributes']} "
          f"degraded={degraded} finnhub={meta['finnhub']['participated']} -> {d}")
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tickers", nargs="*", default=fb.TICKERS)
    ap.add_argument("--force", action="store_true", help="sobrescribir fixtures existentes")
    ap.add_argument("--env", default=fb.DEFAULT_ENV, choices=["local"],
                    help="juego de datos a capturar (prod llega por /api/_capture)")
    args = ap.parse_args()
    logging.disable(logging.WARNING)
    fdir = fb.fixtures_dir(args.env)
    results = [capture(t.upper(), fdir, args.force, args.env) for t in args.tickers]
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
