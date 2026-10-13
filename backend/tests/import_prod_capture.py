"""
Importa las capturas de producción (GET /api/_capture/{symbol} en Render) como
fixtures del juego "prod": tests/fixtures/prod/<TICKER>/.

    cd finanzer_next/backend
    python3 tests/import_prod_capture.py --src ~/Downloads/finanzer_prod_capture
    python3 tests/import_prod_capture.py --src DIR NFLX --force

Espera en --src, por ticker: capture_<T>.json (+ .headers) y, opcionalmente,
analysis_<T>.json (+ .headers): el /api/analysis pedido justo después.

Para cada ticker:
  1. Valida la captura y la revisa en busca de secretos (token=, apikey=,
     ghp_…); si encuentra algo, no importa nada.
  2. Escribe metadata/yahoo_http/yfinance/finnhub con entorno "prod".
  3. Verificación: reproduce el análisis desde los fixtures y lo compara con
     el analysis_<T>.json de prod, SOLO si ambos los sirvió el mismo proceso
     (cabecera X-Capture-Served-By): la caché es por proceso. Guarda el
     resultado en metadata.verification.

La fecha del PDF de prod se congela a la fecha UTC de la captura.
"""
import argparse
import json
import logging
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fixture_backend as fb  # noqa: E402

_SECRET_RE = re.compile(r"(?i)(token=[A-Za-z0-9]{8}|apikey=[A-Za-z0-9]{8}|ghp_[A-Za-z0-9]{10})")


def _served_by(path):
    if not os.path.isfile(path):
        return None
    with open(path, encoding="latin-1") as fh:
        for line in fh:
            if line.lower().startswith("x-capture-served-by:"):
                return line.split(":", 1)[1].strip()
    return None


def import_one(sym, src, force):
    cap_path = os.path.join(src, f"capture_{sym}.json")
    with open(cap_path, encoding="utf-8") as fh:
        raw = fh.read()
    if _SECRET_RE.search(raw):
        print(f"[{sym}] ABORTADO: la captura contiene un patrón de secreto; no se importa")
        return False
    cap = json.loads(raw)
    if not isinstance(cap, dict) or "metadata" not in cap:
        print(f"[{sym}] ABORTADO: {cap_path} no es una captura válida")
        return False

    dest = os.path.join(fb.fixtures_dir("prod"), sym)
    if os.path.isdir(dest) and not force:
        print(f"[{sym}] ya existe ({dest}); usa --force para reimportar")
        return True

    m = dict(cap["metadata"])
    served_cap = _served_by(os.path.join(src, f"capture_{sym}.headers"))
    served_ana = _served_by(os.path.join(src, f"analysis_{sym}.headers"))
    same_process = bool(served_cap) and served_cap == served_ana
    m.update({
        "ticker": sym,
        "environment": "prod",
        "source": "GET /api/_capture (finanzer.app, Render)",
        # Render reporta UTC; se usa como fecha "local" para congelar el PDF.
        "captured_at_local": m["captured_at_utc"][:19],
        "timezone": "UTC",
        "served_by": {"capture": served_cap, "analysis": served_ana, "same_process": same_process},
    })
    m["yahoo"]["http_statuses"] = [e.get("status") for e in cap.get("yahoo_http", [])]
    m["finnhub"]["note"] = ""

    tmp = dest + ".tmp"
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp)
    store = fb.FixtureStore(fb.fixtures_dir("prod"), mode="record")
    store.http[sym] = cap.get("yahoo_http", [])
    store.yf[sym] = cap.get("yfinance", {})
    store.finnhub[sym] = cap.get("finnhub", [])
    store.dir_for = lambda _s: tmp
    store.save(sym, m)

    # Verificación contra el /api/analysis de prod (mismo proceso).
    ana_path = os.path.join(src, f"analysis_{sym}.json")
    with fb.replay(fb.fixtures_dir("prod")) as rstore:
        rstore.dir_for = lambda _s: tmp
        replayed = fb.run_analysis(sym, rstore)
        misses = list(rstore.misses)
    verification = {"replay_misses": misses}
    if os.path.isfile(ana_path) and same_process:
        with open(ana_path, encoding="utf-8") as fh:
            prod_analysis = json.load(fh)
        rep_norm = json.loads(fb.stable_json(json.loads(json.dumps(replayed, default=str))))
        prod_norm = json.loads(fb.stable_json(prod_analysis))
        verification["compared_with_prod_analysis"] = True
        verification["matches_prod_analysis"] = rep_norm == prod_norm
        if rep_norm != prod_norm:
            from diff_golden import diff_analysis
            groups = diff_analysis(prod_norm, rep_norm)
            verification["differences"] = {k: [[p, a, b] for p, a, b in v][:20] for k, v in groups.items()}
    else:
        verification["compared_with_prod_analysis"] = False
        verification["reason"] = ("sin analysis_<T>.json" if not os.path.isfile(ana_path)
                                  else "captura y análisis servidos por procesos distintos")
    m["verification"] = verification
    store.save(sym, m)

    shutil.rmtree(dest, ignore_errors=True)
    os.replace(tmp, dest)
    ok = not misses and verification.get("matches_prod_analysis", True)
    print(f"[{sym}] {'OK ' if ok else 'REVISAR'} statuses={m['yahoo']['http_statuses']} "
          f"fallback={m['yahoo']['fallback_yfinance_used']} finnhub={m['finnhub']['participated']} "
          f"same_process={same_process} replay==prod={verification.get('matches_prod_analysis')} "
          f"misses={len(misses)} -> {dest}")
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tickers", nargs="*", default=fb.TICKERS)
    ap.add_argument("--src", default=os.path.expanduser("~/Downloads/finanzer_prod_capture"))
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    logging.disable(logging.CRITICAL)
    results = [import_one(t.upper(), args.src, args.force) for t in args.tickers]
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
