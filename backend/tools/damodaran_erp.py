"""
F14 · paso 1 (segunda revisión externa, 6-nov-2026): el par Rf–prima de riesgo de Damodaran se lee de su hoja mensual,
no del texto de su portada.

La portada del 1-nov-2026 decía «Implied ERP on November 1, 2026 = 4.41% … with the US treasury rate of 5.29%»: el
5,29 % era el texto de octubre sin actualizar. La hoja con la que calcula la prima (ERPNov26.xlsx, celda «Enter current
10-year US treasury rate» = 4,94 %) y la serie mensual (ERPbymonth.xlsx, «T.Bond Rate» del 1-nov = 4,94 %) dicen otra
cosa. Copiamos el 5,29 % y todo el universo llevó 35 pb de descuento de más.

    cd finanzer_next/backend
    ../.venv313/bin/python -I tools/damodaran_erp.py [--xlsx ERPbymonth.xlsx] [--write]

Sin --xlsx descarga https://pages.stern.nyu.edu/~adamodar/pc/implprem/ERPbymonth.xlsx (hoja «Historical ERP»). Lee la
última fila: el mes, el «T.Bond Rate» (el Rf con el que calcula la prima) y la «ERP (T12 m with sustainable payout)»
(la prima que publica en la portada: «Trailing 12 month, with adjusted payout»). El libro usa fechas de 1904.

Con --write:
  · escribe la serie en tests/fixtures/damodaran/erp_by_month.csv (la que vigila tests/test_damodaran_erp.py: el par de
    config/valuation.toml tiene que ser la fila de su fecha);
  · actualiza el par en config/valuation.toml (risk_free_rate, market_risk_premium, pair_as_of) y su fila en
    config/review.toml (published y consulted).
Los comentarios con las cifras del par en valuation.toml se revisan a mano en el mismo commit.
Si el Rf de la última fila es igual al del mes anterior, avisa y no escribe sin --igual-comprobado (lo que delató el
5,29 % del 1-nov fue que repetía el de octubre): hay que mirarlo en la hoja del mes (ERP<Mes><AA>.xlsx, «Enter current
10-year US treasury rate»).
Sin dependencias: el .xlsx se lee con zipfile y xml de la biblioteca estándar.
"""
import argparse
import csv
import datetime as dt
import io
import os
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = "https://pages.stern.nyu.edu/~adamodar/pc/implprem/ERPbymonth.xlsx"
SHEET = "Historical ERP"
COLS = {"month": "Start of month", "rf": "T.Bond Rate", "erp": "ERP (T12 m with sustainable payout)"}
FIXTURE = os.path.join(BACKEND, "tests", "fixtures", "damodaran", "erp_by_month.csv")
VALUATION = os.path.join(BACKEND, "config", "valuation.toml")
REVIEW = os.path.join(BACKEND, "config", "review.toml")
_M = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"


def _sheet_rows(data: bytes, name: str):
    """Filas de la hoja `name` como {columna: valor en texto}, y si el libro usa fechas de 1904."""
    z = zipfile.ZipFile(io.BytesIO(data))
    shared = []
    if "xl/sharedStrings.xml" in z.namelist():
        for si in ET.fromstring(z.read("xl/sharedStrings.xml")).iter(f"{_M}si"):
            shared.append("".join(t.text or "" for t in si.iter(f"{_M}t")))
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    pr = wb.find(f"{_M}workbookPr")
    date1904 = pr is not None and pr.get("date1904") in ("1", "true")
    rid = next(s.get(f"{_R}id") for s in wb.iter(f"{_M}sheet") if s.get("name") == name)
    rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    target = next(r.get("Target") for r in rels if r.get("Id") == rid).lstrip("/")
    path = target if target.startswith("xl/") else "xl/" + target
    rows = {}
    for c in ET.fromstring(z.read(path)).iter(f"{_M}c"):
        v = c.find(f"{_M}v")
        if v is None:
            continue
        col, row = re.match(r"([A-Z]+)(\d+)", c.get("r")).groups()
        rows.setdefault(int(row), {})[col] = shared[int(v.text)] if c.get("t") == "s" else v.text
    return [rows[k] for k in sorted(rows)], date1904


def monthly_series(data: bytes):
    """[(fecha ISO del mes, Rf, prima)] de la hoja mensual, en orden."""
    rows, date1904 = _sheet_rows(data, SHEET)
    head = {v.strip(): k for k, v in rows[0].items()}
    col = {k: head[name] for k, name in COLS.items()}
    epoch = dt.date(1904, 1, 1) if date1904 else dt.date(1899, 12, 30)
    out = []
    for r in rows[1:]:
        try:
            month = epoch + dt.timedelta(days=int(float(r[col["month"]])))
            rf, erp = float(r[col["rf"]]), float(r[col["erp"]])
        except (KeyError, ValueError):
            continue
        out.append((month.isoformat(), round(rf, 4), round(erp, 4)))
    return out


def unchanged_rf(series):
    """True si el Rf del último mes repite el del anterior: puede ser real, pero fue la señal del texto sin actualizar."""
    return len(series) >= 2 and series[-1][1] == series[-2][1]


def write_fixture(series, path=FIXTURE):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["month", "rf", "erp"])
        w.writerows(series)


def read_fixture(path=FIXTURE):
    with open(path, encoding="utf-8") as fh:
        return [(r["month"], float(r["rf"]), float(r["erp"])) for r in csv.DictReader(fh)]


def _sub(text, pattern, repl):
    new, n = re.subn(pattern, repl, text, count=1, flags=re.M)
    if n != 1:
        sys.exit(f"no encuentro {pattern!r}")
    return new


def write_config(month, rf, erp, consulted):
    with open(VALUATION, encoding="utf-8") as fh:
        t = fh.read()
    t = _sub(t, r"^risk_free_rate = [0-9.]+", f"risk_free_rate = {rf}")
    t = _sub(t, r"^market_risk_premium = [0-9.]+", f"market_risk_premium = {erp}")
    t = _sub(t, r'^pair_as_of = "[0-9-]+"', f'pair_as_of = "{month}"')
    with open(VALUATION, "w", encoding="utf-8") as fh:
        fh.write(t)
    with open(REVIEW, encoding="utf-8") as fh:
        t = fh.read()
    for name in ("market_risk_premium", "risk_free_rate"):
        block = re.search(rf"^\[parameters\.{name}\]\n(?:(?!^\[).*\n?)*", t, flags=re.M)
        b = re.sub(r'^published = "[0-9-]*"', f'published = "{month}"', block.group(0), count=1, flags=re.M)
        b = re.sub(r'^consulted = "[0-9-]*"', f'consulted = "{consulted}"', b, count=1, flags=re.M)
        t = t[:block.start()] + b + t[block.end():]
    with open(REVIEW, "w", encoding="utf-8") as fh:
        fh.write(t)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--xlsx", help="ERPbymonth.xlsx ya descargado (si no, se descarga)")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--igual-comprobado", action="store_true",
                    help="el Rf repite el del mes anterior y se ha comprobado en la hoja del mes")
    a = ap.parse_args()
    if a.xlsx:
        with open(a.xlsx, "rb") as fh:
            data = fh.read()
    else:
        with urllib.request.urlopen(URL, timeout=60) as r:
            data = r.read()
    series = monthly_series(data)
    month, rf, erp = series[-1]
    print(f"Damodaran, {month}: Rf {rf:.2%} (T.Bond Rate) · prima {erp:.2%} (T12m, sustainable payout)")
    for m, r, e in series[-4:-1]:
        print(f"  antes {m}: Rf {r:.2%} · prima {e:.2%}")
    if unchanged_rf(series):
        print(f"AVISO: el Rf ({rf:.2%}) repite el del mes anterior: comprobarlo en la hoja del mes antes de escribir")
        if a.write and not a.igual_comprobado:
            sys.exit("no se escribe: repetir con --igual-comprobado tras comprobarlo")
    if a.write:
        write_fixture(series)
        write_config(month, rf, erp, dt.date.today().isoformat())
        print(f"escrito: {os.path.relpath(FIXTURE, BACKEND)}, config/valuation.toml y config/review.toml")


if __name__ == "__main__":
    main()
