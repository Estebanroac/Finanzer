"""
Datos de los gráficos de la web (etapa 9c): display.charts.

La web vuelve a ser visual (anillos, barras frente al sector, escalas con zonas,
medidores), pero sigue sin decidir nada: cada gráfico recibe aquí su valor, su
referencia, sus zonas y su tono. Las zonas salen de la MISMA config que usan los
lectores de display.py (y el score), así que un marcador siempre cae en la zona
cuya etiqueta es la lectura de la tabla (tests/test_display_charts.py). Nada de
esto cambia una lectura ni un score: solo expone en números lo que ya se lee.

Cada gráfico lleva `state` (con_dato | sin_dato | no_aplica | no_significativo) y,
si no hay dato, `text` con el motivo: la web pinta un estado propio, nunca un hueco.
"""
from typing import Any, Dict, List, Optional

import numfmt
from settings import cfg

_SOL = cfg("thresholds.score.solidez")
_PDF = cfg("thresholds.pdf")

# Etiquetas y tonos de cada lector (display.read_*), en el orden de sus bandas.
_CURRENT = (("Holgada", "Sólida", "Justa", "Ajustada", "Tensión"), ('pos', 'pos', 'neu', 'warn', 'neg'))
_COVERAGE = (("Muy holgada", "Sólida", "Aceptable", "Justa", "Crítica"), ('pos', 'pos', 'neu', 'warn', 'neg'))
_COVERAGE_UTILITY = (("Fuerte", "Adecuada", "En línea", "Ajustada", "Riesgo"), ('pos', 'pos', 'neu', 'warn', 'neg'))
_NDE = (("Baja", "Moderada", "Elevada", "Alta"), ('pos', 'neu', 'warn', 'neg'))
_NDE_BRANCH = (("Conservadora", "Adecuada", "En línea", "Elevada", "Alta"), ('pos', 'pos', 'neu', 'warn', 'neg'))
_DE = (("Conservador", "Controlado", "Aceptable", "Elevado", "Alto"), ('pos', 'pos', 'neu', 'warn', 'neg'))
_RUNWAY = (("Holgado", "Cómodo", "Ajustado", "Crítico"), ('pos', 'pos', 'warn', 'neg'))
_UPSIDE = (("Muy infravalorada", "Infravalorada", "Precio justo", "Prima", "Sobrevalorada"),
           ('pos', 'pos', 'neu', 'warn', 'neg'))
_ALTMAN = (("Zona de riesgo", "Zona gris", "Zona segura"), ('neg', 'warn', 'pos'))
_SEV_TONE = {"excellent": 'pos', "good": 'pos', "ok": 'neu', "moderate": 'warn', "severe": 'neg'}


def _num(v) -> Optional[float]:
    try:
        f = float(v)
        return f if f == f else None
    except (TypeError, ValueError):
        return None


def _pct(v: Optional[float], dec: int = 1) -> Optional[str]:
    """Fracción -> "12.6%" (con el menos tipográfico)."""
    if v is None:
        return None
    return f"{numfmt.MINUS if v < 0 else ''}{abs(v) * 100:.{dec}f}%"


def _fmt(v: Optional[float], fmt: str) -> Optional[str]:
    """Mismo formato que las tablas: múltiplo "22.15x" o porcentaje "41.26%"."""
    if v is None:
        return None
    return f"{v:.2f}x" if fmt == "mult" else _pct(v, 2)


def _rows(D, section, sub=None) -> Dict[str, Dict[str, Any]]:
    sec = (D.get("sections") or {}).get(section) or {}
    if sub:
        sec = sec.get(sub) or {}
    return {r["key"]: r for r in sec.get("rows") or []}


def _na(state: str, text: Optional[str]) -> Dict[str, Any]:
    return {"state": state, "text": text}


def zones_desc(bounds, labels, tones, top: float) -> List[Dict[str, Any]]:
    """Zonas "mayor es mejor" (≥ b0 la mejor) sobre el eje [0, top]."""
    edges = [0.0] + sorted(bounds) + [max(top, max(bounds))]
    n = len(bounds)
    out = []
    for i in range(n + 1):                       # de abajo arriba: la peor primero
        out.append({"from": edges[i], "to": edges[i + 1], "label": labels[n - i], "tone": tones[n - i]})
    return out


def zones_asc(bounds, labels, tones, top: float) -> List[Dict[str, Any]]:
    """Zonas "menor es mejor" (≤ b0 la mejor) sobre el eje [0, top]."""
    edges = [0.0] + list(bounds) + [max(top, bounds[-1])]
    return [{"from": edges[i], "to": edges[i + 1], "label": labels[i], "tone": tones[i]}
            for i in range(len(bounds) + 1)]


# Clave de cada medidor en sectors.archetypes.not_applicable.
_GAUGE_NA = {"current_ratio": "current_ratio", "interest_coverage": "interest_coverage",
             "net_debt_to_ebitda": "net_debt_ebitda", "de": "de"}


def _gauge(key, label, value, value_txt, zones, row, axis_max, *, unit="x", archetype=None) -> Dict[str, Any]:
    """Medidor con zonas: valor, eje, zonas y la lectura de la tabla (etiqueta, tono, texto)."""
    from classify import not_applicable
    why = not_applicable(archetype, _GAUGE_NA.get(key, key))
    if why:
        return {"key": key, "label": label, "state": "no_aplica", "text": why}
    if key == "interest_coverage" and value is None and (row or {}).get("value") == "Sin carga":
        # Fase 1: sin carga financiera neta (EBIT > 0, ingresos financieros netos): lectura sin escala.
        return {"key": key, "label": label, "state": "con_dato", "no_burden": True, "value_txt": row.get("value"),
                "reading": row.get("reading"), "tone": row.get("tone"), "text": row.get("text")}
    if row is None or row.get("state") != "con_dato" or value is None:
        st = (row or {}).get("state") or "sin_dato"
        return {"key": key, "label": label, "state": "sin_dato" if st == "con_dato" else st,
                "text": (row or {}).get("text") or (row or {}).get("reading")}
    if key == "interest_coverage" and value < 0:
        # EBIT < 0 con deuda neta: la cobertura no se sitúa en la escala; la lectura es "Riesgo".
        return {"key": key, "label": label, "state": "con_dato", "negative": True, "value_txt": value_txt,
                "reading": row.get("reading"), "tone": row.get("tone"), "text": row.get("text")}
    return {"key": key, "label": label, "state": "con_dato", "value": value, "value_txt": value_txt,
            "axis_max": axis_max, "clamped": value > axis_max or value < 0, "zones": zones, "unit": unit,
            "reading": row.get("reading"), "tone": row.get("tone"), "text": row.get("text")}


def _fair_value(a, D, price) -> Dict[str, Any]:
    """Precio frente al valor razonable del DCF y al rango de su grid, con las zonas de la lectura
    del upside (thresholds.score.valoracion.dcf_upside_bounds pasadas a precios)."""
    st = a.get("dcf_status") or {}
    rows = _rows(D, "valuation", "intrinsic")
    fv_row, up_row = rows.get("dcf_fair_value"), rows.get("dcf_upside")
    fv = _num((a.get("dcf") or {}).get("fair_value"))
    if st.get("state") in ("no_aplica", "no_significativo") or fv_row and fv_row.get("state") in (
            "no_aplica", "no_significativo"):
        state = st.get("state") if st.get("state") in ("no_aplica", "no_significativo") else fv_row["state"]
        return _na(state, (fv_row or {}).get("text") or st.get("reason"))
    if fv is None or not price:
        return _na("sin_dato", st.get("reason") or (D["sections"]["valuation"].get("dcf_missing")))
    b = cfg("thresholds.score.valoracion.dcf_upside_bounds")
    cuts = [fv / (1 + x) for x in b]               # precio en el que el upside vale cada límite
    grid = [_num(v) for row in ((a.get("sensitivity") or {}).get("matrix") or []) for v in row]
    grid = [g for g in grid if g is not None and g > 0]
    lo_g, hi_g = (min(grid), max(grid)) if grid else (None, None)
    pts = [p for p in (price, fv, lo_g, hi_g, cuts[0], cuts[-1]) if p]
    lo, hi = min(pts) * 0.85, max(pts) * 1.1
    edges = [lo] + cuts + [hi]
    zones = [{"from": edges[i], "to": edges[i + 1], "label": _UPSIDE[0][i], "tone": _UPSIDE[1][i]}
             for i in range(len(edges) - 1)]
    rel = D["sections"]["valuation"]
    return {"state": "con_dato", "method": "DCF", "price": price, "fair_value": fv, "grid_low": lo_g, "grid_high": hi_g,
            "price_txt": numfmt.price(price), "fair_value_txt": numfmt.price(fv),
            "grid_low_txt": numfmt.whole(lo_g) if lo_g else None, "grid_high_txt": numfmt.whole(hi_g) if hi_g else None,
            "axis": [lo, hi], "zones": zones,
            "badge": {"label": (up_row or {}).get("reading"), "tone": (up_row or {}).get("tone")},
            "upside_txt": (up_row or {}).get("value"), "reliability": rel.get("dcf_reliability_level"),
            "reliability_tone": rel.get("dcf_reliability_tone"), "text": (up_row or {}).get("text")}


# Múltiplos y rentabilidades frente a la referencia (barra con marcador de la mediana).
_VAL_KEYS = (("pe", "P/E (TTM)", False, "mult"), ("forward_pe", "Forward P/E", False, "mult"),
             ("pb", "P/B", False, "mult"), ("peg", "PEG", False, "mult"),
             ("ev_ebitda", "EV/EBITDA", False, "mult"), ("pfcf", "P/FCF", False, "mult"),
             ("fcf_yield", "FCF yield", True, "pct"))
_RET_KEYS = (("roe", "ROE", True, "pct"), ("roa", "ROA", True, "pct"), ("roic", "ROIC", True, "pct"))
_MARGIN_KEYS = (("gross_margin", "Margen bruto", True, "pct"), ("operating_margin", "Margen operativo", True, "pct"),
                ("net_margin", "Margen neto", True, "pct"))


def _vs_bench(keys, rows, km, bench, na_text=None) -> List[Dict[str, Any]]:
    out = []
    for key, label, higher, fmt in keys:
        r = rows.get(key)
        if r is None:
            continue
        item = {"key": key, "label": r.get("label") or label, "higher_is_better": higher, "fmt": fmt,
                "state": r.get("state"),
                "text": r.get("text") or (na_text if r.get("state") == "no_aplica" else None)}
        v, b = _num(km.get(key)), _num(bench.get(key))
        if r.get("state") == "con_dato" and v is not None:
            item.update({"value": v, "value_txt": r.get("value"), "bench": b, "bench_txt": r.get("bench"),
                         "gap_txt": r.get("gap") if r.get("gap") not in (None, "—") else None,
                         "gap_pct": ((v - b) / abs(b) * 100) if b else None,
                         "reading": r.get("reading"), "tone": r.get("tone")})
        elif r.get("state") == "con_dato":
            item["state"] = "sin_dato"
        out.append(item)
    return out


# Métrica del desglose de Valoración -> clave de su fila en la tabla (prefijos más largos primero).
_BD_ROW = (("P/FCF normalizado", "p_fcf_normalizado"), ("EV/EBITDA normalizado", "ev_ebitda_normalizado"),
           ("Forward P/E", "forward_pe"), ("PEG", "peg"), ("P/E", "pe"), ("P/FCF", "pfcf"), ("EV/EBITDA", "ev_ebitda"),
           ("P/B frente a ROE", "p_b_frente_a_roe"), ("P/TBV frente a ROTE", "p_tbv_frente_a_rote"),
           ("P/FFO", "p_ffo_reit"), ("EV/Ventas", "ev_ventas"), ("Regla de 40", "regla_de_40"))


def _price_scoring(D) -> tuple:
    """Del desglose de Valoración: la línea del bloque, sus miembros y lo que puntúa aparte (por clave de fila)."""
    cats = ((D["sections"]["institutional"].get("breakdown") or {}).get("categories") or [])
    cat = next((c for c in cats if c.get("group") == "price"), None)
    block, members, others = None, {}, {}
    for it in (cat or {}).get("items") or []:
        m = it.get("metric") or ""
        if m.startswith("Bloque"):
            block = {"label": m, "sign": it.get("sign"), "tone": it.get("tone"), "reason": it.get("reason")}
            continue
        if m.startswith("DCF") or it.get("state") == "no_aplica":
            continue
        key = next((k for pre, k in _BD_ROW if m.startswith(pre)), None)
        if key:
            (members if it.get("in_block") else others)[key] = it
    return block, members, others


def _growth_raw(a) -> Dict[str, Any]:
    adj = {x.get("metric"): x for x in ((a.get("score") or {}).get("breakdown") or {}).get("Crecimiento", {})
           .get("adjustments") or []}
    rev = adj.get("Crecimiento Ingresos 3Y") or adj.get("Retorno total (dividendo + FFO por acción)")
    eps = adj.get("Crecimiento EPS 3Y")
    fcf = (adj.get("Crecimiento FCF 3Y") or adj.get("Crecimiento FCF − SBC 3Y")
           or adj.get("Crecimiento FCF por acción 3Y"))
    return {"revenue": rev, "eps": eps, "fcf": fcf}


def _cagr_series(values: List[Optional[float]]) -> Optional[float]:
    """CAGR entre el primer y el último ejercicio de la serie (orden cronológico), solo con
    extremos positivos: la anotación sobre las barras del histórico."""
    vals = [v for v in values if v is not None]
    if len(vals) < 2 or vals[0] <= 0 or vals[-1] <= 0:
        return None
    n = len(values) - 1
    return (vals[-1] / vals[0]) ** (1 / n) - 1 if n > 0 else None


def build_charts(a: Dict[str, Any], D: Dict[str, Any], sector_bench: Dict[str, Any], *, th, market: bool,
                 de_mode: str) -> Dict[str, Any]:
    km = a.get("key_metrics") or {}
    price = _num(a.get("price"))
    archetype = D.get("archetype")
    na = set(D.get("na_keys") or [])
    bench = sector_bench or {}
    profile = a.get("profile") or {}

    # ── Cabecera: tarjeta de precio ──
    hi, lo = _num(km.get("price_52w_high")), _num(km.get("price_52w_low"))
    price_card = {"price": price, "price_txt": numfmt.price(price),
                  "currency": profile.get("currency"), "exchange": profile.get("exchange"),
                  "from_high_pct": ((price / hi - 1) * 100) if (price and hi) else None,
                  "from_high_txt": numfmt.signed_pct((price / hi - 1) * 100, 1) if (price and hi) else None,
                  "low": lo, "high": hi, "low_txt": numfmt.price(lo) if lo else None,
                  "high_txt": numfmt.price(hi) if hi else None}

    # ── Valoración ──
    vrows = _rows(D, "valuation")
    vc = (a.get("dcf") or {}).get("value_composition") or {}
    dcf_comp = None
    if (D["sections"]["valuation"]["intrinsic"]["rows"] and (a.get("dcf") or {}).get("fair_value")
            and vc.get("terminal_pct") is not None):
        explicit = (vc.get("stage1_pct") or 0) + (vc.get("stage2_pct") or 0)
        dcf_comp = {"explicit_pct": explicit, "terminal_pct": vc["terminal_pct"]}
    # Etapa 9c: papel de cada múltiplo en el score. Los miembros del bloque puntúan a través de él; lo que
    # no entra en el bloque ni puntúa aparte es informativo (se muestra tenue y rotulado).
    block, members, others = _price_scoring(D)
    multiples = _vs_bench(_VAL_KEYS, vrows, km, bench, na_text=f"No aplica a {D.get('archetype_label')}")
    for it in multiples:
        it["role"] = "block" if it["key"] in members else "scored" if it["key"] in others else "informative"
    barred = {it["key"] for it in multiples if it["state"] == "con_dato"}
    scored = []
    for in_block, group in ((True, members), (False, others)):
        for key, it in group.items():
            if key in barred:
                continue
            r = vrows.get(key) or {}
            scored.append({"key": key, "label": r.get("label") or it.get("metric"), "in_block": in_block,
                           "value_txt": r.get("value") or it.get("value") or None,
                           "reading": r.get("reading") if r.get("reading") not in (None, "—") else None,
                           "tone": r.get("tone") or it.get("tone"), "sign": it.get("sign"), "reason": it.get("reason")})
    valuation = {"fair_value": _fair_value(a, D, price), "multiples": multiples, "block": block, "scored": scored,
                 "dcf_composition": dcf_comp}

    # ── Rentabilidad ──
    prows = _rows(D, "profitability")
    sp_row = prows.get("roic_wacc_spread")
    spread = ({"state": "con_dato", "value": _num(km.get("roic_wacc_spread")), "value_txt": sp_row.get("value"),
               "tone": sp_row.get("tone"), "reading": sp_row.get("reading"), "text": sp_row.get("text")}
              if sp_row and sp_row.get("state") == "con_dato" and _num(km.get("roic_wacc_spread")) is not None
              else _na((sp_row or {}).get("state") or ("no_aplica" if "roic_wacc" in na else "sin_dato"),
                       (sp_row or {}).get("text")))
    # Fase 1 (punto 9): ROCE en el bloque visible, junto a ROIC − WACC (y el promedio del ciclo en CYCLICAL). Sin
    # bandas: la lectura es la comparación con el ROIC.
    ro_row, ra_row = prows.get("roce"), prows.get("roce_avg")
    if km.get("roce_state") == "ok" and ro_row and ro_row.get("state") == "con_dato":
        roce = {"state": "con_dato", "value_txt": ro_row.get("value"), "label": "ROCE",
                "basis": "EBIT / capital empleado, antes de impuestos",
                "avg": ({"label": "ROCE promedio del ciclo", "value_txt": ra_row.get("value"),
                         "years": km.get("roce_years"), "incomplete": bool(km.get("roce_cycle_incomplete"))}
                        if ra_row else None),
                "text": D["sections"]["profitability"].get("roce_reading")}
    else:
        roce = _na(km.get("roce_state") or "sin_dato", km.get("roce_reason"))
    rev = _num(km.get("revenue"))
    steps = []
    for key, label in (("gross_margin", "Margen bruto"), ("ebitda_margin", "Margen EBITDA"),
                       ("operating_margin", "Margen operativo"), ("net_margin", "Margen neto")):
        r = prows.get(key)
        na_step = (archetype == "FINANCIAL" and key in ("gross_margin", "ebitda_margin", "operating_margin")) or \
            (r is not None and r.get("state") == "no_aplica") or (key in na)
        m = _num(km.get(key))
        if na_step:
            steps.append({"key": key, "label": label, "state": "no_aplica",
                          "text": (r or {}).get("text") or f"No aplica a {D.get('archetype_label')}"})
        elif m is None:
            steps.append({"key": key, "label": label, "state": "sin_dato", "text": None})
        else:
            steps.append({"key": key, "label": label, "state": "con_dato", "pct": m, "pct_txt": _pct(m),
                          "amount": (rev * m) if rev else None,
                          "amount_txt": numfmt.money(rev * m) if rev else None, "tone": (r or {}).get("tone"),
                          "reading": (r or {}).get("reading")})
    profitability = {"returns": _vs_bench(_RET_KEYS, prows, km, bench, na_text=f"No aplica a {D.get('archetype_label')}"),
                     "margins": _vs_bench(_MARGIN_KEYS, prows, km, bench, na_text=f"No aplica a {D.get('archetype_label')}"), "spread": spread,
                     "roce": roce,
                     "margin_ladder": {"revenue": rev, "revenue_txt": numfmt.money(rev) if rev else None,
                                       "steps": steps}}

    # ── Solidez: medidores con las zonas de los lectores ──
    srows = _rows(D, "solvency")
    utility, reit = archetype == "UTILITY", archetype == "REIT"
    gauges = []
    cr = _num(km.get("current_ratio"))
    cb = _SOL["current_bounds"]
    gauges.append(_gauge("current_ratio", "Current ratio", cr, srows.get("current_ratio", {}).get("value"),
                         zones_desc(cb, *_CURRENT, top=cb[0] * 1.5), srows.get("current_ratio"), cb[0] * 1.5, archetype=archetype))
    ic = _num(km.get("interest_coverage"))
    icb = _SOL["utility_coverage_bounds"] if utility else _SOL["coverage_bounds"]
    gauges.append(_gauge("interest_coverage", "Cobertura de intereses", ic,
                         srows.get("interest_coverage", {}).get("value"),
                         zones_desc(icb, *(_COVERAGE_UTILITY if utility else _COVERAGE), top=icb[0] * 1.5),
                         srows.get("interest_coverage"), icb[0] * 1.5, archetype=archetype))
    nde = _num(km.get("net_debt_to_ebitda"))
    ndb = (_SOL["utility_nde_bounds"] if utility else _SOL["reit_nde_bounds"] if reit else _PDF["nde_bounds"])
    ndl = _NDE_BRANCH if (utility or reit) else _NDE
    g = _gauge("net_debt_to_ebitda", "Deuda neta / EBITDA", nde, srows.get("net_debt_to_ebitda", {}).get("value"),
               zones_asc(ndb, *ndl, top=ndb[-1] * 1.4), srows.get("net_debt_to_ebitda"), ndb[-1] * 1.4, archetype=archetype)
    if g["state"] == "con_dato" and nde is not None and nde < 0:
        g["net_cash"] = True
    gauges.append(g)
    de = _num(km.get("de"))
    if de_mode == "score":
        t, m = th.debt_equity_high, _SOL["de_mults"]
        deb = [t * m[0], t, t * m[1], t * m[2]]
        gauges.append(_gauge("de", "Deuda / Equity", de, srows.get("de", {}).get("value"),
                             zones_asc(deb, *_DE, top=deb[-1] * 1.4), srows.get("de"), deb[-1] * 1.4, archetype=archetype))
    else:
        r = srows.get("de") or {}
        gauges.append({"key": "de", "label": "Deuda / Equity",
                       "state": {"informativo": "con_dato"}.get(de_mode, r.get("state") or "no_aplica"),
                       "text": r.get("text") or r.get("reading"),
                       **({"value": de, "value_txt": r.get("value"), "informative": True, "tone": 'neu',
                           "reading": r.get("reading")} if de_mode == "informativo" and de is not None else {})})
    rw = a.get("archetype_metrics", {}).get("runway") if archetype == "GROWTH_PRE_PROFIT" else None
    runway = None
    if archetype == "GROWTH_PRE_PROFIT":
        rr = srows.get("runway") or {}
        if rw and rw.get("state") == "runway" and rw.get("years") is not None:
            rb = _SOL["runway_bounds"]
            runway = {"state": "con_dato", "years": rw["years"], "years_txt": f"{rw['years']:.1f} años",
                      "axis_max": rb[0] * 1.5,
                      "zones": zones_desc(rb, *_RUNWAY, top=rb[0] * 1.5), "reading": rr.get("reading"),
                      "tone": rr.get("tone"), "text": rr.get("text")}
        elif rw and rw.get("state") == "autofinanciada":
            runway = {"state": "con_dato", "self_funded": True, "reading": rr.get("reading"), "tone": rr.get("tone"),
                      "text": rr.get("text")}
        else:
            runway = _na("sin_dato", (rw or {}).get("reason"))
    ta, eq, debt, cash = (_num(km.get(k)) for k in ("total_assets", "total_equity", "total_debt", "cash"))
    structure = None
    if ta and ta > 0:
        structure = {"state": "con_dato", "assets": ta, "debt": debt, "equity": eq, "cash": cash,
                     "net_debt": _num(km.get("net_debt")),
                     "debt_pct": (debt / ta * 100) if debt is not None else None,
                     "equity_pct": (eq / ta * 100) if eq is not None else None,
                     "cash_pct": (cash / ta * 100) if cash is not None else None,
                     **{f"{k}_txt": numfmt.money(v) if v is not None else None
                        for k, v in (("assets", ta), ("debt", debt), ("equity", eq), ("cash", cash),
                                     ("net_debt", _num(km.get("net_debt"))))}}
    solvency = {"gauges": gauges, "runway": runway, "structure": structure or _na("sin_dato", None)}

    # ── Crecimiento: CAGR que puntúan (con su tono del desglose) ──
    graw = _growth_raw(a)
    growth = []
    for key, label, adj, nak in (("revenue", "Ingresos" if archetype != "REIT" else "Retorno total por acción",
                                  graw["revenue"], None),
                                 ("eps", "BPA", graw["eps"], "eps_growth"), ("fcf", "FCF", graw["fcf"], "fcf_growth")):
        if nak and nak in na:
            growth.append({"key": key, "label": label, "state": "no_aplica",
                           "text": f"No aplica a {D.get('archetype_label')}"})
        elif adj is not None and adj.get("raw") is None and adj.get("severity") == "severe":
            # Negativo en todos los ejercicios: no hay tasa, pero puntúa en el peor tramo (señal, no hueco).
            growth.append({"key": key, "label": label, "state": "con_dato", "sustained_negative": True,
                           "value_txt": adj.get("value"), "tone": _SEV_TONE["severe"], "reading": adj.get("reason")})
        elif adj is None or adj.get("raw") is None:
            growth.append({"key": key, "label": label, "state": "sin_dato", "text": (adj or {}).get("reason")})
        else:
            growth.append({"key": key, "label": label, "state": "con_dato", "value": adj["raw"],
                           "value_txt": _pct(adj["raw"]),
                           "tone": _SEV_TONE.get(adj.get("severity"), 'neu'), "reading": adj.get("reason")})

    # ── Flujo de resultados (TTM): cifras y % de los ingresos; tono solo por signo ──
    flows = []
    fin = archetype == "FINANCIAL"
    for key, label, kmk in (("revenue", "Ingresos", "revenue"), ("ebitda", "EBITDA", "ebitda"),
                            ("operating_income", "Resultado operativo", "operating_income"),
                            ("net_income", "Beneficio neto", "net_income"), ("fcf", "Flujo de caja libre",
                                                                             "free_cash_flow")):
        if (fin and key in ("ebitda", "operating_income", "fcf")) or (key == "fcf" and "fcf" in na):
            flows.append({"key": key, "label": label, "state": "no_aplica",
                          "text": f"No aplica a {D.get('archetype_label')}"})
            continue
        v = _num(km.get(kmk))
        flows.append({"key": key, "label": label, "state": "con_dato" if v is not None else "sin_dato",
                      "amount": v, "amount_txt": numfmt.money(v) if v is not None else None,
                      "pct_of_revenue": (v / rev * 100) if (v is not None and rev) else None,
                      "pct_txt": f"{numfmt.MINUS if v < 0 else ''}{abs(v / rev * 100):.1f}%" if (
                          v is not None and rev) else None,
                      "sign": None if v is None else ("pos" if v >= 0 else "neg")})

    # ── Histórico: CAGR de cada serie para anotarlo sobre sus barras (cronológico) ──
    yrs = sorted(a.get("yearly_financials") or [], key=lambda r: r.get("year") or 0)
    hist_na = D["sections"]["historical"].get("not_applicable") or {}
    sbc = any("fcf_minus_sbc" in r for r in yrs)
    series = []
    for key, label in (("revenue", "Ingresos"), ("net_income", "Beneficio neto"),
                       ("fcf_minus_sbc", "FCF − SBC") if sbc else ("free_cash_flow", "Flujo de caja libre")):
        vals = [_num(r.get(key)) for r in yrs]
        if hist_na.get(key) and all(v is None for v in vals):
            series.append({"key": key, "label": label, "state": "no_aplica", "text": hist_na[key]})
            continue
        pts, prev = [], None
        for r, v in zip(yrs, vals):
            yoy = ((v - prev) / abs(prev) * 100) if (v is not None and prev) else None
            pts.append({"year": r.get("year"), "value": v, "value_txt": numfmt.money(v) if v is not None else "—",
                        "yoy_pct": yoy, "yoy_txt": numfmt.signed_pct(yoy, 1) if yoy is not None else None})
            prev = v
        cg = _cagr_series(vals)
        series.append({"key": key, "label": label,
                       "state": "con_dato" if any(v is not None for v in vals) else "sin_dato",
                       "cagr": cg, "cagr_txt": _pct(cg), "points": pts})
    historical = {"years": len(yrs), "series": series}

    # ── Evaluación institucional: Altman con las zonas de su modelo ──
    al = a.get("altman_z") or {}
    if al.get("applicable") is False or "altman" in na:
        altman = _na("no_aplica", al.get("interpretation"))
    elif _num(al.get("z_score")) is None:
        altman = _na("sin_dato", al.get("interpretation"))
    else:
        A = cfg("valuation.models.altman")
        nonm = "No Manufactura" in (al.get("model") or "") or "Z''" in (al.get("model") or "")
        grey, safe = (A["non_manufacturing_grey"], A["non_manufacturing_safe"]) if nonm else (
            A["original_grey"], A["original_safe"])
        z = _num(al["z_score"])
        top = max(safe * 2, z * 1.1)
        altman = {"state": "con_dato", "value": z, "value_txt": f"{z:.2f}", "model": al.get("model"), "axis_max": top,
                  "zones": [{"from": 0.0, "to": grey, "label": _ALTMAN[0][0], "tone": _ALTMAN[1][0]},
                            {"from": grey, "to": safe, "label": _ALTMAN[0][1], "tone": _ALTMAN[1][1]},
                            {"from": safe, "to": top, "label": _ALTMAN[0][2], "tone": _ALTMAN[1][2]}],
                  "zone": {"safe": _ALTMAN[0][2], "grey": _ALTMAN[0][1], "distress": _ALTMAN[0][0]}.get(al.get("zone")),
                  "text": al.get("interpretation")}

    return {"version": 1, "price_card": price_card, "valuation": valuation, "profitability": profitability,
            "solvency": solvency, "growth": growth, "results_flow": flows, "historical": historical,
            "institutional": {"altman": altman}, "comparison": comparison(a, D, bench, market)}


# ══════════════════ Comparativa con el sector (pestaña propia) ══════════════════
# Solo métricas que aplican al arquetipo y tienen referencia; la lectura es la misma de
# las tablas (read_vs_sector, bandas vs_sector_bounds). "Mejor" = tono pos.
_CMP = (
    ("Valoración", (("pe", "P/E (TTM)", False, "mult", "pe"), ("forward_pe", "Forward P/E", False, "mult", "forward_pe"),
                    ("pb", "P/B", False, "mult", None), ("peg", "PEG", False, "mult", "peg"),
                    ("ev_ebitda", "EV/EBITDA", False, "mult", "ev_ebitda"), ("pfcf", "P/FCF", False, "mult", "p_fcf"),
                    ("fcf_yield", "FCF yield", True, "pct", "p_fcf"))),
    ("Rentabilidad", (("roe", "ROE", True, "pct", "roe"), ("roa", "ROA", True, "pct", "roa"),
                      ("roic", "ROIC", True, "pct", "roic_wacc"), ("gross_margin", "Margen bruto", True, "pct",
                                                                  "gross_margin"),
                      ("operating_margin", "Margen operativo", True, "pct", "operating_margin"),
                      ("net_margin", "Margen neto", True, "pct", "net_margin"))),
    ("Solidez", (("current_ratio", "Current ratio", True, "mult", "current_ratio"),
                 ("de", "Deuda / Equity", False, "mult", "de"),
                 ("interest_coverage", "Cobertura de intereses", True, "mult", "interest_coverage"))),
    ("Crecimiento", (("revenue_growth", "Crecimiento de ingresos (3 años)", True, "pct", None),
                     ("earnings_growth", "Crecimiento del BPA (3 años)", True, "pct", "eps_growth"))),
)


def comparison(a, D, bench, market) -> Dict[str, Any]:
    from display import read_vs_sector
    km = a.get("key_metrics") or {}
    na = set(D.get("na_keys") or [])
    rows_all = {}
    for sec in ("valuation", "profitability", "solvency", "growth"):
        rows_all.update(_rows(D, sec))
    graw = _growth_raw(a)
    gvals = {"revenue_growth": (graw["revenue"] or {}).get("raw") if D.get("archetype") != "REIT" else None,
             "earnings_growth": (graw["eps"] or {}).get("raw")}
    ref = "del mercado" if market else "del sector"
    # Fase 1 (#20): en CYCLICAL la cifra que puntúa es de ciclo medio, no una CAGR a 3 años.
    per = "(ciclo medio)" if D.get("archetype") == "CYCLICAL" else "(3 años)"
    groups, better, total = [], 0, 0
    for title, keys in _CMP:
        items = []
        for key, label, higher, fmt, nak in keys:
            label = label.replace("(3 años)", per).replace("P/E (TTM)", D.get("pe_label") or "P/E (TTM)")
            if (nak and nak in na) or (key in rows_all and rows_all[key].get("state") != "con_dato"):
                continue
            v = gvals[key] if key in gvals else _num(km.get(key))
            b = _num(bench.get(key))
            if v is None or not b:
                continue
            r = read_vs_sector(label, v, b, higher, fmt, ref=ref)
            if not r:
                continue
            lab, tone, text, gap = r
            items.append({"key": key, "label": label, "fmt": fmt, "value": v, "bench": b,
                          "value_txt": _fmt(v, fmt), "bench_txt": _fmt(b, fmt),
                          "gap_pct": (v - b) / abs(b) * 100, "gap_txt": gap, "higher_is_better": higher,
                          "reading": lab, "tone": tone, "text": text})
            total += 1
            better += tone == 'pos'
        if items:
            groups.append({"title": title, "items": items})
    vs = D["sections"]["valuation"]
    return {"groups": groups, "better": better, "total": total,
            "ref": "mercado (S&P 500)" if market else "sector",
            "note": vs.get("provisional_note") or "Medianas de referencia provisionales (fijadas a mano).",
            "market_note": vs.get("market_note")}
