"""
Pasada final de la v4 (V2 · fuentes reales, la portada tras P8b): /api/v2/trending y /api/v2/sparklines contra un
backend real que ya está en marcha (tools/load_server.py, con las claves en su entorno; ver tools/real_sources.py).

    ../../finanzer_next/.venv313/bin/python tools/real_home.py --base http://127.0.0.1:8771 [--name V2_portada]

Espera a que las tendencias estén «listo» (en frío se calculan) y, por cada periodo, comprueba las tres listas:
«Bajan más» solo con valores que bajan y «Suben más» solo con los que suben, sin repetidos; y pide las mini-gráficas
de cada lista (como la portada: hasta `max_symbols` por petición), con su estado, tiempo y motivo de cada `sin_dato`.
Aquí no se leen claves. Informe: ../docs/rediseno/verificacion/<name>.json y .md. Código de salida 1 si algo falla.
"""
import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
REPORT_DIR = os.path.normpath(os.path.join(HERE, "..", "..", "docs", "rediseno", "verificacion"))
TRENDING_TIMEOUT_S = 600
POLL_S = 5
SIGN = {"gainers": 1, "losers": -1}


def get(base: str, path: str):
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(base + path, timeout=120) as r:
            return r.status, json.load(r), time.monotonic() - t0
    except urllib.error.HTTPError as e:
        return e.code, None, time.monotonic() - t0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8771")
    ap.add_argument("--name", default="V2_portada")
    ap.add_argument("--max-symbols", type=int, default=40)
    args = ap.parse_args()
    problems, report = [], {"fecha": time.strftime("%Y-%m-%dT%H:%M:%S"), "base": args.base}

    t0, polls, status, tr = time.monotonic(), 0, None, None
    while time.monotonic() - t0 < TRENDING_TIMEOUT_S:
        status, tr, _ = get(args.base, "/api/v2/trending")
        polls += 1
        if status != 200:
            problems.append(f"trending: HTTP {status}")
            break
        if tr["status"] != "calculando":
            break
        time.sleep(POLL_S)
    report["trending"] = {"status": tr and tr["status"], "s": round(time.monotonic() - t0, 2), "polls": polls,
                          "reason": tr and tr.get("reason")}
    if not tr or tr["status"] != "listo":
        problems.append(f"trending: {report['trending']}")
        return finish(args, report, problems)
    data = tr["data"]
    report["trending"].update(count=data.get("count"), failed_batches=data.get("failed_batches"),
                              universe_date=data.get("universe_date"))

    periods = {}
    for per, lists in data["lists"].items():
        out = {}
        for key, items in lists.items():
            syms = [x["symbol"] for x in items]
            row = {"n": len(items), "repetidos": len(syms) - len(set(syms))}
            if key in SIGN:
                wrong = [f"{x['symbol']} {x['change_pct']:+.2f}%" for x in items
                         if x.get("change_pct") is None or x["change_pct"] * SIGN[key] <= 0]
                row["signo_mal"] = wrong
                if wrong:
                    problems.append(f"{per} · {key}: valores con el signo contrario {wrong[:5]}")
            if row["repetidos"]:
                problems.append(f"{per} · {key}: {row['repetidos']} repetidos")
            # las mini-gráficas de la lista, en el periodo
            sp = {"ok": 0, "sin_dato": 0, "motivos": Counter(), "s": []}
            for i in range(0, len(syms), args.max_symbols):
                q = urllib.parse.urlencode({"symbols": ",".join(syms[i:i + args.max_symbols]), "period": per})
                st, body, dt = get(args.base, f"/api/v2/sparklines?{q}")
                sp["s"].append(round(dt, 2))
                if st != 200:
                    problems.append(f"{per} · {key}: sparklines HTTP {st}")
                    continue
                for it in (body.get("items") or {}).values():        # {símbolo: {status, …}}
                    if it.get("status") == "ok":
                        sp["ok"] += 1
                    else:
                        sp["sin_dato"] += 1
                        sp["motivos"][it.get("reason") or "sin motivo"] += 1
            sp["motivos"] = dict(sp["motivos"])
            row["sparklines"] = sp
            out[key] = row
        periods[per] = {"info": data["periods"].get(per), "lists": out}
    report["periods"] = periods
    return finish(args, report, problems)


def finish(args, report, problems) -> int:
    report["problemas"] = problems
    os.makedirs(REPORT_DIR, exist_ok=True)
    with open(os.path.join(REPORT_DIR, f"{args.name}.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=1)
    L = [f"# V2 · portada con fuentes reales ({report['fecha']})", "",
         f"Tendencias: **{report['trending'].get('status')}** en {report['trending'].get('s')} s "
         f"({report['trending'].get('polls')} consultas); universo {report['trending'].get('count')}, "
         f"lotes fallidos {report['trending'].get('failed_batches')}.", "",
         "| periodo | lista | valores | signo contrario | mini-gráficas ok / sin dato | tiempo (s) | motivos |",
         "|---|---|---|---|---|---|---|"]
    for per, p in (report.get("periods") or {}).items():
        for key, r in p["lists"].items():
            sp = r["sparklines"]
            L.append(f"| {per} | {key} | {r['n']} | {len(r.get('signo_mal') or []) if key in SIGN else '—'} | "
                     f"{sp['ok']} / {sp['sin_dato']} | {', '.join(map(str, sp['s']))} | "
                     f"{'; '.join(f'{k} ({v})' for k, v in sp['motivos'].items()) or '—'} |")
    L += ["", f"**Problemas: {len(problems)}.**"] + [f"- {p}" for p in problems]
    with open(os.path.join(REPORT_DIR, f"{args.name}.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    print("\n".join(L[-(len(problems) + 1):]))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
