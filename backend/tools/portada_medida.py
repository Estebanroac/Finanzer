"""
Portada rápida: cuánto espera quien abre la portada (/v2) a sus tarjetas y mini-gráficas, con el backend real y las
fuentes reales (tools/load_server.py), en frío y en caliente. Hace lo mismo que la web (frontend/src/v2/home/
TickerStrip.tsx): pide /api/v2/trending?period=1D cada `poll_s` mientras dice «calculando» y, con las tarjetas de «Más
negociadas», sus mini-gráficas de 1D.

  · frío: proceso nuevo; el visitante llega en cuanto el servidor responde (`--arrive-s` después, si se pide). Con
    `--snapshot RUTA`, el archivo de la última lista buena es ese (`--fresh`: se borra antes: arranque sin nada).
  · caliente: el mismo proceso, otra visita.
  · TTL vencido: con la vida de las mini-gráficas de 1D acortada a `--ttl-s`, otra visita pasado ese tiempo.

Además, el pico de memoria (RSS) del proceso durante la medida.

    ../../finanzer_next/.venv313/bin/python tools/portada_medida.py --name PORTADA_antes
    ../../finanzer_next/.venv313/bin/python tools/portada_medida.py --backend ../../otro/backend --name ...
Las claves llegan por el entorno; aquí no se leen ni se escriben.
"""
import argparse
import json
import os
import subprocess
import sys
import threading
import time
from typing import Any, Dict, List, Optional

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(HERE)
REPORT_DIR = os.path.join(os.path.dirname(BACKEND), "docs", "rediseno", "verificacion")


def rss_mb(pid: int) -> Optional[float]:
    out = subprocess.run(["ps", "-o", "rss=", "-p", str(pid)], capture_output=True, text=True).stdout.strip()
    return int(out) / 1024 if out else None


def visit(c: requests.Session, base: str, period: str = "1D", timeout_s: float = 300) -> Dict[str, Any]:
    """Una visita a la portada: segundos hasta las tarjetas (y cuántas llegaron «calculando»), y hasta sus
    mini-gráficas."""
    t0 = time.monotonic()
    polls = 0
    while True:
        r = c.get(f"{base}/api/v2/trending", params={"period": period}, timeout=120).json()
        polls += 1
        cards = (((r.get("data") or {}).get("lists") or {}).get(period) or {}).get("most_traded") or []
        if cards:
            break
        if r["status"] == "sin_dato" or time.monotonic() - t0 > timeout_s:
            return {"cards_s": None, "status": r["status"], "reason": r.get("reason"), "polls": polls}
        time.sleep(r.get("poll_s") or 4)
    t_cards = time.monotonic() - t0
    syms = [x["symbol"] for x in cards]
    t1 = time.monotonic()
    sp = c.get(f"{base}/api/v2/sparklines", params={"symbols": ",".join(syms), "period": period},
               timeout=120).json()
    t_sp = time.monotonic() - t1
    ok = sum(1 for it in sp["items"].values() if it.get("status") == "ok")
    return {"cards_s": round(t_cards, 2), "polls": polls, "cards": len(syms), "status": r["status"],
            "refreshing": r.get("refreshing"), "stale": (r.get("data") or {}).get("stale"),
            "sparklines_s": round(t_sp, 2), "sparklines_ok": ok, "total_s": round(time.monotonic() - t0, 2),
            "symbols": syms}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", default=BACKEND)
    ap.add_argument("--port", type=int, default=8796)
    ap.add_argument("--ttl-s", type=float, default=20.0, help="vida de las mini-gráficas de 1D en la medida del TTL")
    ap.add_argument("--arrive-s", type=float, default=0.0, help="el visitante llega estos segundos tras el arranque")
    ap.add_argument("--snapshot", help="archivo de la última lista buena (FINANZER_PORTADA_SNAPSHOT del servidor)")
    ap.add_argument("--fresh", action="store_true", help="borra antes el archivo de --snapshot")
    ap.add_argument("--name", required=True)
    args = ap.parse_args()
    py = sys.executable
    cmd = [py, os.path.join(HERE, "load_server.py"), "--port", str(args.port), "--backend", os.path.abspath(args.backend),
           "--set", f"market.sparklines.periods.1D.ttl_s={int(args.ttl_s)}"]
    env = dict(os.environ)
    if args.snapshot:
        env["FINANZER_PORTADA_SNAPSHOT"] = os.path.abspath(args.snapshot)
        if args.fresh and os.path.exists(args.snapshot):
            os.remove(args.snapshot)
    t_start = time.monotonic()
    proc = subprocess.Popen(cmd, cwd=BACKEND, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    peak = [0.0]
    stop = threading.Event()

    def sampler():
        while not stop.is_set():
            m = rss_mb(proc.pid)
            if m:
                peak[0] = max(peak[0], m)
            time.sleep(0.5)
    threading.Thread(target=sampler, daemon=True).start()
    base = f"http://127.0.0.1:{args.port}"
    out: Dict[str, Any] = {"backend": os.path.abspath(args.backend), "fecha": time.strftime("%Y-%m-%dT%H:%M:%S"),
                           "snapshot": bool(args.snapshot), "fresh": args.fresh}
    try:
        with requests.Session() as c:
            while True:
                try:
                    if c.get(f"{base}/api/health", timeout=5).status_code == 200:
                        break
                except requests.RequestException:
                    pass
                if proc.poll() is not None or time.monotonic() - t_start > 120:
                    raise SystemExit(f"el servidor no arrancó: {proc.stderr.read()[-2000:] if proc.stderr else ''}")
                time.sleep(0.1)
            out["ready_s"] = round(time.monotonic() - t_start, 2)
            if args.arrive_s:
                time.sleep(args.arrive_s)
            out["arrive_s"] = args.arrive_s
            out["frio"] = visit(c, base)
            out["caliente"] = visit(c, base)
            wait = args.ttl_s + 1 - (time.monotonic() - t_start - out["ready_s"] - out["frio"]["total_s"])
            time.sleep(max(0.0, wait))
            out["ttl_vencido"] = visit(c, base)
            out["ttl_vencido_2"] = visit(c, base)     # justo después: lo refrescado en segundo plano
            out["pico_rss_mb"] = round(peak[0], 1)
    finally:
        stop.set()
        proc.terminate()
        try:
            proc.wait(timeout=20)
        except subprocess.TimeoutExpired:
            proc.kill()
    os.makedirs(REPORT_DIR, exist_ok=True)
    with open(os.path.join(REPORT_DIR, f"{args.name}.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    for k in ("frio", "caliente", "ttl_vencido", "ttl_vencido_2"):
        v = {x: y for x, y in out[k].items() if x != "symbols"}
        print(k, v)
    print("listo para servir", out["ready_s"], "s; pico RSS", out["pico_rss_mb"], "MB")


if __name__ == "__main__":
    main()
