"""
PDF rápido: cuánto tarda el primer PDF de una empresa y sus rivales, en frío. Por cada símbolo, un proceso nuevo
(tools/load_server.py, fuentes reales, sin precalentado de tendencias) que ya terminó su arranque (la descarga de las
tendencias del universo, 543 peticiones a Yahoo, compite con todo lo demás; --sin-esperar-tendencias para medir justo al
arrancar): pide /api/analysis/{T} como la página y, en
cuanto llega, el PDF (/api/v2/pdf/{T}), como quien pulsa «Descargar PDF». A la vez pregunta por los rivales
(/api/v2/peers/{T}) cada segundo hasta que están. Anota los segundos de cada cosa desde que se pidió el análisis.

    cd backend
    FINNHUB_API_KEY="$(security find-generic-password -s finanzer-finnhub -w)" \\
    SEC_EDGAR_USER_AGENT="$(security find-generic-password -s finanzer-sec-ua -w)" \\
        ../../finanzer_next/.venv313/bin/python tools/pdf_medida.py NVDA HD --name PDF_despues [--backend otro/backend]
Las claves llegan por el entorno; aquí no se leen ni se escriben.
"""
import argparse
import json
import os
import subprocess
import sys
import threading
import time
from typing import Any, Dict

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(HERE)
REPORT_DIR = os.path.join(os.path.dirname(BACKEND), "docs", "rediseno", "verificacion")


def one(sym: str, backend: str, port: int, snapshot: str, wait_trending: bool = True) -> Dict[str, Any]:
    cmd = [sys.executable, os.path.join(HERE, "load_server.py"), "--port", str(port), "--backend", backend, "--no-prewarm"]
    # La lista de tendencias guardada (portada rápida): cada proceso nuevo la recupera en vez de descargar otra vez el
    # universo (543 peticiones a Yahoo por arranque; con 20 arranques, Yahoo limita y la medida no vale).
    env = {**os.environ, "FINANZER_PORTADA_SNAPSHOT": snapshot}
    proc = subprocess.Popen(cmd, cwd=BACKEND, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = f"http://127.0.0.1:{port}"
    out: Dict[str, Any] = {"symbol": sym}
    try:
        with requests.Session() as s:
            t_boot = time.monotonic()
            while True:
                try:
                    if s.get(f"{base}/api/health", timeout=5).status_code == 200:
                        break
                except requests.RequestException:
                    pass
                if time.monotonic() - t_boot > 120:
                    raise SystemExit("el servidor no arrancó")
                time.sleep(0.2)
            if wait_trending:
                while time.monotonic() - t_boot < 180:
                    tr = s.get(f"{base}/api/v2/trending", params={"period": "1D"}, timeout=30).json()
                    if tr["status"] != "calculando" and not tr.get("refreshing"):
                        break
                    time.sleep(1.0)
                out["tendencias_listas_s"] = round(time.monotonic() - t_boot, 1)
            t0 = time.monotonic()
            r = s.get(f"{base}/api/analysis/{sym}", timeout=180)
            out["analysis"] = {"status": r.status_code, "s": round(time.monotonic() - t0, 2)}
            peers: Dict[str, Any] = {}

            def poll():
                with requests.Session() as p:
                    while time.monotonic() - t0 < 300:
                        b = p.get(f"{base}/api/v2/peers/{sym}", timeout=30).json()
                        if b.get("status") != "calculando":
                            peers.update(status=b.get("status"), s=round(time.monotonic() - t0, 2),
                                         rivals=[(x["symbol"], x["status"]) for x in b.get("rivals") or []])
                            return
                        time.sleep(1.0)
                    peers.update(status="sin terminar a los 300 s", s=None)
            th = threading.Thread(target=poll, daemon=True)
            th.start()
            t1 = time.monotonic()
            pdf = s.get(f"{base}/api/v2/pdf/{sym}", timeout=180)
            out["pdf"] = {"status": pdf.status_code, "s": round(time.monotonic() - t1, 2),
                          "desde_el_analisis_s": round(time.monotonic() - t0, 2), "bytes": len(pdf.content)}
            th.join(310)
            out["peers"] = peers
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=20)
        except subprocess.TimeoutExpired:
            proc.kill()
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("symbols", nargs="+")
    ap.add_argument("--backend", default=BACKEND)
    ap.add_argument("--antes", help="otro backend (el «antes»): por cada símbolo se miden los dos, alternando el orden")
    ap.add_argument("--snapshot", default=os.path.join(BACKEND, ".cache", "pdf_medida_portada.json"),
                    help="archivo de la lista de tendencias que comparten los arranques (fuera de git)")
    ap.add_argument("--port", type=int, default=8795)
    ap.add_argument("--sin-esperar-tendencias", action="store_true")
    ap.add_argument("--name", required=True)
    args = ap.parse_args()
    sides = [("despues", os.path.abspath(args.backend))]
    if args.antes:
        sides.insert(0, ("antes", os.path.abspath(args.antes)))
    res: Dict[str, list] = {k: [] for k, _ in sides}
    for i, sym in enumerate(args.symbols):
        for side, backend in (sides if i % 2 == 0 else sides[::-1]):     # el orden se alterna: igual para los dos
            r = one(sym.upper(), backend, args.port, args.snapshot, not args.sin_esperar_tendencias)
            print(f"{side:7} {r['symbol']}: análisis {r['analysis']['s']} s · primer PDF {r['pdf']['s']} s "
                  f"({r['pdf']['status']}) · rivales {r['peers'].get('status')} a los {r['peers'].get('s')} s", flush=True)
            res[side].append(r)
    with open(os.path.join(REPORT_DIR, f"{args.name}.json"), "w", encoding="utf-8") as fh:
        json.dump({"backends": dict(sides), "fecha": time.strftime("%Y-%m-%dT%H:%M:%S"), "results": res}, fh,
                  ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
