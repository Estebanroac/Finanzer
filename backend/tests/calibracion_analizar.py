"""
Fase 7 (PLAN §4, punto 3): análisis del estudio de calibración (estudio, NO ajuste). Sin red.

    cd finanzer_next/backend
    ../.venv313/bin/python tests/calibracion_analizar.py --data ~/Downloads/finanzer_calibracion --out <informe.md>

HIPÓTESIS (fijadas ANTES de ver los resultados; commit anterior a la primera corrida):
  H1  "Calidad excelente anticipa persistencia de la rentabilidad": la proporción de casos cuyo ROE a 3 años (FY+3)
      sigue en al menos el 75% del de FY (con ROE de FY > 0) es MAYOR en "excelente" que en "media" + "débil".
  H2  "Calidad excelente anticipa menor caída": la caída máxima de la cotización (cierre ajustado) en los 3 años
      siguientes a D es MENOR (en mediana) en "excelente" que en "media" + "débil".
  H3  "Precio muy exigente anticipa peor rentabilidad relativa": la rentabilidad total frente al S&P 500 (SPY, cierre
      ajustado) a 1 y a 3 años es MENOR (en mediana) en "muy exigente" que en "atractivo" + "razonable".
  Descriptivo (no decide): la relación en los 4 niveles de cada escala y el precio sin contraer por la confianza.

REGLA DE DECISIÓN (fijada antes):
  · Muestras separadas: entrenamiento = ejercicios 2012–2016, prueba = 2017–2021 (por periodo); y, aparte, por
    empresa (mitades por el orden del ticker: posiciones pares e impares).
  · Diferencia = grupo de la hipótesis − grupo de contraste, con IC del 90% por bootstrap por empresa (2000
    remuestras; las observaciones de una empresa van juntas: no son independientes).
  · "Validada": la diferencia tiene el signo de la hipótesis en entrenamiento Y en prueba (en las dos particiones) y
    el IC del total excluye 0. "Contradicha": el IC del total excluye 0 con el signo contrario. Si no, "no
    concluyente".
  · NUNCA se cambian umbrales con esto (riesgo de sobreajuste): una regla contradicha se propone para retirar o
    revisar, y decide el usuario.
"""
import argparse
import glob
import json
import os
import random
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fixture_backend  # noqa: E402,F401
import history_fixtures as hf  # noqa: E402
import calibracion_generar as G  # noqa: E402

TRAIN, TEST = range(2012, 2017), range(2017, 2022)
B = 2000


def _adj(data, sym):
    obj = json.load(open(hf.series_file(sym, data)))
    return obj["dates"], [a if a is not None else c for a, c in zip(obj["adj_close"], obj["close"])]


def _at(dates, vals, day):
    """Primer valor en o después de `day` (índice) o None."""
    import bisect
    i = bisect.bisect_left(dates, day)
    return i if i < len(dates) else None


def outcomes(data, rows):
    import datetime as dt
    cache, spy = {}, _adj(data, "SPY")
    tick = json.load(open(os.path.join(data, "edgar", "company_tickers.json")))
    facts_cache = {}
    last_day = spy[0][-1]
    for r in rows:
        t, D = r["ticker"], r["D"]
        if t not in cache:
            cache[t] = _adj(data, t)
        dates, adj = cache[t]
        i0, j0 = _at(dates, adj, D), _at(*spy, D)
        for h, days in (("1a", 365), ("3a", 1095)):
            end = (dt.date.fromisoformat(D) + dt.timedelta(days=days)).isoformat()
            if end > last_day or i0 is None or j0 is None:
                r[f"rel_{h}"] = None
                continue
            i1, j1 = _at(dates, adj, end), _at(*spy, end)
            if i1 is None or j1 is None:
                r[f"rel_{h}"] = None
                continue
            r[f"ret_{h}"] = adj[i1] / adj[i0] - 1
            r[f"rel_{h}"] = r[f"ret_{h}"] - (spy[1][j1] / spy[1][j0] - 1)
        end3 = (dt.date.fromisoformat(D) + dt.timedelta(days=1095)).isoformat()
        if end3 <= last_day and i0 is not None:
            i1 = _at(dates, adj, end3)
            peak, mdd = adj[i0], 0.0
            for v in adj[i0:i1 + 1]:
                peak = max(peak, v)
                mdd = min(mdd, v / peak - 1)
            r["mdd_3a"] = mdd
        else:
            r["mdd_3a"] = None
        # ROE de FY y de FY+3 con los datos de hoy (resultado: aquí sí vale la información posterior)
        cik = (tick.get(t) or {}).get("cik")
        if cik not in facts_cache:
            facts_cache[cik] = json.load(open(os.path.join(data, "edgar", "companyfacts", f"CIK{int(cik):010d}.json")))
        f = facts_cache[cik]
        r["roe_fy"], r["roe_fy3"] = _roe(f, r["fy_end"], 0), _roe(f, r["fy_end"], 3)
    return rows


def _roe(facts, fy_end, k):
    import datetime as dt
    e = dt.date.fromisoformat(fy_end)
    e = e.replace(year=e.year + k)
    ni = G._row(facts, ("NetIncomeLoss",), e, "9999-12-31", True)
    eq1 = G._row(facts, ("StockholdersEquity",), e, "9999-12-31", False)
    eq0 = G._row(facts, ("StockholdersEquity",), e.replace(year=e.year - 1), "9999-12-31", False)
    if ni is None or not eq1:
        return None
    eq = (eq1 + eq0) / 2 if eq0 else eq1
    return ni / eq if eq > 0 else None


def _persist(r):
    a, b = r.get("roe_fy"), r.get("roe_fy3")
    if a is None or b is None or a <= 0:
        return None
    return 1.0 if b >= 0.75 * a else 0.0


HYP = [
    {"id": "H1", "label": "calidad excelente → ROE persistente a 3 años (proporción)", "scale": "quality_level",
     "group": {"excelente"}, "contrast": {"media", "débil"}, "metric": _persist, "stat": "mean", "sign": +1},
    {"id": "H2", "label": "calidad excelente → menor caída máxima a 3 años (mediana)", "scale": "quality_level",
     "group": {"excelente"}, "contrast": {"media", "débil"}, "metric": lambda r: r.get("mdd_3a"),
     "stat": "median", "sign": +1},   # caída menos negativa = mayor
    {"id": "H3a", "label": "precio muy exigente → peor rentabilidad frente al S&P 500 a 1 año (mediana)",
     "scale": "price_level", "group": {"muy exigente"}, "contrast": {"atractivo", "razonable"},
     "metric": lambda r: r.get("rel_1a"), "stat": "median", "sign": -1},
    {"id": "H3b", "label": "precio muy exigente → peor rentabilidad frente al S&P 500 a 3 años (mediana)",
     "scale": "price_level", "group": {"muy exigente"}, "contrast": {"atractivo", "razonable"},
     "metric": lambda r: r.get("rel_3a"), "stat": "median", "sign": -1},
]


def _stat(xs, how):
    if not xs:
        return None
    return statistics.mean(xs) if how == "mean" else statistics.median(xs)


def diff(rows, h):
    g = [h["metric"](r) for r in rows if r.get(h["scale"]) in h["group"]]
    c = [h["metric"](r) for r in rows if r.get(h["scale"]) in h["contrast"]]
    g, c = [x for x in g if x is not None], [x for x in c if x is not None]
    if len(g) < 5 or len(c) < 5:
        return None, len(g), len(c)
    return _stat(g, h["stat"]) - _stat(c, h["stat"]), len(g), len(c)


def boot(rows, h, seed=7):
    by = {}
    for r in rows:
        by.setdefault(r["ticker"], []).append(r)
    firms = sorted(by)
    rnd = random.Random(seed)
    out = []
    for _ in range(B):
        sample = [r for f in (rnd.choice(firms) for _ in firms) for r in by[f]]
        d, _, _ = diff(sample, h)
        if d is not None:
            out.append(d)
    out.sort()
    if len(out) < B * 0.9:
        return None
    return out[int(0.05 * len(out))], out[int(0.95 * len(out)) - 1]


def verdict(rows, h):
    firms = sorted({r["ticker"] for r in rows})
    halves = {"periodo": ([r for r in rows if r["fy"] in TRAIN], [r for r in rows if r["fy"] in TEST]),
              "empresa": ([r for r in rows if firms.index(r["ticker"]) % 2 == 0],
                          [r for r in rows if firms.index(r["ticker"]) % 2 == 1])}
    total, ng, nc = diff(rows, h)
    ci = boot(rows, h)
    parts = {k: (diff(a, h)[0], diff(b, h)[0]) for k, (a, b) in halves.items()}
    same = all(x is not None and x * h["sign"] > 0 for pair in parts.values() for x in pair)
    if ci and same and (ci[0] * h["sign"] > 0 and ci[1] * h["sign"] > 0):
        v = "validada"
    elif ci and ci[0] * h["sign"] < 0 and ci[1] * h["sign"] < 0:
        v = "contradicha"
    else:
        v = "no concluyente"
    return {"id": h["id"], "label": h["label"], "diff": total, "n_group": ng, "n_contrast": nc, "ci90": ci,
            "halves": parts, "verdict": v}


def by_level(rows, scale, labels, metric, how="median"):
    out = []
    for lv in labels:
        xs = [metric(r) for r in rows if r.get(scale) == lv]
        xs = [x for x in xs if x is not None]
        out.append((lv, len(xs), _stat(xs, how)))
    return out


def _pct(x):
    return "—" if x is None else f"{x * 100:+.1f}%"


def report(rows, failed):
    ql = ["excelente", "sólida", "media", "débil"]
    pl = ["atractivo", "razonable", "exigente", "muy exigente"]
    lines = [f"# Calibración histórica · resultados\n", f"{len(rows)} análisis point-in-time "
             f"({len({r['ticker'] for r in rows})} empresas, ejercicios 2012–2021); {failed} sin análisis.\n",
             "## Hipótesis\n", "| | Hipótesis | Diferencia | IC 90% | n (grupo / contraste) | Periodo (entren. / prueba) | "
             "Empresa (mitad A / B) | Veredicto |", "|---|---|---|---|---|---|---|---|"]
    res = [verdict(rows, h) for h in HYP]
    for v in res:
        ci = "—" if not v["ci90"] else f"{_pct(v['ci90'][0])} a {_pct(v['ci90'][1])}"
        hp = " / ".join(_pct(x) for x in v["halves"]["periodo"])
        he = " / ".join(_pct(x) for x in v["halves"]["empresa"])
        lines.append(f"| {v['id']} | {v['label']} | {_pct(v['diff'])} | {ci} | {v['n_group']} / {v['n_contrast']} | "
                     f"{hp} | {he} | **{v['verdict']}** |")
    lines += ["\n## Descriptivo por nivel\n", "| Escala | Nivel | n | ROE persistente | Caída máx. 3a (mediana) | "
              "Relativa 1a (mediana) | Relativa 3a (mediana) |", "|---|---|---|---|---|---|---|"]
    for scale, labels in (("quality_level", ql), ("price_level", pl), ("price_level_raw", pl)):
        for lv in labels:
            sub = [r for r in rows if r.get(scale) == lv]
            pers = [x for x in (_persist(r) for r in sub) if x is not None]
            mdd = [r["mdd_3a"] for r in sub if r.get("mdd_3a") is not None]
            r1 = [r["rel_1a"] for r in sub if r.get("rel_1a") is not None]
            r3 = [r["rel_3a"] for r in sub if r.get("rel_3a") is not None]
            lines.append(f"| {scale} | {lv} | {len(sub)} | {_pct(_stat(pers, 'mean'))} | {_pct(_stat(mdd, 'median'))} | "
                         f"{_pct(_stat(r1, 'median'))} | {_pct(_stat(r3, 'median'))} |")
    return "\n".join(lines) + "\n", res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    data = os.path.expanduser(a.data)
    rows, failed = [], 0
    for p in sorted(glob.glob(os.path.join(data, "resultados", "FY*.jsonl"))):
        for line in open(p):
            r = json.loads(line)
            if "error" in r or not r.get("quality_level"):
                failed += 1
                continue
            rows.append(r)
    rows = outcomes(data, rows)
    txt, res = report(rows, failed)
    with open(os.path.expanduser(a.out), "w") as fh:
        fh.write(txt)
    with open(os.path.join(data, "observaciones.json"), "w") as fh:
        json.dump(rows, fh, default=str)
    print(txt)


if __name__ == "__main__":
    main()
