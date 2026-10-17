"""
Lecturas que entienden el modelo de negocio (fase 3, T6; F3_DISENO §5).

  · **Capital circulante negativo estructural** (restauración, comercio, aerolíneas, software por suscripción y
    consumo básico con financiación de proveedores): un current ratio < 1 es normal en un negocio que cobra antes de
    pagar. No puntúa en Solidez ni alerta, salvo que empeore frente a su propia historia (el último ejercicio por
    debajo de la mediana de los anteriores en más de `worsening_rel`).
  · **Altman referencial**: en esas industrias el modelo (calibrado con manufactureras y su capital circulante
    positivo) no se diseñó para su estructura: se muestra como referencia y no vota.
  · **Piotroski**: modelo cerrado, sin cambio de método; el texto avisa de qué criterios informan poco en la industria
    (liquidez y margen bruto).
Industrias en config (sectors.business_model), normalizadas como el clasificador.
"""
from statistics import median
from typing import Any, Dict, List, Optional

from classify import norm_industry
from settings import cfg


def structural_negative_wc(industry: Optional[str]) -> bool:
    return norm_industry(industry) in cfg("sectors.business_model.negative_working_capital_industries")


def current_ratio_context(industry: Optional[str], st: Optional[Dict[str, Any]],
                          current_ratio: Optional[float]) -> Dict[str, Any]:
    """{structural, history: [CR de cada ejercicio], median_prior, worsening, applies} para la lectura, el score y
    la alerta. `applies`: el current ratio < 1 se lee como estructural (no puntúa ni alerta)."""
    st = st or {}
    ca, cl = st.get("current_assets") or [], st.get("current_liabilities") or []
    hist = [(a / b) if (a is not None and b) else None for a, b in zip(ca, cl)]
    prior = [x for x in hist[1:] if x is not None]
    med = median(prior) if prior else None
    structural = structural_negative_wc(industry)
    rel = cfg("sectors.business_model.worsening_rel")
    worsening = bool(current_ratio is not None and med is not None and current_ratio < med * (1.0 - rel))
    applies = bool(structural and current_ratio is not None and current_ratio < 1.0 and not worsening)
    return {"structural": structural, "history": hist, "median_prior": med, "worsening": worsening,
            "applies": applies, "industry": industry}


def altman_referential(industry: Optional[str]) -> bool:
    return norm_industry(industry) in cfg("sectors.business_model.altman_referential_industries")


def piotroski_caveat(industry: Optional[str]) -> Optional[str]:
    if not structural_negative_wc(industry):
        return None
    return ("En esta industria los criterios de liquidez (current ratio) y de margen bruto informan poco: el capital "
            "circulante negativo y su estructura de márgenes son propios del modelo de negocio.")


def cr_history_text(ctx: Dict[str, Any]) -> Optional[str]:
    h: List[Optional[float]] = [x for x in ctx.get("history") or [] if x is not None]
    if len(h) < 2 or ctx.get("median_prior") is None:
        return None
    return f"mediana de los {len(h) - 1} ejercicios anteriores {ctx['median_prior']:.2f}x"
