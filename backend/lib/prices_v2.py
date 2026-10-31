"""Rediseño /v2: serializa para la web la serie diaria (price_history) y sus eventos.

No calcula nada de análisis. Cada punto lleva la fecha, el cierre sin ajustar por dividendos (`c`, rentabilidad de
precio), el ajustado (`a`, rentabilidad total con dividendos) y el volumen (E2a, T9). Eventos de la serie: dividendos y
splits declarados; los resultados salen de los 8-K del apartado 2.02 de SEC EDGAR (earnings_events)."""
from typing import Any, Dict, List, Optional, Tuple


def _num(x) -> Optional[float]:
    return None if x is None or x != x else float(x)


def _split_label(r: float) -> str:
    """Split 4:1, 3:2 o contrasplit 1:10; un factor que no es una proporción simple (una escisión que Yahoo ajusta
    como split: O en 2021, 1.032) es un ajuste de capital."""
    from fractions import Fraction
    f = Fraction(r).limit_denominator(10)
    if abs(float(f) - r) > 1e-6:
        return f"Ajuste de capital (factor {r:g})"
    return f"Split {f.numerator}:{f.denominator}" if r >= 1 else f"Contrasplit {f.numerator}:{f.denominator}"


def serialize(res: Optional[Dict[str, Any]], symbol: Optional[str]) -> Dict[str, Any]:
    fr = (res or {}).get("frame")
    if fr is None or len(fr) == 0:
        return {"symbol": symbol, "status": "sin_dato", "reason": (res or {}).get("reason") or "sin serie",
                "points": [], "events": []}
    points = []
    for ts, c, a, v in zip(fr.index, fr["close"], fr["adj_close"], fr["volume"]):
        c, a = _num(c), _num(a)
        if c is None and a is None:
            continue
        points.append({"t": ts.strftime("%Y-%m-%d"), "c": c if c is not None else a, "a": a if a is not None else c,
                       "v": _num(v)})
    events = []
    for ts in fr.index:
        d = _num(fr["dividend"].get(ts)) if "dividend" in fr else None
        if d:
            events.append({"t": ts.strftime("%Y-%m-%d"), "kind": "dividend", "value": d,
                           "label": f"Dividendo: {d:g} por acción"})
        sp = _num(fr["split"].get(ts)) if "split" in fr else None
        if sp:
            events.append({"t": ts.strftime("%Y-%m-%d"), "kind": "split", "value": sp, "label": _split_label(sp)})
    return {"symbol": symbol or (res or {}).get("symbol"), "status": "ok", "points": points, "events": events}


def with_total_return(market: Dict[str, Any], total: Dict[str, Any], total_symbol: str) -> Dict[str, Any]:
    """V7 (M7): el índice (^GSPC) no reparte dividendos: su cierre ajustado es el de precio y la columna «con
    dividendos» repetía la de precio. El `a` de cada punto pasa a ser la rentabilidad total de `total` (el cierre
    ajustado de SPY, en config), en la escala del índice desde su primera sesión; `c` sigue siendo el índice. Sin esa
    serie, `total_status` "sin_dato" y el motivo: la web dice «Sin dato», nunca la de precio con otra etiqueta."""
    if market.get("status") != "ok":
        return market
    out = dict(market)
    if (market.get("symbol") or "").upper() == total_symbol.upper():   # ya es el ETF (respaldo del índice)
        return dict(out, total_status="ok", total_symbol=total_symbol,
                    total_note=f"cierre ajustado de {total_symbol}, el ETF que replica el índice")
    if total.get("status") != "ok" or not total.get("points"):
        return dict(out, total_status="sin_dato", total_symbol=total_symbol,
                    total_note=f"sin la serie con dividendos ({total.get('reason') or 'sin serie'})")
    tr = {p["t"]: p["a"] for p in total["points"]}
    days = sorted(tr)
    pts, j, last = [], 0, None
    base_c = base_a = None
    for p in market["points"]:
        while j < len(days) and days[j] <= p["t"]:
            last = tr[days[j]]
            j += 1
        ref = last if last is not None else tr[days[0]]
        if base_c is None:
            base_c, base_a = p["c"], ref
        pts.append(dict(p, a=base_c * ref / base_a))
    return dict(out, points=pts, total_status="ok", total_symbol=total_symbol,
                total_note=(f"rentabilidad total de {total_symbol}, el ETF que replica el índice (cierre ajustado por "
                            "dividendos); el índice solo mide el precio"))


def source_text(company: Dict[str, Any], period: str) -> Optional[str]:
    """V7 (M7): de dónde sale la serie de la gráfica y de las rentabilidades, con su periodo real."""
    pts = company.get("points") or []
    if not pts:
        return None
    yrs = period[:-1] if period.endswith("y") else period
    return (f"Serie diaria de Yahoo Finance de {yrs} años (del {pts[0]['t']} al {pts[-1]['t']}): cierre sin ajustar "
            "para la rentabilidad de precio y cierre ajustado por dividendos y splits para la rentabilidad con "
            "dividendos.")


def earnings_events_from(filings: Optional[List[Dict[str, Any]]], first: Optional[str]) -> List[Dict[str, Any]]:
    """Fechas de publicación de resultados: los 8-K con el apartado 2.02 (Results of Operations), desde `first`."""
    dates = sorted({f["filingDate"] for f in (filings or [])
                    if f.get("form") == "8-K" and "2.02" in (f.get("items") or "") and (not first or f["filingDate"] >= first)})
    return [{"t": d, "kind": "earnings", "value": None, "label": "Resultados (8-K)"} for d in dates]


def earnings_events(symbol: str, first: Optional[str] = None) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """Resultados del emisor en EDGAR con un presupuesto propio (nunca bloquea): (eventos, motivo si faltan)."""
    import sec_edgar
    from settings import cfg
    st = sec_edgar.status()
    if not st["enabled"]:
        return [], st["reason"]
    try:
        b = sec_edgar.Budget()
        ent = sec_edgar.cik_for(symbol, b)
        if ent is None:
            return [], "el emisor no presenta en la SEC: sin fechas de resultados oficiales"
        ev = earnings_events_from(sec_edgar.submissions(ent["cik"], b)["filings"], first)
    except Exception as e:  # EDGAR lento o caído: la gráfica sale sin las marcas de resultados y lo dice
        # Verificación de la v4 (V3): el motivo de EDGAR (sin User-Agent, presupuesto agotado, no respondió a tiempo)
        # y no el nombre de la excepción ("(Unavailable)").
        msg = str(e).strip()
        return [], (f"sin marcas de resultados: {msg}" if msg else f"EDGAR no respondió ({type(e).__name__})")
    since = cfg("data.edgar.since")
    if not ev:
        return [], "sin 8-K de resultados (apartado 2.02) en EDGAR: el emisor presenta 20-F/6-K"
    return ev, (f"resultados desde {since} (filings que se leen de EDGAR)" if first and first < since else None)
