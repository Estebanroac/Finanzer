"""
Cola v4 (decisión del PM, 30-oct): mientras haya usuarios esperando o activos, el trabajo de fondo (rivales y
precalentado de tendencias) toma como mucho un turno de análisis a la vez, sin cambiar su prioridad. Con la máquina
tranquila, los rivales siguen de dos en dos (PDF rápido). «Activo»: un usuario con un turno, esperándolo o que lo
soltó hace menos de `user_active_s` (main._user_active_s: el p95 medido de un análisis sin caché, la pantalla de
carga).

La carga corta de la integración (§2.6) dio un pico de 440 MB y una espera de usuario de 6,0 s, las dos en el minuto con
más turnos de fondo.
"""
import threading
import time

import pytest

import main


@pytest.fixture
def turns(monkeypatch):
    monkeypatch.setattr(main, "_ANALYSIS_SLOTS", threading.BoundedSemaphore(4))
    main._reset_turns()
    yield monkeypatch
    main._reset_turns()


def _hold(user: bool, started: list, release: threading.Event, name: str):
    with main._slot(user):
        started.append(name)
        release.wait(5)


def _start(*args) -> threading.Thread:
    t = threading.Thread(target=_hold, args=args, daemon=True)
    t.start()
    return t


def _wait(pred, timeout=3.0):
    t0 = time.monotonic()
    while not pred():
        assert time.monotonic() - t0 < timeout
        time.sleep(0.01)


def test_with_a_user_active_background_takes_one_turn_at_a_time(turns):
    started, user_go, bg_go = [], threading.Event(), threading.Event()
    _start(True, started, user_go, "usuario")
    _wait(lambda: "usuario" in started)
    _start(False, started, bg_go, "fondo1")
    _start(False, started, bg_go, "fondo2")
    _wait(lambda: "fondo1" in started or "fondo2" in started)
    time.sleep(0.2)
    assert len([s for s in started if s.startswith("fondo")]) == 1      # el segundo espera, aunque hay turnos libres
    bg_go.set()
    _wait(lambda: len([s for s in started if s.startswith("fondo")]) == 2)   # en cuanto el primero suelta el suyo
    user_go.set()


def test_with_the_machine_quiet_background_takes_two_turns(turns):
    turns.setattr(main, "_user_active_s", lambda: 0.0)
    started, go = [], threading.Event()
    _start(False, started, go, "fondo1")
    _start(False, started, go, "fondo2")
    _wait(lambda: len(started) == 2)                                     # los dos rivales a la vez, como hasta ahora
    go.set()


def test_a_user_that_just_left_still_counts_as_active(turns):
    turns.setattr(main, "_user_active_s", lambda: 0.5)
    started, user_go, bg_go = [], threading.Event(), threading.Event()
    t = _start(True, started, user_go, "usuario")
    _wait(lambda: "usuario" in started)
    user_go.set()
    t.join(2)
    _start(False, started, bg_go, "fondo1")
    _start(False, started, bg_go, "fondo2")
    _wait(lambda: "fondo1" in started or "fondo2" in started)
    time.sleep(0.1)
    assert len([s for s in started if s.startswith("fondo")]) == 1      # dentro de la ventana: uno
    _wait(lambda: len([s for s in started if s.startswith("fondo")]) == 2, timeout=3)   # pasada la ventana: dos
    bg_go.set()


def test_background_never_delays_a_user_turn(turns):
    started, bg_go, user_go = [], threading.Event(), threading.Event()
    turns.setattr(main, "_user_active_s", lambda: 0.0)
    _start(False, started, bg_go, "fondo1")
    _start(False, started, bg_go, "fondo2")
    _wait(lambda: len(started) == 2)
    t0 = time.monotonic()
    _start(True, started, user_go, "usuario")
    _wait(lambda: "usuario" in started)
    assert time.monotonic() - t0 < 0.5                                   # quedan turnos: el usuario no espera
    bg_go.set()
    user_go.set()


def test_user_active_window_is_the_measured_p95_of_a_cold_analysis():
    from settings import cfg
    assert main._user_active_s() == cfg("data.web.loading_expected_s")
