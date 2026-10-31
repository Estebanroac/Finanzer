"""
Lecturas de calidad que entienden el modelo de negocio (fase 3, T6; F3_DISENO §5 y el backlog aprobado).

Informan, no puntúan (el score no cambia): cada una devuelve sus cifras y una frase que pasa por el guardián.
  · **DuPont del ROE**: margen neto × rotación de activos × apalancamiento, y qué factor explica el cambio frente al
    primer ejercicio de la ventana.
  · **Margen FCF con tendencia**: FCF − SBC sobre ingresos de cada ejercicio (el FCF si no hay SBC, dicho);
    mejora / estable / empeora por el cambio entre el primero y el último.
  · **Regla de 40** (GROWTH_PROFITABLE, §1.3): crecimiento de ingresos a 3 años + margen FCF − SBC.
  · **SBC como coste real** (§5): con SBC > `sbc_material` de los ingresos, cuánto baja el margen FCF al restarla.
  · **Cobertura de intereses** (petición del usuario, mapa T6): con EBITDA además de EBIT, su tendencia por
    ejercicio, y los intereses PAGADOS del estado de flujos cuando el gasto por intereses no se presenta. En REIT,
    además, con FFO: (FFO + intereses) / intereses, la cobertura que usan las agencias de rating para inmobiliarias
    (el FFO se calcula después de intereses; se suman para medir lo que hay antes de pagarlos).
Series anuales de los estados (más reciente primero), en la moneda de los estados.
"""
import math
from typing import Any, Dict, List, Optional

from historical_metrics import on_statement
from settings import cfg


def _pct(x: float) -> str:
    return f"{x * 100:.1f}%".replace("-", "−")


def _ok(*xs) -> bool:
    return all(x is not None for x in xs)


def _first_last(vals: List[Optional[float]]):
    idx = [i for i, v in enumerate(vals) if v is not None]
    return (idx[0], idx[-1]) if len(idx) >= 2 else (None, None)


def dupont(st: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    yrs = st.get("inc_years") or []
    ni, rev = st.get("net_income") or [], st.get("revenue") or []
    ta = on_statement(st, "total_assets", "bs", "inc")
    eq = on_statement(st, "stockholders_equity", "bs", "inc")
    rows = []
    for i in range(min(len(ni), len(rev), len(ta), len(eq))):
        if _ok(ni[i], rev[i], ta[i], eq[i]) and rev[i] > 0 and ta[i] > 0 and eq[i] > 0:
            rows.append({"i": i, "fy": yrs[i] if i < len(yrs) else None, "margin": ni[i] / rev[i],
                         "turnover": rev[i] / ta[i], "leverage": ta[i] / eq[i], "roe": ni[i] / eq[i]})
        else:
            rows.append(None)
    cur = rows[0] if rows else None
    if not cur:
        return None
    old = next((r for r in reversed(rows[1:]) if r), None)
    out = {"current": cur, "prior": old, "driver": None}
    if old and cur["roe"] > 0 and old["roe"] > 0 and cur["margin"] > 0 and old["margin"] > 0:
        ch = {k: math.log(cur[k] / old[k]) for k in ("margin", "turnover", "leverage")}
        out["driver"] = max(ch, key=lambda k: abs(ch[k]))
        out["changes"] = ch
    out["text"] = dupont_text(out)
    return out


_DRIVER = {"margin": "el margen neto", "turnover": "la rotación de activos", "leverage": "el apalancamiento"}


def dupont_text(d: Dict[str, Any]) -> str:
    c = d["current"]
    # V7 (M2): el DuPont es del último ejercicio de los estados, no TTM: lo dice junto a la cifra.
    fy = f" de FY{c['fy']}" if c.get("fy") else ""
    t = (f"ROE{fy}: {_pct(c['roe'])} = margen neto {_pct(c['margin'])} × rotación de activos {c['turnover']:.2f} × "
         f"apalancamiento {c['leverage']:.2f}")
    if d.get("prior") and d.get("driver"):
        p = d["prior"]
        t += f"; frente a FY{p['fy']} (ROE {_pct(p['roe'])}), el cambio lo explica sobre todo {_DRIVER[d['driver']]}"
    return t + "."


def fcf_margin_trend(st: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    yrs = st.get("cf_years") or []
    fcf, sbc = st.get("free_cash_flow") or [], st.get("stock_based_compensation") or []
    rev = on_statement(st, "revenue", "inc", "cf")
    use_sbc = bool(sbc) and all(s is not None for s, f in zip(sbc, fcf) if f is not None)
    m = []
    for i in range(min(len(fcf), len(rev))):
        f, r = fcf[i], rev[i]
        s = sbc[i] if (use_sbc and i < len(sbc)) else 0.0
        m.append(((f - s) / r) if _ok(f, r) and r > 0 and s is not None else None)
    a, b = _first_last(m)
    if a is None:
        return None
    delta = m[a] - m[b]
    thr = cfg("thresholds.quality_readings.fcf_margin_trend_pp")
    direction = "mejora" if delta > thr else "empeora" if delta < -thr else "estable"
    label = "margen FCF − SBC" if use_sbc else "margen FCF (sin dato de SBC)"
    out = {"basis": label, "series": m, "years": [yrs[i] if i < len(yrs) else None for i in range(len(m))],
           "latest": m[a], "oldest": m[b], "change": delta, "direction": direction}
    fy0 = out["years"][a]
    fy1 = out["years"][b]
    out["text"] = (f"El {label} es del {_pct(m[a])} en FY{fy0}, frente al {_pct(m[b])} en FY{fy1}: "
                   f"{direction} ({'+' if delta >= 0 else '−'}{abs(delta) * 100:.1f} pp).")
    return out


def rule_of_40(revenue_cagr_3y: Optional[float], fcf_sbc_margin: Optional[float], *, per_share: bool = False,
               window: Optional[str] = None, margin_basis: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """V7 (M2): cada sumando con su periodo (crecimiento anual de la ventana de 3 años; margen TTM o del ejercicio)."""
    if not _ok(revenue_cagr_3y, fcf_sbc_margin):
        return None
    g_lab = "crecimiento de ingresos por acción" if per_share else "crecimiento de ingresos"
    g_per = f" (anual, {window})" if window else " (anual, 3 años)"
    m_per = f" ({margin_basis})" if margin_basis else ""
    v = revenue_cagr_3y + fcf_sbc_margin
    bar = cfg("thresholds.quality_readings.rule_of_40")
    return {"value": v, "growth": revenue_cagr_3y, "margin": fcf_sbc_margin, "meets": v >= bar,
            "text": (f"Regla de 40: {g_lab} {_pct(revenue_cagr_3y)}{g_per} + margen FCF − SBC "
                     f"{_pct(fcf_sbc_margin)}{m_per} = {v * 100:.0f} ("
                     + ("por encima" if v >= bar else "por debajo") + f" del listón de {bar * 100:.0f}).")}


def sbc_cost(sbc: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    r = (sbc or {}).get("sbc_to_revenue")
    if r is None or r < cfg("thresholds.quality_readings.sbc_material"):
        return None
    raw, adj = sbc.get("fcf_margin_raw"), sbc.get("fcf_margin_adjusted")
    if not _ok(raw, adj):
        return None
    per = f" ({sbc['basis']})" if sbc.get("basis") else ""   # V7 (M2): TTM o FY del ejercicio
    return {"sbc_to_revenue": r, "fcf_margin_raw": raw, "fcf_margin_adjusted": adj,
            "text": (f"La compensación en acciones es el {_pct(r)} de los ingresos{per}: un coste real que se paga "
                     f"en dilución. Al restarla, el margen FCF{per} baja del {_pct(raw)} al {_pct(adj)}; el DCF "
                     "descuenta el FCF − SBC.")}


def interest_coverage(st: Dict[str, Any], ebit_ttm: Optional[float], ebitda_ttm: Optional[float],
                      interest_ttm: Optional[float], ffo_ttm: Optional[float] = None,
                      period: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Cobertura con EBIT y con EBITDA (TTM), con FFO en REIT, su tendencia por ejercicio y el respaldo de los
    intereses pagados."""
    yrs = st.get("inc_years") or []
    ie = st.get("interest_expense") or []
    paid = on_statement(st, "interest_paid", "cf", "inc")
    ebit = st.get("ebit") or st.get("operating_income") or []
    basis = "gasto por intereses"
    i_ttm = abs(interest_ttm) if interest_ttm else None
    paid_fy = None
    if not i_ttm:
        k0 = next((k for k, x in enumerate(paid) if x), None)
        if k0 is not None:
            # V7 (M3): con los intereses pagados la cifra informa, pero el score (que usa el gasto por intereses de
            # la cuenta de resultados) deja la cobertura sin dato: el texto lo reconcilia.
            paid_fy = yrs[k0] if k0 < len(yrs) else None
            i_ttm, basis = abs(paid[k0]), "intereses pagados (estado de flujos del último ejercicio): sin gasto por intereses"
    if not i_ttm:
        return None
    out = {"basis": basis, "ebit": (ebit_ttm / i_ttm) if ebit_ttm is not None else None,
           "ebitda": (ebitda_ttm / i_ttm) if ebitda_ttm is not None else None,
           "ffo": ((ffo_ttm + i_ttm) / i_ttm) if ffo_ttm is not None else None, "trend": None}
    series = []
    for k in range(min(len(ebit), max(len(ie), len(paid)))):
        den = (abs(ie[k]) if k < len(ie) and ie[k] else (abs(paid[k]) if k < len(paid) and paid[k] else None))
        series.append((ebit[k] / den) if (ebit[k] is not None and den) else None)
    a, b = _first_last(series)
    if a is not None and series[a] > 0 and series[b] > 0:
        r = series[a] / series[b]
        thr = cfg("thresholds.quality_readings.coverage_trend_rel")
        out["trend"] = {"latest": series[a], "oldest": series[b], "fy_latest": yrs[a] if a < len(yrs) else None,
                        "fy_oldest": yrs[b] if b < len(yrs) else None,
                        "direction": "mejora" if r > 1 + thr else "empeora" if r < 1 - thr else "estable"}
    parts = []
    top = cfg("thresholds.quality_readings.coverage_display_max")
    per = f" ({period})" if period else ""   # V7 (M2): "TTM" o "último ejercicio"

    def _x(v):   # V7 (M3): "más de 100 veces", no "526930.4 veces"
        return f"más de {top:.0f}" if v > top else f"{v:.1f}"
    # V7 (M3): un EBIT negativo no "cubre −5.0 veces" los intereses: no los cubre.
    if out["ebit"] is not None:
        parts.append(f"el EBIT{per} cubre {_x(out['ebit'])} veces los intereses" if out["ebit"] >= 0 else
                     f"el EBIT{per} es negativo y no cubre los intereses")
    if out["ebitda"] is not None:
        parts.append(f"el EBITDA{per}, {_x(out['ebitda'])} veces" if out["ebitda"] >= 0 else
                     f"el EBITDA{per} también es negativo")
    if out["ffo"] is not None:
        parts.append(f"el FFO más los intereses, {_x(out['ffo'])} veces")
    if paid_fy is None:
        t = ("Cobertura (" + basis + "): " + "; ".join(parts)) if parts else None
    else:
        t = (f"Cobertura con los intereses pagados en FY{paid_fy} (estado de flujos): la cuenta de resultados no "
             "separa el gasto por intereses, así que el score deja la cobertura sin dato y esta cifra solo informa: "
             + "; ".join(parts)) if parts else None
    tr = out["trend"]
    if t and tr:
        t += (f"; con el EBIT de cada ejercicio, de {_x(tr['oldest'])} veces en FY{tr['fy_oldest']} a "
              f"{_x(tr['latest'])} en FY{tr['fy_latest']} ({tr['direction']})")
    out["text"] = (t + ".") if t else None
    return out
