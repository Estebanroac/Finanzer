"""
Fixtures de las fuentes que el análisis consulta desde la fase 2b (SEC EDGAR y el calendario de resultados de
Finnhub): juego SEPARADO del panel, en tests/fixtures/f2b/.

    metadata.json                     fecha de la captura y resumen por ticker
    edgar/company_tickers.json        {TICKER: {cik, title}} de los tickers capturados
    edgar/submissions/CIK<10>.json    filings recientes del CIK (desde SINCE), con los campos que usa lib/sec_edgar.py
    finnhub_calendar/<TICKER>.json    publicaciones de resultados (Finnhub /calendar/earnings)

Replay sin red: `edgar_fetcher(store)` sirve las respuestas de la SEC con los filings presentados hasta la fecha de
captura del ticker analizado; `calendar(store)` hace lo mismo con el calendario.
"""
import json
import os
import sys

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(TESTS_DIR)
for _p in (BACKEND_DIR, os.path.join(BACKEND_DIR, "lib"), TESTS_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

F2B_DIR = os.path.join(TESTS_DIR, "fixtures", "f2b")
SINCE = "2024-01-01"
KEEP = ("accessionNumber", "filingDate", "reportDate", "form", "items", "isXBRL", "primaryDocument")


def available(base=F2B_DIR):
    return os.path.isfile(os.path.join(base, "metadata.json"))


def _write(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, separators=(",", ":"), ensure_ascii=False, sort_keys=True)
        fh.write("\n")


def save_tickers(table, base=F2B_DIR):
    _write(os.path.join(base, "edgar", "company_tickers.json"), table)


def save_submissions(cik, raw, base=F2B_DIR):
    """Solo los filings desde SINCE y los campos que usa lib/sec_edgar.py (más el documento principal)."""
    r = (raw.get("filings") or {}).get("recent") or {}
    keep = [i for i, d in enumerate(r.get("filingDate") or []) if d >= SINCE]
    out = {"cik": raw.get("cik"), "name": raw.get("name"), "fiscalYearEnd": raw.get("fiscalYearEnd"),
           "filings": {"recent": {k: [r[k][i] for i in keep] for k in KEEP if k in r}}}
    _write(os.path.join(base, "edgar", "submissions", f"CIK{int(cik):010d}.json"), out)


def save_calendar(symbol, entries, base=F2B_DIR):
    _write(os.path.join(base, "finnhub_calendar", f"{symbol.upper()}.json"), entries)


def _load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _until(store):
    cur = store.current
    return str((store.meta.get(cur) or {}).get("captured_at_local") or "")[:10] or None


def edgar_fetcher(store, base=F2B_DIR):
    """FETCHER de lib/sec_edgar.py para el replay."""
    import sec_edgar as edgar

    def fetch(url, _timeout):
        until = _until(store)
        if url == edgar.TICKERS_URL:
            table = _load(os.path.join(base, "edgar", "company_tickers.json"))
            body = {str(i): {"ticker": t, "cik_str": v["cik"], "title": v.get("title")}
                    for i, (t, v) in enumerate(sorted(table.items()))}
            return json.dumps(body).encode(), 200
        name = url.rstrip("/").rsplit("/", 1)[-1]
        path = os.path.join(base, "edgar", "submissions", name)
        if not os.path.isfile(path):
            store.misses.append(f"edgar {name}")
            return None, 404
        obj = _load(path)
        r = obj["filings"]["recent"]
        keep = [i for i, d in enumerate(r.get("filingDate") or []) if until is None or d <= until]
        obj["filings"]["recent"] = {k: [v[i] for i in keep] for k, v in r.items()}
        return json.dumps(obj).encode(), 200
    return fetch


def calendar(store, base=F2B_DIR):
    """Sustituto de finnhub_fallback.earnings_calendar para el replay."""
    def cal(symbol, start, end):
        path = os.path.join(base, "finnhub_calendar", f"{symbol.upper()}.json")
        if not os.path.isfile(path):
            store.misses.append(f"calendario {symbol}")
            return None
        until = _until(store)
        entries = _load(path)
        if entries is None:
            return None
        return [e for e in entries if start <= str(e.get("date")) <= end and (until is None or str(e.get("date")) <= until)]
    return cal
