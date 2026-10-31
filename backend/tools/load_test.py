"""
Verificación de la v4 (V4 · carga y memoria, como Render gratuito): 20 usuarios simulados durante 5 minutos contra el
backend real en local (tools/load_server.py: main.py con la web compilada y la medida de los turnos), con las fuentes
reales y las claves del Llavero en el entorno.

    cd finanzer_next-e4/backend
    FINNHUB_API_KEY="$(security find-generic-password -s finanzer-finnhub -w)" \
    SEC_EDGAR_USER_AGENT="$(security find-generic-password -s finanzer-sec-ua -w)" \
        ../../finanzer_next/.venv313/bin/python tools/load_test.py [--users 20] [--minutes 5]

Las claves no se imprimen ni se escriben: pasan del entorno al proceso del servidor.

- Cliente HTTP: curl_cffi.requests.AsyncSession (asíncrono; httpx no está en el entorno y no se instala nada).
- Memoria: macOS no aplica `ulimit -v` (setrlimit: invalid argument; RLIMIT_AS no se puede fijar), así que se mide el
  RSS del proceso del servidor con `ps` cada `--sample-s` segundos (psutil tampoco está en el entorno).
- Mezcla por usuario, con pausas de 2–5 s:
  - visita a una empresa: la página /v2/{T}, el análisis, la gráfica y los segmentos;
  - escenario, rivales (hasta que estén), tendencias (portada), búsqueda y PDF;
  - y, de vez en cuando, una empresa nueva (análisis sin caché), para medir la cola.

Criterios:
1. Ningún 5xx.
2. Pico de memoria por debajo de 450 MB.
3. p95 de /api/analysis en caché por debajo de 2 s (empresas ya analizadas en el calentamiento).
4. Memoria estable en la segunda mitad: crecimiento por debajo de `--max-growth-mb`.
5. La cola nunca retrasa a un usuario más que otro análisis: la espera máxima de turno de un usuario no supera la
   tenencia máxima de un turno (un análisis).

Informe: JSON y Markdown en ../docs/rediseno/verificacion/ (`--name`, por defecto V4_carga: V4_carga.json y .md).
"""
import argparse
import asyncio
import datetime as dt
import json
import os
import random
import statistics
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(HERE)
REPORT_DIR = os.path.join(BACKEND, "..", "docs", "rediseno", "verificacion")
PYTHON = sys.executable

BOOT_TIMEOUT_S = 60          # arranque del servidor y primera respuesta de la portada
WARM = ["AAPL", "JPM", "O", "NEE", "XOM", "PLTR", "RIVN", "BCS"]       # los 8 de verificación
COLD = ["MSFT", "KO", "PG", "V", "JNJ", "CAT", "DUK", "PGR", "COST", "HD"]   # sin caché: una vez cada uno, al azar
SEARCHES = ["apple", "coca", "jpm", "microsoft", "nvidia"]
MEM_LIMIT_MB = 450
P95_CACHED_S = 2.0
SERVER_ERROR = 500
MB = 1024


def rss_mb(pid: int) -> Optional[float]:
    out = subprocess.run(["ps", "-o", "rss=", "-p", str(pid)], capture_output=True, text=True).stdout.strip()
    return int(out) / MB if out else None


def footprint_mb(pid: int) -> Optional[float]:
    """macOS: huella física del proceso (`footprint`), que incluye la memoria comprimida: el RSS de macOS la excluye y
    baja de golpe cuando el sistema comprime (en Linux, como en Render, el RSS no tiene ese efecto)."""
    if sys.platform != "darwin" or not os.path.exists("/usr/bin/footprint"):
        return None
    out = subprocess.run(["/usr/bin/footprint", "-p", str(pid), "-f", "bytes"], capture_output=True, text=True).stdout
    for tok in out.split("Footprint:")[1:2]:
        return int(tok.split()[0]) / MB / MB
    return None


def mem_mb(x: Dict[str, float]) -> float:
    """La medida de memoria de una muestra: la mayor entre el RSS y la huella física."""
    return max(x["rss_mb"], x.get("footprint_mb") or 0.0)


class Stats:
    def __init__(self):
        self.req: List[Dict[str, Any]] = []

    def add(self, kind: str, status: int, secs: float, cached: Optional[bool] = None, sym: str = ""):
        self.req.append({"kind": kind, "status": status, "s": round(secs, 3), "cached": cached, "sym": sym,
                         "t": round(time.monotonic(), 3)})


# La portada (P8b): sus cuatro periodos y, como mucho, los símbolos por petición de mini-gráficas ([sparklines]).
HOME_PERIODS = ["1D", "1S", "1M", "6M"]
SPARK_MAX = 40


def prewarm_cards(resp: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Las tarjetas que precalienta el motor (lib/trending.py, `_symbols`) en una respuesta de /api/v2/trending sin
    `period`: las tres listas del primer periodo (1D). Desde P8b las listas van por periodo (`lists[periodo][lista]`)."""
    lists = (resp.get("data") or {}).get("lists") or {}
    day = next(iter(lists.values()), None) or {}
    return [c for k in ("most_traded", "gainers", "losers") for c in day.get(k, [])]


async def call(sess, stats: Stats, kind: str, method: str, url: str, cached=None, sym="", **kw):
    t0 = time.monotonic()
    try:
        r = await sess.request(method, url, timeout=180, **kw)
        status, body = r.status_code, r
    except Exception as e:  # noqa: BLE001 — una caída de conexión cuenta como fallo del servidor
        status, body = 599, str(e)
    stats.add(kind, status, time.monotonic() - t0, cached, sym)
    return status, body


async def user_legacy(i: int, base: str, stats: Stats, deadline: float, cold: List[str], cold_lock: asyncio.Lock,
                      sector: Dict[str, str], inputs: Dict[str, Any]):
    """La misma mezcla con lo que existe en la web actual (main): visita (/stock/T y el análisis), portada /,
    búsqueda, PDF y empresas nuevas. Escenario, rivales y tendencias no existen allí: esa fracción del tiempo, pausa."""
    from curl_cffi.requests import AsyncSession
    rnd = random.Random(i)
    async with AsyncSession() as s:
        while time.monotonic() < deadline:
            r = rnd.random()
            sym = rnd.choice(WARM)
            if r < 0.40:
                await call(s, stats, "page", "GET", f"{base}/stock/{sym}", sym=sym)
                await call(s, stats, "analysis", "GET", f"{base}/api/analysis/{sym}", cached=True, sym=sym)
            elif r < 0.67:
                pass                # escenario y rivales: no existen en la web actual
            elif r < 0.82:
                await call(s, stats, "page", "GET", f"{base}/")
            elif r < 0.90:
                await call(s, stats, "search", "GET", f"{base}/api/search", params={"q": rnd.choice(SEARCHES)})
            elif r < 0.95:
                await call(s, stats, "pdf", "GET", f"{base}/api/pdf/{sym}", sym=sym)
            else:
                async with cold_lock:
                    new = cold.pop() if cold else None
                if new:
                    await call(s, stats, "analysis_cold", "GET", f"{base}/api/analysis/{new}", cached=False, sym=new)
            await asyncio.sleep(rnd.uniform(2, 5))


async def user(i: int, base: str, stats: Stats, deadline: float, cold: List[str], cold_lock: asyncio.Lock,
               sector: Dict[str, str], inputs: Dict[str, Any]):
    from curl_cffi.requests import AsyncSession
    rnd = random.Random(i)
    async with AsyncSession() as s:
        while time.monotonic() < deadline:
            r = rnd.random()
            sym = rnd.choice(WARM)
            if r < 0.40:        # visita a una empresa
                await call(s, stats, "page", "GET", f"{base}/v2/{sym}", sym=sym)
                await call(s, stats, "analysis", "GET", f"{base}/api/analysis/{sym}", cached=True, sym=sym)
                await call(s, stats, "prices", "GET", f"{base}/api/v2/prices/{sym}",
                           params={"sector": sector.get(sym, "")}, sym=sym)
                await call(s, stats, "segments", "GET", f"{base}/api/v2/segments/{sym}", sym=sym)
            elif r < 0.52 and inputs.get(sym):
                await call(s, stats, "scenario", "POST", f"{base}/api/v2/scenario", sym=sym,
                           json={"inputs": inputs[sym], "assumptions": {"discount_rate": rnd.choice([0.08, 0.1, 0.12])}})
            elif r < 0.67:      # rivales: se repite cada poll_s hasta que estén (como la página), como mucho 60 s
                t_end = time.monotonic() + 60
                while time.monotonic() < min(t_end, deadline):
                    st, b = await call(s, stats, "peers", "GET", f"{base}/api/v2/peers/{sym}", sym=sym)
                    if st != 200 or b.json().get("status") != "calculando":
                        break
                    await asyncio.sleep(4)
            elif r < 0.82:      # portada (P8b y V6b): las tendencias del periodo que enseña y las mini-gráficas de su lista
                per = rnd.choice(HOME_PERIODS)
                await call(s, stats, "page", "GET", f"{base}/v2")
                st, b = await call(s, stats, "trending", "GET", f"{base}/api/v2/trending", params={"period": per})
                lists = ((b.json().get("data") or {}).get("lists") or {}) if st == 200 else {}
                syms = [x["symbol"] for x in (lists.get(per) or {}).get("most_traded", [])][:SPARK_MAX]
                if syms:
                    await call(s, stats, "sparklines", "GET", f"{base}/api/v2/sparklines",
                               params={"symbols": ",".join(syms), "period": per})
            elif r < 0.90:
                await call(s, stats, "search", "GET", f"{base}/api/v2/search", params={"q": rnd.choice(SEARCHES)})
            elif r < 0.95:
                await call(s, stats, "pdf", "GET", f"{base}/api/pdf/{sym}", sym=sym)
            else:               # una empresa nueva: análisis sin caché de un usuario
                async with cold_lock:
                    new = cold.pop() if cold else None
                if new:
                    await call(s, stats, "analysis_cold", "GET", f"{base}/api/analysis/{new}", cached=False, sym=new)
            await asyncio.sleep(rnd.uniform(2, 5))


async def sampler(pid: int, mem: List[Dict[str, float]], stop: asyncio.Event, every: float):
    t0 = time.monotonic()
    while not stop.is_set():
        m = rss_mb(pid)
        if m is not None:
            f = footprint_mb(pid)
            mem.append({"t": round(time.monotonic() - t0, 1), "rss_mb": round(m, 1),
                        "footprint_mb": None if f is None else round(f, 1)})
        try:
            await asyncio.wait_for(stop.wait(), timeout=every)
        except asyncio.TimeoutError:
            pass


def pct(xs: List[float], q: float) -> Optional[float]:
    if not xs:
        return None
    xs = sorted(xs)
    return round(xs[min(len(xs) - 1, int(round(q * (len(xs) - 1))))], 3)


async def run(args) -> Dict[str, Any]:
    from curl_cffi.requests import AsyncSession
    base = f"http://127.0.0.1:{args.port}"
    env = dict(os.environ)
    env["FINANZER_PORTADA_SNAPSHOT"] = "0"     # portada rápida: cada carga arranca sin la lista guardada (comparables)
    keys = {k: bool((env.get(k) or "").strip()) for k in ("FINNHUB_API_KEY", "SEC_EDGAR_USER_AGENT")}
    t_start = time.monotonic()
    legacy = args.mix == "legacy"
    cmd = [PYTHON, os.path.join(HERE, "load_server.py"), "--port", str(args.port), "--backend", args.backend]
    if args.no_prewarm:
        cmd.append("--no-prewarm")
    for kv in args.set:
        cmd += ["--set", kv]
    proc = subprocess.Popen(cmd, cwd=BACKEND, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    mem: List[Dict[str, float]] = []
    stop = asyncio.Event()
    stats = Stats()
    out: Dict[str, Any] = {"keys_present": keys, "users": args.users, "minutes": args.minutes, "mix": args.mix,
                           "backend": os.path.relpath(os.path.abspath(args.backend), os.path.join(BACKEND, "..", ".."))}
    try:
        async with AsyncSession() as s:
            # Arranque en frío: primera respuesta de la portada y de /v2/AAPL (HTML) y el primer análisis de AAPL.
            home = "/" if legacy else "/v2"
            last = None
            while True:
                try:
                    r = await s.get(f"{base}{home}", timeout=5)
                    last = r.status_code
                    if r.status_code == 200:
                        break
                except Exception:  # noqa: BLE001 — aún arrancando
                    pass
                if time.monotonic() - t_start > BOOT_TIMEOUT_S:
                    # sin la web compilada (frontend/out sin /v2) la portada nunca responde 200: se dice, no se espera
                    raise SystemExit(f"{home} no responde 200 tras {BOOT_TIMEOUT_S} s (último: {last}); "
                                     "¿falta `npm run build` en frontend/?")
                await asyncio.sleep(0.2)
            boot = {"process_to_first_home_s": round(time.monotonic() - t_start, 2)}
            t = time.monotonic()
            r = await s.get(f"{base}{'/stock/AAPL' if legacy else '/v2/AAPL'}", timeout=30)
            boot["first_story_html_s"] = round(time.monotonic() - t, 3)
            samp = asyncio.create_task(sampler(proc.pid, mem, stop, args.sample_s))
            # Calentamiento: el primer análisis de cada empresa (sin caché), uno detrás de otro.
            sector, inputs, warm = {}, {}, {}
            for sym in WARM:
                t = time.monotonic()
                r = await s.get(f"{base}/api/analysis/{sym}", timeout=180)
                warm[sym] = {"status": r.status_code, "s": round(time.monotonic() - t, 2)}
                if r.status_code == 200:
                    a = r.json()
                    sector[sym] = (a.get("profile") or {}).get("sector") or ""
                    inputs[sym] = a.get("scenario_inputs")
            boot["first_analysis_AAPL_s"] = warm["AAPL"]["s"]
            # El precalentado de las tendencias (una vez al día, tras el cierre: ~30 análisis en la cola de fondo) forma
            # parte del calentamiento: la segunda mitad de la carga mide el estado estable, no ese llenado diario.
            t = time.monotonic()
            prewarm = {"status": None, "s": None, "cards": 0}
            while not legacy and time.monotonic() - t < args.prewarm_timeout_s:
                tr = (await s.get(f"{base}/api/v2/trending", timeout=30)).json()
                cards = prewarm_cards(tr)
                busy = [c for c in cards if (c.get("engine") or {}).get("status") in ("en_cola", "analizando")]
                if tr["status"] == "sin_dato" or (tr["status"] == "listo" and not busy and not tr.get("refreshing")):
                    prewarm = {"status": tr["status"], "s": round(time.monotonic() - t, 1), "cards": len(cards),
                               "listo": sum((c.get("engine") or {}).get("status") == "listo" for c in cards)}
                    break
                await asyncio.sleep(3)
            out["prewarm"] = prewarm
            out["cold_start"], out["warmup"] = boot, warm
            warm_end = time.monotonic()
            mem_warm_end = len(mem)
            # Carga
            deadline = time.monotonic() + args.minutes * 60
            cold, cold_lock = list(COLD), asyncio.Lock()
            who = user_legacy if legacy else user
            await asyncio.gather(*(who(i, base, stats, deadline, cold, cold_lock, sector, inputs)
                                   for i in range(args.users)))
            load_end = time.monotonic()
            slots = (await s.get(f"{base}/__load/slots", timeout=30)).json()["records"]
            try:        # tamaño de las cachés al final (solo el load_server de esta rama lo sirve)
                r = await s.get(f"{base}/__load/caches", timeout=120)
                caches = r.json().get("caches", []) if r.status_code == 200 else []
            except Exception:  # noqa: BLE001
                caches = []
        stop.set()
        await samp
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=20)
        except subprocess.TimeoutExpired:
            proc.kill()

    # ── resultados ──
    reqs = stats.req
    by_kind: Dict[str, Any] = {}
    for k in sorted({r["kind"] for r in reqs}):
        xs = [r for r in reqs if r["kind"] == k]
        secs = [r["s"] for r in xs]
        by_kind[k] = {"n": len(xs), "5xx": sum(r["status"] >= SERVER_ERROR for r in xs),
                      "4xx": sum(400 <= r["status"] < SERVER_ERROR for r in xs),
                      "p50_s": pct(secs, 0.5), "p95_s": pct(secs, 0.95), "max_s": max(secs) if secs else None}
    errors = [r for r in reqs if r["status"] >= SERVER_ERROR]
    cached = [r["s"] for r in reqs if r["kind"] == "analysis" and r["status"] == 200]
    load_mem = mem[mem_warm_end:]
    half = load_mem[len(load_mem) // 2:]
    growth = (statistics.mean(mem_mb(x) for x in half[-max(1, len(half) // 4):])
              - statistics.mean(mem_mb(x) for x in half[:max(1, len(half) // 4)])) if len(half) >= 4 else None
    peak = max((mem_mb(x) for x in mem), default=None)
    warm_mem = mem[:mem_warm_end]
    user_waits = [r["wait_s"] for r in slots if r["user"]]
    holds = [r["hold_s"] for r in slots]
    bg = [r for r in slots if not r["user"]]
    criteria = {
        "sin_5xx": {"ok": not errors, "valor": len(errors)},
        "memoria_pico_mb": {"ok": peak is not None and peak < MEM_LIMIT_MB, "valor": peak, "limite": MEM_LIMIT_MB},
        "p95_analisis_en_cache_s": {"ok": pct(cached, 0.95) is not None and pct(cached, 0.95) < P95_CACHED_S,
                                    "valor": pct(cached, 0.95), "limite": P95_CACHED_S, "n": len(cached)},
        "memoria_estable_2a_mitad_mb": {"ok": growth is not None and growth < args.max_growth_mb,
                                        "valor": None if growth is None else round(growth, 1),
                                        "limite": args.max_growth_mb},
        "cola_no_retrasa_mas_que_un_analisis": {
            "ok": legacy or (max(user_waits, default=0.0) <= max(holds, default=0.0) + 0.5),
            "espera_max_usuario_s": max(user_waits, default=0.0), "tenencia_max_s": max(holds, default=0.0),
            "turnos_usuario": len(user_waits), "turnos_fondo": len(bg),
            "espera_p95_usuario_s": pct(user_waits, 0.95)},
    }
    out.update({
        "fecha": dt.datetime.now().isoformat(timespec="seconds"),
        "duracion_carga_s": round(load_end - warm_end, 1),
        "peticiones": len(reqs), "por_tipo": by_kind,
        "errores_5xx": errors[:20],
        "memoria": {"medida": "máx(RSS, huella física de macOS)", "pico_mb": peak,
                    "pico_rss_mb": max((x["rss_mb"] for x in mem), default=None),
                    "pico_footprint_mb": max((x.get("footprint_mb") or 0.0 for x in mem), default=None),
                    "pico_calentamiento_mb": max((mem_mb(x) for x in warm_mem), default=None),
                    "al_empezar_la_carga_mb": mem_mb(warm_mem[-1]) if warm_mem else None,
                    "pico_carga_mb": max((mem_mb(x) for x in load_mem), default=None),
                    "muestras": len(mem), "crecimiento_2a_mitad_mb": criteria[
            "memoria_estable_2a_mitad_mb"]["valor"], "serie": mem},
        "turnos": {"usuario": len(user_waits), "fondo": len(bg), "registros": slots},
        "caches_al_final": caches,
        "criterios": criteria, "todo_ok": all(c["ok"] for c in criteria.values()),
    })
    return out


def write_report(res: Dict[str, Any], name: str = "V4_carga") -> str:
    os.makedirs(REPORT_DIR, exist_ok=True)
    with open(os.path.join(REPORT_DIR, f"{name}.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    c = res["criterios"]
    lines = [
        "# V4 · Carga y memoria (generado por backend/tools/load_test.py)", "",
        f"Fecha: {res['fecha']}. Backend: {res['backend']} (mezcla {res['mix']}). {res['users']} usuarios durante "
        f"{res['minutes']} min (carga medida: "
        f"{res['duracion_carga_s']} s), backend real en local con la web compilada y las fuentes reales. Claves presentes: "
        + ", ".join(f"{k} {'sí' if v else 'no'}" for k, v in res["keys_present"].items()) + ".", "",
        "## Criterios", "", "| Criterio | Resultado | Valor | Límite |", "|---|---|---|---|",
        f"| Ningún 5xx | {'✅' if c['sin_5xx']['ok'] else '❌'} | {c['sin_5xx']['valor']} | 0 |",
        f"| Pico de memoria (máx. de RSS y huella física) | {'✅' if c['memoria_pico_mb']['ok'] else '❌'} | {c['memoria_pico_mb']['valor']:.0f} MB | "
        f"< {MEM_LIMIT_MB} MB |",
        f"| p95 de /api/analysis en caché | {'✅' if c['p95_analisis_en_cache_s']['ok'] else '❌'} | "
        f"{c['p95_analisis_en_cache_s']['valor']} s (n = {c['p95_analisis_en_cache_s']['n']}) | < {P95_CACHED_S} s |",
        f"| Memoria estable (2.ª mitad) | {'✅' if c['memoria_estable_2a_mitad_mb']['ok'] else '❌'} | "
        f"{c['memoria_estable_2a_mitad_mb']['valor']} MB | < {c['memoria_estable_2a_mitad_mb']['limite']} MB |",
        f"| La cola no retrasa a un usuario más que un análisis | "
        f"{'✅' if c['cola_no_retrasa_mas_que_un_analisis']['ok'] else '❌'} | espera máx. de usuario "
        f"{c['cola_no_retrasa_mas_que_un_analisis']['espera_max_usuario_s']} s; tenencia máx. "
        f"{c['cola_no_retrasa_mas_que_un_analisis']['tenencia_max_s']} s | espera ≤ tenencia |", "",
        "## Por tipo de petición", "", "| Tipo | n | 5xx | 4xx | p50 (s) | p95 (s) | máx. (s) |", "|---|---|---|---|---|---|---|"]
    for k, v in res["por_tipo"].items():
        lines.append(f"| {k} | {v['n']} | {v['5xx']} | {v['4xx']} | {v['p50_s']} | {v['p95_s']} | {v['max_s']} |")
    cs, w = res["cold_start"], res["warmup"]
    lines += ["", "## Arranque en frío y calentamiento", "",
              f"- Proceso nuevo → primera respuesta de la portada: {cs['process_to_first_home_s']} s; HTML de /v2/AAPL: "
              f"{cs['first_story_html_s']} s; primer análisis de AAPL: {cs['first_analysis_AAPL_s']} s.",
              "- Primer análisis de cada empresa: " + ", ".join(f"{k} {v['s']} s ({v['status']})" for k, v in w.items()) + ".",
              f"- Precalentado de las tendencias (parte del calentamiento): {res['prewarm']}.",
              f"- Memoria: pico del calentamiento {res['memoria']['pico_calentamiento_mb']} MB; al empezar la carga "
              f"{res['memoria']['al_empezar_la_carga_mb']} MB; pico de la carga {res['memoria']['pico_carga_mb']} MB "
              f"(picos por separado: RSS {res['memoria']['pico_rss_mb']} MB, huella física "
              f"{res['memoria']['pico_footprint_mb']} MB).",
              "", f"Turnos de análisis: {res['turnos']['usuario']} de usuarios y {res['turnos']['fondo']} de la cola de fondo "
              f"(rivales y precalentado). Espera p95 de un usuario: "
              f"{c['cola_no_retrasa_mas_que_un_analisis']['espera_p95_usuario_s']} s.", "",
              f"**Resultado: {'todo en verde' if res['todo_ok'] else 'hay criterios en rojo'}.**", ""]
    if res.get("caches_al_final"):
        lines += ["## Cachés al final de la carga (huella en memoria, aproximada)", "", "| Caché | Entradas | MB |",
                  "|---|---|---|"] + [f"| {c['cache']} | {c['entries']} | {c['mb']} |"
                                      for c in res["caches_al_final"][:12]] + [""]
    md = "\n".join(lines)
    with open(os.path.join(REPORT_DIR, f"{name}.md"), "w", encoding="utf-8") as fh:
        fh.write(md)
    return md


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--users", type=int, default=20)
    ap.add_argument("--minutes", type=float, default=5)
    ap.add_argument("--port", type=int, default=8771)
    ap.add_argument("--sample-s", type=float, default=2.0)
    ap.add_argument("--max-growth-mb", type=float, default=25.0)
    ap.add_argument("--prewarm-timeout-s", type=float, default=420.0)
    ap.add_argument("--backend", default=BACKEND, help="carpeta backend/ que se sirve (la referencia: la de main)")
    ap.add_argument("--mix", choices=["v4", "legacy"], default="v4", help="legacy: lo que existe en la web actual")
    ap.add_argument("--no-prewarm", action="store_true")
    ap.add_argument("--set", action="append", default=[], metavar="RUTA=VALOR",
                    help="cambia un valor de la config en el servidor (opciones de memoria; p. ej. "
                         "data.server.max_concurrent_analyses=3)")
    ap.add_argument("--name", default="V4_carga", help="nombre del informe (V4_carga_5min, V4_carga_12min…)")
    args = ap.parse_args()
    res = asyncio.run(run(args))
    print(write_report(res, args.name))
    sys.exit(0 if res["todo_ok"] else 1)


if __name__ == "__main__":
    main()
