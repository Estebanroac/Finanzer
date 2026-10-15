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
  · Si el valor se sustituye por POLÍTICA del arquetipo (no porque sea erróneo),
    se marca                                      -> action "politica" (no cuenta
    como incidencia de la calidad de fuente).
  · Nunca se corrige en silencio: cada intervención queda en info["_validation"]
    y en la procedencia del campo (info["_provenance"]).

Además, validate_outputs() aplica las reglas que solo tienen sentido sobre
valores YA calculados (múltiplos negativos → "no significativo"). Se aplica al
resultado final para presentación, sin alterar las entradas del score.

Los umbrales viven en backend/config/validation.toml (etapa 4) y se exponen
aquí como THRESHOLDS.
"""
from typing import Any, Dict, List, Optional, Tuple

from settings import cfg

# ═══════════════════════════ umbrales (único lugar) ═══════════════════════════
THRESHOLDS: Dict[str, float] = dict(cfg("validation.thresholds"))

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
        elif action == "politica":
            self.prov[field] = {"source": "politica_arquetipo", "rule": rule, "detail": reason}
        elif action in ("sin_dato", "invalido"):
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


# ═══════════════════════════ guarda de crecimiento (compartida) ═══════════════════════════
def growth_guard(ttm_pct, cagr3_pct, cagr5_pct) -> Optional[float]:
    """YoY en DECIMAL con guarda anti-artefacto. Entradas en PORCENTAJE.

    Regla (originalmente en finnhub_fallback._growth, ahora compartida): un
    hipercrecimiento real muestra un CAGR multi-año comparable; un artefacto
    (p. ej. 'revenue' bancario con definición cambiante) no. Se acepta el YoY
    si |YoY| <= 60% o |YoY| <= 3 × |CAGR-5Y (o 3Y)|; si no, se usa el CAGR-3Y.
    """
    t = THRESHOLDS
    ttm, c3, c5 = _num(ttm_pct), _num(cagr3_pct), _num(cagr5_pct)
    lt = c5 if c5 is not None else c3
    if ttm is not None:
        if abs(ttm) <= t["growth_artifact_abs_pct"] or (
                lt is not None and abs(ttm) <= t["growth_artifact_lt_multiple"] * abs(lt)):
            return ttm / 100.0
    if c3 is not None:
        return c3 / 100.0
    return None


def _cagr(series, years) -> Optional[float]:
    a, b = _at(series, 0), _at(series, years)
    if a is None or b is None or a <= 0 or b <= 0:
        return None
    return (a / b) ** (1.0 / years) - 1.0


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


def _rule_growth(c: _Ctx):
    """Crecimiento de ingresos: guarda anti-artefacto (la de finnhub_fallback)
    en TODAS las rutas, con el CAGR de los estados anuales; y coherencia con el
    YoY de los estados (sustitución solo en financieras, RECON C6)."""
    g = _num(c.get("revenueGrowth"))
    if g is None:
        return
    rev = c.stm.get("revenue") or []
    c3, c5 = _cagr(rev, 3), _cagr(rev, 4)  # 4 intervalos = máximo disponible (~5 ejercicios)
    guarded = growth_guard(g * 100.0, None if c3 is None else c3 * 100.0, None if c5 is None else c5 * 100.0)
    if guarded is None:
        c.set("revenueGrowth", None)
        c.flag("revenueGrowth", "crecimiento_artefacto", "sin_dato", g, None,
               "YoY implausible y sin CAGR de los estados para sustituirlo")
        return
    if abs(guarded - g) > 1e-12:
        c.set("revenueGrowth", guarded)
        c.flag("revenueGrowth", "crecimiento_artefacto", "recalculado", g, guarded,
               f"YoY {g:.1%} implausible frente al CAGR de los estados: se usa CAGR-3Y {guarded:.1%}")
        g = guarded
    r0, r1 = _at(rev, 0), _at(rev, 1)
    if r0 is None or r1 is None or r1 <= 0:
        return
    stmt_yoy = r0 / r1 - 1.0
    year = (c.stm.get("inc_years") or ["?"])[0]
    # Arquetipo FINANCIAL (clasificador único, etapa 6): el crecimiento sale
    # SIEMPRE de los estados, no de la fuente (RECON §7.8: el 'revenue' bancario
    # de Finnhub/quoteSummary tiene otra definición), aunque difieran poco.
    from classify import FINANCIAL, classify
    arch = classify(sector=c.info.get("sector"), industry=c.info.get("industry"), eps_ttm=None,
                    net_margin_ttm=None, statements_fy=c.stm)["archetype"]
    if arch == FINANCIAL:
        if abs(g - stmt_yoy) > 1e-12:
            c.set("revenueGrowth", stmt_yoy)
            # Etapa 9a: sustitución de POLÍTICA del arquetipo, no una corrección de un dato
            # erróneo: queda registrada ("politica") pero no cuenta como incidencia de fuente.
            c.flag("revenueGrowth", "crecimiento_financiera_estados", "politica", g, stmt_yoy,
                   f"arquetipo FINANCIAL: 'revenue' de la fuente con definición inestable (RECON C6, §7.8); "
                   f"se usa siempre el YoY de los estados FY{year} ({stmt_yoy:.1%}) en lugar de {g:.1%}")
        return
    if abs(g - stmt_yoy) <= THRESHOLDS["growth_vs_statements_pp"]:
        return
    else:
        c.flag("revenueGrowth", "crecimiento_incoherente", "aviso", g, g,
               f"{g:.1%} difiere más de 15 pp del YoY de los estados FY{year} ({stmt_yoy:.1%}); "
               f"puede ser aceleración real del último trimestre: se mantiene")


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


_P = cfg("validation.plausibility")


def _rule_per_share_plausibility(c: _Ctx):
    """Etapa 11b: múltiplos por acción imposibles delatan unidades mezcladas (otra clase de
    acciones u otra moneda). Se marcan inválidos y no puntúan; nunca se corrigen en silencio.
      · P/E fuera de [pe_min, pe_max];
      · P/B por debajo de pb_min;
      · BPA × acciones lejos del beneficio neto (más de eps_vs_net_income_max_dev)."""
    price = _num(c.get("currentPrice")) or _num(c.get("regularMarketPrice"))
    eps, shares = (_num(c.get(k)) for k in ("trailingEps", "sharesOutstanding"))
    bad_eps = None
    if price and eps and eps > 0:
        pe = price / eps
        if pe < _P["pe_min"] or pe > _P["pe_max"]:
            bad_eps = ("pe_implausible", f"P/E de {pe:,.4g}x (precio {price:,.2f} / BPA {eps:,.4g}) fuera de "
                                         f"[{_P['pe_min']:g}x, {_P['pe_max']:g}x]: BPA en otra clase o moneda")
    # Beneficio de la misma fuente y ventana que el BPA (lo deja la ingesta). Sin él no se
    # compara: un BPA TTM de Yahoo frente al TTM de los estados (un trimestre atrás) da falsos
    # positivos en empresas que crecen deprisa (MU: 67 % sin error de unidades).
    ni = _num(c.get("_eps_net_income"))
    if bad_eps is None and eps and shares and ni:
        dev = abs(eps * shares - ni) / abs(ni)
        if dev > _P["eps_vs_net_income_max_dev"]:
            bad_eps = ("bpa_incoherente", f"BPA × acciones = {eps * shares:,.4g} frente a un beneficio neto de "
                                          f"{ni:,.4g} (desviación {dev:.0%} > "
                                          f"{_P['eps_vs_net_income_max_dev']:.0%}): BPA en otra clase o moneda")
    if bad_eps is not None:
        rule, why = bad_eps
        c.set("trailingEps", None)
        c.flag("trailingEps", rule, "invalido", eps, None, why + "; no puntúa")
        if c.get("trailingPE") is not None:
            c.flag("trailingPE", rule, "invalido", c.get("trailingPE"), None, "P/E de la fuente sobre el mismo BPA; "
                                                                           "no puntúa")
            c.set("trailingPE", None)
    bv = _num(c.get("bookValue"))
    if price and bv and bv > 0 and price / bv < _P["pb_min"]:
        c.set("bookValue", None)
        c.flag("bookValue", "pb_implausible", "invalido", bv, None,
               f"P/B de {price / bv:.4g}x < {_P['pb_min']:g}x: valor en libros por acción en otra clase o moneda; "
               "no puntúa")
    for path in ("_yahoo_ratios.priceToBook", "priceToBook"):
        pb = _num(c.get(path))
        if pb is not None and 0 < pb < _P["pb_min"]:
            c.set(path, None)
            c.flag(path, "pb_implausible", "invalido", pb, None,
                   f"P/B de la fuente de {pb:.4g}x < {_P['pb_min']:g}x: mezcla clases o monedas; no puntúa")


# Etapa 11b: nombre de Yahoo de cada fila requerida (texto del aviso).
_ROW_NAMES = {"revenue": "Total Revenue", "net_income": "Net Income", "total_assets": "Total Assets",
              "stockholders_equity": "Stockholders Equity", "operating_cash_flow": "Operating Cash Flow",
              "capital_expenditure": "Capital Expenditure", "depreciation_amortization": "Depreciation And Amortization",
              "stock_based_compensation": "Stock Based Compensation", "ebitda": "EBITDA"}


def missing_key_rows(statements_fy: Optional[Dict[str, Any]], archetype: Optional[str]) -> List[Dict[str, Any]]:
    """Avisos por filas de los estados anuales que el arquetipo necesita y no llegaron (ni con su
    nombre alternativo IFRS). Se calcula tras clasificar: depende del arquetipo."""
    st = statements_fy or {}
    req = cfg("validation.required_rows")
    keys = list(req["common"]) + [k for k in (req.get(archetype or "") or []) if k not in req["common"]]
    flags = []
    for k in keys:
        if not any(v is not None for v in (st.get(k) or [])):
            flags.append({"field": f"_statements_fy.{k}", "rule": "fila_clave_ausente", "action": "aviso",
                          "old": None, "new": None,
                          "reason": f"falta la fila '{_ROW_NAMES.get(k, k)}' en los estados anuales (ni con su nombre "
                                    "alternativo IFRS): los componentes que la usan quedan sin dato"})
    return flags


_INPUT_RULES = (_rule_fcf, _rule_impossible, _rule_margins, _rule_units,
                _rule_growth, _rule_split_basis, _rule_jumps, _rule_per_share_plausibility)


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


def dividend_yield_identity(dy: Optional[float], dividends_paid: Optional[float], market_cap: Optional[float],
                            payout: Optional[float] = None, earnings_yield: Optional[float] = None
                            ) -> Tuple[bool, Optional[float], Optional[str]]:
    """Fase 1 (guardián de identidades, datos frente a datos): el dividend yield frente a lo que la empresa paga.

    Estimación: dividendos pagados del último ejercicio / capitalización (base caja); sin dividendos pagados,
    payout × rentabilidad del beneficio (E/P), que es la misma identidad por otra vía. El yield no cuadra si supera
    `dividend_identity_max_ratio` veces la estimación. Devuelve (cuadra, estimación, base). Sin estimación (o sin
    dividendo), no hay nada que comprobar: cuadra."""
    if dy is None or dy <= 0:
        return True, None, None
    est, basis = None, None
    if dividends_paid is not None and dividends_paid > 0 and market_cap:
        est, basis = dividends_paid / market_cap, "dividendos pagados / capitalización"
    elif payout is not None and payout > 0 and earnings_yield is not None and earnings_yield > 0:
        est, basis = payout * earnings_yield, "payout × E/P"
    if est is None:
        return True, None, None
    return dy <= THRESHOLDS["dividend_identity_max_ratio"] * est, est, basis


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
                # Etapa 11b: nombre legible y signo tipográfico (el texto llega al informe).
                name = {"pe": "P/E", "ev_ebitda": "EV/EBITDA", "p_ffo": "P/FFO"}[k]
                flags.append({"field": f"{block}.{k}", "rule": "multiplo_no_significativo",
                              "action": "sin_dato", "old": v, "new": None,
                              "reason": f"{name} de {v:.1f}x".replace("-", "−")
                                        + f": {denom} ≤ 0, el múltiplo no es significativo"})
    # Regla M aplicada a la cobertura de intereses (etapa 5): EBIT < 0 con caja
    # neta -> la ratio no es significativa (los intereses se pagan con caja).
    km = result.get("key_metrics") or {}
    # Fase 1: EBIT > 0 con ingresos financieros netos -> una cobertura negativa no es una ratio con sentido.
    if km.get("interest_coverage_state") == "sin_carga":
        for block in ("key_metrics", "ratios"):
            d = result.get(block) or {}
            v = _num(d.get("interest_coverage"))
            if v is not None and v < 0:
                d["interest_coverage"] = None
                flags.append({"field": f"{block}.interest_coverage", "rule": "ratio_no_significativa",
                              "action": "sin_dato", "old": v, "new": None,
                              "reason": f"Cobertura de intereses = {v:.1f}x".replace("-", "−")
                                        + ": EBIT > 0 y los ingresos financieros superan a los gastos (sin carga "
                                          "financiera neta), la ratio no es significativa"})
    if km.get("interest_coverage_state") == "no_significativo":
        for block in ("key_metrics", "ratios"):
            d = result.get(block) or {}
            v = _num(d.get("interest_coverage"))
            if v is not None:
                d["interest_coverage"] = None
                flags.append({"field": f"{block}.interest_coverage", "rule": "ratio_no_significativa",
                              "action": "sin_dato", "old": v, "new": None,
                              "reason": f"Cobertura de intereses = {v:.1f}x: EBIT < 0 con caja neta, "
                                        "la ratio no es significativa"})
    # Regla M aplicada a deuda neta/EBITDA: con EBITDA <= 0 no es significativa.
    if km.get("net_debt_to_ebitda_state") == "no_significativo":
        for block in ("key_metrics", "ratios"):
            d = result.get(block) or {}
            v = _num(d.get("net_debt_to_ebitda"))
            if v is not None:
                d["net_debt_to_ebitda"] = None
                flags.append({"field": f"{block}.net_debt_to_ebitda", "rule": "ratio_no_significativa",
                              "action": "sin_dato", "old": v, "new": None,
                              "reason": f"Deuda neta/EBITDA de {v:.1f}x".replace("-", "−")
                                        + ": EBITDA ≤ 0, la ratio no es significativa"})
    return flags
