"""
F8 (historia de 10 años en cascada): añade a los companyfacts del juego f2b los hechos de los conceptos de relevo
(sec_edgar.HISTORY_RELAY), que el juego no guardaba porque no estaban en sec_edgar._WANTED cuando se capturó.

  · Solo esos conceptos; lo demás del juego no se toca.
  · Solo hechos presentados hasta la fecha de captura del juego (metadata.json), como el replay.
  · companyfacts de la SEC (gratuito); el User-Agent se lee del entorno, del Llavero en el mismo comando, y nunca se
    imprime:

    cd finanzer_next/backend
    SEC_EDGAR_USER_AGENT="$(security find-generic-password -s finanzer-sec-ua -w)" \\
        ../.venv313/bin/python tests/capture_history_relay_f8.py            # escribe
    (… --check: solo cuenta)
"""
import json
import os
import sys
import time
import urllib.request

import f2b_fixtures as ff
import sec_edgar as edgar

URL = "https://data.sec.gov/api/xbrl/companyfacts/{name}"


def relay_concepts():
    return {"us-gaap": {c for v in edgar.HISTORY_RELAY.values() for c in v[0]},
            "ifrs-full": {c for v in edgar.HISTORY_RELAY.values() for c in v[1]}}


def until():
    meta = json.load(open(os.path.join(ff.F2B_DIR, "metadata.json"), encoding="utf-8"))
    return str(meta.get("captured_at_utc") or "")[:10]


def fetch(name, ua):
    req = urllib.request.Request(URL.format(name=name), headers={"User-Agent": ua, "Accept-Encoding": "identity"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def extend(fixture, raw, day):
    added = 0
    for tx, names in relay_concepts().items():
        for c in sorted(names):
            node = (raw.get("facts") or {}).get(tx, {}).get(c)
            if not node:
                continue
            dst = fixture.setdefault("facts", {}).setdefault(tx, {}).setdefault(c, {"units": {}})
            for u, fs in node["units"].items():
                lst = dst["units"].setdefault(u, [])
                keys = {(f.get("start"), f["end"], f.get("accn"), f.get("val")) for f in lst}
                for f in fs:
                    if f.get("filed", "") > day:
                        continue
                    g = {k: f[k] for k in edgar._FACT_KEYS if f.get(k) is not None}
                    k = (g.get("start"), g["end"], g.get("accn"), g.get("val"))
                    if k not in keys:
                        lst.append(g)
                        keys.add(k)
                        added += 1
                lst.sort(key=lambda f: (f["end"], f.get("start") or "", f.get("filed") or ""))
    return added


def main():
    ua = os.environ.get("SEC_EDGAR_USER_AGENT")
    if not ua:
        sys.exit("falta SEC_EDGAR_USER_AGENT en el entorno")
    check, day = "--check" in sys.argv, until()
    base = os.path.join(ff.F2B_DIR, "edgar", "companyfacts")
    total = 0
    for name in sorted(n for n in os.listdir(base) if n.endswith(".json")):
        path = os.path.join(base, name)
        fixture = json.load(open(path, encoding="utf-8"))
        n = extend(fixture, fetch(name, ua), day)
        time.sleep(0.25)                  # SEC: ≤ 10 peticiones por segundo
        total += n
        if n:
            print(f"{name}: +{n} hechos")
            if not check:
                ff._write(path, fixture)
    print(f"{total} hechos de relevo añadidos (presentados hasta {day})")


if __name__ == "__main__":
    main()
