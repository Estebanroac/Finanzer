"""
Rediseño E4 (Task 2): búsqueda del buscador de /v2 (portada y barra general). La misma lógica que /api/search de la
web actual (base local primero, después la búsqueda de Yahoo), con la bolsa de cada resultado (nombre legible de
lib/exchanges.py) y solo acciones (un ETF o un fondo no se analiza: llevarían a un error). /api/search no cambia.

La bolsa sale de la búsqueda de Yahoo (su `exchange`); un resultado de la base local que Yahoo no devuelve va sin
bolsa (`exchange: null`; la portada lo muestra sin ella, nunca con un hueco). YAHOO_QUOTES es inyectable (tests y
replay: tests/capture_search.py).
"""
import logging
from typing import Any, Callable, Dict, List

import exchanges
from settings import cfg

logger = logging.getLogger(__name__)


def yahoo_quotes(query: str, count: int) -> List[Dict[str, Any]]:
    """Las `quotes` de la búsqueda de Yahoo (mismos parámetros que main._yahoo_search)."""
    import yf_adapter as _ya
    r = _ya._live_session().get("https://query2.finance.yahoo.com/v1/finance/search", params={
        "q": query, "lang": "en-US", "region": "US", "quotesCount": count, "newsCount": 0, "listsCount": 0,
        "enableFuzzyQuery": True, "quotesQueryId": "tss_match_phrase_query"}, timeout=cfg("market.search.timeout_s"))
    if r.status_code != 200:
        return []
    return r.json().get("quotes", []) or []


YAHOO_QUOTES: Callable[[str, int], List[Dict[str, Any]]] = yahoo_quotes


def search(query: str) -> Dict[str, Any]:
    """{results: [{ticker, name, exchange}]}: como mucho `limit`, la base local primero (coincidencia exacta de ticker
    arriba) y después Yahoo; sin repetidos."""
    from stock_database import search_stocks
    S = cfg("market.search")
    q = (query or "").strip()
    if not q:
        return {"results": []}
    try:
        quotes = [x for x in YAHOO_QUOTES(q, S["yahoo_count"]) if x.get("quoteType") == "EQUITY" and x.get("symbol")]
    except Exception as e:  # sin Yahoo, la base local sigue respondiendo
        logger.debug("[SEARCH_V2] Yahoo: %s", type(e).__name__)
        quotes = []
    yahoo = {x["symbol"].upper(): x for x in quotes}
    out: Dict[str, Dict[str, Any]] = {}
    for ticker, name, _score in search_stocks(q, limit=S["limit"]):
        t = ticker.upper()
        out[t] = {"ticker": t, "name": name, "exchange": exchanges.name((yahoo.get(t) or {}).get("exchange"))}
    for t, x in yahoo.items():
        if len(out) >= S["limit"]:
            break
        if t not in out:
            out[t] = {"ticker": t, "name": x.get("longname") or x.get("shortname") or t,
                      "exchange": exchanges.name(x.get("exchange"))}
    results = list(out.values())
    results.sort(key=lambda r: r["ticker"] != q.upper())          # el ticker exacto, el primero
    return {"results": results[:S["limit"]]}
