"""
Fusiona las carpetas de captura en paralelo (fixtures_0, fixtures_1, …) en una sola con la forma del banco de F13:
<T>/, f2b/ (edgar/*, finnhub_calendar/, company_tickers.json y metadata.json fusionados), segments/, _captura/.

    python -I tests/hacia_atras/fusionar.py --out <carpeta> <origen> [<origen> …]
"""
import argparse
import json
import os
import shutil


def _rj(p, d):
    try:
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        return d


def _wj(p, o):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(o, fh, indent=1, ensure_ascii=False, sort_keys=True)
        fh.write("\n")


def copy_tree(src, dst):
    for root, _dirs, files in os.walk(src):
        rel = os.path.relpath(root, src)
        os.makedirs(os.path.join(dst, rel), exist_ok=True)
        for f in files:
            d = os.path.join(dst, rel, f)
            if not os.path.exists(d):
                shutil.copy2(os.path.join(root, f), d)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("src", nargs="+")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    table, meta, state = {}, {"symbols": {}}, {}
    facts_syms = {}
    for s in a.src:
        for name in os.listdir(s):
            p = os.path.join(s, name)
            if name in ("f2b", "_captura") or not os.path.isdir(p) or name.endswith(".tmp"):
                continue
            copy_tree(p, os.path.join(a.out, name))
        f2b = os.path.join(s, "f2b")
        for sub in ("edgar", "finnhub_calendar"):
            if os.path.isdir(os.path.join(f2b, sub)):
                copy_tree(os.path.join(f2b, sub), os.path.join(a.out, "f2b", sub))
        table.update(_rj(os.path.join(f2b, "edgar", "company_tickers.json"), {}))
        m = _rj(os.path.join(f2b, "metadata.json"), {})
        meta.update({k: v for k, v in m.items() if k not in ("symbols", "facts")})
        meta["symbols"].update(m.get("symbols") or {})
        facts_syms.update((m.get("facts") or {}).get("symbols") or {})
        if m.get("facts"):
            meta["facts"] = {k: v for k, v in m["facts"].items() if k != "symbols"}
        state.update(_rj(os.path.join(s, "_captura", "estado.json"), {}))
        if os.path.isdir(os.path.join(s, "_captura", "logs")):
            copy_tree(os.path.join(s, "_captura", "logs"), os.path.join(a.out, "_captura", "logs"))
    if "facts" in meta:
        meta["facts"]["symbols"] = facts_syms
    with open(os.path.join(a.out, "f2b", "edgar", "company_tickers.json"), "w", encoding="utf-8") as fh:
        json.dump(table, fh, separators=(",", ":"), ensure_ascii=False, sort_keys=True)
        fh.write("\n")
    _wj(os.path.join(a.out, "f2b", "metadata.json"), meta)
    _wj(os.path.join(a.out, "_captura", "estado.json"), state)
    ok = [k for k, v in state.items() if v.get("ok")]
    print(f"{len(ok)} capturadas, {len(state) - len(ok)} fallidas: {sorted(k for k, v in state.items() if not v.get('ok'))}")


if __name__ == "__main__":
    main()
