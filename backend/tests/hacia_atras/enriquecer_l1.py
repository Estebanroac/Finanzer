"""
F16: añade a los companyfacts de un juego de fixtures (<dir>/f2b/edgar/companyfacts) los conceptos que lib/precio_l1
necesita y que el reducido de antes de F16 no guardaba (us-gaap ProfitLoss y NetIncomeLossAttributableToNoncontrolling-
Interest), desde los companyfacts completos de la caché de datos_reales (descargados de la SEC el 6-nov-2026). Todos
los hechos: el replay los vuelve a cortar por `filed` al día de la captura (5-nov-2025). Las versiones anteriores del
motor los descartan al reducir: sus resultados no cambian.

    python -I tests/hacia_atras/enriquecer_l1.py <dir de fixtures> <caché de companyfacts completos>
"""
import gzip
import json
import os
import sys

CONCEPTS = ("ProfitLoss", "NetIncomeLossAttributableToNoncontrollingInterest")


def _load(p):
    return json.load(gzip.open(p)) if p.endswith(".gz") else json.load(open(p, encoding="utf-8"))


def _save(p, obj):
    data = json.dumps(obj, separators=(",", ":")).encode()
    if p.endswith(".gz"):
        with gzip.GzipFile(p, "wb", mtime=0) as fh:
            fh.write(data)
    else:
        with open(p, "wb") as fh:
            fh.write(data)


def main():
    base, cache = sys.argv[1], sys.argv[2]
    d = os.path.join(base, "f2b", "edgar", "companyfacts")
    n = added = 0
    for f in sorted(os.listdir(d)):
        if not (f.endswith(".json") or f.endswith(".json.gz")):
            continue
        name = f.split(".")[0]
        src = next((os.path.join(cache, name + ext) for ext in (".json.gz", ".json")
                    if os.path.isfile(os.path.join(cache, name + ext))), None)
        if src is None:
            continue
        full, fx = _load(src), _load(os.path.join(d, f))
        us = (full.get("facts") or {}).get("us-gaap") or {}
        tgt = fx.setdefault("facts", {}).setdefault("us-gaap", {})
        hit = False
        for c in CONCEPTS:
            if c in us and c not in tgt:
                tgt[c] = us[c]
                hit = True
        if hit:
            _save(os.path.join(d, f), fx)
            added += 1
        n += 1
    print(f"{n} companyfacts revisados, {added} enriquecidos")


if __name__ == "__main__":
    main()
