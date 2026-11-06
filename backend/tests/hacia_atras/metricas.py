"""
Prueba hacia atrás · métricas (a)–(e) del pre-registro (docs/fiabilidad/PRUEBA_HACIA_ATRAS_2025_PREREGISTRO.md §4–§7).

    python -I tests/hacia_atras/metricas.py --base <carpeta de evidencias>

Lee <base>/corridas/{A,B,A14}/<T>.json.gz (análisis al corte), <base>/datos_reales/resultados_reales.csv y
al_corte.csv, y tests/hacia_atras/universo_2025-11-05.tsv. Escribe <base>/empresas_410.csv, <base>/metricas.csv y
<base>/metricas.json. No cambia ninguna definición del pre-registro; lo que falta se cuenta como «sin dato».
"""
import argparse
import csv
import gzip
import json
import math
import os
import random
import re
import statistics as st

HERE = os.path.dirname(os.path.abspath(__file__))
VERSIONS = tuple(os.environ.get("VERSIONES", "A,B,A14").split(","))
BARATA = {"atractivo", "muy atractivo"}
CARA = {"exigente", "muy exigente"}
ALIAS = {"BK": "BNY", "FI": "FISV", "MMC": "MRSH", "PSKY": "SKYD", "EQR": "VMRK"}
SEED = 20251105


def fnum(x):
    try:
        v = float(x)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def grupo_precio(label):
    if label in BARATA:
        return "barata"
    if label in CARA:
        return "cara"
    if label == "razonable":
        return "razonable"
    return "sin veredicto"


def g(d, *path):
    for k in path:
        if not isinstance(d, dict):
            return None
        d = d.get(k)
    return d


def load_analysis(base, version, sym):
    p = os.path.join(base, "corridas", version, f"{sym}.json.gz")
    if not os.path.isfile(p):
        return None
    a = json.load(gzip.open(p))
    return None if "__http_error__" in a else a


def _reading(a, key):
    for r in g(a, "market_context", "readings") or []:
        if r.get("key") == key:
            return fnum(r.get("num"))
    return None


def _pct_in(text):
    """«(15.4% frente al 26.7% de hoy)» → 0.154 (el umbral de la condición)."""
    m = re.search(r"\((−?-?[\d.,]+)%\s+frente", text or "")
    return float(m.group(1).replace("−", "-").replace(",", ".")) / 100 if m else None


def engine_row(a):
    if a is None:
        keys = engine_row({}).keys()
        return {**{k: None for k in keys}, "precio": "sin análisis", "grupo": "sin veredicto", "alertas_rojas": None}
    v = a.get("verdict") or {}
    beh = [b.get("kind") for b in g(a, "market_context", "behavioral") or []]
    pm = g(a, "premortem", "items") or []
    return {
        "veredicto": v.get("text"),
        "precio": v.get("price_level") or "sin veredicto",
        "grupo": grupo_precio(v.get("price_level")),
        "puntuacion": fnum(g(a, "price_attractiveness", "score")),
        "puntuacion_cruda": fnum(g(a, "price_attractiveness", "score_raw")),
        "confianza": v.get("confidence"),
        "alertas_rojas": len(g(a, "alerts", "red_flags") or []),
        "alertas_motivos": " | ".join(f.get("reason", "") for f in g(a, "alerts", "red_flags") or []),
        "arquetipo": g(a, "classification", "archetype"),
        "g_dcf": fnum(g(a, "dcf", "growth_rate")),
        "fcf_dcf_anual": fnum(g(a, "dcf", "fcf_input")),
        "conductual": ",".join(k for k in beh if k),
        "momentum": _reading(a, "momentum"),
        "fuerza_relativa": _reading(a, "relative_strength"),
        "premortem_margen": next((_pct_in(i.get("text")) for i in pm if i.get("kind") == "margen"), None),
        "premortem_deuda": next((i.get("text") for i in pm if i.get("kind") == "deuda"), None),
        "premortem_tipos": ",".join(sorted({i.get("kind") for i in pm if i.get("kind")})),
    }


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def median(xs):
    xs = [x for x in xs if x is not None]
    return st.median(xs) if xs else None


def spearman(xs, ys):
    pairs = [(x, y) for x, y in zip(xs, ys) if x is not None and y is not None]
    if len(pairs) < 5:
        return None, len(pairs)

    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(v):
            j = i
            while j + 1 < len(v) and v[order[j + 1]] == v[order[i]]:
                j += 1
            for k in range(i, j + 1):
                r[order[k]] = (i + j) / 2 + 1
            i = j + 1
        return r
    rx, ry = ranks([p[0] for p in pairs]), ranks([p[1] for p in pairs])
    mx, my = mean(rx), mean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return (num / den if den else None), len(pairs)


def spread(rows, lab, ret):
    b = [r[ret] for r in rows if r.get(lab) == "barata" and r.get(ret) is not None]
    c = [r[ret] for r in rows if r.get(lab) == "cara" and r.get(ret) is not None]
    mb, mc = mean(b), mean(c)
    d = mb - mc if mb is not None and mc is not None else None
    ci = None
    if len(b) >= 3 and len(c) >= 3:
        rnd = random.Random(SEED)
        ds = sorted(mean([rnd.choice(b) for _ in b]) - mean([rnd.choice(c) for _ in c]) for _ in range(2000))
        ci = (ds[49], ds[1949])
    return {"n_barata": len(b), "n_cara": len(c), "media_barata": mb, "media_cara": mc, "D": d, "ic95": ci}


def _months(a, b):
    import datetime as dt
    try:
        d0, d1 = dt.date.fromisoformat(str(a)[:10]), dt.date.fromisoformat(str(b)[:10])
    except ValueError:
        return None
    return ((d1 - d0).days + 1) / 30.4375


def real_periods(rr):
    """Los periodos reales siguientes (§6): 2 trimestres; un emisor semestral o anual, su primer periodo (marcado)."""
    trimestral = str(rr.get("tipo_periodo", "")).startswith("trim")
    ps = ["p1", "p2"] if trimestral else ["p1"]
    out = {"periodos_reales": rr.get("tipo_periodo") or "sin dato", "ventas_yoy_2t": None, "fcf_sbc_2t": None,
           "meses_reales": None, "margen_op_2t": None, "deuda_2t": None}
    v = [fnum(rr.get(f"{p}_ventas")) for p in ps]
    v0 = [fnum(rr.get(f"{p}_ventas_hace1a")) for p in ps]
    if all(x is not None for x in v + v0) and sum(v0) > 0:
        out["ventas_yoy_2t"] = sum(v) / sum(v0) - 1
    f = [fnum(rr.get(f"{p}_fcf_menos_sbc")) for p in ps]
    m = [_months(rr.get(f"{p}_inicio"), rr.get(f"{p}_fin")) for p in ps]
    if all(x is not None for x in f + m):
        out["fcf_sbc_2t"], out["meses_reales"] = sum(f), sum(m)
    mg = [fnum(rr.get(f"{p}_margen_operativo")) for p in ps]
    if all(x is not None for x in mg):
        out["margen_op_2t"] = mean(mg)
    out["deuda_2t"] = fnum(rr.get(f"{ps[-1]}_deuda"))
    out["deuda_corte"] = fnum(rr.get("deuda_corte"))
    return out


def load_csv(path, key):
    with open(path, encoding="utf-8") as fh:
        return {r[key]: r for r in csv.DictReader(fh)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    a = ap.parse_args()
    base = a.base
    with open(os.path.join(HERE, "universo_2025-11-05.tsv"), encoding="utf-8") as fh:
        uni = [r for r in csv.DictReader(fh, delimiter="\t") if r["grupo"] in ("110", "control")]
    real = load_csv(os.path.join(base, "datos_reales", "resultados_reales.csv"), "simbolo_2025")
    corte = load_csv(os.path.join(base, "datos_reales", "al_corte.csv"), "simbolo_2025")

    rows = []
    for u in uni:
        s25 = u["symbol"]
        sym = ALIAS.get(s25, s25)
        rr, cc = real.get(s25, {}), corte.get(s25, {})
        row = {"simbolo": s25, "simbolo_datos": sym, "muestra": u["grupo"], "sector": u["gics_sector"],
               "L1": (cc.get("etiqueta_L1") or "").strip() or "sin etiqueta",
               "L2": (cc.get("etiqueta_L2") or "").strip() or "sin etiqueta",
               "pe_relativo": fnum(cc.get("pe_relativo")), "fcf_yield": fnum(cc.get("fcf_yield"))}
        # datos_reales/LEEME.md: tr y rel en % / pp; mdd = caída pico-valle en % POSITIVO → fracciones, caída negativa
        for k in ("rel_6m", "rel_12m", "tr_6m", "tr_12m"):
            x = fnum(rr.get(k))
            row[k] = x / 100 if x is not None else None
        for k in ("mdd_6m", "mdd_12m"):
            x = fnum(rr.get(k))
            row[k] = -abs(x) / 100 if x is not None else None
        rd = str(rr.get("recorte_dividendo", "")).strip().lower()
        row["recorte_dividendo"] = rd in ("1", "true", "si", "sí")
        row["recorte_dividendo_dudoso"] = row["recorte_dividendo"] and str(rr.get("dividendo_revisar", "")).strip() \
            .lower() not in ("", "0", "false", "no")
        row["deslistada"] = rr.get("deslistada", "")
        row.update(real_periods(rr))
        for v in VERSIONS:
            for k, val in engine_row(load_analysis(base, v, sym)).items():
                row[f"{k}_{v}"] = val
        rows.append(row)

    out = {"pre_registro": "docs/fiabilidad/PRUEBA_HACIA_ATRAS_2025_PREREGISTRO.md (c65d36cd)"}
    flat = []
    for muestra in ("control", "110"):
        R = [r for r in rows if r["muestra"] == muestra]
        M = out[muestra] = {"n": len(R), "con_rel_12m": sum(r["rel_12m"] is not None for r in R)}
        # (a) precio
        Ma = M["a"] = {}
        for meth in VERSIONS + ("L1", "L2"):
            lab = f"grupo_{meth}" if meth in VERSIONS else meth
            Ma[meth] = {h: spread(R, lab, f"rel_{h}") for h in ("12m", "6m")}
            if meth in VERSIONS:
                Ma[meth]["spearman_12m"] = spearman([r[f"puntuacion_{meth}"] for r in R], [r["rel_12m"] for r in R])
                Ma[meth]["spearman_6m"] = spearman([r[f"puntuacion_{meth}"] for r in R], [r["rel_6m"] for r in R])
                Ma[meth]["spearman_cruda_12m"] = spearman([r[f"puntuacion_cruda_{meth}"] for r in R],
                                                          [r["rel_12m"] for r in R])
                Ma[meth]["reparto"] = {k: sum(r[f"grupo_{meth}"] == k for r in R)
                                       for k in ("barata", "razonable", "cara", "sin veredicto")}
            else:
                cont = [-(r["pe_relativo"]) if r["pe_relativo"] is not None else None for r in R] \
                    if meth == "L1" else [r["fcf_yield"] for r in R]
                Ma[meth]["spearman_12m"] = spearman(cont, [r["rel_12m"] for r in R])
                Ma[meth]["reparto"] = {k: sum(r[meth] == k for r in R)
                                       for k in ("barata", "media", "cara", "sin etiqueta")}
        for v in VERSIONS:
            dA, d1, d2 = Ma[v]["12m"]["D"], Ma["L1"]["12m"]["D"], Ma["L2"]["12m"]["D"]
            Ma[v]["exito"] = (None if None in (dA, d1, d2)
                              else bool(dA >= 0.05 and dA > d1 and dA > d2))
        # (b) confianza
        Mb = M["b"] = {}
        for v in VERSIONS:
            lv = {}
            for c in ("alta", "media", "baja"):
                hits = [(r[f"grupo_{v}"] == "barata" and r["rel_12m"] > 0) or
                        (r[f"grupo_{v}"] == "cara" and r["rel_12m"] < 0)
                        for r in R if r.get(f"confianza_{v}") == c and r[f"grupo_{v}"] in ("barata", "cara")
                        and r["rel_12m"] is not None]
                lv[c] = {"n": len(hits), "acierto": (sum(hits) / len(hits)) if hits else None}
            t = [lv[c]["acierto"] for c in ("alta", "media", "baja")]
            lv["exito"] = None if None in t else bool(t[0] > t[1] > t[2])
            Mb[v] = lv
        # (c) alertas rojas
        Mc = M["c"] = {}
        for v in VERSIONS:
            def hit(r):
                vals = [r["mdd_6m"], r["mdd_12m"]]
                if all(x is None for x in vals) and not r["recorte_dividendo"]:
                    return None
                return any(x is not None and x <= -0.25 for x in vals) or r["recorte_dividendo"]
            con = [hit(r) for r in R if (r.get(f"alertas_rojas_{v}") or 0) > 0]
            sin = [hit(r) for r in R if r.get(f"alertas_rojas_{v}") == 0]
            con, sin = [x for x in con if x is not None], [x for x in sin if x is not None]
            fc = sum(con) / len(con) if con else None
            fs = sum(sin) / len(sin) if sin else None
            Mc[v] = {"n_con": len(con), "n_sin": len(sin), "frec_con": fc, "frec_sin": fs,
                     "cociente": (fc / fs) if fc is not None and fs else None,
                     "exito": None if fc is None or fs is None else bool(fc >= 2 * fs)}
        # (d) estimaciones
        Md = M["d"] = {}
        for v in VERSIONS:
            by = {}
            for r in R:
                arch = r.get(f"arquetipo_{v}") or "—"
                g0, f0 = r.get(f"g_dcf_{v}"), r.get(f"fcf_dcf_anual_{v}")
                e = by.setdefault(arch, {"err_g": [], "err_fcf": [], "margen_cumplida": [], "n": 0})
                e["n"] += 1
                if g0 is not None and r["ventas_yoy_2t"] is not None:
                    e["err_g"].append(g0 - r["ventas_yoy_2t"])
                if f0 is not None and g0 is not None and r["fcf_sbc_2t"] is not None and f0 != 0:
                    k = r["meses_reales"] / 12          # 2 trimestres = ½ año (§7 d); semestral/anual, su duración
                    proj = f0 * k * (1 + g0) ** k
                    e["err_fcf"].append((proj - r["fcf_sbc_2t"]) / abs(proj))
                thr = r.get(f"premortem_margen_{v}")
                if thr is not None and r["margen_op_2t"] is not None:
                    e["margen_cumplida"].append(r["margen_op_2t"] <= thr)
            Md[v] = {k: {"n": e["n"], "n_g": len(e["err_g"]), "mediana_err_g": median(e["err_g"]),
                         "mediana_abs_err_g": median([abs(x) for x in e["err_g"]]),
                         "n_fcf": len(e["err_fcf"]), "mediana_err_fcf_rel": median(e["err_fcf"]),
                         "mediana_abs_err_fcf_rel": median([abs(x) for x in e["err_fcf"]]),
                         "premortem_margen_evaluadas": len(e["margen_cumplida"]),
                         "premortem_margen_cumplidas": sum(e["margen_cumplida"])}
                     for k, e in sorted(by.items())}
        # (e) lectura conductual (solo precio)
        Me = M["e"] = {}
        for v in VERSIONS:
            caida = [r for r in R if any(k in (r.get(f"conductual_{v}") or "")
                                          for k in ("sobrerreaccion", "caida_sin_explicar"))]
            res = {"caidas_sin_deterioro": {
                h: {"n": sum(r[f"rel_{h}"] is not None for r in caida),
                    "media_rel": mean([r[f"rel_{h}"] for r in caida]),
                    "rebotaron": (lambda xs: sum(x > 0 for x in xs) / len(xs) if xs else None)(
                        [r[f"rel_{h}"] for r in caida if r[f"rel_{h}"] is not None])}
                for h in ("6m", "12m")}}
            for sig in ("momentum", "fuerza_relativa"):
                xs = sorted(r[f"{sig}_{v}"] for r in R if r.get(f"{sig}_{v}") is not None)
                if len(xs) < 9:
                    res[sig] = None
                    continue
                c1, c2 = xs[len(xs) // 3], xs[2 * len(xs) // 3]
                ter = {"bajo": [], "medio": [], "alto": []}
                for r in R:
                    x = r.get(f"{sig}_{v}")
                    if x is None:
                        continue
                    ter["bajo" if x < c1 else "medio" if x < c2 else "alto"].append(r)
                res[sig] = {t: {h: {"n": sum(r[f"rel_{h}"] is not None for r in rs),
                                    "media_rel": mean([r[f"rel_{h}"] for r in rs])} for h in ("6m", "12m")}
                            for t, rs in ter.items()}
            Me[v] = res
        flat += [{"muestra": muestra, "metodo": m, "horizonte": h, **{k: x[h][k] for k in
                  ("n_barata", "n_cara", "media_barata", "media_cara", "D")},
                  "ic95_bajo": (x[h]["ic95"] or (None, None))[0], "ic95_alto": (x[h]["ic95"] or (None, None))[1]}
                 for m, x in Ma.items() for h in ("12m", "6m")]

    cols = list(rows[0].keys())
    with open(os.path.join(base, "empresas_410.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    with open(os.path.join(base, "metricas_a.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(flat[0].keys()))
        w.writeheader()
        w.writerows(flat)
    with open(os.path.join(base, "metricas.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1, default=str)
    print(json.dumps({m: {"a": {k: out[m]["a"][k]["12m"]["D"] for k in out[m]["a"]},
                          "exito_a_A": out[m]["a"]["A"]["exito"]} for m in ("control", "110")},
                     ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
