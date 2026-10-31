"""
E6 · paso 2 (docs/superpowers/plans/2026-10-18-rediseno-e6-migracion.md): las rutas de transición. La v4 pasa a ser la
web principal y la actual queda de respaldo durante la observación:

  · `/` → la portada de la v4 (out/v2/index.html), servida en la misma URL;
  · `/{T}` → redirección temporal (307) a `/v2/{T}`: la historia lee el símbolo de la ruta /v2/{T};
  · `/v2/{T}…` → la v4, como hasta ahora;
  · `/stock/{T}` → la web actual (los enlaces compartidos siguen funcionando), con el aviso «Prueba la nueva versión →»;
  · `/clasica` → la portada actual;
  · `/api/pdf/{T}` (el PDF actual) se mantiene.

Vuelta atrás: revertir el commit de estas rutas. Como test_v2_serving.py, se llama a los manejadores directamente.
"""
import asyncio
import os

import pytest
from fastapi.responses import FileResponse, RedirectResponse

import main


def _route(path: str):
    return next(r for r in main.app.routes if getattr(r, "path", None) == path)


@pytest.fixture
def out(tmp_path, monkeypatch):
    d = tmp_path / "out"
    (d / "v2" / "_").mkdir(parents=True)
    (d / "stock").mkdir()
    for rel in ("index.html", "v2/index.html", "v2/_/index.html", "stock/index.html", "robots.txt", "manifest.webmanifest"):
        (d / rel).write_text(rel, encoding="utf-8")
    monkeypatch.setattr(main, "_frontend_dir", str(d))
    return d


def _served(resp) -> str:
    assert isinstance(resp, FileResponse), resp
    return os.path.relpath(resp.path, main._frontend_dir)


def _get(path: str):
    """La respuesta de la ruta que atiende `path` (como la elige el enrutador: la primera que encaja)."""
    from starlette.routing import Match
    scope = {"type": "http", "path": path, "method": "GET", "root_path": ""}
    for r in main.app.routes:
        m, child = r.matches(scope)
        if m == Match.FULL:
            return asyncio.run(r.endpoint(**child.get("path_params", {})))
    raise AssertionError(f"ninguna ruta para {path}")


def test_root_serves_the_v4_home_at_the_same_url(out):
    assert _served(_get("/")) == "v2/index.html"
    assert "HEAD" in _route("/").methods              # el enrutador de Next comprueba la URL canónica con un HEAD


def test_a_ticker_at_the_root_goes_to_its_v4_story(out):
    for path, to in (("/AAPL", "/v2/AAPL"), ("/BRK-B", "/v2/BRK-B"), ("/MC.PA", "/v2/MC.PA"), ("/aapl", "/v2/aapl")):
        r = _get(path)
        assert isinstance(r, RedirectResponse) and r.status_code == 307 and r.headers["location"] == to, path


def test_v4_routes_stay_as_they_are(out):
    assert _served(_get("/v2")) == "v2/index.html"
    assert _served(_get("/v2/AAPL")) == "v2/_/index.html" and _served(_get("/v2/AAPL/valor")) == "v2/_/index.html"


def test_the_current_web_stays_as_backup(out):
    assert _served(_get("/clasica")) == "index.html" and _served(_get("/clasica/")) == "index.html"
    assert _served(_get("/stock/AAPL")) == "stock/index.html"


def test_real_files_at_the_root_are_still_files(out):
    assert _served(_get("/robots.txt")) == "robots.txt"
    assert _served(_get("/manifest.webmanifest")) == "manifest.webmanifest"   # marca


def test_anything_else_gets_the_v4_home_not_the_old_one(out):
    """Una ruta desconocida de varias partes, o algo que no es un símbolo: la portada de la v4 (antes, la actual)."""
    for path in ("/algo/raro", "/no_es_un_simbolo_valido_123", "/clasica/otra"):
        assert _served(_get(path)) == "v2/index.html", path


def test_traversal_at_the_root_never_serves_files_or_redirects(out):
    for path in ("/../../backend/main.py", "/../secreto"):
        r = _get(path)
        assert not isinstance(r, RedirectResponse), path
        assert _served(r) == "v2/index.html", path


def test_the_current_pdf_endpoint_stays():
    assert _route("/api/pdf/{symbol}") is not None and _route("/api/v2/pdf/{symbol}") is not None
