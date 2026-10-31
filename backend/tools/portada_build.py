"""
E6 · arranque en frío en Render: la instantánea de la portada, calculada en el build. En Render gratuito el disco se
borra en cada arranque, así que el servidor no encuentra `[trending] snapshot_file` y la portada se queda en
«calculando», sin tarjetas, hasta descargar el universo: ~3 min medidos en producción tras el despliegue del 31-oct
(70 s en local con la CPU a 0,1, tools/arranque_frio.py). Con este archivo creado en el build (build.sh, que deja sus
archivos en el servicio desplegado), el servidor sirve la lista al arrancar, con sus fechas, mientras la recalcula
(lib/trending.py, `restore`).

Hace lo mismo que el cálculo del servidor sin el precalentado de las tarjetas: las listas (`compute`) y las
mini-gráficas de su vista inicial, en el archivo. Nunca rompe el build: si Yahoo no responde o pasa de `--max-s`, sale
sin archivo (código 0) y el servidor calcula como antes.

    python backend/tools/portada_build.py            # desde la raíz del repositorio (build.sh)
"""
import argparse
import logging
import os
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(HERE)
sys.path.insert(0, BACKEND)
sys.path.insert(0, os.path.join(BACKEND, "lib"))


def build(path: str) -> int:
    from settings import cfg  # noqa: F401 — carga la config antes que los módulos de datos
    import trending

    trending.SNAPSHOT, trending.WARM_SPARKLINES = path, True
    expected = trending.last_closed_session()
    data = trending.compute(trending.FETCH_BATCH, session=expected)
    with trending._lock:
        trending._state.update(data=data, checked_for=expected, error=None, failed_at=None, computing=False)
    trending._after_lists(data)                     # mini-gráficas de la vista inicial y el archivo
    n = sum(len(cards) for groups in data["lists"].values() for cards in groups.values())
    return n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-s", type=float, default=240, help="tope: pasado, sin archivo")
    ap.add_argument("--out", help="ruta del archivo (por defecto, la de [trending] snapshot_file)")
    a = ap.parse_args()
    logging.basicConfig(level=logging.WARNING)
    from settings import cfg
    path = a.out or os.path.join(BACKEND, cfg("market.trending.snapshot_file"))
    if os.path.exists(path):
        os.remove(path)                             # nunca la de un build anterior
    res: dict = {}

    def run():
        try:
            res["n"] = build(path)
        except Exception as e:  # noqa: BLE001 — el build sigue; el servidor calcula al arrancar
            res["error"] = f"{type(e).__name__}: {e}"[:200]

    t0 = time.monotonic()
    th = threading.Thread(target=run, daemon=True)
    th.start()
    th.join(a.max_s)
    s = time.monotonic() - t0
    if th.is_alive() or "error" in res or not os.path.exists(path):
        if os.path.exists(path):
            os.remove(path)
        why = "tiempo agotado" if th.is_alive() else res.get("error", "sin archivo")
        print(f"portada: sin instantánea ({why}, {s:.0f} s); el servidor la calculará al arrancar")
        sys.stdout.flush()
        os._exit(0)                                 # sin esperar a hilos de descarga colgados
    print(f"portada: instantánea en {os.path.relpath(path, os.path.dirname(BACKEND))} "
          f"({res['n']} tarjetas, {os.path.getsize(path) // 1024} KB, {s:.0f} s)")
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    main()
