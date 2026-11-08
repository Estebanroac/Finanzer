"""
C2 con el criterio del usuario (7-nov-2026): la caída máxima ≥ 40 % en 12 meses debe ser al menos 1,5 veces más
frecuente con la alerta roja de valoración extrema que sin ella, en el total y también fuera de tecnología (GICS
Information Technology), en el control del corte de 2024 y en los dos cortes juntos. Alerta = la de la versión C de
cada corte (2025: corridas/F1p, la verificada antes del push; 2024: corridas/C con el relleno de la desviación 1).

    python3 tests/hacia_atras/c2_criterio.py <evidencias 2025> <evidencias 2024> > c2_criterio.json
"""
import csv
import gzip
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CUTS = (("2025", sys.argv[1], "F1p", {"BK": "BNY", "FI": "FISV", "MMC": "MRSH", "PSKY": "SKYD", "EQR": "VMRK"}),
        ("2024", sys.argv[2], "C", {"BK": "BNY", "FI": "FISV", "MMC": "MRSH", "EQR": "VMRK"}))
RATIO, DROP = 1.5, 40.0


def rows(year, base, run, alias):
    rr = {r[f"simbolo_{year}"]: r for r in csv.DictReader(open(f"{base}/datos_reales/resultados_reales.csv"))}
    uni = os.path.join(HERE, f"universo_{year}-11-05.tsv")
    out = []
    for u in csv.DictReader(open(uni), delimiter="\t"):
        if u["grupo"] != "control":
            continue
        s = u["symbol"]
        d, r = alias.get(s, s), rr.get(s) or {}
        p = f"{base}/corridas/{run}/{d}.json.gz"
        if not os.path.isfile(p) or not r.get("mdd_12m"):
            continue
        a = json.load(gzip.open(p))
        if "__http_error__" in a:
            continue
        red = any("valoración extrema" in (x.get("reason") or "") for x in (a.get("alerts") or {}).get("red_flags") or [])
        out.append({"corte": year, "simbolo": d, "tec": u["gics_sector"] == "Information Technology", "alerta": red,
                    "caida40": float(r["mdd_12m"]) >= DROP})
    return out


def stat(rs):
    c = [r for r in rs if r["alerta"]]
    s = [r for r in rs if not r["alerta"]]
    fc = sum(r["caida40"] for r in c) / len(c) if c else None
    fs = sum(r["caida40"] for r in s) / len(s) if s else None
    q = fc / fs if fc is not None and fs else None
    return {"con": [sum(r["caida40"] for r in c), len(c)], "sin": [sum(r["caida40"] for r in s), len(s)],
            "frec_con": fc, "frec_sin": fs, "cociente": q, "cumple": bool(q is not None and q >= RATIO)}


def main():
    data = {y: rows(y, b, run, al) for y, b, run, al in CUTS}
    data["juntos"] = data["2025"] + data["2024"]
    out = {}
    for k, rs in data.items():
        out[k] = {"total": stat(rs), "sin_tecnologia": stat([r for r in rs if not r["tec"]])}
        out[k]["cumple"] = out[k]["total"]["cumple"] and out[k]["sin_tecnologia"]["cumple"]
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
