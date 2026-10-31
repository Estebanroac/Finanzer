"""
PDF rápido: dónde se va el tiempo de los rivales de una empresa en frío. En un proceso nuevo y con las fuentes reales,
hace lo que el servidor al servir /api/analysis/{T} (el análisis y, F10 · N5, sus rivales en la cola compartida) y
pregunta por los rivales cada segundo hasta que están, como la página. Anota cada petición de red (host y ruta, sin la
consulta: la de Finnhub lleva la clave) y las fases: el ranking por tamaño (capitalizaciones), cada capitalización y
cada análisis de un rival, con su espera en la cola.

    cd backend
    FINNHUB_API_KEY="$(security find-generic-password -s finanzer-finnhub -w)" \\
    SEC_EDGAR_USER_AGENT="$(security find-generic-password -s finanzer-sec-ua -w)" \\
        ../../finanzer_next/.venv313/bin/python tools/perfil_rivales.py HD [--out x.json]
"""
import argparse
import json
import os
import sys
import time
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import perf_frio as PF  # noqa: E402 — su instrumentación de red y fases (y el sys.path del backend)


def main_cli() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("symbol")
    ap.add_argument("--timeout-s", type=float, default=240.0)
    ap.add_argument("--out")
    args = ap.parse_args()
    import logging
    logging.disable(logging.WARNING)
    PF.instrument()
    import main
    import peers
    import analysis_queue as AQ
    PF._wrap_phase(peers, "_rank_now", "rivales: ranking por tamaño")
    PF._wrap_phase(peers, "CAPS_FETCHER", "rivales: capitalización (Finnhub)")
    if getattr(peers, "CAPS_BATCH", None) is not None:
        PF._wrap_phase(peers, "CAPS_BATCH", "rivales: capitalizaciones (Yahoo, una petición)")
    PF._wrap_phase(AQ, "ANALYZE", "rivales: análisis de un rival")
    sym = args.symbol.upper()
    t0 = time.monotonic()
    analysis = main._compute_analysis(sym)
    t_analysis = time.monotonic() - t0
    main._start_peers(sym, analysis, None)
    status, t_ranked = None, None
    while time.monotonic() - t0 < args.timeout_s:
        r = peers.peers_for(sym)
        if t_ranked is None and (r["status"] != "calculando" or r.get("rivals")):
            t_ranked = time.monotonic() - t0
        status = r["status"]
        if status != "calculando":
            break
        time.sleep(1.0)
    total = time.monotonic() - t0
    rivals = [(x["symbol"], x["status"]) for x in r.get("rivals") or []]
    print(f"{sym}: análisis {t_analysis:.1f} s · ranking hecho a los {t_ranked or float('nan'):.1f} s · "
          f"rivales {status} a los {total:.1f} s · {rivals}")
    net = defaultdict(list)
    for e in PF.EVENTS:
        if e["kind"] == "net":
            host = e["name"].split("/", 1)[0]
            path = "/".join(e["name"].split("/")[1:3])
            net[(host, path)].append(e["dur"])
    for (host, path), ds in sorted(net.items(), key=lambda x: -sum(x[1])):
        print(f"  {host}/{path}: {len(ds)} peticiones, {sum(ds):.1f} s en total")
    ph = defaultdict(list)
    for e in PF.EVENTS:
        if e["kind"] == "phase" and e["name"].startswith("rivales"):
            ph[e["name"]].append((e["t"], e["dur"], e.get("arg")))
    for name, xs in ph.items():
        print(f"  [{name}] n={len(xs)} total {sum(d for _, d, _ in xs):.1f} s · de {min(t for t, _, _ in xs):.1f} s "
              f"a {max(t + d for t, d, _ in xs):.1f} s")
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump({"symbol": sym, "analysis_s": t_analysis, "ranked_s": t_ranked, "total_s": total,
                       "status": status, "rivals": rivals, "events": sorted(PF.EVENTS, key=lambda e: e["t"])}, fh,
                      ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main_cli()
