"""Cierre de la v4 (V3, yahoo_down en la portada): los sondeos de la web van por debajo del keep-alive de uvicorn. Con
el mismo intervalo (5 s y 5 s), el servidor cerraba la conexión inactiva justo cuando el sondeo la reutilizaba; Chromium
reintenta, WebKit no y pierde la petición («The network connection was lost»)."""
import uvicorn

from settings import cfg

KEEP_ALIVE_S = uvicorn.Config(app=None).timeout_keep_alive


def test_polls_are_below_server_keep_alive():
    for key in ("market.trending.poll_s", "market.peers.poll_s"):
        assert cfg(key) < KEEP_ALIVE_S, f"{key} = {cfg(key)} s: tiene que ser menor que el keep-alive ({KEEP_ALIVE_S} s)"
