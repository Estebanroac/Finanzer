"""
F13 · banco de pruebas de 110 empresas: congela los insumos crudos del análisis (con red, una vez) y lo recalcula sin red
antes y después de cada corrección del motor.

Los fixtures viven FUERA de git (por defecto en archivo-historico/evidencias-de-pruebas/f13_banco110_2026-11-05/fixtures):

    <dir>/<T>/                    Yahoo, yfinance, Finnhub y series de precios del ticker (capture_fixtures, .json.gz)
    <dir>/f2b/                    EDGAR (tickers, submissions, companyfacts, instancias) y calendario de Finnhub
                                  (capture_f2b_sources, sin y con --facts)
    <dir>/segments/<T>.json       segmentos de negocio y geografía del último anual (capture_segments)
    <dir>/_captura/estado.json    resultado de cada ticker (ok / error, paso, segundos, intento) y logs/<T>.log

Captura (con red; claves solo en el entorno de la orden, nunca escritas ni impresas):

    cd backend
    FINNHUB_API_KEY="$(security find-generic-password -s finanzer-finnhub -w)" \\
    SEC_EDGAR_USER_AGENT="$(security find-generic-password -s finanzer-sec-ua -w)" \\
        ../.venv313/bin/python tests/f13_banco110.py --capture [TICKERS]

  Orden por ticker (cada paso en su propio proceso: los capturadores tocan estado global de sec_edgar y segments):
    1. capture_f2b_sources T --dir <dir>/f2b            submissions + calendario (se fusionan tabla y metadata)
    2. capture_f2b_sources T --facts --dir <dir>/f2b    companyfacts e instancias pendientes
    3. capture_segments T --dir <dir>/segments          segmentos (verifica su propio replay)
    4. capture_fixtures T --env panel --render-sim --gzip --own-sources --dir <dir>
       (ruta de producción; verifica que el replay, con 1–3 SOLO de <dir>, reproduce byte a byte la corrida en vivo)
  Reanudable: salta los tickers ya capturados (<dir>/<T>/metadata.json.gz). Los fallidos se reintentan una vez al final.

Recalcular sin red (determinista: dos corridas dan los mismos bytes):

    ../.venv313/bin/python tests/f13_banco110.py --run --out <carpeta> [TICKERS]

  Escribe <carpeta>/<T>.json.gz (el análisis completo, o {"__http_error__", "detail"} si el backend lo rechaza) y
  <carpeta>/resumen.json (veredicto, notas, nivel, confianza, arquetipo, WACC, rating, upside del DCF, DCF inverso,
  banderas, huella sha256 del análisis y accesos no grabados).
"""
import argparse
import gzip
import json
import os
import shutil
import subprocess
import sys
import time

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(TESTS_DIR)
sys.path.insert(0, TESTS_DIR)

BANCO = "/Users/joseestebanroa/Downloads/Finanzer/archivo-historico/evidencias-de-pruebas/f13_banco110_2026-11-05"
DEFAULT_DIR = os.path.join(BANCO, "fixtures")
DEFAULT_LIST = os.path.join(BANCO, "tickers110.txt")


def load_tickers(path=DEFAULT_LIST):
    with open(path, encoding="utf-8") as fh:
        return [ln.strip().upper() for ln in fh if ln.strip() and not ln.startswith("#")]


def _read_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        return default


def _write_json(path, obj, compact=False):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".part"
    with open(tmp, "w", encoding="utf-8") as fh:
        if compact:
            json.dump(obj, fh, separators=(",", ":"), ensure_ascii=False, sort_keys=True)
        else:
            json.dump(obj, fh, indent=1, ensure_ascii=False, sort_keys=True)
        fh.write("\n")
    os.replace(tmp, path)


def captured(base, sym):
    d = os.path.join(base, sym)
    return os.path.isfile(os.path.join(d, "metadata.json.gz")) or os.path.isfile(os.path.join(d, "metadata.json"))


# ═══════════════════════════ captura ═══════════════════════════

def _step(cmd, log):
    log.write(f"\n$ {' '.join(os.path.basename(c) if c.endswith('.py') else c for c in cmd[1:])}\n")
    log.flush()
    r = subprocess.run(cmd, cwd=BACKEND_DIR, stdout=log, stderr=subprocess.STDOUT, env=os.environ.copy())
    log.write(f"[código {r.returncode}]\n")
    log.flush()
    return r.returncode


def _f2b_sources(sym, f2b, log):
    """Paso 1 con fusión: capture_f2b_sources reescribe la tabla de tickers y la metadata con SOLO los símbolos pedidos."""
    tpath = os.path.join(f2b, "edgar", "company_tickers.json")
    mpath = os.path.join(f2b, "metadata.json")
    old_t, old_m = _read_json(tpath, {}), _read_json(mpath, {})
    rc = _step([sys.executable, "tests/capture_f2b_sources.py", sym, "--dir", f2b], log)
    new_t, new_m = _read_json(tpath, {}), _read_json(mpath, {})
    if rc == 0:
        table = {**old_t, **new_t}
        syms = dict(old_m.get("symbols") or {})
        for s, rep in (new_m.get("symbols") or {}).items():
            syms[s] = dict(rep, captured_at_utc=new_m.get("captured_at_utc"))
        meta = dict(new_m, symbols=syms)
        if "facts" in old_m:
            meta["facts"] = old_m["facts"]
    else:                                   # se deja como estaba
        table, meta = old_t, old_m
    _write_json(tpath, table, compact=True)
    if meta:
        _write_json(mpath, meta)
    return rc


def _f2b_facts(sym, f2b, log):
    mpath = os.path.join(f2b, "metadata.json")
    old_facts = (_read_json(mpath, {}) or {}).get("facts") or {}
    rc = _step([sys.executable, "tests/capture_f2b_sources.py", sym, "--facts", "--dir", f2b], log)
    meta = _read_json(mpath, {})
    new_facts = meta.get("facts") or {}
    syms = dict(old_facts.get("symbols") or {})
    if rc == 0:
        for s, rep in (new_facts.get("symbols") or {}).items():
            syms[s] = dict(rep, captured_at_utc=new_facts.get("captured_at_utc"))
    meta["facts"] = dict(new_facts or old_facts, symbols=syms)
    _write_json(mpath, meta)
    return rc


def _gzip_f2b(f2b):
    """companyfacts, submissions y calendarios comprimidos (f2b_fixtures._load los lee; tabla y metadata, en claro)."""
    import fixture_backend as fb
    for sub in (("edgar", "companyfacts"), ("edgar", "submissions"), ("finnhub_calendar",)):
        d = os.path.join(f2b, *sub)
        if os.path.isdir(d):
            fb.gzip_fixture_dir(d)


def capture_one(sym, base, attempt):
    f2b, seg = os.path.join(base, "f2b"), os.path.join(base, "segments")
    logs = os.path.join(base, "_captura", "logs")
    os.makedirs(logs, exist_ok=True)
    t0 = time.monotonic()
    with open(os.path.join(logs, f"{sym}.log"), "a", encoding="utf-8") as log:
        log.write(f"\n===== {sym} · intento {attempt} · {time.strftime('%Y-%m-%d %H:%M:%S')} =====\n")
        steps = [
            ("f2b", lambda: _f2b_sources(sym, f2b, log)),
            ("facts", lambda: _f2b_facts(sym, f2b, log)),
            ("segments", lambda: _step([sys.executable, "tests/capture_segments.py", sym, "--dir", seg], log)),
            ("fixtures", lambda: _step([sys.executable, "tests/capture_fixtures.py", sym, "--env", "panel",
                                        "--render-sim", "--gzip", "--own-sources", "--force", "--dir", base], log)),
        ]
        for name, fn in steps:
            rc = fn()
            if rc != 0:
                return {"ok": False, "step": name, "rc": rc, "secs": round(time.monotonic() - t0, 1),
                        "attempt": attempt, "detail": _last_error(os.path.join(logs, f"{sym}.log"))}
    _gzip_f2b(f2b)
    return {"ok": True, "secs": round(time.monotonic() - t0, 1), "attempt": attempt}


def _last_error(log_path):
    with open(log_path, encoding="utf-8", errors="replace") as fh:
        lines = [ln.rstrip() for ln in fh if ln.strip()]
    tail = [ln for ln in lines[-40:] if "ERROR" in ln or "Error" in ln or "error" in ln or "misses" in ln]
    return (tail or lines[-3:])[-3:]


def do_capture(tickers, base):
    for k in ("FINNHUB_API_KEY", "SEC_EDGAR_USER_AGENT"):
        if not os.environ.get(k, "").strip():
            raise SystemExit(f"falta {k} en el entorno de la orden (ver el uso)")
    os.makedirs(base, exist_ok=True)
    spath = os.path.join(base, "_captura", "estado.json")
    state = _read_json(spath, {})
    t_all = time.monotonic()
    for attempt in (1, 2):                 # el segundo pase reintenta una vez los fallidos (red)
        todo = [s for s in tickers if not captured(base, s)
                and (attempt == 1 or not state.get(s, {}).get("ok"))]
        if attempt == 2:
            todo = [s for s in todo if state.get(s, {}).get("attempt", 0) < 2]
        for i, sym in enumerate(todo, 1):
            shutil.rmtree(os.path.join(base, sym + ".tmp"), ignore_errors=True)
            res = capture_one(sym, base, attempt)
            state[sym] = res
            _write_json(spath, state)
            print(f"[{attempt}·{i}/{len(todo)}] {sym}: {'OK' if res['ok'] else 'FALLO en ' + res['step']} "
                  f"({res['secs']} s)", flush=True)
            if not res["ok"]:
                shutil.rmtree(os.path.join(base, sym + ".tmp"), ignore_errors=True)
    ok = [s for s in tickers if captured(base, s)]
    print(f"\n{len(ok)}/{len(tickers)} capturadas en {time.monotonic() - t_all:.0f} s; "
          f"fallidas: {[s for s in tickers if s not in ok]}", flush=True)
    return 0 if len(ok) == len(tickers) else 1


# ═══════════════════════════ recálculo sin red ═══════════════════════════

def _g(d, *path):
    for k in path:
        if not isinstance(d, dict):
            return None
        d = d.get(k)
    return d


def summarize(a):
    if "__http_error__" in a:
        return {"http_error": a["__http_error__"], "detail": a.get("detail")}
    rev = _g(a, "reverse_dcf", "main") or {}
    return {
        "veredicto": _g(a, "verdict", "text"),
        "nota_calidad": _g(a, "quality", "score"),
        "nivel_calidad": _g(a, "quality", "level"),
        "nota_precio": _g(a, "price_attractiveness", "score"),
        "nivel_precio": _g(a, "price_attractiveness", "level"),
        "confianza": _g(a, "confidence", "level"),
        "confianza_motivo": _g(a, "verdict", "confidence_text"),
        "confianza_razones": _g(a, "confidence", "reasons"),
        "arquetipo": _g(a, "classification", "archetype"),
        "wacc": _g(a, "wacc", "value"),
        "rating_sintetico": _g(a, "wacc", "rating", "rating"),
        "dcf_upside": _g(a, "dcf", "upside"),
        "dcf_estado": _g(a, "dcf_status", "state"),
        "dcf_inverso": {"aplicable": _g(a, "reverse_dcf", "applicable"), "flujo": rev.get("flow_label"),
                        "flujo_por_accion": rev.get("flow_per_share"), "g10": rev.get("g10"),
                        "banda": rev.get("band"), "estado": rev.get("state")},
        "banderas_rojas": len(_g(a, "alerts", "red_flags") or []),
        "advertencias": len(_g(a, "alerts", "warnings") or []),
    }


def _gz_bytes(text):
    import io
    buf = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=buf, mtime=0) as gz:
        gz.write(text.encode("utf-8"))
    return buf.getvalue()


def do_run(tickers, base, out):
    import logging
    logging.disable(logging.CRITICAL)
    import fixture_backend as fb
    from fastapi import HTTPException
    os.makedirs(out, exist_ok=True)
    resumen, t0 = {}, time.monotonic()
    for sym in tickers:
        if not captured(base, sym):
            resumen[sym] = {"sin_fixtures": True}
            continue
        with fb.replay(base, extra_dirs=(base,), own_sources=True) as store:
            try:
                a = fb.run_analysis(sym, store)
            except HTTPException as e:
                a = {"__http_error__": e.status_code, "detail": e.detail}
            misses = list(store.misses)
        raw = fb.raw_json(a)
        with open(os.path.join(out, f"{sym}.json.gz"), "wb") as fh:
            fh.write(_gz_bytes(raw + "\n"))
        resumen[sym] = dict(summarize(a), sha256=fb.sha256(raw), accesos_no_grabados=misses)
        print(f"{sym}: {resumen[sym].get('veredicto') or resumen[sym].get('http_error')}", flush=True)
    _write_json(os.path.join(out, "resumen.json"), resumen)
    print(f"\n{len(resumen)} empresas en {time.monotonic() - t0:.0f} s → {out}", flush=True)
    return 0 if all(not v.get("accesos_no_grabados") and not v.get("sin_fixtures") for v in resumen.values()) else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--capture", action="store_true", help="capturar con red (reanudable)")
    mode.add_argument("--run", action="store_true", help="recalcular sin red desde los fixtures")
    ap.add_argument("tickers", nargs="*", help="por defecto, los de --list")
    ap.add_argument("--dir", default=DEFAULT_DIR, help="carpeta de los fixtures")
    ap.add_argument("--list", default=DEFAULT_LIST, help="lista de tickers (uno por línea)")
    ap.add_argument("--out", help="con --run: carpeta de salida")
    args = ap.parse_args(argv)
    tickers = [t.upper() for t in args.tickers] or load_tickers(args.list)
    base = os.path.abspath(args.dir)
    if args.capture:
        return do_capture(tickers, base)
    if not args.out:
        ap.error("--run necesita --out <carpeta>")
    return do_run(tickers, base, os.path.abspath(args.out))


if __name__ == "__main__":
    sys.exit(main())
