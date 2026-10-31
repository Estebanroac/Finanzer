"""
Rendimiento (rama rendimiento/v4f8-memoria): los segmentos (y con ellos la prima de riesgo país) son los mismos con la
descarga anticipada y la lista de filings compartida que con el camino de antes. Con las fuentes reales, para cada
ticker: el camino nuevo (submissions de sec_edgar y la descarga anticipada que toma build) y el de antes (submissions
descargado aparte y build descargando él mismo), cada uno con la caché de segmentos vacía; compara el JSON entero.

    cd finanzer_next-perf/backend
    SEC_EDGAR_USER_AGENT="$(security find-generic-password -s finanzer-sec-ua -w)" \\
        ../../finanzer_next/.venv313/bin/python tools/perf_identidad.py AAPL JPM NU ...
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(HERE)
sys.path.insert(0, BACKEND)
sys.path.insert(0, os.path.join(BACKEND, "lib"))


def old_last_annual(cik, budget):
    """lib/segments.last_annual en 461e9266: su propia descarga de submissions."""
    import segments
    import sec_edgar as edgar
    raw = edgar._get_json(edgar.SUBMISSIONS_URL.format(cik=cik), budget) or {}
    found = segments._annual_in((raw.get("filings") or {}).get("recent") or {})
    for page in [] if found else (raw.get("filings") or {}).get("files") or []:
        found = segments._annual_in(edgar._get_json(segments.SUBMISSIONS_PAGE_URL.format(name=page["name"]), budget)
                                    or {})
        if found:
            break
    return max(found, key=segments._annual_order) if found else None


def main() -> None:
    import logging
    logging.disable(logging.WARNING)
    import segments
    import sec_edgar as edgar
    segments.INSURER = lambda s: s in INSURERS
    bad = 0
    for sym in sys.argv[1:]:
        segments.reset()
        edgar.reset()
        segments.prefetch(sym)
        t = time.monotonic()
        while True:                       # espera a que la descarga anticipada esté (o no haya ninguna)
            with segments._lock:
                recs = list(segments._pre.values())
            if (recs and all(r["done"].is_set() for r in recs)) or time.monotonic() - t > 20:
                break
            time.sleep(0.1)
        took = bool(recs and recs[0].get("items") is not None)
        new = segments.build(sym)
        left = len(segments._pre)
        segments.reset()
        edgar.reset()
        real = segments.last_annual
        segments.last_annual = old_last_annual
        try:
            old = segments.build(sym)
        finally:
            segments.last_annual = real
        same = json.dumps(new, sort_keys=True) == json.dumps(old, sort_keys=True)
        bad += not same
        print(f"{sym}: {'igual' if same else 'DISTINTO'} · estado {new.get('status')} · descarga anticipada "
              f"{'tomada' if took and not left else ('sin descarga' if not recs else 'NO tomada')}"
              + ("" if new.get("status") == "ok" else f" · {new.get('reason')}"), flush=True)
        time.sleep(0.5)
    print(f"\n{len(sys.argv) - 1 - bad} iguales, {bad} distintos")
    sys.exit(1 if bad else 0)


INSURERS = {"CB", "PGR", "BRK-B", "TRV", "MET", "AIG", "ALL"}

if __name__ == "__main__":
    main()
