"""
Corrección del corte de 2024 (decisión del usuario, 7-nov-2026): completar los estados anuales de Yahoo con los
ejercicios que Yahoo ya no sirve.

Yahoo solo da hoy los cuatro últimos ejercicios anuales (2022–2025). Cortados al 5-nov-2024 quedan dos o tres, y el
motor necesita cuatro para medir el crecimiento: el 91 % del control perdía la categoría «Crecimiento». Una corrida real
en noviembre de 2024 habría tenido cuatro (2020–2023). Este script añade a una COPIA de los fixtures, en
`income_stmt` y `cashflow` de `yfinance.json.gz`, los ejercicios anteriores al más antiguo de Yahoo hasta llegar a
cuatro columnas.

De dónde salen los valores: la historia de SEC EDGAR que el propio motor calcula al corte (`history_10y` de la corrida
de A: companyfacts con `filed` ≤ corte; mismos conceptos y relevos que el motor). Ningún dato posterior al corte.

Comprobación por empresa y por campo: en el ejercicio más antiguo que Yahoo sí da, EDGAR tiene que coincidir con Yahoo
(±3 % en importes, ±5 % en BPA, capex y caja libre). Si no coincide, ese campo no se rellena (moneda, base por acción,
definición de ingresos en bancos…). Si el ejercicio de Yahoo no trae ese campo, se rellena solo si los ingresos
coincidieron. Los balances no se completan (la historia no los tiene); se declara.

    python -I tests/hacia_atras/rellenar_anuales.py --fixtures <fixtures> --corrida <corridas/A> --out <fixtures nuevo>

Deja `<out>/_relleno.json` con lo añadido y lo rechazado por empresa. No modifica `--fixtures`.
"""
import argparse
import calendar
import datetime as dt
import gzip
import json
import os
import shutil
import subprocess

TARGET = 4
# fila de Yahoo → (estado, campo de history_10y, tolerancia relativa de la comprobación)
FIELDS = (
    ("income_stmt", "Total Revenue", "revenue", 0.03),
    ("income_stmt", "Operating Income", "operating_income", 0.03),
    ("income_stmt", "Net Income", "net_income", 0.03),
    ("income_stmt", "Net Income Common Stockholders", "net_income", 0.03),
    ("income_stmt", "Diluted EPS", "diluted_eps", 0.05),
    ("cashflow", "Operating Cash Flow", "operating_cash_flow", 0.03),
    ("cashflow", "Capital Expenditure", "capex", 0.05),
    ("cashflow", "Free Cash Flow", "free_cash_flow", 0.05),
)


def _load(p):
    return json.load(gzip.open(p)) if p.endswith(".gz") else json.load(open(p, encoding="utf-8"))


def _month_end(d):
    return dt.date(d.year, d.month, calendar.monthrange(d.year, d.month)[1])


def _close(a, b, tol):
    if a is None or b is None:
        return None
    if a == 0 and b == 0:
        return True
    return abs(a - b) <= tol * max(abs(a), abs(b))


def _val(frame, row, col):
    if row not in frame["index"]:
        return None
    v = frame["data"][frame["index"].index(row)][col]
    return None if v is None or v != v else v


def fill(yf, hist):
    """Añade columnas a income_stmt y cashflow. -> (yf modificado o None, informe)."""
    inc, cf = yf.get("income_stmt"), yf.get("cashflow")
    rep = {"añadidos": [], "campos": [], "rechazados": {}}
    if not inc or not inc.get("columns") or not inc.get("columns_are_dates"):
        rep["motivo"] = "sin estado anual de Yahoo"
        return None, rep
    cols = inc["columns"]
    if len(cols) >= TARGET:
        rep["motivo"] = f"ya tiene {len(cols)} ejercicios"
        return None, rep
    if cf and cf.get("columns") != cols:
        rep["motivo"] = "income_stmt y cashflow con columnas distintas"
        return None, rep
    rows = [r for r in (hist or {}).get("rows") or [] if r.get("fy_end")]
    if not rows:
        rep["motivo"] = "sin historia de EDGAR"
        return None, rep
    oldest = dt.date.fromisoformat(cols[-1][:10])

    def row_at(d):
        best = [r for r in rows if abs((dt.date.fromisoformat(r["fy_end"]) - d).days) <= 20]
        return best[0] if best else None
    ov = row_at(oldest)
    if ov is None:
        rep["motivo"] = f"EDGAR no tiene el ejercicio {oldest} para comprobar"
        return None, rep
    frames = {"income_stmt": inc, "cashflow": cf}
    rev_ok = _close(_val(inc, "Total Revenue", len(cols) - 1), ov.get("revenue"), 0.03)
    ok_fields = []
    for st, yrow, hk, tol in FIELDS:
        fr = frames.get(st)
        if not fr or yrow not in fr["index"]:
            continue
        c = _close(_val(fr, yrow, len(cols) - 1), ov.get(hk), tol)
        if c or (c is None and rev_ok and ov.get(hk) is not None):
            ok_fields.append((st, yrow, hk))
        else:
            rep["rechazados"][yrow] = [_val(fr, yrow, len(cols) - 1), ov.get(hk)]
    if not ok_fields:
        rep["motivo"] = "ningún campo coincide con Yahoo en el ejercicio común"
        return None, rep
    # ejercicios anteriores, consecutivos (330–400 días entre uno y otro), hasta TARGET columnas
    new, prev = [], dt.date.fromisoformat(ov["fy_end"])
    for r in sorted(rows, key=lambda r: r["fy_end"], reverse=True):
        e = dt.date.fromisoformat(r["fy_end"])
        if e >= prev:
            continue
        if not 330 <= (prev - e).days <= 400 or len(cols) + len(new) >= TARGET:
            break
        new.append(r)
        prev = e
    if not new:
        rep["motivo"] = "EDGAR no tiene el ejercicio anterior"
        return None, rep
    for r in new:
        col = dt.datetime.combine(_month_end(dt.date.fromisoformat(r["fy_end"])), dt.time()).isoformat()
        for st, fr in frames.items():
            if not fr:
                continue
            fr["columns"].append(col)
            for i, name in enumerate(fr["index"]):
                hk = next((h for s, y, h in ok_fields if s == st and y == name), None)
                v = r.get(hk) if hk else None
                fr["data"][i].append(float(v) if v is not None else None)
        rep["añadidos"].append(r["fy_end"])
    rep["campos"] = sorted({y for _s, y, _h in ok_fields})
    return yf, rep


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fixtures", required=True)
    ap.add_argument("--corrida", required=True, help="corridas/A: de ahí sale history_10y de cada empresa")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    if os.path.exists(a.out):
        raise SystemExit(f"{a.out} ya existe")
    subprocess.run(["cp", "-Rc", a.fixtures, a.out], check=True)        # clon APFS: los demás archivos no cambian
    report = {}
    for sym in sorted(os.listdir(a.out)):
        p = os.path.join(a.out, sym, "yfinance.json.gz")
        h = os.path.join(a.corrida, f"{sym}.json.gz")
        if not os.path.isfile(p):
            continue
        an = _load(h) if os.path.isfile(h) else {}
        yf, rep = fill(_load(p), an.get("history_10y"))
        report[sym] = rep
        if yf is not None:
            tmp = p + ".part"
            with gzip.GzipFile(tmp, "wb", mtime=0) as fh:
                fh.write(json.dumps(yf, separators=(",", ":"), ensure_ascii=False).encode())
            os.replace(tmp, p)
    with open(os.path.join(a.out, "_relleno.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=1, sort_keys=True)
    n = sum(1 for r in report.values() if r["añadidos"])
    print(f"{n} de {len(report)} empresas con ejercicios añadidos → {a.out}")
    why = {}
    for r in report.values():
        if not r["añadidos"]:
            k = r.get("motivo", "?").split(" 1")[0].split(" 2")[0]
            why[k] = why.get(k, 0) + 1
    print("sin añadir:", why)


if __name__ == "__main__":
    main()
