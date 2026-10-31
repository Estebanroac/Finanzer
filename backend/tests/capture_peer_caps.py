"""
Rediseño E2b (Task 3): capitalizaciones de Finnhub (profile2) de los candidatos a rivales de los tickers de
verificación (con la industria que resolvió su análisis: el golden del panel), para el replay y los tests (tests/fixtures/peers/caps.json). Imprime los rivales automáticos.

    cd finanzer_next/backend
    FINNHUB_API_KEY="…" ../.venv313/bin/python tests/capture_peer_caps.py AAPL JPM O NEE XOM PLTR RIVN BCS

La clave solo vive en el entorno del comando: no se escribe (el fixture guarda símbolo -> capitalización).
"""
import datetime as dt
import json
import os
import sys

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
for _p in (os.path.dirname(TESTS_DIR), os.path.join(os.path.dirname(TESTS_DIR), "lib"), TESTS_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import peers  # noqa: E402

CAPS_FILE = os.path.join(TESTS_DIR, "fixtures", "peers", "caps.json")


def load_caps(path=CAPS_FILE):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)["caps"]


def main(symbols):
    if not os.environ.get("FINNHUB_API_KEY"):
        raise SystemExit("falta FINNHUB_API_KEY")
    caps = {}
    for s in symbols:
        # la industria que resolvió el análisis de la empresa (su golden del panel), como en producción
        with open(os.path.join(TESTS_DIR, "golden", "panel", f"{s}.json"), encoding="utf-8") as fh:
            ref = peers.reference(json.load(fh)) or {}
        industry, region = ref.get("industry"), ref.get("region")
        cands = peers.candidates(s, industry, region)
        cands = peers.lookup_order(cands, region)[:peers._limits["max_cap_lookups"]]
        for c in [s] + cands:
            if c not in caps:
                caps[c] = peers.finnhub_cap(c)
        r = peers.rank(s, cands, caps, region)
        own = caps.get(s)
        print(f"{s} ({industry}, {region}, cap {own / 1e9:.0f} B$)" if own else f"{s} ({industry}, {region}, sin cap)",
              "->", ", ".join((f"{x} {caps[x] / 1e9:.0f}" if caps.get(x) else f"{x} ?") + f" [{peers.region_of(x)}]"
                              for x in r["rivals"]),
              f"| {len(cands)} candidatos", r["note"] or "")
    os.makedirs(os.path.dirname(CAPS_FILE), exist_ok=True)
    with open(CAPS_FILE, "w", encoding="utf-8") as fh:
        json.dump({"captured": dt.date.today().isoformat(), "source": "Finnhub /stock/profile2 (marketCapitalization)",
                   "caps": caps}, fh, indent=0, sort_keys=True)
        fh.write("\n")


if __name__ == "__main__":
    main(sys.argv[1:])
