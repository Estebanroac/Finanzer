"""
Rediseño E2b (Task 2): fixtures sin red de los ingresos por segmento (tests/fixtures/segments/<T>.json).

    cd finanzer_next/backend
    SEC_EDGAR_USER_AGENT="…" ../.venv313/bin/python tests/capture_segments.py AAPL JPM O NEE XOM PLTR RIVN BCS MC.PA

Descarga en vivo lo que lee segments.build (tabla de tickers, submissions, índice del filing, instancia y linkbase de
etiquetas) y guarda SOLO lo que usa: la fila del ticker, los anuales de submissions, del índice la instancia y el
linkbase (nombre y tamaño), de la instancia las unidades, los contextos de duración sin dimensión o con un eje de la
config y los hechos de los conceptos de ingresos, y del linkbase la etiqueta estándar de cada miembro. Después
comprueba que el replay da el mismo resultado que la descarga en vivo. El User-Agent no se escribe en ningún sitio.

`replay_fetcher(dir)` sirve las respuestas guardadas (las de todos los tickers a la vez) a segments.FETCHER.
"""
import datetime as dt
import glob
import io
import json
import os
import sys
import time
import xml.etree.ElementTree as ET

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(TESTS_DIR)
for _p in (BACKEND_DIR, os.path.join(BACKEND_DIR, "lib"), TESTS_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import sec_edgar as edgar  # noqa: E402
import segments  # noqa: E402
from settings import cfg  # noqa: E402

FIX_DIR = os.path.join(TESTS_DIR, "fixtures", "segments")
X = "{http://www.xbrl.org/2003/instance}"
XD = "{http://xbrl.org/2006/xbrldi}"


def replay_fetcher(base=FIX_DIR):
    resp = {}
    tickers = {}
    for path in sorted(glob.glob(os.path.join(base, "*.json"))):
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        for url, r in data["responses"].items():
            if url == edgar.TICKERS_URL:
                tickers.update({f"{data['symbol']}:{k}": v for k, v in json.loads(r["body"]).items()})
            else:
                resp[url] = r

    def fetch(url, timeout):
        if url == edgar.TICKERS_URL:
            return json.dumps(tickers).encode(), 200
        r = resp.get(url)
        if r is None:
            return None, 404
        return (r["body"].encode("utf-8") if r["body"] is not None else None), r["code"]
    return fetch


# ───────────────────────── reducción de lo descargado ─────────────────────────

def _reduce_tickers(body, symbol):
    key = symbol.upper().replace(".", "-")
    return {k: v for k, v in json.loads(body).items() if str(v.get("ticker")).upper() == key}


def _reduce_submissions(body):
    raw = json.loads(body)
    cols = ("form", "filingDate", "reportDate", "accessionNumber", "isXBRL")

    def keep(block):
        idx = [i for i, f in enumerate(block.get("form") or []) if f in edgar.ANNUAL_FORMS]
        return {c: [block[c][i] for i in idx] for c in cols if c in block}
    if "filings" in raw:
        return {"cik": raw.get("cik"), "filings": {"recent": keep(raw["filings"].get("recent") or {}),
                                                    "files": raw["filings"].get("files") or []}}
    return keep(raw)                          # página antigua: las columnas en la raíz


def _reduce_index(body):
    items = json.loads(body)["directory"]["item"]
    return {"directory": {"item": [{"name": i["name"], "size": i.get("size")} for i in items
                                   if str(i.get("name", "")).endswith(("_htm.xml", "_lab.xml"))]}}


def _reduce_instance(xml):
    S = cfg("market.segments")
    axes = set(S["axes"]) | set(S["geographic_axes"])
    geo_axes = set(S["geographic_axes"])
    concepts = set(S["revenue_concepts"]) | set(S["extension_total_concepts"])
    neutral = {tuple(n.split("=", 1)) for n in S["neutral_members"]}
    elims = {tuple(n.split("=", 1)) for n in S["elimination_members"]}
    redundant = set(S["redundant_axes"])
    ctxs, units, facts = {}, [], []
    depth = 0
    for ev, el in ET.iterparse(io.BytesIO(xml), events=("start", "end")):
        if ev == "start":
            depth += 1
            continue
        depth -= 1
        if depth != 1:
            continue
        if el.tag == X + "context":
            p = el.find(X + "period")
            if p.find(X + "startDate") is not None and el.find(f".//{XD}typedMember") is None:
                mem = [(m.get("dimension", "").split(":")[-1], (m.text or "").split(":")[-1])
                       for m in el.iter(XD + "explicitMember")]
                mem = [d for d in mem if d not in neutral]
                mem = [d for d in mem if not (d[0] in redundant and any(d[1] == o[1] for o in mem if o != d))]
                el_ = [d for d in mem if d in elims]
                rest = [d for d in mem if d not in elims]
                bus = [d for d in rest if d[0] in axes - geo_axes]
                geo = [d for d in rest if d[0] in geo_axes]
                # lo que clasifica sec_edgar.parse_segments: total, un eje, segmento × zona, eliminaciones
                if (not mem or (len(mem) == 1 and mem[0][0] in axes)
                        or (not el_ and len(rest) == 2 and len(bus) == 1 and len(geo) == 1)
                        or (len(el_) == 1 and len(bus) == 1 and len(rest) == 1 + len(geo) and len(geo) <= 1)):
                    ctxs[el.get("id")] = ET.tostring(el, encoding="unicode")
        elif el.tag == X + "unit":
            units.append(ET.tostring(el, encoding="unicode"))
        elif el.tag.startswith("{") and el.get("contextRef") and el.tag.split("}")[1] in concepts:
            facts.append((el.get("contextRef"), ET.tostring(el, encoding="unicode")))
        el.clear()
    used = {c for c, _ in facts if c in ctxs}
    body = "".join(units) + "".join(ctxs[c] for c in sorted(used)) + "".join(f for c, f in facts if c in used)
    return ('<?xml version="1.0" encoding="utf-8"?><xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance">'
            + body + "</xbrli:xbrl>")


def _reduce_labels(names):
    locs, labs, arcs = [], [], []
    for i, (qn, text) in enumerate(sorted(names.items())):
        pfx, loc = qn.split(":", 1)
        locs.append(f'<link:loc xlink:type="locator" xlink:href="x.xsd#{pfx}_{loc}" xlink:label="l{i}"/>')
        t = text.replace("&", "&amp;").replace("<", "&lt;")
        labs.append(f'<link:label xlink:type="resource" xlink:label="r{i}" '
                    f'xlink:role="http://www.xbrl.org/2003/role/label" xml:lang="en-US">{t}</link:label>')
        arcs.append(f'<link:labelArc xlink:type="arc" xlink:from="l{i}" xlink:to="r{i}"/>')
    return ('<?xml version="1.0" encoding="utf-8"?><link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase" '
            'xmlns:xlink="http://www.w3.org/1999/xlink"><link:labelLink xlink:type="extended">'
            + "".join(locs + labs + arcs) + "</link:labelLink></link:linkbase>")


def capture(symbol, base=FIX_DIR):
    rec = {}

    def fetch(url, timeout):
        body, code = edgar.urllib_fetcher(url, max(timeout, 20.0))
        rec[url] = (body, code)
        return body, code
    edgar.reset()
    segments.reset()
    segments.FETCHER = fetch
    t0 = time.monotonic()
    live = segments.build(symbol)
    secs = time.monotonic() - t0
    out = {}
    for url, (body, code) in rec.items():
        if body is None:
            out[url] = {"code": code, "body": None}
            continue
        if url == edgar.TICKERS_URL:
            text = json.dumps(_reduce_tickers(body, symbol))
        elif url.startswith("https://data.sec.gov/submissions/"):
            text = json.dumps(_reduce_submissions(body))
        elif url.endswith("/index.json"):
            text = json.dumps(_reduce_index(body))
        elif url.endswith("_htm.xml"):
            text = _reduce_instance(body)
        elif url.startswith("https://data.sec.gov/api/xbrl/companyfacts/"):
            raw = json.loads(body)          # solo los conceptos de ingresos (reduce_facts y field_value los leen)
            want = {c for t in edgar.CONCEPTS["revenue"][2:] for c in t}
            text = json.dumps({"cik": raw.get("cik"), "entityName": raw.get("entityName"),
                               "facts": {tx: {c: n for c, n in cs.items() if c in want}
                                         for tx, cs in (raw.get("facts") or {}).items()}})
        elif url.endswith("_lab.xml"):
            # todos los miembros de los ejes (también los de ejes descartados o fuera de la partición)
            parsed = edgar.parse_segments(rec[next(u for u in rec if u.endswith("_htm.xml"))][0],
                                          tuple(cfg("market.segments.axes")) + tuple(cfg("market.segments.geographic_axes")),
                                          tuple(cfg("market.segments.revenue_concepts")),
                                          tuple(cfg("market.segments.neutral_members")),
                                          tuple(cfg("market.segments.geographic_axes")),
                                          tuple(cfg("market.segments.elimination_members")),
                                          tuple(cfg("market.segments.redundant_axes")),
                                          tuple(cfg("market.segments.extension_total_concepts")))
            members = {m for part in ("axes", "by_geo") for ax in parsed[part].values() for ms in ax.values()
                       for m in ms}
            names = edgar.labels(body, members)
            text = _reduce_labels(names)
        else:
            continue
        out[url] = {"code": code, "body": text}
    os.makedirs(base, exist_ok=True)
    path = os.path.join(base, f"{symbol.upper()}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"symbol": symbol.upper(), "captured": dt.date.today().isoformat(), "responses": out}, fh,
                  ensure_ascii=False, sort_keys=True, indent=0)
        fh.write("\n")
    # el replay (solo este archivo, en un directorio temporal sería lo mismo) debe dar lo mismo que el vivo
    segments.reset()
    edgar.reset()
    segments.FETCHER = replay_fetcher(base)
    again = segments.build(symbol)
    sizes = {u.rsplit("/", 1)[-1]: len(b or b"") for u, (b, _c) in rec.items() if u.endswith(".xml")}
    return live, again, secs, sizes, os.path.getsize(path)


def main(symbols, base=FIX_DIR):
    if not edgar.user_agent():
        raise SystemExit("falta SEC_EDGAR_USER_AGENT")
    bad = 0
    for s in symbols:
        live, again, secs, sizes, fsize = capture(s, base)
        same = live == again
        bad += not same
        segs = ", ".join(f"{x['label']} {x['share_last']:.0%}" for x in live["segments"])
        print(f"{s}: {live['status']} {live['axis'] or ''} [{segs}] concilia={live['reconciles']} "
              f"gap={live['gap_pct'] if live['gap_pct'] is None else round(live['gap_pct'], 4)} "
              f"motivo={live['reason']} | {secs:.1f} s, descargas {sizes}, fixture {fsize / 1024:.0f} KB, "
              f"replay {'idéntico' if same else 'DISTINTO'}")
    if bad:
        raise SystemExit(f"{bad} tickers con replay distinto del vivo")


if __name__ == "__main__":
    _args = sys.argv[1:]
    _base = FIX_DIR
    if "--dir" in _args:            # F13: a otra carpeta (banco de pruebas fuera de git) en vez de tests/fixtures/segments
        i = _args.index("--dir")
        _base = os.path.abspath(_args[i + 1])
        del _args[i:i + 2]
    main(_args, _base)
