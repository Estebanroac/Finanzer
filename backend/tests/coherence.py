"""
F9 · R3 (revisión externa de NU): una sola verdad por cifra. Recorre el informe y devuelve cada cifra mostrada como
(métrica, unidad, periodo, valor, tolerancia, dónde); `conflicts` da las parejas de la misma métrica, unidad y periodo
con valores distintos más allá del redondeo con que se muestran.

- `display_figures(a)`: el `display` entero, la web y la base del PDF:
    · toda fila, tarjeta, KPI o punto con `key` y un valor mostrado (`value` / `value_txt`), con el periodo del corte;
    · la historia de 10 años (`extended.history_10y`) y el gráfico histórico (`charts.historical`), por ejercicio;
    · el CAGR del gráfico histórico, con su ventana, frente al crecimiento a 3 años de la ventana del informe;
    · el cuadro de cifras y la escalera de márgenes (periodo del corte).
- `pdf_figures(text, display)`: en el texto del PDF, la cifra que sigue a cada rótulo de una cifra con clave.

El periodo «corte» es el de los estados del análisis (`data_provenance.as_of`: TTM o FY); «FY2025», un ejercicio.
"""
import collections
import re
from typing import Any, Dict, List, Optional, Tuple

_NUM = re.compile(r"^([+\-]?)\$?\s?([+\-]?)(\d[\d,]*(?:\.\d+)?)\s?(%|x|B|M|T|K|pp)?$")
_SCALE = {"B": 1e9, "M": 1e6, "T": 1e12, "K": 1e3}

Figure = Tuple[str, str, str, float, float, str]      # (métrica, unidad, periodo, valor, tolerancia, dónde)


def parse(v: Any, unit: Optional[str] = None) -> Optional[Tuple[float, str, float]]:
    """«$13.17B» → (13.17e9, "$", 0.005e9); «52.31%» → (52.31, "%", 0.005); «4.55x» → (4.55, "x", 0.005). Los números
    crudos (sin formato) no se muestran al lector: None."""
    if not isinstance(v, str):
        return None
    s = v.strip().replace("−", "-").replace(" ", "").replace("\xa0", "")
    m = _NUM.match(s)
    if not m:
        return None
    sign = -1.0 if "-" in (m.group(1) + m.group(2)) else 1.0
    digits, suf = m.group(3).replace(",", ""), m.group(4)
    dec = len(digits.split(".")[1]) if "." in digits else 0
    scale = _SCALE.get(suf or "", 1.0)
    u = "$" if "$" in s else ("%" if suf == "%" else "x" if suf == "x" else "pp" if suf == "pp" else (unit or ""))
    return sign * float(digits) * scale, u, 0.5 * 10 ** -dec * scale


def _fy(year: Any) -> str:
    return f"FY{year}"


def display_figures(a: Dict[str, Any]) -> List[Figure]:
    d = a.get("display") or {}
    out: List[Figure] = []
    skip = ("extended.history_10y", "charts.historical")

    def walk(x, p):
        if isinstance(x, dict):
            k = x.get("key")
            if isinstance(k, str) and not p.startswith(skip):
                for vk in ("value", "value_txt"):
                    r = parse(x.get(vk), x.get("unit") if isinstance(x.get("unit"), str) else None)
                    if r:
                        out.append((k, r[1], "corte", r[0], r[2], f"{p}.{vk}"))
                        break
            for kk, v in x.items():
                walk(v, f"{p}.{kk}" if p else kk)
        elif isinstance(x, list):
            for i, v in enumerate(x):
                walk(v, f"{p}[{i}]")
    walk(d, "")

    # Historia de 10 años y gráfico histórico: por ejercicio.
    for i, r in enumerate(((d.get("extended") or {}).get("history_10y") or {}).get("rows") or []):
        for col, metric in (("revenue_txt", "revenue"), ("revenue_growth_txt", "revenue_growth_yoy"),
                            ("net_margin_txt", "net_margin"), ("net_income_txt", "net_income")):
            v = parse(r.get(col))
            if v:
                out.append((metric, v[1], _fy(r.get("year")), v[0], v[2], f"extended.history_10y.rows[{i}].{col}"))
    for s in (d.get("charts") or {}).get("historical", {}).get("series") or []:
        pts = s.get("points") or []
        for j, pt in enumerate(pts):
            for col, metric in (("value_txt", s.get("key")), ("yoy_txt", f"{s.get('key')}_growth_yoy")):
                v = parse(pt.get(col))
                if v:
                    out.append((metric, v[1], _fy(pt.get("year")), v[0], v[2],
                                f"charts.historical.{s.get('key')}.points[{j}].{col}"))
        v = parse(s.get("cagr_txt"))
        if v and len(pts) == 4 and s.get("key") == "revenue":
            win = f"{_fy(pts[0].get('year'))}–{_fy(pts[-1].get('year'))}"
            out.append(("revenue_growth", v[1], f"3 años {win}", v[0], v[2], "charts.historical.revenue.cagr_txt"))

    # El crecimiento a 3 años de los ingresos con su ventana (la del motor) y el último ejercicio con su año.
    # Con emisión de acciones el motor mide los ingresos POR ACCIÓN y lo rotula: es otra métrica que la del gráfico.
    win = (a.get("growth_basis") or {}).get("revenue_window")
    per_share = "ingresos" in ((a.get("growth_basis") or {}).get("applied_to") or [])
    last_fy = max((y.get("year") for y in a.get("yearly_financials") or [] if y.get("year")), default=None)
    rel = []
    for f in out:
        if f[0] == "revenue_growth" and f[2] == "corte" and win:
            rel.append(("revenue_per_share_growth" if per_share else "revenue_growth", f[1], f"3 años {win}", *f[3:]))
        elif f[0] == "revenue_growth_yoy" and f[2] == "corte" and last_fy:
            rel.append(("revenue_growth_yoy", f[1], _fy(last_fy), *f[3:]))
        else:
            rel.append(f)
    out = rel

    # Cuadro de cifras y escalera de márgenes: el periodo del corte.
    labels = {"Ingresos": "revenue", "Beneficio neto": "net_income", "EBITDA": "ebitda"}
    for i, row in enumerate(((d.get("sections") or {}).get("profitability") or {}).get("figures") or []):
        for j in range(0, len(row) - 1, 2):
            m, v = labels.get(row[j]), parse(row[j + 1])
            if m and v:
                out.append((m, v[1], "corte", v[0], v[2], f"sections.profitability.figures[{i}][{j + 1}]"))
    ml = ((d.get("charts") or {}).get("profitability") or {}).get("margin_ladder") or {}
    v = parse(ml.get("revenue_txt"))
    if v:
        out.append(("revenue", v[1], "corte", v[0], v[2], "charts.profitability.margin_ladder.revenue_txt"))
    return out


def conflicts(figs: List[Figure]) -> List[Tuple[Figure, Figure]]:
    by = collections.defaultdict(list)
    for f in figs:
        by[(f[0], f[1], f[2])].append(f)
    res = []
    for xs in by.values():
        for i in range(len(xs)):
            for j in range(i + 1, len(xs)):
                if abs(xs[i][3] - xs[j][3]) > xs[i][4] + xs[j][4] + 1e-9:
                    res.append((xs[i], xs[j]))
    return res


def pdf_conflicts(text: str, a: Dict[str, Any], value_above: bool = False) -> List[Tuple[str, str, float, List[float]]]:
    """En el texto del PDF, cada rótulo de una cifra con clave del `display` (portada, tarjetas y tablas) con su cifra:
    en el PDF nuevo, la primera en las tres líneas siguientes («P/B» y «4.54x», o «4.5» y «x»; en las tablas, tras la
    definición); en el actual (`value_above`), la de encima del rótulo. Contradicción: la cifra no es la del `display`
    con la misma unidad. Los puntos de la puntuación («+4», «−4»: con signo, enteros y sin unidad) no son la cifra.
    -> [(rótulo, unidad, valor del display, cifras contiguas)]"""
    d = a.get("display") or {}
    ref: Dict[str, Tuple[str, float, float, str]] = {}
    # La portada y el resumen (KPI y tarjetas): lo que la revisión vio con otra cifra que la tabla. Que portada,
    # resumen y tablas coincidan lo comprueba display_figures sobre el `display`, del que sale el PDF.
    for x in list((d.get("cover") or {}).get("kpis") or []) + list((d.get("summary") or {}).get("cards") or []):
        k, lab = x.get("key"), x.get("label")
        r = parse(x.get("value"), x.get("unit") if isinstance(x.get("unit"), str) else None)
        if isinstance(k, str) and isinstance(lab, str) and r and r[1] in ("%", "x", "$"):
            ref.setdefault(lab.strip().upper(), (k, r[0], r[2], r[1]))
    points = re.compile(r"^[+\-−]\d+$")
    lines = [ln.strip() for ln in text.splitlines()]

    def num(i):
        if not (0 <= i < len(lines)) or points.match(lines[i]):
            return None
        s = lines[i] + (lines[i + 1] if i + 1 < len(lines) and lines[i + 1] in ("%", "x") else "")
        return parse(s)
    out = []
    for i, ln in enumerate(lines):
        r = ref.get(ln.upper())
        if not r:
            continue
        k, val, tol, unit = r
        if value_above:
            cand = [num(i - 1)]
        else:
            # La primera cifra tras el rótulo, saltando la definición (texto sin números); un texto con números (las
            # bandas del anexo de definiciones) corta la búsqueda: lo que siga no es la cifra del rótulo.
            cand = []
            for j in range(1, 4):
                v = num(i + j)
                if v:
                    cand = [v]
                    break
                if i + j >= len(lines) or re.search(r"\d", lines[i + j]):
                    break
        near = [v for v in cand if v and v[1] == unit]
        if near and not any(abs(v[0] - val) <= v[2] + tol + 1e-9 for v in near):
            out.append((ln, unit, val, [v[0] for v in near]))
    return out


# ── F10 · B2: los análisis guardados del escaneo del modelo general ──
# tools/universe_scan.py (rama modelo/general-inventario) guarda por empresa <SÍMBOLO>.analysis.json.gz con el análisis
# y el texto del PDF nuevo; FINANZER_SCAN_CACHE apunta a esa carpeta (p. ej.
# ~/Library/Caches/finanzer-universe-scan/2026-10-28-v2) y test_coherencia_f9.py la recorre si existe.
SCAN_ENV = "FINANZER_SCAN_CACHE"


def scan_files(folder: Optional[str] = None) -> List[str]:
    import glob
    import os
    folder = folder or os.environ.get(SCAN_ENV)
    return sorted(glob.glob(os.path.join(folder, "*.analysis.json.gz"))) if folder and os.path.isdir(folder) else []


def scan_load(path: str) -> Tuple[Dict[str, Any], Optional[str]]:
    import gzip
    import json
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        d = json.load(fh)
    return d.get("analysis", d), d.get("pdf_text")


def scan_conflicts(path: str) -> List[str]:
    """Las cifras dobles de un análisis guardado: en el display y entre el PDF nuevo y el display."""
    a, text = scan_load(path)
    out = [f"{x[0]} ({x[2]}): {x[3]:g} en {x[5]} frente a {y[3]:g} en {y[5]}" for x, y in conflicts(display_figures(a))]
    out += [f"PDF: {lab} {near} frente a {val:g}{unit} en el display"
            for lab, unit, val, near in (pdf_conflicts(text, a, False) if text else [])]
    return out


if __name__ == "__main__":     # python tests/coherence.py [CARPETA]: las cifras dobles de un escaneo
    import os
    import sys
    bad = {os.path.basename(p).split(".")[0]: scan_conflicts(p) for p in scan_files(sys.argv[1] if len(sys.argv) > 1
                                                                                    else None)}
    bad = {t: c for t, c in bad.items() if c}
    for t, c in bad.items():
        print(t, len(c), "·", c[0])
    print(f"{len(bad)} empresas con cifras dobles")
