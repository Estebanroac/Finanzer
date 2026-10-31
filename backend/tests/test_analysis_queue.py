"""Rediseño E4 (Task 1): cola de análisis compartida (lib/analysis_queue.py) — rivales pedidos por un usuario (`user`)
antes que el precalentado de las tendencias (`prewarm`), un solo hilo y nunca dos análisis del mismo símbolo."""
import json
import os
import threading
import time

import pytest

import analysis_queue as AQ

GOLDEN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "golden", "panel")


class Engine:
    """Análisis falso (el golden de AAPL con otro símbolo). `first` retiene el primer análisis hasta `release`."""

    def __init__(self, delay=0.01, fail=()):
        self.calls, self.delay, self.fail = [], delay, set(fail)
        self.running, self.overlap = set(), []
        self.started, self.release = threading.Event(), threading.Event()
        self.release.set()
        self._lk = threading.Lock()

    def __call__(self, sym):
        with self._lk:
            if sym in self.running:
                self.overlap.append(sym)
            self.running.add(sym)
            self.calls.append(sym)
        self.started.set()
        self.release.wait(5)
        time.sleep(self.delay)
        with self._lk:
            self.running.discard(sym)
        if sym in self.fail:
            raise RuntimeError(f"{sym} sin datos")
        with open(os.path.join(GOLDEN, "AAPL.json"), encoding="utf-8") as fh:
            return {**json.load(fh), "symbol": sym}


@pytest.fixture
def q(monkeypatch):
    AQ.reset()
    yield monkeypatch
    AQ.reset()


def wait(pred, timeout=5.0):
    t0 = time.monotonic()
    while not pred():
        assert time.monotonic() - t0 < timeout
        time.sleep(0.01)


def test_user_request_jumps_ahead_of_all_pending_prewarm(q):
    eng = Engine()
    eng.release.clear()
    q.setattr(AQ, "ANALYZE", eng)
    AQ.request("P0", AQ.PREWARM)                   # el hilo lo toma y queda retenido
    eng.started.wait(2)
    for i in range(1, 6):
        assert AQ.request(f"P{i}", AQ.PREWARM)["status"] == "en_cola"
    assert AQ.request("RIVAL", AQ.USER)["status"] == "en_cola"
    eng.release.set()
    wait(lambda: len(eng.calls) == 7)
    assert eng.calls[:2] == ["P0", "RIVAL"]        # el rival adelanta a los cinco del precalentado
    assert eng.calls[2:] == [f"P{i}" for i in range(1, 6)]


def test_prewarm_symbol_requested_by_a_user_moves_up_and_runs_once(q):
    eng = Engine()
    eng.release.clear()
    q.setattr(AQ, "ANALYZE", eng)
    AQ.request("P0", AQ.PREWARM)
    eng.started.wait(2)
    for s in ("P1", "P2", "DELL"):
        AQ.request(s, AQ.PREWARM)
    assert AQ.request("DELL", AQ.USER)["status"] == "en_cola"
    eng.release.set()
    wait(lambda: AQ.stats()["user"] == AQ.stats()["prewarm"] == 0 and len(eng.calls) == 4
         and AQ.peek("P2") is not None and AQ.peek("P2")["status"] == "listo")
    time.sleep(0.05)
    assert eng.calls == ["P0", "DELL", "P1", "P2"]  # DELL sube y su entrada antigua no lo repite
    assert AQ.peek("DELL")["status"] == "listo"


def test_never_two_analyses_of_the_same_symbol(q):
    eng = Engine(delay=0.02)
    q.setattr(AQ, "ANALYZE", eng)
    threads = [threading.Thread(target=AQ.request, args=(s, p))
               for _ in range(5) for s in ("AAA", "BBB", "CCC") for p in (AQ.USER, AQ.PREWARM)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    wait(lambda: all((AQ.peek(s) or {}).get("status") == "listo" for s in ("AAA", "BBB", "CCC")))
    time.sleep(0.05)
    assert sorted(eng.calls) == ["AAA", "BBB", "CCC"] and eng.overlap == []


def test_states_and_shared_summary(q):
    eng = Engine(delay=0.2)
    q.setattr(AQ, "ANALYZE", eng)
    assert AQ.peek("MSFT") is None and AQ.cached("MSFT") is None
    assert AQ.request("MSFT", AQ.PREWARM)["status"] == "en_cola"
    wait(lambda: AQ.peek("MSFT")["status"] == "analizando")
    wait(lambda: AQ.peek("MSFT")["status"] == "listo")
    s = AQ.peek("MSFT")["summary"]
    assert s["symbol"] == "MSFT" and set(s["quality"]) == {"score", "level"} and set(s["price_score"]) == {"score",
                                                                                                           "level"}
    assert AQ.cached("MSFT") is s
    assert AQ.request("MSFT", AQ.USER)["status"] == "listo" and eng.calls == ["MSFT"]   # la misma caché para todos


def test_failure_is_remembered(q):
    q.setattr(AQ, "ANALYZE", Engine(fail={"BAD"}))
    AQ.request("BAD", AQ.PREWARM)
    wait(lambda: (AQ.peek("BAD") or {}).get("status") == "fallo")
    assert "BAD sin datos" in AQ.peek("BAD")["reason"]
    assert AQ.request("BAD", AQ.USER)["status"] == "fallo"            # no se reintenta antes de fail_ttl_s


def test_each_priority_has_its_own_bound(q):
    eng = Engine()
    eng.release.clear()
    q.setattr(AQ, "ANALYZE", eng)
    q.setitem(AQ._limits, "max_queue", 2)
    q.setitem(AQ._limits, "max_prewarm_queue", 1)
    AQ.request("X0", AQ.USER)
    eng.started.wait(2)
    # V6 (B7): por encima del tope, "en_cola" con `retry` (sin estado: se reintenta), no "fallo"
    st = [AQ.request(s, AQ.USER) for s in ("U1", "U2", "U3")]
    assert [x.get("retry", False) for x in st] == [False, False, True] and st[2]["reason"] == AQ.FULL
    assert {x["status"] for x in st} == {"en_cola"} and AQ.peek("U3") is None
    assert [AQ.request(s, AQ.PREWARM).get("retry", False) for s in ("P1", "P2")] == [False, True]
    eng.release.set()


def test_waits_while_users_wait_for_a_turn(q):
    eng = Engine()
    busy = {"on": True}
    q.setattr(AQ, "ANALYZE", eng)
    q.setattr(AQ, "BUSY", lambda: busy["on"])
    q.setitem(AQ._limits, "busy_wait_s", 0.02)
    AQ.request("P1", AQ.PREWARM)
    time.sleep(0.2)
    assert eng.calls == []
    busy["on"] = False
    wait(lambda: eng.calls == ["P1"])


def test_jobs_share_the_thread_and_the_priority(q):
    eng = Engine()
    eng.release.clear()
    q.setattr(AQ, "ANALYZE", eng)
    order = []
    AQ.request("P0", AQ.PREWARM)
    eng.started.wait(2)
    AQ.request("P1", AQ.PREWARM)
    assert AQ.submit("RANK", lambda stop: order.append(("job", list(eng.calls))), AQ.USER)
    eng.release.set()
    wait(lambda: order and len(eng.calls) == 2)
    assert order == [("job", ["P0"])]                                 # el trabajo del usuario, antes que P1


def test_no_thread_until_first_request(q):
    assert AQ.stats()["running"] is False
    q.setattr(AQ, "ANALYZE", Engine())
    AQ.request("AAPL", AQ.PREWARM)
    assert AQ.stats()["running"] is True and all(t.daemon for t in AQ._workers)


def test_expired_failures_are_purged(q):
    """V6 (B10): un fallo caducado sale de `_state` (antes quedaba uno por símbolo que falló alguna vez)."""
    import time as _t
    q.setattr(AQ, "ANALYZE", lambda s: (_ for _ in ()).throw(RuntimeError("x")))
    AQ._state["OLD"] = {"status": "fallo", "t": _t.time() - AQ._limits["fail_ttl_s"] - 1, "reason": "x"}
    AQ._state["NEW"] = {"status": "fallo", "t": _t.time(), "reason": "x"}
    AQ.request("ANY", AQ.USER)
    assert "OLD" not in AQ._state and "NEW" in AQ._state


def test_summary_says_when_it_was_made(q):
    """V6 (B13): cada resumen (rival o tarjeta) lleva `as_of`, la hora UTC de su análisis."""
    import datetime as dt
    import json
    import os
    golden = os.path.join(os.path.dirname(os.path.abspath(__file__)), "golden", "panel", "AAPL.json")
    q.setattr(AQ, "ANALYZE", lambda s: json.load(open(golden, encoding="utf-8")))
    s, why = AQ.summary_for("AAPL")
    assert why is None and s["as_of"].endswith("Z")
    assert abs((dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(s["as_of"].replace("Z", "+00:00")))
               .total_seconds()) < 60


# ─────────────────────────── PDF rápido: un segundo hilo para lo que mira el usuario ───────────────────────────
def test_two_rivals_are_analysed_at_the_same_time(q):
    """Los rivales (prioridad `user`) se analizan de dos en dos: el segundo hilo de la cola solo toma trabajos
    `user`. Antes, uno detrás de otro (5 rivales ≈ 8,6 s en frío con HD)."""
    both = threading.Barrier(2, timeout=5)                 # solo pasa si los dos análisis están en marcha a la vez
    seen = []

    def analyze(sym):
        seen.append(sym)
        both.wait()
        return Engine()(sym)
    q.setattr(AQ, "ANALYZE", analyze)
    AQ.request("R1", AQ.USER)
    AQ.request("R2", AQ.USER)
    wait(lambda: all((AQ.peek(s) or {}).get("status") == "listo" for s in ("R1", "R2")))
    assert sorted(seen) == ["R1", "R2"]


def test_the_trends_prewarm_stays_one_at_a_time(q):
    """El precalentado de tendencias (prioridad `prewarm`) sigue de uno en uno (memoria de Render): el segundo hilo no
    lo toma."""
    eng = Engine(delay=0.05)
    q.setattr(AQ, "ANALYZE", eng)
    at_once = []
    real = eng.__call__

    def analyze(sym):
        with eng._lk:
            at_once.append(len(eng.running))
        return real(sym)
    q.setattr(AQ, "ANALYZE", analyze)
    for i in range(4):
        AQ.request(f"P{i}", AQ.PREWARM)
    wait(lambda: all((AQ.peek(f"P{i}") or {}).get("status") == "listo" for i in range(4)))
    assert max(at_once) == 0                                # nunca otro análisis en marcha al empezar uno


def test_two_workers_never_analyse_the_same_symbol_twice(q):
    eng = Engine(delay=0.02)
    q.setattr(AQ, "ANALYZE", eng)
    threads = [threading.Thread(target=AQ.request, args=(s, AQ.USER)) for _ in range(6) for s in ("AAA", "BBB", "CCC")]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    wait(lambda: all((AQ.peek(s) or {}).get("status") == "listo" for s in ("AAA", "BBB", "CCC")))
    time.sleep(0.05)
    assert sorted(eng.calls) == ["AAA", "BBB", "CCC"] and eng.overlap == []
