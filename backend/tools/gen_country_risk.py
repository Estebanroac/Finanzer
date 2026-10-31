"""
F9 · R1 (revisión externa de NU, 27-oct-2026): genera config/country_risk.toml con las primas de riesgo país de
Damodaran (ctryprem.xlsx, NYU Stern), para el Ke = Rf + β·ERP + λ·CRP (lib/country_risk.py). Sin dependencias: lee
el xlsx con zipfile y ElementTree.

    curl -o /tmp/ctryprem.xlsx https://pages.stern.nyu.edu/~adamodar/pc/datasets/ctryprem.xlsx
    python tools/gen_country_risk.py /tmp/ctryprem.xlsx 2026-01-05 2026-10-27

El primer argumento es la fecha de la actualización («Last updated» de la página ctryprem.html; la celda «Date of
update» del xlsx no se mantiene); el segundo, la de consulta. Damodaran la publica dos veces al año (enero y julio):
review.toml la marca para revisión semestral.

Lo que escribe:
  · `mature_market_erp` y `us_erp`: la prima del mercado maduro y la de EE. UU. de esa actualización.
  · [erp]: la prima total de cada país (columna «Total Equity Risk Premium», la del rating soberano en moneda local; la
    de CDS no existe para muchos países).
  · [country_region]: la región de Damodaran de cada país.
  · [region_erp]: las medias regionales ponderadas por PIB (hoja «Regional Weighted Averages»), con sus agrupaciones
    (Europe, EMEA, Latin America & Caribbean, Emerging Markets…).
"""
import os
import sys
import zipfile
from xml.etree import ElementTree as ET

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
      "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}
URL = "https://pages.stern.nyu.edu/~adamodar/pc/datasets/ctryprem.xlsx"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "country_risk.toml")


def _sheets(path):
    z = zipfile.ZipFile(path)
    ss = ["".join(t.text or "" for t in si.iter(f"{{{NS['m']}}}t"))
          for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", NS)]
    rels = {r.get("Id"): r.get("Target") for r in ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))}
    out = {}
    for s in ET.fromstring(z.read("xl/workbook.xml")).find("m:sheets", NS):
        tgt = rels[s.get(f"{{{NS['r']}}}id")]
        tgt = tgt if tgt.startswith("xl/") else "xl/" + tgt.lstrip("/")
        rows = []
        for row in ET.fromstring(z.read(tgt)).iter(f"{{{NS['m']}}}row"):
            vals = []
            for c in row.findall("m:c", NS):
                v = c.find("m:v", NS)
                vals.append(None if v is None else ss[int(v.text)] if c.get("t") == "s" else v.text)
            rows.append(vals)
        out[s.get("name")] = rows
    return out


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _q(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def main(xlsx, updated, consulted):
    sh = _sheets(xlsx)
    erp_rows = sh["ERPs by country"]
    mature = us = None
    countries = {}
    for r in erp_rows:
        if not r or r[0] is None:
            continue
        label = str(r[0])
        if label.startswith("Enter the current risk premium for a mature"):
            mature = _num(r[1])
        elif label.startswith("Enter the current risk premium for the US"):
            us = _num(r[1])
        elif len(r) >= 6 and _num(r[4]) is not None and r[2] and str(r[2]) != "Moody's rating":
            countries[label.strip()] = (str(r[1]).strip(), str(r[2]).strip(), _num(r[4]))
    regions = {}
    for r in sh["Regional Weighted Averages"]:
        v = [x for x in r if x not in (None, "")]
        # una prima (entre 0 y 0,5), no los totales de PIB por región que la hoja trae en otra tabla
        if len(v) >= 2 and isinstance(v[0], str) and _num(v[0]) is None and v[0] not in countries \
                and 0 < (_num(v[1]) or 0) < 0.5:
            regions.setdefault(v[0].strip(), _num(v[1]))
    if mature is None or us is None or len(countries) < 100 or "Global" not in regions:
        sys.exit(f"xlsx inesperado: mature={mature} us={us} países={len(countries)} regiones={sorted(regions)}")
    lines = [
        "# F9 · R1 (revisión externa de NU, 27-oct-2026): primas de riesgo país de A. Damodaran (ctryprem.xlsx).",
        "# GENERADO por backend/tools/gen_country_risk.py: no editar a mano; regenerar con cada actualización (enero y",
        "# julio) y actualizar su fila en review.toml en el mismo commit. Uso: lib/country_risk.py.",
        "",
        'source = "A. Damodaran, Country Default Spreads and Risk Premiums (ctryprem.xlsx), NYU Stern"',
        f'url = "{URL}"',
        f'updated = "{updated}"',
        f'consulted = "{consulted}"',
        f"mature_market_erp = {mature:.6f}",
        f"us_erp = {us:.6f}",
        "",
        "[erp]                           # prima total de cada país (rating soberano en moneda local)",
        *[f"{_q(c)} = {v[2]:.6f}" for c, v in sorted(countries.items())],
        "",
        "[country_region]                # región de Damodaran de cada país",
        *[f"{_q(c)} = {_q(v[0])}" for c, v in sorted(countries.items())],
        "",
        "[region_erp]                    # medias regionales ponderadas por PIB y agrupaciones",
        *[f"{_q(k)} = {v:.6f}" for k, v in sorted(regions.items())],
        "",
    ]
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    print(f"escrito {OUT}: {len(countries)} países, {len(regions)} regiones; mercado maduro {mature:.2%}, EE. UU. "
          f"{us:.2%}")


if __name__ == "__main__":
    main(*sys.argv[1:4])
