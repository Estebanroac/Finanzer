"""
F10 · N2b: región de la referencia por dónde opera y ROE estable global del P/B en dos etapas, de la evidencia en vivo
(docs/fiabilidad/f8_evidencia/<tag>/). Por empresa: región (y por qué), referencia, P/E y P/B de referencia, ROE de la
etapa estable, P/B justificado, convergencia, confianza, precio y nivel.

    cd backend && ../../finanzer_next/.venv313/bin/python tools/f10_n2b_tabla.py f10_n2 f10_n2b [--all] [SYM …]
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from f8_evidencia import AUDIT, load  # noqa: E402

FOCUS = ["CB", "PGR", "AIG", "NU", "JPM", "ITUB"]
REST = ["NVDA"] + [s for s in AUDIT if s not in ("NVDA", "CB", "JPM")] + ["TSM", "AAPL", "BRK-B"]


def _a(tag, s):
    d = load(tag, s)
    return d.get("analysis", d)


def _f(x, pct=False):
    if not isinstance(x, (int, float)):
        return "—"
    return (f"{x * 100:.1f} %" if pct else f"{x:.2f}").replace(".", ",")


def row(s, o, n):
    oi, ni = (o["benchmark"].get("industry") or {}), (n["benchmark"].get("industry") or {})
    op = ni.get("operating_region") or {}
    reg = f"{oi.get('region_label')} → {ni.get('region_label')}"
    why = op.get("reason") if op and op.get("region") != ni.get("domicile_region") else ""
    ov, nv = o["benchmark"].get("values") or {}, n["benchmark"].get("values") or {}
    ots = ((o.get("archetype_metrics") or {}).get("two_stage") or {})
    nts = ((n.get("archetype_metrics") or {}).get("two_stage") or {})
    opb = (o.get("archetype_metrics") or {}).get("pb_justified")
    npb = (n.get("archetype_metrics") or {}).get("pb_justified")
    oc, nc = o["confidence"], n["confidence"]
    ocv, ncv = oc["dimensions"]["convergence"]["level"], nc["dimensions"]["convergence"]["level"]
    op_, np_ = o["price_attractiveness"], n["price_attractiveness"]
    lvl = (op_.get("level") or "—") + ("" if op_.get("level") == np_.get("level") else f" → **{np_.get('level')}**")
    return (f"| {s} | {reg}{(' (' + why + ')') if why else ''} | {_f(ov.get('pe'))} → {_f(nv.get('pe'))} | "
            f"{_f(ov.get('pb'))} → {_f(nv.get('pb'))} | {_f(ots.get('industry_roe'), True)} → "
            f"{_f(nts.get('industry_roe'), True)} | {_f(opb)} → {_f(npb)} | {ocv} → {ncv} | "
            f"{oc['level']} → {nc['level']} | {op_.get('score')} → {np_.get('score')} | {lvl} |")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("before")
    ap.add_argument("after")
    ap.add_argument("--all", action="store_true", help="también las que no cambian")
    ap.add_argument("syms", nargs="*")
    a = ap.parse_args()
    head = ["Empresa", "Región de la referencia", "P/E ref.", "P/B ref.", "ROE estable", "P/B justificado",
            "Convergencia", "Confianza", "Precio", "Nivel"]
    print("| " + " | ".join(head) + " |\n|" + "---|" * len(head))
    for s in (a.syms or FOCUS + REST):
        try:
            o, n = _a(a.before, s), _a(a.after, s)
        except FileNotFoundError:
            print(f"| {s} | falta |" + " |" * (len(head) - 2))
            continue
        r = row(s, o, n)
        same = all(x.split(" → ")[0].strip() == x.split(" → ")[-1].strip() for x in r.split("|")[2:-1] if " → " in x)
        if a.all or a.syms or s in FOCUS or not same:
            print(r)


if __name__ == "__main__":
    main()
