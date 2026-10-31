"""Rediseño E4 (Task 5): /v2 servida por el backend como la exporta Next (main._v2_file y la ruta serve_v2), con un
frontend/out sintético: portada en /v2, historia para /v2/{T}[/{capítulo}], archivos reales tal cual y nada fuera de
out/v2."""
import asyncio

import pytest
from fastapi import HTTPException

import main


@pytest.fixture
def out(tmp_path, monkeypatch):
    v2 = tmp_path / "v2"
    (v2 / "_").mkdir(parents=True)
    (v2 / "index.html").write_text("PORTADA", encoding="utf-8")
    (v2 / "index.txt").write_text("RSC-PORTADA", encoding="utf-8")
    (v2 / "_" / "index.html").write_text("HISTORIA", encoding="utf-8")
    (tmp_path / "secreto.txt").write_text("NO", encoding="utf-8")
    monkeypatch.setattr(main, "_frontend_dir", str(tmp_path))
    return tmp_path


def test_file_resolution(out):
    f = lambda p: main._v2_file(str(out), p)          # noqa: E731
    assert f("").endswith("v2/index.html") and f("/").endswith("v2/index.html")
    assert f("AAPL").endswith("v2/_/index.html") and f("AAPL/valor").endswith("v2/_/index.html")
    assert f("BRK.B/").endswith("v2/_/index.html")
    assert f("index.txt").endswith("v2/index.txt")
    # Recorrido de rutas (verificación de la v4, V5): 404, ni el archivo ni la historia. uvicorn ya ha decodificado
    # %2e%2e y %2f cuando llega aquí.
    for bad in ("../secreto.txt", "../../backend/main.py", "AAPL/../../secreto.txt", "..", "AAPL/..", "..\\secreto.txt"):
        assert f(bad) is None, bad
    assert f("%2e%2e/secreto.txt").endswith("v2/_/index.html")       # sin decodificar no es un recorrido: un símbolo raro


def test_without_build(tmp_path):
    assert main._v2_file(str(tmp_path), "AAPL") is None


def _serve(path):
    r = asyncio.run(main.serve_v2(path))
    with open(r.path, encoding="utf-8") as fh:
        return fh.read(), r.media_type


def test_routes(out):
    assert _serve("") == ("PORTADA", "text/html")
    assert _serve("AAPL") == ("HISTORIA", "text/html") and _serve("AAPL/valor")[0] == "HISTORIA"
    assert _serve("index.txt")[0] == "RSC-PORTADA"
    with pytest.raises(HTTPException) as e:
        asyncio.run(main.serve_v2("../secreto.txt"))
    assert e.value.status_code == 404
    paths = [r.path for r in main.app.routes if hasattr(r, "path")]
    assert paths.index("/v2/{path:path}") < len(paths) and "/api/v2/search" in paths
    assert paths.index("/api/v2/search") < paths.index("/v2/{path:path}")      # la API no la tapa la ruta /v2


def test_404_without_build(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "_frontend_dir", str(tmp_path))
    with pytest.raises(HTTPException) as e:
        asyncio.run(main.serve_v2("AAPL"))
    assert e.value.status_code == 404


def test_traversal_over_real_http(out, tmp_path):
    """Verificación de la v4 (V5): peticiones crudas (sin normalizar la ruta, como un atacante) a un uvicorn real con
    el out/ sintético: cada intento de salir de out/v2 responde 404 sin servir nada; las rutas buenas, su HTML."""
    import http.client
    import socket
    import threading
    import uvicorn
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    server = uvicorn.Server(uvicorn.Config(main.app, host="127.0.0.1", port=port, log_level="error"))
    th = threading.Thread(target=server.run, daemon=True)
    th.start()
    try:
        for _ in range(100):
            if server.started:
                break
            threading.Event().wait(0.05)

        def get(path):
            c = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
            c.request("GET", path)
            r = c.getresponse()
            return r.status, r.read().decode("utf-8", "replace")
        assert get("/v2/AAPL") == (200, "HISTORIA") and get("/v2/AAPL/valor") == (200, "HISTORIA")
        assert get("/v2") == (200, "PORTADA")
        for bad in ("/v2/%2e%2e/secreto.txt", "/v2/..%2fsecreto.txt", "/v2/..%2f..%2fbackend/main.py",
                    "/v2/%2e%2e/%2e%2e/backend/main.py", "/v2/AAPL/%2e%2e/%2e%2e/secreto.txt", "/v2/../secreto.txt"):
            st, body = get(bad)
            assert st == 404 and "NO" != body and "HISTORIA" not in body and "import" not in body, (bad, st, body)
    finally:
        server.should_exit = True
        th.join(timeout=5)
