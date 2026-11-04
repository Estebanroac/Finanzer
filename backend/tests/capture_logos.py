"""
Logotipos: descarga real (lib/logos.fetch_sources: Parqet y, si falta, Finnhub) para el replay y los tests
(tests/fixtures/logos/<símbolo>.png e index.json con la fuente de cada uno, o null si ninguna lo tiene).

    cd finanzer_next/backend
    FINNHUB_API_KEY=… ../.venv313/bin/python tests/capture_logos.py

Los símbolos: la vista inicial del cintillo del replay (las tres listas de 1D de tests/fixtures/trending/batch.json),
los juegos local y panel y los rivales grabados (tests/fixtures/peers), con paleta de 64 colores (`_small`). Los demás
del cintillo (sectores, otros periodos) no se graban: en el replay salen con la placa de las iniciales, como una
empresa sin logotipo.
`replay_fetcher()` devuelve un FETCH que sirve lo grabado sin red.
"""
import datetime as dt
import json
import os
import sys

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
for _p in (os.path.dirname(TESTS_DIR), os.path.join(os.path.dirname(TESTS_DIR), "lib"), TESTS_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

DIR = os.path.join(TESTS_DIR, "fixtures", "logos")
INDEX = os.path.join(DIR, "index.json")


def _file(base, sym):
    return os.path.join(base, f"{sym}.png")


def replay_fetcher(base=DIR):
    """FETCH de lib/logos.py desde la captura: (PNG, fuente) o None (sin logotipo o no grabado)."""
    with open(os.path.join(base, "index.json"), encoding="utf-8") as fh:
        sources = json.load(fh)["sources"]

    def fetch(sym):
        src = sources.get(sym)
        if not src:
            return None
        with open(_file(base, sym), "rb") as fh:
            return fh.read(), src
    return fetch


def _small(data):
    """Solo para la captura (git): paleta de 64 colores, ≈ 1/4 del peso y a la vista igual a 200 px. El servidor sirve
    el PNG tal cual llega."""
    import io
    from PIL import Image
    with Image.open(io.BytesIO(data)) as im:
        out = io.BytesIO()
        im.convert("RGBA").quantize(colors=64, method=Image.Quantize.FASTOCTREE).save(out, format="PNG", optimize=True)
    return out.getvalue() if len(out.getvalue()) < len(data) else data


def _symbols():
    import capture_trending
    import logos
    import fixture_backend as fb
    import trending
    fetch, session = capture_trending.replay_fetcher()
    lists = trending.compute(fetch, session=session)["lists"]["1D"]
    syms = {x["symbol"] for rows in lists.values() for x in rows}
    syms |= set(fb.TICKERS) | (set(fb.env_tickers(fb.PANEL_ENV)) if fb.panel_available() else set())
    peers_dir = os.path.join(TESTS_DIR, "fixtures", "peers")
    syms |= {d for d in os.listdir(peers_dir) if os.path.isdir(os.path.join(peers_dir, d)) and logos.valid(d)}
    return sorted(syms)


def main():
    import logos
    os.makedirs(DIR, exist_ok=True)
    sources = {}
    for sym in _symbols():
        try:
            got = logos.fetch_sources(sym)
        except logos.SourceError as e:
            print(f"{sym}: sin respuesta ({e}); no se graba", flush=True)
            continue
        sources[sym] = got[1] if got else None
        if got:
            with open(_file(DIR, sym), "wb") as fh:
                fh.write(_small(got[0]))
        print(f"{sym}: {sources[sym]}", flush=True)
    with open(INDEX, "w", encoding="utf-8") as fh:
        json.dump({"captured": dt.date.today().isoformat(), "sources": sources}, fh, indent=1, sort_keys=True)
    have = sum(1 for v in sources.values() if v)
    print(f"{have}/{len(sources)} con logotipo")


if __name__ == "__main__":
    main()
