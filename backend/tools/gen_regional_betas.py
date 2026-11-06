"""
F9 · R2b (decisión del PM del 27-oct): genera config/betas_regional.toml con las betas por industria de Damodaran de
Europa y de los mercados emergentes, para la beta de abajo hacia arriba de una empresa que opera allí (lib/beta.py).
Las de EE. UU. siguen en config/betas.toml. F14 · paso 6: y la global, la que se usa cuando la industria de la región
tiene menos empresas que `sectors.benchmarks.industry.min_firms` (la misma regla que las referencias).

    curl -o /tmp/betaEurope.xls https://pages.stern.nyu.edu/~adamodar/pc/datasets/betaEurope.xls
    curl -o /tmp/betaemerg.xls  https://pages.stern.nyu.edu/~adamodar/pc/datasets/betaemerg.xls
    curl -o /tmp/betaGlobal.xls https://pages.stern.nyu.edu/~adamodar/pc/datasets/betaGlobal.xls
    python -I tools/gen_regional_betas.py --lib <carpeta con xlrd> /tmp/betaEurope.xls /tmp/betaemerg.xls \\
        /tmp/betaGlobal.xls 2026-01 2026-11-06

xlrd solo hace falta para esta herramienta (no es una dependencia de la app). Hoja «Industry Averages», las mismas
columnas que la tabla de EE. UU.: [industries] = [empresas, beta media apalancada] (la de las financieras) y
[unlevered] = [empresas, βU corregida por caja, D/E, t] (la que se reapalanca).
"""
import argparse
import os
import sys

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "betas_regional.toml")
URL = "https://pages.stern.nyu.edu/~adamodar/pc/datasets/{}.xls"
REGIONS = (("europe", "betaEurope", "Europa"), ("emerging", "betaemerg", "mercados emergentes"),
           ("global", "betaGlobal", "global"))


def _rows(xlrd, path):
    sh = xlrd.open_workbook(path).sheet_by_name("Industry Averages")
    head = next(i for i in range(sh.nrows) if str(sh.row_values(i)[0]).startswith("Industry Name"))
    cols = [str(c).strip() for c in sh.row_values(head)]
    ix = {k: cols.index(k) for k in ("Number of firms", "Beta", "D/E Ratio", "Effective Tax rate",
                                      "Unlevered beta corrected for cash")}
    out = {}
    for i in range(head + 1, sh.nrows):
        v = sh.row_values(i)
        name = str(v[0]).strip()
        if not name or name.startswith(("Total Market", "Grand Total")):
            continue
        try:
            out[name] = [int(v[ix["Number of firms"]]), float(v[ix["Beta"]]), float(v[ix["D/E Ratio"]]),
                         float(v[ix["Effective Tax rate"]]), float(v[ix["Unlevered beta corrected for cash"]])]
        except (TypeError, ValueError):
            continue
    return out


def _q(s):
    return '"' + s.replace('"', '\\"') + '"'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lib", required=True)
    ap.add_argument("europe")
    ap.add_argument("emerging")
    ap.add_argument("global_", metavar="global")
    ap.add_argument("as_of")
    ap.add_argument("consulted")
    a = ap.parse_args()
    sys.path.insert(0, a.lib)
    import xlrd
    lines = [
        "# F9 · R2b (decisión del PM del 27-oct): betas por industria de A. Damodaran para Europa y los mercados",
        "# emergentes (la de EE. UU. está en betas.toml); F14 · paso 6: y la global (industrias con pocas empresas en su",
        "# región). GENERADO por backend/tools/gen_regional_betas.py: no editar a mano; regenerar cada enero con las",
        "# demás tablas de Damodaran (review.toml). Uso: lib/beta.py.",
        "",
        f'as_of = "{a.as_of}"',
        f'consulted = "{a.consulted}"',
    ]
    for key, fname, label in REGIONS:
        rows = _rows(xlrd, getattr(a, "global_" if key == "global" else key))
        if len(rows) < 80:
            sys.exit(f"{fname}: solo {len(rows)} industrias")
        lines += ["", f"[{key}]", f'source = "A. Damodaran, Betas by Sector ({label}), NYU Stern, {a.as_of}"',
                  f'url = "{URL.format(fname)}"', "",
                  f"[{key}.industries]               # industria -> [empresas, beta media apalancada]",
                  *[f"{_q(k)} = [{r[0]}, {r[1]:.4f}]" for k, r in sorted(rows.items())], "",
                  f"[{key}.unlevered]                # industria -> [empresas, βU corregida por caja, D/E, t]",
                  *[f"{_q(k)} = [{r[0]}, {r[4]:.4f}, {r[2]:.4f}, {r[3]:.4f}]" for k, r in sorted(rows.items())]]
        print(f"{label}: {len(rows)} industrias")
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"escrito {OUT}")


if __name__ == "__main__":
    main()
