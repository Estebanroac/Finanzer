"""
Fixtures de las fuentes que el análisis consulta desde la fase 2b (SEC EDGAR y el calendario de resultados de
Finnhub): juego SEPARADO del panel, en tests/fixtures/f2b/.

    metadata.json                     fecha de la captura y resumen por ticker
    edgar/company_tickers.json        {TICKER: {cik, title}} de los tickers capturados
    edgar/submissions/CIK<10>.json    filings recientes del CIK (desde SINCE), con los campos que usa lib/sec_edgar.py
    edgar/companyfacts/CIK<10>.json   companyfacts reducido a los conceptos de sec_edgar.CONCEPTS (T4); .404 si
                                      la SEC respondió 404 (CIK sin estados XBRL)
    edgar/instances/<accn>.xml        instancia XBRL mínima (los mismos conceptos) de cada filing que companyfacts
                                      aún no traía el día de la captura (F2_PRECEDENCIA §3.1)
    edgar/covers/<accn>.htm           portada (R1) del 20-F de los ADR fuera de config/adr.toml (regla B; hoy ninguno)
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
# rediseño E2a (T3): campos de la ficha del emisor (sec_edgar.submission_profile)
PROFILE_KEYS = ("sic", "sicDescription", "stateOfIncorporation", "stateOfIncorporationDescription", "category", "website")
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
    # fase 4/7: la dirección del emisor (país para la región de su referencia, sec_edgar.issuer_country)
    # rediseño E2a (T3): la ciudad de la sede para la ficha (sec_edgar.submission_profile)
    addresses = {k: {x: v.get(x) for x in ("city", "stateOrCountry", "stateOrCountryDescription", "country", "countryCode",
                                           "isForeignLocation")} for k, v in (raw.get("addresses") or {}).items()}
    out = {"cik": raw.get("cik"), "name": raw.get("name"), "fiscalYearEnd": raw.get("fiscalYearEnd"),
           **{k: raw.get(k) for k in PROFILE_KEYS},
           "addresses": addresses,
           "filings": {"recent": {k: [r[k][i] for i in keep] for k in KEEP if k in r}}}
    _write(os.path.join(base, "edgar", "submissions", f"CIK{int(cik):010d}.json"), out)


FACTS_SINCE = "2019-01-01"   # el análisis usa como mucho 5 ejercicios (y el anterior para un TTM)


def save_facts_not_found(cik, base=F2B_DIR):
    path = os.path.join(base, "edgar", "companyfacts", f"CIK{int(cik):010d}.404")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("companyfacts: 404 en la captura\n")


def save_facts(cik, reduced, base=F2B_DIR):
    """companyfacts reducido, con los hechos que acaban desde FACTS_SINCE. Fase 3 (T7): los conceptos de la historia
    larga (sec_edgar.HISTORY, que clasifica y mide el ciclo con 10+ ejercicios) se guardan enteros, como los amplió
    tests/f3_extend_history_fixtures.py en el juego del panel."""
    import sec_edgar as edgar
    hist = {c for v in edgar.HISTORY.values() for c in (*v[1], *v[2])}
    out = {k: reduced[k] for k in ("cik", "entityName") if k in reduced}
    out["facts"] = {tx: {c: {"units": {u: [f for f in fs if c in hist or f["end"] >= FACTS_SINCE]
                                       for u, fs in node["units"].items()}}
                         for c, node in cs.items()} for tx, cs in reduced.get("facts", {}).items()}
    _write(os.path.join(base, "edgar", "companyfacts", f"CIK{int(cik):010d}.json"), out)


_NS = {"us-gaap": "http://fasb.org/us-gaap/2025", "ifrs-full": "https://xbrl.ifrs.org/taxonomy/2025-03-27/ifrs-full"}


def instance_xml(facts, segment=None):
    """Instancia XBRL mínima con los hechos (forma de companyfacts) que lee sec_edgar.parse_instance y, si se da
    `segment` = {axis, member, by_date: {fecha: {concepto: valor}}}, los saldos con esa dimensión (parse_segment)."""
    from xml.sax.saxutils import escape
    ctx, units, body = {}, {}, []
    seg_ctx = []
    for tx, cs in sorted(facts.get("facts", {}).items()):
        for c, node in sorted(cs.items()):
            for u, fs in sorted(node["units"].items()):
                uid = units.setdefault(u, f"u{len(units)}")
                for f in fs:
                    key = (f.get("start"), f["end"])
                    cid = ctx.setdefault(key, f"c{len(ctx)}")
                    body.append(f'<{tx}:{c} contextRef="{cid}" unitRef="{uid}" decimals="INF">{f["val"]}</{tx}:{c}>')
    if segment:
        uid = units.setdefault("USD", f"u{len(units)}")
        for i, (d, vals) in enumerate(sorted(segment["by_date"].items())):
            cid = f"s{i}"
            seg_ctx.append((cid, d))
            for c, v in sorted(vals.items()):
                body.append(f'<us-gaap:{c} contextRef="{cid}" unitRef="{uid}" decimals="INF">{v:.0f}</us-gaap:{c}>')
    head = ['<?xml version="1.0" encoding="utf-8"?>',
            '<xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance" xmlns:iso4217="http://www.xbrl.org/2003/iso4217" '
            'xmlns:xbrldi="http://xbrl.org/2006/xbrldi" xmlns:srt="http://fasb.org/srt/2025" '
            + " ".join(f'xmlns:{k}="{v}"' for k, v in _NS.items()) + ">"]
    for cid, d in seg_ctx:
        head.append(f'<xbrli:context id="{cid}"><xbrli:entity><xbrli:identifier scheme="http://www.sec.gov/CIK">0'
                    f'</xbrli:identifier><xbrli:segment><xbrldi:explicitMember dimension="srt:{segment["axis"]}">'
                    f'srt:{segment["member"]}</xbrldi:explicitMember></xbrli:segment></xbrli:entity><xbrli:period>'
                    f'<xbrli:instant>{d}</xbrli:instant></xbrli:period></xbrli:context>')
    for (st, en), cid in ctx.items():
        per = (f"<xbrli:startDate>{st}</xbrli:startDate><xbrli:endDate>{en}</xbrli:endDate>" if st
               else f"<xbrli:instant>{en}</xbrli:instant>")
        head.append(f'<xbrli:context id="{cid}"><xbrli:entity><xbrli:identifier scheme="http://www.sec.gov/CIK">0'
                    f'</xbrli:identifier></xbrli:entity><xbrli:period>{per}</xbrli:period></xbrli:context>')
    for u, uid in units.items():
        head.append(f'<xbrli:unit id="{uid}"><xbrli:measure>iso4217:{escape(u)}</xbrli:measure></xbrli:unit>')
    return "\n".join(head + body + ["</xbrli:xbrl>", ""])


def save_instance(accn, facts, base=F2B_DIR, segment=None):
    path = os.path.join(base, "edgar", "instances", f"{accn}.xml")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(instance_xml(facts, segment))


def save_cover(accn, html_text, base=F2B_DIR):
    path = os.path.join(base, "edgar", "covers", f"{accn}.htm")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(html_text)


def save_calendar(symbol, entries, base=F2B_DIR):
    _write(os.path.join(base, "finnhub_calendar", f"{symbol.upper()}.json"), entries)


def _load(path):
    if not os.path.isfile(path) and os.path.isfile(path + ".gz"):      # V4b: los rivales del replay, comprimidos
        import gzip
        with gzip.open(path + ".gz", "rt", encoding="utf-8") as fh:
            return json.load(fh)
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _exists(path):
    return os.path.isfile(path) or os.path.isfile(path + ".gz")


def _find(bases, *parts):
    """V4b: la ruta en la primera carpeta que la tenga (el juego y, detrás, la de los rivales del replay); si ninguna,
    la de la primera."""
    for b in bases:
        p = os.path.join(b, *parts)
        if _exists(p):
            return p
    return os.path.join(bases[0], *parts)


def _until(store):
    cur = store.current
    return str((store.meta.get(cur) or {}).get("captured_at_local") or "")[:10] or None


def edgar_fetcher(store, base=F2B_DIR, extra=()):
    """FETCHER de lib/sec_edgar.py para el replay. `extra`: carpetas de respaldo (V4b: tests/fixtures/peers/f2b)."""
    import sec_edgar as edgar
    bases = (base,) + tuple(e for e in extra if os.path.isdir(e))

    def fetch(url, _timeout):
        until = _until(store)
        if url == edgar.TICKERS_URL:
            table = {}
            for b in reversed(bases):           # el juego manda sobre la carpeta de respaldo
                p = os.path.join(b, "edgar", "company_tickers.json")
                if _exists(p):
                    table.update(_load(p))
            body = {str(i): {"ticker": t, "cik_str": v["cik"], "title": v.get("title")}
                    for i, (t, v) in enumerate(sorted(table.items()))}
            return json.dumps(body).encode(), 200
        name = url.rstrip("/").rsplit("/", 1)[-1]
        if "/Archives/edgar/data/" in url:
            acc = url.rstrip("/").rsplit("/", 2)[-2]
            accn = f"{acc[:10]}-{acc[10:12]}-{acc[12:]}"
            inst = _find(bases, "edgar", "instances", f"{accn}.xml")
            if name == "index.json":
                if not os.path.isfile(inst):
                    store.misses.append(f"edgar índice {accn}")
                    return None, 404
                return json.dumps({"directory": {"item": [{"name": f"{acc}_htm.xml"}]}}).encode(), 200
            if name == "R1.htm":
                path = _find(bases, "edgar", "covers", f"{accn}.htm")
            else:
                path = inst
            if not os.path.isfile(path):
                store.misses.append(f"edgar {name}")
                return None, 404
            with open(path, "rb") as fh:
                return fh.read(), 200
        if "/api/xbrl/companyfacts/" in url:
            path = _find(bases, "edgar", "companyfacts", name)
            if any(os.path.isfile(os.path.join(b, "edgar", "companyfacts", name.replace(".json", ".404"))) for b in bases):
                return None, 404            # la SEC respondió 404 en la captura (CIK sin estados XBRL: SPY)
            if not _exists(path):
                store.misses.append(f"edgar companyfacts {name}")
                return None, 404
            obj = _load(path)
            for cs in obj.get("facts", {}).values():
                for node in cs.values():
                    node["units"] = {u: [f for f in fs if until is None or f.get("filed", "") <= until]
                                     for u, fs in node["units"].items()}
            return json.dumps(obj).encode(), 200
        path = _find(bases, "edgar", "submissions", name)
        if not _exists(path):
            store.misses.append(f"edgar {name}")
            return None, 404
        obj = _load(path)
        r = obj["filings"]["recent"]
        keep = [i for i, d in enumerate(r.get("filingDate") or []) if until is None or d <= until]
        obj["filings"]["recent"] = {k: [v[i] for i in keep] for k, v in r.items()}
        return json.dumps(obj).encode(), 200
    return fetch


def calendar(store, base=F2B_DIR, extra=()):
    """Sustituto de finnhub_fallback.earnings_calendar para el replay."""
    bases = (base,) + tuple(e for e in extra if os.path.isdir(e))

    def cal(symbol, start, end):
        until = _until(store)
        # Rediseño E2a (T8): una consulta que mira más allá del día de la captura (próximos resultados) usa además el
        # calendario a futuro grabado con el ticker (tests/capture_finnhub_e2a.py), si lo hay. Las demás (aviso de
        # resultados publicados) terminan en la sesión de la serie y no cambian.
        ahead = []
        if until and end > until and store.current:
            rec = store.recorded_finnhub(store.current, "/calendar/earnings")
            if rec is not None:
                ahead = [e for e in (rec.get("response") or {}).get("earningsCalendar") or []
                         if start <= str(e.get("date")) <= end]
        path = _find(bases, "finnhub_calendar", f"{symbol.upper()}.json")
        if not _exists(path):
            if ahead:
                return ahead
            store.misses.append(f"calendario {symbol}")
            return None
        entries = _load(path)
        if entries is None:
            return ahead or None
        past = [e for e in entries if start <= str(e.get("date")) <= end and (until is None or str(e.get("date")) <= until)]
        return past + [e for e in ahead if str(e.get("date")) not in {str(x.get("date")) for x in past}]
    return cal
