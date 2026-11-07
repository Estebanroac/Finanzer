"""
F16 (§8 de la prueba hacia atrás del 6-nov-2026): la etiqueta de precio es la regla L1.

  P/E de doce meses = capitalización / beneficio neto de los doce meses al ÚLTIMO periodo con estados presentado en
                      EDGAR (no al corte de Yahoo, que va con retraso: AMZN 45× frente a 35×, CI 21× frente a 11×).
  P/E relativo      = P/E / mediana del P/E (> 0) de su grupo en el universo (config/precio_l1.toml).

F16 bis (7-nov-2026, «Fase 1 bis · integridad de datos que afecta a la L1»):
  · el beneficio es el NORMALIZADO de esos doce meses (sin discontinuadas ni partidas no recurrentes) y la mediana se
    calcula con la misma base; beneficio normalizado ≤ 0: sin etiqueta;
  · grupos: los REIT con P/FFO entre REIT, las financieras (bancos y aseguradoras) entre sí, las demás por sector GICS;
    un grupo con menos de `min_group` empresas, frente a todo el universo;
  · capitalización con las acciones del beneficio cuando la cotización cuenta otras (varias clases, fusión posterior);
  · aviso junto a la etiqueta si EDGAR tiene un informe posterior sin leer o si el periodo es antiguo (20-F).
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


def diluted_shares_at(facts: Dict[str, Any], end) -> Optional[float]:
    """F16 bis · 5: el promedio diluido de acciones (EDGAR) del periodo más corto que acaba en `end` (trimestre,
    semestre o ejercicio), en la clase de los estados; None sin dato."""
    import sec_edgar as edgar
    tax = edgar.taxonomy(facts)
    h = edgar.HISTORY["diluted_shares"]
    node = (facts.get("facts") or {}).get(tax) or {}
    e = _D(str(end))
    for c in (h[1] if tax == "us-gaap" else h[2]):
        best = None
        for f in node.get(c, {}).get("units", {}).get("shares") or []:
            if not f.get("start") or not f.get("val") or abs((_D(f["end"]) - e).days) > 8:
                continue
            days = (_D(f["end"]) - _D(f["start"])).days
            if 80 <= days <= 100 or 170 <= days <= 190 or 350 <= days <= 380:
                k = (-days, f.get("filed") or "")
                if best is None or k > best[0]:
                    best = (k, float(f["val"]))
        if best:
            return best[1]
    return None


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
    # F16 bis · 3: perímetro. El resultado de operaciones discontinuadas de esos doce meses (3M/Solventum, Honeywell)
    # sale del beneficio con el que se compara el precio.
    from settings import cfg
    tol = cfg("data.edgar.report_date_tolerance_days")
    disc = edgar.discontinued_ttm(facts, end, tol)
    disc_v = disc.get("value") if disc else None
    disc_conv = (ctx.convert_amount(disc_v, "flow", end=end) if ctx is not None else disc_v) if disc_v else None
    # F16 bis · 1: los cargos y las ventas no recurrentes de EDGAR de esos mismos doce meses (sec_edgar.charges_ttm), con
    # la prueba de recurrencia de normalize (mismo signo en ≥ recurrence_min_years de los últimos ejercicios: solo el
    # exceso sobre su promedio). Se usan cuando el corte de estados del motor no es este periodo.
    ch = edgar.charges_ttm(facts, end, tol)
    ch_adj = None
    if ch:
        # cargos (≤ 0) y ventas con ganancia (≥ 0) por separado, cada uno con normalize.recurrence: si se repite con el
        # mismo signo en ≥ recurrence_min_years de los últimos ejercicios, solo el exceso sobre su promedio
        from normalize import recurrence
        annual = ch.get("annual") or []
        parts = {k: recurrence(ch.get(k) or 0.0, [a.get(k) for a in annual]) for k in ("neg", "pos") if ch.get(k)}
        pre = sum(r["excess"] for r in parts.values())
        ch_adj = {"pretax": (ctx.convert_amount(pre, "flow", end=end) if (ctx is not None and pre) else pre),
                  "recurrent": {k: r["recurrent"] for k, r in parts.items()}, "detail": ch.get("detail")}
    # F16 bis · 4: un informe periódico posterior a ese periodo que los hechos aún no recogen
    newer = [f for f in edgar.newer_statements(ed.get("filings"), str(end))]
    pending = max(newer, key=lambda f: f.get("reportDate") or "") if newer else None
    return {"status": "ok", "ni_ttm": conv, "ni_ttm_statement": val, "statement_unit": unit, "end": str(end),
            "concept": concept, "method": how,
            "discontinued": disc_conv, "discontinued_concept": (disc or {}).get("concept") if disc_conv else None,
            "charges": ch_adj, "diluted_shares": diluted_shares_at(facts, end),
            "pending": ({"form": pending.get("form"), "report_date": pending.get("reportDate"),
                         "filed": pending.get("filingDate")} if pending else None)}


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


GROUP_REIT, GROUP_FIN = "REIT", "Financieras"


def group(archetype: Optional[str], gics: Optional[str]) -> Optional[str]:
    """F16 bis · 2: el grupo con cuya mediana se compara: los REIT entre REIT (P/FFO), las financieras (bancos y
    aseguradoras) entre financieras; las demás, su sector GICS."""
    if archetype == "REIT":
        return GROUP_REIT
    if archetype == "FINANCIAL":
        return GROUP_FIN
    return gics


def basis(market_cap: Optional[float], inp: Optional[Dict[str, Any]], archetype: Optional[str],
          key_metrics: Optional[Dict[str, Any]], norm: Optional[Dict[str, Any]],
          engine_cut: Optional[str], tol_days: int = 45, tax_rate: Optional[float] = None,
          currency: Optional[Dict[str, Any]] = None, cycle_peak: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """F16 bis · 1–4: el múltiplo con el que se aplica la regla L1.
      · REIT: P/FFO del motor (FFO de doce meses).
      · Demás: capitalización / beneficio NORMALIZADO de doce meses al último periodo presentado en EDGAR: el
        atribuible, sin las operaciones discontinuadas (perímetro) y sin las partidas no recurrentes que el motor
        normaliza en su corte de estados; si ese corte es otro periodo, los cargos y ventas no recurrentes que EDGAR
        declara para esos doce meses (con la misma prueba de recurrencia), después de impuestos.
      · Beneficio normalizado ≤ 0: sin etiqueta.
    Devuelve {status, multiple, metric, earnings, earnings_reported, pe_reported, normalized, notes, warning, reason}."""
    inp = inp or {}
    km = key_metrics or {}
    out: Dict[str, Any] = {"status": "sin_dato", "multiple": None, "metric": "P/E", "earnings": None,
                           "earnings_reported": None, "pe_reported": None, "normalized": False, "notes": [],
                           "shares_note": None, "market_cap": market_cap, "cycle_peak": None,
                           "warning": None, "reason": None, "edgar": inp}
    from settings import cfg
    T = cfg("thresholds.score.price_l1")
    pend = inp.get("pending")
    if pend:
        out["warning"] = (f"EDGAR ya tiene el {pend.get('form')} del periodo cerrado el {pend.get('report_date')} "
                          f"(presentado el {pend.get('filed')}), que el beneficio de doce meses aún no recoge")
    elif engine_cut and inp.get("end") and (_D(engine_cut) - _D(inp["end"])).days > T["stale_days"]:
        # F16 bis · 4: sin un informe posterior en EDGAR que usar (un 20-F sin trimestres en XBRL): se avisa
        out["warning"] = (f"el beneficio de doce meses es el del periodo cerrado el {inp['end']}, el último que EDGAR "
                          f"recoge; los estados del análisis llegan al {engine_cut}")
    # Fase 1 · pendientes (MU): una cíclica con el beneficio de doce meses muy por encima de la mediana de sus últimos
    # ejercicios (condición (a) de lib/earnings_peak.py) puede parecer barata por estar en la parte alta del ciclo
    cp = cycle_peak or {}
    if archetype == "CYCLICAL" and (cp.get("conditions") or {}).get("a"):
        out["cycle_peak"] = {"over": cp.get("ttm_over_median"), "years": cp.get("years")}
        txt = (f"cíclica con el beneficio de doce meses un {cp['ttm_over_median'] * 100:.0f} % por encima de la "
               f"mediana de sus {cp.get('years')} últimos ejercicios: el P/E puede ser bajo por estar en la parte "
               "alta del ciclo")
        out["warning"] = f"{out['warning']}; {txt}" if out.get("warning") else txt
    if archetype == "REIT":
        out["metric"] = "P/FFO"
        pf = km.get("p_ffo")
        if pf is None or pf <= 0:
            out["reason"] = "sin P/FFO con sentido (FFO de doce meses ≤ 0 o sin dato)"
            return out
        out.update(status="ok", multiple=pf)
        return out
    if inp.get("status") != "ok":
        out["reason"] = inp.get("reason") or "sin beneficio de doce meses"
        return out
    if not market_cap or market_cap <= 0:
        out["reason"] = "sin capitalización"
        return out
    # F16 bis · 5: la capitalización con las mismas acciones que el beneficio. En un emisor local (sin conversión de
    # moneda), un factor implícito sin fracción simple (currency.StatementContext, basis «implicito») es que la
    # cotización cuenta otras acciones que el balance: varias clases con unidades de la sociedad operativa (IBKR, BX,
    # TKO) o una fusión posterior al periodo (WAT). La capitalización de la L1 se rehace con las acciones del balance
    # (las del beneficio atribuible) y se dice. Solo emisores us-gaap sin conversión (los ADR, también los que presentan
    # en dólares como BP, ya tienen la capitalización en la clase de la cotización) y solo si EDGAR lo confirma: las
    # acciones del balance coinciden (± share_mismatch) con el promedio diluido de EDGAR del periodo del beneficio (si
    # no, la diferencia es un desdoblamiento que Yahoo aplica hacia atrás o un balance de otro periodo).
    cur = currency or {}
    sc = cur.get("share_class") or {}
    dsh = inp.get("diluted_shares")
    if (sc.get("basis") == "implicito" and not cur.get("converted") and sc.get("statement_shares")
            and sc.get("price_shares") and str(inp.get("concept") or "").startswith("us-gaap:") and dsh
            and abs(sc["statement_shares"] / dsh - 1) <= T["share_mismatch"]):
        ratio = sc["statement_shares"] / sc["price_shares"]
        if abs(ratio - 1) > T["share_mismatch"]:
            market_cap = market_cap * ratio
            out["market_cap"] = market_cap
            out["shares_note"] = (f"capitalización con las acciones del balance ({sc['statement_shares'] / 1e6:,.0f} M, "
                                  f"las del beneficio), no con las de la cotización "
                                  f"({sc['price_shares'] / 1e6:,.0f} M: otras clases o una operación posterior)")
    ni = inp.get("ni_ttm")
    out["earnings_reported"] = ni
    if ni is not None and ni > 0:
        out["pe_reported"] = market_cap / ni
    disc = inp.get("discontinued")
    base = ni - disc if (ni is not None and disc) else ni
    if disc:
        out["notes"].append("sin discontinuadas")
    adj = 0.0
    n = norm or {}
    same = bool(engine_cut and inp.get("end")) and abs(
        (_D(engine_cut) - _D(inp["end"])).days) <= tol_days
    applied = [i for i in n.get("items") or [] if i.get("applied") and i.get("net") is not None
               and not (disc and i.get("type") == "discontinuadas")]
    if same and n.get("used_in_score") and applied:
        adj = sum(float(i["net"]) for i in applied)
        out["normalized"] = bool(adj)
        if adj:
            out["notes"].append("sin partidas no recurrentes")
    elif not same and (inp.get("charges") or {}).get("pretax"):
        # el corte de estados del motor es otro periodo: los cargos y ventas no recurrentes de EDGAR de estos doce
        # meses, después de impuestos (tipo efectivo del análisis o el de config)
        from settings import cfg
        t = tax_rate if (tax_rate is not None and 0 <= tax_rate <= 0.5) else cfg("thresholds.normalization.default_tax_rate")
        adj = float(inp["charges"]["pretax"]) * (1 - t)
        out["normalized"] = True
        out["notes"].append("sin cargos ni ventas no recurrentes de EDGAR")
    earn = (base - adj) if base is not None else None
    out["earnings"] = earn
    if earn is None:
        out["reason"] = "sin beneficio de doce meses"
        return out
    if earn <= 0:
        out["reason"] = ("beneficio normalizado de doce meses ≤ 0: el P/E no tiene sentido" if (adj or disc)
                         else "beneficio de doce meses ≤ 0: el P/E no tiene sentido")
        return out
    out.update(status="ok", multiple=market_cap / earn)
    return out


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
          reading: Optional[Dict[str, Any]] = None, l1_basis: Optional[Dict[str, Any]] = None,
          gics: Optional[str] = None) -> Dict[str, Any]:
    """price_attractiveness con la regla L1 (mismas claves que verdict.price para la vista y el PDF). `gics_sector` es el
    grupo de comparación (group()); `l1_basis`, el múltiplo de basis() (sin él, P/E = capitalización / `inp`)."""
    c = config if config is not None else load_config()
    if l1_basis is not None:
        p = {"value": l1_basis.get("multiple"), "reason": l1_basis.get("reason")}
    else:
        p = pe(market_cap, inp)
    lb = l1_basis or {}
    out: Dict[str, Any] = {"rule": RULE, "pe_ttm": p["value"], "pe_basis": inp, "gics_sector": gics_sector,
                           "group": gics_sector, "gics": gics or gics_sector, "metric": lb.get("metric") or "P/E",
                           "pe_reported_l1": lb.get("pe_reported"), "normalized": lb.get("normalized"),
                           "basis_notes": lb.get("notes") or [], "warning": lb.get("warning"),
                           "shares_note": lb.get("shares_note"), "cycle_peak": lb.get("cycle_peak"),
                           "sector_median": None, "median_scope": None, "relative": None, "percentile": None,
                           "as_of": None,
                           "universe_n": None, "score": None, "score_raw": None, "level": None, "level_raw": None,
                           "factor": None, "confidence": confidence_level, "contracted": False, "border": None,
                           "valuation_reading": reading, "reference_alarm": [], "reason": p["reason"]}
    if c is None:
        out["reason"] = "sin la referencia del universo (config/precio_l1.toml)"
        return out
    out.update(as_of=c.get("as_of"), universe_n=c.get("n"))
    alarm = reference_alarm(c)
    if alarm:      # Fase 1 · pendientes: junto a la etiqueta, como aviso
        out["reference_alarm"] = alarm
        out["warning"] = "; ".join([w for w in (out.get("warning"),) if w] + alarm)
    if p["value"] is None:
        return out
    med = (c.get("sector_median") or {}).get(str(gics_sector or ""))
    if not med and c.get("market_median") and (gics_sector in (c.get("small_groups") or []) or
                                                gics_sector not in (c.get("n_sector") or {})):
        # F16 bis · 2: grupo con pocas empresas en el universo → la mediana de todo el universo
        med = c["market_median"]
        out["median_scope"] = "mercado"
    if not med:
        out["reason"] = f"sin mediana del {out['metric']} de su grupo ({gics_sector or 'sin sector'}) en el universo"
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
    key = lambda r: r.get("group") or r.get("gics_sector")      # F16 bis · 2: grupo (REIT, Financieras o sector)
    for r in rows:
        if r.get("pe") and r["pe"] > 0 and key(r):
            by.setdefault(key(r), []).append(r["pe"])
    from settings import cfg
    min_g = cfg("thresholds.score.price_l1.min_group") or 10
    small = sorted(s for s, v in by.items() if len(v) < min_g)
    market = statistics.median([x for v in by.values() for x in v]) if by else None
    med = {s: statistics.median(v) for s, v in sorted(by.items()) if s not in small}
    # F16 bis · 2: los grupos con menos de min_group empresas se comparan con la mediana de todo el universo
    rel = sorted(r["pe"] / (med.get(key(r)) or market) for r in rows if r.get("pe") and r["pe"] > 0 and key(r) in by)
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
            "sector_median": med, "market_median": market, "small_groups": small, "min_group": min_g,
            "cuts": cuts, "relative_quantiles": [quant(i / 100) for i in range(101)]}


def reference_alarm(c: Optional[Dict[str, Any]], today: Optional[_dt.date] = None) -> List[str]:
    """Fase 1 · pendientes (decisión del usuario, 7-nov-2026): alarma de la referencia del universo. Más de
    `max_age_days` desde su fecha, o los mismos cortes que en la actualización anterior (un escaneo repetido o en
    caché). [] si está bien; sin referencia, eso ya se dice en el precio."""
    if not c:
        return []
    from settings import cfg
    out = []
    lim = cfg("thresholds.score.price_l1.max_age_days")
    try:
        age = ((today or _dt.date.today()) - _dt.date.fromisoformat(str(c.get("as_of")))).days
    except ValueError:
        age = None
    if age is None or age > lim:
        out.append(f"la referencia del universo es del {c.get('as_of')} ({age} días; más de {lim}): hay que actualizarla"
                   if age is not None else "la referencia del universo no tiene fecha válida")
    prev = c.get("previous_cuts")
    if prev and c.get("cuts") and [round(x, 6) for x in prev] == [round(x, 6) for x in c["cuts"]]:
        out.append(f"los cortes de la referencia ({c['cuts'][0]:.3f} y {c['cuts'][1]:.3f}) no cambiaron respecto a la "
                   f"actualización anterior ({c.get('previous_as_of')}): comprobar que el escaneo es nuevo")
    return out


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
             f"market_median = {tv(ref.get('market_median'))}", f"small_groups = {tv(ref.get('small_groups') or [])}",
             f"cuts = {tv(ref['cuts'])}",
             # Fase 1 · pendientes: los cortes y la fecha de la referencia anterior, para la alarma (reference_alarm)
             *([f"previous_as_of = {tv(ref['previous_as_of'])}", f"previous_cuts = {tv(ref['previous_cuts'])}"]
               if ref.get("previous_cuts") else []),
             f"relative_quantiles = {tv(ref['relative_quantiles'])}", "",
             "[sector_median]"]
    lines += [f"{tv(s)} = {tv(v)}" for s, v in ref["sector_median"].items()]
    lines += ["", "[n_sector]"] + [f"{tv(s)} = {v}" for s, v in ref["n_sector"].items()]
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    _cfg_cache.pop(path, None)
