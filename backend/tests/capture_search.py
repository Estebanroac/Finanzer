"""
Rediseño E4 (Task 2): respuestas reales de la búsqueda de Yahoo para el replay y los tests del buscador de /v2
(tests/fixtures/search/quotes.json). Sin claves: la búsqueda de Yahoo es pública.

    cd finanzer_next/backend
    ../.venv313/bin/python tests/capture_search.py

Guarda por consulta solo lo que usa lib/search_v2.py (symbol, shortname, longname, quoteType, exchange).
`replay_quotes` devuelve un YAHOO_QUOTES que responde con lo capturado (o nada si la consulta no se capturó).
"""
import json
import os
import sys

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
for _p in (os.path.dirname(TESTS_DIR), os.path.join(os.path.dirname(TESTS_DIR), "lib"), TESTS_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

QUOTES_FILE = os.path.join(TESTS_DIR, "fixtures", "search", "quotes.json")
QUERIES = ["apple", "aapl", "appl", "microsoft", "coca", "jpm", "lvmh", "nvidia"]
KEEP = ("symbol", "shortname", "longname", "quoteType", "exchange")


def replay_quotes(path=QUOTES_FILE):
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)

    def quotes(query, count):
        return data.get(query.strip().lower(), [])[:count]
    return quotes


def main():
    import search_v2
    from settings import cfg
    out = {}
    for q in QUERIES:
        out[q] = [{k: x.get(k) for k in KEEP} for x in search_v2.yahoo_quotes(q, cfg("market.search.yahoo_count"))]
        print(q, [x["symbol"] for x in out[q]])
    os.makedirs(os.path.dirname(QUOTES_FILE), exist_ok=True)
    with open(QUOTES_FILE, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
