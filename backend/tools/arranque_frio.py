"""
E6 · paso 5 (arranque en frío en Render): qué ve un visitante en los primeros minutos tras un despliegue. Al arrancar,
el servidor no tiene la instantánea de la portada (el disco de Render es efímero) y calcula las tendencias (543
peticiones a Yahoo), precalienta 30 tarjetas y, con la primera visita a una empresa, sus rivales; todo en una CPU de
cuota pequeña.

Arranca tools/load_server.py (backend real, fuentes reales) sin instantánea, le limita la CPU como una cuota de Linux
(cada `--period-ms`, solo `--cpu` de ese tiempo en marcha: SIGSTOP / SIGCONT al proceso; macOS no tiene taskset ni
cgroups) y, cada `--every` s durante `--seconds`, pide a la vez health, la búsqueda, las tendencias y las mini-gráficas
de la portada. Escribe docs/rediseno/verificacion/<name>.json y .md.

    FINNHUB_API_KEY=… SEC_EDGAR_USER_AGENT=… ../.venv313/bin/python tools/arranque_frio.py --cpu 0.1 --name X

Las claves llegan por el entorno y pasan al servidor; aquí no se leen ni se escriben.
"""
import argparse
import json
import os
import signal
import statistics
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(HERE)
OUT_DIR = os.path.join(BACKEND, "..", "docs", "rediseno", "verificacion")
QUERIES = ["apple", "micro", "coca", "bank", "nvidia", "tesla", "amaz", "pfizer", "exxon", "visa"]


def fetch(url: str, timeout: float) -> dict:
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            body = r.read()
            return {"code": r.status, "s": round(time.monotonic() - t0, 3), "body": body}
    except Exception as e:  # noqa: BLE001 — un fallo es una medida más
        return {"code": getattr(e, "code", None) or type(e).__name__, "s": round(time.monotonic() - t0, 3), "body": b""}


def limiter(pid: int, cpu: float, period_ms: int, stop: threading.Event) -> None:
    """Cuota de CPU: `cpu` de cada periodo en marcha, el resto parado."""
    on, off = period_ms * cpu / 1000, period_ms * (1 - cpu) / 1000
    while not stop.is_set():
        time.sleep(on)
        try:
            os.kill(pid, signal.SIGSTOP)
            time.sleep(off)
            os.kill(pid, signal.SIGCONT)
        except ProcessLookupError:
            return
    try:
        os.kill(pid, signal.SIGCONT)
    except ProcessLookupError:
        pass


def sample(base: str, i: int, timeout: float) -> dict:
    res: dict = {}
    q = QUERIES[i % len(QUERIES)]
    urls = {
        "health": f"{base}/api/health",
        "search": f"{base}/api/v2/search?q={q}",
        "trending": f"{base}/api/v2/trending?period=1D",
        "sparklines": f"{base}/api/v2/sparklines?symbols=AAPL,MSFT,NVDA&period=1D",
    }

    def one(k, u):
        r = fetch(u, timeout)
        if k == "trending" and r["body"]:
            try:
                d = json.loads(r["body"])
                cards = ((d.get("data") or {}).get("lists") or {}).get("1D", {}).get("most_traded") or []
                r["status"] = d.get("status")
                r["scored"] = sum(1 for c in cards if (c.get("engine") or {}).get("status") == "listo")
            except ValueError:
                pass
        if k == "search" and r["body"]:
            try:
                r["n"] = len(json.loads(r["body"]).get("results") or [])
            except ValueError:
                pass
        r.pop("body", None)
        res[k] = r

    ts = [threading.Thread(target=one, args=kv) for kv in urls.items()]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8795)
    ap.add_argument("--cpu", type=float, default=1.0, help="fracción de CPU (1 = sin límite)")
    ap.add_argument("--period-ms", type=int, default=100)
    ap.add_argument("--seconds", type=int, default=180)
    ap.add_argument("--every", type=float, default=5)
    ap.add_argument("--timeout", type=float, default=30)
    ap.add_argument("--backend", default=BACKEND, help="carpeta backend que se arranca (otra rama, para comparar)")
    ap.add_argument("--snapshot", help="arrancar con este archivo de la portada (el del build: tools/portada_build.py)")
    ap.add_argument("--name", required=True)
    a = ap.parse_args()
    base = f"http://127.0.0.1:{a.port}"
    # Render: sin la instantánea del disco; con --snapshot, la del build
    env = dict(os.environ, FINANZER_PORTADA_SNAPSHOT=os.path.abspath(a.snapshot) if a.snapshot else "0")
    log = open(os.path.join(tempfile.gettempdir(), f"{a.name}.server.log"), "w")      # fuera del repositorio
    srv = subprocess.Popen([sys.executable, os.path.join(a.backend, "tools", "load_server.py"), "--port", str(a.port)],
                           cwd=a.backend, env=env, stdout=log, stderr=subprocess.STDOUT)
    stop = threading.Event()
    try:
        # el arranque (importar y abrir el puerto) sin límite: Render lo hace antes de recibir tráfico
        for _ in range(240):
            if fetch(f"{base}/api/health", 2)["code"] == 200:
                break
            time.sleep(0.5)
        else:
            print("el servidor no arrancó")
            return 1
        if a.cpu < 1:
            threading.Thread(target=limiter, args=(srv.pid, a.cpu, a.period_ms, stop), daemon=True).start()
        t0 = time.monotonic()
        rows, i, threads = [], 0, []
        lock = threading.Lock()
        while time.monotonic() - t0 < a.seconds:
            at = round(time.monotonic() - t0, 1)

            def run(i=i, at=at):
                r = sample(base, i, a.timeout)
                with lock:
                    rows.append({"t": at, **r})
            th = threading.Thread(target=run)
            th.start()
            threads.append(th)
            i += 1
            time.sleep(a.every)
        for th in threads:
            th.join()
    finally:
        stop.set()
        time.sleep(0.2)
        try:
            os.kill(srv.pid, signal.SIGCONT)
        except ProcessLookupError:
            pass
        srv.terminate()
        try:
            srv.wait(10)
        except subprocess.TimeoutExpired:
            srv.kill()
        log.close()
    rows.sort(key=lambda r: r["t"])
    first_list = next((r["t"] for r in rows if r["trending"].get("status") == "listo"), None)
    summary = {}
    for k in ("health", "search", "trending", "sparklines"):
        v = sorted(r[k]["s"] for r in rows)
        bad = sum(1 for r in rows if r[k]["code"] != 200)
        summary[k] = {"p50": statistics.median(v), "p95": v[min(len(v) - 1, round(0.95 * (len(v) - 1)))],
                      "max": v[-1], "no_200": bad}
    out = {"name": a.name, "cpu": a.cpu, "period_ms": a.period_ms, "seconds": a.seconds, "every": a.every,
           "backend": os.path.relpath(a.backend, os.path.join(BACKEND, "..")),
           "snapshot": bool(a.snapshot), "first_list_s": first_list, "summary": summary, "rows": rows}
    with open(os.path.join(OUT_DIR, f"{a.name}.json"), "w") as f:
        json.dump(out, f, indent=1)
    md = [f"# Arranque en frío: {a.name} (generado por backend/tools/arranque_frio.py)", "",
          f"CPU {a.cpu:g} (cuota cada {a.period_ms} ms), {'con la instantánea del build' if a.snapshot else 'sin instantánea de la portada'}, {a.seconds} s, una muestra cada "
          f"{a.every:g} s (health, búsqueda, tendencias 1D y mini-gráficas de 3 valores, a la vez). Backend: "
          f"`{out['backend']}`.", "",
          f"Primera lista de tendencias: **{first_list if first_list is not None else 'nunca'} s** tras abrir el puerto.",
          "", "| Petición | p50 (s) | p95 (s) | máx. (s) | sin 200 |", "|---|---|---|---|---|"]
    for k, s in summary.items():
        md.append(f"| {k} | {s['p50']} | {s['p95']} | {s['max']} | {s['no_200']} |")
    md += ["", "| t (s) | health | búsqueda | tendencias | tarjetas con motor | mini-gráficas |", "|---|---|---|---|---|---|"]
    for r in rows:
        tr = r["trending"]
        md.append(f"| {r['t']} | {r['health']['s']} | {r['search']['s']} ({r['search'].get('n', r['search']['code'])}) | "
                  f"{tr['s']} {tr.get('status', tr['code'])} | {tr.get('scored', '')} | {r['sparklines']['s']} |")
    with open(os.path.join(OUT_DIR, f"{a.name}.md"), "w") as f:
        f.write("\n".join(md) + "\n")
    print("\n".join(md[:12]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
