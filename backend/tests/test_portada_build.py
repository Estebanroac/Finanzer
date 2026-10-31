"""
E6 · arranque en frío en Render (tools/portada_build.py): la instantánea de la portada, calculada en el build, es la que
el servidor recupera al arrancar (lib/trending.py, `restore`): «listo» en la primera petición y, si es de la misma
sesión, sin volver a descargar el universo.
"""
import importlib.util
import os

import pytest

import sparklines
import trending
from test_trending import SERIES, fetcher, frame, fresh  # noqa: F401 — fixture

_spec = importlib.util.spec_from_file_location(
    "portada_build", os.path.join(os.path.dirname(__file__), "..", "tools", "portada_build.py"))
portada_build = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(portada_build)


def _cards(resp):
    """Las tarjetas sin el estado del motor (cambia con el precalentado, no con el archivo)."""
    return {p: {k: [{f: v for f, v in c.items() if f != "engine"} for c in cs] for k, cs in g.items()}
            for p, g in resp["data"]["lists"].items()}


@pytest.fixture
def offline(fresh):  # noqa: F811
    # build() asigna SNAPSHOT y WARM_SPARKLINES como el servidor: se restauran al terminar (no pasan a otros tests)
    fresh.setattr(trending, "SNAPSHOT", None)
    fresh.setattr(trending, "WARM_SPARKLINES", False)
    fresh.setattr(trending, "_universe_symbols", lambda: list(SERIES))
    fresh.setattr(trending, "last_closed_session", lambda now=None: "2026-10-16")
    fresh.setattr(sparklines, "get", lambda *a, **k: {})
    fresh.setattr(sparklines, "wait_refreshes", lambda *a, **k: None)
    fresh.setattr(sparklines, "dump", lambda *a, **k: {})
    fresh.setattr(sparklines, "load", lambda *a, **k: None)
    return fresh


def test_the_build_snapshot_is_served_at_once_after_boot_without_downloading_again(offline, tmp_path):
    calls = []
    offline.setattr(trending, "FETCH_BATCH", fetcher(frame(SERIES), calls))
    path = str(tmp_path / "portada.json")
    assert portada_build.build(path) > 0 and os.path.exists(path)
    assert len(calls) == 1
    built = _cards(trending.get("1D"))
    trending.reset()                                    # el servidor recién desplegado: nada en memoria
    offline.setattr(trending, "SNAPSHOT", path)
    assert trending.restore() is True
    first = trending.get("1D")
    assert first["status"] == "listo" and first["refreshing"] is False
    assert _cards(first) == built
    assert len(calls) == 1                              # misma sesión: el servidor no descarga el universo


def test_without_yahoo_the_build_leaves_no_snapshot(offline, tmp_path):
    def down(symbols):
        raise ConnectionError("sin red")
    offline.setattr(trending, "FETCH_BATCH", down)
    path = str(tmp_path / "portada.json")
    with pytest.raises(Exception):
        portada_build.build(path)
    assert not os.path.exists(path)                     # el servidor calculará al arrancar, como antes
