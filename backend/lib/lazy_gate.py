"""V6 (revisión de código y seguridad del PM, B8): puerta de las descargas de los endpoints perezosos de /v2 (serie de
la gráfica y segmentos). Tres cosas que les faltaban:

  · como mucho `concurrency` descargas a la vez (las demás esperan su turno);
  · una sola descarga por clave: quien llega mientras otra está en marcha espera su resultado, no la repite;
  · un fallo se recuerda `fail_ttl_s` (60 s): un símbolo que la fuente no da no se vuelve a pedir en cada consulta.

Los resultados buenos los guarda la caché de cada módulo (como antes); aquí solo los fallos, con tope (`max_failed`).
"""
import threading
import time
from typing import Any, Callable, Dict, Hashable, Tuple

import bounded


class Gate:
    def __init__(self, concurrency: int, fail_ttl_s: float, max_failed: int):
        self._sem = threading.BoundedSemaphore(concurrency)
        self._fail_ttl_s = fail_ttl_s
        self._max_failed = max_failed
        self._lock = threading.Lock()
        self._failed: Dict[Hashable, Tuple[float, Any]] = {}
        self._inflight: Dict[Hashable, Tuple[threading.Event, list]] = {}

    def run(self, key: Hashable, make: Callable[[], Any], failed: Callable[[Any], bool]) -> Any:
        """El resultado de `make()` para `key`: el fallo reciente si lo hay, el de la descarga en marcha si la hay o
        uno nuevo (con turno). `failed(res)` dice si el resultado es un fallo que se recuerda."""
        with self._lock:
            hit = self._failed.get(key)
            if hit and time.time() - hit[0] < self._fail_ttl_s:
                return hit[1]
            running = self._inflight.get(key)
            if running is None:
                running = (threading.Event(), [])
                self._inflight[key] = running
                mine = True
            else:
                mine = False
        done, box = running
        if not mine:
            done.wait()
            if box:
                return box[0]
            return self.run(key, make, failed)       # la descarga en marcha lanzó: se intenta de nuevo
        try:
            with self._sem:
                res = make()
            box.append(res)
            with self._lock:
                if failed(res):
                    bounded.put(self._failed, key, (time.time(), res), self._max_failed)
                else:
                    self._failed.pop(key, None)
            return res
        finally:
            with self._lock:
                self._inflight.pop(key, None)
            done.set()

    def reset(self) -> None:
        with self._lock:
            self._failed.clear()
