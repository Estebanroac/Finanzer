"""
Captura (con red) los inputs crudos que consume _compute_analysis y los
congela en tests/fixtures/<env>/<TICKER>/. Uso EXPLÍCITO, nunca automático:

    cd finanzer_next/backend
    python3 tests/capture_fixtures.py                 # los 6 tickers, si no existen
    python3 tests/capture_fixtures.py NFLX --force    # recapturar uno
    python3 tests/capture_fixtures.py --env local     # juego de datos (local por defecto)

El juego "prod" (capturado en Render con /api/_capture) se retiró en la fase 1 (D8);
la ruta de producción la cubre el juego "panel" capturado con --render-sim.

Fase 0 del plan de fiabilidad: el juego "panel" se captura en local con Render
simulado (fixture_backend.render_sim: S1 quoteSummary 401, S2 ticker.info vacío)
y Finnhub activo, con un ritmo de Finnhub bajo su límite de 60 peticiones/min:

    python3 tests/capture_fixtures.py --env panel --render-sim          # los 31
    python3 tests/capture_fixtures.py --render-sim --dir /tmp/x JPM     # a otra carpeta

Tras grabar, reproduce el análisis desde los fixtures y exige que sea
idéntico (byte a byte) al de la corrida en vivo: si el pipeline consumió algo
que no se grabó, la captura falla.

Finnhub participa solo si FINNHUB_API_KEY está exportada en la terminal. La
clave nunca se escribe: los parámetros `token` se eliminan antes de guardar.
"""
import argparse
import contextlib
import datetime as _dt
import logging
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fixture_backend as fb  # noqa: E402


def _run(sym, store):
    """Análisis o, si el backend lo rechaza (etapa 11b: ETF, sin tipo de cambio), su error HTTP."""
    from fastapi import HTTPException
    try:
        return fb.run_analysis(sym, store)
    except HTTPException as e:
        return {"__http_error__": e.status_code, "detail": e.detail}


def capture(sym, fixtures_dir, force, env="local", render_sim=False):
    import yf_adapter
    d = os.path.join(fixtures_dir, sym)
    if os.path.isdir(d) and not force:
        print(f"[{sym}] ya existe ({d}); usa --force para recapturar")
        return True

    key_present = bool(os.environ.get("FINNHUB_API_KEY", "").strip())
    now_local = _dt.datetime.now().astimezone()
    with contextlib.ExitStack() as stack:
        if render_sim:
            stack.enter_context(fb.render_sim())
        store = stack.enter_context(fb.record(fixtures_dir))
        live = _run(sym, store)
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
        "render_simulation": dict(fb.RENDER_SIM_META) if render_sim else None,
        "risk_free": {"frozen": True, "source": "config",
                      "note": "record y replay usan la Rf de config (sin ^TNX); prod en vivo usa ^TNX"},
        "yahoo": {
            "http_calls": len(store.http.get(sym, [])),
            "http_statuses": [e["status"] for e in store.http.get(sym, [])],
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
        replayed = _run(sym, rstore)
        misses = list(rstore.misses)
    ok = fb.raw_json(live) == fb.raw_json(replayed) and not misses
    if not ok:
        print(f"[{sym}] ERROR: el replay no reproduce la corrida en vivo. misses={misses}")
        print(f"        fixtures parciales en {tmp} para inspección")
        return False

    shutil.rmtree(d, ignore_errors=True)
    os.replace(tmp, d)
    path = live.get("data_provenance", {}).get("path") if "__http_error__" not in live else live["__http_error__"]
    print(f"[{sym}] OK  http={meta['yahoo']['http_statuses']} yf={meta['yahoo']['yfinance_attributes']} "
          f"path={path} degraded={degraded} finnhub={meta['finnhub']['participated']} -> {d}")
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tickers", nargs="*")
    ap.add_argument("--force", action="store_true", help="sobrescribir fixtures existentes")
    ap.add_argument("--env", default=fb.DEFAULT_ENV, choices=["local", fb.PANEL_ENV],
                    help="juego de datos a capturar")
    ap.add_argument("--render-sim", action="store_true",
                    help="simular Render: quoteSummary 401 y ticker.info vacío (plan B + Finnhub)")
    ap.add_argument("--sin-finnhub", action="store_true",
                    help="con --render-sim, capturar aunque no haya FINNHUB_API_KEY (no reproduce prod)")
    ap.add_argument("--dir", help="carpeta de destino en vez de tests/fixtures/<env> (validaciones)")
    args = ap.parse_args()
    if args.env == fb.PANEL_ENV and not args.render_sim:
        ap.error("el juego panel solo se captura con --render-sim")
    if args.env == fb.PANEL_ENV and not os.environ.get("FINNHUB_API_KEY", "").strip():
        ap.error("el juego panel necesita Finnhub: exporta FINNHUB_API_KEY en esta pestaña de terminal")
    if args.render_sim and not args.sin_finnhub and not os.environ.get("FINNHUB_API_KEY", "").strip():
        ap.error("sin FINNHUB_API_KEY en este shell: la captura no reproduciría producción (allí Finnhub "
                 "participa). Pásala con FINNHUB_API_KEY=$(security find-generic-password -s finanzer-finnhub -w) "
                 "o usa --sin-finnhub a sabiendas.")
    tickers = args.tickers or (fb.PANEL_TICKERS if args.env == fb.PANEL_ENV else fb.TICKERS)
    logging.disable(logging.WARNING)
    fdir = os.path.abspath(args.dir) if args.dir else fb.fixtures_dir(args.env)
    os.makedirs(fdir, exist_ok=True)
    results = [capture(t.upper(), fdir, args.force, args.env, args.render_sim) for t in tickers]
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
