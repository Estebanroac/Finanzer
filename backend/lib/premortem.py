"""
Pre-mortem del informe (fase 4, T3; PLAN_FIABILIDAD §4.3): "Esta lectura sería errónea si…".

Dos o tres condiciones, derivadas de los datos que sostienen el veredicto, que lo invalidarían. No son previsiones
ni recomendaciones: dicen qué tendría que pasar para que la lectura de hoy fuera la equivocada, con la cifra que lo
mide.

  · **Precio** (el método intrínseco del veredicto):
      - DCF inverso: con precio exigente, la lectura falla si la empresa SÍ sostiene el crecimiento que exige el
        precio; con precio razonable o atractivo, si crece menos de lo que ya descuenta. Con la historia propia al lado.
      - ROTE/ROE implícito (bancos, aseguradoras, utilities): lo mismo con la rentabilidad que descuenta el precio.
  · **Calidad** (excelente o sólida): el margen operativo de hoy por encima de su mediana de los últimos ejercicios
    (o de la de ciclo medio en una cíclica) en más de `margin_gap_rel`: la lectura falla si el margen vuelve a ella.
  · **Deuda**: deuda neta / EBITDA en el tramo "elevada" de la lectura y de las alertas (el `net_debt_ebitda_high` del
    sector; en utilities y REIT, por encima de su banda "en línea", porque se financian con deuda por diseño): la
    lectura falla si el EBITDA cae o la deuda se refinancia más cara.
Como mucho `max_items`, en ese orden.
"""
from statistics import median
from typing import Any, Dict, List, Optional

from settings import cfg

DEMANDING = ("exigente", "muy exigente")


def _cfg(k: str):
    return cfg(f"thresholds.premortem.{k}")


def _pct(x: float) -> str:
    return f"{x * 100:.1f}%".replace("-", "−")


def _price_item(a: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    level = (a.get("price_attractiveness") or {}).get("level")
    if not level:
        return None
    demanding = level in DEMANDING
    m = ((a.get("reverse_dcf") or {}).get("main")) or {}
    own = m.get("own_growth") or {}
    flow = m.get("flow_label") or "flujo"
    hist = (f"; historia propia: {own.get('label') or 'su crecimiento'}, {_pct(own['cagr'])} anual en "
            f"{own.get('years')} años") if own.get("cagr") is not None and own.get("years") else ""
    if m.get("state") == "fuera_de_rango" and m.get("side") in ("superior", "inferior"):
        lo, hi = cfg("valuation.reverse_dcf.growth_bounds")
        if m["side"] == "superior":
            t = (f"el {flow} por acción creciera más de un {_pct(hi)} anual durante los 5 primeros años, como exige el "
                 "precio")
            return {"kind": "precio_inverso", "text": t + hist, "field": "reverse_dcf.main.side", "value": "superior"}
        t = f"el {flow} por acción cayera más de un {_pct(-lo)} anual, lo que ya descuenta el precio"
        return {"kind": "precio_inverso", "text": t + hist, "field": "reverse_dcf.main.side", "value": "inferior"}
    if m.get("state") == "ok" and m.get("g10") is not None:
        g = m["g10"]
        if demanding:
            t = f"el {flow} por acción creciera al menos un {_pct(g)} anual durante 10 años, como exige el precio"
        elif g < 0:
            t = (f"el {flow} por acción cayera más de un {_pct(-g)} anual durante 10 años, lo que ya descuenta el "
                 "precio")
        else:
            t = f"el {flow} por acción creciera menos del {_pct(g)} anual durante 10 años que ya descuenta el precio"
        return {"kind": "precio_inverso", "text": t + hist, "field": "reverse_dcf.main.g10", "value": g}
    imp = (a.get("archetype_metrics") or {}).get("implied") or {}
    if imp.get("implied") is not None and imp.get("own") is not None:
        met = imp.get("metric") or "ROE"
        if demanding:
            t = (f"la entidad sostuviera un {met} de al menos el {_pct(imp['implied'])} que descuenta el precio "
                 f"(obtiene un {_pct(imp['own'])})")
        else:
            t = (f"el {met} sostenido bajara del {_pct(imp['implied'])} que descuenta el precio "
                 f"(obtiene un {_pct(imp['own'])})")
        return {"kind": "precio_implicito", "text": t, "field": "archetype_metrics.implied.implied",
                "value": imp["implied"]}
    return None


def margin_reference(hist: Optional[Dict[str, Any]], mid_cycle: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Margen operativo de referencia: el de ciclo medio (cíclica) o la mediana de los últimos `margin_years`."""
    if mid_cycle and mid_cycle.get("op_margin_mid_cycle") is not None:
        return {"value": mid_cycle["op_margin_mid_cycle"],
                "label": f"media de ciclo medio de {mid_cycle['from'][:4]}–{mid_cycle['to'][:4]}"}
    from cyclicality import _align, _series
    pts = _align(_series(hist or {}, "operating_income"), _series(hist or {}, "revenue"))
    ms = [oi / rv for _e, oi, rv in pts if rv][-int(_cfg("margin_years")):]
    if len(ms) < _cfg("min_margin_years"):
        return None
    return {"value": median(ms), "label": f"mediana de {len(ms)} ejercicios"}


def _margin_item(a: Dict[str, Any], ref: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    q = (a.get("quality") or {}).get("level")
    cur = (a.get("key_metrics") or {}).get("operating_margin")
    arch = (a.get("classification") or {}).get("archetype")
    if q not in ("excelente", "sólida") or cur is None or cur <= 0 or not ref or arch == "FINANCIAL":
        return None
    if ref["value"] <= 0 or cur < ref["value"] * (1 + _cfg("margin_gap_rel")):
        return None
    return {"kind": "margen", "field": "key_metrics.operating_margin", "value": cur,
            "text": (f"el margen operativo volviera a su {ref['label']} ({_pct(ref['value'])} frente al "
                     f"{_pct(cur)} de hoy)")}


def _debt_item(a: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    arch = (a.get("classification") or {}).get("archetype")
    x = (a.get("key_metrics") or {}).get("net_debt_to_ebitda")
    if x is None or arch == "FINANCIAL":
        return None
    if arch in ("UTILITY", "REIT"):
        hi = cfg(f"thresholds.score.solidez.{'utility' if arch == 'UTILITY' else 'reit'}_nde_bounds")[2]
    else:
        from financial_ratios import SECTOR_THRESHOLDS, ThresholdConfig
        # La misma clave que la lectura (display): la del benchmark (sector o "market"), o el sector.
        key = ((a.get("benchmark") or {}).get("thresholds_key") or (a.get("sector_info") or {}).get("mapped_sector")
               or "default")
        hi = SECTOR_THRESHOLDS.get(key, ThresholdConfig()).net_debt_ebitda_high
    if x <= hi:
        return None
    t = f"el EBITDA cayera o la deuda se refinanciara más cara: la deuda neta equivale a {x:.1f} veces el EBITDA"
    if ((a.get("data_provenance") or {}).get("debt") or {}).get("captive_unseparable"):
        # T7 de la fase 3 (DE): la deuda de la financiera cautiva no se puede separar y está dentro.
        t += " (incluye la de la financiera cautiva, que no se puede separar: la de la actividad industrial es menor)"
    return {"kind": "deuda", "field": "key_metrics.net_debt_to_ebitda", "value": x, "text": t}


def build(a: Dict[str, Any], hist: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    items: List[Dict[str, Any]] = [x for x in (_price_item(a), _margin_item(a, margin_reference(
        hist, a.get("mid_cycle"))), _debt_item(a)) if x]
    items = items[:int(_cfg("max_items"))]
    if not items:
        return None
    return {"title": "Esta lectura sería errónea si…", "items": items}
