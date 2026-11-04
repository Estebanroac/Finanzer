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
Deriva tras resultados (PEAD; Bernard y Thomas, 1989): la sorpresa del BPA del último trimestre frente al consenso
(Finnhub, /stock/earnings), con la fecha de su 8-K de resultados (SEC EDGAR, apartado 2.02), y cómo se movió la acción
frente al S&P 500 entre la sesión anterior al anuncio y la siguiente, y después. Sin 8-K (emisores extranjeros) o sin sorpresa, no se lee y
se dice.
"""
import re
import datetime as _dt
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, List, Optional
from zoneinfo import ZoneInfo

import pandas as pd

from settings import cfg

NY = ZoneInfo("America/New_York")


def safe_url(url: Any) -> Optional[str]:
    """V6 (revisión de seguridad, B17): un enlace de titular solo si es http(s); `javascript:`, `data:` o cualquier otro
    esquema que llegue de la fuente sale como None (la web no lo enlaza)."""
    u = str(url or "").strip()
    return u if u.lower().startswith(("https://", "http://")) and len(u) <= 2048 else None


def ny_today(_frame: Any = None, now: Optional[_dt.datetime] = None) -> _dt.date:
    """V6 (revisión de seguridad, B12): "hoy" es la fecha de Nueva York (la del mercado), no la del reloj del servidor
    (UTC en Render: de 20:00 a 24:00 de Nueva York ya era mañana) ni la última sesión de la serie (un lunes, el
    viernes)."""
    return (now.astimezone(NY) if now is not None else _dt.datetime.now(NY)).date()


# Reloj inyectable: recibe la serie de la empresa (el replay lo cambia por el día de su captura, la última sesión de
# la serie, para que el golden no dependa del día en que se corre).
TODAY: Callable[[Any], _dt.date] = ny_today

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


def fiscal_quarter_end(period: _dt.date, filings: Optional[List[Dict[str, Any]]]) -> Optional[_dt.date]:
    """F10 · N6: el cierre fiscal del trimestre que Finnhub fecha en `period` (el cierre natural más cercano): el periodo
    del 10-Q o 10-K de EDGAR más cercano, a `pead_fiscal_match_days` como mucho. None si aún no está presentado."""
    import sec_edgar
    ends = {_dt.date.fromisoformat(f["reportDate"][:10]) for f in filings or []
            if f.get("form") in sec_edgar.ANNUAL_OR_QUARTERLY and f.get("reportDate")}
    near = [e for e in ends if abs((e - period).days) <= cfg("market.context.pead_fiscal_match_days")]
    return min(near, key=lambda e: (abs((e - period).days), e)) if near else None


def pead(symbol: Optional[str], close: Optional[pd.Series], mclose: Optional[pd.Series],
         filings: Optional[List[Dict[str, Any]]], surprises: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """{status, reason | (period, announced, actual, estimate, surprise, reaction, drift, sessions, ...)}. El último
    trimestre cuya publicación (8-K 2.02 dentro de `pead_announce_max_days` tras el cierre) cae dentro de la serie (en
    replay: lo que se sabía ese día). F10 · N6: el cierre es el fiscal (fiscal_quarter_end; `period_basis` "fiscal"),
    o el que da Finnhub si su 10-Q aún no está en EDGAR (`period_basis` "proveedor"). Reacción: acción − S&P 500 desde la sesión anterior al anuncio hasta la
    siguiente; deriva: lo mismo desde ahí hasta hoy o hasta `pead_window_sessions` sesiones después."""
    C = cfg("market.context")
    if close is None or mclose is None or len(close) < 5:
        return {"status": "sin_dato", "reason": "sin serie de la acción o del índice"}
    if surprises is None:
        from finnhub_fallback import earnings_surprises, is_enabled
        if not is_enabled():
            return {"status": "sin_dato", "reason": "sin clave de Finnhub (consenso del BPA)"}
        surprises = earnings_surprises(symbol) if symbol else None
    if not surprises:
        return {"status": "sin_dato", "reason": "sin el BPA frente al consenso de Finnhub"}
    ann8k = sorted(f["filingDate"] for f in (filings or []) if f.get("form") == "8-K" and "2.02" in (f.get("items") or ""))
    if not ann8k:
        return {"status": "sin_dato", "reason": ("el emisor no presenta 8-K de resultados en SEC EDGAR (20-F/6-K): sin "
                                                 "fecha de anuncio con fuente")}
    last = close.index[-1].date()
    for s in sorted((x for x in surprises if x.get("period")), key=lambda x: x["period"], reverse=True):
        fp = _dt.date.fromisoformat(str(s["period"])[:10])
        fe = fiscal_quarter_end(fp, filings)
        p = fe or fp
        dates = [d for d in ann8k if p < _dt.date.fromisoformat(d) <= p + _dt.timedelta(days=C["pead_announce_max_days"])]
        if not dates or _dt.date.fromisoformat(dates[0]) > last:
            continue
        act, est = s.get("actual"), s.get("estimate")
        if act is None or est is None or est == 0:
            return {"status": "sin_dato", "reason": f"sin BPA o consenso del trimestre cerrado el {p}"}
        ann = _dt.date.fromisoformat(dates[0])
        idx = close.index
        i0 = int(idx.searchsorted(pd.Timestamp(ann)))      # primera sesión en o tras el anuncio
        pre, post = i0 - 1, i0 + 1
        if pre < 0:
            return {"status": "sin_dato", "reason": "la serie no cubre la sesión anterior al anuncio"}
        out = {"status": "ok", "period": p.isoformat(), "period_basis": "fiscal" if fe else "proveedor",
               "provider_period": fp.isoformat(), "announced": ann.isoformat(), "actual": float(act),
               "estimate": float(est), "surprise": (float(act) - float(est)) / abs(float(est)), "reaction": None,
               "drift": None, "sessions": 0, "window": C["pead_window_sessions"], "window_passed": False,
               "source": "BPA y consenso: Finnhub; fecha: 8-K de resultados (SEC EDGAR, apartado 2.02)"}
        if post > len(idx) - 1:          # publicado en la última sesión: la reacción aún no se puede medir
            return out
        end = min(post + C["pead_window_sessions"], len(idx) - 1)
        m = mclose.reindex(idx).ffill()
        ret = lambda s_, a_, b_: float(s_.iloc[b_] / s_.iloc[a_] - 1)  # noqa: E731
        out.update(reaction=ret(close, pre, post) - ret(m, pre, post), sessions=end - post,
                   drift=(ret(close, post, end) - ret(m, post, end)) if end > post else None,
                   window_passed=(len(idx) - 1 - post) >= C["pead_window_sessions"])
        return out
    return {"status": "sin_dato", "reason": "ningún trimestre con BPA frente al consenso y 8-K de resultados en la serie"}


def build(symbol: str, company: Optional[Dict[str, Any]], market: Optional[Dict[str, Any]],
          sector_etf: Optional[str], a: Dict[str, Any], filings: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
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
    f_news = _pool.submit(news, symbol, (a.get("profile") or {}).get("name"))
    # Rediseño E2a (T8): próximos resultados en paralelo con los titulares. "Hoy": TODAY (V6, B12: la fecha de Nueva
    # York; en el replay, el día de la captura).
    _today = TODAY((company or {}).get("frame"))
    f_next = _pool.submit(next_earnings, symbol, filings, _today)
    # Rendimiento (v4f8): el BPA frente al consenso (Finnhub) que pide pead, en paralelo con lo anterior; pead lo lee
    # de la caché de finnhub_fallback (la misma respuesta).
    from finnhub_fallback import earnings_surprises, is_enabled
    f_surp = _pool.submit(earnings_surprises, symbol) if (us and symbol and is_enabled()) else None
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
                           # V4b (auditoría de datos): el porqué de una serie que no está (MC.PA: cotiza en EUR)
                           "series_reasons": {k: (v.get("reasons") or [None])[0] for k, v in ps["series"].items()
                                              if v["status"] != "ok" and (v.get("reasons") or [None])[0]},
                           "series_drawdown": series_drawdown(close, raw_close) if close is not None else None,
                           "market_volatility": (realized_volatility(mk["frame"]["close"])
                                                 if mk.get("frame") is not None and mk["status"] == "ok" else None)}
    out["news"] = _wait(f_news, lambda why: {"items": [], "reason": f"sin titulares a tiempo ({why})"})
    out["next_earnings"] = _wait(f_next, lambda why: {"status": "sin_dato", "date": None, "kind": None, "hour": None,
                                                      "source": None, "basis": None,
                                                      "reason": f"sin calendario a tiempo ({why})"})
    mclose = mk["frame"]["close"] if mk.get("frame") is not None and mk["status"] == "ok" else None
    if f_surp is not None:
        try:
            f_surp.result()
        except Exception:  # noqa: BLE001 — pead la pide otra vez y su fallo se trata allí, como antes
            pass
    try:
        out["pead"] = (pead(symbol, close, mclose, filings) if us else
                       {"status": "sin_dato", "reason": f"cotiza en {price_cur}: la deriva se mide frente al S&P 500, en USD"})
    except Exception as e:  # nunca rompe el contexto: sin lectura y se dice
        out["pead"] = {"status": "sin_dato", "reason": f"{type(e).__name__}: {e}"}
    out["readings"] = readings(out)
    out["behavioral"] = behavioral(out, a)
    return out


def mention_terms(symbol: Optional[str], name: Optional[str]) -> set:
    """Rediseño E2a (revisión del PM): cómo se nombra a la empresa en un titular, en minúsculas: el nombre corto (el
    legal sin sufijos societarios: "Exxon Mobil Corporation" → "exxon mobil"), el mismo sin espacios ("exxonmobil") y
    su primera palabra si no es una palabra común ("exxon"; "Realty Income" exige las dos)."""
    C = cfg("market.context")
    suffixes = {x.lower() for x in C["news_name_suffixes"]}
    common = {x.lower() for x in C["news_common_words"]}
    words = [w.strip(".,") for w in str(name or "").split()]
    words = [w for w in words if w]
    while words and words[-1].lower().replace(".", "") in suffixes:
        words.pop()
    while words and words[0].lower() in suffixes:
        words.pop(0)
    if not words:
        return set()
    short = " ".join(words).lower()
    terms = {short}
    if len(words) > 1:
        terms.add(short.replace(" ", ""))
        first = words[0].lower()
        if first not in common and len(first) >= 3:
            terms.add(first)
    return terms


def _mentions(text: str, symbol: str, terms: set) -> bool:
    """¿El texto nombra a la empresa? Ticker como palabra (2+ letras) o entre paréntesis / tras la bolsa; o un término
    de mention_terms como palabra completa, sin distinguir mayúsculas."""
    import re
    sym = re.escape(symbol.upper())
    if (len(symbol) > 1 and re.search(rf"(?<![A-Za-z0-9.]){sym}(?![A-Za-z0-9])", text)) or \
            re.search(rf"\({sym}\)|\b(?:NYSE|NASDAQ|Nasdaq|NYSEARCA|AMEX)\s*:\s*{sym}(?![A-Za-z0-9])", text):
        return True
    low = text.lower()
    return any(re.search(rf"(?<![a-z0-9]){re.escape(t)}(?![a-z0-9])", low) for t in terms)


_C1 = re.compile(r"[\x80-\x9f]")


def clean_external(s: Optional[str]) -> Optional[str]:
    """V4b: texto de un tercero sin controles C1 (sin glifo en el PDF). Suele ser UTF-8 leído como latin-1 («â\x80\x93»
    por «–»): se recompone; si no se puede, se quitan."""
    if not s or not _C1.search(s):
        return s
    try:
        fixed = s.encode("latin-1").decode("utf-8")
        if not _C1.search(fixed):
            return fixed
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass
    return _C1.sub("", s)


def news(symbol: Optional[str], name: Optional[str] = None) -> Dict[str, Any]:
    """Titulares de los últimos `news_days` días de Finnhub (los de la propia empresa, los más recientes primero), sin
    resumen ni interpretación: contexto de qué se ha publicado, no una lectura."""
    import datetime as _dt
    from finnhub_fallback import company_news, is_enabled, provider_symbol
    C = cfg("market.context")
    if not is_enabled():
        return {"items": [], "reason": "sin clave de Finnhub"}
    if not symbol:
        return {"items": [], "reason": "sin símbolo"}
    end = ny_today()
    raw = company_news(symbol, (end - _dt.timedelta(days=C["news_days"])).isoformat(), end.isoformat())
    if raw is None:
        return {"items": [], "reason": "sin titulares de Finnhub (no disponibles o sin respuesta)"}
    # V4b: `related` lleva el símbolo de Finnhub (BRK.B para BRK-B)
    mine = {symbol.upper(), provider_symbol(symbol)}
    own = [x for x in raw if mine & set(str(x.get("related") or "").upper().split(",")) and x.get("headline")]
    # Revisión del PM: solo los que nombran a la empresa (Finnhub la pone en `related` de noticias generales).
    terms = mention_terms(symbol, name)
    own = [x for x in own if _mentions(f"{x['headline']} {x.get('summary') or ''}", symbol, terms)]
    own.sort(key=lambda x: x.get("datetime") or 0, reverse=True)

    def when(x):
        return _dt.datetime.fromtimestamp(int(x["datetime"]), tz=_dt.timezone.utc) if x.get("datetime") else None
    # Una imagen que se repite en titulares distintos es el logotipo del medio (Yahoo), no una foto de la noticia.
    seen: Dict[str, int] = {}
    for x in own:
        if x.get("image"):
            seen[x["image"]] = seen.get(x["image"], 0) + 1

    def image(x):
        im = str(x.get("image") or "")
        return im if im.startswith("https://") and seen.get(im) == 1 else None
    # Rediseño E2a (T8): hasta news_max_v2 titulares con resumen, imagen (solo https y propia), categoría, fecha y
    # hora (UTC) e idioma original; la web actual sigue con news_max (display._market_block).
    def item(x):
        return {"date": when(x).strftime("%Y-%m-%d") if when(x) else None,
                "source": x.get("source"), "headline": clean_external(str(x["headline"]).strip()),
                "url": safe_url(x.get("url")),
                "summary": _summary(clean_external(x.get("summary")), C["news_summary_chars"]),
                "image": image(x),
                "category": x.get("category") or None,
                "datetime": when(x).strftime("%Y-%m-%dT%H:%M:%SZ") if when(x) else None,
                "lang": C["news_lang"]}
    items = [item(x) for x in own[:max(C["news_max"], C["news_max_v2"])]]
    # Centro de noticias (/v2): de los titulares de la semana, primero los que traen foto propia (Finnhub da a casi
    # todos los de Yahoo su logotipo, que no se publica); el resto se completa con los más recientes sin foto. Se
    # enseñan por fecha. La web actual y el PDF siguen con los más recientes (`items`).
    pick = [x for x in own if image(x)][:C["news_max_v2"]]
    pick += [x for x in own if not image(x)][:C["news_max_v2"] - len(pick)]
    pick.sort(key=lambda x: x.get("datetime") or 0, reverse=True)
    return {"items": items, "featured": [item(x) for x in pick], "total": len(own), "days": C["news_days"],
            "reason": None if own else f"ningún titular de los últimos {C['news_days']} días menciona a la empresa"}


def _summary(text: Optional[str], limit: int) -> Optional[str]:
    """Resumen de Finnhub recortado a `limit` caracteres en límite de palabra, con "…" si se recortó."""
    t = " ".join(str(text or "").split())
    if not t:
        return None
    if len(t) <= limit:
        return t
    cut = t[:limit].rsplit(" ", 1)[0].rstrip(" ,;:.-—")
    return cut + "…"


def next_earnings(symbol: Optional[str], filings: Optional[List[Dict[str, Any]]], today: _dt.date) -> Dict[str, Any]:
    """Rediseño E2a (T8): próxima publicación de resultados. Anunciada: la primera fecha ≥ hoy del calendario de
    Finnhub (con la hora, antes o después de la sesión, si viene). Si no hay, estimada: el último 8-K de resultados de
    EDGAR (apartado 2.02) más `estimate_cadence_days`, solo si esa fecha aún no ha pasado. Si no, sin dato."""
    from finnhub_fallback import earnings_calendar, is_enabled
    C = cfg("market.context")
    if symbol and is_enabled():
        cal = earnings_calendar(symbol, today.isoformat(), (today + _dt.timedelta(days=C["next_earnings_days"])).isoformat())
        ahead = sorted((e for e in (cal or []) if str(e.get("date") or "") >= today.isoformat()),
                       key=lambda e: str(e["date"]))
        if ahead:
            e = ahead[0]
            return {"status": "ok", "date": str(e["date"])[:10], "kind": "anunciada",
                    "hour": e.get("hour") if e.get("hour") in ("bmo", "amc") else None,
                    "source": "calendario de resultados de Finnhub", "basis": None, "reason": None}
    ann = sorted(f["filingDate"] for f in (filings or []) if f.get("form") == "8-K" and "2.02" in (f.get("items") or ""))
    if ann:
        est = _dt.date.fromisoformat(ann[-1]) + _dt.timedelta(days=C["estimate_cadence_days"])
        if est >= today:
            return {"status": "ok", "date": est.isoformat(), "kind": "estimada", "hour": None,
                    "source": "SEC EDGAR (8-K de resultados, apartado 2.02)",
                    "basis": {"last_results_8k": ann[-1], "cadence_days": C["estimate_cadence_days"]},
                    "reason": None}
    return {"status": "sin_dato", "date": None, "kind": None, "hour": None, "source": None, "basis": None,
            "reason": "Sin fecha anunciada"}


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
    _rs_key = cfg("market.signals.relative_strength.windows")[-1]
    w = (rs.get("windows") or {}).get(_rs_key) or {}
    # F8 · P3: el periodo con el mismo rótulo que la tabla de rentabilidades de la web y del PDF («1 año»)
    _rs_lab = dict(zip(cfg("market.price_returns.range_keys"), cfg("market.price_returns.range_labels")))[_rs_key]
    if rs.get("status") == "ok" and w.get("status") == "ok":
        own = abs(w["difference"]) >= C["relative_band"]
        add("relative_strength", f"Fuerza relativa frente a {ctx.get('sector_etf')} ({_rs_lab})",
            f"{w['difference'] * 100:+.1f} pp".replace("-", "−"),
            f"en {_rs_lab}, la acción {_pct(w['company'])} frente al {_pct(w['sector'])} del ETF de su sector "
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
    pe = ctx.get("pead") or {}
    if pe.get("status") == "ok":
        s = pe["surprise"]
        per = (f"del trimestre fiscal cerrado el {pe['period']}" if pe.get("period_basis") != "proveedor" else
               f"del trimestre cerrado el {pe['period']} según Finnhub (su 10-Q aún no está en la SEC)")
        txt = (f"resultados {per}, publicados el {pe['announced']}: BPA de "
               f"{pe['actual']:.2f} frente a {pe['estimate']:.2f} de consenso, una sorpresa del {_pct(s)}")
        if pe["reaction"] is None:
            txt += ". Publicados en la última sesión de la serie: la reacción y la deriva aún no se pueden medir"
        else:
            txt += (f". Entre la sesión anterior al anuncio y la siguiente, la acción {_pct(pe['reaction'])} frente al "
                    "S&P 500")
            if pe["drift"] is not None:
                txt += f"; en las {pe['sessions']} sesiones siguientes, {_pct(pe['drift'])} frente al S&P 500"
        if pe["reaction"] is None:
            pass
        elif abs(s) < C["pead_inline"]:
            txt += ": resultado en línea con el consenso, sin sorpresa de la que se espere deriva"
        elif pe["drift"] is None or pe["sessions"] < C["pead_min_sessions"]:
            txt += f": aún pocas sesiones tras el anuncio para hablar de deriva"
        else:
            same = (pe["drift"] >= 0) == (s >= 0)
            txt += (f": la deriva va {'en la dirección' if same else 'en contra'} de la sorpresa. Bernard y Thomas "
                    f"(1989) documentan que el precio sigue la sorpresa unas {pe['window']} sesiones"
                    + (f" (esa ventana ya pasó)" if pe["window_passed"] else "")
                    + "; describe un efecto estudiado, no una previsión")
        add("pead", "Resultados y deriva (PEAD)", f"{_pct(s)} sorpresa", txt, "market_context.pead.surprise", s)
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
    eps = next((x.get("raw") for x in g.get("adjustments") or [] if str(x.get("metric") or "").startswith("Crecimiento del BPA ")), None)
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
                             f"{own.get('years')} años" + (f", {own['window']}" if own.get("window") else "")
                             + "), un ritmo que solo "
                             + ("menos del 1%" if br["share"] < 0.01 else f"un {br['share'] * 100:.0f}%")
                             + " de las comparables sostuvo: el precio da por hecho que el crecimiento pasado continúa, "
                             "y las tasas base dicen que pocas empresas lo repiten (Lakonishok, Shleifer y Vishny, "
                             "1994).")})
    return out
