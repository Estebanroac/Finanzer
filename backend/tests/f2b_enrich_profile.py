"""
Rediseño E2a (T3): añade a los submissions del juego f2b los campos de la ficha del emisor, sin red.

El juego de la 2b (tests/fixtures/f2b/edgar/submissions) guardó solo los filings, el cierre fiscal y el país de la
dirección. La ficha (sec_edgar.submission_profile) usa además el código SIC y su descripción, el estado de
constitución, la categoría de emisor, la web y la ciudad de la sede: vienen en la misma respuesta de submissions, así
que se copian de la caché local de la fase 2a (tests/fixtures/edgar/raw, ignorada por git; en un worktree se lee la
del checkout principal). No se tocan los filings ni nada de lo que ya hay: los golden solo ganan claves nuevas.
Los CIK sin caché local se quedan como están (se listan) y su ficha sale "sin_dato".

    cd finanzer_next/backend
    ../.venv313/bin/python tests/f2b_enrich_profile.py            # escribe
    ../.venv313/bin/python tests/f2b_enrich_profile.py --check    # solo cuenta
"""
import json
import os
import sys

import f2b_fixtures as ff

MAIN_CHECKOUT_RAW = "/Users/joseestebanroa/Downloads/Finanzer/finanzer_next/backend/tests/fixtures/edgar/raw"
RAW = next((p for p in (os.path.join(ff.TESTS_DIR, "fixtures", "edgar", "raw"), MAIN_CHECKOUT_RAW)
            if os.path.isdir(p)), None)


def enrich(fixture, raw):
    """Copia los campos de la ficha y la ciudad de cada dirección; devuelve cuántos valores cambió."""
    n = 0
    for k in ff.PROFILE_KEYS:
        if k in raw and fixture.get(k) != raw[k]:
            fixture[k] = raw[k]
            n += 1
    for kind, addr in (raw.get("addresses") or {}).items():
        dst = (fixture.get("addresses") or {}).get(kind)
        if dst is not None and "city" not in dst:
            dst["city"] = addr.get("city")
            n += 1
    return n


def main():
    check = "--check" in sys.argv
    if RAW is None:
        sys.exit("sin caché local de EDGAR (tests/fixtures/edgar/raw): nada que hacer")
    base = os.path.join(ff.F2B_DIR, "edgar", "submissions")
    missing, total = [], 0
    for name in sorted(os.listdir(base)):
        if not name.endswith(".json"):
            continue
        raw_path = os.path.join(RAW, name.replace(".json", ".submissions.json"))
        if not os.path.isfile(raw_path):
            missing.append(name)
            continue
        path = os.path.join(base, name)
        fixture = json.load(open(path, encoding="utf-8"))
        n = enrich(fixture, json.load(open(raw_path, encoding="utf-8")))
        total += n
        print(f"{name}: +{n} campos")
        if not check and n:
            ff._write(path, fixture)
    print(f"\n{total} campos añadidos; sin caché local: {', '.join(missing) or 'ninguno'}")


if __name__ == "__main__":
    main()
