"""
Verificación de la v4 (V2 · fuentes reales): recorre la API de /v2 de cada ticker contra un backend real que ya está
en marcha (tools/load_server.py, con la web compilada y las claves en su entorno) y anota estado, tiempo y motivo de
cada `sin_dato`. Las páginas (consola y 5xx) las recorre aparte frontend/e2e/fuentes-reales/paginas.spec.ts.

    cd finanzer_next-e4/backend
    FINNHUB_API_KEY="$(security find-generic-password -s finanzer-finnhub -w)" \\
    SEC_EDGAR_USER_AGENT="$(security find-generic-password -s finanzer-sec-ua -w)" \\
        ../../finanzer_next/.venv313/bin/python tools/load_server.py --port 8771 --no-prewarm &
    ../../finanzer_next/.venv313/bin/python tools/real_sources.py --base http://127.0.0.1:8771 [--seed 20261018]

Aquí no se leen claves: solo se habla con el servidor local. Informe: ../docs/rediseno/verificacion/V2_api.json.
"""
import argparse
import asyncio
import csv
import json
import math
import os
import random
import time
from typing import Any, Dict, List, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(HERE)
REPORT_DIR = os.path.normpath(os.path.join(BACKEND, "..", "docs", "rediseno", "verificacion"))

VERIFICATION = ["AAPL", "JPM", "O", "NEE", "XOM", "PLTR", "RIVN", "BCS"]
RARE = {"BRK-B": "dos clases (B)", "GOOG": "dos clases (C)", "GOOGL": "dos clases (A)", "TSM": "ADR con factor",
        "CB": "aseguradora", "PLD": "REIT", "LCID": "pre-beneficio", "CRCL": "salida a bolsa reciente (2025-06)",
        "MC.PA": "París", "SPY": "ETF: no se analiza", "ZZZZZ": "inexistente", "BF.B": "con punto",
        "SIVB": "deslistado (2023)"}
PEERS_TIMEOUT_S = 300
EXTREME = {"high_growth_rate": 0.99, "discount_rate": 0.0001, "terminal_growth": 0.9, "fcf_margin": 9.0}


def universe_sample(n: int, seed: int, exclude: List[str]) -> List[str]:
    path = os.path.join(BACKEND, "config", "universe.tsv")
    with open(path, encoding="utf-8") as fh:
        rows = [r for r in csv.reader((ln for ln in fh if not ln.startswith("#")), delimiter="\t")]
    syms = sorted({r[0] for r in rows[1:] if r and r[0] not in exclude})
    return random.Random(seed).sample(syms, n)


async def timed(s, method: str, url: str, **kw):
    t0 = time.monotonic()
    try:
        r = await s.request(method, url, timeout=kw.pop("timeout", 240), **kw)
        return r, round(time.monotonic() - t0, 3), None
    except Exception as e:  # noqa: BLE001 — se anota el tipo, sin cortar el recorrido
        return None, round(time.monotonic() - t0, 3), f"{type(e).__name__}: {e}"


def _json(r) -> Any:
    try:
        return r.json()
    except Exception:  # noqa: BLE001
        return None


def _finite(x) -> bool:
    return isinstance(x, (int, float)) and math.isfinite(x)


def sin_dato_blocks(a: Dict[str, Any]) -> Dict[str, str]:
    """Los bloques del análisis que dicen sin dato, con su motivo (los de /v2: extended y los de nivel superior)."""
    out: Dict[str, str] = {}
    ext = ((a.get("display") or {}).get("extended") or {})
    for k, v in ext.items():
        if isinstance(v, dict) and v.get("status") in ("sin_dato", "no_disponible"):
            out[f"extended.{k}"] = str(v.get("reason"))
    for k in ("company_profile", "history_10y", "price_change", "scenario_inputs", "dcf_status"):
        v = a.get(k)
        if isinstance(v, dict) and (v.get("status") in ("sin_dato", "no_disponible") or v.get("state") == "sin_dato"):
            out[k] = str(v.get("reason"))
    return out


async def one(s, base: str, sym: str) -> Dict[str, Any]:
    out: Dict[str, Any] = {"symbol": sym, "steps": {}}
    st = out["steps"]

    def put(name, r, dt, err, **extra):
        st[name] = {"status": r.status_code if r is not None else None, "s": dt, "error": err, **extra}

    r, dt, err = await timed(s, "GET", f"{base}/api/analysis/{sym}")
    a = _json(r) if r is not None and r.status_code == 200 else None
    put("analysis", r, dt, err, detail=(None if a is not None or r is None else str((_json(r) or {}).get("detail"))[:200]))
    if a is not None:
        out["sin_dato"] = sin_dato_blocks(a)
        out["figures"] = {"price": a.get("price"), "quality": (a.get("quality") or {}).get("score"),
                          "price_score": (a.get("price_attractiveness") or {}).get("score"),
                          "verdict": ((a.get("verdict") or {}).get("text") or "")[:120],
                          "fair_value": (a.get("dcf") or {}).get("fair_value"),
                          "pe": (a.get("key_metrics") or {}).get("pe"),
                          "market_cap": (a.get("profile") or {}).get("market_cap"),
                          "currency": (a.get("profile") or {}).get("currency"),
                          "archetype": (a.get("classification") or {}).get("archetype")}
    r, dt, err = await timed(s, "GET", f"{base}/v2/{sym}")
    put("html_v2", r, dt, err)
    sector = ((a or {}).get("profile") or {}).get("sector")
    r, dt, err = await timed(s, "GET", f"{base}/api/v2/prices/{sym}", params={"sector": sector} if sector else None)
    p = _json(r) if r is not None and r.status_code == 200 else {}
    put("prices", r, dt, err, **{k: {"status": (p.get(k) or {}).get("status"), "reason": (p.get(k) or {}).get("reason")}
                                 for k in ("company", "market", "sector")})
    r, dt, err = await timed(s, "GET", f"{base}/api/v2/segments/{sym}")
    g = _json(r) if r is not None and r.status_code == 200 else {}
    put("segments", r, dt, err, seg_status=(g or {}).get("status"), reason=(g or {}).get("reason"))
    # rivales hasta completar
    t0 = time.monotonic()
    last, polls = None, 0
    while time.monotonic() - t0 < PEERS_TIMEOUT_S:
        r, dt, err = await timed(s, "GET", f"{base}/api/v2/peers/{sym}")
        polls += 1
        last = r
        body = _json(r) if r is not None and r.status_code == 200 else None
        if body is None or body.get("status") != "calculando":
            break
        await asyncio.sleep(min(body.get("poll_s") or 4, 4))
    body = _json(last) if last is not None and last.status_code == 200 else {}
    rivals = (body or {}).get("rivals") or []
    st["peers"] = {"status": last.status_code if last is not None else None, "s": round(time.monotonic() - t0, 3),
                   "polls": polls, "peers_status": (body or {}).get("status"), "note": (body or {}).get("note"),
                   "industry": (body or {}).get("industry"),
                   "rivals": {x["symbol"]: x["status"] + (f" ({x.get('reason')})" if x.get("reason") else "")
                              for x in rivals}}
    # escenario: base, extremos (recorte) y cuerpos malos (422)
    si = (a or {}).get("scenario_inputs")
    if si:
        r, dt, err = await timed(s, "POST", f"{base}/api/v2/scenario", json={"inputs": si, "assumptions": {}})
        b = _json(r) or {}
        same = (si.get("status") != "ok" or b.get("fair_value") is None
                or abs(b["fair_value"] - ((a.get("dcf") or {}).get("fair_value") or 0)) <= 1e-6 * abs(b["fair_value"]))
        put("scenario_base", r, dt, err, sc_status=b.get("status"), reproduces_engine=same, reason=b.get("reason"))
        r, dt, err = await timed(s, "POST", f"{base}/api/v2/scenario", json={"inputs": si, "assumptions": EXTREME})
        b = _json(r) or {}
        vals = [b.get("fair_value"), b.get("upside")] + [x for row in ((b.get("sensitivity") or {}).get("values") or [])
                                                          for x in row]
        put("scenario_extreme", r, dt, err, sc_status=b.get("status"), clamped=b.get("clamped"),
            finite=all(v is None or _finite(v) for v in vals))
        if si.get("base"):
            bad = json.loads(json.dumps(si))
            bad["base"]["high_growth_years"] = 20_000_000
            r, dt, err = await timed(s, "POST", f"{base}/api/v2/scenario", json={"inputs": bad})
            put("scenario_years_422", r, dt, err)
            r, dt, err = await timed(s, "POST", f"{base}/api/v2/scenario",
                                     content=json.dumps({"inputs": si, "assumptions": {"discount_rate": float("nan")}}),
                                     headers={"Content-Type": "application/json"})
            put("scenario_nan_422", r, dt, err)
    r, dt, err = await timed(s, "GET", f"{base}/api/v2/pdf/{sym}", timeout=300)
    put("pdf_v2", r, dt, err, is_pdf=bool(r is not None and r.status_code == 200 and r.content[:4] == b"%PDF"),
        kb=round(len(r.content) / 1024) if r is not None else None)
    return out


async def run(base: str, syms: List[str], concurrency: int) -> List[Dict[str, Any]]:
    from curl_cffi.requests import AsyncSession
    sem = asyncio.Semaphore(concurrency)
    results: List[Dict[str, Any]] = []

    async def go(sym):
        async with sem:
            async with AsyncSession() as s:
                res = await one(s, base, sym)
            results.append(res)
            ok = {k: v.get("status") for k, v in res["steps"].items()}
            print(f"{sym}: {ok}", flush=True)
    await asyncio.gather(*(go(x) for x in syms))
    order = {x: i for i, x in enumerate(syms)}
    return sorted(results, key=lambda r: order[r["symbol"]])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8771")
    ap.add_argument("--seed", type=int, default=20261018)
    ap.add_argument("--random", type=int, default=30)
    ap.add_argument("--concurrency", type=int, default=3)
    ap.add_argument("--only", default="", help="tickers separados por comas (en lugar de la lista completa)")
    ap.add_argument("--name", default="V2_api")
    args = ap.parse_args()
    if args.only:
        syms, groups = [x.strip() for x in args.only.split(",") if x.strip()], {}
    else:
        rnd = universe_sample(args.random, args.seed, VERIFICATION + list(RARE))
        syms = VERIFICATION + rnd + [x for x in RARE if x not in VERIFICATION]
        groups = {"verificacion": VERIFICATION, "universo": rnd, "raros": RARE}
    t0 = time.monotonic()
    res = asyncio.run(run(args.base, syms, args.concurrency))
    os.makedirs(REPORT_DIR, exist_ok=True)
    with open(os.path.join(REPORT_DIR, f"{args.name}.json"), "w", encoding="utf-8") as fh:
        json.dump({"fecha": time.strftime("%Y-%m-%dT%H:%M:%S"), "seed": args.seed, "groups": groups,
                   "duracion_s": round(time.monotonic() - t0), "results": res}, fh, ensure_ascii=False, indent=1)
    print(f"informe: {os.path.join(REPORT_DIR, args.name + '.json')}")


if __name__ == "__main__":
    main()
