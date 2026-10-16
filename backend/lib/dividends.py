"""
Dividendo indicado en la moneda y la clase del precio (fase 2b, T2; F2_PRECEDENCIA §2.2).

El dividendo indicado es el último dividendo ordinario anualizado. Se calcula en la unidad del precio (dólares por
ADR, por acción B…) con los pagos que la serie de precios declara para el propio título (lib/price_history.py):

  · frecuencia por la mediana de los intervalos entre pagos (mensual, trimestral, semestral, anual);
  · extraordinario: un pago mayor que `extraordinary_multiple` veces la mediana de los demás y sin un pago
    comparable un año antes (el anual variable de PGR); el dividendo final mayor que los trimestrales (HSBC, ASML)
    y el semestral desigual (NVO, BCS) son ordinarios;
  · indicado: trimestral o mensual con importes estables o al alza, o con un cambio de nivel reciente → último
    pago × frecuencia (NVDA 0.25 × 4); trimestral desigual o semestral/anual → suma del último ciclo completo
    (NVO 1.275 + 0.579).

Fuentes, en este orden:
  1. Línea doméstica (el precio y la fuente son la misma cotización): el indicado de la fuente (Finnhub o Yahoo:
     el último declarado × frecuencia, que ya recoge una subida declarada y aún no pagada) si casa con el de los
     pagos a ±`source_tolerance`; si no casa, el de los pagos, diciéndolo.
  2. Línea extranjera (ADR o estados en otra moneda): Finnhub da el dividendo de la línea local por acción
     ordinaria (BCS: 11.5 peniques), en una unidad que su respuesta no declara. Se usa el de los pagos del ADR.
  3. Si los pagos no están (serie sin dato o incompleta, TM): la conversión de la fuente local (importe × factor
     oficial × tipo de cambio, con y sin subunidad) que cuadre con lo pagado por título en los estados.
  4. Si nada cuadra: sin dato, con el motivo.

Comprobaciones en los dos sentidos (magnitudes equivalentes: la misma ventana y la misma unidad):
  · subida verificada: el último pago × frecuencia = indicado y el último pago es mayor que el anterior
    (nota "dividendo aumentado el <fecha>"); un recorte también se dice;
  · indicado menos de la mitad de lo cobrado en 12 meses: extraordinario (nota "excluye el extraordinario de X")
    o recorte;
  · lo cobrado por título en 12 meses frente a lo pagado en los estados (TTM) por título: fuera de `paid_band`,
    aviso con las dos cifras (definición: cupones AT1, dividendos a minoritarios; o periodo).
"""
import datetime as _dt
import statistics
from typing import Any, Dict, List, Optional, Sequence, Tuple

from settings import cfg

Event = Tuple[_dt.date, float]


def _D():
    return cfg("market.dividends")


def _fmt(x: float) -> str:
    return f"{x:,.4f}".rstrip("0").rstrip(".") if abs(x) < 1 else f"{x:,.2f}"


def frequency(dates: Sequence[_dt.date]) -> Optional[int]:
    """Pagos por año según la mediana de los intervalos entre pagos (None con menos de dos pagos)."""
    if len(dates) < 2:
        return None
    gaps = [(b - a).days for a, b in zip(dates[:-1], dates[1:])][-6:]
    g = statistics.median(gaps)
    D = _D()
    if g <= D["monthly_max_gap_days"]:
        return 12
    if g <= D["quarterly_max_gap_days"]:
        return 4
    if g <= D["semiannual_max_gap_days"]:
        return 2
    return 1


def split_extraordinary(events: Sequence[Event], declared_hint: Optional[float] = None
                        ) -> Tuple[List[Event], List[Event]]:
    """(ordinarios, extraordinarios). Un pago grande que se repite (un nivel nuevo: NVDA 0.25 tras 0.01) o que
    tiene su par un año antes (el final de HSBC) es ordinario; el último pago también lo es si la fuente declara
    exactamente ese importe × frecuencia (`declared_hint`: una subida con un solo pago todavía)."""
    D = _D()
    if len(events) < 3:
        return list(events), []
    tol = D["level_tolerance"]
    freq = frequency([d for d, _ in events])
    regular, extra = [], []
    for i, (d, a) in enumerate(events):
        others = [x for j, (_, x) in enumerate(events) if j != i]
        big = a > D["extraordinary_multiple"] * statistics.median(others)
        repeated = any(abs(x / a - 1.0) <= tol for x in others)
        seasonal = any(abs((d - d2).days - D["seasonal_lag_days"]) <= D["seasonal_window_days"]
                       and a2 >= D["seasonal_min_ratio"] * a for d2, a2 in events if d2 < d)
        declared = (i == len(events) - 1 and declared_hint and freq
                    and abs(declared_hint / (a * freq) - 1.0) <= tol)
        (extra if big and not (repeated or seasonal or declared) else regular).append((d, a))
    return regular, extra


def _level_start(regular: Sequence[Event]) -> Tuple[Optional[Event], Optional[Event]]:
    """(primer pago del nivel actual, último pago del nivel anterior)."""
    tol = _D()["level_tolerance"]
    last = regular[-1][1]
    i = len(regular) - 1
    while i > 0 and abs(regular[i - 1][1] / last - 1.0) <= tol:
        i -= 1
    return regular[i], (regular[i - 1] if i > 0 else None)


def _single_level(evs: Sequence[Event]) -> bool:
    tol = _D()["level_tolerance"]
    return bool(evs) and all(abs(a / evs[-1][1] - 1.0) <= tol for _, a in evs)


def from_payments(events: Sequence[Event], as_of: _dt.date, declared_hint: Optional[float] = None,
                  cycle_only: bool = False) -> Dict[str, Any]:
    """Indicado desde los pagos del propio título (unidad del precio). Devuelve {rate, basis, frequency, …} o
    {rate: None, reason}.

    `cycle_only` (línea extranjera): la suma del último ciclo completo de pagos ordinarios. En un ADR el importe en
    dólares de cada pago varía con el tipo de cambio y muchos emisores pagan a cuenta y complementario desiguales
    (ASML, NVO, BCS, HSBC): el último pago × frecuencia no representa el año."""
    D = _D()
    ev = sorted((d, float(a)) for d, a in events if a and a > 0 and 0 <= (as_of - d).days <= D["lookback_days"])
    if not ev:
        return {"rate": None, "reason": "la serie de precios no declara dividendos en los últimos 2 años"}
    regular, extra = split_extraordinary(ev, declared_hint)
    freq = frequency([d for d, _ in regular])
    last_d, last_a = regular[-1]
    out: Dict[str, Any] = {"frequency": freq, "last": {"date": last_d.isoformat(), "amount": last_a},
                           "extraordinary": [{"date": d.isoformat(), "amount": a} for d, a in extra
                                             if (as_of - d).days <= 365],
                           "ttm_total": sum(a for d, a in ev if (as_of - d).days <= 365),
                           "payments": [{"date": d.isoformat(), "amount": a} for d, a in ev]}
    if freq is None:
        out.update(rate=None, reason=f"un solo pago en 2 años ({last_d.isoformat()}): sin frecuencia")
        return out
    gap = 365.0 / freq
    if (as_of - last_d).days > D["stale_gap_multiple"] * gap:
        out.update(rate=None, reason=(f"el último pago es del {last_d.isoformat()} con una frecuencia de {freq} al año: "
                                      "historial incompleto o dividendo suspendido"))
        return out
    cycle = regular[-freq:]
    tol = D["level_tolerance"]
    start, prev = _level_start(regular)
    if freq >= 4 and not cycle_only:
        nondecreasing = all(b >= a * (1 - tol) for (_, a), (_, b) in zip(cycle[:-1], cycle[1:]))
        # Cambio de nivel: al menos dos pagos al nivel nuevo y, en el año anterior, un solo nivel distinto (NVDA
        # 0.01 → 0.25). El ciclo desigual de HSBC (tres trimestrales y un final mayor) no lo es.
        before = [e for e in regular if e[0] < start[0] and (start[0] - e[0]).days <= 365]
        level_change = (prev is not None and start != regular[-1] and (as_of - start[0]).days <= 365
                        and _single_level(before))
        if nondecreasing or level_change or len(cycle) < freq:
            out.update(rate=last_a * freq, basis="ultimo_x_frecuencia")
        else:
            out.update(rate=sum(a for _, a in cycle), basis="suma_ultimo_ciclo")
    else:
        out.update(rate=(sum(a for _, a in cycle) if len(cycle) == freq else last_a * freq),
                   basis="suma_ultimo_ciclo" if len(cycle) == freq else "ultimo_x_frecuencia")
    if out["basis"] == "ultimo_x_frecuencia" and prev is not None and (as_of - start[0]).days <= 365:
        kind = "aumento" if start[1] > prev[1] * (1 + tol) else ("recorte" if start[1] < prev[1] * (1 - tol) else None)
        if kind:
            out["change"] = {"kind": kind, "date": start[0].isoformat(), "from": prev[1], "to": start[1]}
    return out


def assess(events: Sequence[Event], as_of: _dt.date, source_rate: Optional[float], source_name: Optional[str],
           foreign_line: bool, paid_per_unit: Optional[float],
           local_candidates: Sequence[Tuple[float, str]] = (), currency: str = "USD",
           unit: str = "acción") -> Dict[str, Any]:
    """El indicado en la unidad del precio, su fuente y sus comprobaciones (ver el docstring del módulo).

    `paid_per_unit`: dividendos pagados TTM de los estados / títulos de la cotización (misma unidad).
    `local_candidates`: [(importe convertido, cómo)] de la fuente local (solo línea extranjera)."""
    D = _D()
    hint = source_rate if (not foreign_line and source_rate) else None
    pay = (from_payments(events, as_of, hint, cycle_only=foreign_line) if events is not None
           else {"rate": None, "reason": "sin serie de precios"})
    hist = pay.get("rate")
    notes: List[str] = []
    res: Dict[str, Any] = {"payments": pay, "source_rate": source_rate, "source_name": source_name,
                           "foreign_line": foreign_line, "paid_per_unit_statements": paid_per_unit,
                           "currency": currency, "unit": unit}
    rate, source = None, None
    if not foreign_line and source_rate is not None and source_rate > 0:
        if hist is not None:
            ratio = source_rate / hist
            if abs(ratio - 1) <= D["source_tolerance"]:
                rate, source = source_rate, source_name
                if ratio - 1 > D["level_tolerance"]:
                    notes.append(f"la fuente ya recoge un dividendo declarado mayor que el último pagado "
                                 f"({_fmt(source_rate)} frente a {_fmt(hist)} {currency} al año)")
            else:
                rate, source = hist, "pagos"
                notes.append(f"el dividendo de la fuente ({_fmt(source_rate)} {currency}) no cuadra con los pagos "
                             f"({_fmt(hist)} {currency} al año): se usa el de los pagos")
        else:
            rate, source = source_rate, source_name
            res["source_note"] = f"sin verificar con los pagos ({pay.get('reason')})"
    elif hist is not None:
        rate, source = hist, "pagos"
        if foreign_line and source_rate:
            res["source_note"] = (f"la fuente da {_fmt(source_rate)} en la moneda de la cotización local y por acción "
                                  f"ordinaria; se usa lo que paga el {unit}")
    elif foreign_line and local_candidates and paid_per_unit:
        lo, hi = D["paid_band"]
        ok = [(abs(c / paid_per_unit - 1), c, how) for c, how in local_candidates
              if c and lo <= c / paid_per_unit <= hi]
        if ok:
            _, rate, how = min(ok)
            source = "fuente_local_convertida"
            notes.append(f"pagos del {unit} no disponibles ({pay.get('reason')}); dividendo de la línea local "
                         f"convertido: {how}")
    if rate is None and not pay.get("payments") and events is not None and not paid_per_unit \
            and not (source_rate and source_rate > 0):
        # No paga: ni pagos en 2 años, ni dividendos en los estados, ni indicado en la fuente. Es un dato (0%).
        res.update(rate=0.0, source="sin_dividendo", basis="sin_dividendo", notes=notes,
                   reason="no paga dividendos (sin pagos en 2 años ni en los estados)")
        return res
    if rate is None:
        reason = pay.get("reason") or "sin dividendo declarado"
        if foreign_line and source_rate:
            reason += (f"; la fuente da {_fmt(source_rate)} en la línea local y ninguna conversión cuadra con lo "
                       "pagado en los estados")
        res.update(rate=None, source=None, reason=reason, notes=notes)
        return res
    # Comprobaciones en los dos sentidos (misma unidad: la del precio).
    ch = pay.get("change") if source == "pagos" or (hist is not None and abs(rate / hist - 1) <= D["source_tolerance"]) else None
    if ch:
        verb = "aumentado" if ch["kind"] == "aumento" else "recortado"
        notes.append(f"dividendo {verb} el {ch['date']} (de {_fmt(ch['from'])} a {_fmt(ch['to'])} {currency} por pago)")
        res["change"] = ch
    extra = pay.get("extraordinary") or []
    if extra:
        notes.append("excluye el extraordinario de " + ", ".join(f"{_fmt(e['amount'])} {currency} pagado el {e['date']}"
                                                                  for e in extra))
    ttm = pay.get("ttm_total")
    if ttm and rate < D["downward_ratio"] * ttm and not extra and not (ch and ch["kind"] == "recorte"):
        notes.append(f"el indicado ({_fmt(rate)}) es menos de la mitad de lo cobrado en 12 meses ({_fmt(ttm)})")
    if paid_per_unit and ttm:
        lo, hi = D["paid_band"]
        r = paid_per_unit / ttm
        res["identity"] = {"paid_per_unit_statements": paid_per_unit, "collected_ttm": ttm, "ratio": r,
                           "ok": lo <= r <= hi}
        if not lo <= r <= hi:
            notes.append(f"los estados pagan {_fmt(paid_per_unit)} {currency} por {unit} en 12 meses frente a "
                         f"{_fmt(ttm)} cobrados: otra definición (cupones de híbridos, minoritarios) u otro periodo")
    res.update(rate=rate, source=source, basis=(pay.get("basis") if source in ("pagos",) else
                                                ("declarado" if source not in ("fuente_local_convertida",) else
                                                 "convertido")),
               notes=notes)
    return res
