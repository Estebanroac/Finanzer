"""
Verificación de la v4 (V2 · fuentes reales): informe a partir de tools/real_sources.py (V2_api.json) y del recorrido de
páginas (frontend/test-results/fuentes-reales/*.json). Escribe docs/rediseno/verificacion/V2_tablas.md: tasa de éxito y
tiempos por endpoint, páginas, y cada `sin_dato` con su motivo agrupado.

    ../../finanzer_next/.venv313/bin/python tools/real_sources_report.py
"""
import glob
import json
import os
import statistics
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
REPORT_DIR = os.path.normpath(os.path.join(HERE, "..", "..", "docs", "rediseno", "verificacion"))
PAGES_DIR = os.path.normpath(os.path.join(HERE, "..", "..", "frontend", "test-results", "fuentes-reales"))
# Lo que debe responder cada caso raro (no es un fallo): análisis y PDF con su 4xx y su motivo.
EXPECTED_4XX = {"SPY": 422, "ZZZZZ": 404, "SIVB": 404}


def pct(xs, q):
    xs = sorted(xs)
    if not xs:
        return None
    k = max(0, min(len(xs) - 1, int(round(q * (len(xs) - 1)))))
    return xs[k]


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default="V2_api", help="informe de real_sources.py (sin .json)")
    ap.add_argument("--out", default="V2_tablas")
    ap.add_argument("--no-pages", action="store_true")
    args = ap.parse_args()
    d = json.load(open(os.path.join(REPORT_DIR, f"{args.api}.json"), encoding="utf-8"))
    res = d["results"]
    ep = defaultdict(lambda: {"n": 0, "ok": 0, "4xx_esperado": 0, "fallo": [], "t": []})
    reasons = defaultdict(list)
    for r in res:
        sym = r["symbol"]
        for name, st in r["steps"].items():
            e = ep[name]
            e["n"] += 1
            code = st.get("status")
            if st.get("s") is not None and name != "peers":
                e["t"].append(st["s"])
            want = 422 if name.endswith("_422") else 200
            if code == want:
                e["ok"] += 1
            elif sym in EXPECTED_4XX and code == EXPECTED_4XX[sym] and name in ("analysis", "pdf_v2"):
                e["4xx_esperado"] += 1
            else:
                e["fallo"].append(f"{sym} ({code}{': ' + st['error'] if st.get('error') else ''})")
        p = r["steps"].get("peers") or {}
        if p.get("s") is not None:
            ep["peers"]["t"].append(p["s"])
        for k, v in (r.get("sin_dato") or {}).items():
            reasons[(k, v.split(":")[0][:90])].append(sym)
        pr = r["steps"].get("prices") or {}
        for k in ("company", "market", "sector"):
            if (pr.get(k) or {}).get("status") not in ("ok", None):
                reasons[(f"prices.{k}", str(pr[k].get("reason"))[:90])].append(sym)
        sg = r["steps"].get("segments") or {}
        if sg.get("seg_status") not in ("ok", None):
            reasons[("segments", str(sg.get("reason"))[:90])].append(sym)
        if p.get("peers_status") not in ("listo", None):
            reasons[("peers", str(p.get("note"))[:90])].append(sym)
        for rv, stt in (p.get("rivals") or {}).items():
            if not stt.startswith("listo"):
                reasons[("peers.rival", f"{rv}: {stt}"[:90])].append(sym)
    lines = [f"# V2 · tablas: {args.api} (generado por backend/tools/real_sources_report.py)", "",
             f"Recorrido de la API: {d['fecha']}, {len(res)} tickers, {d['duracion_s']} s. Semilla del universo: {d['seed']}.",
             "", "## Endpoints", "",
             "| Endpoint | n | Éxito | 4xx esperado | Fallos | p50 (s) | p95 (s) |", "|---|---|---|---|---|---|---|"]
    for name, e in ep.items():
        lines.append(f"| {name} | {e['n']} | {e['ok']} ({100 * e['ok'] / e['n']:.0f} %) | {e['4xx_esperado']} | "
                     f"{', '.join(e['fallo']) or '—'} | {pct(e['t'], .5)} | {pct(e['t'], .95)} |")
    pages = [] if args.no_pages else sorted(glob.glob(os.path.join(PAGES_DIR, "*.json")))
    if pages:
        n = bad = 0
        ms, issues = [], []
        for f in pages:
            for x in json.load(open(f, encoding="utf-8")):
                n += 1
                ms.append(x["ms"] / 1000)
                if x["errors"] or x["server5xx"] or x["undefined_or_nan"]:
                    bad += 1
                    issues.append(f"{x['url']}: {x['errors'][:2]} {x['server5xx'][:2]}")
        lines += ["", "## Páginas (historia y 9 páginas por ticker, escritorio)", "",
                  f"{n} páginas de {len(pages)} tickers: {n - bad} sin errores de consola, sin 5xx y sin «undefined/NaN» "
                  f"en el texto; {bad} con incidencias. Carga hasta red en reposo: p50 {pct(ms, .5):.2f} s, p95 {pct(ms, .95):.2f} s.",
                  ""] + [f"- {i}" for i in issues]
    lines += ["", "## Cada `sin_dato` con su motivo", "", "| Bloque | Motivo | Tickers |", "|---|---|---|"]
    for (k, why), syms in sorted(reasons.items(), key=lambda kv: (kv[0][0], -len(kv[1]))):
        lines.append(f"| {k} | {why} | {', '.join(syms)} |")
    out = os.path.join(REPORT_DIR, f"{args.out}.md")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
