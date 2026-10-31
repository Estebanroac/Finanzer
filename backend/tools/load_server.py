"""
Verificación de la v4 (V4 · carga y memoria): el backend real (main.py, con la web compilada en ../frontend/out) con
una sola cosa más, la medida de los turnos de análisis. Lo arranca tools/load_test.py; no es para producción.

Cada turno de _ANALYSIS_SLOTS (main._slot) se anota: si es de un usuario o de la cola de fondo (rivales y
precalentado), cuánto esperó el turno y cuánto lo tuvo. `GET /__load/slots` lo devuelve. Con eso, load_test.py
comprueba que la cola nunca retrasa a un usuario más que otro análisis.

    ../.venv313/bin/python tools/load_server.py --port 8771
Las claves (FINNHUB_API_KEY, SEC_EDGAR_USER_AGENT) llegan por el entorno; aquí no se leen ni se escriben.
"""
import argparse
import contextlib
import os
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))


def instrument(main):
    """Envuelve main._slot: anota (usuario o fondo, espera, tenencia) de cada turno."""
    records = []
    lock = threading.Lock()
    real_slot = getattr(main, "_slot", None)
    if real_slot is None:          # backend sin turnos con prioridad (main antes de E2b): solo /__load/slots vacío
        @main.app.get("/__load/slots")
        def no_slots():
            return {"records": []}
        main.app.router.routes.insert(0, main.app.router.routes.pop())
        return records

    @contextlib.contextmanager
    def slot(user: bool = True):
        t0 = time.monotonic()
        with real_slot(user):
            t1 = time.monotonic()
            try:
                yield
            finally:
                with lock:
                    records.append({"user": user, "wait_s": round(t1 - t0, 3),
                                    "hold_s": round(time.monotonic() - t1, 3), "t": round(t0, 3)})
    main._slot = slot

    @main.app.get("/__load/slots")
    def slots():
        with lock:
            return {"records": list(records)}
    # Por delante del comodín de la web compilada (GET /{filepath:path}).
    main.app.router.routes.insert(0, main.app.router.routes.pop())
    return records


def deep_size(obj, seen=None, depth=0) -> int:
    """Huella en memoria aproximada de `obj` y lo que cuelga de él (DataFrame/Series con memory_usage(deep), arrays de
    numpy por nbytes; contenedores y objetos recorridos una vez cada uno)."""
    import numpy as np
    import pandas as pd
    seen = set() if seen is None else seen
    if id(obj) in seen or depth > 40:
        return 0
    seen.add(id(obj))
    if isinstance(obj, pd.DataFrame):
        return int(obj.memory_usage(deep=True, index=True).sum())
    if isinstance(obj, pd.Series):
        return int(obj.memory_usage(deep=True, index=True))
    if isinstance(obj, np.ndarray):
        return int(obj.nbytes)
    n = sys.getsizeof(obj, 0)
    if isinstance(obj, dict):
        n += sum(deep_size(k, seen, depth + 1) + deep_size(v, seen, depth + 1) for k, v in list(obj.items()))
    elif isinstance(obj, (list, tuple, set, frozenset)):
        n += sum(deep_size(x, seen, depth + 1) for x in list(obj))
    elif hasattr(obj, "__dict__") and not isinstance(obj, type):
        n += deep_size(vars(obj), seen, depth + 1)
    return n


def cache_sizes(main):
    """`GET /__load/caches`: huella en memoria (deep_size) y entradas de cada caché de módulo de backend/ (V4 ·
    memoria: qué queda retenido tras la carga). Lo compartido entre cachés cuenta en la primera que lo nombra."""
    import gc

    @main.app.get("/__load/caches")
    def caches():
        gc.collect()
        root = os.path.dirname(os.path.abspath(main.__file__))
        rows, seen = [], set()
        for name, mod in sorted(sys.modules.items()):
            f = getattr(mod, "__file__", "") or ""
            if not f.startswith(root) or "/tests/" in f or "/tools/" in f:
                continue
            for attr, v in list(vars(mod).items()):
                if "cache" not in attr.lower() and attr not in ("_summaries", "_state", "_caps", "_rankings"):
                    continue
                obj = getattr(v, "_cache", v)
                if not isinstance(obj, dict):
                    continue
                try:
                    n = deep_size(obj, seen)
                except Exception:  # noqa: BLE001 — algo que no se recorre: sin tamaño
                    n = None
                rows.append({"cache": f"{name}.{attr}", "entries": len(obj), "mb": None if n is None else round(n / 1e6, 2)})
        return {"caches": sorted(rows, key=lambda r: -(r["mb"] or 0))}
    main.app.router.routes.insert(0, main.app.router.routes.pop())


def override(pairs):
    """`--set ruta=valor` (valor en TOML: 3, 16, true, "x"): rehace settings.SETTINGS con esos cambios antes de importar
    main, así lo leen también los semáforos y topes que se fijan al importar."""
    import tomllib
    import settings

    def thaw(v):
        if isinstance(v, (dict, type(settings.SETTINGS))):
            return {k: thaw(x) for k, x in v.items()}
        if isinstance(v, tuple):
            return [thaw(x) for x in v]
        return v
    data = thaw(settings.SETTINGS)
    for kv in pairs:
        path, raw = kv.split("=", 1)
        *parents, leaf = path.split(".")
        cur = data
        for p in parents:
            cur = cur[p]
        if leaf not in cur:
            raise SystemExit(f"--set: clave inexistente {path}")
        cur[leaf] = tomllib.loads(f"v = {raw}")["v"]
    settings.SETTINGS = settings._freeze(data)


def main_():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8771)
    ap.add_argument("--backend", default=os.path.dirname(HERE),
                    help="carpeta backend/ cuyo main.py se sirve (por defecto, el de esta rama; la referencia: el de main)")
    ap.add_argument("--no-prewarm", action="store_true", help="perfil de memoria: sin precalentado de tendencias")
    ap.add_argument("--segments-shared-parse", action="store_true",
                    help="perfil de memoria: los segmentos con el turno de lecturas del análisis (como antes de V6, B2)")
    ap.add_argument("--set", action="append", default=[], metavar="RUTA=VALOR",
                    help="cambia un valor de la config antes de importar main (medir opciones de memoria)")
    args = ap.parse_args()
    backend = os.path.abspath(args.backend)
    sys.path[:0] = [backend, os.path.join(backend, "lib")]
    os.chdir(backend)
    if args.set:
        override(args.set)
    import uvicorn
    import main
    instrument(main)
    cache_sizes(main)
    if args.segments_shared_parse:
        import sec_edgar
        sec_edgar._segments_parsing = sec_edgar._parsing
    if args.no_prewarm:
        try:
            import trending
            trending._limits["prewarm_max"] = 0
        except ImportError:     # backend sin tendencias (main): no hay precalentado que quitar
            pass
    uvicorn.run(main.app, host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main_()
