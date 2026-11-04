"""Logotipos de las empresas (lib/logos.py, GET /api/v2/logo/{símbolo} y `logo` del análisis). Sin red: fuentes
inyectadas, PNG generados aquí con Pillow y la captura del replay (tests/fixtures/logos)."""
import io
import threading
import time

import pytest
from fastapi import HTTPException

import finnhub_fallback
import logos
from settings import cfg


def png(size=200, color=(200, 30, 30), mode="RGB"):
    from PIL import Image
    out = io.BytesIO()
    Image.new(mode, (size, size) if isinstance(size, int) else size, color).save(out, format="PNG")
    return out.getvalue()


@pytest.fixture
def fresh(monkeypatch):
    logos.reset()
    yield monkeypatch
    logos.reset()


def fake(table, calls=None, delay=0.0):
    """FETCH de prueba: {símbolo: (PNG, fuente) | None | Exception}."""
    def fetch(sym):
        if calls is not None:
            calls.append(sym)
        if delay:
            time.sleep(delay)
        v = table.get(sym)
        if isinstance(v, Exception):
            raise v
        return v
    return fetch


# ───────────────────────── qué es un logotipo aceptable ─────────────────────────

def test_png_size_reads_the_header():
    assert logos.png_size(png((120, 80))) == (120, 80)
    assert logos.png_size(b"<html>404</html>") is None
    assert logos.png_size(b"") is None


def test_acceptable_only_square_pngs_of_reasonable_size():
    assert logos.acceptable(png(200))
    assert not logos.acceptable(None)
    assert not logos.acceptable(b"GIF89a" + b"\0" * 40)                 # no es PNG
    assert not logos.acceptable(png(16))                                # un favicon, no un logotipo
    assert not logos.acceptable(png((300, 100)))                        # apaisado: no cabe en la placa cuadrada
    big = png(200) + b"\0" * cfg("data.logos.max_bytes")
    assert not logos.acceptable(big)


# ───────────────────────── caché, versión y una sola descarga ─────────────────────────

def test_logo_is_cached_with_a_content_version(fresh):
    calls = []
    data = png()
    fresh.setattr(logos, "FETCH", fake({"AAPL": (data, "Parqet")}, calls))
    done, a = logos.get("aapl")
    assert done and a.data == data and a.source == "Parqet"
    assert len(a.version) == cfg("data.logos.version_chars")
    _, b = logos.get("AAPL")
    assert b == a and calls == ["AAPL"]                                 # la segunda, de la caché


def test_missing_logo_is_remembered(fresh):
    calls = []
    fresh.setattr(logos, "FETCH", fake({}, calls))
    assert logos.get("ZZZZ") == (True, None)
    assert logos.get("ZZZZ") == (True, None)
    assert calls == ["ZZZZ"]


def test_source_failure_is_retried_after_fail_ttl(fresh):
    calls = []
    fresh.setattr(logos, "FETCH", fake({"AAPL": logos.SourceError("timeout")}, calls))
    assert logos.get("AAPL") == (True, None)
    assert logos.get("AAPL") == (True, None) and calls == ["AAPL"]
    # caducado el fallo (`fail_ttl_s`), se vuelve a preguntar
    with logos._lock:
        exp, v = logos._cache["AAPL"]
        logos._cache["AAPL"] = (time.monotonic() - 1, v)
    logos.get("AAPL")
    assert calls == ["AAPL", "AAPL"]
    assert cfg("data.logos.fail_ttl_s") < cfg("data.logos.miss_ttl_s") < cfg("data.logos.ttl_s")


def test_unexpected_error_never_leaves_anyone_waiting(fresh):
    fresh.setattr(logos, "FETCH", fake({"AAPL": RuntimeError("boom")}))
    assert logos.get("AAPL", wait_s=1) == (True, None)
    assert logos._inflight == {}


def test_concurrent_requests_download_once(fresh):
    calls = []
    fresh.setattr(logos, "FETCH", fake({"NFLX": (png(), "Parqet")}, calls, delay=0.2))
    got = []
    threads = [threading.Thread(target=lambda: got.append(logos.get("NFLX"))) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert calls == ["NFLX"]
    assert len(got) == 8 and all(done and logo is not None for done, logo in got)


def test_invalid_symbol_is_not_fetched(fresh):
    calls = []
    fresh.setattr(logos, "FETCH", fake({}, calls))
    assert logos.get("../etc") == (True, None)
    assert logos.get("A" * 11) == (True, None)
    assert calls == []


def test_memory_is_bounded_by_entries_and_bytes(fresh):
    data = png()
    fresh.setattr(logos, "FETCH", lambda s: (data, "Parqet"))
    fresh.setattr(logos, "_limits", lambda: {**cfg("data.logos"), "cache_max_entries": 5,
                                             "cache_max_bytes": len(data) * 3})
    for i in range(10):
        logos.get(f"S{i}")
    assert len(logos._cache) == 3 and logos._bytes[0] == len(data) * 3
    assert list(logos._cache) == ["S7", "S8", "S9"]                     # salen las más antiguas
    fresh.setattr(logos, "_limits", lambda: {**cfg("data.logos"), "cache_max_entries": 2})
    logos.get("S10")
    assert list(logos._cache) == ["S9", "S10"] and logos._bytes[0] == len(data) * 2


def test_real_limits_fit_in_render_memory():
    """Render va justo (≈ 315 MB en uso): la caché de logotipos, como mucho 4 MB."""
    assert cfg("data.logos.cache_max_bytes") <= 4 * 1024 * 1024


# ───────────────────────── las fuentes: Parqet primero, Finnhub para lo que falte ─────────────────────────

def test_parqet_first_and_finnhub_not_asked(fresh):
    asked = []
    fresh.setattr(logos, "_parqet", lambda s: png())
    fresh.setattr(logos, "_finnhub", lambda s: asked.append(s))
    data, src = logos.fetch_sources("AAPL")
    assert src == "Parqet" and logos.acceptable(data) and asked == []


def test_finnhub_when_parqet_has_none(fresh):
    fresh.setattr(logos, "_parqet", lambda s: None)
    fresh.setattr(logos, "_finnhub", lambda s: png())
    assert logos.fetch_sources("MRVL")[1] == "Finnhub"


def test_unacceptable_parqet_image_falls_through(fresh):
    fresh.setattr(logos, "_parqet", lambda s: png(16))                  # un favicon
    fresh.setattr(logos, "_finnhub", lambda s: None)
    assert logos.fetch_sources("AAPL") is None


def test_source_error_only_if_no_source_gave_a_logo(fresh):
    def down(s):
        raise logos.SourceError("timeout")
    fresh.setattr(logos, "_parqet", down)
    fresh.setattr(logos, "_finnhub", lambda s: None)
    with pytest.raises(logos.SourceError):
        logos.fetch_sources("AAPL")
    fresh.setattr(logos, "_finnhub", lambda s: png())
    assert logos.fetch_sources("AAPL")[1] == "Finnhub"


class _Resp:
    def __init__(self, body, status=200):
        self.body, self.status = body, status

    def read(self, n=-1):
        return self.body if n < 0 else self.body[:n]

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_parqet_url_uses_yahoo_symbol_and_size(fresh):
    seen = []

    def opener(req, timeout):
        seen.append(req.full_url)
        return _Resp(png())
    fresh.setattr(logos, "urlopen", opener)
    assert logos._parqet("BRK-B")
    assert seen == [f"https://assets.parqet.com/logos/symbol/BRK-B?format=png&size={cfg('data.logos.size_px')}"]


def test_parqet_404_is_no_logo_and_timeout_is_failure(fresh):
    from urllib.error import HTTPError

    def not_found(req, timeout):
        raise HTTPError(req.full_url, 404, "Not Found", {}, None)
    fresh.setattr(logos, "urlopen", not_found)
    assert logos._parqet("ZZZZ") is None

    def slow(req, timeout):
        raise TimeoutError()
    fresh.setattr(logos, "urlopen", slow)
    with pytest.raises(logos.SourceError):
        logos._parqet("AAPL")


def _finnhub_env(monkeypatch, profile, image=None, opened=None):
    monkeypatch.setenv("FINNHUB_API_KEY", "test")
    calls = []
    monkeypatch.setattr(finnhub_fallback, "paced_get", lambda path, params, interval, max_wait_s=None:
                        calls.append((path, params)) or profile)

    def opener(req, timeout):
        (opened if opened is not None else []).append(req.full_url)
        return _Resp(image if image is not None else png(1000))
    monkeypatch.setattr(logos, "urlopen", opener)
    return calls


def test_finnhub_logo_is_downloaded_encoded_and_shrunk(fresh):
    opened = []
    calls = _finnhub_env(fresh, {"logo": "https://static2.finnhub.io/file/publicdatany/finnhubimage/stock_logo/NOVO B.CO.png"},
                         opened=opened)
    data = logos._finnhub("NVO")
    assert calls == [("/stock/profile2", {"symbol": "NVO"})]
    assert opened == ["https://static2.finnhub.io/file/publicdatany/finnhubimage/stock_logo/NOVO%20B.CO.png"]
    n = cfg("data.logos.size_px")
    assert logos.png_size(data) == (n, n) and logos.acceptable(data)


def test_finnhub_class_share_uses_its_dot(fresh):
    calls = _finnhub_env(fresh, {})
    assert logos._finnhub("BRK-B") is None
    assert calls == [("/stock/profile2", {"symbol": "BRK.B"})]


def test_finnhub_not_asked_outside_us_or_without_key(fresh):
    calls = _finnhub_env(fresh, {"logo": "https://static2.finnhub.io/x.png"})
    assert logos._finnhub("MC.PA") is None                             # el plan gratuito responde 403 fuera de EE. UU.
    fresh.delenv("FINNHUB_API_KEY")
    assert logos._finnhub("AAPL") is None
    assert calls == []


def test_finnhub_image_only_from_its_own_store(fresh):
    opened = []
    _finnhub_env(fresh, {"logo": "https://evil.example.com/logo.png"}, opened=opened)
    assert logos._finnhub("AAPL") is None and opened == []
    _finnhub_env(fresh, {"logo": "http://static2.finnhub.io/AAPL.png"}, opened=opened)
    assert logos._finnhub("AAPL") is None and opened == []


def test_finnhub_busy_is_a_failure_not_a_miss(fresh):
    fresh.setenv("FINNHUB_API_KEY", "test")
    fresh.setattr(finnhub_fallback, "paced_get", lambda *a, **k: finnhub_fallback.BUSY)
    with pytest.raises(logos.SourceError):
        logos._finnhub("AAPL")


def test_finnhub_hourly_budget(fresh):
    calls = _finnhub_env(fresh, {})
    fresh.setattr(logos, "_limits", lambda: {**cfg("data.logos"), "finnhub_max_per_hour": 2})
    for s in ("AAA", "BBB", "CCC", "DDD"):
        logos._finnhub(s)
    assert [p["symbol"] for _, p in calls] == ["AAA", "BBB"]


def test_paced_get_spaces_calls_and_reports_busy(monkeypatch):
    sleeps, got = [], []
    monkeypatch.setattr(finnhub_fallback, "_get", lambda path, params: got.append(path) or {"ok": 1})
    monkeypatch.setattr(finnhub_fallback.time, "sleep", lambda s: sleeps.append(s))
    monkeypatch.setattr(finnhub_fallback, "_pace_next", [0.0])
    assert finnhub_fallback.paced_get("/a", {}, 1.5) == {"ok": 1}
    assert finnhub_fallback.paced_get("/b", {}, 1.5) == {"ok": 1}       # espera su turno
    assert len(sleeps) == 1 and 1.0 < sleeps[0] <= 1.5
    assert finnhub_fallback.paced_get("/c", {}, 1.5, max_wait_s=0.5) is finnhub_fallback.BUSY
    assert got == ["/a", "/b"]


# ───────────────────────── en los datos de la acción y por HTTP ─────────────────────────

def test_meta_for_the_analysis(fresh):
    data = png()
    fresh.setattr(logos, "FETCH", fake({"AAPL": (data, "Parqet")}))
    m = logos.meta("AAPL")
    v = logos.get("AAPL")[1].version
    assert m == {"url": f"/api/v2/logo/AAPL?v={v}", "source": "Parqet"}
    assert logos.meta("ZZZZ") is None


def test_meta_does_not_hold_the_analysis(fresh):
    fresh.setattr(logos, "FETCH", fake({"AAPL": (png(), "Parqet")}, delay=0.5))
    fresh.setattr(logos, "_limits", lambda: {**cfg("data.logos"), "meta_wait_s": 0.05})
    t = time.monotonic()
    assert logos.meta("AAPL") == {"url": "/api/v2/logo/AAPL", "source": None}
    assert time.monotonic() - t < 0.4


def test_prefetch_then_meta_downloads_once(fresh):
    calls = []
    fresh.setattr(logos, "FETCH", fake({"NFLX": (png(), "Parqet")}, calls, delay=0.1))
    logos.prefetch("NFLX")
    assert logos.meta("NFLX")["source"] == "Parqet"
    assert calls == ["NFLX"]


class _Req:
    def __init__(self, headers=None):
        self.headers = headers or {}


def _endpoint(sym, v=None, headers=None):
    import asyncio
    import main
    return asyncio.run(main.logo_v2_endpoint(sym, _Req(headers), v=v))


def test_endpoint_serves_png_with_cache_headers(fresh):
    data = png()
    fresh.setattr(logos, "FETCH", fake({"AAPL": (data, "Parqet")}))
    r = _endpoint("aapl")
    v = logos.get("AAPL")[1].version
    assert r.status_code == 200 and r.body == data and r.media_type == "image/png"
    assert r.headers["cache-control"] == f"public, max-age={cfg('data.logos.browser_max_age_s')}"
    assert r.headers["etag"] == f'"{v}"' and r.headers["x-logo-source"] == "Parqet"
    assert _endpoint("AAPL", v=v).headers["cache-control"] == "public, max-age=31536000, immutable"
    assert _endpoint("AAPL", headers={"if-none-match": f'"{v}"'}).status_code == 304


def test_endpoint_without_logo_is_a_short_lived_204(fresh):
    fresh.setattr(logos, "FETCH", fake({}))
    r = _endpoint("ZZZZ")
    assert r.status_code == 204 and r.body == b""
    assert r.headers["cache-control"] == f"public, max-age={cfg('data.logos.fail_ttl_s')}"


def test_endpoint_rejects_invalid_symbols(fresh):
    with pytest.raises(HTTPException) as e:
        _endpoint("a/b")
    assert e.value.status_code == 422


def test_analysis_carries_its_logo_without_touching_the_cached_one(fresh):
    import main
    fresh.setattr(logos, "FETCH", fake({"AAPL": (png(), "Parqet")}))
    cached = {"symbol": "AAPL", "profile": {"name": "Apple"}}
    out = main._with_logo(cached)
    assert out["logo"]["source"] == "Parqet" and out["profile"] == cached["profile"]
    assert "logo" not in cached
    fresh.setattr(logos, "meta", lambda s: (_ for _ in ()).throw(RuntimeError("boom")))
    assert main._with_logo(cached) is cached                           # un fallo del logotipo no rompe el análisis


def test_replay_capture_serves_recorded_logos():
    import capture_logos
    fetch = capture_logos.replay_fetcher()
    data, src = fetch("NFLX")
    assert src in ("Parqet", "Finnhub") and logos.acceptable(data)
    assert fetch("NO-ESTA") is None


def test_endpoint_waits_without_blocking_and_gives_up_uncached(fresh):
    """La fuente no contesta a tiempo: 204 sin caché del navegador (la próxima vez puede tenerlo)."""
    fresh.setattr(logos, "FETCH", fake({"AAPL": (png(), "Parqet")}, delay=0.5))
    import main
    fresh.setattr(main, "cfg", lambda path: {**cfg(path), "endpoint_wait_s": 0.1} if path == "data.logos" else cfg(path))
    r = _endpoint("AAPL")
    assert r.status_code == 204 and r.headers["cache-control"] == "no-store"
    time.sleep(0.6)
    assert _endpoint("AAPL").status_code == 200                         # ya en caché
