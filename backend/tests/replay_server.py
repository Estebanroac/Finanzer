"""
La app completa (API + web compilada en ../frontend/out) en REPLAY (fase 3, T7: comprobación visual sin red ni
claves). Cada /api/analysis/<T> se calcula desde los fixtures del juego, como en los tests (fixture_backend).

    cd finanzer_next/backend
    ../.venv313/bin/python tests/replay_server.py [--env panel | --dir tests/fixtures/f3_externa] [--port 8767]
Antes: `npx next build --webpack` en ../frontend (en un worktree, Turbopack falla con el node_modules enlazado).
"""
import argparse
import logging
import os
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fixture_backend as fb  # noqa: E402


NOT_IN_DEMO = "No incluido en la demo con datos grabados; con datos reales se analiza al momento"
PEERS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "peers")


def install(app_main, base, store):
    """Conecta la app al replay (también la usan los tests: tests/test_faults.py): cada análisis desde los fixtures de
    `base`, uno cada vez, y los segmentos, rivales, tendencias y búsqueda desde sus capturas, sin red."""
    from fastapi import HTTPException
    orig = app_main._compute_analysis
    # Rediseño E2a: un análisis cada vez. El replay tiene estado global (store.current, la clave ficticia y las
    # cachés que reset_state vacía): con varias peticiones a la vez (Playwright en paralelo), un análisis vaciaba
    # la serie de precios de otro a medias y su capítulo 3 salía sin momentum ni tendencia.
    lock = threading.Lock()

    def compute(symbol):
        sym = symbol.upper()
        if not store.has(sym):
            raise HTTPException(404, f"{sym}: sin fixtures en el replay")   # nunca rutas locales en un motivo
        with lock:
            store.current = sym
            store.load(sym)
            if store.meta[sym].get("finnhub", {}).get("participated"):
                os.environ["FINNHUB_API_KEY"] = "fixture-replay"
            else:
                os.environ.pop("FINNHUB_API_KEY", None)
            fb.reset_state()
            return orig(sym)

    app_main._compute_analysis = compute
    # Rediseño E2b: los segmentos desde tests/fixtures/segments (capture_segments.py), sin red.
    import capture_segments
    import segments
    segments.FETCHER = capture_segments.replay_fetcher()
    # Rivales: capitalizaciones de tests/fixtures/peers/caps.json; cada rival se analiza con `compute` desde su juego
    # (tests/fixtures/peers/<T>, comprimido) o, si no lo tiene, sale como fallo con un motivo de lector. El almacén del replay no admite análisis simultáneos:
    # mientras se calculan rivales, no pidas otro análisis.
    import capture_peer_caps
    import peers
    peers.CAPS_FETCHER = capture_peer_caps.load_caps().get
    peers.CAPS_BATCH = None          # PDF rápido: sin la petición a Yahoo; las capitalizaciones grabadas
    # Tendencias: la descarga del universo capturada (tests/fixtures/trending/batch.json). Sus tarjetas se analizan
    # en la misma cola que los rivales (main conecta analysis_queue.ANALYZE a `compute`): las que están en el juego
    # de fixtures salen con la calidad y el precio del motor; las demás, como fallo.
    # V4b (decisión del PM): en la cola de fondo (rivales y tarjetas de la portada), una empresa sin datos grabados no
    # es un fallo: con datos reales se analiza al momento. El 404 del análisis de una página sigue diciendo el suyo.
    import analysis_queue
    from fastapi import HTTPException as _HE
    _analyze = analysis_queue.ANALYZE

    def analyze(sym):
        if not store.has(str(sym).upper()):
            raise _HE(404, NOT_IN_DEMO)
        return _analyze(sym)
    analysis_queue.ANALYZE = analyze
    import capture_trending
    import trending
    trending.FETCH_BATCH = capture_trending.replay_fetcher()[0]
    # Rediseño E4: el buscador de /v2 con las respuestas de Yahoo capturadas (tests/fixtures/search/quotes.json).
    import capture_search
    import search_v2
    search_v2.YAHOO_QUOTES = capture_search.replay_quotes()
    # P8: las mini-gráficas del cintillo, de la descarga capturada (tests/fixtures/sparklines).
    import capture_sparklines
    import sparklines
    sparklines.FETCH = capture_sparklines.replay_fetcher()
    return compute


def add_fault_switch(app):
    """Verificación de la v4 (V3): `POST /__replay/fault?name=<fallo>` activa un fallo de tests/faults.py sobre el
    replay (sin `name`, o `name=none`, lo quita) y `GET /__replay/fault` dice cuál está activo. Solo existe en el
    servidor de replay: main.py no lo tiene."""
    import faults
    switch = faults.Switch()

    @app.post("/__replay/fault")
    def set_fault(name: str = ""):
        from fastapi import HTTPException
        n = None if name in ("", "none") else name
        if n is not None and n not in faults.FAULTS:
            raise HTTPException(422, f"fallo desconocido: {n}")
        return {"fault": switch.set(n), "faults": list(faults.FAULTS)}

    @app.get("/__replay/fault")
    def get_fault():
        return {"fault": switch.name, "faults": list(faults.FAULTS)}
    # Por delante del comodín de la web compilada (GET /{filepath:path}), que si no respondería con la portada.
    app.router.routes.insert(0, app.router.routes.pop())
    app.router.routes.insert(0, app.router.routes.pop())
    return switch


# Revisión V6 (encargo del PM): cupo de precalentado propio del replay. El de producción ([trending] prewarm_max, 30 al
# día) se agotaba con horas de pruebas y, caducado el fallo de una tarjeta, la portada decía «Sin análisis del motor
# por ahora» en vez de su motivo: las pasadas no eran reproducibles.
REPLAY_PREWARM_MAX = 10_000


def add_reset_switch(app, switch, prewarm_max: int = REPLAY_PREWARM_MAX):
    """`POST /__replay/reset`: deja el replay como recién arrancado (cola compartida, rivales, tendencias y su cupo de
    precalentado, y sin fallo activo), para que cada pasada de pruebas empiece igual. Lo llama el globalSetup de
    Playwright. Solo existe en el replay: main.py no lo tiene."""
    import peers
    import trending

    # El cupo propio sobrevive a cualquier reinicio de las tendencias (también al de los fallos: faults.reset_caches).
    production_reset = getattr(trending.reset, "__wrapped__", trending.reset)

    def trending_reset() -> None:
        production_reset()
        trending._limits["prewarm_max"] = prewarm_max
    trending_reset.__wrapped__ = production_reset
    trending.reset = trending_reset

    def reset() -> dict:
        switch.set(None)
        peers.reset()                    # también la cola compartida (analysis_queue.reset)
        trending.reset()
        return {"reset": True, "prewarm_max": trending._limits["prewarm_max"], "fault": switch.name}

    @app.post("/__replay/reset")
    def post_reset():
        return reset()

    app.router.routes.insert(0, app.router.routes.pop())
    reset()
    return reset


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--env", default="panel")
    ap.add_argument("--dir", help="carpeta de fixtures en vez de la del juego")
    ap.add_argument("--port", type=int, default=8767)
    # Rediseño E4 (Lighthouse): producción comprime en Cloudflare (content-encoding: br, comprobado el 2026-10-17);
    # para medir como allí, el replay puede comprimir con gzip. Solo herramienta de medida: main.py no cambia.
    ap.add_argument("--compress", action="store_true", help="gzip como la compresión de Cloudflare en producción")
    ap.add_argument("--prewarm-max", type=int, default=REPLAY_PREWARM_MAX,
                    help="cupo diario de precalentado de tendencias del replay (el de producción se agota con las pruebas)")
    args = ap.parse_args()
    logging.disable(logging.CRITICAL)
    # Portada rápida: el replay calcula sus tendencias al arrancar, pero sin el archivo de la última lista buena (el
    # de backend/.cache puede ser de datos reales).
    os.environ["FINANZER_PORTADA_SNAPSHOT"] = "0"
    import uvicorn
    import main as app_main

    base = args.dir or fb.fixtures_dir(args.env)
    with fb.replay(base, extra_dirs=(PEERS_DIR,)) as store:
        install(app_main, base, store)
        switch = add_fault_switch(app_main.app)
        add_reset_switch(app_main.app, switch, args.prewarm_max)
        app = app_main.app
        if args.compress:
            from starlette.middleware.gzip import GZipMiddleware
            app = GZipMiddleware(app, minimum_size=1000)
        uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
