"""
Contexto de mercado y lectura conductual (fase 5; PLAN_FIABILIDAD §2.2–§2.3; D5: solo contexto).

NUNCA puntúa: no entra en la calidad, el precio, la confianza ni el score. Se muestra en un panel aparte, con el mismo
tono neutro sea la señal buena o mala (efecto marco, §2.3).

Señales (lib/market_signals.py, las de F5prep con su contraste independiente) sobre la serie diaria que el análisis ya
descarga (lib/price_history.py: 2 años, cierre AJUSTADO por dividendos y splits, que es la rentabilidad del
accionista) y la del ETF del sector:
  · momentum 12-1 (Jegadeesh y Titman, 1993), tendencia frente a la media de 200 sesiones (Faber, 2007);
  · volatilidad realizada de 1 año, frente a la del S&P 500 de la misma ventana;
  · caída máxima en 1 año y en la serie entera (2 años);
  · fuerza relativa frente al ETF del sector a 6 y 12 meses (¿el movimiento es de la empresa o del sector?);
  · volumen de las últimas 5 sesiones frente a las 90 anteriores (Gervais, Kaniel y Mingelgrin, 2001).

Lectura conductual del mercado (frente 1 de §2.3), solo cuando los datos la sostienen y con su referencia:
  · **anclaje al máximo de 52 semanas** (George y Hwang, 2004): a menos de `anchor_within` del máximo;
  · **sobrerreacción** (De Bondt y Thaler, 1985): más de `overreaction_drop` por debajo del máximo de 2 años sin
    deterioro de los fundamentales medidos (calidad sólida o excelente e ingresos al alza a 3 años);
  · **extrapolación** (Lakonishok, Shleifer y Vishny, 1994): el precio exige un crecimiento que menos del umbral
    "muy exigente" de las comparables sostuvo, en línea con el que la empresa logró: el precio prolonga el pasado.
La deriva tras resultados (PEAD) no se lee: hace falta la sorpresa del BPA frente al consenso y no hay fuente con
fecha para ella (se dice).
"""
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

import pandas as pd

from settings import cfg

_SIGNALS_NOTE = ("Contexto de mercado: no puntúa en la calidad ni en el precio. Describe cómo se ha movido la acción, "
                 "no qué hará.")


def _pct(x: float, signed: bool = True) -> str:
    return (f"{x * 100:+.1f}%" if signed else f"{x * 100:.1f}%").replace("-", "−")


def _adapt(res: Optional[Dict[str, Any]], calendar=None) -> Dict[str, Any]:
    """Resultado de price_history → entrada de price_series (cierre ajustado como `close`, volumen, splits)."""
    from price_series import _series_entry
    fr = (res or {}).get("frame")
    if fr is not None:
        fr = pd.DataFrame({"close": fr["adj_close"].where(fr["adj_close"].notna(), fr["close"]),
                           "volume": fr["volume"], "split": fr["split"]}, index=fr.index)
        fr = fr[fr["close"].notna()]
    dl = {"symbol": (res or {}).get("symbol"), "frame": fr, "attempts": (res or {}).get("attempts"),
          "latency_s": (res or {}).get("latency_s"), "reason": (res or {}).get("reason") or "sin serie"}
    ent = _series_entry("x", dl, calendar)
    # Fase 5 (punto abierto de F5prep): unas pocas sesiones sueltas sin cotización (festivos locales de un ADR, la
    # sesión de hoy aún sin cierre en otra serie) no falsean el momentum ni la caída máxima; un salto de un día
    # (posible split sin ajustar) sí, y sigue bloqueando. Se declara.
    tol = cfg("market.context.tolerated_missing_days")
    if ent["status"] == "sospechosa" and not ent["jumps"] and len(ent["missing_days"]) <= tol:
        ent["status"] = "ok"
        ent["reasons"] = [f"{len(ent['missing_days'])} sesión/es sin cotización frente al índice, tolerada/s: "
                          + ", ".join(ent["missing_days"])]
    return ent


def series_drawdown(close: pd.Series, quote: Optional[pd.Series] = None) -> Optional[Dict[str, Any]]:
    """Caída máxima en toda la serie (rentabilidad del accionista: cierre ajustado) y distancia de la COTIZACIÓN de hoy
    a su máximo de la serie (cierre sin ajustar: lo que el lector ve; revisión F5, hallazgo 5: el ajustado rebaja los
    precios pasados y daba una caída menor que la real)."""
    if close is None or len(close) < 2:
        return None
    dd = close / close.cummax() - 1
    trough = dd.idxmin()
    peak = close.loc[:trough].idxmax()
    q = quote.dropna() if quote is not None and len(quote.dropna()) >= 2 else close
    return {"value": float(dd.loc[trough]), "peak_date": peak.strftime("%Y-%m-%d"),
            "trough_date": trough.strftime("%Y-%m-%d"), "from_high": float(q.iloc[-1] / q.max() - 1),
            "high_date": q.idxmax().strftime("%Y-%m-%d"),
            "years": round((close.index[-1] - close.index[0]).days / 365.25, 1)}


_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="market_context")


def _wait(fut, default):
    """Resultado de un hilo, o `default` si tarda más que `wait_timeout_s` (nunca bloquea el análisis)."""
    try:
        return fut.result(timeout=cfg("market.context.wait_timeout_s"))
    except Exception as e:  # tiempo agotado u otro fallo: el contexto sigue sin esa parte y lo dice
        return default(f"{type(e).__name__}: {e}")


def build(symbol: str, company: Optional[Dict[str, Any]], market: Optional[Dict[str, Any]],
          sector_etf: Optional[str], a: Dict[str, Any]) -> Dict[str, Any]:
    """{signals, series_drawdown, market_volatility, sector_etf, readings, behavioral, news, note}. La serie del ETF
    del sector y los titulares se piden en paralelo y se esperan como mucho `wait_timeout_s` (revisión F5, hallazgo
    1: antes eran síncronos y, con Yahoo lento, podían sumar ~30 s al análisis)."""
    from market_signals import all_signals, realized_volatility
    import price_history
    C = cfg("market.context")
    P = cfg("market.price_series")
    # El calendario del S&P 500 y el ETF sectorial (SPDR, en USD) solo valen para lo que cotiza en dólares (acciones y
    # ADR): una acción de París tiene sus festivos (MC.PA) y su rentabilidad en EUR no se compara con un ETF en USD
    # (revisión F5, hallazgo 3). Sector desconocido: el ETF de reserva es el propio mercado (SPY), no un sector
    # (hallazgo 8): sin fuerza relativa.
    price_cur = ((a.get("data_provenance") or {}).get("currency") or {}).get("price")
    us = price_cur in (None, "USD")
    sector_ok = bool(sector_etf) and us and sector_etf.upper() not in (P["market_symbol"], P["market_fallback_symbol"])
    f_sec = _pool.submit(price_history.sector, sector_etf) if sector_ok else None
    f_news = _pool.submit(news, symbol)
    sector = (_wait(f_sec, lambda why: {"symbol": sector_etf, "frame": None, "reason": why}) if f_sec else
              {"symbol": None, "frame": None,
               "reason": (f"cotiza en {price_cur}: los ETF de sector de referencia son de EE. UU., en USD" if not us
                          else "sector sin ETF propio (la referencia sería el mercado entero)")})
    mk = _adapt(market)
    cal = mk["frame"].index if (mk.get("frame") is not None and us) else None
    co, se = _adapt(company, cal), _adapt(sector, cal)
    ps = {"series": {"company": dict(co, symbol=(company or {}).get("symbol")),
                     "market": dict(mk, symbol=(market or {}).get("symbol")),
                     "sector": dict(se, symbol=sector_etf)}}
    sig = all_signals(ps, drawdown_years=C["drawdown_years"])
    close = co["frame"]["close"] if co.get("frame") is not None and co["status"] == "ok" else None
    raw_close = (company or {})["frame"]["close"] if (company or {}).get("frame") is not None else None
    out: Dict[str, Any] = {"signals": sig, "sector_etf": sector_etf, "note": _SIGNALS_NOTE,
                           "series_status": {k: v["status"] for k, v in ps["series"].items()},
                           "series_drawdown": series_drawdown(close, raw_close) if close is not None else None,
                           "market_volatility": (realized_volatility(mk["frame"]["close"])
                                                 if mk.get("frame") is not None and mk["status"] == "ok" else None)}
    out["news"] = _wait(f_news, lambda why: {"items": [], "reason": f"sin titulares a tiempo ({why})"})
    out["readings"] = readings(out)
    out["behavioral"] = behavioral(out, a)
    return out


def news(symbol: Optional[str]) -> Dict[str, Any]:
    """Titulares de los últimos `news_days` días de Finnhub (los de la propia empresa, los más recientes primero), sin
    resumen ni interpretación: contexto de qué se ha publicado, no una lectura."""
    import datetime as _dt
    from finnhub_fallback import company_news, is_enabled
    C = cfg("market.context")
    if not is_enabled():
        return {"items": [], "reason": "sin clave de Finnhub"}
    if not symbol:
        return {"items": [], "reason": "sin símbolo"}
    end = _dt.date.today()
    raw = company_news(symbol, (end - _dt.timedelta(days=C["news_days"])).isoformat(), end.isoformat())
    if raw is None:
        return {"items": [], "reason": "sin titulares de Finnhub (no disponibles o sin respuesta)"}
    own = [x for x in raw if symbol.upper() in str(x.get("related") or "").upper().split(",") and x.get("headline")]
    own.sort(key=lambda x: x.get("datetime") or 0, reverse=True)
    items = [{"date": (_dt.datetime.fromtimestamp(int(x["datetime"]), tz=_dt.timezone.utc).strftime("%Y-%m-%d")
                       if x.get("datetime") else None),
              "source": x.get("source"), "headline": str(x["headline"]).strip(), "url": x.get("url")}
             for x in own[:C["news_max"]]]
    return {"items": items, "total": len(own), "days": C["news_days"], "reason": None}


def readings(ctx: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Una frase por señal con dato (tono neutro siempre)."""
    S, C = ctx["signals"], cfg("market.context")
    out = []

    def add(key, label, value, text, field, v):
        out.append({"key": key, "label": label, "value": value, "text": text, "field": field, "num": v})

    m = S.get("momentum_12_1") or {}
    if m.get("status") == "ok":
        v = m["value"]
        verb = ("viene premiando la acción" if v >= C["momentum_band"] else
                "viene castigando la acción" if v <= -C["momentum_band"] else "apenas ha movido la acción")
        add("momentum", "Momentum 12-1", _pct(v),
            f"en los 12 meses anteriores al último, la acción {'subió' if v >= 0 else 'cayó'} un {_pct(abs(v), False)}: "
            f"el mercado {verb}", "market_context.signals.momentum_12_1.value", v)
    t = S.get("trend") or {}
    if t.get("status") == "ok":
        add("trend", "Tendencia (200 sesiones)", t["regime"].capitalize(),
            f"cotiza un {_pct(abs(t['value']), False)} {'por encima' if t['value'] >= 0 else 'por debajo'} de su media "
            f"de 200 sesiones, que {'sube' if t['slope'] >= 0 else 'baja'}: régimen {t['regime']}",
            "market_context.signals.trend.value", t["value"])
    vo, mv = S.get("realized_volatility") or {}, ctx.get("market_volatility") or {}
    if vo.get("status") == "ok":
        txt = f"volatilidad anual realizada del {_pct(vo['value'], False)}"
        if mv.get("status") == "ok":
            txt += f" (S&P 500 en la misma ventana: {_pct(mv['value'], False)})"
        add("volatility", "Volatilidad (1 año)", _pct(vo["value"], False), txt,
            "market_context.signals.realized_volatility.value", vo["value"])
    d1, dd = (S.get("max_drawdown") or {}).get("1") or {}, ctx.get("series_drawdown")
    if d1.get("status") == "ok":
        txt = (f"en el último año llegó a caer un {_pct(abs(d1['value']), False)} desde su máximo "
               f"({d1['peak_date']} → {d1['trough_date']})")
        if dd:
            txt += f"; en los {dd['years']:.0f} años de la serie, un {_pct(abs(dd['value']), False)}"
        add("drawdown", "Caída máxima", _pct(d1["value"]), txt, "market_context.signals.max_drawdown.1.value",
            d1["value"])
    rs = S.get("relative_strength") or {}
    w = (rs.get("windows") or {}).get(str(max(cfg("market.signals.relative_strength.windows_sessions")))) or {}
    if rs.get("status") == "ok" and w.get("status") == "ok":
        own = abs(w["difference"]) >= C["relative_band"]
        add("relative_strength", f"Fuerza relativa frente a {ctx.get('sector_etf')} (12 meses)",
            f"{w['difference'] * 100:+.1f} pp".replace("-", "−"),
            f"en 12 meses, la acción {_pct(w['company'])} frente al {_pct(w['sector'])} del ETF de su sector "
            f"({ctx.get('sector_etf')}): " + ("el movimiento es propio de la empresa" if own
                                              else "se mueve con su sector"),
            "market_context.signals.relative_strength.value", w["difference"])
    av = S.get("abnormal_volume") or {}
    if av.get("status") == "ok":
        z = av["value"]
        add("volume", "Volumen (últimas 5 sesiones)", f"z = {z:.1f}".replace("-", "−"),
            (f"el volumen de las últimas 5 sesiones está muy por encima de lo habitual (z = {z:.1f}): atención "
             "inusual" if z >= C["volume_z"] else
             # revisión F5, hallazgo 4: un z muy negativo no es "habitual"
             f"el volumen de las últimas 5 sesiones está muy por debajo de lo habitual (z = {z:.1f}): poco "
             "interés".replace("-", "−") if z <= -C["volume_z"] else
             f"volumen en el rango habitual (z = {z:.1f})".replace("-", "−")),
            "market_context.signals.abnormal_volume.value", z)
    return out


def behavioral(ctx: Dict[str, Any], a: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Lecturas conductuales del mercado que los datos sostienen (frente 1 de PLAN §2.3)."""
    C = cfg("market.context")
    km = a.get("key_metrics") or {}
    out = []
    price, hi = km.get("price") or a.get("price"), km.get("price_52w_high")
    if price and hi and hi > 0 and price >= hi * (1 - C["anchor_within"]):
        gap = price / hi - 1
        ctx["anchor_gap"] = gap
        out.append({"kind": "anclaje_52s", "field": "market_context.anchor_gap", "num": gap,
                    # revisión F5, hallazgo 6: describe el sesgo, no anticipa el precio
                    "text": (f"Cotiza a un {_pct(abs(gap), False)} de su máximo de 52 semanas. George y Hwang (2004) "
                             "documentan que, cerca de ese máximo, los inversores lo toman como referencia y reaccionan "
                             "con retraso a las noticias: el máximo actúa como ancla. Describe un sesgo estudiado, no "
                             "una previsión.")})
    dd = ctx.get("series_drawdown") or {}
    q = (a.get("quality") or {}).get("level")
    g = (a.get("score") or {}).get("breakdown", {}).get("Crecimiento", {})
    # Revisión F5 (hallazgo 2): los ingresos de verdad (CAGR a 3 años de los estados), no el "retorno total" de la
    # madura de dividendo alto, que suma la rentabilidad por dividendo.
    rev = ((a.get("classification") or {}).get("inputs") or {}).get("revenue_cagr_3y")
    eps = next((x.get("raw") for x in g.get("adjustments") or [] if x.get("metric") == "Crecimiento EPS 3Y"), None)
    # Sin deterioro: calidad sólida o excelente, ingresos al alza y el BPA sin caer (MC.PA: ingresos +0.7% con el
    # BPA a la baja no es "sin deterioro").
    arch = (a.get("classification") or {}).get("archetype")
    # Una cíclica cae con su ciclo (y su BPA es de ciclo medio): no es sobrerreacción. Tampoco en pre-beneficio.
    if (arch not in ("CYCLICAL", "GROWTH_PRE_PROFIT") and dd and dd["from_high"] <= -C["overreaction_drop"]
            and q in ("excelente", "sólida") and rev is not None
            and rev > 0 and eps is not None and eps >= 0):
        out.append({"kind": "sobrerreaccion", "field": "market_context.series_drawdown.from_high",
                    "num": dd["from_high"],
                    "text": (f"Cotiza un {_pct(abs(dd['from_high']), False)} por debajo de su máximo de "
                             f"{dd['years']:.0f} años ({dd['high_date']}) sin deterioro de los fundamentales medidos "
                             f"(calidad {q}, ingresos {_pct(rev)} y BPA {_pct(eps)} anual en 3 años): es el patrón que "
                             "De Bondt y Thaler (1985) estudian como sobrerreacción del mercado a las malas noticias. "
                             "Describe un sesgo estudiado, no una previsión.")})
    m = ((a.get("reverse_dcf") or {}).get("main")) or {}
    br, own = (m.get("base_rate") or {}), (m.get("own_growth") or {})
    if (m.get("state") == "ok" and m.get("band") == "muy_exigente" and br.get("share") is not None
            and br["share"] < cfg("valuation.reverse_dcf.demanding_base_rate") and own.get("cagr") is not None
            and m.get("g10") is not None and own["cagr"] >= m["g10"] * C["extrapolation_own_ratio"]):
        out.append({"kind": "extrapolacion", "field": "reverse_dcf.main.g10", "num": m["g10"],
                    "text": (f"El precio exige crecer un {_pct(m['g10'], False)} anual durante 10 años ("
                             f"{own.get('label') or 'su crecimiento'}: {_pct(own['cagr'], False)} anual en los últimos "
                             f"{own.get('years')} años), un ritmo que solo "
                             + ("menos del 1%" if br["share"] < 0.01 else f"un {br['share'] * 100:.0f}%")
                             + " de las comparables sostuvo: el precio da por hecho que el crecimiento pasado continúa, "
                             "y las tasas base dicen que pocas empresas lo repiten (Lakonishok, Shleifer y Vishny, "
                             "1994).")})
    return out
