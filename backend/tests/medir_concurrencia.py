"""
Fase 6 (solo medir): ¿atiende producción en serie? Latencia en frío y en caliente, en serie y a concurrencia 3.

    cd finanzer_next/backend
    ../.venv313/bin/python tests/medir_concurrencia.py --out <DIR>

Dos rondas con tickers distintos (fuera del panel, para que las dos partan de caché fría del proceso):
  · ronda "serie": 6 tickers, uno tras otro (concurrencia 1);
  · ronda "c3": otros 6 de tamaño parecido, 3 a la vez.
Cada ticker pide /api/analysis (frío), /api/analysis otra vez (caliente) y /api/pdf (caliente). Si el servidor atiende
en serie, la ronda c3 dura lo mismo que la de serie (no gana rendimiento) y cada petición tarda ≈ 3 × su servicio.

Con --sonda-health, mientras corre la ronda en serie un segundo hilo pide /api/health cada segundo (2 peticiones en
vuelo como mucho): si el bucle de eventos queda bloqueado por el análisis, /api/health tarda lo que le quede al
análisis en curso en lugar de ~0.3 s.

Reglas: despierta primero (una petición a /api/health, descartada); contra finanzer.app nunca más de 3 a la vez y
nunca de 15:55 a 16:45 de Nueva York. La prueba de 12 simultáneas del plan queda diseñada para un entorno de pruebas
(`--concurrency 12 --base-url http://<staging>`): contra finanzer.app se niega. Salida: medida.json y medida.md.
"""
import argparse
import concurrent.futures as cf
import datetime as _dt
import json
import os
import statistics
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vigilancia as vg  # noqa: E402

SERIE = ["HD", "PEP", "COST", "MCD", "UNH", "ORCL"]
C3 = ["LOW", "MDLZ", "WMT", "YUM", "CVS", "IBM"]


def _req(url, timeout=240):
    t0 = time.monotonic()
    t_start = time.time()
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "finanzer-f6-medida"}),
                                    timeout=timeout) as r:
            body, status = r.read(), r.status
    except urllib.error.HTTPError as e:
        body, status = e.read(), e.code
    except Exception as e:  # timeout / conexión
        body, status = str(e).encode(), 0
    return {"status": status, "s": round(time.monotonic() - t0, 3), "inicio": t_start, "fin": time.time(),
            "bytes": len(body)}


def ticker_sequence(base, sym):
    out = {"ticker": sym}
    out["analisis_frio"] = _req(f"{base}/api/analysis/{sym}")
    out["analisis_caliente"] = _req(f"{base}/api/analysis/{sym}")
    out["pdf_caliente"] = _req(f"{base}/api/pdf/{sym}")
    return out


def run_round(base, tickers, concurrency, probe=False):
    t0 = time.monotonic()
    pings, stop = [], [False]

    def ping():
        while not stop[0]:
            pings.append(_req(f"{base}/api/health", 120))
            time.sleep(1.0)
    with cf.ThreadPoolExecutor(max_workers=concurrency + (1 if probe else 0)) as ex:
        pf = ex.submit(ping) if probe else None
        res = list(ex.map(lambda s: ticker_sequence(base, s), tickers))
        stop[0] = True
        if pf:
            pf.result()
    out = {"concurrencia": concurrency, "tickers": res, "pared_s": round(time.monotonic() - t0, 2)}
    if probe:
        out["sonda_health"] = pings
    return out


def overlap(res):
    """Fracción del tiempo de la ronda con más de una petición en vuelo (0 en serie)."""
    ev = sorted([(r[k]["inicio"], 1) for r in res for k in ("analisis_frio", "analisis_caliente", "pdf_caliente")]
                + [(r[k]["fin"], -1) for r in res for k in ("analisis_frio", "analisis_caliente", "pdf_caliente")])
    busy = multi = 0.0
    n, last = 0, ev[0][0]
    for t, d in ev:
        if n >= 1:
            busy += t - last
        if n >= 2:
            multi += t - last
        n += d
        last = t
    return round(multi / busy, 3) if busy else 0.0


def summary(rnd):
    def col(k):
        return [r[k]["s"] for r in rnd["tickers"] if r[k]["status"] == 200]
    s = {k: {"mediana": round(statistics.median(col(k)), 2) if col(k) else None,
             "max": max(col(k)) if col(k) else None, "suma": round(sum(col(k)), 2)}
         for k in ("analisis_frio", "analisis_caliente", "pdf_caliente")}
    s["pared_s"] = rnd["pared_s"]
    s["solape"] = overlap(rnd["tickers"])
    s["no_200"] = [(r["ticker"], k, r[k]["status"]) for r in rnd["tickers"]
                   for k in ("analisis_frio", "analisis_caliente", "pdf_caliente") if r[k]["status"] != 200]
    return s


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True)
    ap.add_argument("--base-url", default=vg.BASE_URL)
    ap.add_argument("--concurrency", type=int, default=3, help="concurrencia de la segunda ronda")
    ap.add_argument("--serie", nargs="*", default=SERIE, help="tickers de la ronda en serie")
    ap.add_argument("--c3", nargs="*", default=C3, help="tickers de la ronda concurrente")
    ap.add_argument("--sonda-health", action="store_true", help="sondea /api/health durante la ronda en serie")
    args = ap.parse_args(argv)
    base = args.base_url.rstrip("/")
    if "finanzer.app" in base and args.concurrency > vg.MAX_CONCURRENCY:
        ap.error("contra finanzer.app la concurrencia máxima es 3; 12 simultáneas solo en un entorno de pruebas")
    if vg.in_forbidden_window(vg.ny_now()):
        ap.error("ventana prohibida 15:55–16:45 de Nueva York")
    out = os.path.abspath(os.path.expanduser(args.out))
    os.makedirs(out, exist_ok=True)
    wake = _req(f"{base}/api/health", 180)
    health = _req(f"{base}/api/health", 60)
    res = {"fecha": _dt.datetime.now().astimezone().isoformat(timespec="seconds"), "base_url": base,
           "despertar": wake, "health": health}
    res["serie"] = run_round(base, args.serie, 1, probe=args.sonda_health)
    res["c3"] = run_round(base, args.c3, args.concurrency)
    res["resumen"] = {"serie": summary(res["serie"]), "c3": summary(res["c3"])}
    with open(os.path.join(out, "medida.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1)
    md = [f"# Medida de concurrencia · {res['fecha']}", "",
          f"- Despertar: {wake['s']} s (HTTP {wake['status']}); segunda /api/health {health['s']} s", ""]
    for name in ("serie", "c3"):
        rnd = res[name]
        md += [f"## Ronda {name} (concurrencia {rnd['concurrencia']}) · pared {rnd['pared_s']} s · "
               f"solape {res['resumen'][name]['solape']:.0%}", "",
               "| ticker | análisis frío s | análisis caliente s | PDF caliente s |", "|---|---|---|---|"]
        md += [f"| {r['ticker']} | {r['analisis_frio']['s']} ({r['analisis_frio']['status']}) | "
               f"{r['analisis_caliente']['s']} | {r['pdf_caliente']['s']} ({r['pdf_caliente']['status']}) |"
               for r in rnd["tickers"]]
        s = res["resumen"][name]
        md += ["", f"Medianas: frío {s['analisis_frio']['mediana']} s · caliente {s['analisis_caliente']['mediana']} s"
               f" · PDF {s['pdf_caliente']['mediana']} s. Suma de latencias {sum(s[k]['suma'] for k in ('analisis_frio', 'analisis_caliente', 'pdf_caliente')):.1f} s.", ""]
    pings = res["serie"].get("sonda_health")
    if pings:
        ok = sorted(p["s"] for p in pings if p["status"] == 200)
        md += ["## Sonda de /api/health durante la ronda en serie", "",
               f"{len(pings)} peticiones; mediana {statistics.median(ok):.2f} s, máximo {max(ok):.2f} s; "
               f"{sum(1 for x in ok if x > 1.0)} por encima de 1 s (sin análisis en curso: ~0.3 s).", ""]
    with open(os.path.join(out, "medida.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(md) + "\n")
    print("\n".join(md))
    return 0


if __name__ == "__main__":
    sys.exit(main())
