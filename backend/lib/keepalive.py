"""
Fase 6 (D6: sin plan de pago): Render gratuito apaga el servicio tras 15 minutos sin tráfico entrante y el primer
análisis tardaba 30–50 s más en despertarlo. El propio servicio pide su /api/health por la URL pública cada
`interval_s` (por debajo de los 15 minutos): la petición entra por el proxy de Render como tráfico y el servicio no
se duerme. Sin coste: Render gratuito da 750 horas de instancia al mes y un mes tiene como mucho 744 (si hay otros
servicios gratuitos en el mismo espacio de trabajo, comparten esas horas).

Solo en Render (variable RENDER_EXTERNAL_URL, que Render define); en local y en los tests no arranca. Estado en
/api/health (`keepalive`). Un workflow programado de GitHub haría lo mismo desde fuera, pero el token de git de la
máquina del usuario no tiene el permiso `workflow`.
"""
import os
import threading
import time
import urllib.request
from typing import Any, Dict

from settings import cfg

_state: Dict[str, Any] = {"enabled": False, "url": None, "last_ok": None, "last_error": None, "pings": 0}
_lock = threading.Lock()
_started = False


def state() -> Dict[str, Any]:
    with _lock:
        return {k: _state[k] for k in ("enabled", "last_ok", "last_error", "pings")}


def ping_once(url: str, timeout: float) -> None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "finanzer-keepalive/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            r.read(256)
        with _lock:
            _state.update(last_ok=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), last_error=None)
            _state["pings"] += 1
    except Exception as e:  # nunca rompe el servicio: se registra y se reintenta en el siguiente turno
        with _lock:
            _state["last_error"] = f"{type(e).__name__}: {e}"[:200]


def _loop(url: str, interval: float, timeout: float) -> None:
    time.sleep(cfg("data.keepalive.first_delay_s"))
    while True:
        ping_once(url, timeout)
        time.sleep(interval)


def start(env=None) -> bool:
    """Arranca el hilo una vez si estamos en Render y está activado. Devuelve si arrancó."""
    global _started
    env = os.environ if env is None else env
    C = cfg("data.keepalive")
    base = (env.get("RENDER_EXTERNAL_URL") or "").rstrip("/")
    with _lock:
        if _started or not C["enabled"] or not base:
            return False
        _started = True
        _state.update(enabled=True, url=base + "/api/health")
    threading.Thread(target=_loop, args=(base + "/api/health", C["interval_s"], C["timeout_s"]),
                     name="keepalive", daemon=True).start()
    return True
