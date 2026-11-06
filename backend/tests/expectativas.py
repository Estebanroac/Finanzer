"""
F15 (6-nov-2026): las expectativas de referencia de las 110 empresas (tests/expectativas/golden_110.yaml, del
evaluador externo; solo cambian con la aprobación del usuario y nunca para que un cambio del motor pase la prueba).

    cd finanzer_next/backend
    ../.venv313/bin/python tests/expectativas.py --banco <carpeta del banco congelado> [--estado-escribir]

Por empresa: la etiqueta de precio del veredicto en `precio_aceptable`, la confianza ≤ `confianza_max`, el arquetipo en
`arquetipo` y fuera de `arquetipo_no`, y los textos de `debe_mostrar`. Además, las reglas globales que se pueden medir
sobre un análisis (R1, R2, R3, R4, R6, R8, R10, R11); R5 la cubre verdict.abstention, R7 tests/test_damodaran_erp.py y
R9 la nota de la referencia (F14 · paso 11). Sin red: lee los análisis del banco (`<T>.json.gz`).

Sale con código 1 si alguna regla global se incumple o si una empresa que cumplía (tests/expectativas/estado.json) deja
de cumplir. `--estado-escribir` guarda las que cumplen hoy (solo al cerrar una versión).

El YAML se lee con un lector propio de su subconjunto (claves, listas y cadenas, también entre comillas en varias líneas):
la app no depende de PyYAML.
"""
import argparse
import gzip
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
YAML = os.path.join(HERE, "expectativas", "golden_110.yaml")
ESTADO = os.path.join(HERE, "expectativas", "estado.json")
CONF = ["baja", "media", "alta"]
# R3: industrias de Yahoo de los productores de materias primas (minería, petróleo y gas, química básica, acero,
# fertilizantes)
COMMODITY = ("gold", "silver", "copper", "other precious metals", "other industrial metals", "aluminum", "steel",
             "coking coal", "thermal coal", "uranium", "oil & gas e&p", "oil & gas integrated",
             "oil & gas refining & marketing", "chemicals", "agricultural inputs")


# ── lector del subconjunto de YAML ──
def _scalar(s: str) -> str:
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] == "'":
        return s[1:-1].replace("''", "'")
    if len(s) >= 2 and s[0] == s[-1] == '"':
        return s[1:-1]
    return s


def load_yaml(path: str = YAML) -> Dict[str, Any]:
    lines = []
    with open(path, encoding="utf-8") as fh:
        raw = fh.read().splitlines()
    i = 0
    while i < len(raw):                     # une las cadenas entre comillas que siguen en otras líneas
        ln = raw[i]
        if not ln.strip() or ln.lstrip().startswith("#"):
            i += 1
            continue
        # una cadena entre comillas simples sin cerrar sigue en las líneas siguientes (con '' como comilla escapada)
        val = ln.split(": ", 1)[1] if ": " in ln else ""
        while val.startswith("'") and val.replace("''", "").count("'") % 2 == 1 and i + 1 < len(raw):
            i += 1
            ln += " " + raw[i].strip()
            val = ln.split(": ", 1)[1]
        # un valor sin comillas sigue en las líneas más sangradas que su clave
        ind = len(ln) - len(ln.lstrip(" "))
        key_ind = ind + (2 if ln.lstrip().startswith("- ") else 0)
        while val and i + 1 < len(raw) and raw[i + 1].strip() and not raw[i + 1].lstrip().startswith("#") \
                and len(raw[i + 1]) - len(raw[i + 1].lstrip(" ")) > key_ind:
            i += 1
            ln += " " + raw[i].strip()
        lines.append(ln)
        i += 1
    root: Dict[str, Any] = {}
    key = item = None
    for ln in lines:
        ind = len(ln) - len(ln.lstrip(" "))
        s = ln.strip()
        if ind == 0 and not s.startswith("- "):
            k, _, v = s.partition(":")
            key, item = k.strip(), None
            root[key] = _scalar(v) if v.strip() else []
            continue
        if ind == 0 and s.startswith("- "):          # elemento de una lista de primer nivel
            body = s[2:]
            if re.match(r"^[^:'\"]+:\s", body + " ") and ":" in body:
                k, _, v = body.partition(":")
                item = {k.strip(): _scalar(v)}
                root[key].append(item)
            else:
                item = None
                root[key].append(_scalar(body))
            continue
        if item is None:
            continue
        if s.startswith("- "):                        # lista dentro del elemento
            item[sub].append(_scalar(s[2:]))
            continue
        k, _, v = s.partition(":")
        sub = k.strip()
        item[sub] = _scalar(v) if v.strip() else []
    return root


# ── lectura de un análisis ──
def price_label(a: Dict[str, Any]) -> str:
    t = (a.get("verdict") or {}).get("text") or ""
    p = t.split("precio ", 1)[1] if "precio " in t else "sin veredicto"
    return "sin veredicto" if p in ("sin dato", "sin veredicto") else p


def check_company(e: Dict[str, Any], a: Dict[str, Any]) -> List[str]:
    v = a.get("verdict") or {}
    why = []
    # F16 (decisión del usuario del 6-nov-2026): la etiqueta de precio es la regla L1 de la prueba hacia atrás; los rangos
    # de precio del YAML (`precio_aceptable`) se fijaron con la valoración anterior y ya no son prueba. Se conservan en el
    # archivo como registro, sin comprobarse.
    conf = v.get("confidence")
    if e.get("confianza_max") and conf in CONF and CONF.index(conf) > CONF.index(e["confianza_max"]):
        why.append(f"confianza {conf} > {e['confianza_max']}")
    arch = (a.get("classification") or {}).get("archetype")
    if e.get("arquetipo") and arch not in e["arquetipo"]:
        why.append(f"arquetipo {arch} fuera de {e['arquetipo']}")
    if e.get("arquetipo_no") and arch in e["arquetipo_no"]:
        why.append(f"arquetipo {arch} no permitido")
    blob = json.dumps(a, ensure_ascii=False).lower()
    for m in e.get("debe_mostrar") or []:
        if m.lower() not in blob:
            why.append(f"no muestra «{m}»")
    return why


def global_rules(t: str, a: Dict[str, Any]) -> List[str]:
    """Las reglas globales medibles sobre un análisis: [«Rn: motivo»]."""
    out = []
    v, km = a.get("verdict") or {}, a.get("key_metrics") or {}
    conf = v.get("confidence")
    z = a.get("altman_z") or {}
    ref = bool((a.get("business_model") or {}).get("altman_referential"))
    en = ((a.get("earnings_normalization") or {}).get("operating") or {}).get("normalized")
    rows = (a.get("history_10y") or {}).get("rows") or []
    neg_fcf = sum(1 for r in rows[-3:] if (r.get("free_cash_flow") or 0) < 0)
    arch = (a.get("classification") or {}).get("archetype")
    if conf == "alta":
        if z.get("applicable") and z.get("zone") == "distress" and not ref:
            out.append("R1: confianza alta con Altman en zona de peligro")
        if en is not None and en < 0 and arch != "FINANCIAL":
            out.append("R1: confianza alta con EBIT normalizado negativo")
        if neg_fcf >= 2 and arch != "FINANCIAL":
            out.append("R1: confianza alta con caja libre negativa en 2 de los 3 últimos años")
        up = (a.get("dcf") or {}).get("upside")
        if up is not None and abs(up) > 150:
            out.append(f"R2: confianza alta con un DCF de {up:+.0f} %")
        pen, fpe = km.get("pe_normalized"), km.get("forward_pe")
        if pen and fpe and pen > 0 and fpe > 0 and abs(pen / fpe - 1) > 0.40:
            out.append("R2: confianza alta con el P/E normalizado y el forward a más del 40 %")
    ind = ((a.get("profile") or {}).get("industry") or "").lower()
    if ind in COMMODITY and arch != "CYCLICAL":
        out.append(f"R3: productora de materias primas ({ind}) clasificada {arch}")
    peak = (a.get("earnings_peak") or {}).get("flag")
    if arch == "CYCLICAL" and peak and v.get("price_level") == "atractivo" and conf in ("media", "alta"):
        out.append("R4: cíclica en pico «atractivo» con confianza mayor que baja")
    br, g = a.get("dcf_growth_base_rate") or {}, (a.get("dcf") or {}).get("growth_rate")
    if br.get("company") is not None and g is not None and br["company"] * g < 0:
        out.append("R6: el crecimiento del DCF cambia el signo del de la empresa")
    w = (a.get("wacc") or {}).get("value")
    cov = ((a.get("wacc") or {}).get("rating") or {}).get("coverage")
    if w is not None and not (0.05 <= w <= 0.15) and not (cov is not None and cov < 0):
        out.append(f"R8: coste de capital {w:.1%} fuera de [5 %, 15 %]")
    te = km.get("total_equity")
    ta = ((a.get("yearly_financials") or [{}])[0] or {}).get("total_assets")
    if te and ta and te / ta < 0.05 and any("ROE" in (s.get("reason") or "")
                                           for s in (a.get("alerts") or {}).get("strengths") or []):
        out.append("R10: ROE como fortaleza con un patrimonio menor que el 5 % de los activos")
    meths = [m for m in ((a.get("confidence") or {}).get("dimensions") or {}).get("convergence", {}).get("methods") or []
             if m.get("evaluable")]
    if v.get("price_level") == "muy exigente" and sum(1 for m in meths if m.get("direction") == "cara") < 2:
        out.append("R11: «muy exigente» con un solo método que la ve cara")
    return out


def _load(banco: str, t: str) -> Optional[Dict[str, Any]]:
    for p in (os.path.join(banco, f"{t}.json.gz"), os.path.join(banco, f"{t}.json")):
        if os.path.exists(p):
            with (gzip.open(p) if p.endswith(".gz") else open(p, "rb")) as fh:
                return json.load(fh)
    return None


def evaluate(banco: str, golden: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    g = golden or load_yaml()
    res, rules = {}, {}
    for e in g["empresas"]:
        a = _load(banco, e["ticker"])
        if a is None or "__http_error__" in a:
            res[e["ticker"]] = ["sin análisis en el banco"]
            continue
        res[e["ticker"]] = check_company(e, a)
        r = global_rules(e["ticker"], a)
        if r:
            rules[e["ticker"]] = r
    return {"ok": sorted(t for t, w in res.items() if not w), "fails": {t: w for t, w in res.items() if w},
            "rules": rules, "total": len(res)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--banco", required=True)
    ap.add_argument("--estado-escribir", action="store_true")
    a = ap.parse_args()
    r = evaluate(a.banco)
    print(f"Cumplen {len(r['ok'])} de {r['total']} ({len(r['ok']) / r['total']:.0%})")
    for t, w in r["fails"].items():
        print(f"  {t:6} " + "; ".join(w))
    print(f"Reglas globales: {sum(len(x) for x in r['rules'].values())} incumplimientos")
    for t, w in r["rules"].items():
        print(f"  {t:6} " + "; ".join(w))
    bad = bool(r["rules"])
    if os.path.exists(ESTADO):
        with open(ESTADO, encoding="utf-8") as fh:
            prev = set(json.load(fh)["ok"])
        lost = sorted(prev - set(r["ok"]))
        print(f"Regresiones frente al estado guardado: {lost or 'ninguna'}")
        bad = bad or bool(lost)
    if a.estado_escribir:
        with open(ESTADO, "w", encoding="utf-8") as fh:
            json.dump({"banco": os.path.basename(os.path.normpath(a.banco)), "ok": r["ok"]}, fh, ensure_ascii=False,
                      indent=1)
        print(f"estado escrito: {os.path.relpath(ESTADO, HERE)}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
