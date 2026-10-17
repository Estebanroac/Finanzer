"""
Clasificador de arquetipos (etapa 6 del rediseño; spec §4, RECON §6.0 C9-C13).

Una sola función, `classify`, decide el arquetipo ANTES de puntuar. El motor
(score, DCF, Graham, Altman, Piotroski), las alertas, el PDF y el frontend
leen su salida en lugar de decidir cada uno "es financiera" por su cuenta.

Arquetipos, en orden de prioridad (listas y umbrales en config/sectors.toml):
  FINANCIAL          bancos ("Banks…") y aseguradoras ("Insurance - …"); el
                     balance es el producto. Una industria financiera ambigua
                     también cae aquí, marcada como tal.
  MATURE (excepción) dentro de Financial Services: gestoras, bolsas y datos,
                     corredores de seguros y redes de pago sin cartera de
                     préstamos (Credit Services con poca intensidad de balance).
  REIT               industria "REIT - …" (promotoras y servicios inmobiliarios no).
  UTILITY            utilities reguladas (eléctricas, gas, agua y diversificadas);
                     productores independientes y renovables no (etapa 11b).
  GROWTH_PRE_PROFIT  BPA TTM <= 0 o margen neto < 0, y CAGR real de ingresos a
                     3 años > 15% (con los 4 ejercicios anuales).
  CYCLICAL           fase 3 (D4): por su HISTORIA (10+ ejercicios de EDGAR,
                     lib/cyclicality.py): caídas de ingresos repetidas o
                     desplomes del BPA con caída de ingresos. Con historia
                     corta (< min_years), la regla de industria anterior (lista
                     de cíclicas de Yahoo; las "condicionales" solo con
                     reversión en la ventana), con confianza baja.
  GROWTH_PROFITABLE  fase 3 (D4): no cíclica, ingresos por acción que crecen
                     ≥ 15% anual a 3 años (≥ 10% a 5 si hay historia), BPA TTM
                     > 0 y margen operativo (o FCF − SBC) ≥ 10%.
  MATURE             por defecto.

FINANCIAL lleva subtipo (fase 3, F3_DISENO_METODO §1.4): banco, aseguradora,
conglomerado (aseguradora cuyos ingresos de contratos con clientes, que excluyen
los seguros por norma, son la mayoría: BRK-B) o financiera.

Una clasificación que cambia si un umbral se mueve ±20% se marca "frontera" y
su confianza baja (F3_T2_PARADA2).

Además, una regla cuantitativa SOLO de alerta: una empresa no cíclica con el
margen operativo o el crecimiento muy volátiles se marca "posible cíclica" y
baja la confianza, sin cambiar el arquetipo.
"""
import re
from typing import Any, Dict, List, Optional

import cyclicality as cy
from historical_metrics import cagr, detrended_std, ratio_series, stdev, strict_cagr, yoy_growths
from settings import cfg

FINANCIAL = "FINANCIAL"
REIT = "REIT"
GROWTH_PRE_PROFIT = "GROWTH_PRE_PROFIT"
CYCLICAL = "CYCLICAL"
MATURE = "MATURE"
UTILITY = "UTILITY"
GROWTH_PROFITABLE = "GROWTH_PROFITABLE"
ARCHETYPES = (FINANCIAL, REIT, UTILITY, GROWTH_PRE_PROFIT, CYCLICAL, GROWTH_PROFITABLE, MATURE)

_C = cfg("sectors.archetypes")

# Etapa 9b: etiqueta en español para el usuario; el código (FINANCIAL…) queda solo en
# el detalle técnico. ARCHETYPE_GROUP es la forma de "No aplica a …".
ARCHETYPE_LABELS = {
    FINANCIAL: "Banco/aseguradora",
    REIT: "REIT",
    UTILITY: "Utility regulada",
    GROWTH_PRE_PROFIT: "Crecimiento sin beneficio",
    CYCLICAL: "Cíclica",
    GROWTH_PROFITABLE: "Crecimiento rentable",
    MATURE: "Madura",
}
ARCHETYPE_GROUP = {
    FINANCIAL: "bancos y aseguradoras",
    REIT: "REIT",
    UTILITY: "utilities reguladas",
    GROWTH_PRE_PROFIT: "empresas en crecimiento sin beneficio",
    CYCLICAL: "empresas cíclicas",
    GROWTH_PROFITABLE: "empresas de crecimiento rentable",
    MATURE: "empresas maduras",
}
FINANCIAL_SUBTYPE_LABELS = {"banco": "Banco", "aseguradora": "Aseguradora", "conglomerado": "Conglomerado",
                            "financiera": "Entidad financiera"}


def archetype_label(archetype: Optional[str]) -> str:
    return ARCHETYPE_LABELS.get(archetype or "", archetype or "")


def not_applicable_text(archetype: Optional[str]) -> str:
    """"No aplica a bancos y aseguradoras", "No aplica a empresas cíclicas"…"""
    return f"No aplica a {ARCHETYPE_GROUP.get(archetype or '', archetype or 'este tipo de empresa')}"

# Por qué un componente no aplica a cada arquetipo (texto del informe).
WHY_NOT_APPLICABLE = {
    FINANCIAL: "el balance es el producto (depósitos y préstamos)",
    REIT: "el beneficio contable está distorsionado por la depreciación inmobiliaria",
    GROWTH_PRE_PROFIT: "aún no tiene beneficios que capitalizar",
    UTILITY: "su FCF es negativo por diseño: la inversión en la base de activos regulada supera al flujo "
             "operativo y se financia con deuda",
    CYCLICAL: "el resultado de un solo ejercicio depende de la fase del ciclo",
    GROWTH_PROFITABLE: "",
    MATURE: "",
}

# Motivo propio de un componente cuando el del arquetipo no lo explica.
WHY_NOT_APPLICABLE_KEY = {
    (REIT, "current_ratio"): "activos inmobiliarios de largo plazo financiados con deuda a largo plazo; "
                             "el circulante no mide su liquidez",
    (UTILITY, "altman"): "el Altman se calibró con quiebras de empresas industriales; una utility regulada opera con "
                         "deuda alta y circulante negativo por diseño",
    (UTILITY, "de"): "en una utility regulada el apalancamiento se mide por la deuda neta/EBITDA, con bandas propias",
    (UTILITY, "current_ratio"): "la base regulada se financia a largo plazo; el circulante negativo es estructural y no "
                                "mide su liquidez",
    (UTILITY, "ev_ebitda"): "se valora por P/E frente al sector y rentabilidad por dividendo",
    (UTILITY, "peg"): "su crecimiento lo fija la base regulada, no el mercado: se valora por P/E y dividendo",
    (UTILITY, "garp"): "se valora por P/E y dividendo, sin bonos de crecimiento",
    (GROWTH_PRE_PROFIT, "altman"): "el Altman se calibró con quiebras de empresas maduras endeudadas; "
                                   "su solidez se mide por el runway (caja frente a la quema de FCF)",
    # Etapa 9a: rentabilidad de REIT (sobre FFO) y de GROWTH_PRE_PROFIT (márgenes de su fase).
    (REIT, "gross_margin"): "estructura de arrendamiento neto: el inquilino paga los costes del inmueble, así que "
                            "los márgenes bruto y operativo no son comparables; la rentabilidad se mide sobre el FFO",
    (REIT, "operating_margin"): "estructura de arrendamiento neto: el inquilino paga los costes del inmueble, así que "
                                "los márgenes bruto y operativo no son comparables; la rentabilidad se mide sobre el FFO",
    **{(GROWTH_PRE_PROFIT, k): "negativo por definición del arquetipo (aún sin beneficio); la rentabilidad se mide "
                               "con el margen bruto, el margen operativo y su mejora, y el margen FCF − SBC"
       for k in ("roe", "roa", "net_margin", "roic_wacc")},
}

# Nombre legible de cada componente (claves de sectors.archetypes.not_applicable).
COMPONENT_LABELS = {
    "piotroski": "Piotroski F", "altman": "Altman Z", "ocf": "Flujo operativo", "fcf": "FCF",
    "fcf_to_ni": "FCF / beneficio neto", "de": "D/E", "ev_ebitda": "EV/EBITDA", "pe": "P/E",
    "peg": "PEG", "forward_pe": "Forward P/E", "p_fcf": "P/FCF",
    "garp": "Bonos de crecimiento (GARP)", "current_ratio": "Current ratio",
    "interest_coverage": "Cobertura de intereses", "net_debt_ebitda": "Deuda neta/EBITDA",
    "roic_wacc": "ROIC−WACC", "operating_margin": "Margen operativo",
    "fcf_growth": "Crecimiento del FCF", "eps_growth": "Crecimiento del BPA",
    "dcf": "DCF (FCFF)", "graham": "Número de Graham", "roce": "ROCE",
    "roe": "ROE", "roa": "ROA", "net_margin": "Margen neto", "gross_margin": "Margen bruto",
}


def norm_industry(text: Optional[str]) -> str:
    """Industria comparable: minúsculas y guiones unificados como " - "."""
    s = (text or "").strip().lower()
    return re.sub(r"\s*[—–]\s*|\s+-\s+", " - ", s)


def display_industry(text: Optional[str]) -> str:
    """Industria para el informe con el guion unificado ("REIT—Retail" -> "REIT - Retail")."""
    return re.sub(r"\s*[—–]\s*|\s+-\s+", " - ", (text or "").strip())


def not_applicable(archetype: Optional[str], key: str) -> Optional[str]:
    """Motivo "No aplica a ARQUETIPO: …" si el componente `key` no aplica; None si aplica."""
    if not archetype or key not in cfg(f"sectors.archetypes.not_applicable.{archetype}"):
        return None
    why = WHY_NOT_APPLICABLE_KEY.get((archetype, key)) or WHY_NOT_APPLICABLE.get(archetype) or ""
    return not_applicable_text(archetype) + (f": {why}" if why else "")


def _first(values: Optional[List[Optional[float]]]) -> Optional[float]:
    return (values or [None])[0] if values else None


def _possible_cyclical(st: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Alerta "posible cíclica" por volatilidad del margen operativo (alrededor
    de su tendencia) o del crecimiento interanual de ingresos."""
    P = _C["possible_cyclical"]
    rev = list(st.get("revenue") or [])
    margins = ratio_series(st.get("operating_income") or [], rev)
    m_n = [m for m in margins if m is not None]
    growth = [g for g in yoy_growths(rev) if g is not None]
    m_std = detrended_std(m_n) if len(m_n) >= P["min_years"] else None
    g_std = stdev(growth) if len(rev) >= P["min_years"] and len(growth) >= 2 else None
    out = {"op_margin_detrended_std": m_std, "revenue_growth_std": g_std, "flag": False, "detail": None,
           "detail_plain": None}
    reasons, plain = [], []
    if m_std is not None and m_std > P["op_margin_detrended_std"]:
        plain.append(f"su margen operativo oscila {m_std * 100:.1f} puntos alrededor de su tendencia (el umbral es "
                     f"{P['op_margin_detrended_std'] * 100:.0f})")
        reasons.append(f"margen operativo volátil ({m_std * 100:.1f} pp alrededor de su tendencia > "
                       f"{P['op_margin_detrended_std'] * 100:.0f} pp)")
    if g_std is not None and g_std > P["revenue_growth_std"]:
        plain.append(f"su crecimiento de ingresos oscila {g_std * 100:.1f} puntos de un año a otro (el umbral es "
                     f"{P['revenue_growth_std'] * 100:.0f})")
        reasons.append(f"crecimiento de ingresos volátil ({g_std * 100:.1f} pp > {P['revenue_growth_std'] * 100:.0f} pp)")
    if reasons:
        out["flag"] = True
        out["detail"] = "Posible cíclica: " + "; ".join(reasons) + ". No cambia el arquetipo; baja la confianza."
        out["detail_plain"] = ("Podría ser cíclica: " + " y ".join(plain) + ". No cambia su tipo, pero baja la "
                               "confianza del veredicto.")
    return out


def _reversion(st: Dict[str, Any]) -> Dict[str, Any]:
    """Reversión dentro de la ventana de ejercicios (orden cronológico): mayor caída
    del margen operativo desde un pico anterior y peor variación anual de ingresos."""
    R = _C["reversion"]
    rev = list(st.get("revenue") or [])
    margins = [m for m in reversed(ratio_series(st.get("operating_income") or [], rev)) if m is not None]
    drop, peak = 0.0, None
    for m in margins:
        peak = m if peak is None else max(peak, m)
        drop = max(drop, peak - m)
    growth = [g for g in yoy_growths(rev) if g is not None]
    worst = min(growth) if growth else None
    reasons, plain = [], []
    if len(margins) >= 2 and drop > R["op_margin_peak_to_trough"]:
        plain.append(f"su margen operativo cayó {drop * 100:.1f} puntos desde un máximo")
        reasons.append(f"el margen operativo cayó {drop * 100:.1f} pp desde un pico (> "
                       f"{R['op_margin_peak_to_trough'] * 100:.0f} pp)")
    if worst is not None and worst < -R["revenue_annual_decline"]:
        plain.append(f"sus ingresos cayeron un {abs(worst) * 100:.1f}% en un ejercicio")
        reasons.append(f"los ingresos cayeron {abs(worst) * 100:.1f}% en un ejercicio (> "
                       f"{R['revenue_annual_decline'] * 100:.0f}%)")
    return {"op_margin_peak_to_trough": drop if len(margins) >= 2 else None, "worst_revenue_growth": worst,
            "flag": bool(reasons), "detail": "; ".join(reasons), "detail_plain": " y ".join(plain)}


def _insurer_subtype(history: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Aseguradora o conglomerado: peso de los ingresos de contratos con clientes (los contratos de seguro quedan
    fuera por norma, ASC 606 / NIIF 15) en los ingresos del último ejercicio de la historia de EDGAR."""
    thr = _C["financial_subtypes"]["conglomerate_min_non_insurance_share"]
    rev = dict(cy._series(history or {}, "revenue"))
    cr = cy._series(history or {}, "contract_revenue")
    both = [(e, c, rev[e]) for e, c in cr if rev.get(e)]
    if not both:
        return {"subtype": "aseguradora", "non_insurance_share": None}
    e, c, r = both[-1]
    share = c / r
    return {"subtype": "conglomerado" if share >= thr else "aseguradora", "non_insurance_share": share, "fy_end": e}


def _cyclicality(history: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Ciclicidad por la historia (lib/cyclicality) con su sensibilidad: qué umbral, movido ±20%, cambia la decisión.
    None sin historia."""
    if not history:
        return None
    r = cy.classify_history(history)
    C = _C["cyclicality"]
    flips = []
    for k in ("revenue_decline", "eps_drop", "min_decline_episodes", "min_eps_collapses", "min_years"):
        for f in (0.8, 1.2):
            v = C[k] * f
            if isinstance(C[k], int):
                v = max(1, round(v))
                if v == C[k]:
                    continue
            if cy.classify_history(history, {k: v})["cyclical"] != r["cyclical"]:
                flips.append(f"{k} {C[k]}→{v:g}")
    r["sensitivity"] = flips
    return r


def _growth_profitable(eps_ttm, op_margin, fcf_sbc_margin, history, st) -> Dict[str, Any]:
    """Crecimiento rentable (§1.3): ingresos por acción ≥ 15% anual a 3 años (≥ 10% a 5 si hay historia), BPA TTM > 0
    y margen operativo (o FCF − SBC) ≥ 10%. Sin historia de EDGAR, los ejercicios de Yahoo por acción."""
    G = _C["growth_profitable"]
    m = cy.growth_profitable_measures(history) if history else {"basis": None}
    if not history or m.get("revenue_ps_cagr_3y") is None:
        rev, sh = st.get("revenue") or [], st.get("ordinary_shares") or []
        ps = [(r / s) if (r is not None and s) else None for r, s in zip(rev, sh)]
        c3 = cagr(ps[0], ps[3], 3) if len(ps) >= 4 and ps[0] and ps[3] and ps[0] > 0 and ps[3] > 0 else None
        m = {"basis": "por_accion (Yahoo)", "revenue_ps_cagr_3y": c3, "revenue_ps_cagr_5y": None}
    margin = op_margin if (op_margin is not None and op_margin >= G["min_operating_margin"]) else None
    alt = fcf_sbc_margin if (margin is None and fcf_sbc_margin is not None
                             and fcf_sbc_margin >= G["min_operating_margin"]) else None

    def meets(t3, t5, tm):
        c3, c5 = m.get("revenue_ps_cagr_3y"), m.get("revenue_ps_cagr_5y")
        prof = (op_margin is not None and op_margin >= tm) or (fcf_sbc_margin is not None and fcf_sbc_margin >= tm)
        return bool(c3 is not None and c3 >= t3 and (c5 is None or c5 >= t5)
                    and eps_ttm is not None and eps_ttm > 0 and prof)
    ok = meets(G["min_revenue_ps_cagr_3y"], G["min_revenue_ps_cagr_5y"], G["min_operating_margin"])
    flips = []
    for k, idx in (("min_revenue_ps_cagr_3y", 0), ("min_revenue_ps_cagr_5y", 1), ("min_operating_margin", 2)):
        for f in (0.8, 1.2):
            t = [G["min_revenue_ps_cagr_3y"], G["min_revenue_ps_cagr_5y"], G["min_operating_margin"]]
            t[idx] *= f
            if meets(*t) != ok:
                flips.append(f"{k} {G[k]:g}→{t[idx]:g}")
    return {**m, "meets": ok, "operating_margin": op_margin, "fcf_sbc_margin": fcf_sbc_margin,
            "margin_used": "operativo" if margin is not None else ("FCF − SBC" if alt is not None else None),
            "sensitivity": flips}


def classify(*, sector: Optional[str], industry: Optional[str], eps_ttm: Optional[float],
             net_margin_ttm: Optional[float], statements_fy: Optional[Dict[str, Any]] = None,
             history: Optional[Dict[str, Any]] = None, operating_margin_ttm: Optional[float] = None,
             fcf_sbc_margin: Optional[float] = None) -> Dict[str, Any]:
    """Arquetipo y motivo de la clasificación.

    Devuelve {archetype, reason, rule, sector, industry, ambiguous, confidence,
    alerts, inputs}. `inputs` guarda los datos que decidieron (CAGR de ingresos,
    intensidad de balance, volatilidades) para auditar la decisión."""
    st = statements_fy or {}
    ind_raw = industry if industry and industry.strip().lower() not in ("unknown", "n/a") else None
    ind = norm_industry(ind_raw)
    ind_txt = display_industry(ind_raw) if ind_raw else None
    sec = (sector or "").strip().lower()

    rev_cagr, rev_cagr_why = strict_cagr(st.get("revenue") or [], 3)
    rev0, ta0 = _first(st.get("revenue")), _first(st.get("total_assets"))
    assets_to_revenue = (ta0 / rev0) if (ta0 is not None and rev0 and rev0 > 0) else None
    inputs = {"revenue_cagr_3y": rev_cagr, "revenue_cagr_3y_reason": rev_cagr_why,
              "eps_ttm": eps_ttm, "net_margin_ttm": net_margin_ttm,
              "assets_to_revenue": assets_to_revenue}
    # Ciclicidad por la historia: se mide aquí porque también decide si hace falta la alerta de posible cíclica.
    cyc = _cyclicality(history)
    hist_decides = cyc is not None and cyc["enough"]
    cond_stable = False     # industria cíclica condicional sin reversión en la ventana (sin historia que decida)

    def out(arch, reason, rule, plain, ambiguous=False, subtype=None, frontier=None):
        # reason: motivo técnico (detalle); reason_plain: el mismo motivo en prosa para el usuario.
        res = {"archetype": arch, "label": ARCHETYPE_LABELS[arch], "reason": reason, "reason_plain": plain,
               "rule": rule, "sector": sector or None,
               "industry": ind_txt, "ambiguous": ambiguous, "confidence": "baja" if ambiguous else "normal",
               "alerts": [], "inputs": inputs, "subtype": subtype,
               "subtype_label": FINANCIAL_SUBTYPE_LABELS.get(subtype) if subtype else None,
               "frontier": frontier or None}
        if frontier:
            res["confidence"] = "baja"
        if arch != CYCLICAL and not hist_decides:
            # Con historia suficiente la ciclicidad ya se midió en 10+ ejercicios; la alerta de la ventana corta de
            # Yahoo (4 ejercicios) solo queda para los emisores sin esa historia.
            pc = _possible_cyclical(st)
            inputs["op_margin_detrended_std"] = pc["op_margin_detrended_std"]
            inputs["revenue_growth_std"] = pc["revenue_growth_std"]
            if pc["flag"]:
                res["alerts"].append({"code": "posible_ciclica", "detail": pc["detail"],
                                      "detail_plain": pc["detail_plain"]})
                res["confidence"] = "baja"
        return res

    by_ind = f"por industria {ind_txt}" if ind_txt else ""

    # 1. FINANCIAL: bancos y aseguradoras, por industria.
    if any(ind.startswith(p) for p in _C["bank_prefixes"]):
        return out(FINANCIAL, f"Clasificada como FINANCIAL {by_ind} (banco)", "industria_banco",
                   f"Banco por su industria ({ind_txt}): el balance es el producto.", subtype="banco")
    if any(ind.startswith(p) for p in _C["insurance_prefixes"]):
        ins = _insurer_subtype(history)
        inputs["non_insurance_revenue_share"] = ins["non_insurance_share"]
        if ins["subtype"] == "conglomerado":
            sh = ins["non_insurance_share"] * 100
            return out(FINANCIAL, f"Clasificada como FINANCIAL {by_ind} (conglomerado: los ingresos de contratos con "
                                  f"clientes, sin seguros, son el {sh:.0f}% de los ingresos del FY{ins['fy_end'][:4]})",
                       "industria_aseguradora",
                       f"Conglomerado con negocio asegurador ({ind_txt}): el {sh:.0f}% de sus ingresos son de "
                       "negocios que no son seguros.", subtype="conglomerado")
        return out(FINANCIAL, f"Clasificada como FINANCIAL {by_ind} (aseguradora)", "industria_aseguradora",
                   f"Aseguradora por su industria ({ind_txt}): el balance es el producto.", subtype="aseguradora")

    # 2. Excepciones MATURE dentro de Financial Services; el resto, FINANCIAL ambigua.
    if sec in _C["financial_sectors"]:
        if ind in _C["financial_mature_industries"]:
            return out(MATURE, f"Clasificada como MATURE {by_ind}: excepción dentro de Financial Services "
                               "(sin cartera de préstamos en el balance)", "excepcion_financiera",
                       f"Madura: dentro de los servicios financieros, su industria ({ind_txt}) no tiene cartera "
                       "de préstamos en el balance.")
        if ind in _C["payment_network_industries"]:
            lim = _C["payment_network_max_assets_to_revenue"]
            if assets_to_revenue is not None and assets_to_revenue <= lim:
                return out(MATURE, f"Clasificada como MATURE {by_ind} de tipo red de pagos (activos/ingresos "
                                   f"{assets_to_revenue:.1f}x <= {lim:.1f}x): excepción dentro de Financial Services",
                           "red_de_pagos",
                           f"Madura: red de pagos ({ind_txt}) con {assets_to_revenue:.1f} veces sus ingresos en "
                           f"activos (hasta {lim:.1f} veces), sin cartera de préstamos en el balance.")
            why = (f"activos/ingresos {assets_to_revenue:.1f}x > {lim:.1f}x: cartera de préstamos en el balance"
                   if assets_to_revenue is not None else "sin datos de balance para distinguir una red de pagos")
            plain = (f"Banco/aseguradora: {ind_txt} con {assets_to_revenue:.1f} veces sus ingresos en activos "
                     f"(más de {lim:.1f} veces): tiene cartera de préstamos en el balance."
                     if assets_to_revenue is not None else
                     f"Banco/aseguradora: {ind_txt} sin datos de balance para distinguirla de una red de pagos.")
            return out(FINANCIAL, f"Clasificada como FINANCIAL {by_ind} ({why})", "credito_con_balance", plain,
                       ambiguous=assets_to_revenue is None, subtype="financiera")
        what = f"industria financiera ambigua ({ind_txt})" if ind_txt else "industria sin dato"
        return out(FINANCIAL, f"Clasificada como FINANCIAL por sector Financial Services: {what}; "
                              "se trata como FINANCIAL", "financiera_ambigua",
                   "Banco/aseguradora: sector financiero con una industria ambigua"
                   + (f" ({ind_txt})" if ind_txt else "") + "; se analiza como entidad financiera.", ambiguous=True,
                   subtype="financiera")

    # 3. REIT: solo industrias "REIT - …".
    if any(ind.startswith(p) for p in _C["reit_prefixes"]):
        return out(REIT, f"Clasificada como REIT {by_ind}", "industria_reit", f"REIT por su industria ({ind_txt}).")

    # 3b. UTILITY (etapa 11b): solo las reguladas, por industria.
    if ind in _C["utility_industries"]:
        return out(UTILITY, f"Clasificada como UTILITY {by_ind}", "industria_utility",
                   f"Utility regulada por su industria ({ind_txt}): el regulador fija su retorno sobre una base de "
                   "activos financiada con deuda.")

    # 4. GROWTH_PRE_PROFIT: sin beneficio y crecimiento real alto.
    no_profit = (eps_ttm is not None and eps_ttm <= 0) or (net_margin_ttm is not None and net_margin_ttm < 0)
    g_min = _C["growth_pre_profit_min_revenue_cagr"]
    if no_profit and rev_cagr is not None and rev_cagr > g_min:
        what = (f"BPA TTM {eps_ttm:.2f} <= 0" if (eps_ttm is not None and eps_ttm <= 0)
                else f"margen neto {net_margin_ttm * 100:.1f}% < 0")
        what_plain = (f"beneficio por acción negativo en los últimos doce meses ({eps_ttm:.2f})".replace("-", "−")
                      if (eps_ttm is not None and eps_ttm <= 0)
                      else f"margen neto negativo ({net_margin_ttm * 100:.1f}%)".replace("-", "−"))
        return out(GROWTH_PRE_PROFIT, f"Clasificada como GROWTH_PRE_PROFIT: {what} y CAGR de ingresos a 3 años "
                                      f"{rev_cagr * 100:.1f}% > {g_min * 100:.0f}%", "pre_beneficio_con_crecimiento",
                   f"Crecimiento sin beneficio: {what_plain} e ingresos totales que crecen un {rev_cagr * 100:.1f}% "
                   f"anual en 3 años, por encima del {g_min * 100:.0f}%.")

    # 5. CYCLICAL (fase 3, D4): por la historia de EDGAR si hay bastante; si no, por la industria con confianza baja.
    if cyc is not None:
        m = cyc["measures"]
        inputs["cyclicality"] = {"years": m.get("years"), "basis": m.get("basis"),
                                 "decline_episodes": m.get("decline_episodes"),
                                 "eps_collapse_with_decline": m.get("eps_collapse_with_decline"),
                                 "perimeter_years": m.get("perimeter_years"), "triggers": cyc["triggers"],
                                 "enough": cyc["enough"], "sensitivity": cyc["sensitivity"],
                                 "design_measures": m.get("design")}
    if hist_decides:
        if cyc["cyclical"]:
            eps_ = ", ".join("–".join(y[:4] for y in (ep[0], ep[-1])) if len(ep) > 1 else ep[0][:4]
                             for ep in m["decline_episodes"])
            col = ", ".join(y[:4] for y in m["eps_collapse_with_decline"])
            what = "; ".join(filter(None, [
                f"caídas de ingresos ≥ {_C['cyclicality']['revenue_decline'] * 100:.0f}% en {eps_}" if eps_ else "",
                f"desplomes del BPA con caída de ingresos en {col}" if col else ""]))
            # §1.1 paso 6: si además crece con beneficio, se reconoce como nota (crecimiento estructural), sin
            # cambiar de herramienta: la que más crece en la parte alta del ciclo es la que más necesita el ciclo medio.
            gp = _growth_profitable(eps_ttm, operating_margin_ttm, fcf_sbc_margin, history, st)
            inputs["growth_profitable"] = gp
            note = (f"; además crece con beneficio (crecimiento estructural: ingresos por acción "
                    f"{gp['revenue_ps_cagr_3y'] * 100:.1f}% anual a 3 años)" if gp["meets"] else "")
            res = out(CYCLICAL, f"Clasificada como CYCLICAL por su historia ({m['years']} ejercicios en EDGAR): "
                                f"{what}{note}", "historia_ciclica",
                      f"Cíclica por su historia: en {m['years']} ejercicios, {what}{note}.",
                      frontier=cyc["sensitivity"])
            res["structural_growth"] = gp["meets"]
            return res
    elif ind in _C["cyclical_industries"] or ind in _C["cyclical_conditional_industries"]:
        short = (f" (historia corta: {cyc['measures']['years']} ejercicios en EDGAR, menos de "
                 f"{_C['cyclicality']['min_years']})" if cyc is not None else " (sin historia de EDGAR)")
        if ind in _C["cyclical_industries"]:
            extra = " (inmobiliaria no REIT)" if sec == "real estate" else ""
            return out(CYCLICAL, f"Clasificada como CYCLICAL {by_ind}{extra}{short}", "industria_ciclica",
                       f"Cíclica por su industria ({ind_txt}){extra}; sin historia suficiente para medirlo.",
                       ambiguous=True)
        rv = _reversion(st)
        inputs["op_margin_peak_to_trough"] = rv["op_margin_peak_to_trough"]
        inputs["worst_revenue_growth"] = rv["worst_revenue_growth"]
        if rv["flag"]:
            return out(CYCLICAL, f"Clasificada como CYCLICAL {by_ind} (cíclica condicional) con reversión en la "
                                 f"ventana: {rv['detail']}{short}", "industria_ciclica_condicional",
                       f"Cíclica: su industria ({ind_txt}) puede serlo y en los últimos ejercicios "
                       f"{rv['detail_plain']}.", ambiguous=True)
        cond_stable = True

    # 6. GROWTH_PROFITABLE (fase 3, D4): no cíclica y crecimiento rentable.
    gp = _growth_profitable(eps_ttm, operating_margin_ttm, fcf_sbc_margin, history, st)
    inputs["growth_profitable"] = gp
    if gp["meets"]:
        c3, c5 = gp["revenue_ps_cagr_3y"], gp.get("revenue_ps_cagr_5y")
        mtxt = (f"margen operativo {operating_margin_ttm * 100:.0f}%" if gp["margin_used"] == "operativo"
                else f"margen FCF − SBC {fcf_sbc_margin * 100:.0f}%")
        yrs = f" y {c5 * 100:.1f}% a 5" if c5 is not None else ""
        frontier = gp["sensitivity"] + (cyc["sensitivity"] if cyc else [])
        return out(GROWTH_PROFITABLE, f"Clasificada como GROWTH_PROFITABLE: ingresos por acción {c3 * 100:.1f}% anual "
                                      f"a 3 años{yrs}, BPA TTM > 0 y {mtxt}"
                                      + ("; no cíclica por su historia" if hist_decides else ""),
                   "crecimiento_rentable",
                   f"Crecimiento rentable: sus ingresos por acción crecen un {c3 * 100:.1f}% anual en 3 años{yrs}, "
                   f"con beneficio y un {mtxt}.", ambiguous=not hist_decides,
                   frontier=frontier)

    # 7. MATURE por defecto.
    if cond_stable:
        return out(MATURE, f"Clasificada como MATURE: industria {ind_txt} (cíclica condicional) sin reversión en los "
                           "ejercicios disponibles (ni caída pico-valle del margen ni caída anual de ingresos)"
                           f"{short}", "ciclica_condicional_estable",
                   f"Madura: su industria ({ind_txt}) puede ser cíclica, pero en los ejercicios disponibles no "
                   "hubo caídas fuertes del margen ni de los ingresos.", ambiguous=True,
                   frontier=gp["sensitivity"])
    extra = f" (industria {ind_txt}" + ("; inmobiliaria no REIT)" if sec == "real estate" else ")") if ind_txt \
        else " (industria sin dato)"
    frontier = (cyc["sensitivity"] if cyc else []) + gp["sensitivity"]
    hist_txt = (f"; su historia ({cyc['measures']['years']} ejercicios en EDGAR) no muestra ciclo"
                if hist_decides else "")
    return out(MATURE, "Clasificada como MATURE por defecto: no es financiera, REIT, pre-beneficio con "
                       f"crecimiento, cíclica ni de crecimiento rentable{extra}{hist_txt}", "por_defecto",
               "Madura: no es un banco ni una aseguradora, ni un REIT, ni una empresa en crecimiento sin beneficio, "
               "ni cíclica, ni de crecimiento rentable" + (f" ({ind_txt})." if ind_txt else "."),
               ambiguous=not hist_decides, frontier=frontier)
