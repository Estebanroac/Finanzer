"""F3 · T1: efecto en el veredicto de las definiciones propuestas (what-if en replay; no toca el motor).

Escenarios (cada uno sobre la línea base, y todos juntos):
  ebit   : beneficio operativo = OperatingIncomeLoss / ProfitLossFromOperatingActivities de EDGAR (TTM, FY0, FY1)
           donde Yahoo difiere fuera de tolerancia (Yahoo construye el suyo);
  ingresos_brk : BRK-B, ingresos sin ganancias de inversión (us-gaap:Revenues de EDGAR);
  capex_cat    : CAT, capex sin el equipo arrendado a terceros de Cat Financial (PP&E de EDGAR).
uso: cd backend && ../../finanzer_next/.venv313/bin/python tests/f3_t1_whatif.py OUT_DIR
"""
import copy
import json
import logging
import sys
from pathlib import Path

B = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(B), str(B / "lib"), str(B / "tests")]
logging.disable(logging.CRITICAL)
import edgar_verify as ev  # noqa: E402

FYKEY = {"operating_income": ["operating_income", "ebit"], "revenue": ["revenue"],
         "capital_expenditure": ["capital_expenditure"]}
TTMKEY = {"operating_income": "operatingIncome", "revenue": "totalRevenue", "capex": "capitalExpenditures"}


def build_patch(cap, rows, want):
    """want: {campo_base: predicado(fila)} → patch de info (TTM y _statements_fy)."""
    info = cap["info"]
    patch, fy = {}, None
    for r in rows:
        if r["estado"] != "fuera" or r.get("edgar") is None:
            continue
        camp = r["campo"]
        base = camp.split(".", 1)[1] if camp.startswith("FY") else camp
        pred = want.get(base) or (want.get("capex") if base == "capital_expenditure" else None)
        if not pred or not pred(r):
            continue
        v = r["edgar"] * (r.get("tasa") or 1.0)
        if base in ("capex", "capital_expenditure"):
            v = -abs(v)
        if camp.startswith("FY"):
            i = int(camp[2])
            if fy is None:
                fy = copy.deepcopy(info.get("_statements_fy") or {})
            for k in FYKEY.get(base, []):
                if isinstance(fy.get(k), list) and len(fy[k]) > i:
                    fy[k][i] = v
        else:
            patch[TTMKEY[base]] = v
    if fy is not None:
        patch["_statements_fy"] = fy
    return patch


SCEN = {
    "ebit": {"operating_income": lambda r: True},
    "ingresos_brk": {"revenue": lambda r: r["ticker"] == "BRK-B"},
    "capex_cat": {"capex": lambda r: r["ticker"] == "CAT"},
}
SCEN["todo"] = {k: v for s in SCEN.values() for k, v in s.items()}
SCEN["todo"]["revenue"] = SCEN["ingresos_brk"]["revenue"]
SCEN["todo"]["capex"] = SCEN["capex_cat"]["capex"]


def main():
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    res = {}
    for t in ev.fb.env_tickers("panel"):
        p = ev.E.EDGAR_DIR / f"{t}.json"
        if not p.exists():
            continue
        cap = ev.capture(t)
        if cap.get("fs") is None:
            continue
        rows = ev.compare_ticker(t, json.loads(p.read_text()), cap)
        base = ev.levels(cap["analysis"])
        res[t] = {"base": base}
        for name, want in SCEN.items():
            patch = build_patch(cap, rows, want)
            if not patch:
                continue
            alt = ev.levels(ev.capture(t, patch)["analysis"])
            res[t][name] = {"niveles": alt, "claves": sorted(patch)}
        ch = {n: v["niveles"] for n, v in res[t].items() if n != "base" and v["niveles"] != base}
        print(t, "sin cambios" if not ch else "", flush=True)
        for n, lv in ch.items():
            d = {k: (base[k], lv[k]) for k in lv if lv[k] != base[k]}
            print(f"   {n}: {d}", flush=True)
    (out / "whatif_t1.json").write_text(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
