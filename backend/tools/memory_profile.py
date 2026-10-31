"""
Verificación de la v4 (V4 · memoria): qué aporta cada pieza al pico. Para cada escenario arranca un servidor nuevo
(tools/load_server.py, fuentes reales), mide su huella en reposo, ejecuta solo esa pieza y anota el pico de memoria
sobre esa base (máx. de RSS y huella física de macOS, muestreado cada `--sample-s`).

    cd finanzer_next-e4/backend
    FINNHUB_API_KEY="$(security find-generic-password -s finanzer-finnhub -w)" \
    SEC_EDGAR_USER_AGENT="$(security find-generic-password -s finanzer-sec-ua -w)" \
        ../../finanzer_next/.venv313/bin/python tools/memory_profile.py [--only analisis_x4,pdf_v2]

Informe: ../docs/rediseno/verificacion/V4_memoria_perfil.{json,md} (`--name` para otro nombre).
"""
import argparse
import asyncio
import datetime as dt
import json
import os
import subprocess
import sys
import time
from typing import Any, Awaitable, Callable, Dict, List

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import load_test as LT  # noqa: E402

FOUR = ["AAPL", "JPM", "XOM", "BCS"]
EIGHT = LT.WARM


async def _until(s, url: str, done: Callable[[Dict[str, Any]], bool], timeout: float = 600, every: float = 2.0):
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout:
        r = await s.get(url, timeout=60)
        if r.status_code != 200 or done(r.json()):
            return r
        await asyncio.sleep(every)
    return None


async def sc_analisis_x1(s, base):
    await s.get(f"{base}/api/analysis/AAPL", timeout=180)


async def sc_analisis_x4(s, base):
    await asyncio.gather(*(s.get(f"{base}/api/analysis/{t}", timeout=180) for t in FOUR))


async def sc_serie_5a(s, base):
    for t in EIGHT:
        await s.get(f"{base}/api/v2/prices/{t}", params={"sector": "Technology"}, timeout=180)


async def sc_segmentos(s, base):
    for t in EIGHT:
        await s.get(f"{base}/api/v2/segments/{t}", timeout=180)


async def sc_tendencias(s, base):
    await _until(s, f"{base}/api/v2/trending", lambda r: r["status"] != "calculando")


def _settled(r: Dict[str, Any]) -> bool:
    if r["status"] == "calculando":
        return False
    cards = LT.prewarm_cards(r)
    return not any((c.get("engine") or {}).get("status") in ("en_cola", "analizando") for c in cards)


async def sc_tendencias_prewarm(s, base):
    await _until(s, f"{base}/api/v2/trending", _settled, timeout=900, every=3)


async def sc_rivales(s, base):
    await s.get(f"{base}/api/analysis/AAPL", timeout=180)
    await _until(s, f"{base}/api/v2/peers/AAPL", lambda r: r["status"] != "calculando", timeout=600, every=3)


async def sc_pdf(s, base):
    for t in FOUR[:2]:
        await s.get(f"{base}/api/pdf/{t}", timeout=300)


async def sc_pdf_v2(s, base):
    for t in FOUR[:2]:
        await s.get(f"{base}/api/v2/pdf/{t}", timeout=300)


async def sc_pdf_v2_x4(s, base):
    await asyncio.gather(*(s.get(f"{base}/api/v2/pdf/{t}", timeout=300) for t in FOUR))


async def sc_mezcla_x4(s, base):
    """4 análisis en frío y los segmentos de otras 4 empresas, todo a la vez (V6, B2: ¿coinciden sus lecturas?)."""
    await asyncio.gather(*(s.get(f"{base}/api/analysis/{t}", timeout=180) for t in FOUR),
                         *(s.get(f"{base}/api/v2/segments/{t}", timeout=180) for t in ("O", "NEE", "PLTR", "RIVN")))


async def sc_portada(s, base):
    """La portada como en la carga (P8b, V6b): las tendencias de cada periodo y las mini-gráficas de su lista."""
    await _until(s, f"{base}/api/v2/trending", lambda r: r["status"] != "calculando")
    for per in LT.HOME_PERIODS:
        r = (await s.get(f"{base}/api/v2/trending", params={"period": per}, timeout=60)).json()
        syms = [x["symbol"] for x in (((r.get("data") or {}).get("lists") or {}).get(per) or {}).get("most_traded", [])]
        if syms:
            await s.get(f"{base}/api/v2/sparklines", params={"symbols": ",".join(syms[:LT.SPARK_MAX]), "period": per},
                        timeout=180)


SCENARIOS: Dict[str, Any] = {
    "analisis_x1": ("Un análisis en frío (AAPL)", sc_analisis_x1, True),
    "analisis_x4": ("4 análisis en frío a la vez (AAPL, JPM, XOM, BCS)", sc_analisis_x4, True),
    "serie_5a": ("Gráfica: serie de 5 años, mercado, sector y eventos (8 empresas, sin análisis)", sc_serie_5a, True),
    "segmentos": ("Segmentos XBRL (8 empresas)", sc_segmentos, True),
    "tendencias": ("Tendencias: descarga del universo, sin precalentado", sc_tendencias, True),
    "tendencias_prewarm": ("Tendencias con su precalentado (30 análisis en la cola de fondo)", sc_tendencias_prewarm,
                           False),
    "rivales": ("Rivales de AAPL: su análisis y 5 rivales en la cola", sc_rivales, True),
    "pdf": ("PDF actual (/api/pdf) de 2 empresas, una tras otra", sc_pdf, True),
    "pdf_v2": ("PDF nuevo (/api/v2/pdf) de 2 empresas, una tras otra", sc_pdf_v2, True),
    "pdf_v2_x4": ("PDF nuevo de 4 empresas a la vez", sc_pdf_v2_x4, True),
    "mezcla_x4": ("4 análisis en frío y 4 segmentos a la vez", sc_mezcla_x4, True),
    "portada": ("Portada: tendencias de los 4 periodos y sus mini-gráficas, sin precalentado", sc_portada, True),
}


async def run_one(key: str, args) -> Dict[str, Any]:
    from curl_cffi.requests import AsyncSession
    title, fn, no_prewarm = SCENARIOS[key]
    cmd = [LT.PYTHON, os.path.join(HERE, "load_server.py"), "--port", str(args.port), "--backend", args.backend]
    if no_prewarm:
        cmd.append("--no-prewarm")
    cmd += args.server_arg
    proc = subprocess.Popen(cmd, cwd=LT.BACKEND, env=dict(os.environ), stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)
    base = f"http://127.0.0.1:{args.port}"
    mem: List[Dict[str, float]] = []
    stop = asyncio.Event()
    try:
        async with AsyncSession() as s:
            while True:
                try:
                    if (await s.get(f"{base}/api/health", timeout=5)).status_code == 200:
                        break
                except Exception:  # noqa: BLE001 — arrancando
                    pass
                await asyncio.sleep(0.2)
            samp = asyncio.create_task(LT.sampler(proc.pid, mem, stop, args.sample_s))
            await asyncio.sleep(3)
            n_base = len(mem)
            t0 = time.monotonic()
            await fn(s, base)
            secs = time.monotonic() - t0
            await asyncio.sleep(3)
            stop.set()
            await samp
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=20)
        except subprocess.TimeoutExpired:
            proc.kill()
    base_mb = max((LT.mem_mb(x) for x in mem[:max(n_base, 1)]), default=None)
    peak = max((LT.mem_mb(x) for x in mem), default=None)
    return {"escenario": key, "descripcion": title, "s": round(secs, 1), "base_mb": base_mb, "pico_mb": peak,
            "aporta_mb": None if base_mb is None or peak is None else round(peak - base_mb, 1),
            "fin_mb": LT.mem_mb(mem[-1]) if mem else None}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8772)
    ap.add_argument("--backend", default=LT.BACKEND)
    ap.add_argument("--sample-s", type=float, default=0.5)
    ap.add_argument("--only", default="", help="escenarios separados por comas (por defecto, todos)")
    ap.add_argument("--name", default="V4_memoria_perfil")
    ap.add_argument("--server-arg", action="append", default=[], help="argumento más para load_server.py")
    args = ap.parse_args()
    keys = [k for k in (args.only.split(",") if args.only else SCENARIOS) if k]
    rows = []
    for k in keys:
        r = asyncio.run(run_one(k, args))
        print(f"{k}: base {r['base_mb']} MB, pico {r['pico_mb']} MB, aporta {r['aporta_mb']} MB ({r['s']} s)",
              flush=True)
        rows.append(r)
    os.makedirs(LT.REPORT_DIR, exist_ok=True)
    res = {"fecha": dt.datetime.now().isoformat(timespec="seconds"), "medida": "máx(RSS, huella física de macOS)",
           "escenarios": rows}
    with open(os.path.join(LT.REPORT_DIR, f"{args.name}.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    lines = [f"# Perfil de memoria por pieza (backend/tools/memory_profile.py, {res['fecha']})", "",
             "Cada fila: servidor nuevo, huella en reposo (base), solo esa pieza, pico. Medida: máx(RSS, huella física).",
             "", "| Pieza | Base (MB) | Pico (MB) | Aporta (MB) | Duración (s) |", "|---|---|---|---|---|"]
    lines += [f"| {r['descripcion']} | {r['base_mb']} | {r['pico_mb']} | **{r['aporta_mb']}** | {r['s']} |" for r in rows]
    with open(os.path.join(LT.REPORT_DIR, f"{args.name}.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
