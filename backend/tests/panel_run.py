"""
Fase 0 del plan de fiabilidad: corre el panel de referencia y produce un resumen comparable entre corridas.

    cd finanzer_next/backend
    ../.venv313/bin/python tests/panel_run.py --mode replay --out ~/Downloads/panel_replay
    ../.venv313/bin/python tests/panel_run.py --mode live --base-url https://finanzer.app --out ~/Downloads/panel_live
    ../.venv313/bin/python tests/panel_run.py --mode replay --out <nueva> --compare <anterior>

  --mode replay   desde los fixtures del panel (tests/fixtures/panel), sin red.
  --mode live     contra un servidor (finanzer.app o http://localhost:8000), con --concurrency peticiones a la
                  vez (por defecto 3; producción atiende en serie: no pasar de 4).
  --env           juego de fixtures del replay (panel por defecto; local/prod para pruebas).
  --tickers       subconjunto (por defecto, todos los del juego).
  --compare DIR   añade la sección "Cambios": tickers cuyo arquetipo, nivel de calidad, nivel de precio o
                  confianza cambiaron frente al resumen.csv de DIR.

Salida en --out: resumen.md y resumen.csv, y por ticker <T>.json (análisis), <T>.pdf, <T>.pdf.txt y
<T>.p<N>.png (una imagen por página, con pypdfium2).

En live, la sección "Live frente a replay" compara cada análisis de producción con el replay de su fixture y
separa las diferencias en tres grupos, repitiendo el replay con lo que el servidor usó:
  · solo Rf: desaparecen al usar la Rf del servidor (los fixtures congelan la de config);
  · solo precio intradía: desaparecen al usar además su precio (cotización y capitalización);
  · reales: el resto (datos nuevos, cambios de fuente o de código). Esto es lo que hay que mirar.
"""
import argparse
import concurrent.futures as cf
import copy
import csv
import datetime as _dt
import json
import logging
import os
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fixture_backend as fb  # noqa: E402

# Arquetipos esperados VALIDADOS por el usuario al cerrar la fase 0 (bitácora, registro #6): CAT, TSM y ASML
# CYCLICAL; BRK-B FINANCIAL (el P/B es su métrica; la volatilidad de sus ingresos sigue en la fase 3); NVDA a
# decidir en D4 (cíclica y de alto crecimiento a la vez). "?" = a decidir; "422" = el backend debe rechazarlo.
EXPECTED = {
    **{t: "MATURE" for t in ("AAPL", "MSFT", "KO", "PG", "JNJ", "V", "NVO", "NFLX", "AMZN", "UL")},
    **{t: "FINANCIAL" for t in ("JPM", "BAC", "PGR", "BRK-B", "BCS", "HSBC")},
    **{t: "REIT" for t in ("O", "PLD", "AMT")},
    **{t: "UTILITY" for t in ("NEE", "DUK")},
    **{t: "CYCLICAL" for t in ("XOM", "FCX", "CAT", "MU", "DOW", "TSM", "ASML", "SHEL", "TM")},
    **{t: "CRECIMIENTO_RENTABLE" for t in ("PLTR", "CRWD")},   # hoy no existe (D4): saldrá discrepancia
    **{t: "GROWTH_PRE_PROFIT" for t in ("RIVN", "SNOW")},
    "NVDA": "?", "SPY": "422",
    # Fase 2b (D7): el que asigna hoy el motor, a revisar en la fase 3 (decisión del usuario, 2026-10-16).
    "MC.PA": "MATURE",
}
DOUBTFUL = {}

COLUMNS = [
    "ticker", "grupo", "http", "arquetipo", "regla", "arquetipo_esperado", "coincide",
    "calidad", "calidad_nivel", "precio_sin_ajustar", "precio_ajustado", "precio_nivel",
    "confianza", "confianza_motivos", "metodos_evaluables", "dcf_estado", "dcf_fiabilidad", "dcf_upside_pct",
    "ruta_datos", "finnhub_campos", "validaciones", "errores", "tiempo_s", "tiempo_pdf_s", "paginas_pdf",
]
CHANGE_KEYS = ("arquetipo", "calidad_nivel", "precio_nivel", "confianza")
# Campos que no se comparan en live frente a replay: la serie de precios (gráfica, depende del día), la
# propia Rf (se informa aparte) y el detalle textual de procedencia.
_LIVE_SKIP = ("price_history", "risk_free", "data_provenance.fields")


def group_of(sym):
    return next((g for g, ts in fb.PANEL_GROUPS.items() if sym in ts), "—")


def _g(d, *path, default=None):
    for k in path:
        if not isinstance(d, dict):
            return default
        d = d.get(k)
    return default if d is None else d


def _match(sym, archetype, http):
    exp = EXPECTED.get(sym)
    if exp is None:
        return "—"
    if exp == "422":
        return "sí" if http == 422 else "no"
    if exp == "?":
        return "a decidir"
    if sym in DOUBTFUL and archetype == exp:
        return "dudoso"
    return "sí" if archetype == exp else "no"


def summarize(sym, analysis, pages=None, elapsed=None, elapsed_pdf=None):
    """Fila del resumen a partir del análisis (o de su rechazo HTTP)."""
    http = analysis.get("__http_error__") or 200
    row = dict.fromkeys(COLUMNS, "")
    row.update(ticker=sym, grupo=group_of(sym), http=http, arquetipo_esperado=EXPECTED.get(sym, "—"),
               tiempo_s="" if elapsed is None else round(elapsed, 2),
               tiempo_pdf_s="" if elapsed_pdf is None else round(elapsed_pdf, 2),
               paginas_pdf="" if pages is None else pages)
    if http != 200:
        row.update(errores=str(analysis.get("detail", ""))[:160], coincide=_match(sym, None, http))
        return row
    cls = analysis.get("classification") or {}
    q = analysis.get("quality") or {}
    p = analysis.get("price_attractiveness") or {}
    conf = analysis.get("confidence") or {}
    methods = _g(conf, "dimensions", "convergence", "methods", default=[])
    dcf = analysis.get("dcf") or {}
    prov = analysis.get("data_provenance") or {}
    upside = dcf.get("upside")
    errors = list(analysis.get("errors") or []) + list(prov.get("errors") or [])
    row.update(
        arquetipo=cls.get("archetype", ""), regla=cls.get("rule", ""),
        coincide=_match(sym, cls.get("archetype"), http),
        calidad=q.get("score", ""), calidad_nivel=q.get("level", ""),
        precio_sin_ajustar=p.get("score_raw", ""), precio_ajustado=p.get("score", ""), precio_nivel=p.get("level", ""),
        confianza=conf.get("level", ""), confianza_motivos=" | ".join(conf.get("reasons") or []),
        metodos_evaluables=sum(1 for m in methods if m.get("evaluable")),
        dcf_estado=_g(analysis, "dcf_status", "state", default=""),
        dcf_fiabilidad=_g(dcf, "reliability", "level", default=""),
        dcf_upside_pct="" if upside is None else round(upside, 1),
        ruta_datos=prov.get("path", ""),
        finnhub_campos=sum(1 for f in (prov.get("fields") or {}).values() if f.get("source") == "finnhub"),
        validaciones=len(analysis.get("data_validation") or []),
        errores=" | ".join(str(e) for e in errors)[:300],
    )
    return row


# ═══════════════════════════ ejecución ═══════════════════════════

def run_replay(tickers, env=fb.PANEL_ENV):
    """{sym: {"analysis", "pdf", "elapsed": None}} desde los fixtures, sin red."""
    out = fb.compute_outputs(tickers, fb.fixtures_dir(env))
    return {s: {"analysis": a, "pdf": pdf, "elapsed": None, "elapsed_pdf": None} for s, (a, pdf) in out.items()}


def _get(url, timeout):
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "finanzer-panel-run"}),
                                    timeout=timeout) as r:
            return r.status, r.read(), time.monotonic() - t0
    except urllib.error.HTTPError as e:
        return e.code, e.read(), time.monotonic() - t0


def _fetch_live(base_url, sym, timeout):
    status, body, el = _get(f"{base_url}/api/analysis/{sym}", timeout)
    try:
        data = json.loads(body)
    except Exception:
        data = {"detail": body[:200].decode("utf-8", "replace")}
    if status != 200:
        return sym, {"analysis": {"__http_error__": status, "detail": data.get("detail", data)}, "pdf": None,
                     "elapsed": el, "elapsed_pdf": None}
    pstatus, pdf, el_pdf = _get(f"{base_url}/api/pdf/{sym}", timeout)
    return sym, {"analysis": data, "pdf": pdf if pstatus == 200 else None, "elapsed": el, "elapsed_pdf": el_pdf}


def run_live(tickers, base_url, concurrency=3, timeout=180):
    base_url = base_url.rstrip("/")
    with cf.ThreadPoolExecutor(max_workers=concurrency) as ex:
        return dict(ex.map(lambda s: _fetch_live(base_url, s, timeout), tickers))


# ═══════════════════════════ live frente a replay ═══════════════════════════

def _flat(o, p=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from _flat(v, f"{p}.{k}" if p else k)
    elif isinstance(o, list) and any(isinstance(x, (dict, list)) for x in o):
        for i, v in enumerate(o):
            yield from _flat(v, f"{p}[{i}]")
    else:
        yield p, o


def diff_fields(a, b, rel=1e-6):
    """{campo: (a, b)} de lo que difiere (números con tolerancia relativa `rel`)."""
    fa = {k: v for k, v in _flat(a) if not k.startswith(_LIVE_SKIP)}
    fb_ = {k: v for k, v in _flat(b) if not k.startswith(_LIVE_SKIP)}
    out = {}
    for k in set(fa) | set(fb_):
        x, y = fa.get(k), fb_.get(k)
        if (isinstance(x, (int, float)) and isinstance(y, (int, float)) and not isinstance(x, bool)
                and not isinstance(y, bool) and abs(x - y) <= 1e-12 + rel * max(abs(x), abs(y))):
            continue
        if x != y:
            out[k] = (x, y)
    return out


def _set_price(store, sym, price):
    """Cambia la cotización grabada (y la capitalización en proporción) en las dos rutas: fast_info (plan B,
    la de producción) y quoteSummary (price / financialData / summaryDetail, la de local)."""
    fi = store.yf.get(sym, {}).get("fast_info")
    if fi and fi.get("lastPrice"):
        k = price / fi["lastPrice"]
        fi["lastPrice"] = price
        if fi.get("marketCap"):
            fi["marketCap"] *= k
    for e in store.http.get(sym, []):
        res = (((e.get("body_json") or {}).get("quoteSummary") or {}).get("result") or [None])[0]
        if e.get("status") != 200 or not isinstance(res, dict):
            continue
        cur = _g(res, "price", "regularMarketPrice", "raw") or _g(res, "financialData", "currentPrice", "raw")
        if not cur:
            continue
        k = price / cur
        for mod, key in (("price", "regularMarketPrice"), ("financialData", "currentPrice"),
                         ("price", "marketCap"), ("summaryDetail", "marketCap")):
            v = (res.get(mod) or {}).get(key)
            if isinstance(v, dict) and isinstance(v.get("raw"), (int, float)):
                v["raw"] = price if key != "marketCap" else v["raw"] * k


def _replay_with(sym, env, rf=None, price=None):
    """Replay de `sym` con la Rf y/o el precio que usó el servidor."""
    import cost_of_capital
    with fb.replay(fb.fixtures_dir(env)) as store:
        store.load(sym)
        if rf is not None:
            cost_of_capital._fetch_risk_free = lambda: {"value": rf["value"], "as_of": rf.get("as_of")}
        if price is not None:
            _set_price(store, sym, price)
        a = fb.run_analysis(sym, store)
    return json.loads(json.dumps(a, default=str))


def classify_live_diffs(sym, live, env=fb.PANEL_ENV):
    """Separa las diferencias live/replay en solo Rf, solo precio intradía y reales."""
    norm = lambda x: json.loads(json.dumps(x, default=str))  # noqa: E731
    live = norm(live)
    base = _replay_with(sym, env)
    rf = live.get("risk_free") or None
    with_rf = _replay_with(sym, env, rf=rf) if rf else base
    with_rf_px = _replay_with(sym, env, rf=rf, price=live.get("price"))
    d0, d1, d2 = diff_fields(base, live), diff_fields(with_rf, live), diff_fields(with_rf_px, live)
    return {
        "rf_replay": _g(base, "risk_free", "value"), "rf_live": _g(live, "risk_free", "value"),
        "rf_live_source": _g(live, "risk_free", "source"),
        "price_replay": base.get("price"), "price_live": live.get("price"),
        "solo_rf": {k: d0[k] for k in sorted(set(d0) - set(d1))},
        "solo_precio": {k: d1[k] for k in sorted(set(d1) - set(d2))},
        "reales": {k: d2[k] for k in sorted(d2)},
    }


# ═══════════════════════════ salida ═══════════════════════════

def write_ticker_files(out, sym, res):
    with open(os.path.join(out, f"{sym}.json"), "w", encoding="utf-8") as fh:
        fh.write(fb.stable_json(res["analysis"]))
    pdf = res.get("pdf")
    if not pdf:
        return None
    with open(os.path.join(out, f"{sym}.pdf"), "wb") as fh:
        fh.write(pdf)
    with open(os.path.join(out, f"{sym}.pdf.txt"), "w", encoding="utf-8") as fh:
        fh.write(fb.pdf_text(pdf))
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(pdf)
    try:
        for i in range(len(doc)):
            doc[i].render(scale=1.5).to_pil().save(os.path.join(out, f"{sym}.p{i + 1}.png"))
        return len(doc)
    finally:
        doc.close()


def read_summary(path):
    with open(os.path.join(path, "resumen.csv"), encoding="utf-8") as fh:
        return {r["ticker"]: r for r in csv.DictReader(fh)}


def compare_rows(prev, rows):
    """[(ticker, campo, antes, ahora)] de los cambios en CHANGE_KEYS (y tickers que entran o salen)."""
    cur = {r["ticker"]: r for r in rows}
    changes = []
    for sym in sorted(set(prev) | set(cur)):
        if sym not in prev or sym not in cur:
            changes.append((sym, "ticker", "presente" if sym in prev else "—", "presente" if sym in cur else "—"))
            continue
        for k in CHANGE_KEYS:
            a, b = str(prev[sym].get(k, "")), str(cur[sym].get(k, ""))
            if a != b:
                changes.append((sym, k, a, b))
    return changes


def _md_table(rows, cols):
    esc = lambda v: str(v).replace("|", "\\|").replace("\n", " ")  # noqa: E731
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    lines += ["| " + " | ".join(esc(r.get(c, "")) for c in cols) + " |" for r in rows]
    return "\n".join(lines)


def _short(v, n=60):
    s = json.dumps(v, ensure_ascii=False, default=str) if not isinstance(v, str) else v
    return s if len(s) <= n else s[:n - 1] + "…"


def write_summary(out, rows, header, changes=None, live_diffs=None, max_fields=25):
    with open(os.path.join(out, "resumen.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)
    md = [f"# Corrida del panel · {header['mode']}", ""]
    md += [f"- {k}: {v}" for k, v in header.items()]
    md += ["", "## Veredicto", "", _md_table(rows, ["ticker", "grupo", "http", "arquetipo", "regla",
                                                     "arquetipo_esperado", "coincide", "calidad", "calidad_nivel",
                                                     "precio_sin_ajustar", "precio_ajustado", "precio_nivel",
                                                     "confianza", "metodos_evaluables"])]
    md += ["", "## Datos, DCF y tiempos", "", _md_table(rows, ["ticker", "ruta_datos", "finnhub_campos",
                                                               "validaciones", "dcf_estado", "dcf_fiabilidad",
                                                               "dcf_upside_pct", "errores", "tiempo_s",
                                                               "tiempo_pdf_s", "paginas_pdf"])]
    md += ["", "## Motivos de la confianza", ""]
    md += [f"- **{r['ticker']}** ({r['confianza']}): {r['confianza_motivos'] or '—'}" for r in rows if r["confianza"]]
    if changes is not None:
        md += ["", f"## Cambios frente a {header.get('compare', 'la corrida anterior')}", ""]
        md += ([_md_table([dict(zip(("ticker", "campo", "antes", "ahora"), c)) for c in changes],
                          ["ticker", "campo", "antes", "ahora"])] if changes else ["Sin cambios."])
    if live_diffs is not None:
        md += ["", "## Live frente a replay", "",
               "Cada análisis del servidor frente al replay de su fixture. Las dos primeras columnas se explican "
               "solas (los fixtures congelan la Rf de config y el precio de la captura); **las reales son las que "
               "hay que revisar**.", ""]
        md += [_md_table([{"ticker": s, "solo Rf": len(d["solo_rf"]), "solo precio intradía": len(d["solo_precio"]),
                           "reales": len(d["reales"]),
                           "Rf replay → live": f"{d['rf_replay']} → {d['rf_live']} ({d['rf_live_source']})",
                           "precio replay → live": f"{d['price_replay']} → {d['price_live']}"}
                          for s, d in live_diffs.items()],
                         ["ticker", "solo Rf", "solo precio intradía", "reales", "Rf replay → live",
                          "precio replay → live"])]
        for title, key in (("Solo Rf", "solo_rf"), ("Solo precio intradía", "solo_precio"),
                           ("Diferencias reales", "reales")):
            md += ["", f"### {title}", ""]
            any_ = False
            for s, d in live_diffs.items():
                if d[key]:
                    any_ = True
                    md.append(f"- **{s}** ({len(d[key])} campos)")
                    md += [f"  - `{k}`: {_short(a)} → {_short(b)}" for k, (a, b) in list(d[key].items())[:max_fields]]
                    if len(d[key]) > max_fields:
                        md.append(f"  - … {len(d[key]) - max_fields} más (detalle en live_vs_replay.json)")
            if not any_:
                md.append("Ninguna.")
        with open(os.path.join(out, "live_vs_replay.json"), "w", encoding="utf-8") as fh:
            json.dump(live_diffs, fh, indent=1, ensure_ascii=False, default=str)
    with open(os.path.join(out, "resumen.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(md) + "\n")


def run(mode, out, tickers=None, env=fb.PANEL_ENV, base_url=None, concurrency=3, compare=None,
        live_vs_replay=True):
    tickers = [t.upper() for t in (tickers or fb.env_tickers(env))]
    os.makedirs(out, exist_ok=True)
    t0 = time.monotonic()
    results = run_replay(tickers, env) if mode == "replay" else run_live(tickers, base_url, concurrency)
    rows = []
    for sym in tickers:
        res = results[sym]
        pages = write_ticker_files(out, sym, res)
        rows.append(summarize(sym, res["analysis"], pages, res["elapsed"], res["elapsed_pdf"]))
    header = {"mode": mode, "fecha": _dt.datetime.now().astimezone().isoformat(timespec="seconds"),
              "commit": fb.git_commit(), "juego": env, "tickers": len(tickers),
              "duración_s": round(time.monotonic() - t0, 1)}
    if mode == "live":
        header.update(base_url=base_url, concurrencia=concurrency)
    changes = None
    if compare:
        header["compare"] = compare
        changes = compare_rows(read_summary(compare), rows)
    live_diffs = None
    if mode == "live" and live_vs_replay:
        live_diffs = {s: classify_live_diffs(s, results[s]["analysis"], env) for s in tickers
                      if not results[s]["analysis"].get("__http_error__")
                      and os.path.isdir(os.path.join(fb.fixtures_dir(env), s))}
    write_summary(out, rows, header, changes, live_diffs)
    return rows, changes, live_diffs


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mode", choices=("replay", "live"), required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--base-url", default="https://finanzer.app")
    ap.add_argument("--concurrency", type=int, default=3)
    ap.add_argument("--env", default=fb.PANEL_ENV, choices=fb.ENVS + (fb.PANEL_ENV,))
    ap.add_argument("--tickers", nargs="*")
    ap.add_argument("--compare")
    args = ap.parse_args(argv)
    if args.concurrency > 4 and "finanzer.app" in args.base_url:
        ap.error("producción atiende en serie: como mucho 4 peticiones concurrentes")
    logging.disable(logging.CRITICAL)
    rows, changes, _ = run(args.mode, os.path.abspath(os.path.expanduser(args.out)), args.tickers, args.env,
                           args.base_url, args.concurrency, args.compare)
    print(f"{len(rows)} tickers -> {os.path.join(args.out, 'resumen.md')}"
          + (f" · {len(changes)} cambios" if changes is not None else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
