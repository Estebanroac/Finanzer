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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fixture_backend as fb  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--env", default="panel")
    ap.add_argument("--dir", help="carpeta de fixtures en vez de la del juego")
    ap.add_argument("--port", type=int, default=8767)
    args = ap.parse_args()
    logging.disable(logging.CRITICAL)
    import uvicorn
    from fastapi import HTTPException
    import main as app_main

    base = args.dir or fb.fixtures_dir(args.env)
    with fb.replay(base) as store:
        orig = app_main._compute_analysis

        def compute(symbol):
            sym = symbol.upper()
            if not os.path.isdir(os.path.join(base, sym)):
                raise HTTPException(404, f"{sym} no está en el juego de fixtures ({base})")
            store.current = sym
            store.load(sym)
            if store.meta[sym].get("finnhub", {}).get("participated"):
                os.environ["FINNHUB_API_KEY"] = "fixture-replay"
            else:
                os.environ.pop("FINNHUB_API_KEY", None)
            fb.reset_state()
            return orig(sym)

        app_main._compute_analysis = compute
        uvicorn.run(app_main.app, host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
