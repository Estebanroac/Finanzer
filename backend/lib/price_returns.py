"""Revisión V6 (F1): rentabilidad por periodo, base 100 y marcas de eventos de la serie de precios, en el backend.

Una sola implementación para la web (/api/v2/prices: `ranges`, `returns` por serie y `chart` por periodo) y el PDF
nuevo (lib/pdf_v2: tabla de rentabilidades y gráfica): las dos enseñan los mismos números. Antes la web los calculaba
en el navegador (por número de sesiones) y el PDF aquí (por días naturales); manda la regla del PDF.

Reglas (config/market.toml [price_returns]):
  - el periodo termina en la última sesión de la empresa (sin ella, la del mercado) y empieza `días` antes (o el 1 de
    enero, en lo que va de año);
  - rentabilidad de una serie: de su primera sesión en o después del inicio a su última sesión hasta el final; de precio
    con el cierre sin ajustar (`c`) y total con el ajustado (`a`, con dividendos);
  - una serie que no cubre el periodo (empieza más de `cover_slack_days` después del inicio) queda sin dato, nunca con
    la cifra de un periodo más corto;
  - la gráfica pasa las series a base 100 en la primera sesión común del periodo; si esa ventana dura menos que el
    periodo (menos `chart_slack_days`), dice desde cuándo empieza.
Solo reescala la serie publicada: ninguna lectura del análisis sale de aquí.
"""
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple

from settings import cfg

ROLES = ("company", "market", "sector")
MINUS = "−"


def ranges() -> List[Dict[str, Any]]:
    """[{key, label, days}] en el orden de la web; days = 0: desde el 1 de enero."""
    keys, labels, days = (cfg(f"market.price_returns.{k}") for k in ("range_keys", "range_labels", "range_days"))
    return [{"key": k, "label": lab, "days": int(d)} for k, lab, d in zip(keys, labels, days)]


def _iso(s) -> date:
    return date.fromisoformat(str(s)[:10])


def _ok(v) -> bool:
    return v is not None and v == v


def points(serie: Optional[Dict[str, Any]], field: str = "a") -> List[Tuple[date, float]]:
    """Puntos (fecha, valor) de una serie de /api/v2/prices: `a` (ajustado) o `c` (sin ajustar), cada uno con el otro
    de respaldo si falta."""
    other = "c" if field == "a" else "a"
    out = []
    for p in (serie or {}).get("points") or []:
        v = p.get(field) if _ok(p.get(field)) else p.get(other)
        if _ok(v):
            out.append((_iso(p["t"]), float(v)))
    return out


def start_of(end: date, days: int) -> date:
    return date(end.year, 1, 1) if days == 0 else end - timedelta(days=days)


def end_of(prices: Optional[Dict[str, Any]]) -> Optional[date]:
    """Fin de todos los periodos: la última sesión de la empresa o, sin su serie, la del mercado."""
    for role in ("company", "market"):
        pts = points((prices or {}).get(role))
        if pts:
            return pts[-1][0]
    return None


def period_return(pts: List[Tuple[date, float]], start: date, end: date) -> Optional[float]:
    """Del primer punto en o después de `start` al último hasta `end`; None si la serie no cubre el periodo."""
    pts = [(d, v) for d, v in pts if d <= end]
    first = next(((d, v) for d, v in pts if d >= start), None)
    slack = timedelta(days=cfg("market.price_returns.cover_slack_days"))
    if not (first and pts and pts[0][0] <= start + slack and first[0] < pts[-1][0] and first[1]):
        return None
    return pts[-1][1] / first[1] - 1


def fmt(x: Optional[float]) -> str:
    """+1.2% / −1.2% / 0.0%; sin dato, "—"."""
    if x is None:
        return "—"
    pct = x * 100
    return f"{'+' if pct > 0 else MINUS if pct < 0 else ''}{abs(pct):.1f}%"


def tone(x: Optional[float]) -> str:
    return "neutral" if x is None or x == 0 else "pos" if x > 0 else "neg"


def returns(prices: Optional[Dict[str, Any]]) -> Dict[str, Dict[str, Dict[str, Any]]]:
    """{rol: {clave: {price, total, price_txt, total_txt, price_tone, tone}}} de cada serie con puntos (`tone` es el de
    la rentabilidad total)."""
    end = end_of(prices)
    out: Dict[str, Dict[str, Dict[str, Any]]] = {}
    if end is None:
        return out
    for role in ROLES:
        serie = (prices or {}).get(role)
        pa, pc = points(serie, "a"), points(serie, "c")
        if not pa:
            continue
        # V7 (M7): el índice no reparte dividendos; sin la serie que los incluye (`total_status` "sin_dato"), la
        # rentabilidad con dividendos es «Sin dato», nunca la de precio con otra etiqueta
        no_total = (serie or {}).get("total_status") == "sin_dato"
        out[role] = {}
        for r in ranges():
            start = start_of(end, r["days"])
            tot = None if no_total else period_return(pa, start, end)
            pri = period_return(pc, start, end)
            out[role][r["key"]] = {"price": pri, "total": tot, "price_txt": fmt(pri), "total_txt": fmt(tot),
                                   "price_tone": tone(pri), "tone": tone(tot)}
    return out


def window(prices: Optional[Dict[str, Any]], days: int) -> Dict[str, Any]:
    """Las series del periodo en base 100 desde la primera sesión común (cierre ajustado). {status, reason, series:
    {rol: [(fecha, base100)]}, returns: {rol: fracción}, start, end, covered, missing}."""
    end = end_of(prices)
    comp = (prices or {}).get("company")
    if end is None or not points(comp) and not points((prices or {}).get("market")):
        reason = (comp or {}).get("reason") or ("sin serie de precios" if prices else "la serie de precios no llegó")
        return {"status": "sin_dato", "reason": reason, "series": {}, "returns": {}, "missing": {}}
    start = start_of(end, days)
    roles, missing = {}, {}
    for role in ROLES:
        s = (prices or {}).get(role)
        pts = [(d, v) for d, v in points(s) if d <= end]
        if pts:
            roles[role] = pts
        elif role != "company":
            missing[role] = (s or {}).get("reason") or "sin serie"
    firsts = [next((d for d, _ in pts if d >= start), None) for pts in roles.values()]
    if any(f is None for f in firsts):
        return {"status": "sin_dato", "reason": "la serie no cubre el periodo", "series": {}, "returns": {},
                "missing": missing}
    s0 = max(firsts)
    series, rets = {}, {}
    for role, pts in roles.items():
        win = [(d, v) for d, v in pts if s0 <= d <= end]
        base = win[0][1]
        series[role] = [(d, 100 * v / base) for d, v in win]
        rets[role] = win[-1][1] / base - 1
    span = (end - start).days
    covered = (end - s0).days >= span - cfg("market.price_returns.chart_slack_days")
    return {"status": "ok", "reason": None if covered else f"la serie empieza el {s0.isoformat()}",
            "series": series, "returns": rets, "start": s0, "end": end, "covered": covered, "missing": missing}


def marks(events: Optional[List[Dict[str, Any]]], pts: List[Tuple[date, float]], s0: date, end: date) -> List[Dict[str, Any]]:
    """Eventos del periodo, cada uno en la primera sesión de la serie en o después de su fecha (un 8-K presentado tras
    el cierre o en un día sin sesión cae en la siguiente). Uno por sesión y tipo."""
    sessions = [d for d, _ in pts if s0 <= d <= end]
    out, seen = [], set()
    for e in sorted(events or [], key=lambda e: str(e.get("t"))):
        try:
            t = _iso(e["t"])
        except (KeyError, TypeError, ValueError):
            continue
        if t < s0 or t > end:
            continue
        d = next((x for x in sessions if x >= t), None)
        if d is None or (d, e.get("kind")) in seen:
            continue
        seen.add((d, e.get("kind")))
        out.append({"t": d.isoformat(), "kind": e.get("kind"), "label": e.get("label")})
    return out


def for_web(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Añade a la respuesta de /api/v2/prices lo que la web pinta tal cual:
      - `ranges`: [{key, label}];
      - `returns` en cada serie: {clave: {price, total, price_txt, total_txt, price_tone, tone}};
      - `chart`: {clave: {status, reason, covered, start, end, series: {rol: {i0, values}}, marks}}; `values` son la
        base 100 de los puntos de esa serie desde su índice `i0` (cada serie con su calendario: MC.PA no cotiza los
        mismos días que el S&P 500)."""
    dec = cfg("market.price_returns.chart_decimals")
    rets = returns(payload)
    for role in ROLES:
        if isinstance(payload.get(role), dict):
            payload[role]["returns"] = rets.get(role, {})
    payload["ranges"] = [{"key": r["key"], "label": r["label"]} for r in ranges()]
    chart = {}
    for r in ranges():
        w = window(payload, r["days"])
        if w["status"] != "ok":
            chart[r["key"]] = {"status": "sin_dato", "reason": w["reason"], "covered": False, "start": None,
                               "end": None, "series": {}, "marks": []}
            continue
        series = {}
        for role, win in w["series"].items():
            dates = [p["t"][:10] for p in payload[role]["points"]]
            first = win[0][0].isoformat()
            i0 = dates.index(first) if first in dates else 0
            series[role] = {"i0": i0, "values": [round(v, dec) for _, v in win]}
        comp_pts = [(d, v) for d, v in points(payload.get("company")) if d <= w["end"]]
        chart[r["key"]] = {"status": "ok", "reason": w["reason"], "covered": w["covered"],
                           "start": w["start"].isoformat(), "end": w["end"].isoformat(), "series": series,
                           "marks": marks((payload.get("company") or {}).get("events"), comp_pts, w["start"], w["end"])
                           if "company" in w["series"] else []}
    payload["chart"] = chart
    return payload
