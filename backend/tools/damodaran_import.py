"""
Fase 4/7 (F4_PARADA §5, permiso del usuario del 2026-10-17): referencias por industria y por región de Damodaran.

Lee los conjuntos de datos de A. Damodaran (NYU Stern) descargados en una carpeta y escribe config/industries.toml
(una fila por industria y región, con fuente y fecha). La app no lee los Excel: solo el TOML que sale de aquí.

    cd finanzer_next/backend
    python -I tools/damodaran_import.py --raw ~/Downloads/finanzer_damodaran/raw --lib <carpeta con xlrd> \
        --out config/industries.toml

Ficheros (https://pages.stern.nyu.edu/~adamodar/pc/datasets/): por región R en {"" (EE. UU.), Europe, Japan, emerg,
Global}: pedata.xls | pe{R}.xls, pbvdata.xls | pbv{R}.xls, vebitda{R}.xls, roe{R}.xls, margin{R}.xls, dbtfund{R}.xls.
xlrd solo hace falta para esta herramienta (no es una dependencia de la app).

Columnas y por qué (todas son agregados de la industria salvo lo que se dice):
  · pe: capitalización agregada / beneficio de doce meses agregado de las empresas con beneficio (Damodaran desaconseja
    sus medias simples de P/E: sesgadas por la media igual y por excluir a las que pierden);
  · sin P/E adelantado: Damodaran solo da su media simple, y el cociente adelantado/doce meses de sus medias tampoco
    sirve (software de EE. UU. 16x frente a 37.5x; restauración en Europa 2.4x): la tabla lo muestra sin referencia y
    el tope del score usa el P/E de doce meses (financial_ratios, `sector_forward_pe or sector_pe`);
  · ev_ebitda: de las empresas con EBITDA positivo; pb, roe (sin ajustar por I+D), roic: agregados;
  · gross_margin, operating_margin (antes de impuestos, sin ajustar), net_margin: agregados;
  · interest_coverage: agregado; de: deuda contable / patrimonio contable = BDC / (1 − BDC), con BDC la deuda contable
    sobre capital de Damodaran (identidad, no estimación);
  · pe_avg: la media simple del P/E de doce meses de las empresas con beneficio. No es una referencia: solo sirve para
    la prueba de representatividad (lib/industry_bench.py): normalmente la media supera al agregado (empresas con
    beneficio casi nulo; mediana del cociente 0.66 en EE. UU.); un agregado POR ENCIMA de la media delata una
    industria dominada por pocas empresas de múltiplo extremo (Auto & Truck de EE. UU.: 119.6x frente a 64.3x).
Un margen de 0 o 1 (±0.2 puntos) es un artefacto de definición (la banca no tiene coste de ventas ni beneficio operativo en
estas tablas: margen bruto 100%, operativo 0%), no una medida: sin dato. Un múltiplo ≤ 0 tampoco es una referencia.
"""
import argparse
import datetime as dt
import math
import os
import sys

REGIONS = {"us": ("", "EE. UU."), "europe": ("Europe", "Europa"), "japan": ("Japan", "Japón"),
           "emerging": ("emerg", "mercados emergentes"), "global": ("Global", "global")}
COLUMNS = ["pe", "ev_ebitda", "pb", "roe", "roic", "gross_margin", "operating_margin", "net_margin",
           "interest_coverage", "de", "pe_avg"]
TOTALS = {"Total Market": "Total Market", "Grand Total": "Total Market",
          "Total Market (without financials)": "Total Market (without financials)"}


def _files(code):
    return {"pe": "pedata.xls" if not code else f"pe{code}.xls", "pbv": "pbvdata.xls" if not code else f"pbv{code}.xls",
            "ev": f"vebitda{code}.xls", "roe": f"roe{code}.xls", "margin": f"margin{code}.xls",
            "debt": f"dbtfund{code}.xls"}


def _table(path):
    """{industria: {columna: valor}} de la hoja "Industry Averages", y la fecha de actualización."""
    import xlrd
    book = xlrd.open_workbook(path)
    s = book.sheet_by_name("Industry Averages")
    head = next(r for r in range(s.nrows) if str(s.cell_value(r, 0)).strip() == "Industry Name")
    group = [str(c.value).strip() for c in s.row(head - 1)]
    cols, current = [], ""
    for i, c in enumerate(s.row(head)):
        current = group[i] if i < len(group) and group[i] else current
        cols.append((current, str(c.value).strip()))
    out = {}
    for r in range(head + 1, s.nrows):
        name = str(s.cell_value(r, 0)).strip()
        if not name:
            continue
        name = TOTALS.get(name, name)
        out[name] = {cols[i]: s.cell_value(r, i) for i in range(1, len(cols))}
    serial = s.cell_value(0, 1)
    updated = (dt.date(1899, 12, 30) + dt.timedelta(days=int(serial))).isoformat() if isinstance(serial, float) else None
    return out, updated


def _num(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return math.nan
    return f if math.isfinite(f) else math.nan


def _get(row, *names):
    """Valor de la primera columna cuyo nombre empieza por alguno de `names` (el grupo, si se da, como (grupo, col))."""
    for want in names:
        for (grp, col), v in row.items():
            if isinstance(want, tuple):
                if grp.startswith(want[0]) and col.startswith(want[1]):
                    return _num(v)
            elif col.startswith(want):
                return _num(v)
    return math.nan


def region_rows(raw, code):
    f = {k: os.path.join(raw, v) for k, v in _files(code).items()}
    pe, upd = _table(f["pe"])
    pbv, _ = _table(f["pbv"])
    ev, _ = _table(f["ev"])
    roe, _ = _table(f["roe"])
    mg, _ = _table(f["margin"])
    debt, _ = _table(f["debt"])
    rows = {}
    for ind, p in pe.items():
        n = _get(p, "Number of firms")
        agg = _get(p, "Aggregate Mkt Cap/ Trailing Net Income")
        b = debt.get(ind, {})
        bdc = _get(b, "Book Debt to Capital")
        de = bdc / (1 - bdc) if math.isfinite(bdc) and 0 <= bdc < 1 else math.nan
        vals = {"pe": agg, "pe_avg": _get(p, "Trailing PE"),
                "ev_ebitda": _get(ev.get(ind, {}), ("Only positive EBITDA", "EV/EBITDA")),
                "pb": _get(pbv.get(ind, {}), "PBV"), "roe": _get(roe.get(ind, {}), "ROE (unadjusted)"),
                "roic": _get(pbv.get(ind, {}), "ROIC"),
                "gross_margin": _get(mg.get(ind, {}), "Gross Margin"),
                "operating_margin": _get(mg.get(ind, {}), "Pre-tax Unadjusted Operating Margin"),
                "net_margin": _get(mg.get(ind, {}), "Net Margin"),
                "interest_coverage": _get(b, "Interest Coverage Ratio"), "de": de}
        # un múltiplo ≤ 0 no es una referencia (industria con pérdidas agregadas)
        for k in ("pe", "ev_ebitda", "pb", "interest_coverage"):
            if math.isfinite(vals[k]) and vals[k] <= 0:
                vals[k] = math.nan
        for k in ("gross_margin", "operating_margin", "net_margin"):
            if math.isfinite(vals[k]) and (abs(vals[k]) < 0.002 or abs(vals[k] - 1) < 0.002):
                vals[k] = math.nan
        rows[ind] = [int(n) if math.isfinite(n) else 0] + [vals[c] for c in COLUMNS]
    return rows, upd


def _fmt(x):
    if isinstance(x, int):
        return str(x)
    return "nan" if not math.isfinite(x) else repr(round(x, 4))


def write(raw, out):
    regions, dates = {}, set()
    for key, (code, _label) in REGIONS.items():
        regions[key], upd = region_rows(raw, code)
        dates.add(upd)
    as_of = max(d for d in dates if d)
    lines = [
        "# GENERADO por backend/tools/damodaran_import.py desde los conjuntos de datos de A. Damodaran (NYU Stern).",
        "# NO EDITAR A MANO: vuelve a descargar los Excel (se actualizan cada enero) y ejecuta la herramienta.",
        "# Referencias por industria y región para la brecha frente a la referencia (main._select_benchmark).",
        "# Definición de cada columna: la cabecera de tools/damodaran_import.py.",
        "",
        'source = "A. Damodaran, conjuntos de datos por industria (pedata, vebitda, pbvdata, roe, margin, dbtfund), '
        'NYU Stern"',
        'url = "https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datacurrent.html"',
        f'as_of = "{as_of}"',
        "columns = [" + ", ".join(f'"{c}"' for c in ["firms"] + COLUMNS) + "]",
        "",
    ]
    for key, (code, label) in REGIONS.items():
        lines.append(f"[regions.{key}]")
        lines.append(f'label = "{label}"')
        lines.append(f'file_suffix = "{code}"')
        lines.append("")
        lines.append(f"[regions.{key}.industries]")
        for ind in sorted(regions[key]):
            lines.append(f'"{ind}" = [' + ", ".join(_fmt(x) for x in regions[key][ind]) + "]")
        lines.append("")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    return {k: len(v) for k, v in regions.items()}, as_of


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--lib", help="carpeta que contiene el paquete xlrd")
    a = ap.parse_args()
    if a.lib:
        sys.path.insert(0, os.path.expanduser(a.lib))
    counts, as_of = write(os.path.expanduser(a.raw), a.out)
    print(f"industrias por región: {counts}; actualización de Damodaran: {as_of}")


if __name__ == "__main__":
    main()
