"""
Fase 3 (T1b): amplía los companyfacts del juego f2b con la historia larga, sin red.

El juego de la 2b (tests/fixtures/f2b/edgar/companyfacts) guarda los hechos desde 2019 (`FACTS_SINCE`): le bastaba
para 5 ejercicios. La clasificación por la historia real (D4) y el ciclo medio necesitan 10+, y la historia usa
conceptos nuevos (BPA diluido y acciones medias diluidas; sec_edgar.HISTORY). Este script los añade desde la caché
local de companyfacts de la fase 2a (tests/fixtures/edgar/raw, ignorada por git), sin tocar lo que ya hay:

  · de los conceptos que ya estaban, los hechos que acaban antes de FACTS_SINCE;
  · de los conceptos nuevos de sec_edgar._WANTED, todos los hechos;
  · solo hechos presentados hasta la fecha de captura del juego (metadata.json), como el replay.

Los hechos recientes del juego (capturados en vivo el día de la 2b) no se tocan: los golden de la 2b no cambian por
esto. Los CIK sin caché local se quedan como están (se listan).

    cd finanzer_next/backend
    ../.venv313/bin/python tests/f3_extend_history_fixtures.py            # escribe
    ../.venv313/bin/python tests/f3_extend_history_fixtures.py --check    # solo cuenta
"""
import json
import os
import sys

import f2b_fixtures as ff
import sec_edgar as edgar

RAW = os.path.join(ff.TESTS_DIR, "fixtures", "edgar", "raw")


def _until():
    """Fecha de la captura del juego f2b: nada presentado después entra (el replay corta además por ticker)."""
    meta = json.load(open(os.path.join(ff.F2B_DIR, "metadata.json"), encoding="utf-8"))
    return str(meta.get("captured_at_utc") or "")[:10] or None


def extend(fixture, raw, until):
    added = 0
    old = {(tx, c) for tx, cs in fixture.get("facts", {}).items() for c in cs}
    for tx, names in edgar._WANTED.items():
        for c in sorted(names):
            node = (raw.get("facts") or {}).get(tx, {}).get(c)
            if not node:
                continue
            dst = fixture.setdefault("facts", {}).setdefault(tx, {}).setdefault(c, {"units": {}})
            for u, fs in node["units"].items():
                lst = dst["units"].setdefault(u, [])
                keys = {(f.get("start"), f["end"], f.get("accn"), f.get("val")) for f in lst}
                for f in fs:
                    if until and f.get("filed", "") > until:
                        continue
                    if (tx, c) in old and f["end"] >= ff.FACTS_SINCE:
                        continue            # lo reciente ya está en el juego (captura en vivo)
                    g = {k: f[k] for k in edgar._FACT_KEYS if f.get(k) is not None}
                    k = (g.get("start"), g["end"], g.get("accn"), g.get("val"))
                    if k not in keys:
                        lst.append(g)
                        keys.add(k)
                        added += 1
                lst.sort(key=lambda f: (f["end"], f.get("start") or "", f.get("filed") or ""))
    return added


def main():
    check = "--check" in sys.argv
    until = _until()
    base = os.path.join(ff.F2B_DIR, "edgar", "companyfacts")
    missing, total = [], 0
    for name in sorted(os.listdir(base)):
        if not name.endswith(".json"):
            continue
        raw_path = os.path.join(RAW, name.replace(".json", ".facts.json"))
        if not os.path.isfile(raw_path):
            missing.append(name)
            continue
        path = os.path.join(base, name)
        fixture = json.load(open(path, encoding="utf-8"))
        n = extend(fixture, json.load(open(raw_path, encoding="utf-8")), until)
        total += n
        print(f"{name}: +{n} hechos")
        if not check and n:
            ff._write(path, fixture)
    print(f"\n{total} hechos añadidos (hasta {until}); sin caché local: {', '.join(missing) or 'ninguno'}")


if __name__ == "__main__":
    main()
