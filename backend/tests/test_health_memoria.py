"""
E6 (31-oct): /api/health da la memoria del proceso (el plan gratuito de Render no la enseña): RSS actual y pico en MB y
el MALLOC_ARENA_MAX que ve el proceso. Solo números.
"""
import asyncio

import main


def test_health_reads_current_and_peak_rss_from_proc(tmp_path, monkeypatch):
    status = tmp_path / "status"
    status.write_text("Name:\tpython\nVmHWM:\t  471040 kB\nVmRSS:\t  389120 kB\nThreads:\t12\n", encoding="ascii")
    monkeypatch.setattr(main, "_PROC_STATUS", str(status))
    monkeypatch.setenv("MALLOC_ARENA_MAX", "2")
    mem = asyncio.run(main.health())["memory"]
    assert mem == {"rss_mb": 380.0, "peak_mb": 460.0, "malloc_arena_max": "2"}


def test_without_proc_the_peak_comes_from_getrusage(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "_PROC_STATUS", str(tmp_path / "no-existe"))
    monkeypatch.delenv("MALLOC_ARENA_MAX", raising=False)
    mem = asyncio.run(main.health())["memory"]
    assert mem["rss_mb"] is None and mem["malloc_arena_max"] is None
    assert 10 < mem["peak_mb"] < 4096                    # el proceso de los tests, en MB (no en bytes ni en kB)
