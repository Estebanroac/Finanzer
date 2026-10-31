"""
Rediseño E5: datos de muestra del PDF nuevo, sin red y sin inventar nada.

  analysis(sym)   el análisis del replay congelado en el golden del panel (tests/golden/panel/<T>.json, trae display)
  prices(sym)     la serie con la forma de GET /api/v2/prices ({company, market, sector, as_of}) desde las series
                  grabadas en tests/fixtures/prices (cierre ajustado de Yahoo, 5 años; mercado ^GSPC y el ETF del
                  sector del propio juego de datos)

Lo que E2 aún no publica (display.extended, segmentos) no se fabrica: el PDF de muestra sale sin ello y lo dice.
"""
import json
import os
from typing import Any, Dict, Optional

import price_fixtures as pf
from settings import cfg

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
GOLDEN_PANEL = os.path.join(TESTS_DIR, "golden", "panel")


PANEL_FIXTURES = os.path.join(TESTS_DIR, "fixtures", "panel")


def capture_day(sym: str):
    """Fecha local de captura del juego panel (la que imprime el informe actual en sus golden)."""
    import datetime as _dt
    with open(os.path.join(PANEL_FIXTURES, sym, "metadata.json"), encoding="utf-8") as fh:
        return _dt.datetime.fromisoformat(json.load(fh)["captured_at_local"]).date()


def panel_symbols():
    """Tickers del golden del panel con informe (SPY se rechaza: sin display)."""
    out = []
    for f in sorted(os.listdir(GOLDEN_PANEL)):
        if f.endswith(".json"):
            with open(os.path.join(GOLDEN_PANEL, f), encoding="utf-8") as fh:
                if json.load(fh).get("display"):
                    out.append(f[:-5])
    return out


def inputs(sym: str) -> dict:
    """Lo que recibe build_pdf para `sym` (análisis, series y segmentos grabados, fecha de captura): en producción
    llega de las cachés; aquí se lee y se procesa de los fixtures."""
    return {"analysis": analysis(sym), "prices": prices(sym), "segments": segments_of(sym), "today": capture_day(sym)}


def build_from(inp: dict) -> bytes:
    """PDF nuevo determinista (reportlab invariant) de unas entradas ya cargadas."""
    from reportlab import rl_config
    from pdf_v2 import build_pdf
    old = rl_config.invariant
    rl_config.invariant = 1
    try:
        return build_pdf(inp["analysis"], inp["prices"], segments=inp["segments"], today=inp["today"])
    finally:
        rl_config.invariant = old


def build(sym: str) -> bytes:
    """PDF nuevo determinista de `sym` (reportlab invariant, fecha de captura, series grabadas)."""
    return build_from(inputs(sym))


SEGMENTS_FIXTURES = os.path.join(TESTS_DIR, "fixtures", "segments")


def segments_of(sym: str) -> Optional[Dict[str, Any]]:
    """Ingresos por segmento de `sym` desde su captura de EDGAR (tests/fixtures/segments, E2b), como los serviría
    /api/v2/segments; sin captura, None (el informe dice que el desglose aún no llegó)."""
    if not os.path.isfile(os.path.join(SEGMENTS_FIXTURES, f"{sym}.json")):
        return None
    import capture_segments
    import segments
    env = cfg("data.edgar.user_agent_env")
    old_env, old_fetcher = os.environ.get(env), segments.FETCHER
    os.environ[env] = os.environ.get(env) if "@" in (os.environ.get(env) or "") else "finanzer-tests tests@example.invalid"
    segments.FETCHER = capture_segments.replay_fetcher()
    try:
        segments.reset()
        return segments.build(sym)
    finally:
        segments.FETCHER = old_fetcher
        segments.reset()
        if old_env is None:
            os.environ.pop(env, None)
        else:
            os.environ[env] = old_env


def analysis(sym: str) -> Dict[str, Any]:
    with open(os.path.join(GOLDEN_PANEL, f"{sym}.json"), encoding="utf-8") as fh:
        return json.load(fh)


def _serie(symbol: Optional[str]) -> Dict[str, Any]:
    if not symbol:
        return {"symbol": None, "status": "sin_dato", "reason": "sin ETF de sector", "points": []}
    path = pf.series_file(symbol)
    if not os.path.isfile(path):
        return {"symbol": symbol, "status": "sin_dato", "reason": "sin serie grabada", "points": []}
    with open(path, encoding="utf-8") as fh:
        s = json.load(fh)
    pts = [{"t": t, "c": c, "v": v} for t, c, v in zip(s["dates"], s["close"], s["volume"]) if c is not None]
    return {"symbol": symbol, "status": "ok", "points": pts}


def prices(sym: str) -> Optional[Dict[str, Any]]:
    if not pf.available():
        return None
    meta = pf.metadata()
    info = (meta.get("tickers") or {}).get(sym) or {}
    company = _serie(sym)
    market = _serie(info.get("market_symbol") or meta.get("market_symbol"))
    sector = _serie(info.get("sector_etf"))
    as_of = company["points"][-1]["t"] if company["points"] else None
    return {"symbol": sym, "as_of": as_of, "company": company, "market": market, "sector": sector}
