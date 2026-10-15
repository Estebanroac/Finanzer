"""
Fase 7 del plan de fiabilidad (parte 1): vigilancia semanal del panel contra producción.

    cd finanzer_next/backend
    ../.venv313/bin/python tests/vigilancia.py                       # corre y compara con la corrida anterior
    ../.venv313/bin/python tests/vigilancia.py --prev <DIR>          # compara con otra carpeta
    ../.venv313/bin/python tests/vigilancia.py --solo-comparar <DIR> --prev <DIR>   # sin red: compara dos corridas

Corrida (reutiliza `panel_run` en modo live): despierta el servidor (una petición a /api/health, descartada), corre
todos los tickers del panel contra https://finanzer.app a concurrencia 3 y guarda en
~/Downloads/finanzer_vigilancia/<AAAA-MM-DD>/ el resumen.csv/md, JSON, PDF por ticker y meta.json (hora, commit de
/api/health o null, sello de build de /build-stamp.json). Se niega a correr de 15:55 a 16:45 de Nueva York (captura
de la 2a y de la F5prep) y con concurrencia > 3.

Comparación con la corrida anterior (la carpeta más reciente o --prev). Severidades:
  · ALERTA, rotura de fuente: cambia el arquetipo, el nivel de calidad, el nivel de precio o la confianza sin que
    cambien el código, el precio (±0.5%) ni los datos de los estados. Si solo cambió la Rf (o el precio dentro del
    ±0.5%), se contrasta repitiendo el replay del fixture con la Rf y el precio de cada corrida (la misma separación
    que `panel_run`): si el replay también cambia de nivel, es efecto frontera (aviso); si no, alerta.
  · ALERTA, error: HTTP distinto de 200 (salvo SPY, que espera 422), un análisis con `errors` o un PDF que no se genera.
  · AVISO: p95 de /api/analysis o /api/pdf más de un 50% peor; un campo que pasa de dato a "sin dato"; un nivel que
    cambia con el código, el precio, la Rf o datos nuevos (explicado). Sin el commit de alguna de las dos corridas no
    se puede separar una rotura de un cambio de código: el cambio se degrada a aviso y se dice.

Salida: alertas.md (lo primero que se lee) y comparacion.json en la carpeta de la corrida actual. Código de salida 1
si hay alguna alerta, 0 si no.
"""
import argparse
import datetime as _dt
import glob
import json
import logging
import math
import os
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fixture_backend as fb  # noqa: E402
import panel_run as pr  # noqa: E402

ROOT = os.path.expanduser("~/Downloads/finanzer_vigilancia")
BASE_URL = "https://finanzer.app"
MAX_CONCURRENCY = 3
FORBIDDEN_NY = ((15, 55), (16, 45))    # captura de la 2a (Finnhub) y de la F5prep (Yahoo) tras el cierre
PRICE_TOL = 0.005                      # ±0.5%: por debajo, el precio "no cambió"
RF_TOL = 0.0001                        # 1 pb
LATENCY_WORSE = 0.50                   # p95 más de un 50% peor → aviso
LEVEL_KEYS = pr.CHANGE_KEYS            # arquetipo, calidad_nivel, precio_nivel, confianza
# Huella de los estados financieros: el periodo (fechas) y las cifras que salen de ellos. Ni el precio ni la Rf
# entran aquí: cambiar de trimestre o de ejercicio es "datos nuevos".
STATEMENT_PERIOD = ("data_provenance.ttm.balance_date", "data_provenance.ttm.basis",
                    "data_provenance.ttm.quarters.inc", "data_provenance.ttm.quarters.cf",
                    "data_provenance.currency.share_class.statement_shares_date", "yearly_financials.years")
STATEMENT_VALUES = tuple(f"key_metrics.{k}" for k in (
    "revenue", "operating_income", "net_income", "free_cash_flow", "operating_cash_flow", "ebitda", "total_debt",
    "cash", "total_equity", "total_assets", "interest_expense", "net_interest_income", "ffo")) + (
    "yearly_financials.revenue", "yearly_financials.net_income", "yearly_financials.free_cash_flow")
# Datos de otras fuentes (Finnhub y la cotización de Yahoo): NO explican un cambio de nivel; se citan como pista de
# qué fuente cambió cuando hay una rotura.
OTHER_SOURCES = tuple(f"key_metrics.{k}" for k in (
    "eps", "beta", "forward_pe", "revenue_growth", "earnings_growth", "payout_ratio", "shares_outstanding")) + (
    "data_provenance.path", "finnhub_fields")
# Campos que se vigilan por si pasan de dato a "sin dato".
_NO_DATA_BLOCKS = ("altman_z.available", "piotroski_f.available", "dcf.available")


# ═══════════════════════════ reglas de la corrida ═══════════════════════════

def ny_now():
    try:
        from zoneinfo import ZoneInfo
        return _dt.datetime.now(ZoneInfo("America/New_York"))
    except Exception:  # pragma: no cover - zoneinfo existe en 3.9+
        return _dt.datetime.utcnow() - _dt.timedelta(hours=4)


def in_forbidden_window(t):
    """True si `t` (hora de Nueva York) cae de 15:55 a 16:45, ambos incluidos."""
    (h0, m0), (h1, m1) = FORBIDDEN_NY
    return (h0, m0) <= (t.hour, t.minute) <= (h1, m1)


def _get_json(url, timeout):
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "finanzer-vigilancia"}),
                                    timeout=timeout) as r:
            body, status = r.read(), r.status
    except urllib.error.HTTPError as e:
        body, status = e.read(), e.code
    except (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError) as e:
        return None, {"error": type(e).__name__}, time.monotonic() - t0
    try:
        data = json.loads(body)
    except Exception:
        data = None
    return status, data, time.monotonic() - t0


def _robust_get(url, timeout):
    """`panel_run._get` sin caerse por un timeout o una conexión cortada: status 0 (lo marca como error)."""
    t0 = time.monotonic()
    try:
        return _orig_get(url, timeout)
    except (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError) as e:
        return 0, json.dumps({"detail": f"sin respuesta: {type(e).__name__}"}).encode(), time.monotonic() - t0


_orig_get = pr._get


def run_live(out, base_url=BASE_URL, tickers=None, concurrency=MAX_CONCURRENCY, now=None):
    """Despierta el servidor, corre el panel en live y escribe meta.json. Devuelve meta."""
    if concurrency > MAX_CONCURRENCY:
        raise SystemExit(f"concurrencia {concurrency} > {MAX_CONCURRENCY}: producción atiende en serie")
    t = now or ny_now()
    if in_forbidden_window(t):
        raise SystemExit(f"{t:%H:%M} de Nueva York: ventana prohibida 15:55–16:45 (capturas del cierre)")
    base_url = base_url.rstrip("/")
    os.makedirs(out, exist_ok=True)
    started = _dt.datetime.now().astimezone()
    w_status, _, w_el = _get_json(f"{base_url}/api/health", 180)          # despertar: se descarta
    h_status, health, h_el = _get_json(f"{base_url}/api/health", 60)
    s_status, stamp, _ = _get_json(f"{base_url}/build-stamp.json", 60)
    health = health if isinstance(health, dict) else {}
    pr._get = _robust_get
    try:
        rows, _, live = pr.run("live", out, tickers, base_url=base_url, concurrency=concurrency)
    finally:
        pr._get = _orig_get
    meta = {
        "fecha": started.isoformat(timespec="seconds"),
        "fecha_ny": t.isoformat(timespec="seconds"),
        "fin": _dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "base_url": base_url, "concurrencia": concurrency, "tickers": [r["ticker"] for r in rows],
        "commit": health.get("commit"), "commit_origen": "api/health" if health.get("commit") else None,
        "health": {"status": h_status, "body": health, "despertar_s": round(w_el, 1), "despertar_http": w_status,
                   "segunda_s": round(h_el, 2)},
        "build_stamp": stamp if s_status == 200 and isinstance(stamp, dict) else None,
        "herramienta_commit": fb.git_commit(),
    }
    with open(os.path.join(out, "meta.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=1, ensure_ascii=False)
    return meta


# ═══════════════════════════ lectura de una corrida ═══════════════════════════

def load_run(path, declared_commit=None):
    """Una corrida en disco: resumen, análisis por ticker y meta. Acepta las corridas de `panel_run` sin meta.json
    (F0, F1): el commit queda desconocido salvo que se declare (`declared_commit`)."""
    meta = {}
    mp = os.path.join(path, "meta.json")
    if os.path.isfile(mp):
        with open(mp, encoding="utf-8") as fh:
            meta = json.load(fh)
    if declared_commit:
        meta = dict(meta, commit=declared_commit, commit_origen="declarado por el operador")
    rows = pr.read_summary(path)
    analyses = {}
    for sym in rows:
        jp = os.path.join(path, f"{sym}.json")
        if os.path.isfile(jp):
            with open(jp, encoding="utf-8") as fh:
                analyses[sym] = json.load(fh)
    if not meta.get("fecha"):
        m = re.search(r"^- fecha: (.+)$", _read(os.path.join(path, "resumen.md")), re.M)
        meta["fecha"] = m.group(1).strip() if m else None
    return {"path": path, "meta": meta, "rows": rows, "analyses": analyses}


def _read(p):
    try:
        with open(p, encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return ""


def latest_run(root=ROOT, exclude=None):
    """La carpeta de corrida más reciente bajo `root` (por nombre AAAA-MM-DD[...]), sin `exclude`."""
    dirs = sorted(d for d in glob.glob(os.path.join(root, "*"))
                  if os.path.isfile(os.path.join(d, "resumen.csv"))
                  and (not exclude or os.path.abspath(d) != os.path.abspath(exclude)))
    return dirs[-1] if dirs else None


def _get(d, path):
    for k in path.split("."):
        if not isinstance(d, dict):
            return None
        d = d.get(k)
    return d


def extract(analysis, path):
    """Valor de un campo de la huella (con los casos especiales de las listas)."""
    if path.startswith("yearly_financials."):
        yf = analysis.get("yearly_financials") or []
        key = path.split(".", 1)[1]
        return [y.get("year") for y in yf] if key == "years" else [y.get(key) for y in yf]
    if path == "finnhub_fields":
        fields = _get(analysis, "data_provenance.fields") or {}
        return sorted(k for k, v in fields.items() if (v or {}).get("source") == "finnhub")
    return _get(analysis, path)


def _same(x, y, rel=1e-6):
    if isinstance(x, list) and isinstance(y, list):
        return len(x) == len(y) and all(_same(a, b, rel) for a, b in zip(x, y))
    if (isinstance(x, (int, float)) and isinstance(y, (int, float)) and not isinstance(x, bool)
            and not isinstance(y, bool)):
        if any(isinstance(v, float) and math.isnan(v) for v in (x, y)):
            return all(isinstance(v, float) and math.isnan(v) for v in (x, y))
        return abs(x - y) <= 1e-12 + rel * max(abs(x), abs(y))
    return x == y


def diff_paths(a, b, paths):
    return {p: (extract(a, p), extract(b, p)) for p in paths if not _same(extract(a, p), extract(b, p))}


# ═══════════════════════════ código ═══════════════════════════

def same_code(c0, c1, repo=fb.REPO_DIR):
    """True si los dos commits tienen el mismo backend y el mismo frontend compilado (los commits de solo
    documentación no cambian lo que sirve producción). None si git no los conoce."""
    if c0 == c1:
        return True
    try:
        r = subprocess.run(["git", "-C", repo, "diff", "--quiet", c0, c1, "--", "backend/", "frontend/out/",
                            "requirements.txt", "build.sh"], capture_output=True, timeout=30)
    except Exception:
        return None
    return {0: True, 1: False}.get(r.returncode)


def code_change(prev_meta, cur_meta, code_cmp=same_code):
    """('distinto' | 'igual' | 'desconocido', explicación)."""
    c0, c1 = prev_meta.get("commit"), cur_meta.get("commit")
    s0 = (prev_meta.get("build_stamp") or {}).get("contract_sha256")
    s1 = (cur_meta.get("build_stamp") or {}).get("contract_sha256")
    if c0 and c1:
        same = code_cmp(c0, c1)
        if same is True:
            return "igual", (f"mismo commit ({c1[:7]})" if c0 == c1
                             else f"commits {c0[:7]} → {c1[:7]} sin cambios en backend/ ni frontend/out/")
        if same is False:
            return "distinto", f"commit distinto: {c0[:7]} → {c1[:7]}"
        return "distinto", f"commits {c0[:7]} → {c1[:7]} (git no los conoce: se tratan como distintos)"
    if s0 and s1 and s0 != s1:
        return "distinto", "sello de build distinto (contrato de la web cambiado)"
    falta = " y ".join(n for n, c in (("anterior", c0), ("actual", c1)) if not c)
    return "desconocido", f"sin commit en la corrida {falta}: no se puede distinguir una rotura de un cambio de código"


# ═══════════════════════════ contraste con el replay (Rf y precio) ═══════════════════════════

def replay_counterfactual(sym, prev_a, cur_a, env=fb.PANEL_ENV):
    """¿Mueve la Rf (y el precio) de las dos corridas el nivel en el replay del fixture? Devuelve
    {clave: (nivel con la Rf/precio anteriores, nivel con los actuales)} o None si no hay fixture."""
    if not os.path.isdir(os.path.join(fb.fixtures_dir(env), sym)):
        return None
    out = {}
    rows = []
    for a in (prev_a, cur_a):
        rf = a.get("risk_free") or None
        rows.append(pr.summarize(sym, pr._replay_with(sym, env, rf=rf, price=a.get("price"))))
    for k in LEVEL_KEYS:
        out[k] = (str(rows[0].get(k, "")), str(rows[1].get(k, "")))
    return out


# ═══════════════════════════ comparación ═══════════════════════════

def _pct(v):
    v = [float(x) for x in v if x not in ("", None)]
    if not v:
        return {"n": 0, "p50": None, "p95": None, "max": None}
    v.sort()

    def q(p):
        k = (len(v) - 1) * p
        lo, hi = math.floor(k), math.ceil(k)
        return v[lo] + (v[hi] - v[lo]) * (k - lo)
    return {"n": len(v), "p50": round(q(0.5), 2), "p95": round(q(0.95), 2), "max": round(v[-1], 2)}


def latencies(run):
    """p50/p95/máx (interpolación lineal) de las peticiones con HTTP 200: un 422 rápido no rebaja el p95."""
    rows = [r for r in run["rows"].values() if str(r.get("http")) == "200"]
    return {"analysis": _pct(r.get("tiempo_s") for r in rows),
            "pdf": _pct(r.get("tiempo_pdf_s") for r in rows)}


def _expects_422(sym):
    return pr.EXPECTED.get(sym) == "422"


def errors_of(run):
    """[(ticker, causa)] de los errores de la corrida."""
    out = []
    for sym, r in run["rows"].items():
        http = str(r.get("http", ""))
        if _expects_422(sym):
            if http != "422":
                out.append((sym, f"HTTP {http}; se espera 422 (no es una acción)"))
            continue
        if http != "200":
            out.append((sym, f"HTTP {http}: {r.get('errores') or 'sin detalle'}"))
            continue
        if r.get("errores"):
            out.append((sym, f"el análisis trae errores: {r['errores']}"))
        if not str(r.get("paginas_pdf", "")).strip():
            out.append((sym, "el PDF no se generó"))
    return out


def lost_fields(prev_a, cur_a):
    """Campos que tenían dato y ahora no."""
    lost = [f"key_metrics.{k}" for k, v in (prev_a.get("key_metrics") or {}).items()
            if v is not None and (cur_a.get("key_metrics") or {}).get(k) is None]
    lost += [p for p in _NO_DATA_BLOCKS if _get(prev_a, p) is True and _get(cur_a, p) is not True]
    return sorted(lost)


def explain(sym, prev, cur, code, counterfactual=replay_counterfactual):
    """Severidad y causa de un cambio de nivel de `sym`. Devuelve (severidad, causa, detalle)."""
    a0, a1 = prev["analyses"].get(sym) or {}, cur["analyses"].get(sym) or {}
    p0, p1 = a0.get("price"), a1.get("price")
    dprice = (p1 / p0 - 1) if p0 and p1 else None
    rf0, rf1 = _get(a0, "risk_free.value"), _get(a1, "risk_free.value")
    drf = (rf1 - rf0) if rf0 is not None and rf1 is not None else None
    period = diff_paths(a0, a1, STATEMENT_PERIOD)
    values = diff_paths(a0, a1, STATEMENT_VALUES)
    others = diff_paths(a0, a1, OTHER_SOURCES)
    detail = {"precio": [p0, p1], "precio_var": None if dprice is None else round(dprice, 5),
              "rf": [rf0, rf1], "estados_periodo": period, "estados_cifras": sorted(values),
              "otras_fuentes": sorted(others), "codigo": code[1]}
    pista = f"; cambian datos de otras fuentes: {', '.join(sorted(others))}" if others else ""
    causes = []
    if code[0] == "distinto":
        causes.append(f"cambio de código ({code[1]})")
    if period:
        k, (x, y) = next(iter(period.items()))
        causes.append(f"datos nuevos de los estados (periodo: {k.split('.')[-1]} {_s(x)} → {_s(y)})")
    appeared = sorted(k for k, (x, y) in values.items() if x is None or y is None)
    changed = sorted(k for k in values if k not in appeared)
    if changed:
        causes.append("estados con el mismo periodo y otras cifras (" + ", ".join(changed[:4])
                      + "): la fuente cambia sin periodo nuevo, revisar")
    if appeared:
        causes.append("campos de los estados que aparecen o desaparecen (" + ", ".join(appeared[:4]) + ")")
    if dprice is not None and abs(dprice) > PRICE_TOL:
        causes.append(f"precio {p0:.2f} → {p1:.2f} ({dprice:+.1%})")
    if code[0] == "desconocido":
        # Sin commit no se puede descartar un cambio de código: nunca se alerta, se dice.
        return "aviso", "; ".join(causes + [code[1]]) + pista, detail
    if causes:
        return "aviso", "explicado por: " + "; ".join(causes) + pista, detail
    market = (drf is not None and abs(drf) >= RF_TOL) or (dprice is not None and dprice != 0)
    if market:
        cf = counterfactual(sym, a0, a1) if counterfactual else None
        detail["contraste_replay"] = cf
        mov = f"Rf {_s(rf0)} → {_s(rf1)}, precio {dprice:+.2%}" if dprice is not None else f"Rf {rf0} → {rf1}"
        if cf is None:
            if drf is not None and abs(drf) >= RF_TOL:
                return "aviso", f"atribuible a la Rf ({mov}), sin fixture para contrastarlo{pista}", detail
        else:
            moved = [k for k, (x, y) in cf.items() if x != y]
            if moved:
                return ("aviso", f"efecto frontera: la Rf y el precio ({mov}) también cambian "
                        f"{', '.join(moved)} en el replay del fixture{pista}", detail)
            return ("alerta", f"rotura de fuente: con el mismo código y los mismos estados, la Rf y el precio ({mov}) "
                    f"no lo reproducen en el replay{pista}", detail)
    return "alerta", f"rotura de fuente: mismo código, mismo precio (±0.5%) y mismos estados{pista}", detail


def _s(v):
    return json.dumps(v, ensure_ascii=False, default=str) if not isinstance(v, str) else v


def compare(prev, cur, code_cmp=same_code, counterfactual=replay_counterfactual):
    """Resultado de la comparación: {'alertas': [...], 'avisos': [...], 'latencias': {...}, 'codigo': ...}."""
    code = code_change(prev["meta"], cur["meta"], code_cmp)
    alerts, notices = [], []
    for sym, cause in errors_of(cur):
        alerts.append({"tipo": "error", "ticker": sym, "causa": cause})
    changes = pr.compare_rows(prev["rows"], list(cur["rows"].values()))
    by_sym = {}
    for sym, key, a, b in changes:
        by_sym.setdefault(sym, []).append((key, a, b))
    for sym, items in sorted(by_sym.items()):
        if any(k == "ticker" for k, _, _ in items):
            notices.append({"tipo": "panel", "ticker": sym,
                            "causa": "entra en el panel" if items[0][2] == "presente" else "sale del panel"})
            continue
        r0, r1 = prev["rows"][sym], cur["rows"][sym]
        if str(r0.get("http")) != "200" or str(r1.get("http")) != "200":
            continue                                    # los errores ya se cuentan aparte
        sev, cause, detail = explain(sym, prev, cur, code, counterfactual)
        entry = {"tipo": "rotura de fuente" if sev == "alerta" else "cambio explicado", "ticker": sym,
                 "cambios": [{"campo": k, "antes": a, "ahora": b} for k, a, b in items], "causa": cause,
                 "detalle": detail}
        (alerts if sev == "alerta" else notices).append(entry)
    for sym in sorted(set(prev["analyses"]) & set(cur["analyses"])):
        lost = lost_fields(prev["analyses"][sym], cur["analyses"][sym])
        if lost:
            notices.append({"tipo": "sin dato", "ticker": sym, "causa": "pasan de dato a «sin dato»: " + ", ".join(lost)})
    lat0, lat1 = latencies(prev), latencies(cur)
    for ep, label in (("analysis", "/api/analysis"), ("pdf", "/api/pdf")):
        a, b = lat0[ep]["p95"], lat1[ep]["p95"]
        if a and b and b > a * (1 + LATENCY_WORSE):
            notices.append({"tipo": "latencia", "ticker": "—",
                            "causa": f"p95 de {label} {a} s → {b} s ({b / a - 1:+.0%})"})
    return {"anterior": prev["path"], "actual": cur["path"],
            "commit_anterior": prev["meta"].get("commit"), "commit_actual": cur["meta"].get("commit"),
            "origen_commit": [prev["meta"].get("commit_origen"), cur["meta"].get("commit_origen")],
            "fecha_anterior": prev["meta"].get("fecha"), "fecha_actual": cur["meta"].get("fecha"),
            "codigo": {"estado": code[0], "explicacion": code[1]},
            "alertas": alerts, "avisos": notices, "latencias": {"anterior": lat0, "actual": lat1}}


# ═══════════════════════════ salida ═══════════════════════════

def _cambios(e):
    return "; ".join(f"{c['campo']} {c['antes'] or '—'} → {c['ahora'] or '—'}" for c in e.get("cambios", []))


def render_md(res):
    al, av = res["alertas"], res["avisos"]
    rot = [a for a in al if a["tipo"] == "rotura de fuente"]
    err = [a for a in al if a["tipo"] == "error"]
    md = [f"# Vigilancia del panel · {(res['fecha_actual'] or '')[:10]}", ""]
    estado = "🔴 HAY ALERTAS" if al else "🟢 Sin alertas"
    md += [f"**{estado}:** {len(rot)} rotura(s) de fuente, {len(err)} error(es) · {len(av)} aviso(s).", ""]
    md += [f"- Corrida actual: `{res['actual']}` ({res['fecha_actual']}), commit "
           f"{res['commit_actual'] or 'desconocido'}" + (f" ({res['origen_commit'][1]})" if res['origen_commit'][1] else ""),
           f"- Corrida anterior: `{res['anterior']}` ({res['fecha_anterior']}), commit "
           f"{res['commit_anterior'] or 'desconocido'}" + (f" ({res['origen_commit'][0]})" if res['origen_commit'][0] else ""),
           f"- Código: **{res['codigo']['estado']}** — {res['codigo']['explicacion']}", ""]
    md += ["## Alertas", ""]
    if not al:
        md.append("Ninguna.")
    for title, items in (("Rotura de fuente", rot), ("Errores", err)):
        if items:
            md += [f"### {title}", ""]
            md += [f"- **{e['ticker']}**: " + (f"{_cambios(e)}. " if e.get("cambios") else "") + e["causa"]
                   for e in items]
            md.append("")
    md += ["", "## Avisos", ""]
    md += ([f"- **{e['ticker']}** ({e['tipo']}): " + (f"{_cambios(e)}. " if e.get("cambios") else "") + e["causa"]
            for e in av] or ["Ninguno."])
    lat = res["latencias"]
    md += ["", "## Latencias (s)", "", "| endpoint | | p50 | p95 | máx | n |", "|---|---|---|---|---|---|"]
    for ep, label in (("analysis", "/api/analysis"), ("pdf", "/api/pdf")):
        for when, name in (("anterior", "anterior"), ("actual", "actual")):
            v = lat[when][ep]
            md.append(f"| {label} | {name} | {v['p50']} | {v['p95']} | {v['max']} | {v['n']} |")
    md += ["", "La primera petición tras el despertar no se cuenta como fallo; `meta.json` guarda lo que tardó en "
           "despertar. Detalle de cada cambio en `comparacion.json`."]
    return "\n".join(md) + "\n"


def write_outputs(out, res):
    with open(os.path.join(out, "comparacion.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, ensure_ascii=False, default=str)
    with open(os.path.join(out, "alertas.md"), "w", encoding="utf-8") as fh:
        fh.write(render_md(res))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=ROOT, help="carpeta de las corridas semanales")
    ap.add_argument("--out", help="carpeta de esta corrida (por defecto <root>/<AAAA-MM-DD>)")
    ap.add_argument("--prev", help="corrida anterior (por defecto, la más reciente bajo --root)")
    ap.add_argument("--solo-comparar", metavar="DIR", help="no corre: compara DIR con --prev (sin red)")
    ap.add_argument("--base-url", default=BASE_URL)
    ap.add_argument("--concurrency", type=int, default=MAX_CONCURRENCY)
    ap.add_argument("--tickers", nargs="*")
    ap.add_argument("--commit-anterior", help="commit de producción de la corrida anterior, si no lo trae su meta.json")
    ap.add_argument("--commit-actual", help="ídem para la corrida actual")
    ap.add_argument("--salida", help="con --solo-comparar: dónde escribir alertas.md (por defecto, en DIR)")
    args = ap.parse_args(argv)
    logging.disable(logging.CRITICAL)
    root = os.path.abspath(os.path.expanduser(args.root))
    if args.solo_comparar:
        cur_dir = os.path.abspath(os.path.expanduser(args.solo_comparar))
    else:
        cur_dir = os.path.abspath(os.path.expanduser(args.out or os.path.join(root, _dt.date.today().isoformat())))
        if os.path.isfile(os.path.join(cur_dir, "resumen.csv")):
            ap.error(f"{cur_dir} ya tiene una corrida: usa --out o --solo-comparar")
        meta = run_live(cur_dir, args.base_url, args.tickers, args.concurrency)
        print(f"corrida en {cur_dir} · commit {meta['commit'] or 'desconocido'} · "
              f"despertar {meta['health']['despertar_s']} s")
    prev_dir = args.prev and os.path.abspath(os.path.expanduser(args.prev)) or latest_run(root, exclude=cur_dir)
    if not prev_dir:
        print("sin corrida anterior: esta es la semana 0 (no hay comparación)")
        return 0
    res = compare(load_run(prev_dir, args.commit_anterior), load_run(cur_dir, args.commit_actual))
    out = os.path.abspath(os.path.expanduser(args.salida)) if args.salida else cur_dir
    os.makedirs(out, exist_ok=True)
    write_outputs(out, res)
    print(f"{len(res['alertas'])} alertas, {len(res['avisos'])} avisos -> {os.path.join(out, 'alertas.md')}")
    return 1 if res["alertas"] else 0


if __name__ == "__main__":
    sys.exit(main())
