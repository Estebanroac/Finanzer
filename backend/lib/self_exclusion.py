"""
F10 · N2 (revisión del informe de NVIDIA; regla del modelo general): la referencia de la industria nunca incluye a la
propia empresa. NVIDIA es el 66 % de la capitalización de los semiconductores de EE. UU. en el conjunto de Damodaran
(5-ene-2026): compararla con ese agregado es, en buena parte, compararla consigo misma.

  · Cifras de la empresa a la fecha del conjunto (`industries.dollar_as_of`):
      - doce meses que acaban en el último trimestre presentado a esa fecha (SEC EDGAR: ingresos, beneficio bruto,
        operativo y neto, amortizaciones e intereses; como define Damodaran sus agregados), a la moneda del precio con
        el tipo de cambio medio de esos doce meses;
      - balance de ese trimestre o ejercicio (Yahoo: deuda, caja, patrimonio y acciones; misma definición que el
        resto del análisis);
      - capitalización de ese día = cierre de ese día × acciones de la clase que cotiza (capitalización de hoy /
        precio de hoy) × acciones de entonces / acciones de hoy.
    Sin precio en USD (los totales de Damodaran están en USD), sin EDGAR o con doce meses que acaban más de
    `data.edgar.stale_coverage_days` (+ la tolerancia de fechas de cierre) antes de esa fecha (un 20-F: solo el
    ejercicio en XBRL): sin cifras.
  · Cada columna de Damodaran es un cociente de totales de la industria: P/E = capitalización / beneficio, EV/EBITDA,
    P/B, ROE, ROIC (resultado operativo después de impuestos / capital invertido), márgenes, cobertura de intereses y
    D/E. De los dos totales, uno sale de Dollar{R}.xls (el ANCLA: el que la definición de la columna no recorta) y el
    otro de la cifra publicada (ancla / valor, o valor × ancla). Sin la empresa:
        multiplicador (P/E, EV/EBITDA, P/B, cobertura):  (A − a) / (A / valor − d)
        rentabilidad, margen y D/E:                      (valor × A − n) / (A − a)
    con A el ancla de la industria y a, n, d las cifras de la empresa. Así se respeta la definición de Damodaran (el
    P/E y el EV/EBITDA solo con las empresas con beneficio o EBITDA positivos: con el beneficio de TODAS, NFLX salía
    con una referencia de 221x; una empresa en pérdidas no está en ese agregado y no se quita), es continua (con peso
    0 da la publicada) y no depende de las empresas en pérdidas.
  · Respaldo, la mediana de los pares del universo de la misma industria (config/peer_metrics.tsv, sin la empresa ni
    sus otras clases): sin cifras a la fecha; o si lo que queda no es representativo: la empresa pesa ≥ `max_weight`
    de la capitalización (AAPL y ASML ≈ 100 %: quedarían restos) o quedan menos de `min_firms` empresas. Con menos de
    `min_peers` pares con dato, esa columna queda sin referencia.
Peso declarado siempre: capitalización de la empresa / capitalización de la industria, a la fecha del conjunto.
"""
import datetime as _dt
import math
import os
import statistics
import threading
from typing import Any, Dict, List, Optional

from settings import cfg

# columna de Damodaran -> (numerador, denominador, ancla): la parte que se toma de Dollar{R}.xls es el ancla; la otra
# sale de la cifra publicada
PARTS = {"pe": ("mcap", "net_income", "mcap"), "ev_ebitda": ("ev", "ebitda", "ev"),
         "pb": ("mcap", "book_equity", "mcap"), "roe": ("net_income", "book_equity", "book_equity"),
         "roic": ("ebit_after_tax", "invested_capital", "invested_capital"),
         "gross_margin": ("gross_profit", "revenue", "revenue"), "operating_margin": ("ebit", "revenue", "revenue"),
         "net_margin": ("net_income", "revenue", "revenue"), "interest_coverage": ("ebit", "interest", "ebit"),
         "de": ("total_debt", "book_equity", "book_equity")}
# Damodaran agrega el P/E solo con las empresas con beneficio y el EV/EBITDA con las de EBITDA positivo
ONLY_POSITIVE = {"pe": "net_income", "ev_ebitda": "ebitda"}
LABELS = {"pe": "P/E", "ev_ebitda": "EV/EBITDA", "pb": "P/B", "roe": "ROE", "roic": "ROIC",
          "gross_margin": "margen bruto", "operating_margin": "margen operativo", "net_margin": "margen neto",
          "interest_coverage": "cobertura de intereses", "de": "D/E"}
EDGAR_FLOWS = {"revenue": "revenue", "gross_profit": "gross_profit", "ebit": "operating_income",
               "net_income": "net_income", "depreciation": "depreciation", "interest": "interest_expense"}
PEERS_FILE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config",
                                           "peer_metrics.tsv"))
MILLION = 1e6


def _no(reason: str) -> Dict[str, Any]:
    return {"status": "sin_dato", "reason": reason}


# F10 (PM, 29-oct; ENB): las últimas cifras válidas de cada empresa a la fecha del conjunto. Son de una fecha fija
# (`industries.dollar_as_of`): no caducan hasta que cambia el conjunto, que es parte de la clave.
_LAST_OK: Dict[tuple, Dict[str, Any]] = {}
_LAST_LOCK = threading.Lock()


def figures_resilient(symbol: str, info: Dict[str, Any], ed: Dict[str, Any], frame, ctx=None) -> Dict[str, Any]:
    """`figures_at` sin que un tiempo agotado de EDGAR cambie la referencia en silencio (ENB, 29-oct: P/E de referencia
    16,95x en una pasada y 25,0x, la mediana de los pares, en la siguiente). EDGAR ya reintentó
    (sec_edgar.retry_if_transient). Si aun así no respondió (no si el emisor no tiene estados): las últimas cifras válidas
    de la caché; sin ninguna, `degraded` con el motivo (la referencia lo declara)."""
    import sec_edgar as edgar
    key = (str(symbol or "").upper(), cfg("industries.dollar_as_of"))
    ed = ed or {}
    facts = ed.get("facts") if ed.get("status") == "ok" else None
    transient = facts is None and edgar.transient(ed)
    why = ed.get("facts_reason") or ed.get("reason") or "EDGAR no respondió"
    retried = bool(ed.get("retried"))
    if not transient:
        fig = figures_at(info, facts, frame, ctx)
        if fig.get("status") == "ok":
            with _LAST_LOCK:
                _LAST_OK[key] = fig
        return fig
    with _LAST_LOCK:
        last = _LAST_OK.get(key)
    if last:
        return {**last, "from_cache": True,
                "cache_note": f"EDGAR no respondió ({why}); cifras de la caché (son a una fecha fija)"}
    return {"status": "sin_dato", "degraded": True,
            "reason": f"{why}{' (reintentado)' if retried else ''}: referencia degradada, no la industria sin la empresa"}


def _near(d: str, at: _dt.date, tol: int) -> bool:
    return abs((_dt.date.fromisoformat(d) - at).days) <= tol


def _flow(facts: Dict[str, Any], field: str, cut: _dt.date, tol: int) -> Optional[Dict[str, Any]]:
    """Doce meses del campo que acaban en `cut`: el primer concepto (en el orden de sec_edgar.CONCEPTS) que los tenga.
    Aquí sí se pasa al siguiente: solo se usa para pesar a la empresa en su industria, no para sus estados."""
    import sec_edgar as edgar
    sign = edgar.CONCEPTS[field][1]
    for _c, fs in edgar.candidates(facts, field):
        r = edgar.flow_ttm(fs, cut, tol)
        if r is not None:
            return {**r, "value": sign * r["value"]}
    return None


def figures_at(info: Dict[str, Any], facts: Optional[Dict[str, Any]], frame, ctx=None) -> Dict[str, Any]:
    """Cifras de la empresa a la fecha del conjunto de Damodaran, en millones de la moneda del precio (USD), o
    {"status": "sin_dato", "reason"}."""
    import sec_edgar as edgar
    as_of = _dt.date.fromisoformat(cfg("industries.dollar_as_of"))
    tol = cfg("data.edgar.report_date_tolerance_days")
    cur = (info.get("_currency") or {}).get("price") or info.get("currency")
    if cur != "USD":
        return _no(f"cotiza en {cur or 'una moneda sin dato'} y los totales de Damodaran son en USD")
    if not facts:
        return _no("sin estados en SEC EDGAR")
    cands = edgar.candidates(facts, "net_income")
    # el último trimestre (o ejercicio) presentado antes de esa fecha cuyos doce meses se pueden reconstruir
    ends = sorted({f["end"] for _c, fs in cands for f in fs
                   if f.get("start") and 80 <= (edgar._days(f) or 0) <= 380 and (f.get("filed") or "9") <= str(as_of)},
                  reverse=True)
    cut = next((_dt.date.fromisoformat(e) for e in ends if _flow(facts, "net_income", _dt.date.fromisoformat(e), tol)),
               None)
    if cut is None:
        return _no("sin beneficio de doce meses presentado en SEC EDGAR antes de esa fecha")
    # Los doce meses de Damodaran son los del último trimestre presentado a esa fecha. Si los de EDGAR acaban más de
    # `stale_coverage_days` antes (la regla de estados desfasados, F8 · E6: un trimestre más el plazo de un 10-Q), son
    # de otro periodo: un emisor con 20-F solo tiene en XBRL su ejercicio (SAP: 2024, con la reestructuración; Damodaran
    # usa los doce meses a septiembre de 2025).
    lag = (as_of - cut).days
    # (más la tolerancia de fechas de cierre: trimestres de 52/53 semanas, KO al 26-sep)
    if lag > cfg("data.edgar.stale_coverage_days") + tol:
        import numfmt
        return _no(f"los últimos doce meses en SEC EDGAR a esa fecha acaban el {numfmt.date_long(str(cut))} ({lag} "
                   "días antes): no son los del conjunto")
    out: Dict[str, Any] = {"status": "ok", "date": str(as_of), "cut": str(cut), "currency": "USD", "values": {},
                           "missing": []}
    v = out["values"]
    for key, field in EDGAR_FLOWS.items():
        r = _flow(facts, field, cut, tol)
        if r is None:
            out["missing"].append(key)
            continue
        val = r["value"]
        if ctx is not None and getattr(ctx, "convert_currency", False):
            val = ctx.convert_amount(val, "flow", end=str(cut))
        v[key] = val / MILLION
    if "ebit" in v and "depreciation" in v:
        v["ebitda"] = v["ebit"] + v["depreciation"]
    bal = info.get("_q_balances") or {}
    at = next((d for d in sorted(bal, reverse=True) if _near(d, cut, tol)), None)
    b = dict(bal.get(at) or {})
    # el corte es un ejercicio (20-F) o al trimestre de Yahoo le faltan filas: las del balance anual de esa fecha
    fy = info.get("_fy_balances") or {}
    fb = next((fy[d] for d in sorted(fy, reverse=True) if _near(d, cut, tol)), {})
    b.update({k: x for k, x in fb.items() if b.get(k) is None and x is not None})
    if b.get("equity") is not None:
        v["book_equity"] = b["equity"] / MILLION
    else:
        r = edgar.field_value(facts, "equity_parent", cut, tol)
        if r is not None:
            val = r["value"]
            if ctx is not None and getattr(ctx, "convert_currency", False):
                val = ctx.convert_amount(val, "balance", end=str(cut))
            v["book_equity"] = val / MILLION
    if b.get("totalDebt") is not None:
        v["total_debt"] = b["totalDebt"] / MILLION
    if b.get("cash") is not None:
        v["cash"] = b["cash"] / MILLION
    # capitalización de ese día
    if frame is None or "close" not in frame:
        return _no("sin serie de precios")
    import pandas as pd
    closes = frame["close"].loc[:pd.Timestamp(as_of)].dropna()
    if closes.empty:
        return _no("la serie de precios no llega a esa fecha")
    price, mcap = info.get("currentPrice") or info.get("regularMarketPrice"), info.get("marketCap")
    if not price or not mcap:
        return _no("sin capitalización ni precio de hoy")
    latest = max(bal) if bal else None
    sh_then, sh_now = b.get("shares"), (bal.get(latest) or {}).get("shares")
    ratio = sh_then / sh_now if sh_then and sh_now else None
    out["close"] = float(closes.iloc[-1])
    out["session"] = str(closes.index[-1].date())
    out["shares_ratio"] = ratio
    v["mcap"] = out["close"] * (mcap / price) * (ratio if ratio else 1.0) / MILLION
    if ratio is None:
        out["missing"].append("acciones de entonces (se toman las de hoy)")
    if "total_debt" in v and "cash" in v:
        v["ev"] = v["mcap"] + v["total_debt"] - v["cash"]
        if "book_equity" in v:
            v["invested_capital"] = v["book_equity"] + v["total_debt"] - v["cash"]
    return out


# ───────────────────────── el agregado sin la empresa ─────────────────────────

MULTIPLES = ("pe", "ev_ebitda", "pb", "interest_coverage")


def without(values: Dict[str, float], dollars: Dict[str, float], fig: Dict[str, Any]) -> Dict[str, Any]:
    """{values, columns: {col: {before, after, how}}, weight} de la referencia sin la empresa (`fig`: figures_at)."""
    c = dict(fig["values"])
    tot = dict(dollars)
    # ROIC: el resultado operativo después de impuestos de la empresa, con el tipo implícito de la industria
    # (ROIC publicado × capital invertido / EBIT de la industria)
    roic = values.get("roic")
    if roic is not None and c.get("ebit") is not None and tot.get("ebit") and tot.get("invested_capital"):
        c["ebit_after_tax"] = c["ebit"] * roic * tot["invested_capital"] / tot["ebit"]
    out_vals, cols = {}, {}
    for col, val in values.items():
        parts = PARTS.get(col)
        if parts is None:
            out_vals[col] = val
            continue
        pos = ONLY_POSITIVE.get(col)
        if pos and c.get(pos) is not None and c[pos] <= 0:
            out_vals[col] = val
            cols[col] = {"before": val, "after": val, "how": "no_entra"}
            continue
        num, den, anchor = parts
        A, n, d = tot.get(anchor), c.get(num), c.get(den)
        new = None
        if None not in (A, n, d) and A > 0 and val:
            if col in MULTIPLES:                       # (A − a) / (A / valor − d), con a = n (el ancla es el numerador)
                rest = A / val - d
                new = (A - n) / rest if rest > 0 and A - n > 0 else None
            else:                                      # (valor × A − n) / (A − a), con a = d (el ancla es el denominador)
                new = (val * A - n) / (A - d) if A - d > 0 else None
        if new is None:
            cols[col] = {"before": val, "after": None, "how": "sin_dato"}
            continue
        out_vals[col] = new
        cols[col] = {"before": val, "after": new, "how": "sin_empresa"}
    return {"values": out_vals, "columns": cols, "weight": c["mcap"] / tot["mcap"] if tot.get("mcap") else None}


# ───────────────────────── respaldo: mediana de pares del universo ─────────────────────────

_peers: Dict[str, Any] = {}
_peers_lock = threading.Lock()


def _load_peers() -> Dict[str, Any]:
    with _peers_lock:
        if not _peers:
            rows, date = [], None
            if os.path.isfile(PEERS_FILE):
                with open(PEERS_FILE, encoding="utf-8") as fh:
                    head = None
                    for line in fh:
                        line = line.rstrip("\n")
                        if line.startswith("#"):
                            if "GENERADO" in line and " el " in line:
                                date = line.split(" el ", 1)[1].split()[0]
                            continue
                        parts = line.split("\t")
                        if head is None:
                            head = parts
                            continue
                        row = dict(zip(head, parts))
                        rows.append({k: (float(x) if k not in ("symbol", "damodaran_industry", "damodaran_region")
                                         else x) for k, x in row.items()})
            _peers.update(rows=rows, date=date)
        return _peers


def peer_median(industry: str, symbol: Optional[str], columns: List[str],
                region: Optional[str] = None) -> Dict[str, Any]:
    """{values, columns: {col: {after, n}}, n_peers, date, scope, n_region}: mediana de los pares del universo de la
    industria de Damodaran, sin la propia empresa ni sus otras clases (mismo CIK). F11 · T1 (revisión de NU): con
    `region` (la de la referencia), solo los pares de esa región; si son menos de `min_peers`, los de todas las regiones,
    dicho en `scope` (NU: 19 pares de «Bank (Money Center)», 17 de otras regiones)."""
    import universe
    P = _load_peers()
    me = universe.get(symbol) or {}
    sym = universe.norm_symbol(symbol)
    peers = [r for r in P["rows"] if r["damodaran_industry"] == industry and r["symbol"] != sym
             and not (me.get("cik") and (universe.get(r["symbol"]) or {}).get("cik") == me.get("cik"))]
    pe_max = cfg("market.peers.pe_meaningful_max")
    k_min = cfg("market.peers.min_peers")
    scope, n_region = "todas", None
    if region and region != "global":
        local = [r for r in peers if r.get("damodaran_region") == region]
        n_region = len(local)
        if n_region >= k_min:
            peers, scope = local, region
    vals, cols = {}, {}
    for col in columns:
        xs = [r[col] for r in peers if col in r and math.isfinite(r[col]) and (col != "pe" or r[col] <= pe_max)]
        if len(xs) >= k_min:
            vals[col] = statistics.median(xs)
            cols[col] = {"after": vals[col], "n": len(xs), "how": "mediana_pares"}
        else:
            cols[col] = {"after": None, "n": len(xs), "how": "sin_dato"}
    return {"values": vals, "columns": cols, "n_peers": len(peers), "date": P["date"], "scope": scope,
            "n_region": n_region}


def reset() -> None:
    with _peers_lock:
        _peers.clear()
