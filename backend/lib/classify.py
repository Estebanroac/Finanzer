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
  GROWTH_PRE_PROFIT  BPA TTM <= 0 o margen neto < 0, y CAGR real de ingresos a
                     3 años > 15% (con los 4 ejercicios anuales).
  CYCLICAL           industria de la lista de cíclicas de Yahoo; las
                     "condicionales" (Semiconductors, Specialty Chemicals)
                     solo si hay reversión en la ventana: caída pico-valle del
                     margen operativo o caída anual de ingresos.
  MATURE             por defecto.

Además, una regla cuantitativa SOLO de alerta: una empresa no cíclica con el
margen operativo o el crecimiento muy volátiles se marca "posible cíclica" y
baja la confianza, sin cambiar el arquetipo.
"""
import re
from typing import Any, Dict, List, Optional

from historical_metrics import detrended_std, ratio_series, stdev, strict_cagr, yoy_growths
from settings import cfg

FINANCIAL = "FINANCIAL"
REIT = "REIT"
GROWTH_PRE_PROFIT = "GROWTH_PRE_PROFIT"
CYCLICAL = "CYCLICAL"
MATURE = "MATURE"
ARCHETYPES = (FINANCIAL, REIT, GROWTH_PRE_PROFIT, CYCLICAL, MATURE)

_C = cfg("sectors.archetypes")

# Por qué un componente no aplica a cada arquetipo (texto del informe).
WHY_NOT_APPLICABLE = {
    FINANCIAL: "el balance es el producto (depósitos y préstamos)",
    REIT: "el beneficio contable está distorsionado por la depreciación inmobiliaria",
    GROWTH_PRE_PROFIT: "aún no tiene beneficios que capitalizar",
    CYCLICAL: "el resultado de un solo ejercicio depende de la fase del ciclo",
    MATURE: "",
}

# Motivo propio de un componente cuando el del arquetipo no lo explica.
WHY_NOT_APPLICABLE_KEY = {
    (REIT, "current_ratio"): "activos inmobiliarios de largo plazo financiados con deuda a largo plazo; "
                             "el circulante no mide su liquidez",
    (GROWTH_PRE_PROFIT, "altman"): "el Altman se calibró con quiebras de empresas maduras endeudadas; "
                                   "su solidez se mide por el runway (caja frente a la quema de FCF)",
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
    return f"No aplica a {archetype}" + (f": {why}" if why else "")


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
    out = {"op_margin_detrended_std": m_std, "revenue_growth_std": g_std, "flag": False, "detail": None}
    reasons = []
    if m_std is not None and m_std > P["op_margin_detrended_std"]:
        reasons.append(f"margen operativo volátil ({m_std * 100:.1f} pp alrededor de su tendencia > "
                       f"{P['op_margin_detrended_std'] * 100:.0f} pp)")
    if g_std is not None and g_std > P["revenue_growth_std"]:
        reasons.append(f"crecimiento de ingresos volátil ({g_std * 100:.1f} pp > {P['revenue_growth_std'] * 100:.0f} pp)")
    if reasons:
        out["flag"] = True
        out["detail"] = "Posible cíclica: " + "; ".join(reasons) + ". No cambia el arquetipo; baja la confianza."
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
    reasons = []
    if len(margins) >= 2 and drop > R["op_margin_peak_to_trough"]:
        reasons.append(f"el margen operativo cayó {drop * 100:.1f} pp desde un pico (> "
                       f"{R['op_margin_peak_to_trough'] * 100:.0f} pp)")
    if worst is not None and worst < -R["revenue_annual_decline"]:
        reasons.append(f"los ingresos cayeron {abs(worst) * 100:.1f}% en un ejercicio (> "
                       f"{R['revenue_annual_decline'] * 100:.0f}%)")
    return {"op_margin_peak_to_trough": drop if len(margins) >= 2 else None, "worst_revenue_growth": worst,
            "flag": bool(reasons), "detail": "; ".join(reasons)}


def classify(*, sector: Optional[str], industry: Optional[str], eps_ttm: Optional[float],
             net_margin_ttm: Optional[float], statements_fy: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
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

    def out(arch, reason, rule, ambiguous=False):
        res = {"archetype": arch, "reason": reason, "rule": rule, "sector": sector or None,
               "industry": ind_txt, "ambiguous": ambiguous, "confidence": "baja" if ambiguous else "normal",
               "alerts": [], "inputs": inputs}
        if arch != CYCLICAL:
            pc = _possible_cyclical(st)
            inputs["op_margin_detrended_std"] = pc["op_margin_detrended_std"]
            inputs["revenue_growth_std"] = pc["revenue_growth_std"]
            if pc["flag"]:
                res["alerts"].append({"code": "posible_ciclica", "detail": pc["detail"]})
                res["confidence"] = "baja"
        return res

    by_ind = f"por industria {ind_txt}" if ind_txt else ""

    # 1. FINANCIAL: bancos y aseguradoras, por industria.
    if any(ind.startswith(p) for p in _C["bank_prefixes"]):
        return out(FINANCIAL, f"Clasificada como FINANCIAL {by_ind} (banco)", "industria_banco")
    if any(ind.startswith(p) for p in _C["insurance_prefixes"]):
        return out(FINANCIAL, f"Clasificada como FINANCIAL {by_ind} (aseguradora)", "industria_aseguradora")

    # 2. Excepciones MATURE dentro de Financial Services; el resto, FINANCIAL ambigua.
    if sec in _C["financial_sectors"]:
        if ind in _C["financial_mature_industries"]:
            return out(MATURE, f"Clasificada como MATURE {by_ind}: excepción dentro de Financial Services "
                               "(sin cartera de préstamos en el balance)", "excepcion_financiera")
        if ind in _C["payment_network_industries"]:
            lim = _C["payment_network_max_assets_to_revenue"]
            if assets_to_revenue is not None and assets_to_revenue <= lim:
                return out(MATURE, f"Clasificada como MATURE {by_ind} de tipo red de pagos (activos/ingresos "
                                   f"{assets_to_revenue:.1f}x <= {lim:.1f}x): excepción dentro de Financial Services",
                           "red_de_pagos")
            why = (f"activos/ingresos {assets_to_revenue:.1f}x > {lim:.1f}x: cartera de préstamos en el balance"
                   if assets_to_revenue is not None else "sin datos de balance para distinguir una red de pagos")
            return out(FINANCIAL, f"Clasificada como FINANCIAL {by_ind} ({why})", "credito_con_balance",
                       ambiguous=assets_to_revenue is None)
        what = f"industria financiera ambigua ({ind_txt})" if ind_txt else "industria sin dato"
        return out(FINANCIAL, f"Clasificada como FINANCIAL por sector Financial Services: {what}; "
                              "se trata como FINANCIAL", "financiera_ambigua", ambiguous=True)

    # 3. REIT: solo industrias "REIT - …".
    if any(ind.startswith(p) for p in _C["reit_prefixes"]):
        return out(REIT, f"Clasificada como REIT {by_ind}", "industria_reit")

    # 4. GROWTH_PRE_PROFIT: sin beneficio y crecimiento real alto.
    no_profit = (eps_ttm is not None and eps_ttm <= 0) or (net_margin_ttm is not None and net_margin_ttm < 0)
    g_min = _C["growth_pre_profit_min_revenue_cagr"]
    if no_profit and rev_cagr is not None and rev_cagr > g_min:
        what = (f"BPA TTM {eps_ttm:.2f} <= 0" if (eps_ttm is not None and eps_ttm <= 0)
                else f"margen neto {net_margin_ttm * 100:.1f}% < 0")
        return out(GROWTH_PRE_PROFIT, f"Clasificada como GROWTH_PRE_PROFIT: {what} y CAGR de ingresos a 3 años "
                                      f"{rev_cagr * 100:.1f}% > {g_min * 100:.0f}%", "pre_beneficio_con_crecimiento")

    # 5. CYCLICAL: industria cíclica siempre, o condicional con volatilidad alta.
    if ind in _C["cyclical_industries"]:
        extra = " (inmobiliaria no REIT)" if sec == "real estate" else ""
        return out(CYCLICAL, f"Clasificada como CYCLICAL {by_ind}{extra}", "industria_ciclica")
    if ind in _C["cyclical_conditional_industries"]:
        rv = _reversion(st)
        inputs["op_margin_peak_to_trough"] = rv["op_margin_peak_to_trough"]
        inputs["worst_revenue_growth"] = rv["worst_revenue_growth"]
        if rv["flag"]:
            return out(CYCLICAL, f"Clasificada como CYCLICAL {by_ind} (cíclica condicional) con reversión en la "
                                 f"ventana: {rv['detail']}", "industria_ciclica_condicional")
        return out(MATURE, f"Clasificada como MATURE: industria {ind_txt} (cíclica condicional) sin reversión en los "
                           "ejercicios disponibles (ni caída pico-valle del margen ni caída anual de ingresos)",
                   "ciclica_condicional_estable")

    # 6. MATURE por defecto.
    extra = f" (industria {ind_txt}" + ("; inmobiliaria no REIT)" if sec == "real estate" else ")") if ind_txt \
        else " (industria sin dato)"
    return out(MATURE, "Clasificada como MATURE por defecto: no es financiera, REIT, pre-beneficio con "
                       f"crecimiento ni de industria cíclica{extra}", "por_defecto")
