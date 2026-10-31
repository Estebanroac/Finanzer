"""F6 (F6_DIAGNOSTICO §2): el análisis no bloquea el bucle de eventos y respeta el tope de simultáneos. Sin red."""
import asyncio
import json
import threading
import time

import main


async def _get(path):
    """GET mínimo sobre la app ASGI (sin httpx): (status, cuerpo JSON)."""
    out = {"status": None, "body": b""}
    sent = [False]

    async def receive():
        if not sent[0]:
            sent[0] = True
            return {"type": "http.request", "body": b"", "more_body": False}
        await asyncio.sleep(3600)

    async def send(msg):
        if msg["type"] == "http.response.start":
            out["status"] = msg["status"]
        elif msg["type"] == "http.response.body":
            out["body"] += msg.get("body", b"")
    scope = {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": "GET", "scheme": "http",
             "path": path, "raw_path": path.encode(), "query_string": b"", "headers": [], "server": ("t", 80),
             "client": ("c", 1), "root_path": ""}
    await main.app(scope, receive, send)
    return out["status"], json.loads(out["body"] or b"null")


def test_health_answers_while_an_analysis_runs(monkeypatch):
    started = threading.Event()

    def slow(symbol):
        started.set()
        time.sleep(1.0)
        return {"symbol": symbol}
    monkeypatch.setattr(main, "_compute_analysis", slow)

    async def run():
        # El tiempo cuenta desde que se lanza el análisis: con el bucle bloqueado, /api/health espera a que termine.
        t0 = time.perf_counter()
        job = asyncio.create_task(_get("/api/analysis/AAA"))
        await asyncio.sleep(0.05)
        h = await _get("/api/health")
        dt = time.perf_counter() - t0
        r = await job
        return h[0], dt, r[1]

    code, dt, body = asyncio.run(run())
    assert code == 200 and dt < 0.5, f"/api/health tardó {dt:.2f} s con un análisis en curso"
    assert body == {"symbol": "AAA"}


def test_concurrent_analyses_are_capped(monkeypatch):
    cap = main._ANALYSIS_SLOTS._initial_value
    live, peak, lock = [0], [0], threading.Lock()

    def slow(symbol):
        with lock:
            live[0] += 1
            peak[0] = max(peak[0], live[0])
        time.sleep(0.2)
        with lock:
            live[0] -= 1
        return {"symbol": symbol}
    monkeypatch.setattr(main, "_compute_analysis", slow)

    async def run():
        t0 = time.perf_counter()
        rs = await asyncio.gather(*(_get(f"/api/analysis/S{i}") for i in range(cap * 2)))
        return [r[0] for r in rs], time.perf_counter() - t0

    codes, dt = asyncio.run(run())
    assert codes == [200] * (cap * 2)
    assert peak[0] == cap                       # en paralelo hasta el tope, no más
    assert dt < 0.2 * cap * 2 * 0.75            # y claramente menos que en serie


def test_shared_cache_is_thread_safe():
    """Revisión de F6, hallazgo 1: SimpleCache sin lock lanzaba "dictionary changed size during iteration" con 4
    análisis a la vez (miles de veces en una prueba de 4 hilos)."""
    import threading
    import data_fetcher
    c = data_fetcher.SimpleCache(max_entries=50)
    errors = []

    def work(k):
        try:
            for i in range(3000):
                c.set(f"{k}:{i % 80}", i, ttl_minutes=1)
                c.get(f"{(k + 1) % 4}:{i % 80}")
        except Exception as e:
            errors.append(e)
    ts = [threading.Thread(target=work, args=(k,)) for k in range(4)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert not errors


def test_edgar_budget_does_not_pay_for_the_queue():
    """Revisión de F6, hallazgo 2: la espera detrás de otro análisis no gasta el presupuesto de EDGAR."""
    import threading
    import time
    import sec_edgar
    b = sec_edgar.Budget(seconds=1.0)
    sem = threading.BoundedSemaphore(1)
    sem.acquire()
    threading.Timer(0.3, sem.release).start()
    with b.turn(sem):
        pass
    assert b.queued_s >= 0.25 and b.left() > 0.9


def test_queue_wait_is_counted_while_waiting():
    """V6 (B2): la espera del turno cuenta en `queued_s` mientras se espera (no al conseguirlo): quien espera el
    resultado (collect) alarga su plazo a la vez."""
    import threading
    import time
    import sec_edgar
    from settings import cfg
    b = sec_edgar.Budget(seconds=1.0)
    sem = threading.BoundedSemaphore(1)
    sem.acquire()
    seen = []

    def waiter():
        with b.turn(sem):
            pass
    t = threading.Thread(target=waiter)
    t.start()
    time.sleep(0.4 + 2 * cfg("data.edgar.turn_poll_s"))
    seen.append(b.queued_s)                      # aún esperando
    sem.release()
    t.join(5)
    assert seen[0] >= 0.4 and b.queued_s >= seen[0]


def test_queue_wait_beyond_the_forgiven_queue_gives_up(monkeypatch):
    """V6 (B2): si la cola perdonada (`queue_max_s`) se agota antes del turno, EDGAR no está para este análisis y se
    dice, en vez de seguir esperando a un resultado que ya nadie recoge."""
    import threading
    import pytest
    import sec_edgar
    import settings
    real = settings.cfg
    monkeypatch.setattr(sec_edgar, "cfg", lambda k: 0.3 if k == "data.edgar.queue_max_s" else
                        (0.05 if k == "data.edgar.turn_poll_s" else real(k)))
    b = sec_edgar.Budget(seconds=1.0)
    sem = threading.BoundedSemaphore(1)
    sem.acquire()
    with pytest.raises(sec_edgar.Unavailable, match="EDGAR ocupado"):
        with b.turn(sem):
            pass
    sem.release()


def test_segments_do_not_take_the_analysis_parse_turn(monkeypatch):
    """V6 (B2): con una lectura de segmentos lenta en curso, el análisis consigue su turno de lecturas grandes sin
    esperar (antes compartían el único turno de _parsing() y el análisis perdía EDGAR)."""
    import threading
    import time
    import sec_edgar
    monkeypatch.setattr(sec_edgar, "_parse_lock", None)
    monkeypatch.setattr(sec_edgar, "_segments_lock", None)
    inside, release = threading.Event(), threading.Event()

    def slow_segments_parse():
        with sec_edgar.Budget(10.0).turn(sec_edgar._segments_parsing()):
            inside.set()
            release.wait(5)
    t = threading.Thread(target=slow_segments_parse)
    t.start()
    assert inside.wait(5)
    b = sec_edgar.Budget(seconds=1.0)
    t0 = time.monotonic()
    with b.turn(sec_edgar._parsing()):
        waited = time.monotonic() - t0
    release.set()
    t.join(5)
    assert waited < 0.1 and b.queued_s < 0.1


def test_segments_parse_uses_its_own_turn():
    import inspect
    import segments
    src = inspect.getsource(segments)
    assert "edgar._segments_parsing()" in src and "edgar._parsing()" not in src
