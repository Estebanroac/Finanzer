"""
Fase 6 (solo diagnóstico): dónde se va el tiempo de un análisis y del PDF, en replay y sin red.

    cd finanzer_next/backend
    ../.venv313/bin/python tests/perfil_local.py --out <DIR>

1. Perfilado (cProfile) de `fixture_backend.run_analysis` y de `build_pdf_bytes` para los 6 de `local` y 6 del panel
   de arquetipos distintos: tiempo de pared por ticker, CPU por módulo y las 15 funciones con más tiempo propio.
   Antes se hace una pasada de calentamiento (imports y cachés de módulo) que se informa aparte.
2. Llamadas externas por análisis en el panel (la ruta de producción: plan B + Finnhub), contadas al vuelo en el
   replay: peticiones HTTP a Yahoo por tipo, atributos de yfinance (cada uno es una descarga), Finnhub y tipos de
   cambio. La Rf (^TNX) no está en los fixtures (se congela la de config) y se suma aparte.
3. Opcional, con red (`--red-local T1 T2 …`): el análisis real desde este Mac con Render simulado (S1, S2) y SIN
   Finnhub (no hace falta la clave), en frío y en caliente, con el tiempo de get_ticker_info (estados + cotización)
   y de la Rf. Es una referencia de la red desde una IP residencial, no la de Render. Solo Yahoo: respetar la
   ventana de 15:55 a 16:45 de Nueva York igualmente.

No toca la red ni cambia ninguna salida de la app. Salida: perfil.md y perfil.json en --out.
"""
import argparse
import collections
import cProfile
import json
import logging
import os
import pstats
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fixture_backend as fb  # noqa: E402

LOCAL = [("local", t) for t in fb.TICKERS]                       # NFLX, JPM, O, FCX, SNOW, V
PANEL = [("panel", t) for t in ("AAPL", "BAC", "PLD", "NEE", "XOM", "RIVN")]  # MATURE, FIN., REIT, UTIL., CYCL., PRE


def module_of(filename):
    f = filename.replace("\\", "/")
    if "/backend/lib/" in f:
        return "lib/" + f.split("/backend/lib/")[1]
    if f.endswith("/backend/main.py"):
        return "main.py"
    if "/backend/tests/" in f:
        return "tests (replay de fixtures)"
    for pkg in ("reportlab", "pandas", "numpy", "yfinance", "pypdf", "PIL", "curl_cffi", "fastapi", "pydantic",
                "dateutil", "tomllib"):
        if f"/{pkg}/" in f:
            return pkg
    if f.startswith("~") or f.startswith("<"):
        return "builtins"
    return "stdlib/otros"


def _stats_rows(prof):
    st = pstats.Stats(prof)
    for (fn, line, name), (cc, nc, tt, ct, _callers) in st.stats.items():
        yield fn, line, name, nc, tt, ct


def profile_case(env, sym, store):
    """(tiempos, perfil del análisis, perfil del PDF) de un ticker en un replay ya abierto."""
    prof_a = cProfile.Profile()
    t0 = time.perf_counter()
    prof_a.enable()
    a = fb.run_analysis(sym, store)
    prof_a.disable()
    ta = time.perf_counter() - t0
    prof_p = cProfile.Profile()
    t0 = time.perf_counter()
    prof_p.enable()
    fb.build_pdf_bytes(a, fb.capture_date(store.meta[sym]))
    prof_p.disable()
    tp = time.perf_counter() - t0
    return {"analysis_s": ta, "pdf_s": tp, "archetype": (a.get("classification") or {}).get("archetype")}, prof_a, prof_p


def plain_times(env, sym, store, n=3):
    """Tiempo de pared sin el perfilador (cProfile infla las funciones pequeñas): mediana de n."""
    ts_a, ts_p = [], []
    for _ in range(n):
        t0 = time.perf_counter()
        a = fb.run_analysis(sym, store)
        ts_a.append(time.perf_counter() - t0)
        t0 = time.perf_counter()
        fb.build_pdf_bytes(a, fb.capture_date(store.meta[sym]))
        ts_p.append(time.perf_counter() - t0)
    return sorted(ts_a)[n // 2], sorted(ts_p)[n // 2]


def aggregate(profs):
    by_mod = collections.Counter()
    by_fn = collections.Counter()
    cum_fn = collections.Counter()
    calls = collections.Counter()
    total = 0.0
    for prof in profs:
        for fn, line, name, nc, tt, ct in _stats_rows(prof):
            mod = module_of(fn)
            key = f"{mod}:{line} {name}"
            by_mod[mod] += tt
            by_fn[key] += tt
            cum_fn[key] += ct
            calls[key] += nc
            total += tt
    return {
        "total_cpu_s": round(total, 3),
        "por_modulo": [(m, round(t, 3), round(100 * t / total, 1)) for m, t in by_mod.most_common()],
        "top_propio": [(k, round(t, 3), calls[k]) for k, t in by_fn.most_common(15)],
        "top_acumulado_lib": [(k, round(t, 3), calls[k]) for k, t in cum_fn.most_common(200)
                              if k.startswith(("lib/", "main.py"))][:15],
    }


def count_external_calls(tickers=None):
    """{sym: {tipo: n}} contando los accesos del motor a los fixtures del panel en replay."""
    out = {}
    with fb.replay(fb.fixtures_dir(fb.PANEL_ENV)) as store:
        counts = collections.Counter()
        orig = {n: getattr(store, n) for n in ("replay_http", "replay_yf", "replay_finnhub", "replay_fx")}

        def http(url, params):
            kind = ("quoteSummary" if "quoteSummary" in url else "timeseries (moneda)" if "timeseries" in url
                    else "search" if "/search" in url else "otro")
            counts[f"yahoo_http:{kind}"] += 1
            return orig["replay_http"](url, params)

        def yf(sym, attr):
            counts[f"yfinance:{attr}"] += 1
            return orig["replay_yf"](sym, attr)

        def fh(sym, path, params):
            counts[f"finnhub:{path}"] += 1
            return orig["replay_finnhub"](sym, path, params)

        def fx(fx_sym):
            counts["fx:history"] += 1
            return orig["replay_fx"](fx_sym)

        store.replay_http, store.replay_yf, store.replay_finnhub, store.replay_fx = http, yf, fh, fx
        from fastapi import HTTPException
        for sym in tickers or fb.env_tickers(fb.PANEL_ENV):
            counts.clear()
            try:
                fb.run_analysis(sym, store)
            except HTTPException:
                pass
            out[sym] = dict(counts)
    return out


def _path(url):
    u = str(url).split("?")[0]
    u = u.split("://", 1)[-1]
    host, _, rest = u.partition("/")
    return host.split(".")[0] + "/" + "/".join(rest.split("/")[:4])


def network_local(tickers):
    """{sym: tiempos} del análisis real (red de Yahoo) en frío y en caliente, sin Finnhub."""
    import cost_of_capital
    import main as app_main
    import yf_adapter
    os.environ.pop("FINNHUB_API_KEY", None)
    out = {}
    with fb.render_sim():
        p = fb._Patcher()
        acc = collections.Counter()

        def timed(mod, name):
            fn = getattr(mod, name)

            def w(*a, **kw):
                t0 = time.perf_counter()
                try:
                    return fn(*a, **kw)
                finally:
                    acc[name] += time.perf_counter() - t0
            p.set(mod, name, w)
        timed(yf_adapter, "get_ticker_info")
        timed(cost_of_capital, "_fetch_risk_free")
        # Cada petición HTTP de yfinance (YfData._make_request) y del adaptador (sesión curl_cffi): ruta y duración.
        import yfinance.data as yfd
        reqs = []
        t_origin = [0.0]
        real_make = yfd.YfData._make_request

        def make(self, url, *a, **kw):
            t0 = time.perf_counter()
            try:
                return real_make(self, url, *a, **kw)
            finally:
                reqs.append(("yfinance", _path(url), t0 - t_origin[0], time.perf_counter() - t0))
        p.set(yfd.YfData, "_make_request", make)
        real_ensure = yf_adapter._ensure_session

        def ensure():
            real_ensure()
            sess = yf_adapter._session
            if sess is not None and not getattr(sess, "_perfil", False):
                real_get = sess.get

                def get(url, *a, **kw):
                    t0 = time.perf_counter()
                    try:
                        return real_get(url, *a, **kw)
                    finally:
                        reqs.append(("adaptador", _path(url), t0 - t_origin[0], time.perf_counter() - t0))
                try:
                    sess.get = get
                    sess._perfil = True
                except Exception:
                    pass
        p.set(yf_adapter, "_ensure_session", ensure)
        try:
            for sym in tickers:
                fb.reset_state()
                r = {}
                for phase in ("frio", "caliente"):
                    acc.clear()
                    reqs.clear()
                    t0 = t_origin[0] = time.perf_counter()
                    c0 = time.process_time()
                    app_main._compute_analysis(sym)
                    r[phase] = {"total_s": round(time.perf_counter() - t0, 3),
                                "cpu_s": round(time.process_time() - c0, 3),
                                **{k: round(v, 3) for k, v in acc.items()},
                                "peticiones": [(o, u, round(st, 3), round(d, 3)) for o, u, st, d in reqs],
                                "n_peticiones": len(reqs), "suma_peticiones_s": round(sum(x[3] for x in reqs), 3)}
                out[sym] = r
        finally:
            p.undo()
    return out


def _md_table(rows, cols):
    return "\n".join(["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
                     + ["| " + " | ".join(str(c) for c in r) + " |" for r in rows])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True)
    ap.add_argument("--red-local", nargs="*", metavar="TICKER", help="mide también la red real desde este Mac")
    args = ap.parse_args(argv)
    logging.disable(logging.CRITICAL)
    out = os.path.abspath(os.path.expanduser(args.out))
    os.makedirs(out, exist_ok=True)

    # Calentamiento: primera ejecución del proceso (imports de main, reportlab, pandas; cachés de módulo).
    with fb.replay(fb.fixtures_dir("local")) as store:
        t0 = time.perf_counter()
        a = fb.run_analysis("NFLX", store)
        warm_a = time.perf_counter() - t0
        t0 = time.perf_counter()
        fb.build_pdf_bytes(a, fb.capture_date(store.meta["NFLX"]))
        warm_p = time.perf_counter() - t0

    cases, prof_a, prof_p = [], [], []
    for env, sym in LOCAL + PANEL:
        with fb.replay(fb.fixtures_dir(env)) as store:
            info, pa, pp = profile_case(env, sym, store)
            ta, tp = plain_times(env, sym, store)
        info.update(env=env, ticker=sym, analysis_sin_perfil_s=ta, pdf_sin_perfil_s=tp)
        cases.append(info)
        prof_a.append(pa)
        prof_p.append(pp)
    agg_a, agg_p = aggregate(prof_a), aggregate(prof_p)
    calls = count_external_calls()
    res = {"calentamiento": {"analysis_s": warm_a, "pdf_s": warm_p}, "casos": cases,
           "analisis": agg_a, "pdf": agg_p, "llamadas_externas": calls}
    with open(os.path.join(out, "perfil.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, ensure_ascii=False)

    md = ["# Perfil local (replay, sin red)", "",
          f"- Calentamiento (primera ejecución del proceso, NFLX): análisis {warm_a:.2f} s · PDF {warm_p:.2f} s", "",
          "## Tiempo de pared por ticker (mediana de 3, sin perfilador)", ""]
    md.append(_md_table([(c["env"], c["ticker"], c["archetype"], f"{c['analysis_sin_perfil_s']:.3f}",
                          f"{c['pdf_sin_perfil_s']:.3f}", f"{c['analysis_s']:.3f}", f"{c['pdf_s']:.3f}")
                         for c in cases],
                        ["juego", "ticker", "arquetipo", "análisis s", "PDF s", "análisis s (cProfile)",
                         "PDF s (cProfile)"]))
    for title, agg in (("Análisis", agg_a), ("PDF", agg_p)):
        md += ["", f"## {title}: CPU por módulo (tiempo propio, 12 tickers, con cProfile)", "",
               f"Total: {agg['total_cpu_s']} s", ""]
        md.append(_md_table(agg["por_modulo"][:12], ["módulo", "s", "%"]))
        md += ["", f"### {title}: 15 funciones con más tiempo propio", ""]
        md.append(_md_table(agg["top_propio"], ["función", "s", "llamadas"]))
        md += ["", f"### {title}: 15 funciones del motor con más tiempo acumulado", ""]
        md.append(_md_table(agg["top_acumulado_lib"], ["función", "s", "llamadas"]))
    kinds = sorted({k for c in calls.values() for k in c})
    md += ["", "## Llamadas externas por análisis (panel, ruta de producción)", ""]
    md.append(_md_table([(s, *[c.get(k, 0) for k in kinds]) for s, c in calls.items()], ["ticker", *kinds]))
    tot = collections.Counter()
    for c in calls.values():
        tot.update(c)
    n = len(calls)
    md += ["", "Media por ticker: " + ", ".join(f"{k} {tot[k] / n:.2f}" for k in kinds)
           + ". Más la Rf (^TNX, una descarga de yfinance cada 24 h por proceso), que el replay congela."]
    if args.red_local:
        import vigilancia as vg
        if vg.in_forbidden_window(vg.ny_now()):
            ap.error("ventana prohibida 15:55–16:45 de Nueva York")
        net = network_local([t.upper() for t in args.red_local])
        res["red_local"] = net
        with open(os.path.join(out, "perfil.json"), "w", encoding="utf-8") as fh:
            json.dump(res, fh, indent=1, ensure_ascii=False)
        md += ["", "## Red real desde este Mac (Render simulado, sin Finnhub)", ""]
        md.append(_md_table([(s, r["frio"]["total_s"], r["frio"]["cpu_s"], r["frio"].get("get_ticker_info", 0),
                              r["frio"].get("_fetch_risk_free", 0), r["caliente"]["total_s"])
                             for s, r in net.items()],
                            ["ticker", "frío total s", "frío CPU del proceso s", "get_ticker_info s", "Rf (^TNX) s",
                             "caliente total s"]))
        for sym, r in net.items():
            f = r["frio"]
            md += ["", f"### {sym} en frío: {f['n_peticiones']} peticiones HTTP, suma {f['suma_peticiones_s']} s "
                   f"en {f['total_s']} s de pared", "", "| origen | ruta | inicio s | duración s |", "|---|---|---|---|"]
            md += [f"| {o} | {u} | {st} | {d} |" for o, u, st, d in f["peticiones"]]
    with open(os.path.join(out, "perfil.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(md) + "\n")
    print(f"perfil -> {os.path.join(out, 'perfil.md')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
