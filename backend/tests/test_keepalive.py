"""Fase 6 (D6): el servicio se mantiene despierto en Render pidiéndose /api/health. Sin red."""
import keepalive as K


def test_does_not_start_outside_render(monkeypatch):
    monkeypatch.setattr(K, "_started", False)
    assert K.start({}) is False and K.state()["enabled"] in (False, True)


def test_starts_once_on_render(monkeypatch):
    started = []
    monkeypatch.setattr(K, "_started", False)
    monkeypatch.setattr(K.threading, "Thread", lambda **kw: type("T", (), {"start": lambda self: started.append(kw)})())
    env = {"RENDER_EXTERNAL_URL": "https://finanzer.app/"}
    assert K.start(env) is True and K.start(env) is False
    assert len(started) == 1 and started[0]["args"][0] == "https://finanzer.app/api/health" and started[0]["daemon"]


def test_failed_ping_is_recorded_not_raised(monkeypatch):
    def boom(*a, **k):
        raise OSError("sin red")
    monkeypatch.setattr(K.urllib.request, "urlopen", boom)
    K.ping_once("https://finanzer.app/api/health", 1.0)
    assert "OSError" in K.state()["last_error"]
