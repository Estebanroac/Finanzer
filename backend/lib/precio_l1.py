"""
F16 (§8 de la prueba hacia atrás del 6-nov-2026): la etiqueta de precio es la regla L1.

  P/E de doce meses = capitalización / beneficio neto de los doce meses al ÚLTIMO periodo con estados presentado en
                      EDGAR (no al corte de Yahoo, que va con retraso: AMZN 45× frente a 35×, CI 21× frente a 11×).
  P/E relativo      = P/E / mediana del P/E (> 0) de su sector GICS en el universo (config/precio_l1.toml).
  Nivel             = tercio del P/E relativo en el universo: bajo «atractivo», alto «exigente», el resto «razonable».
  Puntuación        = 100 × (1 − percentil del P/E relativo en el universo): ≥ 66,7 atractivo, < 33,3 exigente.

Beneficio ≤ 0 o sin P/E: sin veredicto de precio, con el motivo. La confianza NO mueve el precio (decisión del usuario):
se sigue mostrando como fiabilidad de los datos. El DCF, el DCF inverso, los múltiplos frente al sector y los escenarios
se calculan y se muestran como lectura (`valuation_reading`), sin decidir la etiqueta.

`config/precio_l1.toml` (medianas por sector, cuantiles del P/E relativo y fecha) lo escribe
tools/precio_l1_universo.py con el P/E de este módulo en cada empresa del universo: el mismo número que aquí.
"""
import bisect
import datetime as _dt
import os
import tomllib
from typing import Any, Dict, List, Optional

RULE = "L1"
LABELS = ["atractivo", "razonable", "exigente"]
BANDS = [67, 34]                    # = thresholds.score.price_l1 (puntuación entera)
CONFIG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config", "precio_l1.toml")
_cfg_cache: Dict[str, Any] = {}


def load_config(path: str = CONFIG) -> Optional[Dict[str, Any]]:
    if path in _cfg_cache:
        return _cfg_cache[path]
    try:
        with open(path, "rb") as fh:
            c = tomllib.load(fh)
    except FileNotFoundError:
        c = None
    _cfg_cache[path] = c
    return c


def reset() -> None:
    _cfg_cache.clear()


# ═══════════════════════ beneficio de doce meses (EDGAR) ═══════════════════════
# La misma lectura que la línea base L1 de la prueba hacia atrás (datos_reales/scripts/edgar_lib.py), portada aquí:
#  · para el mismo periodo manda el hecho presentado más tarde;
#  · trimestres: directos (80–120 días) o diferencia de acumulados del mismo ejercicio; 4.º = anual − (T1+T2+T3);
#  · doce meses al último periodo: el anual, 4 trimestres o anual + acumulado − el del año anterior;
#  · conceptos en orden fijo de preferencia; si ninguno solo da los doce meses, la serie combinada; los emisores que
#    solo etiquetan el resultado consolidado (MA, AVGO, ITW): ProfitLoss − minoritarios.
NI_US = ("NetIncomeLossAvailableToCommonStockholdersBasic", "NetIncomeLoss",
         "NetIncomeLossAvailableToCommonStockholdersDiluted")
NI_IFRS = ("ProfitLossAttributableToOrdinaryEquityHoldersOfParentEntity", "ProfitLossAttributableToOwnersOfParent",
           "ProfitLoss")
# Conceptos que sec_edgar tiene que conservar al reducir companyfacts (lib/sec_edgar._WANTED).
EXTRA_US = ("ProfitLoss", "NetIncomeLossAttributableToNoncontrollingInterest")
END_KEYS = {"us-gaap": ("Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax",
                        "NetCashProvidedByUsedInOperatingActivities") + NI_US,
            "ifrs-full": ("Revenue", "CashFlowsFromUsedInOperatingActivities") + NI_IFRS}
PERIODIC_FORMS = {"10-K", "10-Q", "20-F", "40-F", "10-KT", "10-QT", "6-K", "10-K/A", "10-Q/A", "20-F/A", "40-F/A"}


def _D(s):
    return _dt.date.fromisoformat(str(s)[:10])


def _raw(facts, tax, concept, unit):
    return list((((facts.get("facts") or {}).get(tax) or {}).get(concept) or {}).get("units", {}).get(unit) or [])


def _dedup(fs):
    best = {}
    for f in fs:
        k = (f.get("start"), f["end"])
        if k not in best or str(f.get("filed", "")) > str(best[k].get("filed", "")):
            best[k] = f
    return best


class _Flow:
    def __init__(self, concept, fs):
        from collections import defaultdict
        self.concept = concept
        self.dur, self.ver = {}, defaultdict(list)
        for (s, e), f in _dedup([f for f in fs if f.get("start")]).items():
            self.dur[(_D(s), _D(e))] = (float(f["val"]), str(f.get("filed", "")))
        for f in fs:
            if f.get("start"):
                self.ver[(_D(f["start"]), _D(f["end"]))].append((str(f.get("filed", "")), float(f["val"])))
        for k in self.ver:
            self.ver[k].sort()
        self.q = self._quarters()

    def _as_of(self, key, filed):
        vs = self.ver.get(key) or []
        prev = [v for fd, v in vs if fd <= filed]
        return prev[-1] if prev else (vs[0][1] if vs else None)

    def _quarters(self):
        from collections import defaultdict
        q = {}
        for (s, e), (v, fd) in self.dur.items():
            if 80 <= (e - s).days + 1 <= 120:
                q[e] = (s, v, fd)
        by_start = defaultdict(list)
        for (s, e), (v, fd) in self.dur.items():
            if 80 <= (e - s).days + 1 <= 380:
                by_start[s].append((e, v, fd))
        for s, lst in by_start.items():
            lst.sort()
            for i, (e2, v2, f2) in enumerate(lst):
                if e2 in q:
                    continue
                prev = [(e1, v1, f1) for e1, v1, f1 in lst[:i] if 80 <= (e2 - e1).days <= 120]
                if prev:
                    e1, _v1, f1 = prev[-1]
                    q[e2] = (e1 + _dt.timedelta(days=1), v2 - self._as_of((s, e1), f2), max(f1, f2))
        for (s, e), (v, fd) in self.dur.items():
            if 350 <= (e - s).days + 1 <= 380 and e not in q:
                inner = sorted(x for x in q if s < x < e - _dt.timedelta(days=60) and q[x][0] >= s - _dt.timedelta(days=5))
                if len(inner) == 3:
                    q[e] = (inner[-1] + _dt.timedelta(days=1),
                            v - sum(self._as_of((q[x][0], x), fd) if (q[x][0], x) in self.ver else q[x][1]
                                    for x in inner), max([fd] + [q[x][2] for x in inner]))
        return q

    def _quarter_at(self, e, tol=8):
        for x in sorted(self.q, key=lambda x: abs((x - e).days)):
            return (x, self.q[x]) if abs((x - e).days) <= tol else (None, None)
        return None, None

    def _period(self, end, lo, hi, tol=6):
        for (s, e), (v, fd) in sorted(self.dur.items(), key=lambda kv: abs((kv[0][1] - end).days)):
            if abs((e - end).days) > tol:
                break
            if lo <= (e - s).days + 1 <= hi:
                return s, e, v
        return None

    def ttm(self, end):
        p = self._period(end, 350, 380)
        if p:
            return p[2], "anual"
        qs, e = [], end
        for _ in range(4):
            x, v = self._quarter_at(e)
            if x is None:
                break
            qs.append(v[1])
            e = v[0] - _dt.timedelta(days=1)
        if len(qs) == 4:
            return sum(qs), "4 trimestres"
        for (s, e2), (v, fd) in self.dur.items():
            if abs((e2 - end).days) <= 6 and 100 < (e2 - s).days + 1 < 350:
                ann = self._period(s - _dt.timedelta(days=1), 350, 380)
                prev = self._period(end - _dt.timedelta(days=365), (e2 - s).days + 1 - 8, (e2 - s).days + 1 + 8, tol=8)
                if ann and prev:
                    pv = self._as_of((prev[0], prev[1]), self.dur[(ann[0], ann[1])][1])
                    return ann[2] + v - pv, f"anual + acumulado {(e2 - s).days + 1} días − el del año anterior"
        return None, None


def last_period_end(facts, tax, unit):
    best = None
    for c in END_KEYS.get(tax, ()):
        for f in _raw(facts, tax, c, unit):
            if f.get("start") and f.get("form") in PERIODIC_FORMS:
                e = _D(f["end"])
                if (e - _D(f["start"])).days >= 80 and (best is None or e > best):
                    best = e
    return best


def ni_ttm(facts, end):
    """(valor, concepto, método) del beneficio neto atribuible de doce meses que terminan en `end`, o (None, …)."""
    import sec_edgar as edgar
    tax = edgar.taxonomy(facts)
    unit = edgar.reporting_unit(facts, tax)
    if tax is None or unit is None:
        return None, None, "sin taxonomía o moneda de los estados"
    names = NI_US if tax == "us-gaap" else NI_IFRS
    for c in names:
        fs = _raw(facts, tax, c, unit)
        if fs:
            v, how = _Flow(c, fs).ttm(end)
            if v is not None:
                return v, f"{tax}:{c}", how
    merged, used = {}, []
    for c in names:
        fs = [f for f in _raw(facts, tax, c, unit) if f.get("start")]
        if fs:
            used.append(c)
        for k, f in _dedup(fs).items():
            merged.setdefault(k, f)
    if len(used) > 1:
        v, how = _Flow("+".join(used), list(merged.values())).ttm(end)
        if v is not None:
            return v, f"{tax}:" + "+".join(used) + " (combinada)", how
    if tax == "us-gaap":
        pl = _dedup([f for f in _raw(facts, tax, "ProfitLoss", unit) if f.get("start")])
        nci = _dedup([f for f in _raw(facts, tax, "NetIncomeLossAttributableToNoncontrollingInterest", unit)
                      if f.get("start")])
        if pl:
            synth = []
            for k, f in pl.items():
                g = dict(f)
                g["val"] = float(f["val"]) - (float(nci[k]["val"]) if k in nci else 0.0)
                synth.append(g)
            v, how = _Flow("ProfitLoss − minoritarios", synth).ttm(end)
            if v is not None:
                return v, "us-gaap:ProfitLoss − NetIncomeLossAttributableToNoncontrollingInterest", how
    return None, None, "sin los doce meses"


def inputs(ed: Dict[str, Any], ctx=None) -> Dict[str, Any]:
    """Beneficio neto atribuible de doce meses al último periodo presentado en EDGAR, en la moneda de la cotización."""
    import sec_edgar as edgar
    if (ed or {}).get("status") != "ok" or not ed.get("facts"):
        return {"status": "sin_dato", "reason": "sin estados de SEC EDGAR"}
    facts = ed["facts"]
    tax = edgar.taxonomy(facts)
    unit = edgar.reporting_unit(facts, tax)
    end = last_period_end(facts, tax, unit) if tax and unit else None
    if end is None:
        return {"status": "sin_dato", "reason": "EDGAR no tiene un periodo presentado con ventas, beneficio o flujos"}
    val, concept, how = ni_ttm(facts, end)
    if val is None:
        return {"status": "sin_dato", "reason": f"EDGAR no da el beneficio de doce meses al último periodo ({end})"}
    conv = ctx.convert_amount(val, "flow", end=end) if ctx is not None else val
    return {"status": "ok", "ni_ttm": conv, "ni_ttm_statement": val, "statement_unit": unit, "end": str(end),
            "concept": concept, "method": how}


def pe(market_cap: Optional[float], inp: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    inp = inp or {}
    if inp.get("status") != "ok":
        return {"value": None, "reason": inp.get("reason") or "sin beneficio de doce meses"}
    ni = inp.get("ni_ttm")
    if not market_cap or market_cap <= 0:
        return {"value": None, "reason": "sin capitalización"}
    if ni is None:
        return {"value": None, "reason": "sin beneficio de doce meses"}
    if ni <= 0:
        return {"value": None, "reason": "beneficio de doce meses ≤ 0: el P/E no tiene sentido"}
    return {"value": market_cap / ni, "reason": None}


# Sector de Yahoo → sector GICS (los 11 de la tabla del S&P 500), solo para empresas fuera del universo.
YAHOO_TO_GICS = {"Technology": "Information Technology", "Healthcare": "Health Care",
                 "Financial Services": "Financials", "Consumer Cyclical": "Consumer Discretionary",
                 "Consumer Defensive": "Consumer Staples", "Energy": "Energy", "Industrials": "Industrials",
                 "Basic Materials": "Materials", "Real Estate": "Real Estate", "Utilities": "Utilities",
                 "Communication Services": "Communication Services"}


def gics_sector(symbol: Optional[str], yahoo_sector: Optional[str]) -> Optional[str]:
    """El sector GICS del universo (config/universe.tsv); fuera de él, el de Yahoo traducido."""
    try:
        import universe
        row = universe.get(symbol)
        if row and row.get("gics_sector"):
            return row["gics_sector"]
    except Exception:
        pass
    return YAHOO_TO_GICS.get(str(yahoo_sector or ""))


# ═══════════════════════ nivel ═══════════════════════

def _level(score: Optional[float]) -> Optional[str]:
    if score is None:
        return None
    for b, lab in zip(BANDS, LABELS):
        if score >= b:
            return lab
    return LABELS[-1]


def price(market_cap: Optional[float], inp: Optional[Dict[str, Any]], gics_sector: Optional[str],
          confidence_level: Optional[str] = None, config: Optional[Dict[str, Any]] = None,
          reading: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """price_attractiveness con la regla L1 (mismas claves que verdict.price para la vista y el PDF)."""
    c = config if config is not None else load_config()
    p = pe(market_cap, inp)
    out: Dict[str, Any] = {"rule": RULE, "pe_ttm": p["value"], "pe_basis": inp, "gics_sector": gics_sector,
                           "sector_median": None, "relative": None, "percentile": None, "as_of": None,
                           "universe_n": None, "score": None, "score_raw": None, "level": None, "level_raw": None,
                           "factor": None, "confidence": confidence_level, "contracted": False, "border": None,
                           "valuation_reading": reading, "reason": p["reason"]}
    if c is None:
        out["reason"] = "sin la referencia del universo (config/precio_l1.toml)"
        return out
    out.update(as_of=c.get("as_of"), universe_n=c.get("n"))
    if p["value"] is None:
        return out
    med = (c.get("sector_median") or {}).get(str(gics_sector or ""))
    if not med:
        out["reason"] = f"sin mediana del P/E de su sector GICS ({gics_sector or 'sin sector'}) en el universo"
        return out
    rel = p["value"] / med
    q: List[float] = c.get("relative_quantiles") or []
    if len(q) < 3:
        out["reason"] = "referencia del universo incompleta (sin cuantiles)"
        return out
    # percentil por interpolación lineal entre los cuantiles 0..100 (solo para la puntuación que se enseña)
    k = bisect.bisect_right(q, rel)
    if k <= 0:
        pct = 0.0
    elif k >= len(q):
        pct = 1.0
    else:
        lo, hi = q[k - 1], q[k]
        pct = ((k - 1) + ((rel - lo) / (hi - lo) if hi > lo else 0.0)) / (len(q) - 1)
    score = int(round(100 * (1 - pct)))
    # el nivel, con los dos cortes exactos de los tercios (la regla medida), no con la puntuación redondeada
    cuts = c.get("cuts") or []
    level = None if len(cuts) != 2 else ("atractivo" if rel <= cuts[0] else "exigente" if rel > cuts[1]
                                         else "razonable")
    out.update(sector_median=med, relative=rel, percentile=pct, score=score, score_raw=score, level=level,
               level_raw=level, reason=None if level else "referencia del universo sin cortes", cuts=cuts)
    from verdict import border
    out["border"] = border(score, BANDS, LABELS)
    return out


def reprice(p: Dict[str, Any], confidence_level: Optional[str]) -> Dict[str, Any]:
    """La confianza no mueve el precio (F16): solo se anota."""
    return {**p, "confidence": confidence_level}


# ═══════════════════════ referencia del universo ═══════════════════════

def build_reference(rows: List[Dict[str, Any]], as_of: str, source: str) -> Dict[str, Any]:
    """rows: {symbol, gics_sector, pe} (pe > 0 o None). Medianas por sector, cuantiles 0..100 del P/E relativo y los dos
    cortes de tercios (los de la prueba hacia atrás: rango < n/3 barata, ≥ 2n/3 cara)."""
    import statistics
    by: Dict[str, List[float]] = {}
    for r in rows:
        if r.get("pe") and r["pe"] > 0 and r.get("gics_sector"):
            by.setdefault(r["gics_sector"], []).append(r["pe"])
    med = {s: statistics.median(v) for s, v in sorted(by.items())}
    rel = sorted(r["pe"] / med[r["gics_sector"]] for r in rows
                 if r.get("pe") and r["pe"] > 0 and r.get("gics_sector") in med)
    n = len(rel)
    if n < 30:
        raise ValueError(f"universo insuficiente para la referencia L1 ({n} empresas con P/E)")

    def quant(p: float) -> float:
        x = p * (n - 1)
        i = int(x)
        return rel[i] if i + 1 >= n else rel[i] + (rel[i + 1] - rel[i]) * (x - i)
    import math
    cuts = [rel[math.ceil(n / 3) - 1], rel[math.ceil(2 * n / 3) - 1]]
    return {"as_of": as_of, "source": source, "n": n, "n_sector": {s: len(v) for s, v in sorted(by.items())},
            "sector_median": med, "cuts": cuts, "relative_quantiles": [quant(i / 100) for i in range(101)]}


def write_reference(ref: Dict[str, Any], path: str = CONFIG) -> None:
    def tv(v):
        if isinstance(v, str):
            return '"' + v.replace('"', '\\"') + '"'
        if isinstance(v, float):
            return repr(round(v, 6))
        if isinstance(v, list):
            return "[" + ", ".join(tv(x) for x in v) + "]"
        return str(v)
    lines = ["# F16 · referencia del universo para la etiqueta de precio L1 (lib/precio_l1.py).",
             "# GENERADO por tools/precio_l1_universo.py. No editar a mano.",
             f"as_of = {tv(ref['as_of'])}", f"source = {tv(ref['source'])}", f"n = {ref['n']}",
             f"cuts = {tv(ref['cuts'])}", f"relative_quantiles = {tv(ref['relative_quantiles'])}", "",
             "[sector_median]"]
    lines += [f"{tv(s)} = {tv(v)}" for s, v in ref["sector_median"].items()]
    lines += ["", "[n_sector]"] + [f"{tv(s)} = {v}" for s, v in ref["n_sector"].items()]
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    _cfg_cache.pop(path, None)
