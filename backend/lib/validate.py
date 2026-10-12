"""
Capa de validación de entrada (etapa 3 del rediseño; el "séptimo cambio" del
Apéndice del spec).

Se ejecuta DESPUÉS de la ingesta (yf_adapter.get_ticker_info: Yahoo o plan B
+ último-bueno-conocido + Finnhub) y ANTES de cualquier cálculo del motor:
todo lo que consumen data_fetcher y main.py sale del dict ya validado.

Política (igual para todas las reglas):
  · Si el dato se puede recalcular POR DEFINICIÓN desde los estados
    financieros, se recalcula y se marca  -> action "recalculado".
  · Si no, pasa a None ("sin dato") con flag y motivo -> action "sin_dato".
  · Si la regla solo detecta una sospecha y no hay base para corregir, se deja
    el valor y se emite un aviso                  -> action "aviso".
  · Nunca se corrige en silencio: cada intervención queda en info["_validation"]
    y en la procedencia del campo (info["_provenance"]).

Además, validate_outputs() aplica las reglas que solo tienen sentido sobre
valores YA calculados (múltiplos negativos → "no significativo"). Se aplica al
resultado final para presentación, sin alterar las entradas del score.

Los umbrales viven en THRESHOLDS (en la etapa 4 pasarán a YAML).
"""
from typing import Any, Dict, List, Optional

# ═══════════════════════════ umbrales (único lugar) ═══════════════════════════
THRESHOLDS: Dict[str, float] = {
    # FCF <= OCF (mismo periodo). Tolerancia absoluta por redondeos de la fuente.
    "fcf_over_ocf_tolerance_abs": 1e6,
    # Márgenes válidos: [-1000%, 100%] (en decimal).
    "margin_min": -10.0,
    "margin_max": 1.0,
    # Saltos interanuales (FY actual / FY previo) considerados anómalos.
    "revenue_jump_ratio_max": 5.0,
    "revenue_jump_ratio_min": 0.2,
    "net_income_jump_ratio_max": 20.0,    # mismo signo, |actual/previo|
    "net_income_jump_ratio_min": 0.05,
    # Acciones: fuera de [0.5x, 2x] entre ejercicios -> sospecha de base de split.
    "shares_ratio_min": 0.5,
    "shares_ratio_max": 2.0,
    "split_match_tolerance": 0.15,        # |ratio / factor − 1|
    # Unidades: |crecimiento| > 1000% o yield > 50% delatan escala porcentual.
    "growth_units_abs_max": 10.0,
    "dividend_yield_max": 0.5,
    "payout_ratio_max": 10.0,
}

# Campos que, si se anulan o recalculan, invalidan derivados que se recalculan
# o anulan con ellos (procedencia coherente).
_PRIOR_DERIVED = {
    "revenue": ("asset_turnover", "gross_margin"),
    "net_income": ("roa",),
}


# ═══════════════════════════ utilidades ═══════════════════════════
def _num(v) -> Optional[float]:
    try:
        if v is None or isinstance(v, bool):
            return None
        f = float(v)
        return f if f == f and f not in (float("inf"), float("-inf")) else None
    except (TypeError, ValueError):
        return None


def _first(seq) -> Optional[float]:
    return _num(seq[0]) if seq else None


def _at(seq, i) -> Optional[float]:
    return _num(seq[i]) if seq and len(seq) > i else None


class _Ctx:
    def __init__(self, info: Dict[str, Any], symbol: str):
        self.info = info
        self.symbol = symbol
        self.flags: List[Dict[str, Any]] = []
        self.prov = info.setdefault("_provenance", {})

    def flag(self, field, rule, action, old, new, reason):
        self.flags.append({"field": field, "rule": rule, "action": action,
                           "old": old, "new": new, "reason": reason})
        if action == "recalculado":
            self.prov[field] = {"source": "recalculado_por_validacion", "rule": rule, "detail": reason}
        elif action == "sin_dato":
            self.prov[field] = {"source": "sin_dato", "rule": rule, "detail": reason}

    # acceso a campos con ruta "a.b"
    def get(self, path):
        cur = self.info
        for p in path.split("."):
            if not isinstance(cur, dict):
                return None
            cur = cur.get(p)
        return cur

    def set(self, path, value):
        parts = path.split(".")
        cur = self.info
        for p in parts[:-1]:
            nxt = cur.get(p)
            if not isinstance(nxt, dict):
                nxt = {}
                cur[p] = nxt
            cur = nxt
        cur[parts[-1]] = value

    @property
    def stm(self) -> Dict[str, Any]:
        return self.info.get("_statements_fy") or {}


# ═══════════════════════════ reglas de entrada ═══════════════════════════
def _rule_fcf(c: _Ctx):
    """FCF <= OCF. Si se viola: FCF = OCF − |capex| del estado de flujos (mismo FY)."""
    fcf, ocf = _num(c.get("freeCashflow")), _num(c.get("operatingCashflow"))
    if fcf is None or ocf is None or fcf <= ocf + THRESHOLDS["fcf_over_ocf_tolerance_abs"]:
        return
    s = c.stm
    s_ocf, s_capex = _first(s.get("operating_cash_flow")), _first(s.get("capital_expenditure"))
    year = (s.get("cf_years") or ["?"])[0]
    if s_ocf is not None and s_capex is not None:
        new = s_ocf - abs(s_capex)
        c.set("freeCashflow", new)
        c.flag("freeCashflow", "fcf_le_ocf", "recalculado", fcf, new,
               f"FCF ({fcf:,.0f}) > OCF ({ocf:,.0f}): imposible por definición. Recalculado como "
               f"OCF − capex del estado de flujos FY{year}")
    else:
        c.set("freeCashflow", None)
        c.flag("freeCashflow", "fcf_le_ocf", "sin_dato", fcf, None,
               f"FCF ({fcf:,.0f}) > OCF ({ocf:,.0f}) y sin estado de flujos para recalcularlo")


def _rule_impossible(c: _Ctx):
    """Valores imposibles: activos, acciones, capitalización y precio <= 0."""
    s = c.stm
    price, mcap, shares = (_num(c.get(k)) for k in ("currentPrice", "marketCap", "sharesOutstanding"))
    for field, val in (("totalAssets", _num(c.get("totalAssets"))),):
        if val is not None and val <= 0:
            alt = _first(s.get("total_assets"))
            if alt is not None and alt > 0:
                c.set(field, alt)
                c.flag(field, "valor_imposible", "recalculado", val, alt,
                       "activos <= 0: se toma Total Assets del último balance anual")
            else:
                c.set(field, None)
                c.flag(field, "valor_imposible", "sin_dato", val, None, "activos <= 0")
    if shares is not None and shares <= 0:
        new = (mcap / price) if (mcap and price and mcap > 0 and price > 0) else None
        c.set("sharesOutstanding", new)
        c.flag("sharesOutstanding", "valor_imposible", "recalculado" if new else "sin_dato", shares, new,
               "acciones <= 0" + (": recalculado como capitalización / precio" if new else ""))
    if mcap is not None and mcap <= 0:
        sh = _num(c.get("sharesOutstanding"))
        new = (price * sh) if (price and sh and price > 0 and sh > 0) else None
        c.set("marketCap", new)
        c.flag("marketCap", "valor_imposible", "recalculado" if new else "sin_dato", mcap, new,
               "capitalización <= 0" + (": recalculada como precio × acciones" if new else ""))
    if price is not None and price <= 0:
        for k in ("currentPrice", "regularMarketPrice"):
            if c.get(k) is not None:
                c.set(k, None)
        c.flag("currentPrice", "valor_imposible", "sin_dato", price, None, "precio <= 0")


def _rule_margins(c: _Ctx):
    """Márgenes fuera de [-1000%, 100%]: los precalculados de la fuente se
    descartan (el motor los recalcula desde componentes) y, si un componente
    implica un margen imposible, ese componente pasa a sin dato."""
    lo, hi = THRESHOLDS["margin_min"], THRESHOLDS["margin_max"]
    for k in ("grossMargins", "operatingMargins", "profitMargins", "ebitdaMargins"):
        path = f"_yahoo_ratios.{k}"
        v = _num(c.get(path))
        if v is not None and not (lo <= v <= hi):
            c.set(path, None)
            c.flag(path, "margen_fuera_de_rango", "sin_dato", v, None,
                   f"margen {v:.1%} fuera de [-1000%, 100%]; el motor lo recalcula desde componentes")
    rev = _num(c.get("totalRevenue"))
    if rev is None or rev <= 0:
        return
    for k, label in (("grossProfits", "bruto"), ("operatingIncome", "operativo"),
                     ("netIncome", "neto"), ("ebitda", "EBITDA")):
        v = _num(c.get(k))
        if v is not None and not (lo <= v / rev <= hi):
            c.set(k, None)
            c.flag(k, "margen_fuera_de_rango", "sin_dato", v, None,
                   f"margen {label} implícito {v / rev:.1%} fuera de [-1000%, 100%]")


def _rule_units(c: _Ctx):
    """Coherencia de unidades (decimal vs porcentaje)."""
    t = THRESHOLDS
    price = _num(c.get("currentPrice"))
    for path in ("dividendYield", "_yahoo_ratios.dividendYield"):
        v = _num(c.get(path))
        if v is not None and v > t["dividend_yield_max"]:
            rate = _num(c.get("dividendRate"))
            new = (rate / price) if (rate is not None and price) else None
            ok = new is not None and 0 <= new <= t["dividend_yield_max"]
            c.set(path, new if ok else None)
            c.flag(path, "unidades", "recalculado" if ok else "sin_dato", v, new if ok else None,
                   f"yield {v} > 50%: escala porcentual" + (": recalculado como dividendo / precio" if ok else ""))
    for path in ("payoutRatio", "_yahoo_ratios.payoutRatio"):
        v = _num(c.get(path))
        if v is not None and abs(v) > t["payout_ratio_max"]:
            c.set(path, None)
            c.flag(path, "unidades", "sin_dato", v, None, f"payout {v} > 1000%: unidades incoherentes")
    for path in ("revenueGrowth", "earningsGrowth"):
        v = _num(c.get(path))
        if v is not None and abs(v) > t["growth_units_abs_max"]:
            c.set(path, None)
            c.flag(path, "unidades", "sin_dato", v, None, f"crecimiento {v} (> 1000%): escala porcentual")


def _split_factor(raw) -> Optional[float]:
    """'10:1' -> 10.0 ; '1:10' -> 0.1 ; None si no se puede interpretar."""
    if not raw or not isinstance(raw, str) or ":" not in raw:
        return None
    a, b = raw.split(":", 1)
    a, b = _num(a), _num(b)
    return (a / b) if (a and b) else None


def _rule_split_basis(c: _Ctx):
    """Acciones del FY actual y del previo en la MISMA base antes de comparar."""
    t = THRESHOLDS
    cur, prev = _num(c.get("_piotroski_current.shares")), _num(c.get("_prior_year.shares"))
    if cur is None or prev is None or prev <= 0:
        return
    r = cur / prev
    if t["shares_ratio_min"] <= r <= t["shares_ratio_max"]:
        return
    f = _split_factor(c.info.get("lastSplitFactor"))
    if f and abs(r / f - 1.0) <= t["split_match_tolerance"]:
        c.set("_prior_year.shares", prev * f)
        c.flag("_prior_year.shares", "base_de_split", "recalculado", prev, prev * f,
               f"acciones ×{r:.2f} entre ejercicios ≈ split {c.info.get('lastSplitFactor')}: "
               f"año previo llevado a la base actual")
    else:
        c.set("_prior_year.shares", None)
        c.flag("_prior_year.shares", "base_de_split", "sin_dato", prev, None,
               f"acciones ×{r:.2f} entre ejercicios sin un factor de split que lo explique")


def _rule_jumps(c: _Ctx):
    """Saltos interanuales anómalos en ingresos y beneficio (estados FY)."""
    t, s = THRESHOLDS, c.stm
    for key, series, hi, lo, same_sign in (
            ("revenue", s.get("revenue"), t["revenue_jump_ratio_max"], t["revenue_jump_ratio_min"], False),
            ("net_income", s.get("net_income"), t["net_income_jump_ratio_max"], t["net_income_jump_ratio_min"], True)):
        a, b = _at(series, 0), _at(series, 1)
        if a is None or b is None or b == 0 or a == 0:
            continue
        if same_sign and (a > 0) != (b > 0):
            continue  # cambio de signo: normal en beneficio, no se evalúa como salto
        r = abs(a / b)
        if lo <= r <= hi:
            continue
        old = c.get(f"_prior_year.{key}")
        c.set(f"_prior_year.{key}", None)
        c.flag(f"_prior_year.{key}", "salto_interanual", "sin_dato", old, None,
               f"{key} FY actual/previo = ×{r:.2f} fuera de [{lo}, {hi}]: comparación interanual no fiable")
        for dep in _PRIOR_DERIVED.get(key, ()):
            dv = c.get(f"_prior_year.{dep}")
            if dv is not None:
                c.set(f"_prior_year.{dep}", None)
                c.flag(f"_prior_year.{dep}", "salto_interanual", "sin_dato", dv, None,
                       f"derivado de _prior_year.{key}, anulado por salto interanual")


_INPUT_RULES = (_rule_fcf, _rule_impossible, _rule_margins, _rule_units,
                _rule_split_basis, _rule_jumps)


def validate_info(info: Dict[str, Any], symbol: str = "") -> Dict[str, Any]:
    """Valida (en sitio) el dict de ingesta y devuelve el mismo dict.

    Deja la lista de intervenciones en info["_validation"] (se reemplaza en
    cada ejecución) y actualiza info["_provenance"]."""
    if not isinstance(info, dict) or not info:
        return info
    c = _Ctx(info, symbol)
    for rule in _INPUT_RULES:
        rule(c)
    info["_validation"] = c.flags
    return info


# ═══════════════════════════ reglas de salida ═══════════════════════════
NON_SIGNIFICANT_MULTIPLES = ("pe", "ev_ebitda", "p_ffo")


def validate_outputs(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Múltiplos <= 0 (P/E, EV/EBITDA, P/FFO) no son múltiplos válidos: pasan a
    None ("no significativo") en lo que se presenta (key_metrics y ratios). Se
    aplica al final, así que no altera las entradas del score ni de las alertas
    (que ya tratan esos casos como 'sin beneficios')."""
    flags = []
    for block in ("key_metrics", "ratios"):
        d = result.get(block) or {}
        for k in NON_SIGNIFICANT_MULTIPLES:
            v = _num(d.get(k))
            if v is not None and v <= 0:
                d[k] = None
                denom = {"pe": "beneficio", "ev_ebitda": "EBITDA", "p_ffo": "FFO"}[k]
                flags.append({"field": f"{block}.{k}", "rule": "multiplo_no_significativo",
                              "action": "sin_dato", "old": v, "new": None,
                              "reason": f"{k.upper()} = {v:.1f}: {denom} <= 0, el múltiplo no es significativo"})
    return flags
