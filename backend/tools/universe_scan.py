"""
Modelo general: corre el análisis REAL de cada empresa del universo del backend (config/universe.tsv: S&P 500 + ADR, el
de tendencias y sparklines) y le pasa las reglas de cordura de lib/model_invariants.py. Informe: docs/modelo/ESCANEO_<fecha>.md
y su .json (violaciones por regla, por arquetipo y por empresa, y las más graves con su causa probable).

    cd finanzer_next-mg/backend
    FINNHUB_API_KEY="$(security find-generic-password -s finanzer-finnhub -w)" \\
    SEC_EDGAR_USER_AGENT="$(security find-generic-password -s finanzer-sec-ua -w)" \\
        ../../finanzer_next/.venv313/bin/python tools/universe_scan.py [--limit N] [--symbols A,B] [--no-pdf]
    ../../finanzer_next/.venv313/bin/python tools/universe_scan.py --report-only     # rehace el informe de la caché
    ../../finanzer_next/.venv313/bin/python tools/universe_scan.py --reevaluate      # y vuelve a pasar las reglas

- En el proceso, sin servidor: main._compute_analysis y el PDF nuevo (main._pdf_v2_build) como los pide un usuario,
  sin precalentado ni rivales (el PDF lee los rivales solo de su caché, vacía aquí).
- Por lotes (invariants.escaneo: tamaño, pausa entre lotes, análisis a la vez). Límites compartidos con las demás
  sesiones, por encima de los de la app (sin tocar lib/): EDGAR a ≤ `edgar_max_rps` (envuelve sec_edgar._pace, por
  donde pasa toda descarga de la SEC) y Finnhub a ≤ `finnhub_max_per_min`, sin las rutas que las reglas no usan
  (`finnhub_skip_paths`: titulares, sorpresas, calendario). Yahoo, con los reintentos de la app.
- Vigilancia: pasados `check_after_min`, si el ritmo proyecta más de `max_minutes` o la memoria pasa de `max_rss_mb`, se
  para y deja el informe de lo hecho.
- Caché: un .json por empresa en --cache (por defecto ~/Library/Caches/finanzer-universe-scan/<fecha>); otra corrida
  del mismo día se salta las hechas (reanudable). Lo guardado es el resumen de la empresa y sus violaciones y, aparte y
  comprimidos, el análisis y el texto del PDF (<SÍMBOLO>.analysis.json.gz): con --reevaluate las reglas se vuelven a
  pasar sin descargar nada.
- Las claves vienen del entorno; aquí no se leen ni se escriben.
- Además de las reglas, registra qué componentes del score se registraron en cada empresa (con dato, sin dato, no aplica,
  no significativo): tools/model_inventory.py --scan los usa para la aplicabilidad medida por arquetipo.
"""
import argparse
import concurrent.futures
import datetime as _dt
import gc
import io
import json
import logging
import os
import subprocess
import sys
import threading
import time
import traceback
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(HERE)
REPO = os.path.dirname(BACKEND)
sys.path.insert(0, BACKEND)
sys.path.insert(0, os.path.join(BACKEND, "lib"))
sys.path.insert(0, HERE)

from settings import cfg  # noqa: E402

DOCS = os.path.join(REPO, "docs", "modelo")
# Lo que la ronda F10 (rama fiabilidad/f10-motor, E2a; plan docs/superpowers/plans/2026-10-28-fiabilidad-revision-nvda.md)
# corrige o se espera que corrija, por regla. El escaneo corre sobre la base sin F10: tras fusionarla, repetirlo.
F10 = {"margen_neto_techo": "N1: beneficio no operativo fuera del normalizado",
       "peso_en_referencia": "N2: la referencia sin la empresa (o mediana de pares)",
       "crecimiento_robusto": "N3: BPA con el método robusto y PEG n.s. con base anómala"}
DEFAULT_CACHE = os.path.expanduser("~/Library/Caches/finanzer-universe-scan")


import model_invariants as inv  # noqa: E402


def git_commit() -> Optional[str]:
    try:
        return subprocess.check_output(["git", "-C", REPO, "rev-parse", "--short", "HEAD"], text=True).strip()
    except Exception:  # noqa: BLE001
        return None


def git_branch() -> Optional[str]:
    try:
        return subprocess.check_output(["git", "-C", REPO, "rev-parse", "--abbrev-ref", "HEAD"], text=True).strip()
    except Exception:  # noqa: BLE001
        return None


def pdf_text(pdf: bytes) -> str:
    from pypdf import PdfReader
    r = PdfReader(io.BytesIO(pdf))
    return "\n".join(f"===== página {i + 1} =====\n{p.extract_text() or ''}" for i, p in enumerate(r.pages))


def _summary(sym: str, a: Dict[str, Any]) -> Dict[str, Any]:
    c = a.get("classification") or {}
    km = a.get("key_metrics") or {}
    bm = a.get("benchmark") or {}
    dp = a.get("data_provenance") or {}
    sc = a.get("score") or {}
    return {
        "symbol": sym, "name": (a.get("profile") or {}).get("name"), "archetype": c.get("archetype"),
        "subtype": c.get("subtype"), "rule": c.get("rule"), "classification_confidence": c.get("confidence"),
        "sector": (a.get("profile") or {}).get("sector"), "industry": (a.get("profile") or {}).get("industry"),
        "currency": (a.get("profile") or {}).get("currency"), "market_cap": km.get("market_cap"),
        "quality": (sc.get("quality") or {}).get("score") if isinstance(sc.get("quality"), dict) else sc.get("quality"),
        "price_score": (a.get("price_attractiveness") or {}).get("score"),
        "verdict": (a.get("verdict") or {}).get("text"), "confidence": (a.get("confidence") or {}).get("level"),
        "benchmark": {"profile": bm.get("profile"), "industry": {k: (bm.get("industry") or {}).get(k)
                                                                 for k in ("basis", "damodaran", "region", "classified")}},
        "as_of": (dp.get("as_of") or {}).get("date"), "path": dp.get("path"),
        "edgar": bool((dp.get("edgar") or {}).get("participated") or (dp.get("official_source") or {}).get("status")
                      == "registrado"),
    }


def _analysis_path(cache: str, sym: str) -> str:
    return os.path.join(cache, f"{sym}.analysis.json.gz")


def analyze(sym: str, with_pdf: bool, today: str, cache: Optional[str] = None) -> Dict[str, Any]:
    import model_inventory as mi
    from fastapi import HTTPException
    import main
    t0 = time.monotonic()
    rec: Dict[str, Any] = {"symbol": sym, "status": "ok"}
    with mi.record_components() as regs:
        try:
            a = main._compute_analysis(sym)
        except HTTPException as e:
            return {"symbol": sym, "status": f"http_{e.status_code}", "detail": str(e.detail)[:300],
                    "seconds": round(time.monotonic() - t0, 2)}
        except Exception as e:  # noqa: BLE001 — se anota y se sigue
            return {"symbol": sym, "status": "error", "detail": f"{type(e).__name__}: {e}"[:300],
                    "trace": traceback.format_exc()[-1500:], "seconds": round(time.monotonic() - t0, 2)}
    rec["seconds_analysis"] = round(time.monotonic() - t0, 2)
    rec.update(_summary(sym, a))
    rec["components"] = regs
    rec["breakdown"] = {k: [{"metric": x.get("metric"), "adjustment": x.get("adjustment")} for x in v.get("adjustments") or []]
                        for k, v in ((a.get("score") or {}).get("breakdown") or {}).items()}
    text = None
    if with_pdf:
        t1 = time.monotonic()
        try:
            text = pdf_text(main._pdf_v2_build(sym, a).body)
            rec["pdf"] = "ok"
        except Exception as e:  # noqa: BLE001
            rec["pdf"] = f"error: {type(e).__name__}: {e}"[:200]
        rec["seconds_pdf"] = round(time.monotonic() - t1, 2)
    if cache:
        import gzip
        with gzip.open(_analysis_path(cache, sym), "wt", encoding="utf-8") as fh:
            json.dump({"analysis": a, "pdf_text": text}, fh, ensure_ascii=False, default=str)
    res = inv.evaluate(a, pdf_text=text, today=today)
    rec["results"] = {k: dict(v) for k, v in res.items()}
    rec["peso_input"] = {"symbol": a.get("symbol"), "key_metrics": {"market_cap": (a.get("key_metrics") or {}).get(
        "market_cap")}, "benchmark": a.get("benchmark")}
    rec["seconds"] = round(time.monotonic() - t0, 2)
    return rec


_LIMITS: Dict[str, Any] = {"edgar_calls": 0, "finnhub_calls": 0, "finnhub_skipped": 0}


def install_limits() -> None:
    """EDGAR y Finnhub con los límites del escaneo (invariants.escaneo), por encima de los de la app."""
    import finnhub_fallback
    import sec_edgar
    E = cfg("invariants.escaneo")
    if getattr(sec_edgar._pace, "_scan", False):
        return
    e_lock, e_last = threading.Lock(), [0.0]
    o_pace = sec_edgar._pace

    def pace(budget):
        t0 = time.monotonic()
        with e_lock:
            w = e_last[0] + 1.0 / E["edgar_max_rps"] - time.monotonic()
            if w > 0:
                time.sleep(w)
            e_last[0] = time.monotonic()
            _LIMITS["edgar_calls"] += 1
        budget.add_queue(time.monotonic() - t0)     # la espera en cola no gasta el presupuesto de EDGAR (como la de la app)
        return o_pace(budget)
    pace._scan = True
    sec_edgar._pace = pace

    f_lock, f_last = threading.Lock(), [0.0]
    o_get = finnhub_fallback._get

    def get(path, params):
        if path in E["finnhub_skip_paths"]:
            _LIMITS["finnhub_skipped"] += 1
            return None
        with f_lock:
            w = f_last[0] + 60.0 / E["finnhub_max_per_min"] - time.monotonic()
            if w > 0:
                time.sleep(w)
            f_last[0] = time.monotonic()
            _LIMITS["finnhub_calls"] += 1
        return o_get(path, params)
    finnhub_fallback._get = get


def rss_mb() -> float:
    import resource
    r = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return r / 1e6 if sys.platform == "darwin" else r / 1e3     # macOS en bytes; Linux en KB


def universe_rows() -> List[Dict[str, Any]]:
    import universe
    return universe.rows() if hasattr(universe, "rows") else universe._data()["rows"]


def run(symbols: List[str], cache: str, with_pdf: bool, today: str, workers: Optional[int] = None) -> Optional[str]:
    """Devuelve el motivo de la parada si la vigilancia la cortó; None si terminó. `workers`: análisis a la vez, si no
    son los de la config (p. ej. 1 para quedar por debajo del límite de memoria)."""
    E = dict(cfg("invariants.escaneo"))
    if workers:
        E["workers"] = workers
    install_limits()
    os.makedirs(cache, exist_ok=True)
    todo = [s for s in symbols if not os.path.isfile(os.path.join(cache, f"{s}.json"))]
    print(f"{len(symbols)} empresas, {len(symbols) - len(todo)} ya en la caché ({cache}); quedan {len(todo)}", flush=True)
    lock = threading.Lock()
    done = [0]
    t0 = time.monotonic()
    for b in range(0, len(todo), E["batch_size"]):
        batch = todo[b:b + E["batch_size"]]
        with concurrent.futures.ThreadPoolExecutor(max_workers=E["workers"]) as ex:
            futs = {ex.submit(analyze, s, with_pdf, today, cache): s for s in batch}
            for f in concurrent.futures.as_completed(futs):
                s = futs[f]
                try:
                    rec = f.result()
                except Exception as e:  # noqa: BLE001
                    rec = {"symbol": s, "status": "error", "detail": f"{type(e).__name__}: {e}"}
                with open(os.path.join(cache, f"{s}.json"), "w", encoding="utf-8") as fh:
                    json.dump(rec, fh, ensure_ascii=False, default=str)
                with lock:
                    done[0] += 1
                    nv = sum(len(r.get("violations") or []) for r in (rec.get("results") or {}).values())
                    el = time.monotonic() - t0
                    print(f"[{done[0]}/{len(todo)} · {el / 60:.1f} min · {rss_mb():.0f} MB · EDGAR "
                          f"{_LIMITS['edgar_calls']} · Finnhub {_LIMITS['finnhub_calls']}] {s}: {rec['status']} "
                          f"{rec.get('archetype') or ''} {rec.get('seconds', '')} s, {nv} violaciones", flush=True)
        gc.collect()
        el = (time.monotonic() - t0) / 60
        proj = el * len(todo) / max(done[0], 1)
        if el >= E["check_after_min"] and (proj > E["max_minutes"] or rss_mb() > E["max_rss_mb"]):
            why = (f"vigilancia: a los {el:.1f} min, {done[0]}/{len(todo)} hechas, proyección {proj:.0f} min "
                   f"(límite {E['max_minutes']:.0f}), memoria máxima {rss_mb():.0f} MB (límite {E['max_rss_mb']:.0f})")
            print("PARADA — " + why, flush=True)
            return why
        if b + E["batch_size"] < len(todo):
            time.sleep(E["pause_between_batches_s"])
    return None


def reevaluate(cache: str, symbols: List[str], today: str) -> int:
    """Vuelve a pasar las reglas sobre los análisis guardados (sin red) y reescribe los resultados en la caché."""
    import gzip
    n = 0
    for s in symbols:
        p, ap = os.path.join(cache, f"{s}.json"), _analysis_path(cache, s)
        if not (os.path.isfile(p) and os.path.isfile(ap)):
            continue
        with open(p, encoding="utf-8") as fh:
            rec = json.load(fh)
        with gzip.open(ap, "rt", encoding="utf-8") as fh:
            saved = json.load(fh)
        rec["results"] = {k: dict(v) for k, v in inv.evaluate(saved["analysis"], pdf_text=saved.get("pdf_text"),
                                                              today=today).items()}
        with open(p, "w", encoding="utf-8") as fh:
            json.dump(rec, fh, ensure_ascii=False, default=str)
        n += 1
    return n


# ═══════════════════════ Informe ═══════════════════════

def load_cache(cache: str, symbols: List[str]) -> List[Dict[str, Any]]:
    out = []
    for s in symbols:
        p = os.path.join(cache, f"{s}.json")
        if os.path.isfile(p):
            with open(p, encoding="utf-8") as fh:
                out.append(json.load(fh))
    return out


def universe_caps(recs: List[Dict[str, Any]], rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Capitalización del universo por (industria de Damodaran, región), con la clasificación de config/universe.tsv."""
    firm = {r["symbol"]: (r.get("damodaran_industry"), r.get("damodaran_region")) for r in rows
            if r.get("damodaran_industry")}
    caps: Dict[Any, float] = defaultdict(float)
    counts: Counter = Counter()
    for r in recs:
        f, mc = firm.get(r["symbol"]), r.get("market_cap")
        if r.get("status") == "ok" and f and isinstance(mc, (int, float)) and mc > 0:
            caps[f] += mc
            counts[f] += 1
    return {"firm": firm, "caps": dict(caps), "counts": dict(counts)}


def finalize(recs: List[Dict[str, Any]], rows: List[Dict[str, Any]]) -> None:
    """La regla del peso en la referencia necesita el universo entero: se evalúa al final, con la caché."""
    U = universe_caps(recs, rows)
    for r in recs:
        if r.get("status") == "ok" and r.get("peso_input"):
            r["results"]["peso_en_referencia"] = dict(inv.peso_en_referencia(r["peso_input"], {"universe": U}))


def _fmt_pct(n: int, d: int) -> str:
    return f"{n / d:.0%}" if d else "—"


def build_report(recs: List[Dict[str, Any]], meta: Dict[str, Any]) -> Dict[str, Any]:
    ok = [r for r in recs if r.get("status") == "ok"]
    by_rule = {k: Counter() for k in inv.RULES}
    rule_examples: Dict[str, List[Any]] = defaultdict(list)
    by_arch: Dict[str, Counter] = defaultdict(Counter)
    arch_n: Counter = Counter()
    all_v: List[Dict[str, Any]] = []
    per_company = []
    for r in ok:
        arch = r.get("archetype") or "?"
        if r.get("subtype"):
            arch_key = f"{arch} · {r['subtype']}"
        else:
            arch_key = arch
        arch_n[arch_key] += 1
        nv, rules_hit = 0, []
        for k, res in (r.get("results") or {}).items():
            by_rule.setdefault(k, Counter())[res["state"]] += 1
            if res["state"] == "violacion":
                by_arch[arch_key][k] += 1
                rules_hit.append(k)
                n = res.get("count") or len(res["violations"])
                nv += n
                for v in res["violations"]:
                    all_v.append({**v, "symbol": r["symbol"], "archetype": arch_key, "name": r.get("name")})
                rule_examples[k].append((max(v["severity"] for v in res["violations"]), r["symbol"]))
        per_company.append({"symbol": r["symbol"], "name": r.get("name"), "archetype": arch_key, "violations": nv,
                            "rules": rules_hit, "quality": r.get("quality"), "price_score": r.get("price_score"),
                            "confidence": r.get("confidence")})
    groups: Dict[str, Counter] = {"motivo_de_vacio": Counter(), "cifra_unica": Counter()}
    for r in ok:
        res = (r.get("results") or {})
        for k, n in ((res.get("motivo_de_vacio") or {}).get("fields") or {}).items():
            groups["motivo_de_vacio"][k] += n
        seen = set()
        for v in (res.get("cifra_unica") or {}).get("violations") or []:
            import re as _re
            m = _re.match(r"(\S+) \(([^)]*)\): \S+ en ([\w.]+?)(?:\.rows|\.points|\[|\.value| ).*? frente a \S+ en "
                          r"([\w.]+?)(?:\.rows|\.points|\[|\.value| |$)", v["detail"])
            key = f"{m.group(1)} · {m.group(3)} · {m.group(4)}" if m else v["detail"].split(":")[0]
            if key not in seen:
                seen.add(key)
                groups["cifra_unica"][key] += 1
    top_n = cfg("invariants.escaneo.top_n")
    # Las más graves: una por (empresa, regla) para que una empresa con diez cifras dobles no llene la lista.
    best: Dict[Any, Dict[str, Any]] = {}
    for v in all_v:
        k = (v["symbol"], v["rule"])
        if k not in best or v["severity"] > best[k]["severity"]:
            best[k] = v
    top = sorted(best.values(), key=lambda v: (-v["severity"], v["symbol"], v["rule"]))[:top_n]
    statuses = Counter(r.get("status") for r in recs)
    errors = [{"symbol": r["symbol"], "status": r.get("status"), "detail": r.get("detail")} for r in recs
              if r.get("status") != "ok"]
    return {"meta": {**meta, "companies": len(recs), "ok": len(ok), "statuses": dict(statuses),
                     "edgar_share": sum(1 for r in ok if r.get("edgar")) / len(ok) if ok else None,
                     "pdf_ok": sum(1 for r in ok if r.get("pdf") == "ok"),
                     "seconds_median": sorted(r.get("seconds", 0) for r in ok)[len(ok) // 2] if ok else None},
            "rules": {k: {"title": inv.RULES[k][1] if k in inv.RULES else k, "states": dict(c),
                          "examples": [s for _, s in sorted(rule_examples[k], key=lambda x: (-x[0], x[1]))[:8]]}
                      for k, c in by_rule.items()},
            "by_archetype": {a: {"n": arch_n[a], "violations": dict(by_arch[a])} for a in sorted(arch_n)},
            "archetypes": dict(Counter(r.get("archetype") for r in ok)),
            "subtypes": dict(Counter(f"{r.get('archetype')} · {r.get('subtype')}" for r in ok if r.get("subtype"))),
            "classification_rules": dict(Counter(r.get("rule") for r in ok)),
            "top": top, "companies": sorted(per_company, key=lambda c: (-c["violations"], c["symbol"])),
            "groups": {k: dict(v) for k, v in groups.items()},
            "errors": errors}


def write_markdown(rep: Dict[str, Any], path: str) -> None:
    M, R = rep["meta"], rep["rules"]
    n_ok = M["ok"]
    L = [f"# Escaneo del universo con las reglas de cordura ({M['date']})", "",
         f"> Generado por `backend/tools/universe_scan.py` (commit `{M.get('commit')}`, rama `{M.get('branch') or '?'}`). "
         "No editar a mano: se rehace con `--report-only` desde la caché. Las reglas MIDEN: ninguna puntuación cambió.", "",
         "## Corrida", "",
         f"- Universo: {M['universe']} empresas (`config/universe.tsv`, S&P 500 + ADR); analizadas {M['companies']}; "
         f"con análisis {n_ok}. Estados: " + ", ".join(f"{k} {v}" for k, v in sorted(M["statuses"].items())) + ".",
         f"- Análisis real en el proceso (`main._compute_analysis`), sin precalentado ni rivales; PDF nuevo "
         f"{'generado en ' + str(M['pdf_ok']) + ' empresas' if M.get('with_pdf') else 'no generado (--no-pdf)'}.",
         f"- Con EDGAR (fuente oficial registrada): {M['edgar_share']:.0%}." if M.get("edgar_share") is not None else "",
         f"- Tiempo mediano por empresa: {M.get('seconds_median')} s; duración total: {M.get('duration_min', '—')} min; "
         f"memoria máxima del proceso {M.get('max_rss_mb', '—')} MB.",
         f"- Límites (compartidos con las demás sesiones): EDGAR ≤ {M['scan_config']['edgar_max_rps']:g} peticiones/s "
         f"({M['limits'].get('edgar_calls')} peticiones), Finnhub ≤ {M['scan_config']['finnhub_max_per_min']}/min "
         f"({M['limits'].get('finnhub_calls')} llamadas; {M['limits'].get('finnhub_skipped')} saltadas: "
         f"{', '.join(M['scan_config']['finnhub_skip_paths'])}, que las reglas no usan); "
         f"{M['scan_config']['workers']} análisis a la vez, lotes de {M['scan_config']['batch_size']}."
         if M.get("scan_config") and M.get("limits") else "",
         f"- **Parado por la vigilancia**: {M['stopped']}." if M.get("stopped") else "",
         "- `peso_en_referencia` mide el peso con la capitalización de las empresas del UNIVERSO en esa industria de "
         "Damodaran (el agregado de Damodaran tiene más empresas): es una cota superior del peso real.", "",
         "## Violaciones por regla", "",
         f"Base del escaneo: `{M.get('branch') or '?'}` en `{M.get('commit')}`. La columna F10 dice qué ronda de F10 "
         "corrige cada regla; las violaciones que quedan son lo pendiente del modelo general.", "",
         "| Regla | Comprobación | Violación | OK | No aplica | No evaluable | % de las evaluadas | F10 | Ejemplos (más graves) |",
         "|---|---|---:|---:|---:|---:|---:|---|---|"]
    for k, x in sorted(R.items(), key=lambda kv: -kv[1]["states"].get("violacion", 0)):
        s = x["states"]
        ev = s.get("violacion", 0) + s.get("ok", 0)
        L.append(f"| `{k}` | {x['title']} | {s.get('violacion', 0)} | {s.get('ok', 0)} | {s.get('no_aplica', 0)} | "
                 f"{s.get('no_evaluable', 0)} | {_fmt_pct(s.get('violacion', 0), ev)} | {F10.get(k, '—')} | "
                 f"{', '.join(x['examples'])} |")
    massive = [k for k, x in R.items()
               if (x["states"].get("violacion", 0) + x["states"].get("ok", 0))
               and x["states"].get("violacion", 0) / (x["states"].get("violacion", 0) + x["states"].get("ok", 0)) >= 0.3]
    if massive:
        L += ["", "**Fallo masivo (≥ 30 % de las evaluadas):** " + ", ".join(f"`{k}`" for k in massive) + "."]
    G = rep.get("groups") or {}
    if G.get("motivo_de_vacio"):
        tot = sum(G["motivo_de_vacio"].values())
        top = sorted(G["motivo_de_vacio"].items(), key=lambda kv: -kv[1])
        top10 = sum(n for _, n in top[:10])
        L += ["", "### Vacíos sin motivo, por campo", "",
              f"{tot} vacíos sin motivo en {R['motivo_de_vacio']['states'].get('violacion', 0)} empresas, en {len(top)} "
              f"campos; los 10 primeros suman el {top10 / tot:.0%}.", "",
              "| Campo | Vacíos |", "|---|---:|"] + [f"| {k} | {n} |" for k, n in top[:20]]
    if G.get("cifra_unica"):
        L += ["", "### Cifras dobles, por par de bloques", "",
              "| Métrica · bloque A · bloque B | Empresas |", "|---|---:|"] + [
            f"| {k} | {n} |" for k, n in sorted(G["cifra_unica"].items(), key=lambda kv: -kv[1])]
    archs = rep["by_archetype"]
    rules = [k for k in R if any(archs[a]["violations"].get(k) for a in archs)]
    L += ["", "## Violaciones por arquetipo", "",
          "Empresas con al menos una violación de cada regla, sobre las empresas del arquetipo (n).", "",
          "| Arquetipo | n | " + " | ".join(f"`{k}`" for k in rules) + " |",
          "|---|---:|" + "---:|" * len(rules)]
    for a, x in archs.items():
        L.append(f"| {a} | {x['n']} | " + " | ".join(str(x["violations"].get(k, 0) or "") for k in rules) + " |")
    L += ["", f"## Las {len(rep['top'])} más graves", "",
          "Severidad = peso de la regla (config/invariants.toml) × magnitud (cuánto se pasa del umbral, acotada). Una "
          "por empresa y regla.", "",
          "| # | Empresa | Arquetipo | Regla | Severidad | Qué | Causa probable |", "|---:|---|---|---|---:|---|---|"]
    for i, v in enumerate(rep["top"], 1):
        L.append(f"| {i} | {v['symbol']} ({v.get('name') or ''}) | {v['archetype']} | `{v['rule']}` | {v['severity']:.1f} | "
                 f"{v['detail'].replace('|', '/')} | {v['cause'].replace('|', '/')} |")
    L += ["", "## Tipos de empresa en el universo", "",
          "| Arquetipo | Empresas |", "|---|---:|"]
    for a, n in sorted(rep["archetypes"].items(), key=lambda kv: -kv[1]):
        L.append(f"| {a} | {n} |")
    if rep["subtypes"]:
        L += ["", "Subtipos: " + "; ".join(f"{k} {v}" for k, v in sorted(rep["subtypes"].items())) + "."]
    L += ["", "Regla de clasificación que decidió: " + "; ".join(
        f"`{k}` {v}" for k, v in sorted(rep["classification_rules"].items(), key=lambda kv: -kv[1])) + "."]
    L += ["", "## Por empresa (con alguna violación)", "",
          "| Empresa | Arquetipo | Violaciones | Reglas | Calidad | Precio | Confianza |", "|---|---|---:|---|---:|---:|---|"]
    for c in rep["companies"]:
        if c["violations"]:
            L.append(f"| {c['symbol']} | {c['archetype']} | {c['violations']} | {', '.join(c['rules'])} | "
                     f"{c.get('quality') if c.get('quality') is not None else '—'} | "
                     f"{c.get('price_score') if c.get('price_score') is not None else '—'} | {c.get('confidence') or '—'} |")
    if rep["errors"]:
        L += ["", "## Sin análisis", "", "| Empresa | Estado | Detalle |", "|---|---|---|"]
        for e in rep["errors"]:
            L.append(f"| {e['symbol']} | {e['status']} | {str(e.get('detail') or '').replace('|', '/')[:200]} |")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(x for x in L if x is not None) + "\n")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", help="lista separada por comas (por defecto, todo el universo)")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--no-pdf", action="store_true")
    ap.add_argument("--date", default=_dt.date.today().isoformat())
    ap.add_argument("--cache")
    ap.add_argument("--report-only", action="store_true")
    ap.add_argument("--workers", type=int, help="análisis a la vez (por defecto, invariants.escaneo.workers)")
    ap.add_argument("--reevaluate", action="store_true", help="reglas de nuevo sobre los análisis guardados (sin red)")
    ap.add_argument("--out", default=DOCS)
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.ERROR)
    logging.getLogger().setLevel(logging.ERROR)
    rows = universe_rows()
    syms = [s.strip().upper() for s in args.symbols.split(",")] if args.symbols else [r["symbol"] for r in rows]
    if args.limit:
        syms = syms[:args.limit]
    cache = args.cache or os.path.join(DEFAULT_CACHE, args.date)
    t0 = time.monotonic()
    stopped = None
    if args.reevaluate:
        args.report_only = True
        print(f"reevaluadas {reevaluate(cache, syms, args.date)} empresas con los análisis guardados", flush=True)
    if not args.report_only:
        stopped = run(syms, cache, not args.no_pdf, args.date, args.workers)
    recs = load_cache(cache, syms)
    finalize(recs, rows)
    meta = {"date": args.date, "commit": git_commit(), "branch": git_branch(), "universe": len(rows), "with_pdf": not args.no_pdf,
            "duration_min": None if args.report_only else round((time.monotonic() - t0) / 60, 1), "cache": cache,
            "stopped": stopped, "limits": dict(_LIMITS), "max_rss_mb": round(rss_mb()),
            "scan_config": {**{k: (list(v) if isinstance(v, tuple) else v) for k, v in cfg("invariants.escaneo").items()},
                            **({"workers": args.workers} if args.workers else {})}}
    if args.report_only and os.path.isfile(os.path.join(args.out, f"ESCANEO_{args.date}.json")):
        with open(os.path.join(args.out, f"ESCANEO_{args.date}.json"), encoding="utf-8") as fh:
            old = json.load(fh).get("meta", {})
        meta.update({k: old.get(k) for k in ("duration_min", "stopped", "limits", "max_rss_mb", "scan_config", "commit")})
    rep = build_report(recs, meta)
    os.makedirs(args.out, exist_ok=True)
    js = os.path.join(args.out, f"ESCANEO_{args.date}.json")
    # El json lleva el informe y, por empresa, los componentes registrados (para tools/model_inventory.py --scan).
    rep["components"] = {r["symbol"]: {"archetype": r.get("archetype"), "subtype": r.get("subtype"),
                                       "components": r.get("components"), "breakdown": r.get("breakdown")}
                         for r in recs if r.get("status") == "ok"}
    with open(js, "w", encoding="utf-8") as fh:
        json.dump(rep, fh, ensure_ascii=False, indent=1, default=str)
    write_markdown(rep, os.path.join(args.out, f"ESCANEO_{args.date}.md"))
    print(f"informe: {os.path.join(args.out, f'ESCANEO_{args.date}.md')} ({rep['meta']['ok']} con análisis)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
