"""F3 · T1: coste de la historia larga de EDGAR en el camino del análisis.

Por CIK, en un proceso nuevo cada uno (el pico de memoria no se mezcla):
  · descarga en vivo de companyfacts (User-Agent de SEC_EDGAR_USER_AGENT; nunca se imprime): tiempo y bytes;
  · json.loads + lib.sec_edgar.reduce_facts: tiempo, pico de memoria (tracemalloc) y RSS máximo del proceso;
  · tamaño del extracto reducido (lo que queda en la caché en memoria) y de un extracto "solo anual" (FY).
uso: SEC_EDGAR_USER_AGENT=... ../.venv313/bin/python tests/f3_t1_mem.py CIK [--offline]
"""
import gzip
import json
import os
import resource
import sys
import time
import tracemalloc
import urllib.request
from pathlib import Path

B = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(B))
sys.path.insert(0, str(B / "lib"))
RAW = B / "tests/fixtures/edgar/raw"


def rss_mb():
    r = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return r / 1024 / 1024 if sys.platform == "darwin" else r / 1024


def main():
    cik = int(sys.argv[1])
    offline = "--offline" in sys.argv
    out = {"cik": cik}
    import lib.sec_edgar as se  # importa pandas y config: base del proceso
    base_rss = rss_mb()
    out["rss_base_mb"] = round(base_rss, 1)
    if not offline:
        url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
        req = urllib.request.Request(url, headers={"User-Agent": os.environ["SEC_EDGAR_USER_AGENT"],
                                                   "Accept-Encoding": "gzip"})
        t = time.perf_counter()
        with urllib.request.urlopen(req, timeout=30) as r:
            body = r.read()
            enc = r.headers.get("Content-Encoding")
        out["descarga_s"] = round(time.perf_counter() - t, 2)
        out["bytes_red"] = len(body)
        if enc == "gzip":
            body = gzip.decompress(body)
    else:
        body = (RAW / f"CIK{cik:010d}.facts.json").read_bytes()
    out["bytes_json"] = len(body)
    tracemalloc.start()
    t = time.perf_counter()
    raw = json.loads(body)
    red = se.reduce_facts(raw)
    out["parse_reduce_s"] = round(time.perf_counter() - t, 2)
    del raw
    _cur, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    out["pico_tracemalloc_mb"] = round(peak / 1e6, 1)
    out["rss_max_mb"] = round(rss_mb(), 1)
    out["rss_delta_mb"] = round(rss_mb() - base_rss, 1)
    out["reducido_bytes"] = len(json.dumps(red))
    # extracto solo anual (formularios anuales): lo mínimo para clasificar y para el ciclo medio
    ann = {"facts": {}}
    for tx, cs in red["facts"].items():
        for c, node in cs.items():
            for u, fs in node["units"].items():
                keep = [f for f in fs if f.get("form") in se.ANNUAL_FORMS]
                if keep:
                    ann["facts"].setdefault(tx, {}).setdefault(c, {"units": {}})["units"][u] = keep
    out["anual_bytes"] = len(json.dumps(ann))
    print(json.dumps(out))


if __name__ == "__main__":
    main()
