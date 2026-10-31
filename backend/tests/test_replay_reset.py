"""
Revisión V6 (encargo del PM): `POST /__replay/reset` deja el replay como recién arrancado y con un cupo de precalentado
propio, para que las pasadas de pruebas (V1, e2e) sean reproducibles aunque el replay lleve horas arrancado.
"""
import time

from fastapi import FastAPI

import analysis_queue as AQ
import faults
import peers
import replay_server
import trending


def _route(app, path, method="POST"):
    return next(r for r in app.routes if getattr(r, "path", None) == path and method in r.methods)


def test_reset_clears_queue_peers_trending_and_fault_and_sets_its_own_quota():
    app, switch = FastAPI(), faults.Switch()
    try:
        replay_server.add_reset_switch(app, switch, prewarm_max=1234)
        assert trending._limits["prewarm_max"] == 1234
        # horas de pruebas: cupo del día gastado, fallos y clasificaciones guardados, un fallo activo
        trending._state.update(prewarm_day="2026-10-18", prewarmed={f"S{i}" for i in range(40)})
        AQ._state["TSLA"] = {"status": "fallo", "t": time.time() - 10_000, "reason": "TSLA: sin fixtures en el replay"}
        peers._rankings["AAPL"] = (time.time(), {"rivals": ["DELL"], "industry": "x", "note": None})
        switch.set(next(iter(faults.FAULTS)))
        out = _route(app, "/__replay/reset").endpoint()
        assert out == {"reset": True, "prewarm_max": 1234, "fault": None}
        assert trending._state["prewarmed"] == set() and trending._limits["prewarm_max"] == 1234
        assert "TSLA" not in AQ._state and peers._rankings == {} and switch.name is None
        # quitar un fallo reinicia las tendencias (faults.reset_caches): el cupo del replay se mantiene
        switch.set(next(iter(faults.FAULTS)))
        switch.set(None)
        assert trending._limits["prewarm_max"] == 1234
    finally:
        switch.set(None)
        trending.reset = getattr(trending.reset, "__wrapped__", trending.reset)
        peers.reset()
        trending.reset()


def test_replay_quota_is_larger_than_production():
    from settings import cfg
    assert replay_server.REPLAY_PREWARM_MAX > cfg("market.trending.prewarm_max")
